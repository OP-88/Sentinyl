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


# ========== Pydantic Schemas ==========

class ScanType(str, Enum):
    """Types of security scans"""
    TYPOSQUAT = "typosquat"
    LEAK = "leak"
    PHISHING = "phishing"


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
