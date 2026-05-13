import logging

# Configuration for SMTP would go here
# SMTP_SERVER = "smtp.gmail.com"
# SMTP_PORT = 587
# SMTP_USER = "your-email@gmail.com"
# SMTP_PASS = "your-app-password"

class EmailService:
    @staticmethod
    async def send_license_warning(to_email: str, company_name: str, days_left: int, license_key: str):
        """
        In a real scenario, this would use smtplib or an external service like SendGrid/Mailgun.
        For now, we log the action to simulate the email sending.
        """
        subject = f"IMPORTANT: Your NEXUS ERP License is expiring in {days_left} days"
        body = f"""
        Hello {company_name},
        
        This is an automated notification from NEXUS ERP.
        Your system license (Key: {license_key}) is scheduled to expire in {days_left} days.
        
        To avoid service interruption and ensure your data remains accessible, please contact 
        your system administrator to renew your annual subscription.
        
        License Key: {license_key}
        Expiration Date: In {days_left} days.
        
        Thank you for using NEXUS ERP.
        """
        
        # Simulate sending
        logging.info(f"--- EMAIL SENT TO {to_email} ---")
        logging.info(f"Subject: {subject}")
        logging.info(f"Body: {body}")
        logging.info("-------------------------------")
        
        return True

    @staticmethod
    async def send_welcome_license(to_email: str, company_name: str, license_key: str, expiration_date: str):
        subject = f"Welcome to NEXUS ERP - Your License is Active"
        body = f"""
        Hello {company_name},
        
        Your account in NEXUS ERP has been successfully created.
        
        Your License Details:
        License Key: {license_key}
        Expiration Date: {expiration_date}
        
        You can now log in and start managing your business.
        """
        logging.info(f"--- WELCOME EMAIL SENT TO {to_email} ---")
        logging.info(f"Subject: {subject}")
        logging.info("---------------------------------------")
        return True
