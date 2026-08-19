import smtplib
from email.message import EmailMessage

from app.config.settings import settings

def send_password_reset_email(to_email: str, reset_url: str):
    # If SMTP is not configured, print the reset URL for local development.
    if not settings.SMTP_HOST or not settings.SMTP_FROM:
        print(f"[DEV] Password reset URL for {to_email}: {reset_url}")
        return

    msg = EmailMessage()
    msg["Subject"] = "Password Reset"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg.set_content(f"Use this link to reset your password:\n\n{reset_url}\n\nThis link expires soon.")

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        if settings.SMTP_USERNAME:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)
