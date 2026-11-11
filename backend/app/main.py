from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import auth, bookings, logs, reports, resources, users

app = FastAPI(title='Booking API', version='0.1.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://172.28.123.193:5173'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
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
