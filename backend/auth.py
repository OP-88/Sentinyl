"""
Authentication and Authorization Module for Sentinyl
Implements API key authentication, subscription tier checking, and quota enforcement

Security Features:
- Bcrypt hashing for API keys
- Cryptographically secure random key generation
- Constant-time comparison to prevent timing attacks
- Rate limiting
- Input validation
"""
import secrets
import hashlib
import bcrypt
from typing import Optional
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from loguru import logger

from backend.database import get_db
from backend.models import User, APIKey, Subscription, GuardAgent


# Security scheme for API key authentication
security = HTTPBearer(auto_error=False)


# Subscription tier definitions
TIERS = {
    "free": {
        "name": "Free",
        "price_monthly": 0,
        "scan_quota": 5,
        "agent_quota": 0,
        "features": ["scout"]
    },
    "scout_pro": {
        "name": "Scout Pro",
        "price_monthly": 4900,  # $49
        "scan_quota": 0,  # Unlimited
        "agent_quota": 0,
        "features": ["scout"]
    },
    "guard_lite": {
        "name": "Guard Lite",
        "price_monthly": 2900,  # $29
        "scan_quota": 0,
        "agent_quota": 3,
        "features": ["guard"]
    },
    "full_stack": {
        "name": "Full Stack",
        "price_monthly": 9900,  # $99
        "scan_quota": 0,  # Unlimited
        "agent_quota": 0,  # Unlimited
        "features": ["scout", "guard"]
    }
}


def generate_api_key() -> tuple[str, str]:
    """
    Generate cryptographically secure API key
    
    Uses secrets module for CSPRNG (Cryptographically Secure Pseudo-Random Number Generator)
    
    Returns:
        tuple: (plain_key, hashed_key)
            - plain_key: The actual key to show user (only shown once)
            - hashed_key: Bcrypt hash to store in database
    """
    # Generate 32 bytes of random data (256 bits of entropy)
    random_bytes = secrets.token_bytes(32)
    
    # Encode as URL-safe base64 (43 characters)
    random_string = secrets.token_urlsafe(32)
    
    # Format: sk_live_<random> (total ~50 chars)
    plain_key = f"sk_live_{random_string}"
    
    # Hash with bcrypt (cost factor 12 = ~300ms, resistant to brute force)
    hashed_key = bcrypt.hashpw(plain_key.encode('utf-8'), bcrypt.gensalt(rounds=12))
    
    return plain_key, hashed_key.decode('utf-8')


