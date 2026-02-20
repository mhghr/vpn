from database import engine
from sqlalchemy import text

print("Adding missing columns to servers table...")

with engine.begin() as conn:
    # Add service_type_id
    try:
        conn.execute(text('ALTER TABLE servers ADD COLUMN service_type_id INTEGER'))
        print('Added service_type_id')
    except Exception as e:
        print(f'service_type_id: {e}')
    
    # Add host
    try:
        conn.execute(text('ALTER TABLE servers ADD COLUMN host VARCHAR'))
        print('Added host')
    except Exception as e:
        print(f'host: {e}')
    
    # Add api_port
    try:
        conn.execute(text('ALTER TABLE servers ADD COLUMN api_port INTEGER DEFAULT 8728'))
        print('Added api_port')
    except Exception as e:
        print(f'api_port: {e}')
    
    # Add wg_interface
    try:
        conn.execute(text('ALTER TABLE servers ADD COLUMN wg_interface VARCHAR'))
        print('Added wg_interface')
    except Exception as e:
        print(f'wg_interface: {e}')
    
    # Add wg_server_public_key
    try:
        conn.execute(text('ALTER TABLE servers ADD COLUMN wg_server_public_key VARCHAR'))
        print('Added wg_server_public_key')
    except Exception as e:
        print(f'wg_server_public_key: {e}')
    
    # Add wg_server_endpoint
    try:
        conn.execute(text('ALTER TABLE servers ADD COLUMN wg_server_endpoint VARCHAR'))
        print('Added wg_server_endpoint')
    except Exception as e:
        print(f'wg_server_endpoint: {e}')
    
    # Add wg_server_port
    try:
        conn.execute(text('ALTER TABLE servers ADD COLUMN wg_server_port INTEGER'))
        print('Added wg_server_port')
    except Exception as e:
        print(f'wg_server_port: {e}')
    
    # Add wg_client_network_base
    try:
        conn.execute(text('ALTER TABLE servers ADD COLUMN wg_client_network_base VARCHAR'))
        print('Added wg_client_network_base')
    except Exception as e:
        print(f'wg_client_network_base: {e}')
    
    # Add wg_client_dns
    try:
        conn.execute(text('ALTER TABLE servers ADD COLUMN wg_client_dns VARCHAR'))
        print('Added wg_client_dns')
    except Exception as e:
        print(f'wg_client_dns: {e}')
    
    # Add capacity
    try:
        conn.execute(text('ALTER TABLE servers ADD COLUMN capacity INTEGER DEFAULT 100'))
        print('Added capacity')
    except Exception as e:
        print(f'capacity: {e}')
    
    # Add is_active
    try:
        conn.execute(text('ALTER TABLE servers ADD COLUMN is_active BOOLEAN DEFAULT TRUE'))
        print('Added is_active')
    except Exception as e:
        print(f'is_active: {e}')
    
    # Add local_ip
    try:
        conn.execute(text('ALTER TABLE servers ADD COLUMN local_ip VARCHAR'))
        print('Added local_ip')
    except Exception as e:
        print(f'local_ip: {e}')
    
    # Add path
    try:
        conn.execute(text('ALTER TABLE servers ADD COLUMN path VARCHAR DEFAULT \"/\"'))
        print('Added path')
    except Exception as e:
        print(f'path: {e}')
    
    # Add api_username
    try:
        conn.execute(text('ALTER TABLE servers ADD COLUMN api_username VARCHAR'))
        print('Added api_username')
    except Exception as e:
        print(f'api_username: {e}')
    
    # Add api_password
    try:
        conn.execute(text('ALTER TABLE servers ADD COLUMN api_password VARCHAR'))
        print('Added api_password')
    except Exception as e:
        print(f'api_password: {e}')
    
    # Add xui_version
    try:
        conn.execute(text('ALTER TABLE servers ADD COLUMN xui_version VARCHAR'))
        print('Added xui_version')
    except Exception as e:
        print(f'xui_version: {e}')
    
    # Add system_info
    try:
        conn.execute(text('ALTER TABLE servers ADD COLUMN system_info TEXT'))
        print('Added system_info')
    except Exception as e:
        print(f'system_info: {e}')
    
    # Add approved_at
    try:
        conn.execute(text('ALTER TABLE servers ADD COLUMN approved_at TIMESTAMP'))
        print('Added approved_at')
    except Exception as e:
        print(f'approved_at: {e}')
    
    # Create index for service_type_id
    try:
        conn.execute(text('CREATE INDEX IF NOT EXISTS idx_servers_service_type_id ON servers(service_type_id)'))
        print('Created index')
    except Exception as e:
        print(f'index: {e}')

print("\nDone!")
