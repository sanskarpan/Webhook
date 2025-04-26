"""Add webhooks table

Revision ID: 2023b063d129
Revises: 1721b063d128
Create Date: 2025-04-27 15:12:23.458854

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2023b063d129'
down_revision = '1721b063d128'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create webhooks table
    op.create_table(
        'webhooks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
    )
    
    # Create index on webhooks.id
    op.create_index(op.f('ix_webhooks_id'), 'webhooks', ['id'], unique=False)
    
    # Recreate indexes for delivery_logs
    op.create_index('ix_delivery_logs_webhook_attempt', 'delivery_logs', ['webhook_id', 'attempt_number'], unique=False)
    op.create_index('ix_delivery_logs_subscription_status', 'delivery_logs', ['subscription_id', 'status'], unique=False)
    op.create_index('ix_delivery_logs_retry_status_time', 'delivery_logs', ['status', 'next_retry_at'], unique=False, 
                    postgresql_where=sa.text("status = 'pending'::deliverystatus AND next_retry_at IS NOT NULL"))
    op.create_index('ix_delivery_logs_retention', 'delivery_logs', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop webhooks table
    op.drop_table('webhooks')
    
    # Drop recreated indexes
    op.drop_index('ix_delivery_logs_webhook_attempt', table_name='delivery_logs')
    op.drop_index('ix_delivery_logs_subscription_status', table_name='delivery_logs')
    op.drop_index('ix_delivery_logs_retry_status_time', table_name='delivery_logs', 
                 postgresql_where="status = 'pending'::deliverystatus AND next_retry_at IS NOT NULL")
    op.drop_index('ix_delivery_logs_retention', table_name='delivery_logs') 