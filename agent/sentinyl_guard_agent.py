"""
Sentinyl Guard Agent
Host-based behavioral anomaly detection with Dead Man's Switch

This agent monitors VPS instances for:
- Geo-anomalies (connections to hostile countries)
- Process anomalies (reverse shells, suspicious spawns)
- Resource anomalies (crypto-mining signatures)

When an anomaly is detected, it sends an alert to Sentinyl SaaS and starts
a 5-minute countdown. If admin doesn't mark as safe, it auto-blocks the connection.
"""
import psutil
import requests
import time
import subprocess
import socket
import platform
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

# Configuration
API_BASE_URL = "http://localhost:8000"  # Override with --api-url flag
AGENT_ID = str(uuid.uuid4())  # Override with --agent-id flag
POLL_INTERVAL = 30  # seconds
STATUS_CHECK_INTERVAL = 15  # seconds (how often to check for admin override)
COUNTDOWN_DURATION = 300  # seconds (5 minutes)

# Geo-anomaly high-risk countries (can be customized)
HIGH_RISK_COUNTRIES = [
    "Russia", "China", "North Korea", "Iran", 
    "Belarus", "Syria", "Venezuela"
]

# Trusted IPs/subnets (whitelist - connections to these are always safe)
TRUSTED_IPS = [
    "8.8.8.8",  # Google DNS
    "1.1.1.1",  # Cloudflare DNS
    # Add your trusted service IPs here
]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - Sentinyl Guard - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/sentinyl-guard.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BehavioralSensor:
    """Monitors system for behavioral anomalies"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.hostname = socket.gethostname()
        self.baseline_cpu = self._get_baseline_cpu()
        
    def _get_baseline_cpu(self) -> float:
        """Calculate baseline CPU usage"""
        cpu_samples = []
        for _ in range(5):
            cpu_samples.append(psutil.cpu_percent(interval=1))
        return sum(cpu_samples) / len(cpu_samples)
    
    def detect_geo_anomaly(self) -> Optional[Dict[str, Any]]:
        """
        Detect connections to high-risk geographic locations
        
        Returns anomaly details if suspicious connection found
        """
        try:
            connections = psutil.net_connections(kind='inet')
            
            for conn in connections:
                # Skip if not established
                if conn.status != psutil.CONN_ESTABLISHED:
                    continue
                
                # Skip if no remote address
                if not conn.raddr:
                    continue
                
                remote_ip = conn.raddr.ip
                
                # Skip trusted IPs
                if remote_ip in TRUSTED_IPS or remote_ip.startswith("127."):
                    continue
                
                # Lookup geo location using ipinfo.io
                country = self._lookup_country(remote_ip)
                
                if country in HIGH_RISK_COUNTRIES:
                    logger.warning(f"Geo-anomaly detected: Connection to {remote_ip} ({country})")
                    return {
                        "anomaly_type": "geo",
                        "severity": "critical",
                        "target_ip": remote_ip,
                        "target_country": country,
                        "details": {
                            "local_port": conn.laddr.port if conn.laddr else "N/A",
                            "remote_port": conn.raddr.port,
                            "connection_status": conn.status,
                            "pid": conn.pid
                        }
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting geo anomalies: {str(e)}")
            return None
    
    def detect_process_anomaly(self) -> Optional[Dict[str, Any]]:
        """
        Detect suspicious process execution patterns (reverse shells)
        
        Checks if web server processes (node, python, nginx) spawn shells
        """
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    proc_name = proc_info['name']
                    cmdline = ' '.join(proc_info['cmdline']) if proc_info['cmdline'] else ''
                    
                    # Check if web server process
                    web_processes = ['node', 'python', 'python3', 'nginx', 'apache2', 'httpd']
                    if proc_name not in web_processes:
                        continue
                    
                    # Get child processes
                    try:
                        children = proc.children(recursive=True)
                    except psutil.NoSuchProcess:
                        continue
                    
                    # Check if any child is a shell
                    shells = ['bash', 'sh', 'zsh', 'dash', 'ksh']
                    for child in children:
                        try:
                            child_name = child.name()
                            if child_name in shells:
                                logger.warning(
                                    f"Process anomaly detected: {proc_name} spawned {child_name}"
                                )
                                return {
                                    "anomaly_type": "process",
                                    "severity": "critical",
                                    "process_name": f"{proc_name} -> {child_name}",
                                    "details": {
                                        "parent_pid": proc.pid,
                                        "parent_cmdline": cmdline,
                                        "child_pid": child.pid,
                                        "child_name": child_name
                                    }
                                }
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting process anomalies: {str(e)}")
            return None
    
    def detect_resource_anomaly(self) -> Optional[Dict[str, Any]]:
        """
        Detect abnormal resource consumption (crypto-mining)
        
        Checks for sustained high CPU usage
        """
        try:
            current_cpu = psutil.cpu_percent(interval=2)
            current_mem = psutil.virtual_memory().percent
            
            # Crypto-mining typically causes sustained 90%+ CPU
            if current_cpu > 90 and current_cpu > self.baseline_cpu + 40:
                logger.warning(
                    f"Resource anomaly detected: CPU at {current_cpu}% "
                    f"(baseline: {self.baseline_cpu}%)"
                )
                
                # Get top CPU process
                top_process = max(
                    psutil.process_iter(['pid', 'name', 'cpu_percent']),
                    key=lambda p: p.info['cpu_percent'] or 0
                )
                
                return {
                    "anomaly_type": "resource",
                    "severity": "high",
                    "process_name": top_process.info['name'],
                    "details": {
                        "cpu_percent": current_cpu,
                        "mem_percent": current_mem,
                        "baseline_cpu": self.baseline_cpu,
                        "top_process_pid": top_process.info['pid'],
                        "top_process_cpu": top_process.info['cpu_percent']
                    }
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting resource anomalies: {str(e)}")
            return None
    
    def _lookup_country(self, ip_address: str) -> str:
        """Lookup country for IP address using ipinfo.io"""
        try:
            response = requests.get(
                f"https://ipinfo.io/{ip_address}/json",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('country', 'Unknown')
            return "Unknown"
        except Exception as e:
            logger.error(f"Error looking up IP {ip_address}: {str(e)}")
            return "Unknown"


class DeadManSwitch:
    """Countdown timer with auto-blocking logic"""
    
    def __init__(self, api_base_url: str, agent_id: str):
        self.api_base_url = api_base_url
        self.agent_id = agent_id
        self.active_events: Dict[str, Dict[str, Any]] = {}
    
    def send_alert(self, anomaly: Dict[str, Any]) -> Optional[str]:
        """
        Send alert to Sentinyl SaaS API
        
        Returns event_id if successful
        """
        try:
            payload = {
                "agent_id": self.agent_id,
                "hostname": socket.gethostname(),
                "anomaly_type": anomaly["anomaly_type"],
                "severity": anomaly["severity"],
                "target_ip": anomaly.get("target_ip"),
                "target_country": anomaly.get("target_country"),
                "process_name": anomaly.get("process_name"),
                "details": anomaly.get("details", {})
            }
            
            response = requests.post(
                f"{self.api_base_url}/guard/alert",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 202:
                data = response.json()
                event_id = data["event_id"]
                logger.info(f"Alert sent successfully. Event ID: {event_id}")
                
                # Track event locally with expiration time
                self.active_events[event_id] = {
                    "anomaly": anomaly,
                    "expires_at": datetime.now() + timedelta(seconds=COUNTDOWN_DURATION),
                    "checked_at": datetime.now()
                }
                
                return event_id
            else:
                logger.error(f"Failed to send alert: {response.status_code} {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error sending alert: {str(e)}")
            return None
    
    def check_for_override(self) -> None:
        """
        Poll API for admin override commands
        
        Checks if admin marked any alerts as safe or commanded block
        """
        try:
            response = requests.get(
                f"{self.api_base_url}/guard/status/{self.agent_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                events = data.get("events", [])
                
                for event in events:
                    event_id = event["event_id"]
                    admin_response = event.get("admin_response")
                    should_block = event.get("should_block", False)
                    countdown_remaining = event.get("countdown_remaining", 0)
                    
                    if event_id not in self.active_events:
                        continue
                    
                    anomaly = self.active_events[event_id]["anomaly"]
                    
                    if admin_response == "safe":
                        logger.info(f"Event {event_id} marked as SAFE by admin - no action taken")
                        del self.active_events[event_id]
                    
                    elif should_block:
                        logger.warning(
                            f"Event {event_id} requires BLOCK - executing iptables rule"
                        )
                        self.execute_block(anomaly)
                        del self.active_events[event_id]
                    
                    elif countdown_remaining > 0:
                        logger.info(
                            f"Event {event_id} countdown: {countdown_remaining}s remaining"
                        )
            
            # Clean up expired events
            now = datetime.now()
            expired = [
                eid for eid, data in self.active_events.items()
                if data["expires_at"] < now
            ]
            for eid in expired:
                del self.active_events[eid]
                
        except Exception as e:
            logger.error(f"Error checking for override: {str(e)}")
    
    def execute_block(self, anomaly: Dict[str, Any]) -> None:
        """
        Execute iptables block for suspicious connection
        
        IMPORTANT: This blocks ONLY the suspicious remote IP (e.g., the C2 server in Russia).
        Your SSH access, monitoring tools, and legitimate connections are NOT affected.
        
        Example: If anomaly detected connection to 185.220.101.1 (Russia),
        we block that IP only. Your SSH from 203.0.113.50 remains active.
        """
        target_ip = anomaly.get("target_ip")
        
        if not target_ip:
            logger.error("Cannot block: no target IP specified")
            return
        
        # Safety check: Log what we're about to block
        logger.info(f"Preparing to block suspicious IP: {target_ip}")
        logger.info(f"Admin connections and whitelisted IPs are NOT affected")
        
        try:
            # Add iptables rules to block both INPUT and OUTPUT
            # These rules ONLY affect the specific suspicious IP
            commands = [
                f"iptables -A INPUT -s {target_ip} -j DROP",
                f"iptables -A OUTPUT -d {target_ip} -j DROP"
            ]
            
            for cmd in commands:
                result = subprocess.run(
                    cmd.split(),
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    logger.info(f"Executed: {cmd}")
                else:
                    logger.error(f"Failed to execute {cmd}: {result.stderr}")
            
            logger.warning(f"🛡️ BLOCKED: {target_ip} - Suspicious connection severed")
            logger.info("Your admin SSH connection remains active")
            
        except Exception as e:
            logger.error(f"Error executing block: {str(e)}")


def main():
    """Main agent loop"""
    logger.info("="*60)
    logger.info("Sentinyl Guard Agent Starting")
    logger.info(f"Agent ID: {AGENT_ID}")
    logger.info(f"Hostname: {socket.gethostname()}")
    logger.info(f"OS: {platform.system()} {platform.release()}")
    logger.info(f"API: {API_BASE_URL}")
    logger.info("="*60)
    
    sensor = BehavioralSensor(AGENT_ID)
    dead_man_switch = DeadManSwitch(API_BASE_URL, AGENT_ID)
    
    last_status_check = datetime.now()
    
    while True:
        try:
            # Scan for anomalies
            logger.debug("Performing behavioral scan...")
            
            # Check for geo anomalies
            geo_anomaly = sensor.detect_geo_anomaly()
            if geo_anomaly:
                dead_man_switch.send_alert(geo_anomaly)
            
            # Check for process anomalies
            process_anomaly = sensor.detect_process_anomaly()
            if process_anomaly:
                dead_man_switch.send_alert(process_anomaly)
            
            # Check for resource anomalies
            resource_anomaly = sensor.detect_resource_anomaly()
            if resource_anomaly:
                dead_man_switch.send_alert(resource_anomaly)
            
            # Check for admin override commands
            if (datetime.now() - last_status_check).total_seconds() >= STATUS_CHECK_INTERVAL:
                dead_man_switch.check_for_override()
                last_status_check = datetime.now()
            
            # Sleep before next scan
            time.sleep(POLL_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("Agent shutdown requested")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {str(e)}")
            time.sleep(10)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Sentinyl Guard Agent")
    parser.add_argument("--api-url", default=API_BASE_URL, help="Sentinyl API base URL")
    parser.add_argument("--agent-id", default=AGENT_ID, help="Unique agent identifier")
    parser.add_argument("--poll-interval", type=int, default=POLL_INTERVAL, help="Scan interval (seconds)")
    
    args = parser.parse_args()
    
    API_BASE_URL = args.api_url
    AGENT_ID = args.agent_id
    POLL_INTERVAL = args.poll_interval
    
    main()
