import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.database import SessionLocal
from app.models.models import Booking,Show,Event,Ticket
logger=logging.getLogger(__name__)
scheduler=AsyncIOScheduler()
def expire_bookings():
    db=SessionLocal()
    try:
        for b in db.query(Booking).filter(Booking.status=='Pending Payment',Booking.expires_at<datetime.utcnow()).all():b.status='Expired'
        db.commit()
    except Exception:db.rollback();logger.exception('Expired booking job failed')
    finally:db.close()
def complete_shows():
    db=SessionLocal()
    try:
        for s in db.query(Show).filter(Show.status=='Scheduled',Show.end_time<datetime.utcnow()).all():s.status='Completed'
        db.commit()
    except Exception:db.rollback();logger.exception('Show completion job failed')
    finally:db.close()
def complete_events():
    db=SessionLocal()
    try:
        for e in db.query(Event).filter(Event.status=='Published').all():
            if e.shows and all(s.status in ('Completed','Cancelled') for s in e.shows):e.status='Completed'
        db.commit()
    except Exception:db.rollback();logger.exception('Event completion job failed')
    finally:db.close()
def start_scheduler():
    if scheduler.running:return
    scheduler.add_job(expire_bookings,'interval',minutes=1,id='expire_bookings',replace_existing=True)
    scheduler.add_job(complete_shows,'interval',minutes=15,id='complete_shows',replace_existing=True)
    scheduler.add_job(complete_events,'interval',hours=24,id='complete_events',replace_existing=True)
    scheduler.start()
def stop_scheduler():
    if scheduler.running:scheduler.shutdown(wait=False)
