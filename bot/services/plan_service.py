import ipaddress

from models import Server, PlanServerMap, WireGuardConfig


def _normalize_ip_pool(server: Server) -> tuple[str | None, int | None, int | None]:
    """
    Normalize server IP pool fields.

    Supports legacy values that may be stored as:
      - CIDR (e.g. 192.168.30.0/24)
      - explicit range (e.g. 192.168.30.10-192.168.30.220 or 192.168.30.10-220)
      - base IP only (e.g. 192.168.30.0)
    """
    raw_base = (server.wg_client_network_base or "").strip()
    start = server.wg_ip_range_start
    end = server.wg_ip_range_end

    if not raw_base:
        return raw_base or None, start, end

    # Legacy: value kept as CIDR in DB
    if "/" in raw_base:
        try:
            network = ipaddress.ip_network(raw_base, strict=False)
            if isinstance(network, ipaddress.IPv4Network):
                raw_base = str(network.network_address)
                if start is None or end is None:
                    start = int(network.network_address) & 0xFF
                    end = int(network.broadcast_address) & 0xFF
        except ValueError:
            pass

    # Legacy/manual: explicit range kept in base field
    if "-" in raw_base and "/" not in raw_base:
        left, right = [p.strip() for p in raw_base.split("-", 1)]
        left_parts = left.split(".")
        if len(left_parts) == 4:
            prefix = ".".join(left_parts[:3])
            try:
                start = int(left_parts[3]) if start is None else start
                if "." in right:
                    right_parts = right.split(".")
                    if len(right_parts) == 4 and ".".join(right_parts[:3]) == prefix:
                        end = int(right_parts[3]) if end is None else end
                else:
                    end = int(right) if end is None else end
                raw_base = f"{prefix}.0"
            except ValueError:
                pass

    # Fallback for missing range columns
    if start is None:
        start = 1
    if end is None:
        end = 254

    return raw_base, start, end

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


def build_wg_kwargs(server: Server, user_id: str, plan, plan_name: str, duration_days: int, traffic_limit_gb: float = None):
    network_base, ip_range_start, ip_range_end = _normalize_ip_pool(server)
    return dict(
        mikrotik_host=server.host,
        mikrotik_user=server.username,
        mikrotik_pass=server.password,
        mikrotik_port=server.api_port,
        wg_interface=server.wg_interface,
        wg_server_public_key=server.wg_server_public_key,
        wg_server_endpoint=server.wg_server_endpoint,
        wg_server_port=server.wg_server_port,
        wg_client_network_base=network_base,
        wg_client_dns=server.wg_client_dns,
        wg_ip_range_start=ip_range_start,
        wg_ip_range_end=ip_range_end,
        user_telegram_id=str(user_id),
        plan_id=plan.id if plan else None,
        plan_name=plan_name,
        duration_days=duration_days,
        traffic_limit_gb=(traffic_limit_gb if traffic_limit_gb is not None else (plan.traffic_gb if plan else None)),
        server_id=server.id,
    )
