"""
Database configuration for EvidenceFlow AI
Supports both SQLite (local) and PostgreSQL (production on Render)
"""
import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import hashlib

# Database URL configuration
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres"):
    # PostgreSQL for production (Render)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    # SQLite for local development
    engine = create_engine("sqlite:///users.db", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# User model
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    
    # Create default admin user if not exists
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.role == "admin").first()
        if not admin:
            admin_password = hashlib.sha256("admin123".encode()).hexdigest()
            admin_user = User(
                email="admin@evidenceflow.ai",
                name="Admin User",
                password_hash=admin_password,
                role="admin",
                is_verified=True
            )
            db.add(admin_user)
            db.commit()
            print("Default admin user created: admin@evidenceflow.ai / admin123")
        else:
            # Ensure existing admin is verified
            admin.is_verified = True
            db.commit()
            print("Ensured admin user is verified")
    finally:
        db.close()

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()