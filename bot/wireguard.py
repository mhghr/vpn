"""
WireGuard account creation on MikroTik using MikroTik API
"""
import os
import sys
import logging
from io import BytesIO
import base64
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import dependencies
from database import SessionLocal
from models import WireGuardConfig, Plan

logger.info("=" * 60)
logger.info("Loading wireguard module...")
logger.info(f"Python executable: {sys.executable}")

# Import required dependencies
logger.info("Checking dependencies...")

try:
    import paramiko
    logger.info("✓ paramiko imported")
    PARAMIKO_AVAILABLE = True
except ImportError as e:
    logger.error(f"✗ paramiko NOT available: {e}")
    PARAMIKO_AVAILABLE = False

try:
    import qrcode
    logger.info("✓ qrcode imported")
    QRCODE_AVAILABLE = True
except ImportError as e:
    logger.error(f"✗ qrcode NOT available: {e}")
    QRCODE_AVAILABLE = False

try:
    from cryptography.hazmat.primitives.asymmetric import x25519
    from cryptography.hazmat.primitives import serialization
    logger.info("✓ cryptography imported")
    CRYPTO_AVAILABLE = True
except ImportError as e:
    logger.error(f"✗ cryptography NOT available: {e}")
    CRYPTO_AVAILABLE = False

try:
    from routeros_api import RouterOsApiPool
    logger.info("✓ routeros_api imported")
    ROUTEROS_API_AVAILABLE = True
except ImportError as e:
    logger.error(f"✗ routeros_api NOT available: {e}")
    logger.error("Please install: pip install routeros-api")
    ROUTEROS_API_AVAILABLE = False


def generate_wireguard_keypair():
    """
    Generate WireGuard private/public key pair using cryptography library
    No external CLI tools required
    """
    logger.info("[Step 1] Generating WireGuard keypair...")
    
    try:
        # Generate private key
        priv = x25519.X25519PrivateKey.generate()
        pub = priv.public_key()
        
        # Get raw bytes
        priv_b = priv.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        pub_b = pub.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        # Encode as base64
        private_key = base64.b64encode(priv_b).decode("ascii")
        public_key = base64.b64encode(pub_b).decode("ascii")
        
        logger.info(f"[Step 1] ✓ WireGuard keypair generated successfully")
        return public_key, private_key
    except Exception as e:
        logger.error(f"[Step 1] ✗ Failed to generate keypair: {e}")
        raise


def format_endpoint_host(host: str):
    """Format endpoint host for WireGuard config"""
    if ":" in host and not (host.startswith("[") and host.endswith("]")):
        return f"[{host}]"
    return host


def get_next_available_ip_from_db(network_base: str) -> str:
    """
    Get next available IP from the database
    Range: 10-250 (skipping 1-9 and 251+)
    """
    logger.info(f"[Step 2] Getting next available IP from database, network: {network_base}...")
    
    # Parse network base (e.g., "192.168.30.0" -> "192.168.30.")
    base_parts = network_base.rsplit('.', 1)
    prefix = base_parts[0] + "."
    
    db = SessionLocal()
    try:
        # Get all active configs from database
        configs = db.query(WireGuardConfig).filter(WireGuardConfig.status == "active").all()
        
        # Extract used IPs
        used_ips = set()
        for config in configs:
            if config.client_ip:
                ip = config.client_ip
                if ip.count('.') == 3:  # IPv4
                    try:
                        last_octet = int(ip.rsplit('.', 1)[-1])
                        used_ips.add(last_octet)
                    except (ValueError, IndexError):
                        pass
        
        logger.info(f"[Step 2] Used IPs in database: {sorted(used_ips)}")
        
        # Find next available IP in range 10-250
        for i in range(10, 251):
            if i not in used_ips:
                ip = f"{prefix}{i}"
                logger.info(f"[Step 2] ✓ Selected available IP: {ip}")
                return ip
        
        logger.warning("[Step 2] ✗ No available IP found in range 10-250")
        return None
        
    except Exception as e:
        logger.error(f"[Step 2] ✗ Error getting IP from database: {e}")
        raise
    finally:
        db.close()


