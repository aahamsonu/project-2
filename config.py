import os
from datetime import timedelta

class Config:
    SECRET_KEY = 'cutm-complaint-portal-secret-key-2026'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///complaint_portal.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload settings
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    
    # Auto escalation time (in hours)
    ESCALATION_TIME = 48
    
    # Notification settings
    NOTIFICATION_CHECK_INTERVAL = 30  # seconds