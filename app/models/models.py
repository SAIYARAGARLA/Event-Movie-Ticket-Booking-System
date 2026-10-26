from datetime import datetime
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, Time, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class User(TimestampMixin, Base):
    __tablename__='users'
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]=mapped_column(String(120), nullable=False)
    email: Mapped[str]=mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[str|None]=mapped_column(String(10), nullable=True)
    password_hash: Mapped[str]=mapped_column(String(255), nullable=False)
    role: Mapped[str]=mapped_column(String(20), default='Customer', nullable=False)
    is_active: Mapped[bool]=mapped_column(Boolean, default=True, nullable=False)
    is_approved: Mapped[bool]=mapped_column(Boolean, default=False, nullable=False)
    venue_id: Mapped[int|None]=mapped_column(ForeignKey('venues.id'), nullable=True)
    events: Mapped[list['Event']]=relationship(back_populates='organizer', foreign_keys='Event.organizer_id')

class Venue(TimestampMixin, Base):
    __tablename__='venues'
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]=mapped_column(String(150), nullable=False)
    city: Mapped[str]=mapped_column(String(100), index=True, nullable=False)
    address: Mapped[str]=mapped_column(String(255), nullable=False)
    is_active: Mapped[bool]=mapped_column(Boolean, default=True, nullable=False)
    screens: Mapped[list['Screen']]=relationship(back_populates='venue', cascade='all, delete-orphan')

class Screen(TimestampMixin, Base):
    __tablename__='screens'
    id: Mapped[int]=mapped_column(primary_key=True)
    venue_id: Mapped[int]=mapped_column(ForeignKey('venues.id'), nullable=False)
    name: Mapped[str]=mapped_column(String(100), nullable=False)
    total_seats: Mapped[int]=mapped_column(Integer, default=0, nullable=False)
    venue: Mapped[Venue]=relationship(back_populates='screens')
    seats: Mapped[list['Seat']]=relationship(back_populates='screen', cascade='all, delete-orphan')

class Seat(TimestampMixin, Base):
    __tablename__='seats'
    __table_args__=(UniqueConstraint('screen_id','row_label','seat_number',name='uq_screen_row_seat'),)
    id: Mapped[int]=mapped_column(primary_key=True)
    screen_id: Mapped[int]=mapped_column(ForeignKey('screens.id'), nullable=False, index=True)
    row_label: Mapped[str]=mapped_column(String(5), nullable=False)
    seat_number: Mapped[int]=mapped_column(Integer, nullable=False)
    category: Mapped[str]=mapped_column(String(20), default='Silver', nullable=False)
    is_active: Mapped[bool]=mapped_column(Boolean, default=True, nullable=False)
    screen: Mapped[Screen]=relationship(back_populates='seats')

class Event(TimestampMixin, Base):
    __tablename__='events'
    id: Mapped[int]=mapped_column(primary_key=True)
    organizer_id: Mapped[int]=mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    title: Mapped[str]=mapped_column(String(200), index=True, nullable=False)
    category: Mapped[str]=mapped_column(String(30), nullable=False)
    language: Mapped[str]=mapped_column(String(40), nullable=False)
    description: Mapped[str]=mapped_column(Text, default='')
    duration_minutes: Mapped[int]=mapped_column(Integer, nullable=False)
    age_rating: Mapped[str]=mapped_column(String(5), default='U', nullable=False)
    status: Mapped[str]=mapped_column(String(20), default='Draft', nullable=False)
    organizer: Mapped[User]=relationship(back_populates='events', foreign_keys=[organizer_id])
    shows: Mapped[list['Show']]=relationship(back_populates='event', cascade='all, delete-orphan')

class Show(TimestampMixin, Base):
    __tablename__='shows'
    id: Mapped[int]=mapped_column(primary_key=True)
    event_id: Mapped[int]=mapped_column(ForeignKey('events.id'), nullable=False, index=True)
    screen_id: Mapped[int]=mapped_column(ForeignKey('screens.id'), nullable=False, index=True)
    show_date: Mapped[datetime]=mapped_column(DateTime, nullable=False, index=True)
    start_time: Mapped[datetime]=mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime]=mapped_column(DateTime, nullable=False)
    booking_closes_at: Mapped[datetime]=mapped_column(DateTime, nullable=False)
    status: Mapped[str]=mapped_column(String(20), default='Scheduled', nullable=False)
    event: Mapped[Event]=relationship(back_populates='shows')
    screen: Mapped[Screen]=relationship()
    prices: Mapped[list['SeatCategoryPrice']]=relationship(back_populates='show', cascade='all, delete-orphan')

class SeatCategoryPrice(TimestampMixin, Base):
    __tablename__='seat_category_prices'
    __table_args__=(UniqueConstraint('show_id','category',name='uq_show_category_price'),)
    id: Mapped[int]=mapped_column(primary_key=True)
    show_id: Mapped[int]=mapped_column(ForeignKey('shows.id'), nullable=False)
    category: Mapped[str]=mapped_column(String(20), nullable=False)
    price: Mapped[float]=mapped_column(Numeric(10,2), nullable=False)
    show: Mapped[Show]=relationship(back_populates='prices')

