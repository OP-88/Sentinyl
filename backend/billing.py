"""
Billing and Entitlement Management for Sentinyl Enterprise
Stripe integration and quota enforcement middleware
"""
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
from pydantic import BaseModel
from loguru import logger
import stripe
import os


# Stripe Configuration
stripe.api_key = os.getenv("STRIPE_API_KEY")


class Plan(BaseModel):
    """Subscription Plan"""
    id: str
    name: str  # Free, Pro, Enterprise
    scan_quota: int  # Monthly scan limit
    price_monthly: int  # In cents
    features: list[str]


class UserEntitlement(BaseModel):
    """User's current entitlement and usage"""
    user_id: str
    plan_id: str
    quota_used: int
    quota_limit: int
    billing_cycle_start: datetime
    billing_cycle_end: datetime


# Available Plans
PLANS = {
    "free": Plan(
        id="free",
        name="Free",
        scan_quota=10,  # 10 scans per month
        price_monthly=0,
        features=[
            "Basic typosquatting detection",
            "GitHub leak scanning",
            "Slack notifications"
        ]
    ),
    "pro": Plan(
        id="pro",
        name="Professional",
        scan_quota=100,  # 100 scans per month
        price_monthly=4900,  # $49/month
        features=[
            "Advanced typosquatting detection",
            "Continuous GitHub monitoring",
            "MITRE ATT&CK mapping",
            "Investigation graph analytics",
            "Teams & Slack notifications",
            "Risk scoring"
        ]
    ),
    "enterprise": Plan(
        id="enterprise",
        name="Enterprise",
        scan_quota=1000,  # 1000 scans per month
        price_monthly=19900,  # $199/month
        features=[
            "Unlimited typosquatting scans",
            "Real-time GitHub monitoring",
            "MITRE ATT&CK mapping",
            "Full graph analytics",
            "Custom integrations",
            "Priority support",
            "SLA guarantees"
        ]
    )
}


class BillingManager:
    """Manages billing, quotas, and Stripe integration"""
    
    def __init__(self, db_connection):
        """
        Initialize billing manager
        
        Args:
            db_connection: PostgreSQL connection for quota tracking
        """
        self.db = db_connection
    
    def get_user_entitlement(self, user_id: str) -> Optional[UserEntitlement]:
        """
        Get user's current entitlement
        
        Args:
            user_id: User identifier
            
        Returns:
            UserEntitlement or None if not found
        """
        try:
            cursor = self.db.cursor()
            query = """
                SELECT user_id, plan_id, quota_used, quota_limit,
                       billing_cycle_start, billing_cycle_end
                FROM user_entitlements
                WHERE user_id = %s
            """
            cursor.execute(query, (user_id,))
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                return UserEntitlement(
                    user_id=row[0],
                    plan_id=row[1],
                    quota_used=row[2],
                    quota_limit=row[3],
                    billing_cycle_start=row[4],
                    billing_cycle_end=row[5]
                )
            
            # Create default free tier if not exists
            return self._create_default_entitlement(user_id)
            
        except Exception as e:
            logger.error(f"Failed to get entitlement for {user_id}: {e}")
            return None
    
    def _create_default_entitlement(self, user_id: str) -> UserEntitlement:
        """Create default free tier for new user"""
        try:
            cursor = self.db.cursor()
            cycle_start = datetime.utcnow()
            cycle_end = cycle_start + timedelta(days=30)
            
            query = """
                INSERT INTO user_entitlements
                (user_id, plan_id, quota_used, quota_limit, billing_cycle_start, billing_cycle_end)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING user_id, plan_id, quota_used, quota_limit, billing_cycle_start, billing_cycle_end
            """
            cursor.execute(query, (
                user_id, "free", 0, PLANS["free"].scan_quota,
                cycle_start, cycle_end
            ))
            
            row = cursor.fetchone()
            self.db.commit()
            cursor.close()
            
            logger.info(f"Created free tier for user {user_id}")
            
            return UserEntitlement(
                user_id=row[0],
                plan_id=row[1],
                quota_used=row[2],
                quota_limit=row[3],
                billing_cycle_start=row[4],
                billing_cycle_end=row[5]
            )
        except Exception as e:
            logger.error(f"Failed to create default entitlement: {e}")
            raise
    
    def check_quota(self, user_id: str) -> bool:
        """
        Check if user has available quota
        
        Args:
            user_id: User identifier
            
        Returns:
            True if quota available, False otherwise
        """
        entitlement = self.get_user_entitlement(user_id)
        
        if not entitlement:
            return False
        
        # Check if billing cycle has reset
        if datetime.utcnow() > entitlement.billing_cycle_end:
            self._reset_billing_cycle(user_id)
            entitlement = self.get_user_entitlement(user_id)
        
        return entitlement.quota_used < entitlement.quota_limit
    
    def increment_usage(self, user_id: str) -> bool:
        """
        Atomically increment usage counter
        
        Args:
            user_id: User identifier
            
        Returns:
            True if successful
        """
        try:
            cursor = self.db.cursor()
            query = """
                UPDATE user_entitlements
                SET quota_used = quota_used + 1
                WHERE user_id = %s AND quota_used < quota_limit
                RETURNING quota_used
            """
            cursor.execute(query, (user_id,))
            result = cursor.fetchone()
            self.db.commit()
            cursor.close()
            
            if result:
                logger.info(f"Incremented usage for {user_id}: {result[0]}")
                return True
            
            logger.warning(f"Quota exceeded for {user_id}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to increment usage: {e}")
            return False
    
    def _reset_billing_cycle(self, user_id: str):
        """Reset billing cycle and quota"""
        try:
            cursor = self.db.cursor()
            new_start = datetime.utcnow()
            new_end = new_start + timedelta(days=30)
            
            query = """
                UPDATE user_entitlements
                SET quota_used = 0,
                    billing_cycle_start = %s,
                    billing_cycle_end = %s
                WHERE user_id = %s
            """
            cursor.execute(query, (new_start, new_end, user_id))
            self.db.commit()
            cursor.close()
            
            logger.info(f"Reset billing cycle for {user_id}")
        except Exception as e:
            logger.error(f"Failed to reset billing cycle: {e}")
    
    def create_checkout_session(
        self,
        user_id: str,
        plan_id: str,
        success_url: str,
        cancel_url: str
    ) -> Optional[str]:
        """
        Create Stripe checkout session
        
        Args:
            user_id: User identifier
            plan_id: Target plan ID
            success_url: Redirect URL on success
            cancel_url: Redirect URL on cancel
            
        Returns:
            Checkout session URL or None
        """
        if not stripe.api_key:
            logger.warning("Stripe not configured - checkout disabled")
            return None
        
        if plan_id not in PLANS:
            logger.error(f"Invalid plan ID: {plan_id}")
            return None
        
        plan = PLANS[plan_id]
        
        if plan.price_monthly == 0:
            logger.warning("Cannot create checkout for free plan")
            return None
        
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"Sentinyl {plan.name} Plan",
                            "description": f"{plan.scan_quota} scans/month",
                        },
                        "unit_amount": plan.price_monthly,
                        "recurring": {"interval": "month"}
                    },
                    "quantity": 1
                }],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=user_id,
                metadata={"plan_id": plan_id}
            )
            
            logger.info(f"Created checkout session for {user_id}: {session.id}")
            return session.url
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            return None


