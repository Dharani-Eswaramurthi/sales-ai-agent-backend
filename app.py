import ast
from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import Column, String, TIMESTAMP, create_engine, text, ForeignKey, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
import uuid
from datetime import datetime
from email_verifier import find_valid_email
from google_api import google_search
from info_gather import get_company_and_person_info
import openai
import requests
import os
import json
import re
from fastapi.middleware.cors import CORSMiddleware
from Crypto.Cipher import AES
from base64 import b64decode
from base64 import b64decode
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from email_proposal import generate_email

# Database Configuration
DATABASE_URL = "postgresql://user:sales%40123@db-status.postgres.database.azure.com/mail-status"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)
secret_key = os.environ.get('ENCRYPTION_KEY')

Base = declarative_base()

# Email Tracking Model
class EmailStatus(Base):
    __tablename__ = "email_status"
    id = Column(String, primary_key=True)
    dm_name = Column(String, nullable=False)
    company_name = Column(String, nullable=False)
    dm_position = Column(String, nullable=False)
    email_id = Column(String, nullable=False)
    email_subject = Column(String, nullable=False)
    email_body = Column(String, nullable=False)
    email_type = Column(String) 
    status = Column(String, default="Not Responded")
    date_sent = Column(TIMESTAMP, default=datetime.utcnow)
    date_opened = Column(TIMESTAMP)
    sender_name = Column(String, nullable=False)
    sender_company = Column(String, nullable=False)
    sender_position = Column(String, nullable=False)
    sender_email = Column(String)
    product_id = Column(String, ForeignKey('product_details.product_id', ondelete='CASCADE'))

# Follow-up Email Model
class FollowupStatus(Base):
    __tablename__ = "followup_status"
    followup_id = Column(String, ForeignKey('email_status.id', ondelete='CASCADE'), primary_key=True)
    email_uid = Column(String, nullable=False)
    followup_date = Column(TIMESTAMP, nullable=False)
    followup_status = Column(String, nullable=False)
    body = Column(String)
    subject = Column(String)
    followup_sent_count = Column(Integer)
    company_name = Column(String, nullable=False)
    recipient_name = Column(String, nullable=False)
    recipient = Column(String, nullable=False)
    sender_name = Column(String, nullable=False)
    sender_company = Column(String, nullable=False)
    sender_position = Column(String, nullable=False)
    sender_email = Column(String)
    followup_threshold = Column(Integer)
    followup_type = Column(String)


# Product Details Model
class ProductDetails(Base):
    __tablename__ = "product_details"
    product_id = Column(String, primary_key=True, default=text("nextval('product_details_product_id_seq'::regclass)"))
    product_name = Column(String, nullable=False)
    existing_customers = Column(String, nullable=True)
    product_description = Column(String, nullable=True)
    target_min_emp_count = Column(Integer, nullable=True)
    target_max_emp_count = Column(Integer, nullable=True)
    target_industries = Column(String, nullable=True)
    target_geo_loc = Column(String, nullable=True)
    target_business_model = Column(String, nullable=True)
    addressing_pain_points = Column(String, nullable=True)

# Email Configuration
SMTP_SERVER = "smtpout.secureserver.net"
SMTP_PORT = 587
USERNAME = os.environ.get('EMAIL_USERNAME')
PASSWORD = os.environ.get('EMAIL_PASSWORD')


# FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://sales-ai-agent-crm-fgbna0ghdrhxb5hp.centralindia-01.azurewebsites.net"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models
class EmailData(BaseModel):
    recipient_name: str
    company_name: str
    dm_position: str
    recipient: str
    subject: str
    body: str
    sender_name: str
    sender_company: str
    sender_position: str
    product_id: str

class FollowupData(BaseModel):
    email_uid: str
    body: str = None
    subject: str = None
    followup_sent_count: int = 0
    recipient_name: str = None
    company_name: str = None
    sender_name: str = None
    sender_company: str = None
    sender_position: str = None
    recipient: str = None