class Booking(TimestampMixin, Base):
    __tablename__='bookings'
    id: Mapped[int]=mapped_column(primary_key=True)
    booking_number: Mapped[str]=mapped_column(String(32), unique=True, index=True, nullable=False)
    customer_id: Mapped[int]=mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    show_id: Mapped[int]=mapped_column(ForeignKey('shows.id'), nullable=False, index=True)
    seat_count: Mapped[int]=mapped_column(Integer, nullable=False)
    ticket_total: Mapped[float]=mapped_column(Numeric(10,2), nullable=False)
    convenience_fee: Mapped[float]=mapped_column(Numeric(10,2), nullable=False)
    gst_amount: Mapped[float]=mapped_column(Numeric(10,2), nullable=False)
    grand_total: Mapped[float]=mapped_column(Numeric(10,2), nullable=False)
    status: Mapped[str]=mapped_column(String(25), default='Pending Payment', nullable=False)
    expires_at: Mapped[datetime]=mapped_column(DateTime, nullable=False)
    confirmed_at: Mapped[datetime|None]=mapped_column(DateTime, nullable=True)
    show: Mapped[Show]=relationship()
    seats: Mapped[list['BookedSeat']]=relationship(back_populates='booking', cascade='all, delete-orphan')
    payments: Mapped[list['Payment']]=relationship(back_populates='booking', cascade='all, delete-orphan')
    refunds: Mapped[list['Refund']]=relationship(back_populates='booking', cascade='all, delete-orphan')

class BookedSeat(TimestampMixin, Base):
    __tablename__='booked_seats'
    __table_args__=(UniqueConstraint('show_id','seat_id',name='uq_show_booked_seat'),)
    id: Mapped[int]=mapped_column(primary_key=True)
    booking_id: Mapped[int]=mapped_column(ForeignKey('bookings.id'), nullable=False, index=True)
    show_id: Mapped[int]=mapped_column(ForeignKey('shows.id'), nullable=False, index=True)
    seat_id: Mapped[int]=mapped_column(ForeignKey('seats.id'), nullable=False)
    price: Mapped[float]=mapped_column(Numeric(10,2), nullable=False)
    is_cancelled: Mapped[bool]=mapped_column(Boolean, default=False, nullable=False)
    booking: Mapped[Booking]=relationship(back_populates='seats')
    seat: Mapped[Seat]=relationship()

class Payment(TimestampMixin, Base):
    __tablename__='payments'
    id: Mapped[int]=mapped_column(primary_key=True)
    booking_id: Mapped[int]=mapped_column(ForeignKey('bookings.id'), nullable=False, index=True)
    transaction_id: Mapped[str]=mapped_column(String(50), unique=True, nullable=False)
    amount: Mapped[float]=mapped_column(Numeric(10,2), nullable=False)
    payment_method: Mapped[str]=mapped_column(String(20), nullable=False)
    status: Mapped[str]=mapped_column(String(20), nullable=False)
    paid_at: Mapped[datetime|None]=mapped_column(DateTime, nullable=True)
    booking: Mapped[Booking]=relationship(back_populates='payments')

class Ticket(TimestampMixin, Base):
    __tablename__='tickets'
    id: Mapped[int]=mapped_column(primary_key=True)
    booking_id: Mapped[int]=mapped_column(ForeignKey('bookings.id'), unique=True, nullable=False)
    qr_token: Mapped[str]=mapped_column(String(255), unique=True, nullable=False)
    scanned_at: Mapped[datetime|None]=mapped_column(DateTime, nullable=True)

class Refund(TimestampMixin, Base):
    __tablename__='refunds'
    id: Mapped[int]=mapped_column(primary_key=True)
    booking_id: Mapped[int]=mapped_column(ForeignKey('bookings.id'), nullable=False, index=True)
    amount: Mapped[float]=mapped_column(Numeric(10,2), nullable=False)
    reason: Mapped[str]=mapped_column(String(40), nullable=False)
    status: Mapped[str]=mapped_column(String(20), default='Success', nullable=False)
    refunded_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    booking: Mapped[Booking]=relationship(back_populates='refunds')

class Waitlist(TimestampMixin, Base):
    __tablename__='waitlist'
    __table_args__=(UniqueConstraint('show_id','customer_id',name='uq_waitlist_customer_show'),)
    id: Mapped[int]=mapped_column(primary_key=True)
    show_id: Mapped[int]=mapped_column(ForeignKey('shows.id'), nullable=False, index=True)
    customer_id: Mapped[int]=mapped_column(ForeignKey('users.id'), nullable=False)
    seat_count: Mapped[int]=mapped_column(Integer, nullable=False)
    preferred_category: Mapped[str]=mapped_column(String(20), nullable=False)
    status: Mapped[str]=mapped_column(String(20), default='Waiting', nullable=False)
    customer: Mapped[User]=relationship()
    show: Mapped[Show]=relationship()

class Notification(TimestampMixin, Base):
    __tablename__='notifications'
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    message: Mapped[str]=mapped_column(String(500), nullable=False)
    is_read: Mapped[bool]=mapped_column(Boolean, default=False, nullable=False)

class TicketEntry(TimestampMixin, Base):
    __tablename__='ticket_entries'
    id: Mapped[int]=mapped_column(primary_key=True)
    ticket_id: Mapped[int]=mapped_column(ForeignKey('tickets.id'), nullable=False, unique=True)
    staff_id: Mapped[int]=mapped_column(ForeignKey('users.id'), nullable=False)
    scanned_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow, nullable=False)
