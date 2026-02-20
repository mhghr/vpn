"""
Database connection and session management.
"""
import os
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy import inspect
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:123@localhost:5432/myvpn")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _ensure_servers_columns_exist(conn):
    """Defensively add WireGuard-related columns for legacy servers tables."""
    required_columns = {
        "service_type_id": "INTEGER",
        "host": "VARCHAR",
        "api_port": "INTEGER DEFAULT 8728",
        "username": "VARCHAR",
        "password": "VARCHAR",
        "wg_interface": "VARCHAR",
        "wg_server_public_key": "VARCHAR",
        "wg_server_endpoint": "VARCHAR",
        "wg_server_port": "INTEGER",
        "wg_client_network_base": "VARCHAR",
        "wg_client_dns": "VARCHAR",
        "wg_ip_range_start": "INTEGER",
        "wg_ip_range_end": "INTEGER",
        "wg_is_ip_range": "BOOLEAN DEFAULT FALSE",
        "capacity": "INTEGER DEFAULT 100",
        "is_active": "BOOLEAN DEFAULT TRUE",
    }

    inspector = inspect(conn)
    existing_columns = {c["name"] for c in inspector.get_columns("servers")}
    for column_name, column_type in required_columns.items():
        if column_name not in existing_columns:
            conn.execute(text(f"ALTER TABLE servers ADD COLUMN {column_name} {column_type}"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from models import (
        User,
        Panel,
        ServiceType,
        Server,
        Plan,
        PlanServerMap,
        PaymentReceipt,
        WireGuardConfig,
        GiftCode,
    )

    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        # WireGuard config columns
        conn.execute(text("ALTER TABLE wireguard_configs ADD COLUMN IF NOT EXISTS cumulative_rx_bytes BIGINT DEFAULT 0"))
        conn.execute(text("ALTER TABLE wireguard_configs ADD COLUMN IF NOT EXISTS cumulative_tx_bytes BIGINT DEFAULT 0"))
        conn.execute(text("ALTER TABLE wireguard_configs ADD COLUMN IF NOT EXISTS last_rx_counter BIGINT DEFAULT 0"))
        conn.execute(text("ALTER TABLE wireguard_configs ADD COLUMN IF NOT EXISTS last_tx_counter BIGINT DEFAULT 0"))
        conn.execute(text("ALTER TABLE wireguard_configs ADD COLUMN IF NOT EXISTS counter_reset_flag BOOLEAN DEFAULT FALSE"))
        conn.execute(text("ALTER TABLE wireguard_configs ADD COLUMN IF NOT EXISTS low_traffic_alert_sent BOOLEAN DEFAULT FALSE"))
        conn.execute(text("ALTER TABLE wireguard_configs ADD COLUMN IF NOT EXISTS expiry_alert_sent BOOLEAN DEFAULT FALSE"))
        conn.execute(text("ALTER TABLE wireguard_configs ADD COLUMN IF NOT EXISTS threshold_alert_sent BOOLEAN DEFAULT FALSE"))
        
        # Add server_id column if it doesn't exist (for FK to servers table)
        conn.execute(text("ALTER TABLE wireguard_configs ADD COLUMN IF NOT EXISTS server_id INTEGER"))

        # User columns
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS has_used_test_account BOOLEAN DEFAULT FALSE"))

        # Plan columns
        try:
            conn.execute(text("ALTER TABLE plans ALTER COLUMN traffic_gb TYPE DOUBLE PRECISION USING traffic_gb::double precision"))
        except Exception:
            pass
        
        conn.execute(text("ALTER TABLE plans ADD COLUMN IF NOT EXISTS service_type_id INTEGER"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_plans_service_type_id ON plans(service_type_id)"))
        conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'fk_plans_service_type_id'
                ) THEN
                    ALTER TABLE plans
                    ADD CONSTRAINT fk_plans_service_type_id
                    FOREIGN KEY (service_type_id) REFERENCES service_types(id)
                    ON DELETE SET NULL;
                END IF;
            END;
            $$;
        """))

        # Payment receipt columns
        conn.execute(text("ALTER TABLE payment_receipts ADD COLUMN IF NOT EXISTS server_id INTEGER"))

        # Server columns (for legacy databases created before service type support)
        conn.execute(text("ALTER TABLE servers ADD COLUMN IF NOT EXISTS service_type_id INTEGER"))
        conn.execute(text("ALTER TABLE servers ADD COLUMN IF NOT EXISTS host VARCHAR"))
        conn.execute(text("ALTER TABLE servers ADD COLUMN IF NOT EXISTS api_port INTEGER DEFAULT 8728"))
        conn.execute(text("ALTER TABLE servers ADD COLUMN IF NOT EXISTS username VARCHAR"))
        conn.execute(text("ALTER TABLE servers ADD COLUMN IF NOT EXISTS password VARCHAR"))
        conn.execute(text("ALTER TABLE servers ADD COLUMN IF NOT EXISTS wg_interface VARCHAR"))
        conn.execute(text("ALTER TABLE servers ADD COLUMN IF NOT EXISTS wg_server_public_key VARCHAR"))
        conn.execute(text("ALTER TABLE servers ADD COLUMN IF NOT EXISTS wg_server_endpoint VARCHAR"))
        conn.execute(text("ALTER TABLE servers ADD COLUMN IF NOT EXISTS wg_server_port INTEGER"))
        conn.execute(text("ALTER TABLE servers ADD COLUMN IF NOT EXISTS wg_client_network_base VARCHAR"))
        conn.execute(text("ALTER TABLE servers ADD COLUMN IF NOT EXISTS wg_client_dns VARCHAR"))
        conn.execute(text("ALTER TABLE servers ADD COLUMN IF NOT EXISTS wg_ip_range_start INTEGER"))
        conn.execute(text("ALTER TABLE servers ADD COLUMN IF NOT EXISTS wg_ip_range_end INTEGER"))
        conn.execute(text("ALTER TABLE servers ADD COLUMN IF NOT EXISTS wg_is_ip_range BOOLEAN DEFAULT FALSE"))
        conn.execute(text("ALTER TABLE servers ADD COLUMN IF NOT EXISTS capacity INTEGER DEFAULT 100"))
        conn.execute(text("ALTER TABLE servers ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE"))

        # Some environments can still miss columns due partial/legacy migrations.
        # Re-check the actual table shape and patch missing fields explicitly.
        _ensure_servers_columns_exist(conn)

        conn.execute(text("""
            INSERT INTO service_types (code, name, is_active, created_at)
            VALUES
                ('wireguard', 'WireGuard', TRUE, NOW()),
                ('v2ray', 'V2Ray', TRUE, NOW())
            ON CONFLICT (code) DO NOTHING
        """))

        # Backfill missing service_type_id values to WireGuard for old server rows
        conn.execute(text("""
            UPDATE servers
            SET service_type_id = st.id
            FROM service_types st
            WHERE st.code = 'wireguard'
              AND servers.service_type_id IS NULL
        """))
        conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'fk_servers_service_type_id'
                ) THEN
                    ALTER TABLE servers
                    ADD CONSTRAINT fk_servers_service_type_id
                    FOREIGN KEY (service_type_id) REFERENCES service_types(id)
                    ON DELETE RESTRICT;
                END IF;
            END;
            $$;
        """))

        # Try to create indexes for tables that may not exist yet
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_servers_service_type_id ON servers(service_type_id)"))
        except Exception:
            pass
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_plan_server_map_plan_id ON plan_server_map(plan_id)"))
        except Exception:
            pass
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_plan_server_map_server_id ON plan_server_map(server_id)"))
        except Exception:
            pass

        # Keep service type defaults present in case of partial startup failures
        try:
            conn.execute(text("""
                INSERT INTO service_types (code, name, is_active, created_at)
                VALUES
                    ('wireguard', 'WireGuard', TRUE, NOW()),
                    ('v2ray', 'V2Ray', TRUE, NOW())
                ON CONFLICT (code) DO NOTHING
            """))
        except Exception:
            pass