class ProductRequest(BaseModel):
    product_name: str
    existing_customers: List[str] = None
    product_description: str = None
    product_description: str = None
    target_min_emp_count: int = None
    target_max_emp_count: int = None
    target_industries: List[str] = None
    target_geo_loc: List[str] = None
    target_business_model: List[str] = None
    addressing_pain_points: List[str] = None

class DecisionMakerRequest(BaseModel):
    company_name: str
    domain_name: str

class EmailProposalRequest(BaseModel):
    product_description: str
    company_name: str
    decision_maker: str
    decision_maker_position: str
    sender_name: str
    sender_position: str
    sender_company: str

class ReminderRequest(BaseModel):
    type: str
    sender_name: str
    sender_position: str
    sender_company: str

class TrackedEmail(BaseModel):
    id: str

# OpenAI and Perplexity Configuration
API_KEY = os.getenv("PERPLEXITY_API_KEY")
BASE_URL = "https://api.perplexity.ai/chat/completions"
openai.api_key = os.getenv("OPEN_AI_API_KEY")

@app.post("/potential-companies")
def get_potential_companies(request: ProductRequest):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API Key not configured")
    
    prompt = f"""
                Given the detailed product information and Ideal Client Profile (ICP) provided below, analyze and identify the top five companies with strong growth potential that are likely to be interested in this product. For each company, include the name, industry, and domain. Present the results in JSON format.

                Product Information:
                - Product Name: {request.product_name}
                - Product Description: {request.product_description or 'N/A'}
                - Existing Customers: {', '.join(request.existing_customers) if request.existing_customers else 'N/A'}
                - Target Employee Count: {request.target_min_emp_count or 'N/A'} - {request.target_max_emp_count or 'N/A'}
                - Target Industries: {', '.join(request.target_industries) if request.target_industries else 'N/A'}
                - Target Geographical Locations: {', '.join(request.target_geo_loc) if request.target_geo_loc else 'N/A'}
                - Target Business Models: {', '.join(request.target_business_model) if request.target_business_model else 'N/A'}
                - Addressing Pain Points: {', '.join(request.addressing_pain_points) if request.addressing_pain_points else 'N/A'}

                Output Format:
                (Provide only the list of dictionaries, each containing the name, industry, and company's domain name of the top 5 potential companies, no extra content. Use 'name', 'industry', and 'domain' as the keys. For the domain, format like example.com.)
                """


    payload = {
        "model": "llama-3.1-sonar-large-128k-online",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 200,
    }

    try:
        response = requests.post(
            BASE_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"API request failed: {str(e)}")

    formatted_response = format_response(response.json())
    return formatted_response

