from models import Server, PlanServerMap, WireGuardConfig
from config import (
    MIKROTIK_HOST, MIKROTIK_USER, MIKROTIK_PASS, MIKROTIK_PORT,
    WG_INTERFACE, WG_SERVER_PUBLIC_KEY, WG_SERVER_ENDPOINT, WG_SERVER_PORT,
    WG_CLIENT_NETWORK_BASE, WG_CLIENT_DNS,
)


def get_plan_servers(db, plan_id: int):
    return db.query(Server).join(PlanServerMap, PlanServerMap.server_id == Server.id).filter(
        PlanServerMap.plan_id == plan_id,
        Server.is_active == True,
    ).all()


def get_server_active_config_count(db, server_id: int) -> int:
    return db.query(WireGuardConfig).filter(
        WireGuardConfig.server_id == server_id,
        WireGuardConfig.status == "active",
    ).count()


def get_available_servers_for_plan(db, plan_id: int):
    servers = get_plan_servers(db, plan_id)
    return [srv for srv in servers if (srv.capacity or 0) <= 0 or get_server_active_config_count(db, srv.id) < (srv.capacity or 0)]


def build_wg_kwargs(server: Server, user_id: str, plan, plan_name: str, duration_days: int):
    return dict(
        mikrotik_host=server.host or MIKROTIK_HOST,
        mikrotik_user=server.username or MIKROTIK_USER,
        mikrotik_pass=server.password or MIKROTIK_PASS,
        mikrotik_port=server.api_port or MIKROTIK_PORT,
        wg_interface=server.wg_interface or WG_INTERFACE,
        wg_server_public_key=server.wg_server_public_key or WG_SERVER_PUBLIC_KEY,
        wg_server_endpoint=server.wg_server_endpoint or WG_SERVER_ENDPOINT,
        wg_server_port=server.wg_server_port or WG_SERVER_PORT,
        wg_client_network_base=server.wg_client_network_base or WG_CLIENT_NETWORK_BASE,
        wg_client_dns=server.wg_client_dns or WG_CLIENT_DNS,
        wg_ip_range_start=server.wg_ip_range_start if server.wg_is_ip_range else None,
        wg_ip_range_end=server.wg_ip_range_end if server.wg_is_ip_range else None,
        user_telegram_id=str(user_id),
        plan_id=plan.id if plan else None,
        plan_name=plan_name,
        duration_days=duration_days,
        server_id=server.id,
    )
