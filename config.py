# config.py
import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret") # secret key to secure cookies and session data.
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_AUTH_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_AUTH_CLIENT_SECRET")