from datetime import datetime,timedelta
import secrets
from fastapi import APIRouter,Depends,HTTPException,BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Booking,BookedSeat,Show,Seat,SeatCategoryPrice,Payment,Ticket,Refund,User,TicketEntry,Waitlist
from app.schemas.schemas import LockSeatsIn,BookingIn,PayIn,ScanIn,WaitlistIn
from app.auth.security import get_current_user,require_roles
from app.services.seat_locks import lock_seat,unlock_seat,lock_owner,lock_expiry
from app.services.tickets import sign_booking,verify_ticket,make_ticket_pdf
from app.services.notifications import send_email
from app.redis_client import get_redis
router=APIRouter(tags=['Seats, Bookings, Payments & Tickets'])
def seat_name(seat):return f'{seat.row_label}{seat.seat_number}'
def notify_user(user,subject,body):send_email(user.email,subject,body)
@router.get('/shows/{show_id}/seats')
def show_seats(show_id:int,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    s=db.get(Show,show_id)
    if not s:raise HTTPException(404,'Show not found')
    prices={p.category:float(p.price) for p in s.prices}; booked={b.seat_id for b in db.query(BookedSeat).filter_by(show_id=show_id,is_cancelled=False).all()}; result=[]
    for seat in sorted(s.screen.seats,key=lambda x:(x.row_label,x.seat_number)):
        owner=lock_owner(show_id,seat.id) if seat.is_active and seat.id not in booked else None
        status='Unavailable' if not seat.is_active else 'Booked' if seat.id in booked else 'Locked' if owner else 'Available'
        if owner and owner==str(user.id):status='Yours'
        result.append({'seat_id':seat.id,'row':seat.row_label,'seat_number':seat.seat_number,'category':seat.category,'price':prices.get(seat.category),'status':status})
    return {'show_id':show_id,'seats':result}
@router.post('/shows/{show_id}/lock-seats')
def lock_seats(show_id:int,data:LockSeatsIn,user:User=Depends(require_roles('Customer')),db:Session=Depends(get_db)):
    try:
        r=get_redis();key=f'ratelimit:lock:{user.id}';n=r.incr(key)
        if n==1:r.expire(key,60)
        if n>5:raise HTTPException(429,detail=f'Too many seat-lock requests. Retry in {max(r.ttl(key),1)} seconds')
    except RuntimeError:raise HTTPException(503,'Redis is required for seat locking')
    show=db.get(Show,show_id)
    if not show:raise HTTPException(404,'Show not found')
    if show.status!='Scheduled' or datetime.utcnow()>=show.booking_closes_at:raise HTTPException(409,'Seat locking is closed for this show')
    if len(set(data.seat_ids))!=len(data.seat_ids):raise HTTPException(422,'Duplicate seat IDs are not allowed')
    existing=db.query(BookedSeat).filter(BookedSeat.show_id==show_id,BookedSeat.is_cancelled==False,BookedSeat.seat_id.in_(data.seat_ids)).all()
    invalid={x.seat_id for x in existing}; seats=db.query(Seat).filter(Seat.id.in_(data.seat_ids),Seat.screen_id==show.screen_id).all()
    if len(seats)!=len(data.seat_ids):raise HTTPException(404,'One or more seats do not belong to this show screen')
    invalid|={x.id for x in seats if not x.is_active}
    acquired=[]
    for seat in seats:
        if seat.id in invalid:continue
        if lock_owner(show_id,seat.id) not in (None,str(user.id)):invalid.add(seat.id);continue
        if lock_owner(show_id,seat.id)==str(user.id):continue
        if lock_seat(show_id,seat.id,user.id):acquired.append(seat.id)
        else:invalid.add(seat.id)
    if invalid:
        for sid in acquired:unlock_seat(show_id,sid,user.id)
        raise HTTPException(409,detail={'message':'Some seats are unavailable; all locks from this request were released','unavailable_seat_ids':sorted(invalid)})
    expiry=datetime.utcnow()+timedelta(minutes=10)
    return {'show_id':show_id,'locked_seat_ids':data.seat_ids,'expires_at':expiry.isoformat(),'expires_in_seconds':600}
@router.delete('/shows/{show_id}/lock-seats')
def release_seats(show_id:int,data:LockSeatsIn,user:User=Depends(require_roles('Customer'))):
    released=[]
    for sid in data.seat_ids:
        if unlock_seat(show_id,sid,user.id):released.append(sid)
    return {'released_seat_ids':released,'message':'Only your own locks are released'}
@router.post('/bookings',status_code=201)
def create_booking(show_id:int,data:BookingIn,db:Session=Depends(get_db),user:User=Depends(require_roles('Customer'))):
    # Keep the mentor-requested POST /bookings route; show_id is a query parameter.
    return create_booking_for_show(show_id, data, db, user)
@router.post('/bookings/create',status_code=201)
def create_booking_for_show(show_id:int,data:BookingIn,db:Session=Depends(get_db),user:User=Depends(require_roles('Customer'))):
    show=db.get(Show,show_id)
    if not show:raise HTTPException(404,'Show not found')
    if show.status!='Scheduled' or datetime.utcnow()>=show.booking_closes_at:raise HTTPException(409,'Booking is closed')
    if not 1<=len(data.seat_ids)<=10 or len(set(data.seat_ids))!=len(data.seat_ids):raise HTTPException(422,'Choose 1 to 10 unique seats')
    for sid in data.seat_ids:
        if lock_owner(show_id,sid)!=str(user.id):raise HTTPException(409,f'Seat {sid} is not locked by you')
    seats=db.query(Seat).filter(Seat.id.in_(data.seat_ids),Seat.screen_id==show.screen_id,Seat.is_active==True).all()
    if len(seats)!=len(data.seat_ids):raise HTTPException(409,'Some seats are unavailable')
    if db.query(BookedSeat).filter(BookedSeat.show_id==show_id,BookedSeat.is_cancelled==False,BookedSeat.seat_id.in_(data.seat_ids)).first():raise HTTPException(409,'Seat already booked')
    prices={p.category:float(p.price) for p in show.prices};total=round(sum(prices[s.category] for s in seats),2);fee=30*len(seats);gst=round((total+fee)*.18,2);grand=round(total+fee+gst,2)
    expires=min([lock_expiry(show_id,sid) for sid in data.seat_ids])
    b=Booking(booking_number=f'BKG-{datetime.utcnow():%Y%m%d}-{secrets.token_hex(3).upper()}',customer_id=user.id,show_id=show_id,seat_count=len(seats),ticket_total=total,convenience_fee=fee,gst_amount=gst,grand_total=grand,status='Pending Payment',expires_at=expires)
    db.add(b);db.flush()
    for seat in seats:db.add(BookedSeat(booking_id=b.id,show_id=show_id,seat_id=seat.id,price=prices[seat.category]))
    db.commit();db.refresh(b)
    return {'id':b.id,'booking_number':b.booking_number,'show_id':show_id,'seat_count':b.seat_count,'ticket_total':total,'convenience_fee':fee,'gst_amount':gst,'grand_total':grand,'status':b.status,'expires_at':b.expires_at}
@router.get('/bookings')
def list_bookings(skip:int=0,limit:int=20,status:str|None=None,show_id:int|None=None,from_date:datetime|None=None,to_date:datetime|None=None,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    q=db.query(Booking)
    if user.role=='Customer':q=q.filter(Booking.customer_id==user.id)
    elif user.role=='Organizer':q=q.join(Booking.show).join(Show.event).filter(Show.event.has(organizer_id=user.id))
    elif user.role not in ('Admin',):raise HTTPException(403,'Role cannot view bookings')
    if status:q=q.filter(Booking.status==status)
    if show_id:q=q.filter(Booking.show_id==show_id)
    if from_date:q=q.filter(Booking.created_at>=from_date)
    if to_date:q=q.filter(Booking.created_at<=to_date)
    return q.order_by(Booking.created_at.desc()).offset(skip).limit(min(limit,100)).all()
@router.get('/bookings/{booking_id}')
def booking_detail(booking_id:int,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    b=db.get(Booking,booking_id)
    if not b:raise HTTPException(404,'Booking not found')
    if user.role=='Customer' and b.customer_id!=user.id:raise HTTPException(403,'Not your booking')
    if user.role=='Organizer' and b.show.event.organizer_id!=user.id:raise HTTPException(403,'Not your event booking')
    return {'id':b.id,'booking_number':b.booking_number,'customer_id':b.customer_id,'show_id':b.show_id,'seats':[{'seat_id':x.seat_id,'seat':seat_name(x.seat),'price':float(x.price),'cancelled':x.is_cancelled} for x in b.seats],'seat_count':b.seat_count,'ticket_total':float(b.ticket_total),'convenience_fee':float(b.convenience_fee),'gst_amount':float(b.gst_amount),'grand_total':float(b.grand_total),'status':b.status,'expires_at':b.expires_at,'payments':b.payments}
@router.post('/bookings/{booking_id}/pay')
def pay(booking_id:int,data:PayIn,bg:BackgroundTasks,db:Session=Depends(get_db),user:User=Depends(require_roles('Customer'))):
    b=db.get(Booking,booking_id)
    if not b or b.customer_id!=user.id:raise HTTPException(404,'Booking not found')
    if b.status=='Confirmed':raise HTTPException(409,'Booking is already confirmed')
    if b.status in ('Expired','Cancelled') or datetime.utcnow()>b.expires_at:raise HTTPException(409,'Booking expired or cancelled')
    payment=Payment(booking_id=b.id,transaction_id=f'TXN-{datetime.utcnow():%Y%m%d}-{secrets.token_hex(3).upper()}',amount=b.grand_total,payment_method=data.payment_method,status=data.simulate_status,paid_at=datetime.utcnow() if data.simulate_status=='Success' else None)
    db.add(payment)
    if data.simulate_status=='Failed':
        db.commit();bg.add_task(notify_user,user,'Payment failed',f'Payment failed for booking {b.booking_number}. You may retry before the seat lock expires.')
        return {'payment_status':'Failed','booking_status':b.status,'transaction_id':payment.transaction_id,'message':'Payment failed; booking remains pending'}
    if datetime.utcnow()>b.expires_at or any(lock_owner(b.show_id,x.seat_id)!=str(user.id) for x in b.seats):
        payment.status='Refunded';b.status='Cancelled';db.add(Refund(booking_id=b.id,amount=b.grand_total,reason='Late Payment',status='Success'));db.commit()
        for x in b.seats:unlock_seat(b.show_id,x.seat_id,user.id)
        raise HTTPException(409,'Seat lock expired; mock payment was refunded and booking cancelled')
    b.status='Confirmed';b.confirmed_at=datetime.utcnow();db.flush()
    ticket=Ticket(booking_id=b.id,qr_token=sign_booking(b.booking_number));db.add(ticket)
    db.commit();db.refresh(b)
    for x in b.seats:unlock_seat(b.show_id,x.seat_id,user.id)
    bg.add_task(notify_user,user,'Booking confirmed',f'Your booking {b.booking_number} is confirmed. Download your ticket from /bookings/{b.id}/ticket.')
    return {'payment_status':'Success','booking_status':b.status,'transaction_id':payment.transaction_id,'amount':float(payment.amount),'ticket_endpoint':f'/bookings/{b.id}/ticket'}
@router.get('/bookings/{booking_id}/payments')
def payments(booking_id:int,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    b=db.get(Booking,booking_id)
    if not b:raise HTTPException(404,'Booking not found')
    if user.role=='Customer' and b.customer_id!=user.id:raise HTTPException(403,'Not your booking')
    return b.payments
@router.get('/bookings/{booking_id}/ticket')
def download_ticket(booking_id:int,db:Session=Depends(get_db),user:User=Depends(require_roles('Customer'))):
    from fastapi.responses import Response
    b=db.get(Booking,booking_id)
    if not b or b.customer_id!=user.id:raise HTTPException(404,'Booking not found')
    if b.status!='Confirmed':raise HTTPException(409,'Ticket is available only for confirmed bookings')
    t=db.query(Ticket).filter_by(booking_id=b.id).first()
    if not t:raise HTTPException(404,'Ticket record not found')
    show=b.show;seats=[seat_name(x.seat) for x in b.seats if not x.is_cancelled]
    pdf=make_ticket_pdf(b,show.event.title,show.screen.venue.name,show.screen.name,str(show.start_time),seats)
    return Response(content=pdf,media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename={b.booking_number}.pdf'})
@router.post('/tickets/scan')
def scan_ticket(data:ScanIn,db:Session=Depends(get_db),staff:User=Depends(require_roles('Staff'))):
    number=verify_ticket(data.qr_token)
    if not number:raise HTTPException(400,'Invalid QR signature')
    b=db.query(Booking).filter_by(booking_number=number).first()
    if not b or b.status!='Confirmed':raise HTTPException(409,'Ticket belongs to a cancelled, expired, or unconfirmed booking')
    if b.show.screen.venue_id!=staff.venue_id:raise HTTPException(403,'Staff can scan only tickets for their assigned venue')
    now=datetime.utcnow()
    if now<b.show.start_time-timedelta(hours=1) or now>b.show.end_time:raise HTTPException(409,'Ticket scanning is outside the allowed show window')
    t=db.query(Ticket).filter_by(booking_id=b.id).first()
    if t.scanned_at:raise HTTPException(409,f'Ticket already used at {t.scanned_at.isoformat()}')
    t.scanned_at=now;db.add(TicketEntry(ticket_id=t.id,staff_id=staff.id,scanned_at=now));db.commit()
    customer=db.get(User,b.customer_id)
    return {'message':'Entry accepted','customer_name':customer.name,'seats':[seat_name(x.seat) for x in b.seats if not x.is_cancelled],'seat_count':b.seat_count,'scanned_at':now}
@router.get('/shows/{show_id}/entries')
def show_entries(show_id:int,db:Session=Depends(get_db),user:User=Depends(require_roles('Admin','Organizer','Staff'))):
    s=db.get(Show,show_id)
    if not s:raise HTTPException(404,'Show not found')
    if user.role=='Staff' and user.venue_id!=s.screen.venue_id:raise HTTPException(403,'Not your venue')
    if user.role=='Organizer' and user.id!=s.event.organizer_id:raise HTTPException(403,'Not your event')
    total=db.query(Booking).filter_by(show_id=show_id,status='Confirmed').count();entered=db.query(TicketEntry).join(Ticket).join(Booking).filter(Booking.show_id==show_id).count()
    return {'show_id':show_id,'entered':entered,'confirmed_bookings':total,'remaining':max(total-entered,0)}
@router.put('/bookings/{booking_id}/cancel')
def cancel_booking(booking_id:int,bg:BackgroundTasks,db:Session=Depends(get_db),user:User=Depends(require_roles('Customer'))):
    b=db.get(Booking,booking_id)
    if not b or b.customer_id!=user.id:raise HTTPException(404,'Booking not found')
    if b.status!='Confirmed':raise HTTPException(409,'Only confirmed bookings can be cancelled')
    hours=(b.show.start_time-datetime.utcnow()).total_seconds()/3600
    if hours<2:raise HTTPException(409,'Cancellation is not allowed less than 2 hours before show')
    pct=1.0 if hours>24 else .5; amount=round(float(b.ticket_total)*pct,2)
    b.status='Cancelled';db.add(Refund(booking_id=b.id,amount=amount,reason='Customer Cancellation',status='Success'))
    for x in b.seats:x.is_cancelled=True
    for x in b.payments:
        if x.status=='Success':x.status='Refunded';break
    db.commit();bg.add_task(notify_user,user,'Booking cancelled',f'Booking {b.booking_number} cancelled. Refund amount: INR {amount:.2f}.')
    return {'booking_status':b.status,'refund_amount':amount,'policy':'100% ticket total if >24h; 50% between 2-24h; fees and GST excluded'}
@router.get('/bookings/{booking_id}/refunds')
def refunds(booking_id:int,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    b=db.get(Booking,booking_id)
    if not b:raise HTTPException(404,'Booking not found')
    if user.role=='Customer' and b.customer_id!=user.id:raise HTTPException(403,'Not your booking')
    return b.refunds
@router.post('/shows/{show_id}/waitlist',status_code=201)
def join_waitlist(show_id:int,data:WaitlistIn,db:Session=Depends(get_db),user:User=Depends(require_roles('Customer'))):
    s=db.get(Show,show_id)
    if not s:raise HTTPException(404,'Show not found')
    if db.query(Waitlist).filter_by(show_id=show_id,customer_id=user.id).first():raise HTTPException(409,'Already on this show waitlist')
    booked=db.query(BookedSeat).filter_by(show_id=show_id,is_cancelled=False).count();total=sum(1 for x in s.screen.seats if x.is_active)
    if booked<total:raise HTTPException(409,'Waitlist is only for sold-out shows')
    if db.query(Booking).filter_by(show_id=show_id,customer_id=user.id,status='Confirmed').first():raise HTTPException(409,'You already have a confirmed booking')
    w=Waitlist(show_id=show_id,customer_id=user.id,seat_count=data.seat_count,preferred_category=data.preferred_category);db.add(w);db.commit();db.refresh(w);return {'id':w.id,'show_id':show_id,'status':w.status}
@router.get('/shows/{show_id}/waitlist')
def list_waitlist(show_id:int,skip:int=0,limit:int=20,db:Session=Depends(get_db),user:User=Depends(require_roles('Admin','Organizer'))):
    s=db.get(Show,show_id)
    if not s:raise HTTPException(404,'Show not found')
    if user.role=='Organizer' and s.event.organizer_id!=user.id:raise HTTPException(403,'Not your event')
    return db.query(Waitlist).filter_by(show_id=show_id).order_by(Waitlist.created_at).offset(skip).limit(min(limit,100)).all()
@router.delete('/waitlist/{waitlist_id}')
def leave_waitlist(waitlist_id:int,db:Session=Depends(get_db),user:User=Depends(require_roles('Customer'))):
    w=db.get(Waitlist,waitlist_id)
    if not w or w.customer_id!=user.id:raise HTTPException(404,'Waitlist entry not found')
    db.delete(w);db.commit();return {'message':'Removed from waitlist'}
