from datetime import datetime, timedelta
from app.redis_client import get_redis
LOCK_SECONDS=600
def key(show_id:int,seat_id:int)->str: return f'lock:show:{show_id}:seat:{seat_id}'
def lock_seat(show_id:int,seat_id:int,user_id:int)->bool:
    return bool(get_redis().set(key(show_id,seat_id),str(user_id),nx=True,ex=LOCK_SECONDS))
def unlock_seat(show_id:int,seat_id:int,user_id:int)->bool:
    r=get_redis(); k=key(show_id,seat_id)
    # Lua compare-and-delete prevents one customer deleting another customer's lock.
    script="if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end"
    return bool(r.eval(script,1,k,str(user_id)))
def lock_owner(show_id:int,seat_id:int): return get_redis().get(key(show_id,seat_id))
def lock_expiry(show_id:int,seat_id:int):
    ttl=get_redis().ttl(key(show_id,seat_id)); return datetime.utcnow()+timedelta(seconds=max(ttl,0))
