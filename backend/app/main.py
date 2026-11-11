import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from app import auth, bookings, logs, reports, resources, users
from app.config import DEFAULT_SECRET, settings
from app.database import ensure_indexes

logger = logging.getLogger('booking')


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.SECRET_KEY == DEFAULT_SECRET:
        logger.warning('SECRET_KEY uses the default value; set a real secret in .env')
    try:
        await ensure_indexes()
    except Exception as exc:  # noqa: BLE001 - приложение должно подняться даже без индексов
        logger.warning('Could not create MongoDB indexes: %s', exc)
    yield


app = FastAPI(title='Booking API', version='0.2.0', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r'https?://(localhost|127\.0\.0\.1)(:\d+)?$',
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.exception_handler(PyMongoError)
async def mongo_error_handler(request: Request, exc: PyMongoError):
    logger.error('MongoDB error on %s %s: %s', request.method, request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content={'detail': 'Database temporarily unavailable'},
    )


app.include_router(auth.router)
app.include_router(resources.router)
app.include_router(bookings.router)
app.include_router(reports.router)
app.include_router(users.router)
app.include_router(logs.router)


@app.get('/health')
def health():
    return {'status': 'ok'}
