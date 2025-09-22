import os
import stripe
from typing import Optional, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..database import Subscription, Course, SubscriptionStatus, PlanType

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

class StripeService:
    def __init__(self):
        self.webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
        self.price_ids = {
            PlanType.BASIC: os.getenv('STRIPE_BASIC_PRICE_ID'),
            PlanType.PREMIUM: os.getenv('STRIPE_PREMIUM_PRICE_ID'),
            PlanType.ENTERPRISE: os.getenv('STRIPE_ENTERPRISE_PRICE_ID'),
        }
    
    def create_customer(self, email: str, name: str, metadata: Dict = None) -> Optional[str]:
        """Create a Stripe customer"""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {}
            )
            return customer.id
        except stripe.error.StripeError as e:
            print(f"Error creating Stripe customer: {e}")
            return None
    
    def create_subscription(self, customer_id: str, plan_type: PlanType, trial_days: int = 14) -> Optional[str]:
        """Create a Stripe subscription"""
        try:
            price_id = self.price_ids.get(plan_type)
            if not price_id:
                print(f"No price ID configured for plan type: {plan_type}")
                return None
            
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{'price': price_id}],
                trial_period_days=trial_days,
                payment_behavior='default_incomplete',
                payment_settings={'save_default_payment_method': 'on_subscription'},
                expand=['latest_invoice.payment_intent'],
            )
            return subscription.id
        except stripe.error.StripeError as e:
            print(f"Error creating Stripe subscription: {e}")
            return None
    
    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> bool:
        """Cancel a Stripe subscription"""
        try:
            stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=at_period_end
            )
            return True
        except stripe.error.StripeError as e:
            print(f"Error canceling Stripe subscription: {e}")
            return False
    
    def get_subscription(self, subscription_id: str) -> Optional[Dict]:
        """Get Stripe subscription details"""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return {
                'id': subscription.id,
                'status': subscription.status,
                'current_period_start': datetime.fromtimestamp(subscription.current_period_start),
                'current_period_end': datetime.fromtimestamp(subscription.current_period_end),
                'trial_end': datetime.fromtimestamp(subscription.trial_end) if subscription.trial_end else None,
                'cancel_at_period_end': subscription.cancel_at_period_end,
            }
        except stripe.error.StripeError as e:
            print(f"Error retrieving Stripe subscription: {e}")
            return None
    
    def handle_webhook(self, payload: str, sig_header: str) -> Optional[Dict]:
        """Handle Stripe webhook"""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
            return event
        except ValueError as e:
            print(f"Invalid payload: {e}")
            return None
        except stripe.error.SignatureVerificationError as e:
            print(f"Invalid signature: {e}")
            return None
    
    def update_subscription_in_db(self, db: Session, stripe_subscription_id: str, event_data: Dict):
        """Update subscription in database based on Stripe webhook"""
        subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_subscription_id
        ).first()
        
        if not subscription:
            return
        
        stripe_sub = event_data['object']
        
        subscription.status = SubscriptionStatus(stripe_sub['status'])
        subscription.current_period_start = datetime.fromtimestamp(stripe_sub['current_period_start'])
        subscription.current_period_end = datetime.fromtimestamp(stripe_sub['current_period_end'])
        subscription.cancel_at_period_end = stripe_sub['cancel_at_period_end']
        
        if stripe_sub.get('trial_end'):
            subscription.trial_end = datetime.fromtimestamp(stripe_sub['trial_end'])
        
        db.commit()

stripe_service = StripeService()
