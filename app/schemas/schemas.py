from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from typing import Literal

class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Literal['Customer','Organizer'] = 'Customer'
    phone: str | None = None
    @field_validator('phone')
    @classmethod
    def phone_digits(cls, v):
        if v is not None and (not v.isdigit() or len(v) != 10): raise ValueError('Phone must contain exactly 10 digits')
        return v
class LoginIn(BaseModel):
    email: EmailStr
    password: str
class UserOut(BaseModel):
    id:int; name:str; email:str; role:str; is_active:bool; is_approved:bool
    model_config=ConfigDict(from_attributes=True)
class VenueIn(BaseModel): name:str; city:str; address:str; is_active:bool=True
class ScreenIn(BaseModel): name:str; total_seats:int=0
class BulkSeatsIn(BaseModel): start_row:str='A'; end_row:str='E'; seats_per_row:int=12; category:Literal['Silver','Gold','Recliner']='Silver'
class EventIn(BaseModel):
    title:str; category:Literal['Movie','Concert','Comedy','Sports','Workshop']; language:str; description:str=''; duration_minutes:int=Field(ge=30,le=300); age_rating:Literal['U','UA','A']='U'; status:Literal['Draft','Published']='Draft'
class ShowIn(BaseModel): screen_id:int; start_time:datetime; prices:dict[str,float]
class LockSeatsIn(BaseModel): seat_ids:list[int]=Field(min_length=1,max_length=10)
class BookingIn(BaseModel): seat_ids:list[int]=Field(min_length=1,max_length=10)
class PayIn(BaseModel): payment_method:Literal['UPI','Card','Net Banking']; simulate_status:Literal['Success','Failed']
class ScanIn(BaseModel): qr_token:str
class WaitlistIn(BaseModel): seat_count:int=Field(ge=1,le=10); preferred_category:Literal['Silver','Gold','Recliner']