@app.post("/potential-decision-makers")
def get_potential_decision_makers(request: DecisionMakerRequest):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API Key not configured")
    
    print("Fetching decision makers for ", request.company_name)
    comp_name = request.company_name
    api_key = 'AIzaSyDWQdpxZHM7Zpft2tMJ_1olqoXthQrlXfo'
    search_engine_id = '82bd22c03bc644768'
    positions = ['CEO', 'Co-CEO', 'VP']
    results = []
    for i in positions:
        query = f"Present {i} at {comp_name} site:linkedin.com"
        result = google_search(api_key, search_engine_id, query, limit=5)  # Set limit to 5
        # Process results
        ref_res = []
        for item in result.get('items', []):
            title = item.get('title')
            snippet = item.get('snippet')
            print(f'Title: {title}\nSnippet: {snippet}\n')
            ref_res.append({'title': title, 'snippet': snippet})
        results.append({i: ref_res})

    print("Results fetched ", results)


    scrapped_docs = []

    # Process results
    for item in results:
        for key, value in item.items():
            for i in value:
                scrapped_docs.append({'name': i['title'], 'position': key})

    print("Scrapped CEO, Co-CEO and VP of the company ", comp_name, " from LinkedIn: ", scrapped_docs)
    
    print("Decision makers details fetched for ", comp_name)

    prompt = f"""
                Given the list of Scrapped CEO, Co-CEO and VP of the company {comp_name} from LinkedIn, please analyse identify the top 3 decision makers who would be the responsible for business decisions. For each decision maker, include the name and title only.

                List of Scrapped CEO, Co-CEO and VP of the company {comp_name} from LinkedIn: {scrapped_docs}

                Output Format:
                ( provide only the dictionary as output of the company {comp_name} with name and title as the key and corresponding value for each decision maker. Strictly without any other extra text or content. )

                """
    
    # Prepare the Perplexity API request payload
    payload = {
        "model": "llama-3.1-sonar-large-128k-online",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 70
    }

    try:
        response = requests.post(
            BASE_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json=payload,
        )

        response.raise_for_status()
    
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"API request failed: {str(e)}")
    
    api_response = format_response(response.json())

    print("Decision makers found and formatted for ", comp_name)

    company = {'name': comp_name, 'decision_maker': None, 'decision_maker_mail': None, 'decision_maker_position': None}

    for i in list(api_response.keys()):
        print("Fetching email of ", i," from the company ", comp_name)
        ref_dm = i
        dm_pos = api_response[i]

        valid_mail = find_valid_email(ref_dm.split(' ')[0], ref_dm.split(' ')[1], request.domain_name)

        if valid_mail:
            company['decision_maker'] = i
            company['decision_maker_mail'] = valid_mail
            company['decision_maker_position'] = dm_pos
            break
        else:
            company['decision_maker'] = api_response
            company['decision_maker_mail'] = None
            company['decision_maker_position'] = None
            continue
            
    return company

@app.post("/email-proposal")
def get_email_proposal(request: EmailProposalRequest):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API Key not configured")
    
    
    print("Fetching email for ", request.decision_maker)
    company_name = request.company_name
    ref_dm = request.decision_maker

    print("Finding the type of Decision maker")

    #find the datatype of decision_maker['decision_maker']
    if type(ref_dm) == str:
        print("True")
        dm_pos = request.decision_maker_position
        # domain = decision_maker['domain']

        response = get_company_and_person_info(request.decision_maker, ref_dm, dm_pos, request.product_description)

        print("Information fetched for ", ref_dm," from the company ", company_name,":", response)

        req_info = format_response(response)

        print("Information fetched for ", ref_dm)

        query = "Personalised Email proposal based on Target Company and Decision Maker"

        situation = "email"

        kwargs = {
                    "product_description": {request.product_description},
                    "company_name": {company_name},
                    "decision_maker": {ref_dm},
                    "decision_maker_position": {dm_pos},
                    "req_info": req_info,
                    "sender_name": {request.sender_name},
                    "sender_position": {request.sender_position},
                    "sender_company": {request.sender_company}
                }


        response = generate_email(query, situation, **kwargs)

        print("Email template generated for", ref_dm)

        # print(response['choices'][0]['message']['content'])
        
        return format_response(response)
        

def format_response(response):
    # Parse and clean JSON output
    json_string = response["choices"][0]["message"]["content"].strip()
    cleaned_json_string = re.sub(r'```(json|)', '', json_string).strip()
    try:
        # Ensure the JSON string is properly formatted
        if not cleaned_json_string.startswith('{') or not cleaned_json_string.endswith('}'):
            raise ValueError("Invalid JSON format")
        return json.loads(cleaned_json_string)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error parsing JSON response: {e}")
        # Attempt to fix common formatting issues
        cleaned_json_string = re.sub(r'(?<!\\)\n', '\\n', cleaned_json_string)
        try:
            return ast.literal_eval(cleaned_json_string)
        except (SyntaxError, ValueError) as e:
            print(f"Error evaluating JSON response: {e}")
            raise HTTPException(status_code=500, detail="Invalid response format from API")


