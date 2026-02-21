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


def build_peer_comment(user_telegram_id: str, client_ip: str, legacy: bool = False) -> str:
    """Build MikroTik peer comment from user id and client IP."""
    ip_parts = (client_ip or "").split(".")
    ip_suffix = ""
    if len(ip_parts) >= 2:
        ip_suffix = f"{ip_parts[-2]}{ip_parts[-1]}"
    elif client_ip:
        ip_suffix = client_ip.replace(".", "")

    if not user_telegram_id:
        return f"wg-{ip_suffix}" if ip_suffix else "wg-client"

    if legacy:
        last_octet = client_ip.rsplit('.', 1)[-1] if client_ip and '.' in client_ip else client_ip
        return f"{user_telegram_id}-{last_octet}" if last_octet else str(user_telegram_id)

    # Requested format: <user_id>-3020 for client IP like 192.168.30.20
    return f"{user_telegram_id}-{ip_suffix}" if ip_suffix else str(user_telegram_id)


def _safe_int(value) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def _read_peer_counter(peer: dict, *candidate_keys: str) -> int:
    """Read first existing counter key from RouterOS peer payload."""
    for key in candidate_keys:
        if key in peer and peer.get(key) not in (None, ""):
            return _safe_int(peer.get(key))
    return 0


def _resolve_config_for_peer(peer: dict, config_index: dict):
    """Match MikroTik peer with a DB config using comment or allowed-address."""
    comment = (peer.get("comment", "") or "").strip()
    if comment and comment in config_index:
        return config_index[comment]

    allowed_address = peer.get("allowed-address", "")
    peer_ip = allowed_address.split('/')[0].strip() if allowed_address else ""
    if peer_ip:
        return config_index.get(peer_ip)
    return None


def sync_wireguard_usage_counters(
    mikrotik_host: str,
    mikrotik_user: str,
    mikrotik_pass: str,
    mikrotik_port: int,
    wg_interface: str,
):
    """Sync RX/TX counters from MikroTik peers into local DB with reboot/reset handling."""
    if not ROUTEROS_API_AVAILABLE:
        logger.warning("routeros_api unavailable; skipping usage sync")
        return

    db = SessionLocal()
    pool = None
    try:
        active_configs = db.query(WireGuardConfig).filter(WireGuardConfig.status == "active").all()
        if not active_configs:
            return

        config_index = {}
        for config in active_configs:
            if config.user_telegram_id and config.client_ip:
                config_index[build_peer_comment(config.user_telegram_id, config.client_ip)] = config
                config_index[build_peer_comment(config.user_telegram_id, config.client_ip, legacy=True)] = config
            if config.client_ip:
                config_index[config.client_ip] = config

        pool = RouterOsApiPool(
            mikrotik_host,
            username=mikrotik_user,
            password=mikrotik_pass,
            port=mikrotik_port,
            plaintext_login=True
        )
        api = pool.get_api()
        peers = api.get_resource('/interface/wireguard/peers').get()

        for peer in peers:
            config = _resolve_config_for_peer(peer, config_index)
            if not config:
                continue

            peer_interface = peer.get("interface")
            if peer_interface and peer_interface != wg_interface:
                continue

            current_rx = _read_peer_counter(peer, "rx", "rx-byte", "rx-bytes")
            current_tx = _read_peer_counter(peer, "tx", "tx-byte", "tx-bytes")
            previous_rx = config.last_rx_counter or 0
            previous_tx = config.last_tx_counter or 0

            if config.counter_reset_flag:
                config.cumulative_rx_bytes = 0
                config.cumulative_tx_bytes = 0
                delta_rx = 0
                delta_tx = 0
                config.counter_reset_flag = False
            else:
                # Router reboot / counter reset: if current counter is smaller than previous
                delta_rx = current_rx if current_rx < previous_rx else current_rx - previous_rx
                delta_tx = current_tx if current_tx < previous_tx else current_tx - previous_tx

            config.cumulative_rx_bytes = (config.cumulative_rx_bytes or 0) + max(delta_rx, 0)
            config.cumulative_tx_bytes = (config.cumulative_tx_bytes or 0) + max(delta_tx, 0)
            config.last_rx_counter = current_rx
            config.last_tx_counter = current_tx

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to sync wireguard usage counters: {e}")
    finally:
        if pool:
            try:
                pool.disconnect()
            except Exception:
                pass
        db.close()


