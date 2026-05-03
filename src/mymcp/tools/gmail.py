import os
import smtplib
from email.mime.text import MIMEText

from mymcp.utils import is_valid_html

def send_email(receiver, subject: str, body:str):
    """
    Send an email through Gmail.

    The content of 'body'can either be plain text, or html code.

    Args:
        receiver (str): The email address of the recipient.
        body (str): The body of the email. Can be plain text or HTML.

    Returns:
        str: A message indicating that the email was sent successfully.
    """
    
    # Requires GMail credentials
    assert "GOOGLE_GMAIL_SENDER" in os.environ, f"Error, environment variable 'GOOGLE_GMAIL_SENDER' not set"
    assert "GOOGLE_GMAIL_PASSWORD" in os.environ, f"Error, environment variable 'GOOGLE_GMAIL_PASSWORD' not set"
    
    sender = os.environ["GOOGLE_GMAIL_SENDER"]
    app_password = os.environ["GOOGLE_GMAIL_PASSWORD"]
    
    content_type = 'html' if is_valid_html(body) else 'plain'
    
    msg = MIMEText(body, content_type)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = receiver

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, app_password)
        smtp.sendmail(sender, receiver, msg.as_string())

    return f"Sent e-mail of type '{content_type}' to {receiver}"
