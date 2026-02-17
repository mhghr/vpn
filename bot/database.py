"""
Database connection and session management.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:123@localhost:5432/myvpn")

# Create engine
engine = create_engine(DATABASE_URL, echo=False)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()


def get_db():
    """
    Dependency for getting database session.
    Use this in your route handlers.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database - create all tables.
    Call this on application startup.
    """
    from models import User, Panel, Plan, PaymentReceipt, WireGuardConfig
    Base.metadata.create_all(bind=engine)