def _peer_matches_config(peer: dict, config: WireGuardConfig) -> bool:
    comment = (peer.get("comment", "") or "").strip()
    expected_comment = build_peer_comment(config.user_telegram_id, config.client_ip)
    legacy_comment = build_peer_comment(config.user_telegram_id, config.client_ip, legacy=True)
    if comment in {expected_comment, legacy_comment}:
        return True

    allowed_address = (peer.get("allowed-address") or "").split('/')[0].strip()
    return bool(allowed_address and allowed_address == config.client_ip)


def disable_expired_or_exhausted_configs(
    mikrotik_host: str,
    mikrotik_user: str,
    mikrotik_pass: str,
    mikrotik_port: int,
    wg_interface: str,
):
    """Disable peers on MikroTik when plan duration or traffic is exhausted."""
    if not ROUTEROS_API_AVAILABLE:
        logger.warning("routeros_api unavailable; skipping disable checks")
        return

    db = SessionLocal()
    pool = None
    try:
        active_configs = db.query(WireGuardConfig).filter(WireGuardConfig.status == "active").all()
        if not active_configs:
            return

        now = datetime.utcnow()
        targets = []
        for config in active_configs:
            if not config.plan_id:
                continue
            plan = db.query(Plan).filter(Plan.id == config.plan_id).first()
            if not plan or not plan.duration_days or not plan.traffic_gb:
                continue

            expires_at = config.expires_at or (config.created_at + timedelta(days=plan.duration_days))
            plan_traffic_bytes = plan.traffic_gb * (1024 ** 3)
            consumed_bytes = config.cumulative_rx_bytes or 0
            exhausted_traffic = consumed_bytes >= plan_traffic_bytes
            expired_time = expires_at <= now

            if exhausted_traffic or expired_time:
                targets.append(config)

        if not targets:
            return

        pool = RouterOsApiPool(
            mikrotik_host,
            username=mikrotik_user,
            password=mikrotik_pass,
            port=mikrotik_port,
            plaintext_login=True
        )
        api = pool.get_api()
        peers_resource = api.get_resource('/interface/wireguard/peers')
        peers = peers_resource.get()

        for config in targets:
            for peer in peers:
                peer_interface = peer.get("interface")
                if peer_interface and peer_interface != wg_interface:
                    continue
                if _peer_matches_config(peer, config):
                    peer_id = peer.get(".id")
                    if peer_id:
                        peers_resource.set(**{".id": peer_id, "disabled": "yes"})
                    break
            config.status = "expired"

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to disable expired/exhausted configs: {e}")
    finally:
        if pool:
            try:
                pool.disconnect()
            except Exception:
                pass
        db.close()


def disable_wireguard_peer(
    mikrotik_host: str,
    mikrotik_user: str,
    mikrotik_pass: str,
    mikrotik_port: int,
    wg_interface: str,
    client_ip: str,
):
    """Disable a specific WireGuard peer on MikroTik by IP."""
    if not ROUTEROS_API_AVAILABLE:
        logger.warning("routeros_api unavailable; skipping disable")
        return False

    pool = None
    try:
        pool = RouterOsApiPool(
            mikrotik_host,
            username=mikrotik_user,
            password=mikrotik_pass,
            port=mikrotik_port,
            plaintext_login=True
        )
        api = pool.get_api()
        peers = api.get_resource('/interface/wireguard/peers').get()

        for peer in peers:
            peer_interface = peer.get("interface")
            if peer_interface and peer_interface != wg_interface:
                continue
            
            allowed_address = (peer.get("allowed-address") or "").split('/')[0].strip()
            if allowed_address == client_ip:
                peer_id = peer.get(".id")
                if peer_id:
                    api.get_resource('/interface/wireguard/peers').set(**{".id": peer_id, "disabled": "yes"})
                    logger.info(f"Disabled peer with IP: {client_ip}")
                    return True
        
        logger.warning(f"Peer not found for IP: {client_ip}")
        return False
    except Exception as e:
        logger.error(f"Failed to disable peer: {e}")
        return False
    finally:
        if pool:
            try:
                pool.disconnect()
            except Exception:
                pass


