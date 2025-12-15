"""
Risk Scoring Engine for Sentinyl Enterprise
Calculates risk scores (0-100) based on multiple factors
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional
from loguru import logger


class Severity(str, Enum):
    """Risk severity levels"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class RiskAssessment:
    """Risk assessment result"""
    score: int  # 0-100
    severity: Severity
    factors: Dict[str, float]  # Individual factor scores
    reasoning: str


@dataclass
class Finding:
    """Generic finding/threat data structure"""
    finding_type: str  # typosquat, leak, phishing
    visibility: str  # public, private, internal
    discovered_at: datetime
    asset_value: str  # production, staging, development, unknown
    metadata: Dict[str, Any]


class RiskScorer:
    """
    Sophisticated risk scoring algorithm
    
    Scoring Factors:
    - Visibility (40%): public > private > internal
    - Age (30%): new findings = higher risk
    - Asset Value (30%): production > staging > development
    """
    
    # Weight distribution (must sum to 1.0)
    WEIGHT_VISIBILITY = 0.40
    WEIGHT_AGE = 0.30
    WEIGHT_ASSET_VALUE = 0.30
    
    # Severity thresholds
    THRESHOLD_CRITICAL = 80
    THRESHOLD_HIGH = 60
    THRESHOLD_MEDIUM = 40
    
    def calculate_risk(self, finding: Finding) -> RiskAssessment:
        """
        Calculate comprehensive risk score for a finding
        
        Args:
            finding: Finding object with all necessary attributes
            
        Returns:
            RiskAssessment with score, severity, and breakdown
        """
        logger.info(f"Calculating risk for {finding.finding_type} finding")
        
        # Calculate individual factor scores (0-100)
        visibility_score = self._score_visibility(finding.visibility)
        age_score = self._score_age(finding.discovered_at)
        asset_score = self._score_asset_value(finding.asset_value)
        
        # Apply weights to get final score
        weighted_score = (
            visibility_score * self.WEIGHT_VISIBILITY +
            age_score * self.WEIGHT_AGE +
            asset_score * self.WEIGHT_ASSET_VALUE
        )
        
        final_score = int(weighted_score)
        severity = self._determine_severity(final_score)
        
        # Build reasoning string
        reasoning = self._build_reasoning(
            final_score, visibility_score, age_score, asset_score, finding
        )
        
        factors = {
            "visibility": visibility_score,
            "age": age_score,
            "asset_value": asset_score
        }
        
        logger.info(
            f"Risk assessment complete: {final_score}/100 ({severity.value})"
        )
        
        return RiskAssessment(
            score=final_score,
            severity=severity,
            factors=factors,
            reasoning=reasoning
        )
    
    def _score_visibility(self, visibility: str) -> float:
        """
        Score based on data visibility
        
        Public exposure = highest risk
        Private = medium risk
        Internal-only = lowest risk
        """
        visibility_map = {
            "public": 100.0,      # Accessible to everyone
            "private": 50.0,      # Restricted but exists
            "internal": 25.0,     # Internal network only
            "unknown": 60.0       # Assume medium risk when unknown
        }
        
        score = visibility_map.get(visibility.lower(), 60.0)
        logger.debug(f"Visibility '{visibility}' scored: {score}/100")
        return score
    
    def _score_age(self, discovered_at: datetime) -> float:
        """
        Score based on finding age
        
        Newer findings = higher urgency
        Age decay: 100 -> 50 over 30 days
        """
        now = datetime.utcnow()
        age_days = (now - discovered_at).days
        
        if age_days < 0:
            # Future timestamp (clock skew) - treat as brand new
            age_days = 0
        
        # Score decay formula: starts at 100, decays to 50 over 30 days
        # After 30 days, stabilizes at 50 (still a risk, just not urgent)
        if age_days == 0:
            score = 100.0  # Brand new
        elif age_days <= 30:
            # Linear decay from 100 to 50 over first 30 days
            decay_rate = 50.0 / 30.0  # 1.67 points per day
            score = 100.0 - (age_days * decay_rate)
        else:
            # Older than 30 days = stable at 50
            score = 50.0
        
        logger.debug(f"Age {age_days} days scored: {score}/100")
        return score
    
    def _score_asset_value(self, asset_value: str) -> float:
        """
        Score based on asset criticality
        
        Production systems = highest impact
        Development = lowest impact
        """
        asset_map = {
            "production": 100.0,   # Live customer-facing
            "prod": 100.0,         # Alias
            "staging": 70.0,       # Pre-production
            "stage": 70.0,         # Alias
            "development": 40.0,   # Dev environment
            "dev": 40.0,           # Alias
            "test": 30.0,          # Testing only
            "unknown": 60.0        # Assume medium value
        }
        
        score = asset_map.get(asset_value.lower(), 60.0)
        logger.debug(f"Asset value '{asset_value}' scored: {score}/100")
        return score
    
    def _determine_severity(self, score: int) -> Severity:
        """Map numeric score to severity level"""
        if score >= self.THRESHOLD_CRITICAL:
            return Severity.CRITICAL
        elif score >= self.THRESHOLD_HIGH:
            return Severity.HIGH
        elif score >= self.THRESHOLD_MEDIUM:
            return Severity.MEDIUM
        else:
            return Severity.LOW
    
    def _build_reasoning(
        self,
        final_score: int,
        visibility: float,
        age: float,
        asset: float,
        finding: Finding
    ) -> str:
        """Build human-readable reasoning string"""
        
        # Identify primary risk drivers
        factors = [
            ("visibility", visibility, self.WEIGHT_VISIBILITY),
            ("age", age, self.WEIGHT_AGE),
            ("asset_value", asset, self.WEIGHT_ASSET_VALUE)
        ]
        
        # Sort by weighted contribution
        factors_sorted = sorted(
            factors, key=lambda x: x[1] * x[2], reverse=True
        )
        
        primary_driver = factors_sorted[0][0]
        
        reasoning_parts = []
        
        # Overall assessment
        severity = self._determine_severity(final_score)
        reasoning_parts.append(
            f"{severity.value} risk ({final_score}/100):"
        )
        
        # Visibility reasoning
        if finding.visibility.lower() == "public":
            reasoning_parts.append("publicly accessible")
        elif finding.visibility.lower() == "private":
            reasoning_parts.append("restricted but exposed")
        
        # Age reasoning
        age_days = (datetime.utcnow() - finding.discovered_at).days
        if age_days == 0:
            reasoning_parts.append("discovered today")
        elif age_days <= 7:
            reasoning_parts.append("recent discovery")
        elif age_days > 30:
            reasoning_parts.append("older finding")
        
        # Asset reasoning
        if finding.asset_value.lower() in ["production", "prod"]:
            reasoning_parts.append("affects production systems")
        elif finding.asset_value.lower() in ["development", "dev"]:
            reasoning_parts.append("development environment only")
        
        return ", ".join(reasoning_parts) + "."


# Convenience function for quick scoring
def score_finding(
    finding_type: str,
    visibility: str = "unknown",
    asset_value: str = "unknown",
    discovered_at: Optional[datetime] = None,
    **metadata
) -> RiskAssessment:
    """
    Quick risk scoring without creating Finding object
    
    Example:
        assessment = score_finding(
            finding_type="leak",
            visibility="public",
            asset_value="production",
            repository="user/repo"
        )
    """
    if discovered_at is None:
        discovered_at = datetime.utcnow()
    
    finding = Finding(
        finding_type=finding_type,
        visibility=visibility,
        discovered_at=discovered_at,
        asset_value=asset_value,
        metadata=metadata
    )
    
    scorer = RiskScorer()
    return scorer.calculate_risk(finding)
