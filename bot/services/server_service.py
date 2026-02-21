import socket

from routeros_api import RouterOsApiPool


def check_server_connection(server) -> tuple[bool, str]:
    try:
        pool = RouterOsApiPool(
            server.host,
            username=server.username or "",
            password=server.password or "",
            port=server.api_port or 8728,
            plaintext_login=True,
        )
        try:
            api = pool.get_api()
            api.get_resource('/system/resource').get()
        finally:
            pool.disconnect()
        return True, "اتصال برقرار است"
    except Exception as e:
        return False, str(e)


def evaluate_server_parameters(server) -> dict:
    """Validate checkable server parameters and return per-field status.

    Status values are True/False/None where None means "not checkable".
    """
    result = {
        "host": None,
        "api_port": None,
        "username": None,
        "password": None,
        "wg_interface": None,
    }

    host = (server.host or "").strip()
    api_port = server.api_port
    username = (server.username or "").strip()
    password = (server.password or "").strip()
    wg_interface = (server.wg_interface or "").strip()

    # Stage 1: network reachability for host/port
    can_reach = False
    if host and isinstance(api_port, int) and 1 <= api_port <= 65535:
        try:
            with socket.create_connection((host, api_port), timeout=4):
                can_reach = True
        except Exception:
            can_reach = False

    result["host"] = can_reach
    result["api_port"] = can_reach

    # Stage 2: API auth check for username/password
    api = None
    pool = None
    auth_ok = False
    if can_reach and username and password:
        try:
            pool = RouterOsApiPool(
                host,
                username=username,
                password=password,
                port=api_port,
                plaintext_login=True,
            )
            api = pool.get_api()
            api.get_resource('/system/resource').get()
            auth_ok = True
        except Exception:
            auth_ok = False

    result["username"] = auth_ok
    result["password"] = auth_ok

    # Stage 3: interface existence check
    if auth_ok and wg_interface:
        try:
            interface_rows = api.get_resource('/interface').get(name=wg_interface)
            result["wg_interface"] = bool(interface_rows)
        except Exception:
            result["wg_interface"] = False
    elif wg_interface:
        result["wg_interface"] = False

    if pool:
        try:
            pool.disconnect()
        except Exception:
            pass

    checkable_values = [value for value in result.values() if value is not None]
    result["all_ok"] = bool(checkable_values) and all(checkable_values)
    return result
