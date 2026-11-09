from fastapi import FastAPI

from app import auth, bookings, logs, reports, resources, users

app = FastAPI(title='Booking API', version='0.1.0')

app.include_router(auth.router)
app.include_router(resources.router)
app.include_router(bookings.router)
app.include_router(reports.router)
app.include_router(users.router)
app.include_router(logs.router)


@app.get('/health')
def health():
    return {'status': 'ok'}
