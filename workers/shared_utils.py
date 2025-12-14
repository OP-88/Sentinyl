"""
Shared utilities for Sentinyl workers
Database connections, Redis helpers, and notification functions
"""
import redis
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, Any
from loguru import logger
from functools import wraps
import time
import os


# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://sentinyl:sentinyl_secure_pass@localhost:5432/sentinyldb")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def get_redis_connection() -> redis.Redis:
    """Get Redis connection"""
    return redis.from_url(REDIS_URL, decode_responses=True)


def get_db_connection():
    """Get PostgreSQL database connection"""
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def retry_on_failure(max_retries: int = 3, delay: int = 2):
    """
    Decorator to retry function on failure with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay in seconds (doubles each retry)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries: {e}")
                        raise
                    
                    logger.warning(f"Function {func.__name__} failed (attempt {retries}/{max_retries}), retrying in {current_delay}s: {e}")
                    time.sleep(current_delay)
                    current_delay *= 2  # Exponential backoff
            
        return wrapper
    return decorator


def update_job_status(
    job_id: str,
    status: str,
    error_message: Optional[str] = None
) -> bool:
    """
    Update scan job status in database
    
    Args:
        job_id: Job UUID
        status: New status (pending, processing, completed, failed)
        error_message: Optional error message
    
    Returns:
        True if updated successfully
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if status == "processing":
            query = """
                UPDATE scan_jobs 
                SET status = %s, started_at = NOW()
                WHERE id = %s
            """
            cursor.execute(query, (status, job_id))
        elif status in ["completed", "failed"]:
            query = """
                UPDATE scan_jobs 
                SET status = %s, completed_at = NOW(), error_message = %s
                WHERE id = %s
            """
            cursor.execute(query, (status, error_message, job_id))
        else:
            query = """
                UPDATE scan_jobs 
                SET status = %s
                WHERE id = %s
            """
            cursor.execute(query, (status, job_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Updated job {job_id} status to: {status}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update job status: {e}")
        return False


def save_threat(threat_data: Dict[str, Any]) -> Optional[str]:
    """
    Save detected threat to database
    
    Args:
        threat_data: Dictionary containing threat information
    
    Returns:
        Threat ID if saved successfully, None otherwise
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            INSERT INTO threats (
                job_id, original_domain, malicious_domain, 
                threat_type, severity, ip_address, nameservers,
                whois_data, discovered_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, NOW()
            ) RETURNING id
        """
        
        cursor.execute(query, (
            threat_data.get("job_id"),
            threat_data.get("original_domain"),
            threat_data.get("malicious_domain"),
            threat_data.get("threat_type", "typosquat"),
            threat_data.get("severity", "medium"),
            threat_data.get("ip_address"),
            threat_data.get("nameservers", []),
            threat_data.get("whois_data")
        ))
        
        threat_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Saved threat: {threat_data.get('malicious_domain')}")
        return str(threat_id)
        
    except Exception as e:
        logger.error(f"Failed to save threat: {e}")
        return None


def save_leak(leak_data: Dict[str, Any]) -> Optional[str]:
    """
    Save detected leak to database
    
    Args:
        leak_data: Dictionary containing leak information
    
    Returns:
        Leak ID if saved successfully, None otherwise
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            INSERT INTO github_leaks (
                job_id, domain, repository_url, repository_name,
                file_path, snippet, leak_type, severity, discovered_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, NOW()
            ) RETURNING id
        """
        
        cursor.execute(query, (
            leak_data.get("job_id"),
            leak_data.get("domain"),
            leak_data.get("repository_url"),
            leak_data.get("repository_name"),
            leak_data.get("file_path"),
            leak_data.get("snippet"),
            leak_data.get("leak_type", "unknown"),
            leak_data.get("severity", "high")
        ))
        
        leak_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Saved leak: {leak_data.get('repository_url')}")
        return str(leak_id)
        
    except Exception as e:
        logger.error(f"Failed to save leak: {e}")
        return None


# Configure logging for workers
logger.add("logs/workers.log", rotation="500 MB", retention="10 days", level="INFO")
