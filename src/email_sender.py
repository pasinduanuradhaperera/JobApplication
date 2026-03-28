"""
email_sender.py — Sends the application email with the cover letter PDF attached.
Uses TLS (STARTTLS) via Gmail SMTP.  Credentials are read from environment variables.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication


def send_application_email(
    to_address: str,
    subject: str,
    body: str,
    cover_letter_pdf_path: str,
    cv_path: str = "",
) -> None:
    """
    Send an email with PDF attachments (cover letter + optional CV).

    Parameters
    ----------
    to_address           : Recipient email address (hiring manager / HR)
    subject              : Email subject line
    body                 : Plain-text email body
    cover_letter_pdf_path: Absolute path to the cover letter PDF
    cv_path              : Absolute path to the CV PDF (optional)
    """
    from_address = os.environ["EMAIL_ADDRESS"]
    password     = os.environ["EMAIL_PASSWORD"]
    smtp_host    = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port    = int(os.environ.get("SMTP_PORT", 587))

    # Build message
    msg = MIMEMultipart()
    msg["From"]    = from_address
    msg["To"]      = to_address
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    # Attach cover letter PDF
    with open(cover_letter_pdf_path, "rb") as f:
        pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
        pdf_attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=os.path.basename(cover_letter_pdf_path),
        )
        msg.attach(pdf_attachment)

    # Attach CV PDF if provided
    if cv_path and os.path.isfile(cv_path):
        with open(cv_path, "rb") as f:
            cv_attachment = MIMEApplication(f.read(), _subtype="pdf")
            cv_attachment.add_header(
                "Content-Disposition",
                "attachment",
                filename=os.path.basename(cv_path),
            )
            msg.attach(cv_attachment)

    # Send via STARTTLS
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(from_address, password)
        server.sendmail(from_address, to_address, msg.as_string())

    print(f"[email_sender] Email sent to {to_address}")