def reset_wireguard_peer_traffic(
    mikrotik_host: str,
    mikrotik_user: str,
    mikrotik_pass: str,
    mikrotik_port: int,
    wg_interface: str,
    client_ip: str,
):
    """Disable then enable a WireGuard peer to reset its counters on router side."""
    if not ROUTEROS_API_AVAILABLE:
        logger.warning("routeros_api unavailable; skipping peer reset")
        return False

    pool = None
    try:
        pool = RouterOsApiPool(
            mikrotik_host,
            username=mikrotik_user,
            password=mikrotik_pass,
            port=mikrotik_port,
            plaintext_login=True
        )
        api = pool.get_api()
        peers_resource = api.get_resource('/interface/wireguard/peers')
        peers = peers_resource.get()

        for peer in peers:
            peer_interface = peer.get("interface")
            if peer_interface and peer_interface != wg_interface:
                continue

            allowed_address = (peer.get("allowed-address") or "").split('/')[0].strip()
            if allowed_address == client_ip:
                peer_id = peer.get(".id")
                if not peer_id:
                    return False
                peers_resource.set(**{".id": peer_id, "disabled": "yes"})
                peers_resource.set(**{".id": peer_id, "disabled": "no"})
                logger.info(f"Reset peer traffic counters for IP: {client_ip}")
                return True

        logger.warning(f"Peer not found for reset, IP: {client_ip}")
        return False
    except Exception as e:
        logger.error(f"Failed to reset peer traffic: {e}")
        return False
    finally:
        if pool:
            try:
                pool.disconnect()
            except Exception:
                pass


def delete_wireguard_peer(
    mikrotik_host: str,
    mikrotik_user: str,
    mikrotik_pass: str,
    mikrotik_port: int,
    wg_interface: str,
    client_ip: str,
):
    """Delete a specific WireGuard peer on MikroTik by IP."""
    if not ROUTEROS_API_AVAILABLE:
        logger.warning("routeros_api unavailable; skipping delete")
        return False

    pool = None
    try:
        pool = RouterOsApiPool(
            mikrotik_host,
            username=mikrotik_user,
            password=mikrotik_pass,
            port=mikrotik_port,
            plaintext_login=True
        )
        api = pool.get_api()
        peers = api.get_resource('/interface/wireguard/peers').get()

        for peer in peers:
            peer_interface = peer.get("interface")
            if peer_interface and peer_interface != wg_interface:
                continue
            
            allowed_address = (peer.get("allowed-address") or "").split('/')[0].strip()
            if allowed_address == client_ip:
                peer_id = peer.get(".id")
                if peer_id:
                    api.get_resource('/interface/wireguard/peers').remove(**{".id": peer_id})
                    logger.info(f"Deleted peer with IP: {client_ip}")
                    return True
        
        logger.warning(f"Peer not found for IP: {client_ip}")
        return False
    except Exception as e:
        logger.error(f"Failed to delete peer: {e}")
        return False
    finally:
        if pool:
            try:
                pool.disconnect()
            except Exception:
                pass