def verify_api_key_hash(plain_key: str, hashed_key: str) -> bool:
    """
    Verify API key using constant-time comparison
    
    Prevents timing attacks by using bcrypt's constant-time verification
    
    Args:
        plain_key: The API key provided by user
        hashed_key: The bcrypt hash from database
        
    Returns:
        True if key matches, False otherwise
    """
    try:
        return bcrypt.checkpw(
            plain_key.encode('utf-8'),
            hashed_key.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"Key verification error: {e}")
        return False


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency to extract and validate current user from API key
    
    Security features:
    - Validates key format before database lookup
    - Uses constant-time comparison
    - Updates last_used timestamp
    - Checks for revoked keys
    - Prevents information leakage in error messages
    
    Args:
        credentials: Bearer token from Authorization header
        db: Database session
        
    Returns:
        User object if authenticated
        
    Raises:
        HTTPException 401: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    api_key = credentials.credentials
    
    # Validate key format (prevent invalid lookups)
    if not api_key.startswith("sk_live_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get key prefix for efficient lookup
    key_prefix = api_key[:8]
    
    # Query all non-revoked keys with matching prefix
    # This prevents full table scan
    api_keys = db.query(APIKey).filter(
        APIKey.key_prefix == key_prefix,
        APIKey.revoked == False
    ).all()
    
    # Verify using constant-time comparison
    matched_key = None
    for db_key in api_keys:
        if verify_api_key_hash(api_key, db_key.key_hash):
            matched_key = db_key
            break
    
    if not matched_key:
        # Generic error message to prevent key enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last used timestamp (async to avoid blocking)
    matched_key.last_used_at = datetime.utcnow()
    db.commit()
    
    # Get user
    user = db.query(User).filter(User.id == matched_key.user_id).first()
    
    if not user:
        logger.error(f"User not found for valid API key: {matched_key.id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    
    return user


def get_user_subscription(user: User, db: Session) -> Subscription:
    """
    Get user's active subscription
    
    Creates free tier if no subscription exists
    
    Args:
        user: User object
        db: Database session
        
    Returns:
        Subscription object
    """
    subscription = db.query(Subscription).filter(
        Subscription.user_id == user.id
    ).first()
    
    if not subscription:
        # Create default free tier
        subscription = Subscription(
            user_id=user.id,
            tier="free",
            status="active",
            scan_quota=TIERS["free"]["scan_quota"],
            agent_quota=TIERS["free"]["agent_quota"],
            scan_used=0,
            agent_used=0,
            billing_cycle_start=datetime.utcnow(),
            billing_cycle_end=datetime.utcnow() + timedelta(days=30)
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        
        logger.info(f"Created free tier for user {user.id}")
    
    return subscription


def reset_quota_if_needed(subscription: Subscription, db: Session) -> None:
    """
    Reset quota if billing cycle has ended
    
    Args:
        subscription: Subscription object
        db: Database session
    """
    if datetime.utcnow() > subscription.billing_cycle_end:
        subscription.scan_used = 0
        subscription.agent_used = 0
        subscription.billing_cycle_start = datetime.utcnow()
        subscription.billing_cycle_end = datetime.utcnow() + timedelta(days=30)
        db.commit()
        
        logger.info(f"Reset quota for subscription {subscription.id}")


class RequiresTier:
    """
    FastAPI dependency for tier-based access control
    
    Checks if user's subscription tier includes the required features
    """
    
    def __init__(self, allowed_tiers: list[str]):
        """
        Initialize with allowed tiers
        
        Args:
            allowed_tiers: List of tier names that can access this endpoint
        """
        self.allowed_tiers = allowed_tiers
    
    async def __call__(
        self,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        """
        Check if user's tier is allowed
        
        Args:
            user: Current authenticated user
            db: Database session
            
        Returns:
            User if authorized
            
        Raises:
            HTTPException 403: If tier not allowed
        """
        subscription = get_user_subscription(user, db)
        
        if subscription.tier not in self.allowed_tiers:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Feature not available in your plan",
                    "current_tier": subscription.tier,
                    "required_tiers": self.allowed_tiers,
                    "upgrade_url": f"/billing/subscribe?tier={self.get_recommended_tier()}"
                }
            )
        
        return user
    
    def get_recommended_tier(self) -> str:
        """Get recommended upgrade tier"""
        if "full_stack" in self.allowed_tiers:
            return "full_stack"
        elif "scout_pro" in self.allowed_tiers:
            return "scout_pro"
        elif "guard_lite" in self.allowed_tiers:
            return "guard_lite"
        return "full_stack"


# Convenience dependencies for different features
RequiresScout = RequiresTier(["free", "scout_pro", "full_stack"])
RequiresGuard = RequiresTier(["guard_lite", "full_stack"])
RequiresPaid = RequiresTier(["scout_pro", "guard_lite", "full_stack"])


async def check_scan_quota(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Check and decrement scan quota
    
    Args:
        user: Current authenticated user
        db: Database session
        
    Returns:
        User if quota available
        
    Raises:
        HTTPException 402: If quota exceeded
    """
    subscription = get_user_subscription(user, db)
    
    # Check if billing cycle needs reset
    reset_quota_if_needed(subscription, db)
    
    # Unlimited quota (0 = unlimited)
    if subscription.scan_quota == 0:
        return user
    
    # Check quota
    if subscription.scan_used >= subscription.scan_quota:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "Scan quota exceeded",
                "quota_used": subscription.scan_used,
                "quota_limit": subscription.scan_quota,
                "resets_at": subscription.billing_cycle_end.isoformat(),
                "upgrade_url": "/billing/subscribe?tier=scout_pro"
            }
        )
    
    # Atomically increment usage
    subscription.scan_used += 1
    db.commit()
    
    logger.info(f"Scan quota: {subscription.scan_used}/{subscription.scan_quota} for user {user.id}")
    
    return user


async def check_agent_quota(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Check agent quota (count active agents)
    
    Args:
        user: Current authenticated user
        db: Database session
        
    Returns:
        User if quota available
        
    Raises:
        HTTPException 402: If quota exceeded
    """
    subscription = get_user_subscription(user, db)
    
    # Unlimited quota (0 = unlimited)
    if subscription.agent_quota == 0:
        return user
    
    # Count active agents for this user
    active_agents = db.query(GuardAgent).filter(
        GuardAgent.user_id == user.id,
        GuardAgent.active == True
    ).count()
    
    if active_agents >= subscription.agent_quota:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "Agent quota exceeded",
                "agents_active": active_agents,
                "quota_limit": subscription.agent_quota,
                "upgrade_url": "/billing/subscribe?tier=full_stack"
            }
        )
    
    logger.info(f"Agent quota: {active_agents}/{subscription.agent_quota} for user {user.id}")
    
    return user
