"""
Sentinyl Guard Alert Worker
Processes behavioral anomaly alerts from VPS agents and sends enriched notifications
"""
import redis
import json
import time
from datetime import datetime
from loguru import logger
from sqlalchemy.orm import Session
from typing import Dict, Any

from backend.database import SessionLocal
from backend.models import GuardEvent
from workers.smart_alert import SmartAlert

# Configure logging
logger.add("logs/guard_worker.log", rotation="500 MB", retention="10 days", level="INFO")

# Redis connection
REDIS_URL = "redis://redis:6379/0"
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

QUEUE_NAME = "queue:guard"
POLL_INTERVAL = 2  # seconds


def process_guard_alert(job_data: Dict[str, Any], db: Session) -> None:
    """
    Process guard alert and send enriched notification
    
    Args:
        job_data: Alert payload from Redis queue
        db: Database session
    """
    event_id = job_data.get("event_id")
    agent_id = job_data.get("agent_id")
    hostname = job_data.get("hostname")
    anomaly_type = job_data.get("anomaly_type")
    severity = job_data.get("severity")
    target_ip = job_data.get("target_ip")
    target_country = job_data.get("target_country", "Unknown")
    process_name = job_data.get("process_name")
    details = job_data.get("details", {})
    countdown_expires_at = job_data.get("countdown_expires_at")
    
    logger.info(f"Processing guard alert {event_id}: {anomaly_type} from {hostname}")
    
    try:
        # Calculate countdown remaining
        if countdown_expires_at:
            expires = datetime.fromisoformat(countdown_expires_at)
            countdown_remaining = int((expires - datetime.utcnow()).total_seconds())
            countdown_remaining = max(0, countdown_remaining)
        else:
            countdown_remaining = 300  # Default 5 minutes
        
        # Initialize smart alert system
        alert_system = SmartAlert(
            enable_graph=False,  # Graph not needed for guard alerts
            enable_slack=True,
            enable_teams=True
        )
        
        # Build notification details based on anomaly type
        if anomaly_type == "geo":
            title = f"🌍 Geo-Anomaly Detected: {hostname}"
            description = (
                f"**VPS Instance**: `{hostname}`\n"
                f"**Target IP**: `{target_ip}`\n"
                f"**Country**: {target_country}\n"
                f"**Severity**: {severity.upper()}\n\n"
                f"A connection to an unusual geographic location has been detected. "
                f"This may indicate C2 beacon activity or data exfiltration."
            )
            mitre_technique = "T1071.001"  # Application Layer Protocol: Web Protocols
            
        elif anomaly_type == "process":
            title = f"⚠️ Process Anomaly Detected: {hostname}"
            description = (
                f"**VPS Instance**: `{hostname}`\n"
                f"**Process**: `{process_name}`\n"
                f"**Severity**: {severity.upper()}\n\n"
                f"A suspicious process execution pattern has been detected. "
                f"This may indicate reverse shell or RCE exploitation."
            )
            mitre_technique = "T1059"  # Command and Scripting Interpreter
            
        elif anomaly_type == "resource":
            title = f"💻 Resource Anomaly Detected: {hostname}"
            cpu_usage = details.get("cpu_percent", "N/A")
            mem_usage = details.get("mem_percent", "N/A")
            description = (
                f"**VPS Instance**: `{hostname}`\n"
                f"**CPU Usage**: {cpu_usage}%\n"
                f"**Memory Usage**: {mem_usage}%\n"
                f"**Severity**: {severity.upper()}\n\n"
                f"Abnormal resource consumption has been detected. "
                f"This may indicate crypto-mining malware."
            )
            mitre_technique = "T1496"  # Resource Hijacking
            
        else:
            title = f"🔔 Anomaly Detected: {hostname}"
            description = f"**VPS Instance**: `{hostname}`\n**Type**: {anomaly_type}\n**Severity**: {severity.upper()}"
            mitre_technique = "T1071"  # Application Layer Protocol
        
        # Add countdown timer to description
        minutes = countdown_remaining // 60
        seconds = countdown_remaining % 60
        description += f"\n\n⏱️ **Dead Man's Switch**: Auto-block in **{minutes}:{seconds:02d}** unless marked safe"
        
        # Build enriched alert
        alert_details = {
            "event_id": event_id,
            "agent_id": agent_id,
            "hostname": hostname,
            "anomaly_type": anomaly_type,
            "target_ip": target_ip or "N/A",
            "target_country": target_country,
            "process_name": process_name or "N/A",
            "countdown_remaining": f"{minutes}:{seconds:02d}",
            "details": details
        }
        
        mitre_context = {
            "technique_id": mitre_technique,
            "technique_name": get_mitre_name(mitre_technique),
            "tactic": get_mitre_tactic(mitre_technique)
        }
        
        # Calculate risk score (always HIGH for guard alerts)
        risk_score = 85 if severity == "critical" else 75
        
        # Build action buttons for Teams/Slack
        action_buttons = [
            {
                "label": "✅ MARK AS SAFE",
                "action": "safe",
                "style": "positive",
                "url": f"http://localhost:8000/guard/response",  # Will be webhook callback
                "payload": {"event_id": event_id, "response": "safe"}
            },
            {
                "label": "🛑 CONFIRM BLOCK",
                "action": "block",
                "style": "destructive",
                "url": f"http://localhost:8000/guard/response",
                "payload": {"event_id": event_id, "response": "block"}
            }
        ]
        
        # Send multi-channel alert
        alert_system._send_multi_channel_alert(
            title=title,
            severity=severity,
            risk_score=risk_score,
            mitre_context=mitre_context,
            details=alert_details,
            action_buttons=action_buttons
        )
        
        logger.info(f"Successfully sent guard alert for event {event_id}")
        alert_system.close()
        
    except Exception as e:
        logger.error(f"Error processing guard alert {event_id}: {str(e)}")
        raise


def get_mitre_name(technique_id: str) -> str:
    """Get MITRE technique name from ID"""
    mitre_names = {
        "T1071": "Application Layer Protocol",
        "T1071.001": "Application Layer Protocol: Web Protocols",
        "T1059": "Command and Scripting Interpreter",
        "T1496": "Resource Hijacking"
    }
    return mitre_names.get(technique_id, technique_id)


def get_mitre_tactic(technique_id: str) -> str:
    """Get MITRE tactic from technique ID"""
    mitre_tactics = {
        "T1071": "Command and Control",
        "T1071.001": "Command and Control",
        "T1059": "Execution",
        "T1496": "Impact"
    }
    return mitre_tactics.get(technique_id, "Unknown")


def main():
    """Main worker loop"""
    logger.info("Starting Sentinyl Guard Alert Worker")
    logger.info(f"Listening on queue: {QUEUE_NAME}")
    
    while True:
        try:
            # Block and wait for job
            _, job_data_str = redis_client.brpop(QUEUE_NAME, timeout=POLL_INTERVAL)
            
            if job_data_str:
                job_data = json.loads(job_data_str)
                logger.info(f"Received guard alert job: {job_data.get('event_id')}")
                
                # Process with database session
                db = SessionLocal()
                try:
                    process_guard_alert(job_data, db)
                except Exception as e:
                    logger.error(f"Job processing failed: {str(e)}")
                finally:
                    db.close()
        
        except redis.exceptions.ConnectionError:
            logger.error("Redis connection lost, retrying...")
            time.sleep(5)
        except KeyboardInterrupt:
            logger.info("Worker shutdown requested")
            break
        except Exception as e:
            logger.error(f"Unexpected error in worker loop: {str(e)}")
            time.sleep(5)


if __name__ == "__main__":
    main()
