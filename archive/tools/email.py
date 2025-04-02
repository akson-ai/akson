import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from langchain_core.tools import tool


@tool
def send_email(to: str, subject: str, body: str):
    """Sends an email. Input is treated as HTML."""
    msg = MIMEMultipart()
    msg["From"] = os.environ["ZOHO_SMTP_EMAIL"]
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))

    with smtplib.SMTP_SSL("smtp.zoho.com", 465) as server:
        server.login(os.environ["ZOHO_SMTP_EMAIL"], os.environ["ZOHO_SMTP_PASSWORD"])
        server.sendmail(msg["From"], msg["To"], msg.as_string())
        server.quit()
