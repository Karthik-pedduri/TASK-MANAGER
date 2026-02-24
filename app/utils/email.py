import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings

async def send_email_async(subject: str, body: str, to_email: str | None = None):
    """
    Asynchronous email sending function using aiosmtplib.
    """
    try:
        if not settings.EMAIL_HOST:
            print(f"[EMAIL SKIPPED] Config missing - {subject[:50]}...")
            return
            
        if not to_email:
            to_email = settings.EMAIL_TO
            
        msg = MIMEMultipart()
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        # Send asynchronously using STARTTLS (common for port 587)
        # Note: hostname/port/username/password come from our config
        await aiosmtplib.send(
            msg,
            hostname=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=settings.EMAIL_USER,
            password=settings.EMAIL_PASS,
            start_tls=True,
            timeout=10
        )
        print(f"[EMAIL SENT] To {msg['To']}: {subject}")
    except Exception as e:
        # Silently fail to prevent blocking the application worker
        print(f"[EMAIL FAILED] {e} - {subject[:50]}...")