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
