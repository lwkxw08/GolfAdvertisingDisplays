from sqlalchemy.orm import Session
from ..database import Course, User, Subscription, EmailTemplate, UserRole, PlanType, SubscriptionStatus
from ..auth import get_password_hash
from .email_service import email_service
from .stripe_service import stripe_service
from typing import Dict, Optional
import uuid
import os

class ProvisioningService:
    def __init__(self):
        pass
    
    def create_course_with_owner(self, db: Session, course_data: Dict) -> Optional[Dict]:
        """Create a new course with owner user and subscription"""
        try:
            course = Course(
                name=course_data['course_name'],
                location=course_data['location'],
                owner_email=course_data['owner_email'],
                phone=course_data.get('phone'),
                website=course_data.get('website'),
                is_active=True,
                onboarding_completed=False
            )
            db.add(course)
            db.flush()
            
            owner_user = User(
                email=course_data['owner_email'],
                hashed_password=get_password_hash(course_data['owner_password']),
                role=UserRole.CLIENT_TENANT,
                course_id=course.id,
                is_active=True
            )
            db.add(owner_user)
            
            stripe_customer_id = stripe_service.create_customer(
                email=course_data['owner_email'],
                name=course_data['course_name'],
                metadata={'course_id': str(course.id)}
            )
            
            subscription = Subscription(
                course_id=course.id,
                stripe_customer_id=stripe_customer_id,
                plan_type=course_data.get('plan_type', PlanType.BASIC),
                status=SubscriptionStatus.TRIALING
            )
            db.add(subscription)
            
            if stripe_customer_id:
                stripe_subscription_id = stripe_service.create_subscription(
                    stripe_customer_id,
                    subscription.plan_type
                )
                subscription.stripe_subscription_id = stripe_subscription_id
            
            db.commit()
            
            self.send_welcome_email(db, course_data['owner_email'], {
                'course_name': course_data['course_name'],
                'owner_email': course_data['owner_email']
            })
            
            return {
                'course_id': course.id,
                'user_id': owner_user.id,
                'subscription_id': subscription.id
            }
            
        except Exception as e:
            db.rollback()
            print(f"Error creating course: {e}")
            return None
    
    def send_welcome_email(self, db: Session, recipient_email: str, variables: Dict):
        """Send welcome email to new course owner"""
        email_service.send_email(
            db=db,
            template_name='welcome_course_owner',
            recipient_email=recipient_email,
            variables=variables
        )
    
    def send_invitation_email(self, db: Session, recipient_email: str, course_name: str, invite_token: str):
        """Send invitation email to new team member"""
        variables = {
            'course_name': course_name,
            'invite_link': f"{os.getenv('FRONTEND_URL')}/invite/{invite_token}",
            'recipient_email': recipient_email
        }
        
        email_service.send_email(
            db=db,
            template_name='team_invitation',
            recipient_email=recipient_email,
            variables=variables
        )
    
    def create_default_email_templates(self, db: Session):
        """Create default email templates"""
        templates = [
            {
                'name': 'welcome_course_owner',
                'subject': 'Welcome to Golf CMS - {{course_name}}',
                'html_content': '''
                <h1>Welcome to Golf CMS!</h1>
                <p>Hi there,</p>
                <p>Welcome to Golf CMS! Your course <strong>{{course_name}}</strong> has been successfully set up.</p>
                <p>You can now start managing your tee box displays and sponsor campaigns.</p>
                <p>Your account: {{owner_email}}</p>
                <p>Best regards,<br>The Golf CMS Team</p>
                ''',
                'text_content': '''
                Welcome to Golf CMS!
                
                Hi there,
                
                Welcome to Golf CMS! Your course {{course_name}} has been successfully set up.
                
                You can now start managing your tee box displays and sponsor campaigns.
                
                Your account: {{owner_email}}
                
                Best regards,
                The Golf CMS Team
                '''
            },
            {
                'name': 'team_invitation',
                'subject': 'You\'re invited to join {{course_name}} on Golf CMS',
                'html_content': '''
                <h1>You're invited!</h1>
                <p>Hi there,</p>
                <p>You've been invited to join <strong>{{course_name}}</strong> on Golf CMS.</p>
                <p><a href="{{invite_link}}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Accept Invitation</a></p>
                <p>If the button doesn't work, copy and paste this link: {{invite_link}}</p>
                <p>Best regards,<br>The Golf CMS Team</p>
                ''',
                'text_content': '''
                You're invited!
                
                Hi there,
                
                You've been invited to join {{course_name}} on Golf CMS.
                
                Accept your invitation here: {{invite_link}}
                
                Best regards,
                The Golf CMS Team
                '''
            },
            {
                'name': 'billing_payment_success',
                'subject': 'Payment Successful - Golf CMS',
                'html_content': '''
                <h1>Payment Successful</h1>
                <p>Hi there,</p>
                <p>Your payment for Golf CMS has been processed successfully.</p>
                <p>Amount: ${{amount}}</p>
                <p>Next billing date: {{next_billing_date}}</p>
                <p>Thank you for your continued subscription!</p>
                <p>Best regards,<br>The Golf CMS Team</p>
                ''',
                'text_content': '''
                Payment Successful
                
                Hi there,
                
                Your payment for Golf CMS has been processed successfully.
                
                Amount: ${{amount}}
                Next billing date: {{next_billing_date}}
                
                Thank you for your continued subscription!
                
                Best regards,
                The Golf CMS Team
                '''
            }
        ]
        
        for template_data in templates:
            existing = db.query(EmailTemplate).filter(EmailTemplate.name == template_data['name']).first()
            if not existing:
                template = EmailTemplate(**template_data)
                db.add(template)
        
        db.commit()

provisioning_service = ProvisioningService()
