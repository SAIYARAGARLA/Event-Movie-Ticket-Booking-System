from datetime import datetime,timedelta
from fastapi import APIRouter,Depends,HTTPException,Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app.models.models import Event,Show,Screen,Seat,SeatCategoryPrice,Booking,BookedSeat
from app.schemas.schemas import EventIn,ShowIn
from app.auth.security import get_current_user,require_roles
from app.redis_client import redis_client
from datetime import timezone
router=APIRouter(tags=['Events & Shows'])
def clear_event_cache(event_id=None):
    if redis_client:
        try:
            for k in redis_client.scan_iter('events:*'):redis_client.delete(k)
        except Exception:pass
@router.post('/events',status_code=201)
def create_event(data:EventIn,db:Session=Depends(get_db),user=Depends(require_roles('Organizer'))):
    if not user.is_approved:raise HTTPException(403,'Organizer must be approved by Admin')
    e=Event(organizer_id=user.id,**data.model_dump());db.add(e);db.commit();db.refresh(e);clear_event_cache();return e
@router.get('/events')
def list_events(skip:int=0,limit:int=20,title:str|None=None,city:str|None=None,category:str|None=None,language:str|None=None,from_date:datetime|None=None,to_date:datetime|None=None,min_price:float|None=None,max_price:float|None=None,sort_by:str='title',order:str='asc',db:Session=Depends(get_db)):
    cachekey=f'events:{skip}:{limit}:{title}:{city}:{category}:{language}:{from_date}:{to_date}:{min_price}:{max_price}:{sort_by}:{order}'
    if redis_client:
        try:
            cached=redis_client.get(cachekey)
            if cached:return __import__('json').loads(cached)
        except Exception:pass
    q=db.query(Event).filter(Event.status=='Published')
    if title:q=q.filter(Event.title.ilike(f'%{title}%'))
    if category:q=q.filter(Event.category==category)
    if language:q=q.filter(Event.language==language)
    if city:q=q.join(Event.shows).join(Show.screen).join(Screen.venue).filter(__import__('app.models.models',fromlist=['Venue']).Venue.city.ilike(f'%{city}%'))
    if from_date:q=q.join(Event.shows).filter(Show.start_time>=from_date)
    if to_date:q=q.join(Event.shows).filter(Show.start_time<=to_date)
    sort_col={'title':Event.title,'show_date':Event.created_at,'price':Event.title}.get(sort_by,Event.title)
    q=q.order_by(sort_col.desc() if order.lower()=='desc' else sort_col.asc()).distinct()
    items=q.offset(skip).limit(min(limit,100)).all()
    out=[{'id':e.id,'organizer_id':e.organizer_id,'title':e.title,'category':e.category,'language':e.language,'description':e.description,'duration_minutes':e.duration_minutes,'age_rating':e.age_rating,'status':e.status,'shows':[{'id':s.id,'start_time':s.start_time.isoformat(),'end_time':s.end_time.isoformat(),'screen_id':s.screen_id,'status':s.status,'prices':{p.category:float(p.price) for p in s.prices}} for s in e.shows if s.status=='Scheduled']} for e in items]
    if redis_client:
        try:redis_client.setex(cachekey,300,__import__('json').dumps(out))
        except Exception:pass
    return out
@router.get('/events/{event_id}')
def event_detail(event_id:int,db:Session=Depends(get_db)):
    e=db.get(Event,event_id)
    if not e or e.status!='Published':raise HTTPException(404,'Published event not found')
    return {'id':e.id,'title':e.title,'category':e.category,'language':e.language,'description':e.description,'duration_minutes':e.duration_minutes,'age_rating':e.age_rating,'shows':[{'id':s.id,'start_time':s.start_time,'end_time':s.end_time,'screen_id':s.screen_id,'prices':{p.category:float(p.price) for p in s.prices}} for s in e.shows if s.status=='Scheduled']}
@router.put('/events/{event_id}')
def update_event(event_id:int,data:EventIn,db:Session=Depends(get_db),user=Depends(require_roles('Organizer'))):
    e=db.get(Event,event_id)
    if not e:raise HTTPException(404,'Event not found')
    if e.organizer_id!=user.id:raise HTTPException(403,'You can manage only your own events')
    for k,v in data.model_dump().items():setattr(e,k,v)
    db.commit();db.refresh(e);clear_event_cache();return e
