"""
SQLAlchemy database models.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, Float, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=True)
    is_member = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    is_blocked = Column(Boolean, default=False)
    is_organization_customer = Column(Boolean, default=False)
    org_price_per_gb = Column(Integer, default=3000)
    org_last_settlement_at = Column(DateTime, nullable=True)
    wallet_balance = Column(Integer, default=0)
    has_used_test_account = Column(Boolean, default=False)
    representative_id = Column(Integer, nullable=True)
    joined_at = Column(DateTime, default=datetime.utcnow)


class Panel(Base):
    __tablename__ = "panels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    ip_address = Column(String, nullable=False)
    local_ip = Column(String, nullable=True)
    location = Column(String, nullable=True)
    port = Column(Integer, default=2053)
    path = Column(String, default="/")
    api_username = Column(String, nullable=True)
    api_password = Column(String, nullable=True)
    xui_version = Column(String, nullable=True)
    system_info = Column(Text, nullable=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)


class ServiceType(Base):
    __tablename__ = "service_types"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False, index=True)  # e.g. wireguard, v2ray
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    service_type_id = Column(Integer, ForeignKey("service_types.id"), nullable=False, index=True)
    host = Column(String, nullable=False)
    api_port = Column(Integer, default=8728)
    username = Column(String, nullable=True)
    password = Column(String, nullable=True)
    wg_interface = Column(String, nullable=True)
    wg_server_public_key = Column(String, nullable=True)
    wg_server_endpoint = Column(String, nullable=True)
    wg_server_port = Column(Integer, nullable=True)
    wg_client_network_base = Column(String, nullable=True)
    wg_client_dns = Column(String, nullable=True)
    wg_ip_range_start = Column(Integer, nullable=True)
    wg_ip_range_end = Column(Integer, nullable=True)
    wg_is_ip_range = Column(Boolean, default=False)
    capacity = Column(Integer, default=100)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    service_type = relationship("ServiceType")


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    service_type_id = Column(Integer, ForeignKey("service_types.id"), nullable=True, index=True)
    duration_days = Column(Integer, nullable=False)
    traffic_gb = Column(Float, nullable=False)
    price = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    service_type = relationship("ServiceType")


class PlanServerMap(Base):
    __tablename__ = "plan_server_map"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PaymentReceipt(Base):
    __tablename__ = "payment_receipts"

    id = Column(Integer, primary_key=True, index=True)
    user_telegram_id = Column(String, index=True, nullable=False)
    plan_id = Column(Integer, nullable=True)
    plan_name = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)
    payment_method = Column(String, nullable=False)
    receipt_file_id = Column(String, nullable=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(String, nullable=True)
    server_id = Column(Integer, nullable=True)  # No FK until servers table exists
    renew_config_id = Column(Integer, nullable=True)
    representative_id = Column(Integer, nullable=True)


class WireGuardConfig(Base):
    __tablename__ = "wireguard_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_telegram_id = Column(String, index=True, nullable=False)
    plan_name = Column(String, nullable=True)
    plan_id = Column(Integer, nullable=True)
    server_id = Column(Integer, nullable=True)  # No FK until servers table exists
    representative_id = Column(Integer, nullable=True)
    private_key = Column(Text, nullable=False)
    public_key = Column(Text, nullable=False)
    client_ip = Column(String, nullable=False)
    preshared_key = Column(Text, nullable=True)
    wg_server_public_key = Column(String, nullable=False)
    wg_server_endpoint = Column(String, nullable=False)
    wg_server_port = Column(Integer, nullable=False)
    wg_client_dns = Column(String, default="8.8.8.8,1.0.0.1")
    allowed_ips = Column(String, default="0.0.0.0/0, ::/0")
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    cumulative_rx_bytes = Column(BigInteger, default=0)
    cumulative_tx_bytes = Column(BigInteger, default=0)
    last_rx_counter = Column(BigInteger, default=0)
    last_tx_counter = Column(BigInteger, default=0)
    counter_reset_flag = Column(Boolean, default=False)
    low_traffic_alert_sent = Column(Boolean, default=False)
    expiry_alert_sent = Column(Boolean, default=False)
    threshold_alert_sent = Column(Boolean, default=False)


class GiftCode(Base):
    __tablename__ = "gift_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    discount_percent = Column(Integer, nullable=True)
    discount_amount = Column(Integer, nullable=True)
    max_uses = Column(Integer, default=1)
    used_count = Column(Integer, default=0)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ServiceTutorial(Base):
    """Tutorial for each service type"""
    __tablename__ = "service_tutorials"

    id = Column(Integer, primary_key=True, index=True)
    service_type_id = Column(Integer, ForeignKey("service_types.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    media_type = Column(String, nullable=True)  # photo, video
    media_file_id = Column(String, nullable=True)  # Telegram file_id
    media_url = Column(String, nullable=True)  # Alternative URL
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    service_type = relationship("ServiceType")


class Representative(Base):
    __tablename__ = "representatives"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    bot_token = Column(String, nullable=False)
    admin_telegram_id = Column(String, nullable=False)
    channel_id = Column(String, nullable=False)
    docker_container_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    total_configs = Column(Integer, default=0)
    total_traffic_bytes = Column(BigInteger, default=0)
    total_sales_amount = Column(BigInteger, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
