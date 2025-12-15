"""
MITRE ATT&CK Framework Mapper for Sentinyl Enterprise
Maps security findings to MITRE ATT&CK techniques
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum
from loguru import logger


class Tactic(str, Enum):
    """MITRE ATT&CK Tactics"""
    RECONNAISSANCE = "Reconnaissance"
    RESOURCE_DEVELOPMENT = "Resource Development"
    INITIAL_ACCESS = "Initial Access"
    EXECUTION = "Execution"
    PERSISTENCE = "Persistence"
    PRIVILEGE_ESCALATION = "Privilege Escalation"
    DEFENSE_EVASION = "Defense Evasion"
    CREDENTIAL_ACCESS = "Credential Access"
    DISCOVERY = "Discovery"
    LATERAL_MOVEMENT = "Lateral Movement"
    COLLECTION = "Collection"
    COMMAND_AND_CONTROL = "Command and Control"
    EXFILTRATION = "Exfiltration"
    IMPACT = "Impact"


@dataclass
class MITRETechnique:
    """MITRE ATT&CK Technique"""
    technique_id: str  # e.g., T1552.001
    name: str
    tactics: List[Tactic]
    description: str
    detection: str
    mitigation: str


class MITREMapper:
    """
    Maps security findings to MITRE ATT&CK techniques
    
    Supported Techniques:
    - T1552.001: Unsecured Credentials: Credentials In Files
    - T1552.004: Unsecured Credentials: Private Keys
    - T1589.002: Gather Victim Identity Information: Email Addresses
    - T1594: Search Victim-Owned Websites
    - T1596.002: Search Open Technical Databases: WHOIS
    """
    
    # MITRE Technique Database
    TECHNIQUES = {
        "T1552.001": MITRETechnique(
            technique_id="T1552.001",
            name="Unsecured Credentials: Credentials In Files",
            tactics=[Tactic.CREDENTIAL_ACCESS],
            description="Adversaries may search local file systems and remote file shares for files containing insecurely stored credentials.",
            detection="Monitor for access to files and repositories that store credentials.",
            mitigation="Remove credentials from code repositories. Use secure credential storage."
        ),
        "T1552.004": MITRETechnique(
            technique_id="T1552.004",
            name="Unsecured Credentials: Private Keys",
            tactics=[Tactic.CREDENTIAL_ACCESS],
            description="Adversaries may search for private key certificate files on compromised systems.",
            detection="Monitor for access to private keys and SSH keys in repositories.",
            mitigation="Secure private keys with encryption and access controls."
        ),
        "T1589.002": MITRETechnique(
            technique_id="T1589.002",
            name="Gather Victim Identity Information: Email Addresses",
            tactics=[Tactic.RECONNAISSANCE],
            description="Adversaries may gather email addresses that can be used to target individuals.",
            detection="Monitor for suspicious WHOIS queries and data harvesting.",
            mitigation="Limit publicly available email addresses."
        ),
        "T1594": MITRETechnique(
            technique_id="T1594",
            name="Search Victim-Owned Websites",
            tactics=[Tactic.RECONNAISSANCE],
            description="Adversaries may search websites owned by the victim for information.",
            detection="Monitor for reconnaissance activity on company domains.",
            mitigation="Minimize information disclosure on public websites."
        ),
        "T1596.002": MITRETechnique(
            technique_id="T1596.002",
            name="Search Open Technical Databases: WHOIS",
            tactics=[Tactic.RECONNAISSANCE],
            description="Adversaries may search WHOIS data for information about victims.",
            detection="Monitor for unusual WHOIS query patterns.",
            mitigation="Consider WHOIS privacy protection services."
        ),
        "T1583.001": MITRETechnique(
            technique_id="T1583.001",
            name="Acquire Infrastructure: Domains",
            tactics=[Tactic.RESOURCE_DEVELOPMENT],
            description="Adversaries may acquire domains that can be used during targeting.",
            detection="Monitor for registration of domains similar to your brand.",
            mitigation="Proactive domain monitoring and takedowns."
        )
    }
    
    # Mapping rules: finding_type -> technique_id
    FINDING_MAPPINGS = {
        # Leak detection mappings
        "password": "T1552.001",
        "api_key": "T1552.001",
        "apikey": "T1552.001",
        "secret": "T1552.001",
        "secret_key": "T1552.001",
        "token": "T1552.001",
        "access_token": "T1552.001",
        "credentials": "T1552.001",
        "private_key": "T1552.004",
        "ssh_key": "T1552.004",
        "email": "T1589.002",
        
        # Domain-based mappings
        "typosquat": "T1583.001",
        "phishing_domain": "T1583.001",
        "brand_abuse": "T1583.001",
        
        # Reconnaissance mappings
        "whois_exposure": "T1596.002",
        "subdomain_enum": "T1594"
    }
    
    def map_finding_to_mitre(
        self,
        finding_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[MITRETechnique]:
        """
        Map a finding to MITRE ATT&CK technique
        
        Args:
            finding_type: Type of finding (password, api_key, typosquat, etc.)
            context: Additional context (file_path, repository, domain, etc.)
            
        Returns:
            MITRETechnique object or None if no mapping exists
        """
        finding_lower = finding_type.lower()
        
        # Check direct mapping
        technique_id = self.FINDING_MAPPINGS.get(finding_lower)
        
        # Context-based refinement
        if context and not technique_id:
            technique_id = self._map_from_context(finding_lower, context)
        
        if technique_id and technique_id in self.TECHNIQUES:
            technique = self.TECHNIQUES[technique_id]
            logger.info(
                f"Mapped '{finding_type}' to {technique_id}: {technique.name}"
            )
            return technique
        
        logger.warning(f"No MITRE mapping found for finding: {finding_type}")
        return None
    
    def _map_from_context(
        self,
        finding_type: str,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """
        Determine MITRE technique based on context
        
        Args:
            finding_type: Type of finding
            context: Additional context clues
            
        Returns:
            Technique ID or None
        """
        # If file path contains certain patterns
        if "file_path" in context:
            file_path = context["file_path"].lower()
            
            if any(ext in file_path for ext in [".pem", ".key", ".ssh"]):
                return "T1552.004"  # Private keys
            
            if any(name in file_path for name in [".env", "config", "credentials"]):
                return "T1552.001"  # Credentials in files
        
        # If repository-related
        if "repository" in context or "repository_url" in context:
            if finding_type in ["leak", "exposure"]:
                return "T1552.001"
        
        # If domain-related
        if "domain" in context or "malicious_domain" in context:
            return "T1583.001"  # Domain acquisition
        
        return None
    
    def get_technique_by_id(self, technique_id: str) -> Optional[MITRETechnique]:
        """Get technique details by ID"""
        return self.TECHNIQUES.get(technique_id)
    
    def list_techniques(self, tactic: Optional[Tactic] = None) -> List[MITRETechnique]:
        """
        List all supported techniques, optionally filtered by tactic
        
        Args:
            tactic: Filter by specific tactic
            
        Returns:
            List of MITRE techniques
        """
        techniques = list(self.TECHNIQUES.values())
        
        if tactic:
            techniques = [
                t for t in techniques if tactic in t.tactics
            ]
        
        return techniques
    
    def generate_alert_context(
        self,
        finding_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate enriched context for alerting
        
        Args:
            finding_type: Type of finding
            context: Additional context
            
        Returns:
            Dictionary with MITRE context for alerts
        """
        technique = self.map_finding_to_mitre(finding_type, context)
        
        if not technique:
            return {
                "mitre_mapped": False,
                "finding_type": finding_type
            }
        
        return {
            "mitre_mapped": True,
            "technique_id": technique.technique_id,
            "technique_name": technique.name,
            "tactics": [t.value for t in technique.tactics],
            "description": technique.description,
            "detection": technique.detection,
            "mitigation": technique.mitigation,
            "mitre_url": f"https://attack.mitre.org/techniques/{technique.technique_id.replace('.', '/')}"
        }


# Convenience function for quick mapping
def map_finding(finding_type: str, **context) -> Optional[MITRETechnique]:
    """
    Quick MITRE mapping without creating mapper instance
    
    Example:
        technique = map_finding("password", file_path=".env")
    """
    mapper = MITREMapper()
    return mapper.map_finding_to_mitre(finding_type, context)
