"""
Database models and Pydantic schemas for Sentinyl
"""
from datetime import datetime
from typing import Optional, List
from enum import Enum
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field
import uuid

from backend.database import Base


# ========== SQLAlchemy Models ==========

class Domain(Base):
    """Domain being monitored"""
    __tablename__ = "domains"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain = Column(String(255), unique=True, nullable=False, index=True)
    company_name = Column(String(255))
    priority = Column(String(20), default="medium")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    scan_jobs = relationship("ScanJob", back_populates="domain")


class ScanJob(Base):
    """Scan job tracking"""
    __tablename__ = "scan_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id", ondelete="CASCADE"))
    job_type = Column(String(50), nullable=False)
    status = Column(String(20), default="pending")
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    domain = relationship("Domain", back_populates="scan_jobs")
    threats = relationship("Threat", back_populates="job")
    leaks = relationship("GitHubLeak", back_populates="job")


class Threat(Base):
    """Detected threat (typosquatting, phishing, etc.)"""
    __tablename__ = "threats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("scan_jobs.id", ondelete="CASCADE"))
    original_domain = Column(String(255), nullable=False)
    malicious_domain = Column(String(255), nullable=False, index=True)
    threat_type = Column(String(50))
    severity = Column(String(20), default="medium")
    ip_address = Column(String(45))
    nameservers = Column(ARRAY(Text))
    whois_data = Column(JSONB)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    notified = Column(Boolean, default=False, index=True)
    discovered_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime)
    resolved_at = Column(DateTime)
    
    job = relationship("ScanJob", back_populates="threats")


class GitHubLeak(Base):
    """Detected GitHub leak"""
    __tablename__ = "github_leaks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("scan_jobs.id", ondelete="CASCADE"))
    domain = Column(String(255), nullable=False)
    repository_url = Column(Text, nullable=False)
    repository_name = Column(String(255))
    file_path = Column(Text)
    snippet = Column(Text)
    leak_type = Column(String(50))
    severity = Column(String(20), default="high")
    is_public = Column(Boolean, default=True)
    notified = Column(Boolean, default=False, index=True)
    discovered_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)
    
    job = relationship("ScanJob", back_populates="leaks")


class GuardAgent(Base):
    """VPS agent registration for Sentinyl Guard"""
    __tablename__ = "guard_agents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hostname = Column(String(255), nullable=False)
    ip_address = Column(String(45))
    os_info = Column(String(255))
    last_heartbeat = Column(DateTime)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    events = relationship("GuardEvent", back_populates="agent")


class GuardEvent(Base):
    """Behavioral anomaly event from Sentinyl Guard agent"""
    __tablename__ = "guard_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("guard_agents.id", ondelete="CASCADE"))
    anomaly_type = Column(String(50), nullable=False)  # geo, process, resource
    severity = Column(String(20), default="high")
    target_ip = Column(String(45))
    target_country = Column(String(100))
    process_name = Column(String(255))
    details = Column(JSONB)
    countdown_started_at = Column(DateTime)
    countdown_expires_at = Column(DateTime)
    admin_response = Column(String(20))  # safe, block, null
    admin_user = Column(String(255))
    responded_at = Column(DateTime)
    blocked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    agent = relationship("GuardAgent", back_populates="events")


# ========== Pydantic Schemas ==========

class ScanType(str, Enum):
    """Types of security scans"""
    TYPOSQUAT = "typosquat"
    LEAK = "leak"
    PHISHING = "phishing"


class AnomalyType(str, Enum):
    """Types of behavioral anomalies"""
    GEO = "geo"
    PROCESS = "process"
    RESOURCE = "resource"


class SeverityLevel(str, Enum):
    """Severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ScanRequest(BaseModel):
    """Request to initiate a scan"""
    domain: str = Field(..., description="Target domain to scan", example="example.com")
    scan_type: ScanType = Field(..., description="Type of scan to perform")
    priority: Optional[SeverityLevel] = Field(default=SeverityLevel.MEDIUM, description="Scan priority")


class ScanResponse(BaseModel):
    """Response after initiating a scan"""
    job_id: str = Field(..., description="Unique job identifier")
    domain: str
    scan_type: str
    status: str
    message: str
    
    class Config:
        from_attributes = True


class ThreatResult(BaseModel):
    """Typosquatting threat result"""
    id: str
    malicious_domain: str
    threat_type: str
    severity: str
    ip_address: Optional[str]
    discovered_at: datetime
    
    class Config:
        from_attributes = True


class LeakResult(BaseModel):
    """GitHub leak result"""
    id: str
    repository_url: str
    repository_name: Optional[str]
    file_path: Optional[str]
    snippet: Optional[str]
    leak_type: str
    severity: str
    discovered_at: datetime
    
    class Config:
        from_attributes = True


class JobStatus(BaseModel):
    """Job status and results"""
    job_id: str
    domain: str
    job_type: str
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    threats: Optional[List[ThreatResult]] = []
    leaks: Optional[List[LeakResult]] = []
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


class GuardAlertRequest(BaseModel):
    """Request from agent reporting behavioral anomaly"""
    agent_id: str = Field(..., description="Unique agent identifier")
    hostname: str = Field(..., description="VPS hostname")
    anomaly_type: AnomalyType = Field(..., description="Type of anomaly detected")
    severity: SeverityLevel = Field(..., description="Severity level")
    target_ip: Optional[str] = Field(None, description="Target IP address (for geo/network anomalies)")
    target_country: Optional[str] = Field(None, description="Target country (from geo lookup)")
    process_name: Optional[str] = Field(None, description="Suspicious process name")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional anomaly details")


class AdminResponseRequest(BaseModel):
    """Admin response to guard alert"""
    event_id: str = Field(..., description="Guard event UUID")
    response: str = Field(..., description="Admin decision: 'safe' or 'block'")
    admin_user: str = Field(..., description="Admin username/email")


class GuardEventStatus(BaseModel):
    """Guard event status for agent polling"""
    event_id: str
    anomaly_type: str
    severity: str
    admin_response: Optional[str] = None
    countdown_remaining: Optional[int] = None  # seconds
    should_block: bool = False
    
    class Config:
        from_attributes = True
