"""
Microsoft Teams Notifier for Sentinyl Enterprise
Sends Adaptive Cards to Teams channels
"""
from typing import Dict, Any, Optional, List
from loguru import logger
import requests
import os


class TeamsNotifier:
    """
    Microsoft Teams notification handler using Adaptive Cards
    
    Sends rich, interactive alerts with risk scores, MITRE techniques,
    and action buttons
    """
    
    # Color codes by severity
    COLORS = {
        "CRITICAL": "FF0000",  # Red
        "HIGH": "FF6600",      # Orange
        "MEDIUM": "FFD700",    # Yellow/Gold
        "LOW": "00FF00"        # Green
    }
    
    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialize Teams notifier
        
        Args:
            webhook_url: Teams incoming webhook URL
        """
        self.webhook_url = webhook_url or os.getenv("TEAMS_WEBHOOK_URL")
        
        if not self.webhook_url:
            logger.warning("Teams webhook URL not configured")
    
    def is_configured(self) -> bool:
        """Check if webhook is configured"""
        return self.webhook_url is not None
    
    def send_alert(
        self,
        title: str,
        severity: str,
        risk_score: int,
        mitre_technique: Optional[Dict[str, Any]],
        details: Dict[str, Any],
        action_buttons: Optional[List[Dict[str, str]]] = None
    ) -> bool:
        """
        Send adaptive card alert to Teams
        
        Args:
            title: Alert title
            severity: CRITICAL, HIGH, MEDIUM, LOW
            risk_score: 0-100 risk score
            mitre_technique: MITRE ATT&CK context
            details: Additional alert details
            action_buttons: Optional action buttons
            
        Returns:
            True if sent successfully
        """
        if not self.is_configured():
            logger.warning("Teams not configured - skipping alert")
            return False
        
        try:
            card = self._build_adaptive_card(
                title, severity, risk_score,
                mitre_technique, details, action_buttons
            )
            
            response = requests.post(
                self.webhook_url,
                json=card,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            
            logger.info(f"Teams alert sent: {title} ({severity})")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Teams alert: {e}")
            return False
    
    def _build_adaptive_card(
        self,
        title: str,
        severity: str,
        risk_score: int,
        mitre_technique: Optional[Dict[str, Any]],
        details: Dict[str, Any],
        action_buttons: Optional[List[Dict[str, str]]]
    ) -> Dict[str, Any]:
        """Build Adaptive Card JSON structure"""
        
        color = self.COLORS.get(severity, self.COLORS["MEDIUM"])
        
        # Build card facts
        facts = [
            {"title": "Severity", "value": f"**{severity}**"},
            {"title": "Risk Score", "value": f"{risk_score}/100"}
        ]
        
        # Add detail facts
        for key, value in details.items():
            if key not in ["mitre", "action_buttons"]:
                facts.append({
                    "title": key.replace("_", " ").title(),
                    "value": str(value)
                })
        
        # Build card sections
        sections = [{
            "activityTitle": f"🛡️ {title}",
            "activitySubtitle": f"Sentinyl Security Alert",
            "facts": facts
        }]
        
        # Add MITRE section if available
        if mitre_technique:
            mitre_section = {
                "activityTitle": "🎯 MITRE ATT&CK Mapping",
                "facts": [
                    {
                        "title": "Technique ID",
                        "value": f"[{mitre_technique['technique_id']}]({mitre_technique.get('mitre_url', '')})"
                    },
                    {
                        "title": "Technique Name",
                        "value": mitre_technique['technique_name']
                    },
                    {
                        "title": "Tactics",
                        "value": ", ".join(mitre_technique['tactics'])
                    }
                ]
            }
            sections.append(mitre_section)
        
        # Build action buttons
        potential_actions = []
        if action_buttons:
            for button in action_buttons:
                potential_actions.append({
                    "@type": "OpenUri",
                    "name": button["text"],
                    "targets": [{
                        "os": "default",
                        "uri": button["url"]
                    }]
                })
        else:
            # Default actions
            potential_actions = [
                {
                    "@type": "OpenUri",
                    "name": "🔍 View in Graph",
                    "targets": [{
                        "os": "default",
                        "uri": "http://localhost:7474"
                    }]
                },
                {
                    "@type": "OpenUri",
                    "name": "📊 View Dashboard",
                    "targets": [{
                        "os": "default",
                        "uri": "http://localhost:8000"
                    }]
                }
            ]
        
        # Construct message card
        card = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": title,
            "themeColor": color,
            "sections": sections,
            "potentialAction": potential_actions
        }
        
        return card
    
    def send_summary(
        self,
        domain: str,
        scan_type: str,
        total_threats: int,
        critical_threats: int,
        scan_duration: Optional[float] = None
    ) -> bool:
        """
        Send scan summary card
        
        Args:
            domain: Scanned domain
            scan_type: Type of scan
            total_threats: Total threats found
            critical_threats: Number of critical threats
            scan_duration: Scan duration in seconds
            
        Returns:
            True if sent successfully
        """
        if not self.is_configured():
            return False
        
        try:
            severity = "CRITICAL" if critical_threats > 0 else "MEDIUM" if total_threats > 0 else "LOW"
            
            details = {
                "Domain": domain,
                "Scan Type": scan_type.title(),
                "Total Threats": str(total_threats),
                "Critical Threats": str(critical_threats)
            }
            
            if scan_duration:
                details["Duration"] = f"{scan_duration:.1f}s"
            
            return self.send_alert(
                title="Scan Complete",
                severity=severity,
                risk_score=0,  # Summary doesn't have risk score
                mitre_technique=None,
                details=details,
                action_buttons=None
            )
            
        except Exception as e:
            logger.error(f"Failed to send summary: {e}")
            return False
