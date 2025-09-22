import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional
from sqlalchemy.orm import Session
from ..database import EmailTemplate, EmailLog

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_username)
    
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
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = recipient_email
            
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                msg.attach(text_part)
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            self._log_email(db, recipient_email, template_name, subject, "sent")
            return True
            
        except Exception as e:
            error_msg = str(e)
            self._log_email(db, recipient_email, template_name, subject if 'subject' in locals() else "Unknown", "error", error_msg)
            print(f"Error sending email: {error_msg}")
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
