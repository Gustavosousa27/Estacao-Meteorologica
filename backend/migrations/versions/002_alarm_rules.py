"""Configurable warning and alarm rules for the primary station."""
from alembic import op
import sqlalchemy as sa
revision = '002'
down_revision = '001'

def upgrade():
    op.create_table('alarm_rules',
        sa.Column('id',sa.Integer,primary_key=True),
        sa.Column('station_id',sa.Integer,sa.ForeignKey('stations.id'),nullable=False),
        sa.Column('name',sa.String(120),nullable=False),
        sa.Column('metric',sa.String(40),nullable=False),
        sa.Column('operator',sa.String(8),nullable=False),
        sa.Column('threshold',sa.Float,nullable=False),
        sa.Column('severity',sa.String(12),nullable=False),
        sa.Column('enabled',sa.Boolean,nullable=False))
    op.create_index('ix_alarm_rules_station_id','alarm_rules',['station_id'])

def downgrade():
    op.drop_table('alarm_rules')
