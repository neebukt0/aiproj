import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_SECRET = 'change-me-secret-key-0123456789abcdef'


class Settings:
    MONGODB_URL = os.environ.get('MONGODB_URL', 'mongodb://localhost:27017')
    MONGODB_DB = os.environ.get('MONGODB_DB', 'booking')
    SECRET_KEY = os.environ.get('SECRET_KEY', DEFAULT_SECRET)
    JWT_ACCESS_LIFETIME_MINUTES = int(os.environ.get('JWT_ACCESS_LIFETIME_MINUTES', 15))
    JWT_REFRESH_LIFETIME_DAYS = int(os.environ.get('JWT_REFRESH_LIFETIME_DAYS', 7))
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.environ.get(
            'CORS_ORIGINS',
            'http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000',
        ).split(',')
        if origin.strip()
    ]


settings = Settings()