def decrypt_password(encrypted_password: str) -> str:
    secret_key = os.environ.get("ENCRYPTION_KEY")
    iv = os.environ.get("ENCRYPTION_IV")
    if not secret_key or not iv:
        raise ValueError("ENCRYPTION_KEY or ENCRYPTION_IV environment variable is not set")
    
    ciphertext = b64decode(encrypted_password)
    derived_key = b64decode(secret_key)
    cipher = AES.new(derived_key, AES.MODE_CBC, iv.encode('utf-8'))
    decrypted_data = cipher.decrypt(ciphertext)
    return unpad(decrypted_data, 16).decode("utf-8")

@app.post("/send_email")
async def send_email(email: EmailData, user_email: str, encrypted_password: str):
    recipient_name = email.recipient_name
    company_name = email.company_name
    dm_position = email.dm_position
    recipient = email.recipient
    subject = email.subject
    body = email.body.replace('\n', '<br>')  # Replace \n with <br> for line breaks
    # email_type = email.email_type/
    sender_name = email.sender_name
    sender_company = email.sender_company
    sender_position = email.sender_position
    sender_email = user_email
    product_id = email.product_id

    # Debugging: Print the encrypted password received
    print(f"Received Encrypted Password: {encrypted_password}")

    # Decrypt the password
    try:
        decrypted_password = decrypt_password(encrypted_password)
        print(f"Decrypted Password: {decrypted_password}")  # Debugging: Print the decrypted password
    except Exception as e:
        print(f"Decryption Error: {e}")  # Debugging: Print the decryption error
        raise HTTPException(status_code=400, detail="Invalid encrypted password")

    # Generate unique tracking ID
    tracking_id = str(uuid.uuid4())

    # Save tracking info in the database
    try:
        db = SessionLocal()
        new_email = EmailStatus(
            id=tracking_id,
            dm_name=recipient_name,
            company_name=company_name,
            dm_position=dm_position,
            email_id=recipient,
            email_subject=subject,
            email_body=body,
            # email_type=email_type,
            product_id=product_id,
            sender_name=sender_name,
            sender_company=sender_company,
            sender_position=sender_position,
            sender_email=sender_email,
            status="Not Responded",
        )
        db.add(new_email)
        db.commit()
    except Exception as e:
        print(f"Database Error: {e}")  # Debugging: Print the database error
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        db.close()

    # Email content with tracking pixel
    html_body = f"""
    <html>
        <body>
            <p>{body}</p>
            <img src="http://localhost:8000/track/{tracking_id}" width="3" height="3" style="display:none;" />
            <a href="http://localhost:8000/track-response/{tracking_id}/interested">Interested</a><br/>
            <a href="http://localhost:8000/track-response/{tracking_id}/not-interested">Not Interested</a>
        </body>
    </html>
    """

    # Send email
    msg = MIMEMultipart()
    msg['From'] = user_email
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(user_email, decrypted_password)
            server.sendmail(user_email, recipient, msg.as_string())
        return {"message": "Email sent!"}
    except Exception as e:
        print(f"Email Sending Error: {e}")  # Debugging: Print the email sending error
        raise HTTPException(status_code=500, detail=f"Error sending email: {e}")

@app.get("/track/{tracking_id}")
async def track(tracking_id: str):
    # Update the email status to "Not Responded" in the database
    db = SessionLocal()
    email_entry = db.query(EmailStatus).filter(EmailStatus.id == tracking_id).first()

    if email_entry:
        email_entry.status = "Not Responded"
        db.commit()
        db.close()
        print(f"Email with Tracking ID: {tracking_id} has been opened.")
    else:
        db.close()

@app.get("/track-response/{tracking_id}/{response}")
async def track(tracking_id: str, response: str):
    # Update the email status to "Opened" in the database
    db = SessionLocal()
    email_entry = db.query(EmailStatus).filter(EmailStatus.id == tracking_id).first()

    if email_entry and response == "interested":
        email_entry.status = "Interested"
        db.commit()
        db.close()
        print(f"Email with Tracking ID: {tracking_id} has been opened and interested")
        #return a html page with a thank you message
        return FileResponse("interested.html")
    
    elif email_entry and response == "not-interested":
        email_entry.status = "Not Interested"
        db.commit()
        db.close()
        print(f"Email with Tracking ID: {tracking_id} has been opened but not interested")
        return FileResponse("not-interested.html")

    else:
        db.close()