def save_wireguard_config_to_db(
    user_telegram_id: str,
    plan_id: int = None,
    plan_name: str = None,
    private_key: str = None,
    public_key: str = None,
    client_ip: str = None,
    wg_server_public_key: str = None,
    wg_server_endpoint: str = None,
    wg_server_port: int = None,
    wg_client_dns: str = None,
    duration_days: int = None
) -> WireGuardConfig:
    """Save WireGuard config to database"""
    logger.info(f"[Step 7] Saving WireGuard config to database for user {user_telegram_id}...")
    
    db = SessionLocal()
    try:
        # Calculate expiration date
        expires_at = None
        if duration_days:
            expires_at = datetime.utcnow() + timedelta(days=duration_days)
        
        config = WireGuardConfig(
            user_telegram_id=str(user_telegram_id),
            plan_id=plan_id,
            plan_name=plan_name,
            private_key=private_key,
            public_key=public_key,
            client_ip=client_ip,
            wg_server_public_key=wg_server_public_key,
            wg_server_endpoint=wg_server_endpoint,
            wg_server_port=wg_server_port,
            wg_client_dns=wg_client_dns,
            status="active",
            expires_at=expires_at
        )
        
        db.add(config)
        db.commit()
        db.refresh(config)
        
        logger.info(f"[Step 7] ✓ WireGuard config saved with ID: {config.id}")
        return config
        
    except Exception as e:
        logger.error(f"[Step 7] ✗ Failed to save WireGuard config: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_wireguard_account(
    mikrotik_host: str,
    mikrotik_user: str,
    mikrotik_pass: str,
    mikrotik_port: int,
    wg_interface: str,
    wg_server_public_key: str,
    wg_server_endpoint: str,
    wg_server_port: int,
    wg_client_network_base: str = "192.168.30.0",
    wg_client_dns: str = "8.8.8.8,1.0.0.1",
    user_telegram_id: str = None,
    plan_id: int = None,
    plan_name: str = None,
    duration_days: int = None
) -> dict:
    """
    Create a WireGuard account on MikroTik using RouterOS API
    
    IP Range: 10-250 (skips 1-9 and 251+)
    
    Args:
        user_telegram_id: Telegram user ID
        plan_id: Plan ID from database
        plan_name: Plan name
        duration_days: Account duration in days
    
    Returns:
        dict with keys: success, private_key, public_key, client_ip, config, qr_code, error
    """
    logger.info("=" * 60)
    logger.info(f"Starting WireGuard account creation for user: {user_telegram_id}")
    logger.info(f"MikroTik: {mikrotik_host}:{mikrotik_port}")
    logger.info(f"Interface: {wg_interface}")
    logger.info(f"Network: {wg_client_network_base}")
    
    # Check if required dependencies are available
    if not ROUTEROS_API_AVAILABLE:
        error_msg = "routeros_api module not installed. Please run: pip install routeros-api"
        logger.error(f"✗ {error_msg}")
        return {"success": False, "error": error_msg}
    
    if not CRYPTO_AVAILABLE:
        error_msg = "cryptography module not installed"
        logger.error(f"✗ {error_msg}")
        return {"success": False, "error": error_msg}
    
    if not QRCODE_AVAILABLE:
        error_msg = "qrcode module not installed"
        logger.error(f"✗ {error_msg}")
        return {"success": False, "error": error_msg}
    
    pool = None
    try:
        # Determine if IPv6
        is_ipv6 = ":" in wg_client_network_base
        mask = 128 if is_ipv6 else 32
        
        # Step 1: Generate keys
        public_key, private_key = generate_wireguard_keypair()
        
        # Step 2: Get next available IP
        client_ip = get_next_available_ip_from_db(wg_client_network_base)
        
        if client_ip is None:
            error_msg = "No available IP in range 10-250"
            logger.error(f"✗ {error_msg}")
            return {"success": False, "error": error_msg}
        
        logger.info(f"[Step 3] Selected IP: {client_ip}")
        
        # Step 3: Connect to MikroTik
        logger.info(f"[Step 3] Connecting to MikroTik {mikrotik_host}:{mikrotik_port}...")
        try:
            pool = RouterOsApiPool(
                mikrotik_host,
                username=mikrotik_user,
                password=mikrotik_pass,
                port=mikrotik_port,
                plaintext_login=True
            )
            api = pool.get_api()
            logger.info("[Step 3] ✓ Connected to MikroTik API successfully")
        except Exception as e:
            error_msg = f"Failed to connect to MikroTik: {str(e)}"
            logger.error(f"[Step 3] ✗ {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Step 4: Check WireGuard interface
        logger.info(f"[Step 4] Checking WireGuard interface '{wg_interface}'...")
        try:
            wgifs = api.get_resource('/interface/wireguard').get()
            logger.info(f"[Step 4] Available interfaces: {[i.get('name') for i in wgifs]}")
            
            if not any(i.get('name') == wg_interface for i in wgifs):
                error_msg = f"WireGuard interface '{wg_interface}' not found on MikroTik!"
                logger.error(f"[Step 4] ✗ {error_msg}")
                return {"success": False, "error": error_msg}
            
            logger.info(f"[Step 4] ✓ WireGuard interface '{wg_interface}' found")
        except Exception as e:
            error_msg = f"Failed to check WireGuard interface: {str(e)}"
            logger.error(f"[Step 4] ✗ {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Step 5: Add peer to MikroTik
        logger.info("[Step 5] Adding peer to MikroTik...")
        try:
            # Create peer name as: telegramID-lastOctet (e.g., 6245412936-10)
            last_octet = client_ip.rsplit('.', 1)[-1]
            peer_name = f"{user_telegram_id}-{last_octet}" if user_telegram_id else f"wg-{last_octet}"
            
            peer_data = {
                'interface': wg_interface,
                'public-key': public_key,
                'allowed-address': f'{client_ip}/{mask}',
                'comment': peer_name
            }
            
            logger.info(f"[Step 5] Peer name: {peer_name}")
            
            api.get_resource('/interface/wireguard/peers').add(**peer_data)
            logger.info("[Step 5] ✓ Peer added successfully")
        except Exception as e:
            if 'already exists' not in str(e).lower():
                error_msg = f"Failed to add peer: {str(e)}"
                logger.error(f"[Step 5] ✗ {error_msg}")
                return {"success": False, "error": error_msg}
            logger.warning(f"[Step 5] Peer might already exist: {str(e)}")
        
        # Step 6: Disconnect
        logger.info("[Step 6] Disconnecting from MikroTik...")
        if pool:
            pool.disconnect()
            pool = None
        logger.info("[Step 6] ✓ Disconnected successfully")
        
        # Step 7: Save to database
        db_config = save_wireguard_config_to_db(
            user_telegram_id=user_telegram_id,
            plan_id=plan_id,
            plan_name=plan_name,
            private_key=private_key,
            public_key=public_key,
            client_ip=client_ip,
            wg_server_public_key=wg_server_public_key,
            wg_server_endpoint=wg_server_endpoint,
            wg_server_port=wg_server_port,
            wg_client_dns=wg_client_dns,
            duration_days=duration_days
        )
        
        # Step 8: Generate config text
        logger.info("[Step 8] Generating WireGuard config text...")
        endpoint_host = format_endpoint_host(wg_server_endpoint)
        config_lines = [
            "[Interface]",
            f"PrivateKey = {private_key}",
            f"Address = {client_ip}/{mask}",
            f"DNS = {wg_client_dns}",
            "",
            "[Peer]",
            f"PublicKey = {wg_server_public_key}",
            "AllowedIPs = 0.0.0.0/0, ::/0",
            f"Endpoint = {endpoint_host}:{wg_server_port}",
            "PersistentKeepalive = 25"
        ]
        config = "\n".join(config_lines)
        logger.info("[Step 8] ✓ Config text generated")
        
        # Step 9: Generate QR code
        logger.info("[Step 9] Generating QR code...")
        try:
            qr = qrcode.make(config)
            buffer = BytesIO()
            qr.save(buffer, format="PNG")
            qr_base64 = base64.b64encode(buffer.getvalue()).decode()
            logger.info("[Step 9] ✓ QR code generated")
        except Exception as e:
            logger.warning(f"[Step 9] Failed to generate QR code: {e}")
            qr_base64 = None
        
        logger.info("=" * 60)
        logger.info(f"✓ WireGuard account created successfully!")
        logger.info(f"  Client IP: {client_ip}")
        logger.info(f"  Database ID: {db_config.id}")
        logger.info("=" * 60)
        
        return {
            "success": True,
            "private_key": private_key,
            "public_key": public_key,
            "client_ip": client_ip,
            "config": config,
            "qr_code": f"data:image/png;base64,{qr_base64}" if qr_base64 else None,
            "config_id": db_config.id,
            "expires_at": db_config.expires_at
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error("=" * 60)
        logger.error(f"✗ WireGuard account creation FAILED!")
        logger.error(f"  Error: {error_msg}")
        logger.error("=" * 60)
        return {
            "success": False,
            "error": error_msg
        }
    finally:
        if pool:
            try:
                pool.disconnect()
                logger.info("Disconnected (cleanup)")
            except:
                pass
