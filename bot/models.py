"""
SQLAlchemy database models.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
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
    Panel model - stores XUI panel information.
    """
    __tablename__ = "panels"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    location = Column(String, nullable=False)
    ip_address = Column(String, nullable=False)
    port = Column(Integer, default=2053)
    path = Column(String, default="/")
    api_username = Column(String, nullable=False)
    api_password = Column(String, nullable=False)
    local_ip = Column(String, nullable=True)
    xui_version = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, approved, rejected
    system_info = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Panel(name={self.name}, location={self.location})>"


class Plan(Base):
    """
    Plan model - stores VPN service plans.
    """
    __tablename__ = "plans"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    duration_days = Column(Integer, nullable=False)  # Duration in days
    traffic_gb = Column(Integer, nullable=False)  # Traffic in GB
    price = Column(Integer, nullable=False)  # Price in Toman
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Plan(name={self.name}, {self.duration_days} days, {self.traffic_gb}GB)>"


class PaymentReceipt(Base):
    """
    PaymentReceipt model - stores payment receipt information.
    """
    __tablename__ = "payment_receipts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_telegram_id = Column(String, index=True, nullable=False)
    plan_id = Column(Integer, nullable=False)
    plan_name = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)
    payment_method = Column(String, nullable=False)  # card_to_card, wallet
    receipt_file_id = Column(String, nullable=True)  # Telegram file ID
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
Endpoint = {self.wg_server_endpoint}:{self.wg_server_port}
AllowedIPs = {self.allowed_ips}
"""
        if self.preshared_key:
            config += f"PresharedKey = {self.preshared_key}\n"
        
        config += "PersistentKeepalive = 25"
        return config