@app.post("/email-reminder")
def get_email_reminder(tracking_id: str, request: ReminderRequest):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API Key not configured")
    
    db = SessionLocal()

    email = db.query(EmailStatus).filter(EmailStatus.id == tracking_id).first()

    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    company_name = email.company_name
    decision_maker = email.dm_name
    body = email.email_body
    product_description = db.query(ProductDetails).filter(ProductDetails.product_id == email.product_id).first().product_description
    dm_pos = email.dm_position
    response = get_company_and_person_info(decision_maker, decision_maker, dm_pos, product_description)

    print("Information fetched for ", decision_maker," from the company ", company_name,":", response)

    req_info = format_response(response)

    query = f"Personalised {request.type[0].upper() + request.type[1:]} proposal based on Target Company and Decision Maker"

    situation = request.type

    kwargs = {
                "product_description": {product_description},
                "company_name": {company_name},
                "decision_maker": {decision_maker},
                "decision_maker_position": {dm_pos},
                "req_info": req_info,
                "sender_name": {request.sender_name},
                "sender_position": {request.sender_position},
                "sender_company": {request.sender_company}
            }


    response = generate_email(query, situation, **kwargs)

    formatted_response = format_response(response)

    subject = formatted_response.get("subject")
    body = formatted_response.get("body")

    return {"subject": subject, "body": body}

@app.post('/update-followup')
def update_followup(followup_id: str, followup_field: str, field_value: str):
    db = SessionLocal()
    followup = db.query(FollowupStatus).filter(FollowupStatus.followup_id == followup_id).first()
    if not followup:
        raise HTTPException(status_code=404, detail="Followup not found")

    setattr(followup, followup_field, field_value)
    db.commit()
    db.close()
    return {"message": "Followup updated successfully"}


