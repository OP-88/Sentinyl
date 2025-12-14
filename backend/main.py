"""
Sentinyl - B2B Digital Risk Protection Platform
FastAPI Backend API
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Dict, Any
import redis
import json
import uuid
from datetime import datetime
from loguru import logger

from backend.config import settings
from backend.database import get_db, engine
from backend.models import (
    Base, Domain, ScanJob, Threat, GitHubLeak,
    ScanRequest, ScanResponse, JobStatus, ScanType,
    ThreatResult, LeakResult
)

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="B2B Digital Risk Protection and External Attack Surface Management Platform",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis connection
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

# Configure logging
logger.add("logs/api.log", rotation="500 MB", retention="10 days", level="INFO")


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Test database connection
    try:
        with engine.connect() as conn:
            logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise
    
    # Test Redis connection
    try:
        redis_client.ping()
        logger.info("Redis connection successful")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Sentinyl API")
    redis_client.close()


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for Docker and monitoring
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Check database
    try:
        with engine.connect() as conn:
            health_status["services"]["database"] = "connected"
    except Exception as e:
        health_status["services"]["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Check Redis
    try:
        redis_client.ping()
        health_status["services"]["redis"] = "connected"
    except Exception as e:
        health_status["services"]["redis"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    return health_status


@app.post("/scan", response_model=ScanResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_scan(
    scan_request: ScanRequest,
    db: Session = Depends(get_db)
) -> ScanResponse:
    """
    Initiate a security scan
    
    Accepts a domain and scan type, creates a job in the database,
    and pushes it to the Redis queue for worker processing.
    
    - **domain**: Target domain to scan (e.g., example.com)
    - **scan_type**: Type of scan (typosquat, leak, phishing)
    - **priority**: Scan priority level (optional)
    """
    try:
        # Validate domain format (basic validation)
        domain = scan_request.domain.lower().strip()
        if not domain or "." not in domain:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid domain format"
            )
        
        # Get or create domain record
        domain_record = db.query(Domain).filter(Domain.domain == domain).first()
        if not domain_record:
            domain_record = Domain(
                domain=domain,
                priority=scan_request.priority.value
            )
            db.add(domain_record)
            db.commit()
            db.refresh(domain_record)
            logger.info(f"Created new domain record: {domain}")
        
        # Create scan job
        job = ScanJob(
            domain_id=domain_record.id,
            job_type=scan_request.scan_type.value,
            status="pending"
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        job_id = str(job.id)
        logger.info(f"Created scan job {job_id} for {domain} (type: {scan_request.scan_type.value})")
        
        # Push job to Redis queue
        queue_name = f"queue:{scan_request.scan_type.value}"
        job_payload = {
            "job_id": job_id,
            "domain": domain,
            "scan_type": scan_request.scan_type.value,
            "priority": scan_request.priority.value,
            "created_at": datetime.utcnow().isoformat()
        }
        
        redis_client.lpush(queue_name, json.dumps(job_payload))
        logger.info(f"Pushed job {job_id} to queue: {queue_name}")
        
        return ScanResponse(
            job_id=job_id,
            domain=domain,
            scan_type=scan_request.scan_type.value,
            status="pending",
            message=f"Scan job created and queued for processing"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating scan: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create scan: {str(e)}"
        )


@app.get("/results/{job_id}", response_model=JobStatus)
async def get_scan_results(
    job_id: str,
    db: Session = Depends(get_db)
) -> JobStatus:
    """
    Retrieve scan job status and results
    
    - **job_id**: UUID of the scan job
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(job_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid job_id format"
            )
        
        # Query job
        job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Build response
        response = JobStatus(
            job_id=str(job.id),
            domain=job.domain.domain,
            job_type=job.job_type,
            status=job.status,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message
        )
        
        # Include threats if typosquat scan
        if job.job_type == ScanType.TYPOSQUAT.value:
            threats = db.query(Threat).filter(Threat.job_id == job_id).all()
            response.threats = [
                ThreatResult(
                    id=str(t.id),
                    malicious_domain=t.malicious_domain,
                    threat_type=t.threat_type,
                    severity=t.severity,
                    ip_address=t.ip_address,
                    discovered_at=t.discovered_at
                )
                for t in threats
            ]
        
        # Include leaks if leak scan
        if job.job_type == ScanType.LEAK.value:
            leaks = db.query(GitHubLeak).filter(GitHubLeak.job_id == job_id).all()
            response.leaks = [
                LeakResult(
                    id=str(l.id),
                    repository_url=l.repository_url,
                    repository_name=l.repository_name,
                    file_path=l.file_path,
                    snippet=l.snippet[:200] if l.snippet else None,  # Truncate
                    leak_type=l.leak_type,
                    severity=l.severity,
                    discovered_at=l.discovered_at
                )
                for l in leaks
            ]
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving results: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve results: {str(e)}"
        )


@app.get("/stats")
async def get_statistics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get platform statistics
    """
    try:
        stats = {
            "total_domains": db.query(Domain).filter(Domain.active == True).count(),
            "total_scans": db.query(ScanJob).count(),
            "pending_scans": db.query(ScanJob).filter(ScanJob.status == "pending").count(),
            "active_threats": db.query(Threat).filter(Threat.is_active == True).count(),
            "total_leaks": db.query(GitHubLeak).count(),
            "unnotified_threats": db.query(Threat).filter(Threat.notified == False).count(),
        }
        return stats
    except Exception as e:
        logger.error(f"Error retrieving stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
