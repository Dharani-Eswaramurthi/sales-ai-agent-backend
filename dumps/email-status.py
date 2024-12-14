from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import Column, String, Boolean, TIMESTAMP, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import uuid
from datetime import datetime

app = FastAPI()

# Database Configuration
DATABASE_URL = "postgresql://user:sales%40123@db-status.postgres.database.azure.com/mail-status"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)

Base = declarative_base()

# Email Tracking Model
class EmailStatus(Base):
    __tablename__ = "email_status"
    id = Column(String, primary_key=True)
    email_id = Column(String, nullable=False)
    email_subject = Column(String)
    email_body = Column(String)
    status = Column(String, default="Not Opened")
    date_sent = Column(TIMESTAMP, default=datetime.utcnow)

# Create the table
Base.metadata.create_all(bind=engine)

# Replace with your email configuration
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
USERNAME = 'dharani96556@gmail.com'
PASSWORD = 'ujcu lwca ouch knvf'  # Ensure this is the correct app password

# Pydantic model for email body data
class EmailData(BaseModel):
    recipient: str
    subject: str
    body: str

@app.post("/send_email")
async def send_email(email: EmailData):
    recipient = email.recipient
    subject = email.subject
    body = email.body

    # Generate a unique tracking ID
    tracking_id = str(uuid.uuid4())

    # Insert the tracking info into the database
    db = SessionLocal()
    new_email = EmailStatus(
        id=tracking_id,
        email_id=recipient,
        email_subject=subject,
        email_body=body,
        status="Not Opened",
    )
    db.add(new_email)
    db.commit()
    db.close()

    # Create the email content with tracking pixel
    html_body = f"""
    <html>
        <body>
            <p>{body}</p>
            <img src="http://localhost:8000/track/{tracking_id}" width="1" height="1" style="display:none;" />
        </body>
    </html>
    """

    # Send the email
    msg = MIMEMultipart()
    msg['From'] = USERNAME
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(USERNAME, PASSWORD)
            server.sendmail(USERNAME, recipient, msg.as_string())
        return {"message": "Email sent!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending email: {e}")

@app.get("/track/{tracking_id}")
async def track(tracking_id: str):
    # Update the email status to "Opened" in the database
    db = SessionLocal()
    email_entry = db.query(EmailStatus).filter(EmailStatus.id == tracking_id).first()

    if email_entry:
        email_entry.status = "Opened"
        db.commit()
        db.close()
        print(f"Email with Tracking ID: {tracking_id} has been opened.")
    else:
        db.close()

    # Return a tiny transparent image (1x1 pixel)
    return FileResponse('path/to/transparent_pixel.png', media_type='image/png')

def status():
    # Fetch all tracked emails from the database
    db = SessionLocal()
    tracked_emails = db.query(EmailStatus).all()
    db.close()
    return {"tracked_emails": [{"id": email.id, "email_id": email.email_id, "email_subject": email.email_subject, "email_body": email.email_body,  "status": email.status} for email in tracked_emails]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
