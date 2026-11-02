import os


class Settings:
    MONGODB_URL = os.environ.get('MONGODB_URL', 'mongodb://localhost:27017')
    MONGODB_DB = os.environ.get('MONGODB_DB', 'booking')
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-secret-key-0123456789abcdef')
    JWT_ACCESS_LIFETIME_MINUTES = int(os.environ.get('JWT_ACCESS_LIFETIME_MINUTES', 15))
    JWT_REFRESH_LIFETIME_DAYS = int(os.environ.get('JWT_REFRESH_LIFETIME_DAYS', 7))


settings = Settings()
