"""
SQL Helper utilities for working around ORM limitations.
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.delivery_log import DeliveryStatus

logger = logging.getLogger(__name__)

async def create_delivery_log_raw(
    session: AsyncSession,
    webhook_id: UUID,
    subscription_id: UUID,
    target_url: str,
    payload: Dict[str, Any],
    event_type: Optional[str] = None,
    status: DeliveryStatus = DeliveryStatus.PENDING,
    attempt_number: int = 1,
    http_status: Optional[int] = None,
    error_details: Optional[str] = None,
    next_retry_at: Optional[datetime] = None
) -> Optional[Dict[str, Any]]:
    """
    Create a delivery log entry using raw SQL to work around enum issues.
    
    Args:
        session: Database session
        webhook_id: Webhook UUID
        subscription_id: Subscription UUID
        target_url: Target URL for webhook delivery
        payload: Webhook payload
        event_type: Optional event type
        status: Delivery status enum value
        attempt_number: Attempt number
        http_status: Optional HTTP status code
        error_details: Optional error details
        next_retry_at: Optional next retry time
        
    Returns:
        Dictionary with created log data or None on error
    """
    log_id = uuid.uuid4()
    
    try:
        # Handle payload that might be in different formats
        # Ensure payload is properly serialized to JSON string
        if isinstance(payload, dict) or isinstance(payload, list):
            payload_json = json.dumps(payload)
        elif isinstance(payload, str):
            # Check if it's a valid JSON string already
            try:
                json.loads(payload)  # Just to validate
                payload_json = payload
            except json.JSONDecodeError:
                # If not a valid JSON string, treat it as a literal string and serialize
                payload_json = json.dumps(payload)
        else:
            # For any other types, convert to string and serialize
            payload_json = json.dumps(str(payload))
        
        # Map status enum to string value
        status_str = status.value
        
        # Use a simpler form with named parameters
        # The asyncpg driver doesn't handle the ::json cast correctly in parameterized queries
        query = """
        INSERT INTO delivery_logs (
            id, webhook_id, subscription_id, target_url, payload, 
            event_type, attempt_number, status, http_status, error_details, 
            next_retry_at
        ) VALUES (
            :id, :webhook_id, :subscription_id, :target_url, cast(:payload as jsonb),
            :event_type, :attempt_number, :status, :http_status, :error_details,
            :next_retry_at
        ) RETURNING id, created_at, updated_at;
        """
        
        # Execute the query using named parameters
        result = await session.execute(
            text(query),
            {
                "id": log_id,
                "webhook_id": webhook_id,
                "subscription_id": subscription_id,
                "target_url": target_url,
                "payload": payload_json,  # Already converted to JSON string
                "event_type": event_type,
                "attempt_number": attempt_number,
                "status": status_str,
                "http_status": http_status,
                "error_details": error_details,
                "next_retry_at": next_retry_at
            }
        )
        
        # Get the result row
        row = result.fetchone()
        
        # Commit the transaction
        await session.commit()
        
        if row:
            # Return a dictionary with the log data including the original payload object
            # This avoids potential issues with double serialization
            return {
                "id": log_id,
                "webhook_id": webhook_id,
                "subscription_id": subscription_id,
                "target_url": target_url,
                "payload": payload,  # Use the original payload object
                "event_type": event_type,
                "attempt_number": attempt_number,
                "status": status,
                "http_status": http_status,
                "error_details": error_details,
                "next_retry_at": next_retry_at,
                "created_at": row[1],
                "updated_at": row[2]
            }
        
        return None
    
    except Exception as e:
        logger.error(f"Error creating delivery log: {str(e)}")
        await session.rollback()
        raise e 

def get_delivery_log_raw(
    session: Session,
    log_id: UUID
) -> Optional[Dict[str, Any]]:
    """
    Get a delivery log entry using raw SQL to work around enum issues.
    
    Args:
        session: Database session
        log_id: Log UUID
        
    Returns:
        Dictionary with log data or None if not found
    """
    try:
        # Query using raw SQL
        query = """
        SELECT 
            id, webhook_id, subscription_id, target_url, payload, 
            event_type, attempt_number, status, http_status, error_details, 
            created_at, updated_at, next_retry_at
        FROM delivery_logs
        WHERE id = :id
        """
        
        # Execute the query
        result = session.execute(
            text(query),
            {"id": log_id}
        )
        
        # Get the result row
        row = result.fetchone()
        
        if not row:
            return None
        
        # Define column names for the result row
        columns = [
            "id", "webhook_id", "subscription_id", "target_url", "payload", 
            "event_type", "attempt_number", "status", "http_status", "error_details", 
            "created_at", "updated_at", "next_retry_at"
        ]
        
        # Convert row to dictionary using a robust approach
        try:
            # First attempt direct conversion
            log_data = dict(row)
        except Exception as dict_error:
            # If direct conversion fails, use a more explicit column-by-column approach
            try:
                log_data = {columns[i]: row[i] for i in range(len(columns))}
            except Exception as fallback_error:
                logger.error(f"Dictionary conversion failed: {dict_error}. Fallback also failed: {fallback_error}")
                return None
            
        # Map status string to enum
        status_str = log_data.get("status")  # Now using the dictionary access
        status = None
        for enum_val in DeliveryStatus:
            if enum_val.value.lower() == status_str.lower():
                status = enum_val
                break
        
        # Parse JSON payload - handle different potential payload types
        try:
            # If payload is a string, try to parse it as JSON
            payload_value = log_data.get("payload")
            if isinstance(payload_value, str):
                payload = json.loads(payload_value)
            # If it's already a dict, use it directly
            elif isinstance(payload_value, dict):
                payload = payload_value
            # If it's None, use empty dict
            elif payload_value is None:
                payload = {}
            # Handle other cases (like raw JSON from PostgreSQL) by converting to string first
            else:
                payload = json.loads(str(payload_value))
        except Exception as e:
            logger.error(f"Error parsing payload: {str(e)}")
            payload = {}
        
        # Update the dictionary with processed values
        log_data["status"] = status
        log_data["payload"] = payload
        
        return log_data
        
    except Exception as e:
        logger.error(f"Error getting delivery log: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def update_delivery_log_status_raw(
    session: Session,
    log_id: UUID,
    status: str,
    http_status: Optional[int] = None,
    error_details: Optional[str] = None,
    next_retry_at: Optional[datetime] = None
) -> Optional[Dict[str, Any]]:
    """
    Update a delivery log status using raw SQL to avoid enum issues.
    
    Args:
        session: SQLAlchemy database session
        log_id: DeliveryLog UUID
        status: New delivery status (as a string)
        http_status: HTTP status code (optional)
        error_details: Error details (optional)
        next_retry_at: Next retry time (optional)
        
    Returns:
        Dictionary with updated log data or None if not found/error
    """
    try:
        # Convert dates to ISO format if they exist
        next_retry_at_str = next_retry_at.isoformat() if next_retry_at else None
        
        # Build the SQL query using string concatenation with consistent parameter style
        query_str = (
            "UPDATE delivery_logs "
            "SET status = :status::deliverystatus, updated_at = NOW()"
        )
        
        params = {
            "log_id": log_id,
            "status": status
        }
        
        # Add additional parameters if they exist
        if http_status is not None:
            query_str += ", http_status = :http_status"
            params["http_status"] = http_status
            
        if error_details is not None:
            query_str += ", error_details = :error_details"
            params["error_details"] = error_details
            
        if next_retry_at is not None:
            query_str += ", next_retry_at = :next_retry_at"
            params["next_retry_at"] = next_retry_at_str
        
        # Add the WHERE clause and RETURNING
        query_str += (
            " WHERE id = :log_id "
            "RETURNING "
            "id, webhook_id, subscription_id, target_url, payload, event_type, "
            "attempt_number, status, http_status, error_details, created_at, updated_at, next_retry_at"
        )
        
        # Execute the raw SQL UPDATE
        query = text(query_str)
        result = session.execute(query, params)
        row = result.fetchone()
        
        if not row:
            return None
            
        # Define column names for the result row
        columns = [
            "id", "webhook_id", "subscription_id", "target_url", "payload", 
            "event_type", "attempt_number", "status", "http_status", "error_details", 
            "created_at", "updated_at", "next_retry_at"
        ]
        
        # Convert row to dictionary using a robust approach
        try:
            # First attempt direct conversion
            log_data = dict(row)
        except Exception as dict_error:
            # If direct conversion fails, use a more explicit column-by-column approach
            try:
                log_data = {columns[i]: row[i] for i in range(len(columns))}
            except Exception as fallback_error:
                logger.error(f"Dictionary conversion failed: {dict_error}. Fallback also failed: {fallback_error}")
                return None
        
        # Parse the payload JSON if needed
        try:
            payload_value = log_data.get("payload")
            if isinstance(payload_value, str):
                log_data["payload"] = json.loads(payload_value)
        except Exception as e:
            logger.error(f"Error parsing payload in updated log: {str(e)}")
        
        # Ensure the session commits this transaction
        session.commit()
        
        return log_data
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating delivery log status: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def create_retry_log_raw(
    session: Session,
    previous_log_data: Dict[str, Any],
    next_retry_at: Optional[datetime] = None
) -> Optional[Dict[str, Any]]:
    """
    Create a new retry log entry based on a previous delivery log using raw SQL.
    
    Args:
        session: SQLAlchemy database session
        previous_log_data: Dictionary containing the previous log's data
        next_retry_at: When to retry next (optional)
        
    Returns:
        Dictionary with created retry log data or None on error
    """
    try:
        # Handle payload that might be in different formats
        payload = previous_log_data.get("payload", {})
        
        # Ensure payload is properly serialized to JSON string
        if isinstance(payload, dict) or isinstance(payload, list):
            payload_json = json.dumps(payload)
        elif isinstance(payload, str):
            # Check if it's a valid JSON string already
            try:
                json.loads(payload)  # Just to validate
                payload_json = payload
            except json.JSONDecodeError:
                # If not a valid JSON string, treat it as a literal string and serialize
                payload_json = json.dumps(payload)
        else:
            # For any other types, convert to string and serialize
            payload_json = json.dumps(str(payload))
        
        # Convert dates to ISO format if they exist
        next_retry_at_str = next_retry_at.isoformat() if next_retry_at else None
        
        # Execute the raw SQL INSERT
        query = text("""
            INSERT INTO delivery_logs (
                id, webhook_id, subscription_id, target_url, payload, event_type,
                attempt_number, status, next_retry_at
            )
            VALUES (
                gen_random_uuid(), 
                :webhook_id, 
                :subscription_id, 
                :target_url, 
                CAST(:payload AS jsonb), 
                :event_type,
                :attempt_number, 
                'pending'::deliverystatus, 
                :next_retry_at
            )
            RETURNING 
                id, webhook_id, subscription_id, target_url, payload, event_type,
                attempt_number, status, http_status, error_details, created_at, updated_at, next_retry_at
        """)
        
        result = session.execute(query, {
            "webhook_id": previous_log_data.get("webhook_id"),
            "subscription_id": previous_log_data.get("subscription_id"),
            "target_url": previous_log_data.get("target_url"),
            "payload": payload_json,
            "event_type": previous_log_data.get("event_type"),
            "attempt_number": previous_log_data.get("attempt_number", 1) + 1,
            "next_retry_at": next_retry_at_str
        })
        
        row = result.fetchone()
        if not row:
            return None
            
        # Convert row to dictionary - using a more robust approach that works across SQLAlchemy versions
        try:
            # First attempt direct conversion
            log_data = dict(row)
        except Exception as dict_error:
            # If direct conversion fails, use a more explicit column-by-column approach
            try:
                columns = [
                    "id", "webhook_id", "subscription_id", "target_url", "payload", 
                    "event_type", "attempt_number", "status", "http_status", "error_details", 
                    "created_at", "updated_at", "next_retry_at"
                ]
                log_data = {columns[i]: row[i] for i in range(len(columns))}
            except Exception as fallback_error:
                logger.error(f"Dictionary conversion failed: {dict_error}. Fallback also failed: {fallback_error}")
                return None
        
        # Parse the payload JSON if needed
        try:
            if isinstance(log_data.get("payload"), str):
                log_data["payload"] = json.loads(log_data["payload"])
        except Exception as e:
            logger.error(f"Error parsing payload in retry log: {str(e)}")
        
        # Ensure the session commits this transaction
        session.commit()
        
        return log_data
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating retry log: {str(e)}")
        # Log the full stack trace for better debugging
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def update_delivery_log_simple(
    session: Session,
    log_id: UUID,
    status: str,
    http_status: Optional[int] = None,
    error_details: Optional[str] = None,
    next_retry_at: Optional[datetime] = None
) -> Optional[Dict[str, Any]]:
    """
    Update a delivery log status using direct SQL execution.
    
    Args:
        session: SQLAlchemy database session
        log_id: DeliveryLog UUID
        status: New delivery status string value 
        http_status: HTTP status code (optional)
        error_details: Error details (optional)
        next_retry_at: Next retry time (optional)
        
    Returns:
        Dictionary with updated log data or None if not found/error
    """
    try:
        # Build the SQL query directly with string parameters
        query = """
        UPDATE delivery_logs
        SET status = '{0}'::deliverystatus, updated_at = NOW()
        """.format(status)
        
        params = []
        
        if http_status is not None:
            query += ", http_status = %s"
            params.append(http_status)
            
        if error_details is not None:
            query += ", error_details = %s"
            params.append(error_details)
            
        if next_retry_at is not None:
            next_retry_at_str = next_retry_at.isoformat() if next_retry_at else None
            query += ", next_retry_at = %s"
            params.append(next_retry_at_str)
        
        # Add the WHERE clause and RETURNING
        query += """
        WHERE id = %s
        RETURNING 
            id, webhook_id, subscription_id, target_url, payload, event_type,
            attempt_number, status, http_status, error_details, created_at, updated_at, next_retry_at
        """
        params.append(str(log_id))
        
        # Execute the query directly with the connection
        # Get a raw connection
        conn = session.connection().connection
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        
        if not row:
            return None
            
        # Define column names for the result row
        columns = [
            "id", "webhook_id", "subscription_id", "target_url", "payload", 
            "event_type", "attempt_number", "status", "http_status", "error_details", 
            "created_at", "updated_at", "next_retry_at"
        ]
        
        # Create a dictionary mapping column names to values - using a robust approach
        try:
            log_data = dict(zip(columns, row))
        except Exception as dict_error:
            # If that fails, use a more explicit approach
            try:
                log_data = {columns[i]: row[i] for i in range(min(len(columns), len(row)))}
            except Exception as fallback_error:
                logger.error(f"Dictionary conversion failed: {dict_error}. Fallback also failed: {fallback_error}")
                return None
        
        # Parse the payload JSON if needed
        try:
            payload_value = log_data.get("payload")
            if isinstance(payload_value, str):
                log_data["payload"] = json.loads(payload_value)
        except Exception as e:
            logger.error(f"Error parsing payload: {str(e)}")
            
        # Map status string to enum
        status_str = log_data.get("status")
        if status_str:
            for enum_val in DeliveryStatus:
                if enum_val.value == status_str:
                    log_data["status"] = enum_val
                    break
        
        # Commit after data processing
        session.commit()
        
        return log_data
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error in simple update: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None 