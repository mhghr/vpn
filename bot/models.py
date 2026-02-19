"""
SQLAlchemy database models.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    """
    User model - stores Telegram user information.
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=True)
    is_member = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    wallet_balance = Column(Integer, default=0)
    joined_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, name={self.first_name})>"


class Panel(Base):
    """
    Panel model - stores panel information.
    """
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
    status = Column(String, default="pending")  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Panel(name={self.name}, ip={self.ip_address})>"


class Plan(Base):
    """
    Plan model - stores VPN service plans.
    """
    __tablename__ = "plans"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    duration_days = Column(Integer, nullable=False)
    traffic_gb = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Plan(name={self.name}, days={self.duration_days}, price={self.price})>"


class PaymentReceipt(Base):
    """
    PaymentReceipt model - stores payment receipt information.
    """
    __tablename__ = "payment_receipts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_telegram_id = Column(String, index=True, nullable=False)
    plan_id = Column(Integer, nullable=True)
    plan_name = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)
    payment_method = Column(String, nullable=False)  # card_to_card, wallet
    receipt_file_id = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(String, nullable=True)
    
    def __repr__(self):
        return f"<PaymentReceipt(user={self.user_telegram_id}, plan={self.plan_name}, status={self.status})>"


class WireGuardConfig(Base):
    """
    WireGuardConfig model - stores WireGuard VPN configuration for users.
    """
    __tablename__ = "wireguard_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_telegram_id = Column(String, index=True, nullable=False)
    plan_name = Column(String, nullable=True)
    plan_id = Column(Integer, nullable=True)
    private_key = Column(Text, nullable=False)
    public_key = Column(Text, nullable=False)
    client_ip = Column(String, nullable=False)  # e.g., 192.168.30.10
    preshared_key = Column(Text, nullable=True)  # Optional PSK
    wg_server_public_key = Column(String, nullable=False)
    wg_server_endpoint = Column(String, nullable=False)
    wg_server_port = Column(Integer, nullable=False)
    wg_client_dns = Column(String, default="8.8.8.8,1.0.0.1")
    allowed_ips = Column(String, default="0.0.0.0/0, ::/0")
    status = Column(String, default="active")  # active, expired, revoked
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    cumulative_rx_bytes = Column(BigInteger, default=0)
    cumulative_tx_bytes = Column(BigInteger, default=0)
    last_rx_counter = Column(BigInteger, default=0)
    last_tx_counter = Column(BigInteger, default=0)
    counter_reset_flag = Column(Boolean, default=False)
    low_traffic_alert_sent = Column(Boolean, default=False)
    expiry_alert_sent = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<WireGuardConfig(user={self.user_telegram_id}, ip={self.client_ip})>"
    
    @property
    def is_active(self) -> bool:
        """Check if config is still valid."""
        if self.status != "active":
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True
    
    def get_config_text(self) -> str:
        """
        Generate WireGuard config in standard format.
        """
        # Determine mask based on IP version
        if ":" in self.client_ip:
            mask = 128
        else:
            mask = 32
        
        config = f"""[Interface]
PrivateKey = {self.private_key}
Address = {self.client_ip}/{mask}
DNS = {self.wg_client_dns}

[Peer]
PublicKey = {self.wg_server_public_key}
AllowedIPs = {self.allowed_ips}
Endpoint = {self.wg_server_endpoint}:{self.wg_server_port}
PersistentKeepalive = 25"""
        
        if self.preshared_key:
            config += f"\nPresharedKey = {self.preshared_key}"
        
        return config


class GiftCode(Base):
    """Gift/discount code model."""
    __tablename__ = "gift_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    discount_percent = Column(Integer, nullable=True)
    discount_amount = Column(Integer, nullable=True)  # Toman
    max_uses = Column(Integer, default=1)
    used_count = Column(Integer, default=0)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