# FastAPI Dependency for quota checking
security = HTTPBearer(auto_error=False)


async def check_scan_quota(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """
    FastAPI dependency to enforce scan quotas
    
    Raises:
        HTTPException 401: If no authentication provided
        HTTPException 402: If quota exceeded
        
    Returns:
        user_id if quota available
    """
    # For now, use a simple user_id extraction
    # In production, implement proper JWT validation
    if not credentials:
        # Allow anonymous with 'anonymous' user_id for testing
        user_id = "anonymous"
    else:
        user_id = credentials.credentials  # In production: decode JWT
    
    # Get database connection (you'll need to inject this properly)
    from workers.shared_utils import get_db_connection
    
    db = get_db_connection()
    billing = BillingManager(db)
    
    # Check quota
    if not billing.check_quota(user_id):
        entitlement = billing.get_user_entitlement(user_id)
        db.close()
        
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Quota exceeded",
                "quota_used": entitlement.quota_used if entitlement else 0,
                "quota_limit": entitlement.quota_limit if entitlement else 0,
                "upgrade_url": "/billing/upgrade"
            }
        )
    
    # Increment usage
    if not billing.increment_usage(user_id):
        db.close()
        raise HTTPException(
            status_code=402,
            detail={"error": "Failed to reserve quota"}
        )
    
    db.close()
    return user_id


def handle_stripe_webhook(payload: bytes, sig_header: str) -> Dict[str, Any]:
    """
    Handle Stripe webhook events
    
    Args:
        payload: Raw request body
        sig_header: Stripe signature header
        
    Returns:
        Event data
    """
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    if not webhook_secret:
        logger.warning("Stripe webhook secret not configured")
        return {}
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
        
        logger.info(f"Received Stripe event: {event['type']}")
        
        # Handle different event types
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            user_id = session.get("client_reference_id")
            plan_id = session["metadata"].get("plan_id")
            
            logger.info(f"Checkout completed: {user_id} -> {plan_id}")
            
            # TODO: Update user entitlement in database
            
        elif event["type"] == "invoice.payment_failed":
            logger.warning(f"Payment failed: {event['data']['object']}")
            # TODO: Handle failed payment
        
        return event
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise
