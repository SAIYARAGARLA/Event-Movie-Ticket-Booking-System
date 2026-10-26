from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import User
from app.schemas.schemas import RegisterIn
from app.auth.security import require_roles,hash_password
router=APIRouter(prefix='/admin',tags=['Admin'])
@router.put('/organizers/{user_id}/approve')
def approve(user_id:int,db:Session=Depends(get_db),admin:User=Depends(require_roles('Admin'))):
    user=db.get(User,user_id)
    if not user or user.role!='Organizer': raise HTTPException(404,'Organizer not found')
    user.is_approved=True; db.commit(); return {'message':'Organizer approved','user_id':user.id}
@router.post('/staff',status_code=201)
def create_staff(data:RegisterIn,venue_id:int,db:Session=Depends(get_db),admin:User=Depends(require_roles('Admin'))):
    if db.query(User).filter(User.email==data.email.lower()).first(): raise HTTPException(409,'Email already registered')
    from app.models.models import Venue
    if not db.get(Venue,venue_id): raise HTTPException(404,'Venue not found')
    staff=User(name=data.name,email=data.email.lower(),phone=data.phone,password_hash=hash_password(data.password),role='Staff',venue_id=venue_id,is_approved=True)
    db.add(staff);db.commit();db.refresh(staff);return {'id':staff.id,'email':staff.email,'role':staff.role,'venue_id':staff.venue_id}
