import string
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Venue,Screen,Seat
from app.schemas.schemas import VenueIn,ScreenIn,BulkSeatsIn
from app.auth.security import require_roles
router=APIRouter(tags=['Venues, Screens & Seats'])
@router.post('/venues',status_code=201)
def create_venue(data:VenueIn,db:Session=Depends(get_db),user=Depends(require_roles('Admin'))):
    v=Venue(**data.model_dump());db.add(v);db.commit();db.refresh(v);return v
@router.get('/venues')
def list_venues(skip:int=0,limit:int=20,db:Session=Depends(get_db)):
    return db.query(Venue).filter(Venue.is_active==True).offset(skip).limit(min(limit,100)).all()
@router.put('/venues/{venue_id}')
def update_venue(venue_id:int,data:VenueIn,db:Session=Depends(get_db),user=Depends(require_roles('Admin'))):
    v=db.get(Venue,venue_id)
    if not v:raise HTTPException(404,'Venue not found')
    for k,val in data.model_dump().items():setattr(v,k,val)
    db.commit();db.refresh(v);return v
@router.post('/venues/{venue_id}/screens',status_code=201)
def create_screen(venue_id:int,data:ScreenIn,db:Session=Depends(get_db),user=Depends(require_roles('Admin'))):
    if not db.get(Venue,venue_id):raise HTTPException(404,'Venue not found')
    s=Screen(venue_id=venue_id,**data.model_dump());db.add(s);db.commit();db.refresh(s);return s
@router.post('/screens/{screen_id}/seats/bulk',status_code=201)
def bulk_seats(screen_id:int,data:BulkSeatsIn,db:Session=Depends(get_db),user=Depends(require_roles('Admin'))):
    screen=db.get(Screen,screen_id)
    if not screen:raise HTTPException(404,'Screen not found')
    rows=list(string.ascii_uppercase); start=data.start_row.upper(); end=data.end_row.upper()
    if start not in rows or end not in rows or rows.index(start)>rows.index(end):raise HTTPException(422,'Invalid row range')
    created=[]
    for row in rows[rows.index(start):rows.index(end)+1]:
        for num in range(1,data.seats_per_row+1):
            exists=db.query(Seat).filter_by(screen_id=screen_id,row_label=row,seat_number=num).first()
            if not exists:
                seat=Seat(screen_id=screen_id,row_label=row,seat_number=num,category=data.category);db.add(seat);created.append(seat)
    screen.total_seats=db.query(Seat).filter_by(screen_id=screen_id).count()+len(created);db.commit()
    return {'created_count':len(created),'screen_id':screen_id}
@router.get('/screens/{screen_id}/layout')
def layout(screen_id:int,db:Session=Depends(get_db)):
    if not db.get(Screen,screen_id):raise HTTPException(404,'Screen not found')
    seats=db.query(Seat).filter_by(screen_id=screen_id).order_by(Seat.row_label,Seat.seat_number).all(); rows={}
    for s in seats:rows.setdefault(s.row_label,[]).append({'id':s.id,'seat_number':s.seat_number,'category':s.category,'is_active':s.is_active,'status':'Available' if s.is_active else 'Unavailable'})
    return {'screen_id':screen_id,'rows':rows}
@router.put('/seats/{seat_id}/status')
def seat_status(seat_id:int,is_active:bool,db:Session=Depends(get_db),user=Depends(require_roles('Admin'))):
    s=db.get(Seat,seat_id)
    if not s:raise HTTPException(404,'Seat not found')
    s.is_active=is_active;db.commit();return {'seat_id':seat_id,'is_active':s.is_active}
