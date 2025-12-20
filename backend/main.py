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
    GuardAgent, GuardEvent, User, APIKey, Subscription,
    ScanRequest, ScanResponse, JobStatus, ScanType,
    ThreatResult, LeakResult,
    GuardAlertRequest, AdminResponseRequest, GuardEventStatus, AnomalyType,
    UserRegisterRequest, UserRegisterResponse,
    APIKeyCreateRequest, APIKeyResponse, APIKeyListItem,
    SubscriptionResponse, BillingCheckoutRequest
)
from backend import auth
from backend.auth import (
    generate_api_key, get_current_user, get_user_subscription,
    RequiresScout, RequiresGuard, check_scan_quota, check_agent_quota, TIERS
)
from backend import stripe_billing
import stripe

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="B2B Digital Risk Protection and External Attack Surface Management Platform",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware - Use environment-based allowed origins for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
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
    user: User = Depends(RequiresScout),  # Tier check: Scout access required
    _: User = Depends(check_scan_quota),  # Quota check and increment
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
                user_id=user.id,
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




@app.post("/guard/alert", status_code=status.HTTP_202_ACCEPTED)
async def receive_guard_alert(
    alert: GuardAlertRequest,
    user: User = Depends(RequiresGuard),  # Tier check: Guard access required
    _: User = Depends(check_agent_quota),  # Quota check
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Receive behavioral anomaly alert from Sentinyl Guard agent
    
    Creates a GuardEvent and pushes to Redis queue for worker processing
    """
    try:
        # Register/update agent
        agent = db.query(GuardAgent).filter(GuardAgent.id == alert.agent_id).first()
        if not agent:
            agent = GuardAgent(
                id=alert.agent_id,
                user_id=user.id,  # Link to authenticated user
                hostname=alert.hostname,
                ip_address=alert.details.get("ip_address"),
                os_info=alert.details.get("os_info"),
                last_heartbeat=datetime.utcnow(),
                active=True
            )
            db.add(agent)
            db.commit()
            db.refresh(agent)
            logger.info(f"Registered new guard agent: {alert.agent_id} ({alert.hostname})")
        else:
            # Update heartbeat
            agent.last_heartbeat = datetime.utcnow()
            db.commit()
        
        # Create guard event with countdown timer
        countdown_start = datetime.utcnow()
        countdown_expires = datetime.fromtimestamp(countdown_start.timestamp() + 300)  # 5 minutes
        
        event = GuardEvent(
            agent_id=alert.agent_id,
            anomaly_type=alert.anomaly_type.value,
            severity=alert.severity.value,
            target_ip=alert.target_ip,
            target_country=alert.target_country,
            process_name=alert.process_name,
            details=alert.details,
            countdown_started_at=countdown_start,
            countdown_expires_at=countdown_expires
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        
        event_id = str(event.id)
        logger.warning(
            f"Guard anomaly detected: {alert.anomaly_type.value} from {alert.hostname} "
            f"(severity: {alert.severity.value}, target: {alert.target_ip or 'N/A'})"
        )
        
        # Push to Redis queue for smart alert processing
        queue_name = "queue:guard"
        job_payload = {
            "event_id": event_id,
            "agent_id": alert.agent_id,
            "hostname": alert.hostname,
            "anomaly_type": alert.anomaly_type.value,
            "severity": alert.severity.value,
            "target_ip": alert.target_ip,
            "target_country": alert.target_country,
            "process_name": alert.process_name,
            "details": alert.details,
            "countdown_expires_at": countdown_expires.isoformat(),
            "created_at": datetime.utcnow().isoformat()
        }
        
        redis_client.lpush(queue_name, json.dumps(job_payload))
        logger.info(f"Pushed guard event {event_id} to queue: {queue_name}")
        
        return {
            "event_id": event_id,
            "status": "pending",
            "countdown_seconds": 300,
            "message": "Alert received and queued for processing"
        }
        
    except Exception as e:
        logger.error(f"Error receiving guard alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process alert: {str(e)}"
        )


@app.post("/guard/response")
async def receive_admin_response(
    response: AdminResponseRequest,
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Receive admin response from Teams/Slack interactive button
    
    Updates GuardEvent with admin decision (safe/block)
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(response.event_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid event_id format"
            )
        
        # Validate response value
        if response.response not in ["safe", "block"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Response must be 'safe' or 'block'"
            )
        
        # Update event
        event = db.query(GuardEvent).filter(GuardEvent.id == response.event_id).first()
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        event.admin_response = response.response
        event.admin_user = response.admin_user
        event.responded_at = datetime.utcnow()
        
        # If admin chose to block, mark as blocked
        if response.response == "block":
            event.blocked = True
        
        db.commit()
        
        logger.info(
            f"Admin response received for event {response.event_id}: "
            f"{response.response} by {response.admin_user}"
        )
        
        return {
            "status": "success",
            "message": f"Response '{response.response}' recorded"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing admin response: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process response: {str(e)}"
        )


@app.get("/guard/status/{agent_id}")
async def get_guard_status(
    agent_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Agent polls for admin override commands
    
    Returns pending GuardEvents for this agent with admin decisions
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(agent_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid agent_id format"
            )
        
        # Get pending events (not yet responded or within countdown window)
        events = db.query(GuardEvent).filter(
            GuardEvent.agent_id == agent_id,
            GuardEvent.countdown_expires_at > datetime.utcnow()
        ).order_by(GuardEvent.created_at.desc()).all()
        
        event_statuses = []
        for event in events:
            # Calculate countdown remaining
            countdown_remaining = int(
                (event.countdown_expires_at - datetime.utcnow()).total_seconds()
            )
            countdown_remaining = max(0, countdown_remaining)
            
            # Determine if should block
            should_block = False
            if event.admin_response == "block":
                should_block = True
            elif event.admin_response is None and countdown_remaining == 0:
                # Countdown expired, no response = auto-block
                should_block = True
                # Update event to mark as blocked
                event.blocked = True
                db.commit()
            
            event_statuses.append(
                GuardEventStatus(
                    event_id=str(event.id),
                    anomaly_type=event.anomaly_type,
                    severity=event.severity,
                    admin_response=event.admin_response,
                    countdown_remaining=countdown_remaining,
                    should_block=should_block
                )
            )
        
        return {
            "agent_id": agent_id,
            "pending_events": len(event_statuses),
            "events": [e.dict() for e in event_statuses]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting guard status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}"
        )


# ========== Authentication Endpoints ==========

@app.post("/auth/register", response_model=UserRegisterResponse)
async def register_user(
    request: UserRegisterRequest,
    db: Session = Depends(get_db)
) -> UserRegisterResponse:
    """
    Register new user with free tier
    
    Returns API key (shown only once!)
    """
    try:
        # Check if email already exists
        existing = db.query(User).filter(User.email == request.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create user
        user = User(email=request.email, name=request.name)
        db.add(user)
        db.flush()
        
        # Create default subscription (free tier)
        from datetime import timedelta
        subscription = Subscription(
            user_id=user.id,
            tier="free",
            scan_quota=TIERS["free"]["scan_quota"],
            agent_quota=TIERS["free"]["agent_quota"],
            scan_used=0,
            agent_used=0,
            billing_cycle_start=datetime.utcnow(),
            billing_cycle_end=datetime.utcnow() + timedelta(days=30)
        )
        db.add(subscription)
        
        # Generate API key
        plain_key, hashed_key = generate_api_key()
        api_key_record = APIKey(
            user_id=user.id,
            key_hash=hashed_key,
            key_prefix=plain_key[:8],
            name="Default"
        )
        db.add(api_key_record)
        
        db.commit()
        
        logger.info(f"New user registered: {user.email}")
        
        return UserRegisterResponse(
            user_id=str(user.id),
            email=user.email,
            name=user.name,
            api_key=plain_key,
            tier="free"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@app.get("/auth/me", response_model=SubscriptionResponse)
async def get_current_user_info(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> SubscriptionResponse:
    """Get current user's subscription details"""
    subscription = get_user_subscription(user, db)
    
    return SubscriptionResponse(
        tier=subscription.tier,
        status=subscription.status,
        scan_quota=subscription.scan_quota,
        agent_quota=subscription.agent_quota,
        scan_used=subscription.scan_used,
        agent_used=subscription.agent_used,
        billing_cycle_end=subscription.billing_cycle_end
    )


@app.post("/auth/keys", response_model=APIKeyResponse)
async def create_api_key(
    request: APIKeyCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> APIKeyResponse:
    """Create new API key for current user"""
    plain_key, hashed_key = generate_api_key()
    
    api_key = APIKey(
        user_id=user.id,
        key_hash=hashed_key,
        key_prefix=plain_key[:8],
        name=request.name
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    logger.info(f"New API key created for user {user.email}: {request.name}")
    
    return APIKeyResponse(
        api_key=plain_key,
        prefix=plain_key[:8],
        name=request.name,
        created_at=api_key.created_at
    )


@app.get("/auth/keys", response_model=list[APIKeyListItem])
async def list_api_keys(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> list[APIKeyListItem]:
    """List user's API keys (without showing full keys)"""
    keys = db.query(APIKey).filter(APIKey.user_id == user.id).all()
    
    return [
        APIKeyListItem(
            id=str(key.id),
            prefix=key.key_prefix,
            name=key.name,
            last_used_at=key.last_used_at,
            created_at=key.created_at,
            revoked=key.revoked
        )
        for key in keys
    ]


@app.delete("/auth/keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Revoke an API key"""
    try:
        key_uuid = uuid.UUID(key_id)
    except ValueError:
        raise HTTPException(400, "Invalid key ID")
    
    key = db.query(APIKey).filter(
        APIKey.id == key_uuid,
        APIKey.user_id == user.id
    ).first()
    
    if not key:
        raise HTTPException(404, "API key not found")
    
    key.revoked = True
    db.commit()
    
    logger.info(f"API key revoked: {key.name} ({key.key_prefix})")
    
    return {"message": "API key revoked successfully"}


# ========== Billing Endpoints ==========

@app.post("/billing/subscribe")
async def create_subscription(
    request: BillingCheckoutRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Create Stripe checkout session for subscription upgrade"""
    checkout_url = await stripe_billing.create_checkout_session(
        user=user,
        tier=request.tier,
        db=db
    )
    
    return {"checkout_url": checkout_url}


@app.post("/billing/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Handle Stripe webhook events (subscription updates, payments)"""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    return await stripe_billing.handle_webhook_event(payload, sig_header, db)


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
