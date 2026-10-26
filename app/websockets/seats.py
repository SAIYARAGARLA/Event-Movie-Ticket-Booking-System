import json
from fastapi import APIRouter,WebSocket,WebSocketDisconnect
from jose import jwt,JWTError
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.config import settings
from app.models.models import User,Show,Seat,BookedSeat
from app.services.seat_locks import lock_owner
router=APIRouter()
class ConnectionManager:
    def __init__(self):self.connections={}
    async def connect(self,show_id,ws):await ws.accept();self.connections.setdefault(show_id,set()).add(ws)
    def disconnect(self,show_id,ws):self.connections.get(show_id,set()).discard(ws)
    async def broadcast(self,show_id,payload):
        for ws in list(self.connections.get(show_id,set())):
            try:await ws.send_json(payload)
            except Exception:self.disconnect(show_id,ws)
manager=ConnectionManager()
@router.websocket('/ws/shows/{show_id}/seats')
async def seat_socket(ws:WebSocket,show_id:int,token:str):
    try:
        payload=jwt.decode(token,settings.jwt_secret_key,algorithms=[settings.jwt_algorithm]);uid=int(payload['sub'])
    except (JWTError,ValueError,KeyError):await ws.close(code=1008);return
    db:Session=SessionLocal()
    try:
        user=db.get(User,uid);show=db.get(Show,show_id)
        if not user or not user.is_active or not show:await ws.close(code=1008);return
        await manager.connect(show_id,ws)
        booked={x.seat_id for x in db.query(BookedSeat).filter_by(show_id=show_id,is_cancelled=False).all()};items=[]
        for s in sorted(show.screen.seats,key=lambda x:(x.row_label,x.seat_number)):
            owner=lock_owner(show_id,s.id) if s.is_active and s.id not in booked else None
            status='Unavailable' if not s.is_active else 'Booked' if s.id in booked else 'Yours' if owner==str(uid) else 'Locked' if owner else 'Available'
            items.append({'seat_id':s.id,'row':s.row_label,'seat_number':s.seat_number,'status':status})
        await ws.send_json({'type':'seat_map','show_id':show_id,'seats':items})
        while True:await ws.receive_text()
    except WebSocketDisconnect:pass
    finally:manager.disconnect(show_id,ws);db.close()
