"""Initial station and measurement schema."""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None

def upgrade():
    op.create_table('stations', sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('identifier', sa.String(64), nullable=False, unique=True),
        sa.Column('name', sa.String(120), nullable=False), sa.Column('description', sa.String(500)),
        sa.Column('location', sa.String(200)), sa.Column('is_demo', sa.Boolean, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False), sa.Column('last_seen', sa.DateTime))
    columns = [sa.Column('id', sa.Integer, primary_key=True),
               sa.Column('station_id', sa.Integer, sa.ForeignKey('stations.id'), nullable=False)]
    columns += [sa.Column(n, sa.Float) for n in ['temperature_c', 'humidity_pct', 'pressure_hpa', 'bmp_temperature_c', 'luminosity_lux']]
    columns += [sa.Column(n, sa.Integer) for n in ['gas_adc_raw', 'gas_gpio_mv', 'gas_ao_mv_estimated', 'rain_sensor_digital']]
    columns += [sa.Column('rain_detected', sa.Boolean), sa.Column('received_at', sa.DateTime, nullable=False)]
    op.create_table('measurements', *columns)
    op.create_index('ix_measurements_station_time', 'measurements', ['station_id', 'received_at', 'id'])
    table = sa.table('stations', sa.column('identifier'), sa.column('name'), sa.column('is_demo'), sa.column('created_at'))
    from datetime import datetime
    op.bulk_insert(table, [{'identifier': 'estacao-01', 'name': 'Estação principal', 'is_demo': False, 'created_at': datetime.utcnow()}])

def downgrade():
    op.drop_table('measurements')
    op.drop_table('stations')
