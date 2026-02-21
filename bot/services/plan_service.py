from models import Server, PlanServerMap, WireGuardConfig

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
        mikrotik_host=server.host,
        mikrotik_user=server.username,
        mikrotik_pass=server.password,
        mikrotik_port=server.api_port,
        wg_interface=server.wg_interface,
        wg_server_public_key=server.wg_server_public_key,
        wg_server_endpoint=server.wg_server_endpoint,
        wg_server_port=server.wg_server_port,
        wg_client_network_base=server.wg_client_network_base,
        wg_client_dns=server.wg_client_dns,
        wg_ip_range_start=server.wg_ip_range_start,
        wg_ip_range_end=server.wg_ip_range_end,
        user_telegram_id=str(user_id),
        plan_id=plan.id if plan else None,
        plan_name=plan_name,
        duration_days=duration_days,
        server_id=server.id,
    )
