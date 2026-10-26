import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.routers import auth,admin,venues,events,bookings,reports
from app.websockets.seats import router as websocket_router
from app.jobs.scheduler import start_scheduler,stop_scheduler

logging.basicConfig(level=logging.INFO)
@asynccontextmanager
async def lifespan(app:FastAPI):
    start_scheduler()
    yield
    stop_scheduler()
app=FastAPI(title=settings.app_name,version='1.0.0',description='Event and movie ticket booking API with JWT, Redis seat locks, mock payments and QR tickets.',lifespan=lifespan)
app.include_router(auth.router);app.include_router(admin.router);app.include_router(venues.router);app.include_router(events.router);app.include_router(bookings.router);app.include_router(reports.router);app.include_router(websocket_router)
app.mount('/static',StaticFiles(directory='static'),name='static')
@app.get('/',tags=['Health'])
def root():return {'app':settings.app_name,'status':'running','docs':'/docs'}
@app.get('/health',tags=['Health'])
def health():return {'status':'ok'}
@app.get('/seat-map-test',include_in_schema=False)
def seat_map_test():return FileResponse('static/seat_map_test.html')