@app.post("/send_followup_email")
async def send_followup_email(user_email: str, encrypted_password: str, followup: FollowupData):
    db = SessionLocal()
    try:
        followup_data = db.query(FollowupStatus).filter(FollowupStatus.email_uid == followup.email_uid).first()
        if not followup_data:
            # insert a followup mail
            new_followup = FollowupStatus(
                followup_id=str(uuid.uuid4()),
                email_uid=followup.email_uid,
                followup_date=datetime.utcnow(),
                followup_status="Not Responded",
                body=followup.body,
                subject=followup.subject,
                followup_sent_count=1,
                recipient_name=followup.recipient_name,
                company_name=followup.company_name,
                sender_name=followup.sender_name,
                sender_company=followup.sender_company,
                sender_position=followup.sender_position,
                sender_email=user_email,
                sender_threshold=2,
                recipient=followup.recipient,
                followup_type="Followup Mail"
            )
            db.add(new_followup)
            db.commit()
        
        else:
            # update the followup mail
            followup_data.followup_date = datetime.utcnow()
            followup_data.followup_status = "Not Responded"
            followup_data.body = followup.body
            followup_data.subject = followup.subject
            followup_data.followup_sent_count += 1
            db.commit()

        # Decrypt the password
        decrypted_password = decrypt_password(encrypted_password)

        # Send follow-up email
        msg = MIMEMultipart()
        msg['From'] = user_email
        msg['To'] = followup.recipient
        msg['Subject'] = followup.subject
        msg.attach(MIMEText(followup.body, 'html'))

        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(user_email, decrypted_password)
                server.sendmail(user_email, followup.recipient, msg.as_string())

            return {"message": "Follow-up email sent!"}
        except Exception as e:
            db.commit()
            return {"message": "Follow-up email sent!"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error sending follow-up email: {e}")
    finally:
        db.close()

@app.get("/status")
def status():
    # Fetch tracked emails
    db = SessionLocal()
    tracked_emails = db.query(EmailStatus).all()
    db.close()
    return {
        "tracked_emails": [
            {
                "id": email.id,
                "email_id": email.email_id,
                "email_subject": email.email_subject,
                "email_body": email.email_body,
                "email_datesent": email.date_sent,
                "status": email.status,
            }
            for email in tracked_emails
        ]
    }

@app.get("/fetch-mail-status")
def fetch_mail_status():
    db = SessionLocal()
    email_statuses = db.query(EmailStatus).all()
    product_details = {product.product_id: product.product_name for product in db.query(ProductDetails).all()}
    followup = {followup.email_uid: {"status": followup.followup_status,
                                     "followup_id": followup.followup_id,
                                     "date_sent": followup.followup_date, 
                                     "followup_sent_count": followup.followup_sent_count, 
                                     "sender_name": followup.sender_name,
                                     "sender_company": followup.sender_company,
                                     "sender_position": followup.sender_position,
                                     "sender_email": followup.sender_email,
                                     "followup_threshold": followup.followup_threshold
                                     } for followup in db.query(FollowupStatus).all()}
    db.close()
    
    result = []
    for email in email_statuses:
        followup_data = followup.get(email.id, "No Followup")
        result.append({
            "id": email.id,
            "followup_id": followup_data['followup_id'] if followup_data != "No Followup" else None,
            "dm_name": email.dm_name,
            "company_name": email.company_name,
            "dm_position": email.dm_position,
            "email_id": email.email_id,
            "email_subject": email.email_subject,
            "sender_name": followup_data['sender_name'] if followup_data != "No Followup" else email.sender_name,
            "sender_company": followup_data['sender_company'] if followup_data != "No Followup" else email.sender_company,
            "sender_position": followup_data['sender_position'] if followup_data != "No Followup" else email.sender_position,
            "sender_email": followup_data['sender_email'] if followup_data != "No Followup" else email.sender_email,
            "followup_threshold": followup_data['followup_threshold'] if followup_data != "No Followup" else 0,
            "email_body": email.email_body,
            "followup_sent_count": followup_data['followup_sent_count'] if followup_data != "No Followup" else 0,
            "status": followup_data['status'] if followup_data != "No Followup" else email.status,
            "date_sent": followup_data['date_sent'] if followup_data != "No Followup" else email.date_sent,
            "product_id": email.product_id,
            "product_name": product_details.get(email.product_id, "Unknown")
        })
    
    return result

@app.get("/email-status-check")
def check_email_status(tracking_id: str):
    current_time = datetime.utcnow()

    # Open the session
    db = SessionLocal()
    try:
        email = db.query(EmailStatus).filter(EmailStatus.id == tracking_id).first()
        followup = db.query(FollowupStatus).filter(FollowupStatus.email_uid == tracking_id).first()
        followup_threshold = db.query(FollowupStatus).filter(FollowupStatus.email_uid == tracking_id).first().followup_threshold

        if not email:
            return {"error": "Email with the provided tracking ID not found."}

        if followup:
            date_sent = followup.followup_date
            status = followup.followup_status
        else:
            date_sent = email.date_sent
            status = email.status

        time_difference = current_time - date_sent
        days_difference = time_difference.days

        if days_difference > followup_threshold and status != "Not Interested":
            status = "Send Reminder"
            if followup:
                followup.followup_status = "Send Reminder"
                db.commit()
            else:
                email.status = "Send Reminder"
                db.commit()
            return {
                "email_id": email.email_id,
                "status": f"Need to send a reminder as the email was sent {days_difference} days ago",
                "days_since_sent": days_difference
            }
        else:
            return {
                "email_id": email.email_id,
                "status": status,
                "days_since_sent": days_difference
            }
    finally:
        # Ensure the session is closed after the operation
        db.close()

@app.delete("/delete-entity/{id}")
def delete_entity(id: str):
    db = SessionLocal()
    try:
        email_entry = db.query(EmailStatus).filter(EmailStatus.id == id).first()
        if not email_entry:
            raise HTTPException(status_code=404, detail="Entity not found")
        db.delete(email_entry)
        db.commit()
        return {"message": "Entity deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting entity: {e}")
    finally:
        db.close()

@app.post("/add_product")
def add_product(request: ProductRequest):
    db = SessionLocal()
    try:
        new_product = ProductDetails(
            product_name=request.product_name,
            existing_customers=request.existing_customers,
            product_description=request.product_description,
            target_min_emp_count=request.target_min_emp_count,
            target_max_emp_count=request.target_max_emp_count,
            target_industries=request.target_industries,
            target_geo_loc=request.target_geo_loc,
            target_business_model=request.target_business_model,
            addressing_pain_points=request.addressing_pain_points
        )
        db.add(new_product)
        db.commit()
        return {"message": "Product added successfully", "product_id": new_product.product_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error adding product: {e}")
    finally:
        db.close()

@app.get("/get_products")
def get_products():
    db = SessionLocal()
    try:
        products = db.query(ProductDetails).all()
        return [
            {
                "product_id": product.product_id,
                "product_name": product.product_name,
                "existing_customers": product.existing_customers,
                "product_description": product.product_description,
                "target_min_emp_count": product.target_min_emp_count,
                "target_max_emp_count": product.target_max_emp_count,
                "target_industries": product.target_industries,
                "target_geo_loc": product.target_geo_loc,
                "target_business_model": product.target_business_model,
                "addressing_pain_points": product.addressing_pain_points
            }
            for product in products
        ]
    finally:
        db.close()

@app.get("/get_single_product/{product_id}")
def get_existing_customers(product_id: str):
    db = SessionLocal()
    try:
        # Fetch the product details
        product = db.query(ProductDetails).filter(ProductDetails.product_id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Fetch the company names whose decision makers are interested in the product
        interested_companies = db.query(EmailStatus.company_name).filter(
            EmailStatus.product_id == product_id,
            EmailStatus.status == "Interested"
        ).distinct().all()

        # Extract company names from the query result
        company_names = [company[0] for company in interested_companies]

        # update existing_customers field in the product details with company names
        product.existing_customers = company_names
        db.commit()

        # return the updated product details
        return {
            "product_id": product.product_id,
            "product_name": product.product_name,
            "existing_customers": product.existing_customers,
            "product_description": product.product_description,
            "target_min_emp_count": product.target_min_emp_count,
            "target_max_emp_count": product.target_max_emp_count,
            "target_industries": product.target_industries,
            "target_geo_loc": product.target_geo_loc,
            "target_business_model": product.target_business_model,
            "addressing_pain_points": product.addressing_pain_points
        }

    finally:
        db.close()

@app.put("/update_product/{product_id}")
def update_product(product_id: str, request: ProductRequest):
    db = SessionLocal()
    try:
        # Fetch the product details
        product = db.query(ProductDetails).filter(ProductDetails.product_id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Update the product details
        product.product_name = request.product_name
        product.existing_customers = request.existing_customers
        product.product_description = request.product_description
        product.target_min_emp_count = request.target_min_emp_count
        product.target_max_emp_count = request.target_max_emp_count
        product.target_industries = request.target_industries
        product.target_geo_loc = request.target_geo_loc
        product.target_business_model = request.target_business_model
        product.addressing_pain_points = request.addressing_pain_points

        db.commit()

        # Return the updated product details
        return {
            "product_id": product.product_id,
            "product_name": product.product_name,
            "existing_customers": product.existing_customers,
            "product_description": product.product_description,
            "target_min_emp_count": product.target_min_emp_count,
            "target_max_emp_count": product.target_max_emp_count,
            "target_industries": product.target_industries,
            "target_geo_loc": product.target_geo_loc,
            "target_business_model": product.target_business_model,
            "addressing_pain_points": product.addressing_pain_points
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating product: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)