@router.post('/events/{event_id}/shows',status_code=201)
def create_show(event_id:int,data:ShowIn,db:Session=Depends(get_db),user=Depends(require_roles('Organizer'))):
    e=db.get(Event,event_id)
    if not e:raise HTTPException(404,'Event not found')
    if e.organizer_id!=user.id or not user.is_approved:raise HTTPException(403,'Approved organizer can manage only own events')
    if data.start_time <= datetime.now(timezone.utc).replace(tzinfo=None) if data.start_time.tzinfo is None else data.start_time <= datetime.now(timezone.utc):
        raise HTTPException(422, 'Show must be in the future')
    screen=db.get(Screen,data.screen_id)
    if not screen:raise HTTPException(404,'Screen not found')
    end=data.start_time+timedelta(minutes=e.duration_minutes); close=data.start_time-timedelta(minutes=30)
    conflicts=db.query(Show).filter(Show.screen_id==screen.id,Show.status=='Scheduled',Show.start_time<end+timedelta(minutes=15),Show.end_time>data.start_time-timedelta(minutes=15)).first()
    if conflicts:raise HTTPException(409,'Shows on the same screen require a 15-minute cleaning gap')
    categories={s.category for s in screen.seats if s.is_active}
    if not categories or not categories.issubset(data.prices.keys()):raise HTTPException(422,'A price is required for every active seat category on the screen')
    if any(v<=0 for v in data.prices.values()):raise HTTPException(422,'Prices must be greater than zero')
    s=Show(event_id=event_id,screen_id=screen.id,show_date=data.start_time.replace(hour=0,minute=0,second=0,microsecond=0),start_time=data.start_time,end_time=end,booking_closes_at=close)
    db.add(s);db.flush()
    for cat,price in data.prices.items():db.add(SeatCategoryPrice(show_id=s.id,category=cat,price=price))
    db.commit();db.refresh(s);clear_event_cache();return {'id':s.id,'event_id':s.event_id,'screen_id':s.screen_id,'start_time':s.start_time,'end_time':s.end_time,'booking_closes_at':s.booking_closes_at,'prices':data.prices}
@router.get('/events/{event_id}/shows')
def event_shows(event_id:int,skip:int=0,limit:int=20,db:Session=Depends(get_db)):
    if not db.get(Event,event_id):raise HTTPException(404,'Event not found')
    return db.query(Show).filter_by(event_id=event_id).order_by(Show.start_time).offset(skip).limit(min(limit,100)).all()
@router.put('/shows/{show_id}')
def update_show(show_id:int,data:ShowIn,db:Session=Depends(get_db),user=Depends(require_roles('Organizer'))):
    s=db.get(Show,show_id)
    if not s:raise HTTPException(404,'Show not found')
    if s.event.organizer_id!=user.id:raise HTTPException(403,'Not your show')
    if db.query(Booking).filter(Booking.show_id==show_id,Booking.status=='Confirmed').first():raise HTTPException(409,'Prices/show cannot be changed after confirmed bookings')
    if data.start_time<=datetime.utcnow():raise HTTPException(422,'Show must be in future')
    s.start_time=data.start_time;s.show_date=data.start_time.replace(hour=0,minute=0,second=0,microsecond=0);s.end_time=data.start_time+timedelta(minutes=s.event.duration_minutes);s.booking_closes_at=data.start_time-timedelta(minutes=30)
    s.prices.clear()
    for cat,price in data.prices.items():
        if price<=0:raise HTTPException(422,'Prices must be positive')
        s.prices.append(SeatCategoryPrice(category=cat,price=price))
    db.commit();clear_event_cache();return {'message':'Show updated','show_id':show_id}
@router.put('/shows/{show_id}/cancel')
def cancel_show(show_id:int,db:Session=Depends(get_db),user=Depends(require_roles('Organizer'))):
    s=db.get(Show,show_id)
    if not s:raise HTTPException(404,'Show not found')
    if s.event.organizer_id!=user.id:raise HTTPException(403,'Not your show')
    s.status='Cancelled';db.commit();clear_event_cache();return {'message':'Show cancelled. Refund processing for confirmed bookings must be run via the cancellation workflow.'}
