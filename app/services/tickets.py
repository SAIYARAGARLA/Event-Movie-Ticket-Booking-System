import hashlib,hmac,io,os
import qrcode
from reportlab.pdfgen import canvas
from app.config import settings

def sign_booking(booking_number:str)->str:
    sig=hmac.new(settings.ticket_hmac_secret.encode(),booking_number.encode(),hashlib.sha256).hexdigest()
    return f'{booking_number}.{sig}'
def verify_ticket(token:str)->str|None:
    try: number,sig=token.rsplit('.',1)
    except ValueError: return None
    expected=hmac.new(settings.ticket_hmac_secret.encode(),number.encode(),hashlib.sha256).hexdigest()
    return number if hmac.compare_digest(sig,expected) else None

def make_ticket_pdf(booking, event_title:str, venue_name:str, screen_name:str, show_time:str, seat_names:list[str])->bytes:
    os.makedirs('tickets',exist_ok=True); buff=io.BytesIO(); c=canvas.Canvas(buff,pagesize=(420,600))
    c.setFont('Helvetica-Bold',18); c.drawString(30,555,'Event & Movie Ticket')
    c.setFont('Helvetica',11)
    lines=[f'Event: {event_title}',f'Venue: {venue_name}',f'Screen: {screen_name}',f'Show: {show_time}',f'Booking: {booking.booking_number}',f'Seats: {", ".join(seat_names)}',f'Seats count: {booking.seat_count}',f'Amount paid: INR {booking.grand_total}']
    y=515
    for line in lines: c.drawString(30,y,line[:75]); y-=24
    qr=qrcode.make(sign_booking(booking.booking_number)); qbuf=io.BytesIO(); qr.save(qbuf,format='PNG'); from reportlab.lib.utils import ImageReader
    c.drawImage(ImageReader(io.BytesIO(qbuf.getvalue())),135,45,width=150,height=150); c.save(); return buff.getvalue()
