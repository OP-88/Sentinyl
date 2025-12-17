"""
Stripe billing integr functionality for Sentinyl subscriptions
"""
import stripe
from typing import Optional, Dict, Any
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
from loguru import logger
from datetime import datetime, timedelta

from backend.config import settings
from backend.models import User, Subscription
from backend.auth import TIERS


# Configure Stripe
if settings.STRIPE_API_KEY:
    stripe.api_key = settings.STRIPE_API_KEY


async def create_checkout_session(
    user: User,
    tier: str,
    db: Session
) -> str:
    """
    Create Stripe checkout session for subscription
    
    Args:
        user: User object
        tier: Target subscription tier
        db: Database session
        
    Returns:
        Checkout session URL
        
    Raises:
        HTTPException: If Stripe not configured or invalid tier
    """
    if not stripe.api_key:
        raise HTTPException(503, "Billing not configured")
    
    if tier not in TIERS:
        raise HTTPException(400, f"Invalid tier: {tier}")
    
    tier_config = TIERS[tier]
    
    if tier_config["price_monthly"] == 0:
        raise HTTPException(400, "Cannot subscribe to free tier")
    
    try:
        # Create customer if doesn't exist
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.name,
                metadata={"user_id": str(user.id)}
            )
            user.stripe_customer_id = customer.id
            db.commit()
        
        # Create checkout session
session = stripe.checkout.Session.create(
            customer=user.stripe_customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"Sentinyl {tier_config['name']}",
                        "description": f"Scout: {'✅' if 'scout' in tier_config['features'] else '❌'} | Guard: {'✅' if 'guard' in tier_config['features'] else '❌'}"
                    },
                    "unit_amount": tier_config["price_monthly"],
                    "recurring": {"interval": "month"}
                },
                "quantity": 1
            }],
            mode="subscription",
            success_url=f"{settings.APP_NAME}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.APP_NAME}/pricing",
            client_reference_id=str(user.id),
            metadata={"tier": tier}
        )
        
        logger.info(f"Created checkout session for {user.email}: {tier}")
        
        return session.url
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        raise HTTPException(500, "Billing error")


async def handle_webhook_event(payload: bytes, sig_header: str, db: Session) -> Dict[str, Any]:
    """
    Handle Stripe webhook events
    
    Args:
        payload: Raw request body
        sig_header: Stripe signature header
        db: Database session
        
    Returns:
        Event details
    """
    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.warning("Stripe webhook secret not configured")
        return {"status": "skipped"}
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(400, "Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")
    
    logger.info(f"Received Stripe event: {event['type']}")
    
    # Handle checkout session completed
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session["client_reference_id"]
        tier = session["metadata"]["tier"]
        stripe_subscription_id = session.get("subscription")
        
        # Update user subscription
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        
        if subscription:
            subscription.tier = tier
            subscription.status = "active"
            subscription.scan_quota = TIERS[tier]["scan_quota"]
            subscription.agent_quota = TIERS[tier]["agent_quota"]
            subscription.scan_used = 0
            subscription.agent_used = 0
            subscription.billing_cycle_start = datetime.utcnow()
            subscription.billing_cycle_end = datetime.utcnow() + timedelta(days=30)
            subscription.stripe_subscription_id = stripe_subscription_id
            db.commit()
            
            logger.info(f"Upgraded user {user_id} to {tier}")
    
    # Handle subscription deletion
    elif event["type"] == "customer.subscription.deleted":
        stripe_subscription_id = event["data"]["object"]["id"]
        
        # Downgrade to free tier
        subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_subscription_id
        ).first()
        
        if subscription:
            subscription.tier = "free"
            subscription.status = "canceled"
            subscription.scan_quota = TIERS["free"]["scan_quota"]
            subscription.agent_quota = TIERS["free"]["agent_quota"]
            subscription.scan_used = 0
            subscription.agent_used = 0
            db.commit()
            
            logger.info(f"Downgraded subscription {subscription.id} to free")
    
    # Handle failed payment
    elif event["type"] == "invoice.payment_failed":
        subscription_id = event["data"]["object"]["subscription"]
        
        subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()
        
        if subscription:
            subscription.status = "past_due"
            db.commit()
            
            logger.warning(f"Payment failed for subscription {subscription.id}")
    
    return {"status": "processed", "event_type": event["type"]}