def get_next_available_ip_from_db(network_base: str, ip_range_start: int = None, ip_range_end: int = None, excluded_last_octets: set | None = None) -> str:
    """
    Get next available IP from the database
    Range: by default 10-250 (skipping 1-9 and 251+)
    Can be customized with ip_range_start and ip_range_end
    """
    logger.info(f"[Step 2] Getting next available IP from database, network: {network_base}...")
    
    # Parse network base (e.g., "192.168.30.0" -> "192.168.30.")
    base_parts = network_base.rsplit('.', 1)
    prefix = base_parts[0] + "."
    
    # Default range if not specified
    start = ip_range_start if ip_range_start else 10
    end = ip_range_end if ip_range_end else 250
    
    logger.info(f"[Step 2] IP range: {start}-{end}")
    
    excluded_last_octets = excluded_last_octets or set()
    db = SessionLocal()
    try:
        # Get all active configs from database
        configs = db.query(WireGuardConfig).filter(WireGuardConfig.status == "active").all()
        
        # Extract used IPs
        used_ips = set()
        for config in configs:
            if config.client_ip:
                ip = config.client_ip
                if ip.count('.') == 3 and ip.startswith(prefix):  # IPv4 in the same network prefix
                    try:
                        last_octet = int(ip.rsplit('.', 1)[-1])
                        used_ips.add(last_octet)
                    except (ValueError, IndexError):
                        pass
        
        if excluded_last_octets:
            used_ips.update(excluded_last_octets)

        logger.info(f"[Step 2] Used IPs in database/router: {sorted(used_ips)}")
        
        # Find next available IP in the specified range
        for i in range(start, end + 1):
            if i not in used_ips:
                ip = f"{prefix}{i}"
                logger.info(f"[Step 2] ✓ Selected available IP: {ip}")
                return ip
        
        logger.warning(f"[Step 2] ✗ No available IP found in range {start}-{end}")
        return None
        
    except Exception as e:
        logger.error(f"[Step 2] ✗ Error getting IP from database: {e}")
        raise
    finally:
        db.close()


def get_used_ip_last_octets_from_mikrotik(api, network_base: str) -> set:
    """Collect used IP last octets from MikroTik peers in the target network."""
    used_ips = set()
    base_parts = (network_base or "").rsplit('.', 1)
    if len(base_parts) != 2:
        return used_ips
    prefix = base_parts[0] + "."

    try:
        peers = api.get_resource('/interface/wireguard/peers').get()
    except Exception as e:
        logger.warning(f"[Step 3] Failed to read peers from MikroTik for duplicate IP check: {e}")
        return used_ips

    for peer in peers:
        allowed_address = (peer.get('allowed-address') or '').split('/')[0].strip()
        if allowed_address.count('.') == 3 and allowed_address.startswith(prefix):
            try:
                used_ips.add(int(allowed_address.rsplit('.', 1)[-1]))
            except (ValueError, IndexError):
                continue

    return used_ips


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
    duration_days: int = None,
    server_id: int = None
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
            expires_at=expires_at,
            server_id=server_id
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




def parse_mikrotik_byte_value(value) -> int:
    """Parse MikroTik traffic counters to integer bytes."""
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)

    txt = str(value).strip().lower()
    units = {
        'b': 1,
        'kb': 1000,
        'mb': 1000 ** 2,
        'gb': 1000 ** 3,
        'tb': 1000 ** 4,
        'kib': 1024,
        'mib': 1024 ** 2,
        'gib': 1024 ** 3,
        'tib': 1024 ** 4,
    }

    for unit in sorted(units, key=len, reverse=True):
        if txt.endswith(unit):
            num = txt[:-len(unit)].strip()
            try:
                return int(float(num) * units[unit])
            except ValueError:
                return 0

    try:
        return int(float(txt))
    except ValueError:
        return 0


def fetch_wireguard_peers_usage(
    mikrotik_host: str,
    mikrotik_user: str,
    mikrotik_pass: str,
    mikrotik_port: int
) -> dict:
    """Fetch WireGuard peers usage counters from MikroTik."""
    if not ROUTEROS_API_AVAILABLE:
        raise RuntimeError("routeros_api module not installed")

    pool = None
    try:
        pool = RouterOsApiPool(
            mikrotik_host,
            username=mikrotik_user,
            password=mikrotik_pass,
            port=mikrotik_port,
            plaintext_login=True
        )
        api = pool.get_api()
        peers = api.get_resource('/interface/wireguard/peers').get()

        usage = {}
        for peer in peers:
            public_key = peer.get('public-key')
            if not public_key:
                continue
            rx = parse_mikrotik_byte_value(peer.get('rx') or peer.get('rx-byte'))
            tx = parse_mikrotik_byte_value(peer.get('tx') or peer.get('tx-byte'))
            usage[public_key] = {'rx': rx, 'tx': tx}

        return usage
    finally:
        if pool:
            pool.disconnect()


def sync_wireguard_usage_to_db(
    mikrotik_host: str,
    mikrotik_user: str,
    mikrotik_pass: str,
    mikrotik_port: int
) -> tuple[int, int]:
    """Sync usage from MikroTik to DB. Returns (updated_configs, total_active_configs)."""
    usage_map = fetch_wireguard_peers_usage(
        mikrotik_host=mikrotik_host,
        mikrotik_user=mikrotik_user,
        mikrotik_pass=mikrotik_pass,
        mikrotik_port=mikrotik_port
    )

    db = SessionLocal()
    try:
        configs = db.query(WireGuardConfig).filter(WireGuardConfig.status == 'active').all()
        updated = 0
        now = datetime.utcnow()

        for cfg in configs:
            peer_usage = usage_map.get(cfg.public_key)
            if not peer_usage:
                continue

            rx = max(peer_usage.get('rx', 0), 0)
            tx = max(peer_usage.get('tx', 0), 0)
            total_now = rx + tx

            prev_total = max((cfg.last_rx_bytes or 0) + (cfg.last_tx_bytes or 0), 0)
            if total_now >= prev_total:
                delta = total_now - prev_total
                cfg.traffic_used_bytes = (cfg.traffic_used_bytes or 0) + delta
            else:
                # Counter reset on router reboot; add full current counter as new baseline usage.
                cfg.traffic_used_bytes = (cfg.traffic_used_bytes or 0) + total_now

            cfg.last_rx_bytes = rx
            cfg.last_tx_bytes = tx
            cfg.last_usage_sync_at = now
            updated += 1

        db.commit()
        return updated, len(configs)
    except Exception:
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
    wg_ip_range_start: int = None,
    wg_ip_range_end: int = None,
    user_telegram_id: str = None,
    plan_id: int = None,
    plan_name: str = None,
    duration_days: int = None,
    server_id: int = None
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
        
        # Step 2: Get next available IP from DB
        client_ip = get_next_available_ip_from_db(wg_client_network_base, wg_ip_range_start, wg_ip_range_end)
        
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

            # Prevent duplicate IP assignment by checking current router peers.
            router_used_ips = get_used_ip_last_octets_from_mikrotik(api, wg_client_network_base)
            if client_ip and client_ip.count('.') == 3:
                try:
                    selected_last_octet = int(client_ip.rsplit('.', 1)[-1])
                except (ValueError, IndexError):
                    selected_last_octet = None

                if selected_last_octet in router_used_ips:
                    logger.warning(f"[Step 3] Selected IP {client_ip} already exists on MikroTik. Selecting a new IP...")
                    client_ip = get_next_available_ip_from_db(
                        wg_client_network_base,
                        wg_ip_range_start,
                        wg_ip_range_end,
                        excluded_last_octets=router_used_ips,
                    )
                    if client_ip is None:
                        error_msg = "No available IP in range after duplicate check"
                        logger.error(f"[Step 3] ✗ {error_msg}")
                        return {"success": False, "error": error_msg}
                    logger.info(f"[Step 3] ✓ Re-selected IP after MikroTik duplicate check: {client_ip}")
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
            peer_name = build_peer_comment(user_telegram_id, client_ip)
            
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
            duration_days=duration_days,
            server_id=server_id
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
            "peer_comment": peer_name,
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
