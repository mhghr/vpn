"""
Database connection and session management.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy import text
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
    from models import User, Panel, Plan, PaymentReceipt, WireGuardConfig, GiftCode
    Base.metadata.create_all(bind=engine)

    # Lightweight schema migration for usage counters (safe for repeated runs)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE wireguard_configs ADD COLUMN IF NOT EXISTS cumulative_rx_bytes BIGINT DEFAULT 0"))
        conn.execute(text("ALTER TABLE wireguard_configs ADD COLUMN IF NOT EXISTS cumulative_tx_bytes BIGINT DEFAULT 0"))
        conn.execute(text("ALTER TABLE wireguard_configs ADD COLUMN IF NOT EXISTS last_rx_counter BIGINT DEFAULT 0"))
        conn.execute(text("ALTER TABLE wireguard_configs ADD COLUMN IF NOT EXISTS last_tx_counter BIGINT DEFAULT 0"))
        conn.execute(text("ALTER TABLE wireguard_configs ADD COLUMN IF NOT EXISTS counter_reset_flag BOOLEAN DEFAULT FALSE"))
        conn.execute(text("ALTER TABLE wireguard_configs ADD COLUMN IF NOT EXISTS low_traffic_alert_sent BOOLEAN DEFAULT FALSE"))
        conn.execute(text("ALTER TABLE wireguard_configs ADD COLUMN IF NOT EXISTS expiry_alert_sent BOOLEAN DEFAULT FALSE"))
        conn.execute(text("ALTER TABLE wireguard_configs ADD COLUMN IF NOT EXISTS threshold_alert_sent BOOLEAN DEFAULT FALSE"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS has_used_test_account BOOLEAN DEFAULT FALSE"))
        conn.execute(text("ALTER TABLE plans ALTER COLUMN traffic_gb TYPE DOUBLE PRECISION USING traffic_gb::double precision"))
