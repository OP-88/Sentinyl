"""
Slack notification integration for Sentinyl
Uses Slack Block Kit for rich, interactive alerts
"""
import requests
from typing import Optional, Dict, Any, List
from loguru import logger
import os


class SlackNotifier:
    """
    Slack webhook notifier using Block Kit format
    Sends rich, formatted alerts to Slack channels
    """
    
    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialize Slack notifier
        
        Args:
            webhook_url: Slack incoming webhook URL (optional, reads from env)
        """
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        
        if not self.webhook_url:
            logger.warning("SLACK_WEBHOOK_URL not configured - notifications will be skipped")
        else:
            logger.info("Slack notifier initialized")
    
    def send_alert(
        self,
        domain: str,
        threat_type: str,
        severity: str,
        details: Dict[str, Any]
    ) -> bool:
        """
        Send formatted alert to Slack using Block Kit
        
        Args:
            domain: Target domain being monitored
            threat_type: Type of threat (typosquat, leak, phishing)
            severity: Severity level (LOW, MEDIUM, HIGH, CRITICAL)
            details: Additional threat information
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.webhook_url:
            logger.warning("Slack webhook not configured, skipping alert")
            return False
        
        try:
            # Build Block Kit payload
            blocks = self._build_blocks(domain, threat_type, severity, details)
            
            payload = {
                "blocks": blocks
            }
            
            # Send to Slack
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            logger.info(f"Slack alert sent successfully: {threat_type} - {severity}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Slack alert: {e}")
            return False
    
    def _build_blocks(
        self,
        domain: str,
        threat_type: str,
        severity: str,
        details: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Build Slack Block Kit blocks for the alert
        
        Args:
            domain: Target domain
            threat_type: Type of threat
            severity: Severity level
            details: Additional details
        
        Returns:
            List of Block Kit blocks
        """
        # Emoji mapping for severity
        emoji_map = {
            "LOW": "ℹ️",
            "MEDIUM": "⚠️",
            "HIGH": "🚨",
            "CRITICAL": "🔴"
        }
        
        emoji = emoji_map.get(severity.upper(), "⚠️")
        
        # Color coding for severity
        color_map = {
            "LOW": "#36a64f",      # Green
            "MEDIUM": "#ff9900",    # Orange
            "HIGH": "#ff6600",      # Red-Orange
            "CRITICAL": "#cc0000"   # Red
        }
        
        blocks = []
        
        # Header block with emoji and title
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🛡️ Sentinyl Security Alert",
                "emoji": True
            }
        })
        
        # Main section with severity and target
        fields = [
            {
                "type": "mrkdwn",
                "text": f"*Severity:*\n{emoji} {severity.upper()}"
            },
            {
                "type": "mrkdwn",
                "text": f"*Target Domain:*\n`{domain}`"
            },
            {
                "type": "mrkdwn",
                "text": f"*Threat Type:*\n{threat_type.title()}"
            }
        ]
        
        # Add threat-specific fields
        if threat_type == "typosquat":
            malicious_domain = details.get("malicious_domain", "N/A")
            ip_address = details.get("ip_address", "N/A")
            
            fields.append({
                "type": "mrkdwn",
                "text": f"*Malicious Domain:*\n`{malicious_domain}`"
            })
            fields.append({
                "type": "mrkdwn",
                "text": f"*IP Address:*\n`{ip_address}`"
            })
        
        elif threat_type == "leak":
            repository = details.get("repository_name", "N/A")
            leak_type = details.get("leak_type", "N/A")
            
            fields.append({
                "type": "mrkdwn",
                "text": f"*Repository:*\n{repository}"
            })
            fields.append({
                "type": "mrkdwn",
                "text": f"*Leak Type:*\n{leak_type}"
            })
        
        blocks.append({
            "type": "section",
            "fields": fields
        })
        
        # Add divider
        blocks.append({
            "type": "divider"
        })
        
        # Add details section if available
        if threat_type == "typosquat" and details.get("nameservers"):
            nameservers = details.get("nameservers", [])
            ns_text = "\n".join([f"• {ns}" for ns in nameservers[:3]])
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Nameservers:*\n{ns_text}"
                }
            })
        
        elif threat_type == "leak" and details.get("repository_url"):
            repo_url = details.get("repository_url")
            file_path = details.get("file_path", "N/A")
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*File Path:*\n`{file_path}`"
                }
            })
        
        # Add action buttons for CRITICAL severity
        if severity.upper() == "CRITICAL":
            actions = {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "🔍 View Dashboard",
                            "emoji": True
                        },
                        "style": "danger",
                        "url": "http://localhost:3000"
                    }
                ]
            }
            
            # Add repository link for leaks
            if threat_type == "leak" and details.get("repository_url"):
                actions["elements"].append({
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📂 View Repository",
                        "emoji": True
                    },
                    "url": details.get("repository_url")
                })
            
            blocks.append(actions)
        
        # Footer with timestamp
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"🕐 Alert generated by Sentinyl DRP Platform"
                }
            ]
        })
        
        return blocks
    
    def send_summary(
        self,
        domain: str,
        scan_type: str,
        total_threats: int,
        critical_threats: int
    ) -> bool:
        """
        Send scan completion summary to Slack
        
        Args:
            domain: Scanned domain
            scan_type: Type of scan performed
            total_threats: Total threats found
            critical_threats: Number of critical threats
        
        Returns:
            True if sent successfully
        """
        if not self.webhook_url:
            return False
        
        try:
            emoji = "✅" if total_threats == 0 else "⚠️"
            
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} Scan Complete",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Domain:*\n`{domain}`"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Scan Type:*\n{scan_type.title()}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Total Threats:*\n{total_threats}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Critical:*\n{critical_threats}"
                        }
                    ]
                }
            ]
            
            payload = {"blocks": blocks}
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Slack summary sent for {domain}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Slack summary: {e}")
            return False
