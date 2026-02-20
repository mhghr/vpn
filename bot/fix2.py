from database import engine
from sqlalchemy import text

# Run each ALTER in separate transaction
tables = [
    ('path', 'VARCHAR'),
    ('api_username', 'VARCHAR'),
    ('api_password', 'VARCHAR'),
    ('xui_version', 'VARCHAR'),
    ('system_info', 'TEXT'),
    ('approved_at', 'TIMESTAMP')
]

for col, typ in tables:
    try:
        with engine.begin() as conn:
            conn.execute(text(f'ALTER TABLE servers ADD COLUMN {col} {typ}'))
            print(f'Added {col}')
    except Exception as e:
        print(f'{col}: {e}')

# Create index separately
try:
    with engine.begin() as conn:
        conn.execute(text('CREATE INDEX IF NOT EXISTS idx_servers_service_type_id ON servers(service_type_id)'))
        print('Created index')
except Exception as e:
    print(f'index: {e}')
