from database import engine
from sqlalchemy import text

# Add missing columns
missing = [
    ('service_type_id', 'INTEGER'),
    ('host', 'VARCHAR'),
    ('api_port', 'INTEGER DEFAULT 8728'),
    ('wg_interface', 'VARCHAR'),
    ('wg_server_public_key', 'VARCHAR'),
    ('wg_server_endpoint', 'VARCHAR'),
    ('wg_server_port', 'INTEGER'),
    ('wg_client_network_base', 'VARCHAR'),
    ('wg_client_dns', 'VARCHAR'),
    ('capacity', 'INTEGER DEFAULT 100'),
    ('is_active', 'BOOLEAN DEFAULT TRUE'),
    ('local_ip', 'VARCHAR'),
]

for col, typ in missing:
    try:
        with engine.begin() as conn:
            conn.execute(text(f'ALTER TABLE servers ADD COLUMN {col} {typ}'))
            print(f'Added {col}')
    except Exception as e:
        print(f'{col}: {e}')

# Index
try:
    with engine.begin() as conn:
        conn.execute(text('CREATE INDEX IF NOT EXISTS idx_servers_service_type_id ON servers(service_type_id)'))
        print('Index created')
except Exception as e:
    print(f'Index: {e}')
