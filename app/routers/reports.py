from datetime import datetime,timedelta
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.models import Booking,Payment,Refund,Event,Show,BookedSeat,TicketEntry,Ticket
from app.auth.security import require_roles
router=APIRouter(prefix='/reports',tags=['Reports & Dashboard'])
@router.get('/admin-dashboard')
def admin_dashboard(db:Session=Depends(get_db),user=Depends(require_roles('Admin'))):
    today=datetime.utcnow().date(); bookings=db.query(Booking).filter(func.date(Booking.created_at)==today).count(); revenue=db.query(func.coalesce(func.sum(Payment.amount),0)).filter(Payment.status=='Success',func.date(Payment.paid_at)==today).scalar(); refunds=db.query(func.coalesce(func.sum(Refund.amount),0)).filter(func.date(Refund.refunded_at)==today).scalar(); active=db.query(Event).filter(Event.status=='Published').count(); scanned=db.query(TicketEntry).filter(func.date(TicketEntry.scanned_at)==today).count()
    return {'today_bookings':bookings,'today_revenue':float(revenue or 0),'today_refunds':float(refunds or 0),'active_events':active,'tickets_scanned_today':scanned}
@router.get('/event-sales')
def event_sales(from_date:datetime|None=None,to_date:datetime|None=None,db:Session=Depends(get_db),user=Depends(require_roles('Admin','Organizer'))):
    q=db.query(Booking).join(Booking.show).join(Show.event)
    if user.role=='Organizer':q=q.filter(Event.organizer_id==user.id)
    if from_date:q=q.filter(Booking.created_at>=from_date)
    if to_date:q=q.filter(Booking.created_at<=to_date)
    rows={}
    for b in q.all():
        e=b.show.event;key=(e.id,e.title,b.show.id,b.show.start_time.isoformat());r=rows.setdefault(key,{'event_id':e.id,'event_title':e.title,'show_id':b.show.id,'show_time':key[3],'tickets_sold':0,'revenue':0.0,'refunds':0.0})
        if b.status=='Confirmed':r['tickets_sold']+=b.seat_count;r['revenue']+=float(b.grand_total)
        r['refunds']+=sum(float(x.amount) for x in b.refunds)
    return list(rows.values())
@router.get('/occupancy')
def occupancy(db:Session=Depends(get_db),user=Depends(require_roles('Admin','Organizer'))):
    out=[]
    for s in db.query(Show).all():
        if user.role=='Organizer' and s.event.organizer_id!=user.id:continue
        total=sum(1 for x in s.screen.seats if x.is_active);booked=db.query(BookedSeat).filter_by(show_id=s.id,is_cancelled=False).count();cats={}
        for seat in s.screen.seats:
            if not seat.is_active:continue
            item=cats.setdefault(seat.category,{'total':0,'booked':0});item['total']+=1
            if db.query(BookedSeat).filter_by(show_id=s.id,seat_id=seat.id,is_cancelled=False).first():item['booked']+=1
        out.append({'show_id':s.id,'event':s.event.title,'booked_seats':booked,'total_seats':total,'occupancy_percent':round(100*booked/total,2) if total else 0,'categories':{k:{**v,'occupancy_percent':round(100*v['booked']/v['total'],2) if v['total'] else 0} for k,v in cats.items()}})
    return out
@router.get('/top-events')
def top_events(from_date:datetime|None=None,to_date:datetime|None=None,db:Session=Depends(get_db),user=Depends(require_roles('Admin'))):
    q=db.query(Event)
    result=[]
    for e in q.all():
        bookings=db.query(Booking).join(Show).filter(Show.event_id==e.id,Booking.status=='Confirmed')
        if from_date:bookings=bookings.filter(Booking.created_at>=from_date)
        if to_date:bookings=bookings.filter(Booking.created_at<=to_date)
        bs=bookings.all();result.append({'event_id':e.id,'title':e.title,'tickets_sold':sum(b.seat_count for b in bs),'revenue':sum(float(b.grand_total) for b in bs)})
    return sorted(result,key=lambda x:x['tickets_sold'],reverse=True)[:10]
@router.get('/refunds')
def refund_report(db:Session=Depends(get_db),user=Depends(require_roles('Admin'))):
    rows=db.query(Refund).all();out={}
    for r in rows:
        item=out.setdefault(r.reason,{'count':0,'amount':0.0});item['count']+=1;item['amount']+=float(r.amount)
    return out
