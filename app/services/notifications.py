import logging, smtplib
from email.message import EmailMessage
from app.config import settings
logger=logging.getLogger(__name__)
def send_email(to:str, subject:str, body:str, attachment:tuple[str,bytes,str]|None=None):
    if not settings.smtp_username or not settings.smtp_password or not to:
        logger.info('SMTP not configured; skipped email to %s: %s',to,subject); return
    try:
        msg=EmailMessage(); msg['Subject']=subject; msg['From']=settings.smtp_from or settings.smtp_username; msg['To']=to; msg.set_content(body)
        if attachment: msg.add_attachment(attachment[1], maintype=attachment[2].split('/')[0], subtype=attachment[2].split('/')[-1], filename=attachment[0])
        with smtplib.SMTP(settings.smtp_host,settings.smtp_port,timeout=10) as server:
            if settings.smtp_use_tls: server.starttls()
            server.login(settings.smtp_username,settings.smtp_password); server.send_message(msg)
    except Exception: logger.exception('Email delivery failed; main request is not rolled back')
