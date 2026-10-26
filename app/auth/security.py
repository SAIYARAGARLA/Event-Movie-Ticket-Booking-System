from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.models import User

pwd_context=CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_scheme=OAuth2PasswordBearer(tokenUrl='/auth/login')
def hash_password(password:str)->str: return pwd_context.hash(password)
def verify_password(password:str, hashed:str)->bool: return pwd_context.verify(password, hashed)
def create_access_token(user:User)->str:
    now=datetime.now(timezone.utc)
    return jwt.encode({'sub':str(user.id),'role':user.role,'iat':now,'exp':now+timedelta(minutes=settings.access_token_expire_minutes)},settings.jwt_secret_key,algorithm=settings.jwt_algorithm)
def get_current_user(token:str=Depends(oauth2_scheme), db:Session=Depends(get_db))->User:
    error=HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail='Invalid or expired access token',headers={'WWW-Authenticate':'Bearer'})
    try: payload=jwt.decode(token,settings.jwt_secret_key,algorithms=[settings.jwt_algorithm]); user_id=int(payload.get('sub','0'))
    except (JWTError,ValueError): raise error
    user=db.get(User,user_id)
    if not user or not user.is_active: raise error
    return user
def require_roles(*roles):
    def checker(user:User=Depends(get_current_user)):
        if user.role not in roles: raise HTTPException(403,'Insufficient role permissions')
        return user
    return checker
