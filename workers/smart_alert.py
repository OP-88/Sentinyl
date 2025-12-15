"""
Smart Alert System for Sentinyl Enterprise
Enriches alerts with risk scores, MITRE mapping, and graph context
"""
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

# Import core enterprise components
from core.risk_engine import RiskScorer, Finding, Severity
from core.mitre_mapper import MITREMapper
from core.graph_manager import GraphManager

# Import notification systems
from workers.slack_utils import SlackNotifier
from workers.teams_notifier import TeamsNotifier


class SmartAlert:
    """
    Intelligence-enriched alert system
    
    Combines:
    - Risk scoring
    - MITRE ATT&CK mapping
    - Graph database integration
    - Multi-channel notifications (Slack + Teams)
    """
    
    def __init__(
        self,
        enable_graph: bool = True,
        enable_slack: bool = True,
        enable_teams: bool = True
    ):
        """
        Initialize smart alert system
        
        Args:
            enable_graph: Enable graph database ingestion
            enable_slack: Enable Slack notifications
            enable_teams: Enable Teams notifications
        """
        self.risk_scorer = RiskScorer()
        self.mitre_mapper = MITREMapper()
        
        # Initialize graph manager
        self.graph = None
        if enable_graph:
            try:
                self.graph = GraphManager()
                if not self.graph.is_available():
                    logger.warning("Graph database unavailable - graph features disabled")
                    self.graph = None
            except Exception as e:
                logger.error(f"Failed to initialize graph: {e}")
                self.graph = None
        
        # Initialize notifiers
        self.slack = SlackNotifier() if enable_slack else None
        self.teams = TeamsNotifier() if enable_teams else None
    
    def process_typosquat_finding(
        self,
        domain: str,
        malicious_domain: str,
        ip_address: str,
        nameservers: list,
        visibility: str = "public",
        asset_value: str = "production"
    ) -> Dict[str, Any]:
        """
        Process typosquatting finding with full intelligence enrichment
        
        Args:
            domain: Original domain
            malicious_domain: Typosquatted domain
            ip_address: Resolved IP address
            nameservers: List of nameservers
            visibility: public/private
            asset_value: production/staging/development
            
        Returns:
            Enriched finding data
        """
        logger.info(f"Processing typosquat: {malicious_domain}")
        
        # 1. Calculate risk score
        finding = Finding(
            finding_type="typosquat",
            visibility=visibility,
            discovered_at=datetime.utcnow(),
            asset_value=asset_value,
            metadata={
                "original_domain": domain,
                "malicious_domain": malicious_domain,
                "ip_address": ip_address
            }
        )
        
        risk_assessment = self.risk_scorer.calculate_risk(finding)
        
        # 2. Map to MITRE
        mitre_context = self.mitre_mapper.generate_alert_context(
            "typosquat",
            context={"domain": malicious_domain}
        )
        
        # 3. Ingest to graph
        if self.graph and self.graph.is_available():
            self._ingest_typosquat_to_graph(
                domain, malicious_domain, ip_address, nameservers
            )
        
        # 4. Send alerts (only for MEDIUM+ severity)
        if risk_assessment.severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM]:
            self._send_multi_channel_alert(
                title=f"Typosquatting Detected: {malicious_domain}",
                severity=risk_assessment.severity.value,
                risk_score=risk_assessment.score,
                mitre_context=mitre_context,
                details={
                    "Original Domain": domain,
                    "Malicious Domain": malicious_domain,
                    "IP Address": ip_address,
                    "Nameservers": ", ".join(nameservers[:3]) if nameservers else "None",
                    "Risk Reasoning": risk_assessment.reasoning
                }
            )
        
        return {
            "finding_type": "typosquat",
            "risk_assessment": risk_assessment,
            "mitre_context": mitre_context,
            "alerted": risk_assessment.severity != Severity.LOW
        }
    
    def process_leak_finding(
        self,
        domain: str,
        repository_name: str,
        repository_url: str,
        file_path: str,
        leak_type: str,
        snippet: str,
        visibility: str = "public",
        asset_value: str = "production"
    ) -> Dict[str, Any]:
        """
        Process GitHub leak finding with full intelligence enrichment
        
        Args:
            domain: Target domain
            repository_name: Repository full name
            repository_url: Repository URL
            file_path: Path to file with leak
            leak_type: Type of leak (password, api_key, etc.)
            snippet: Code snippet
            visibility: public/private
            asset_value: production/staging/development
            
        Returns:
            Enriched finding data
        """
        logger.info(f"Processing leak: {leak_type} in {repository_name}")
        
        # 1. Calculate risk score
        finding = Finding(
            finding_type="leak",
            visibility=visibility,
            discovered_at=datetime.utcnow(),
            asset_value=asset_value,
            metadata={
                "domain": domain,
                "repository": repository_name,
                "leak_type": leak_type,
                "file_path": file_path
            }
        )
        
        risk_assessment = self.risk_scorer.calculate_risk(finding)
        
        # 2. Map to MITRE
        mitre_context = self.mitre_mapper.generate_alert_context(
            leak_type,
            context={"file_path": file_path, "repository": repository_name}
        )
        
        # 3. Ingest to graph
        if self.graph and self.graph.is_available():
            self._ingest_leak_to_graph(
                domain, repository_name, repository_url, leak_type, file_path
            )
        
        # 4. Send alerts (only for MEDIUM+ severity)
        if risk_assessment.severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM]:
            action_buttons = [
                {"text": "🔍 View Repository", "url": repository_url},
                {"text": "📊 View Dashboard", "url": "http://localhost:8000"}
            ]
            
            self._send_multi_channel_alert(
                title=f"Credential Leak Detected: {leak_type}",
                severity=risk_assessment.severity.value,
                risk_score=risk_assessment.score,
                mitre_context=mitre_context,
                details={
                    "Domain": domain,
                    "Repository": repository_name,
                    "Leak Type": leak_type,
                    "File Path": file_path,
                    "Snippet": snippet[:100] + "..." if len(snippet) > 100 else snippet,
                    "Risk Reasoning": risk_assessment.reasoning
                },
                action_buttons=action_buttons
            )
        
        return {
            "finding_type": "leak",
            "risk_assessment": risk_assessment,
            "mitre_context": mitre_context,
            "alerted": risk_assessment.severity != Severity.LOW
        }
    
    def _ingest_typosquat_to_graph(
        self,
        original_domain: str,
        malicious_domain: str,
        ip_address: str,
        nameservers: list
    ):
        """Ingest typosquatting finding into graph database"""
        try:
            # Create domain node and IP node with relationship
            relations = [
                ("RESOLVES_TO", "IP_Address", {
                    "id": ip_address,
                    "discovered_at": datetime.utcnow().isoformat()
                })
            ]
            
            # Add nameserver relations
            for ns in nameservers[:5]:  # Limit to 5
                relations.append(
                    ("HAS_NAMESERVER", "Nameserver", {
                        "id": ns,
                        "nameserver": ns
                    })
                )
            
            self.graph.ingest_finding(
                entity_type="Domain",
                properties={
                    "id": malicious_domain,
                    "domain": malicious_domain,
                    "is_malicious": True,
                    "typosquat_of": original_domain,
                    "discovered_at": datetime.utcnow().isoformat()
                },
                relations=relations
            )
            
            logger.info(f"Ingested typosquat to graph: {malicious_domain}")
            
        except Exception as e:
            logger.error(f"Failed to ingest typosquat to graph: {e}")
    
    def _ingest_leak_to_graph(
        self,
        domain: str,
        repository_name: str,
        repository_url: str,
        leak_type: str,
        file_path: str
    ):
        """Ingest leak finding into graph database"""
        try:
            # Create repository node with exposes secret relationship
            self.graph.ingest_finding(
                entity_type="Repository",
                properties={
                    "id": repository_url,
                    "name": repository_name,
                    "url": repository_url,
                    "discovered_at": datetime.utcnow().isoformat()
                },
                relations=[
                    ("EXPOSES", "Secret", {
                        "id": f"{repository_url}:{file_path}",
                        "type": leak_type,
                        "file_path": file_path,
                        "target_domain": domain
                    })
                ]
            )
            
            logger.info(f"Ingested leak to graph: {repository_name}")
            
        except Exception as e:
            logger.error(f"Failed to ingest leak to graph: {e}")
    
    def _send_multi_channel_alert(
        self,
        title: str,
        severity: str,
        risk_score: int,
        mitre_context: Dict[str, Any],
        details: Dict[str, Any],
        action_buttons: Optional[list] = None
    ):
        """Send alert to all configured channels"""
        
        # Send to Slack
        if self.slack:
            try:
                # Build Slack-specific details
                slack_details = details.copy()
                if mitre_context.get("mitre_mapped"):
                    slack_details["MITRE Technique"] = (
                        f"{mitre_context['technique_id']}: {mitre_context['technique_name']}"
                    )
                
                self.slack.send_alert(
                    domain=details.get("Domain", "Unknown"),
                    threat_type=title,
                    severity=severity,
                    details=slack_details
                )
            except Exception as e:
                logger.error(f"Failed to send Slack alert: {e}")
        
        # Send to Teams
        if self.teams and self.teams.is_configured():
            try:
                self.teams.send_alert(
                    title=title,
                    severity=severity,
                    risk_score=risk_score,
                    mitre_technique=mitre_context if mitre_context.get("mitre_mapped") else None,
                    details=details,
                    action_buttons=action_buttons
                )
            except Exception as e:
                logger.error(f"Failed to send Teams alert: {e}")
    
    def close(self):
        """Close connections"""
        if self.graph:
            self.graph.close()
