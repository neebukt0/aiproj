from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from app import auth, bookings, logs, reports, resources, users

app = FastAPI(title='Booking API', version='0.1.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost:5173',
        'http://127.0.0.1:5173',
        'http://localhost:3000',
        'http://172.28.123.193:5173',
    ],
    allow_origin_regex=r'https?://(localhost|127\.0\.0\.1)(:\d+)?$',
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.exception_handler(PyMongoError)
async def mongo_error_handler(request: Request, exc: PyMongoError):
    return JSONResponse(
        status_code=503,
        content={'detail': f'Database error: {str(exc)}'},
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
