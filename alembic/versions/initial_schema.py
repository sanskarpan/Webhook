"""Initial database schema

Revision ID: 9b7bceca0c4c
Revises: 
Create Date: 2025-04-27 2:13:09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '9b7bceca0c4c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('target_url', sa.String(255), nullable=False, index=True),
        sa.Column('secret_key', sa.String(255), nullable=True),
        sa.Column('event_types', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
    )
    
    # Create delivery_logs table
    op.create_table(
        'delivery_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('webhook_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('subscriptions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('target_url', sa.String(255), nullable=False),
        sa.Column('payload', postgresql.JSON, nullable=False),
        sa.Column('event_type', sa.String(100), nullable=True, index=True),
        sa.Column('attempt_number', sa.Integer, nullable=False, default=1),
        sa.Column('status', sa.Enum('success', 'failed_attempt', 'final_failure', 'pending', name='deliverystatus'), nullable=False, default='pending', index=True),
        sa.Column('http_status', sa.Integer, nullable=True),
        sa.Column('error_details', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, index=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True, index=True),
    )
    
    # Create indexes
    op.create_index('ix_delivery_logs_subscription_status', 'delivery_logs', ['subscription_id', 'status'])
    op.create_index('ix_delivery_logs_webhook_attempt', 'delivery_logs', ['webhook_id', 'attempt_number'])
    op.create_index('ix_delivery_logs_retry_status_time', 'delivery_logs', ['status', 'next_retry_at'], 
                   postgresql_where=sa.text("status = 'pending' AND next_retry_at IS NOT NULL"))
    
    # Index for log retention cleanup
    op.create_index('ix_delivery_logs_retention', 'delivery_logs', ['created_at'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('delivery_logs')
    op.drop_table('subscriptions')
    
    # Drop enum type
    op.execute('DROP TYPE IF EXISTS deliverystatus')