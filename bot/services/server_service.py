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
    """Check only host reachability and WG interface existence for server health."""
    result = {
        "host": False,
        "wg_interface": False,
    }

    host = (server.host or "").strip()
    api_port = server.api_port
    username = (server.username or "").strip()
    password = (server.password or "").strip()
    wg_interface = (server.wg_interface or "").strip()

    if not (host and isinstance(api_port, int) and 1 <= api_port <= 65535 and username and password and wg_interface):
        result["all_ok"] = False
        return result

    pool = None
    try:
        with socket.create_connection((host, api_port), timeout=2):
            pass
        result["host"] = True

        pool = RouterOsApiPool(
            host,
            username=username,
            password=password,
            port=api_port,
            plaintext_login=True,
        )
        api = pool.get_api()
        interface_rows = api.get_resource('/interface').get(name=wg_interface)
        result["wg_interface"] = bool(interface_rows)
    except Exception:
        result["host"] = False
        result["wg_interface"] = False
    finally:
        if pool:
            try:
                pool.disconnect()
            except Exception:
                pass

    result["all_ok"] = bool(result["host"] and result["wg_interface"])
    return result
