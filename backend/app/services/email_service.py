import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional
from sqlalchemy.orm import Session
from ..database import EmailTemplate, EmailLog

class EmailService:
    def __init__(self):
        self.email_provider = os.getenv('EMAIL_PROVIDER', 'smtp')
        self.sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.sendgrid.net')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME', 'apikey')
        self.smtp_password = os.getenv('SMTP_PASSWORD', self.sendgrid_api_key)
        self.from_email = os.getenv('FROM_EMAIL', 'noreply@golfcms.com')
        self.from_name = os.getenv('FROM_NAME', 'Golf CMS')
    
    def send_email(self, db: Session, template_name: str, recipient_email: str, variables: Dict[str, str] = None) -> bool:
        """Send email using template"""
        try:
            template = db.query(EmailTemplate).filter(
                EmailTemplate.name == template_name,
                EmailTemplate.is_active == True
            ).first()
            
            if not template:
                self._log_email(db, recipient_email, template_name, "Template not found", "error", "Template not found")
                return False
            
            subject = self._replace_variables(template.subject, variables or {})
            html_content = self._replace_variables(template.html_content, variables or {})
            text_content = self._replace_variables(template.text_content or "", variables or {})
            
            if self.email_provider == 'sendgrid' and self.sendgrid_api_key:
                return self._send_via_sendgrid(db, recipient_email, subject, html_content, text_content, template_name)
            else:
                return self._send_via_smtp(db, recipient_email, subject, html_content, text_content, template_name)
            
        except Exception as e:
            error_msg = str(e)
            self._log_email(db, recipient_email, template_name, subject if 'subject' in locals() else "Unknown", "error", error_msg)
            print(f"Error sending email: {error_msg}")
            return False
    
    def _send_via_sendgrid(self, db: Session, recipient_email: str, subject: str, html_content: str, text_content: str, template_name: str) -> bool:
        """Send email via SendGrid API"""
        try:
            url = "https://api.sendgrid.com/v3/mail/send"
            headers = {
                "Authorization": f"Bearer {self.sendgrid_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "personalizations": [{
                    "to": [{"email": recipient_email}],
                    "subject": subject
                }],
                "from": {
                    "email": self.from_email,
                    "name": self.from_name
                },
                "content": [
                    {"type": "text/plain", "value": text_content},
                    {"type": "text/html", "value": html_content}
                ]
            }
            
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 202:
                self._log_email(db, recipient_email, template_name, subject, "sent")
                return True
            else:
                error_msg = f"SendGrid API error: {response.status_code} - {response.text}"
                self._log_email(db, recipient_email, template_name, subject, "error", error_msg)
                return False
                
        except Exception as e:
            error_msg = f"SendGrid error: {str(e)}"
            self._log_email(db, recipient_email, template_name, subject, "error", error_msg)
            return False
    
    def _send_via_smtp(self, db: Session, recipient_email: str, subject: str, html_content: str, text_content: str, template_name: str) -> bool:
        """Send email via SMTP"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = recipient_email
            
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                msg.attach(text_part)
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            self._log_email(db, recipient_email, template_name, subject, "sent")
            return True
            
        except Exception as e:
            error_msg = f"SMTP error: {str(e)}"
            self._log_email(db, recipient_email, template_name, subject, "error", error_msg)
            return False
    
    def _replace_variables(self, content: str, variables: Dict[str, str]) -> str:
        """Replace template variables with actual values"""
        for key, value in variables.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))
        return content
    
    def _log_email(self, db: Session, recipient: str, template: str, subject: str, status: str, error: str = None):
        """Log email sending attempt"""
        log = EmailLog(
            recipient_email=recipient,
            template_name=template,
            subject=subject,
            status=status,
            error_message=error
        )
        db.add(log)
        db.commit()

email_service = EmailService()
