import ast
from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import Column, String, TIMESTAMP, Integer, create_engine
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

# Database Configuration
DATABASE_URL = "postgresql://user:sales%40123@db-status.postgres.database.azure.com/mail-status"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)

Base = declarative_base()

# Email Tracking Model
class EmailStatus(Base):
    __tablename__ = "email_status"
    id = Column(String, primary_key=True)
    dm_name = Column(String)
    company_name = Column(String)
    dm_position = Column(String)
    email_id = Column(String, nullable=False)
    email_subject = Column(String)
    email_body = Column(String)
    status = Column(String, default="Not Responded")
    date_sent = Column(TIMESTAMP, default=datetime.utcnow)
    date_opened = Column(TIMESTAMP)

#Followup status
class FollowupStatus(Base):
    __tablename__ = "followup_status"
    followup_id = Column(String, primary_key=True)
    email_id = Column(String, nullable=False)
    subject = Column(String)
    body = Column(String)
    followup_status = Column(String, default="Not Responded")
    followup_sent_count = Column(Integer)
    followup_date = Column(TIMESTAMP, default=datetime.utcnow,)


# Create the table
Base.metadata.create_all(bind=engine)

# Email Configuration
SMTP_SERVER = os.environ.get('SMTP_SERVER') 
SMTP_PORT = os.environ.get('SMTP_PORT')
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
    email_type: str = "Cold Email"

class ProductRequest(BaseModel):
    product_description: str
    icp: dict

class DecisionMakerRequest(BaseModel):
    company_name: str
    domain_name: str

class EmailProposalRequest(BaseModel):
    product_description: str
    company_name: str
    decision_maker: str
    decision_maker_position: str

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
                Given the product description and Ideal Client Profile (ICP) detailed below, please analyse and identify the list of top five companies that demonstrate strong growth potential and would likely be interested in this product. For each company, include the name, industry. Present the results in JSON format.
                Product Description: {request.product_description}
                Ideal Client Profile (ICP): {request.icp}

                Output Format: 
                ( provide only the list of dictionaries, each containing the name, industry and company's domain name of top 5 potential companies, no extra content )

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

                List of Scrapped CEO, Co-CEO and VP of the compnay {comp_name} from LinkedIn: {scrapped_docs}

                Output Format:
                ( provide only the dictionary as output of the company {comp_name} with name and title as the key and corresponding value, strictly without any other extra text or content. )

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

    # Make the API request
    try:
        response = requests.post(
            BASE_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"API request failed: {str(e)}")
    
    # Parse the API response
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


        elif i == list(api_response.keys())[-1] and not valid_mail:
            raise HTTPException(status_code=404, detail="Email not found for the decision maker")
            
            
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

        prompt = f"""
                    Product Description: {request.product_description}
                    Target Company details and Decision Maker details: {req_info}

                    Follow the below steps to get the necessary information:
                    1. Understand the provided product description alongwith the company {company_name}'s pain points.
                    2. Now understand the gathered information of the target company {company_name} and the target decision maker {ref_dm} who is the {dm_pos} of the company {company_name}.
                    3. Now craft a casual engaging yet human-like business email tailored to the recipient's profile and company's latest news and updates that enhance their existing feature or overcome an issue. The mail should be tailored to only the target decision maker preferences and interests.

                    Output Format:
                    ( provide only json of subject and body of the email, strictly without any other extra text or content. )

                    NOTE: Enclose multiple lines of the email body in a triple quotes( ''' ).

                    """

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a professional email writer who crafts persuasive and engaging business emails tailored "
                    "to the recipient's profile and company context."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        print("Starting to generate email template for", ref_dm)
        openai.api_key = os.getenv("OPEN_AI_API_KEY")

        response = openai.ChatCompletion.create(
            model="gpt-4",  # Best GPT model for this task
            messages=messages,
            max_tokens=400,
            temperature=0.7
        )

        print("Email template generated for", ref_dm)

        return format_response(response)

def format_response(response):
    # Parse and clean JSON output
    json_string = response["choices"][0]["message"]["content"]
    cleaned_json_string = re.sub(r'```(json|)', '', json_string).strip()
    try:
        print("Cleaned JSON String: ", cleaned_json_string)
        return json.loads(cleaned_json_string)
    except Exception as e:
        cleaned_json_string = re.sub(r'(?<!\\)\n', '\\n', json_string)
        return ast.literal_eval(cleaned_json_string)

@app.post("/send_email")
async def send_email(email: EmailData, tracking_id: str = None):
    recipient_name = ''
    company_name = ''
    dm_position = ''
    recipient = email.recipient
    subject = email.subject
    body = email.body
    email_type = email.email_type

    db = SessionLocal()

    if email_type == "Cold Email":  # Generate unique tracking ID
        tracking_id = str(uuid.uuid4())
        recipient_name = email.recipient_name
        company_name = email.company_name
        dm_position = email.dm_position

        new_email = EmailStatus(
            id=tracking_id,
            dm_name=recipient_name,
            company_name=company_name,
            dm_position=dm_position,
            email_id=recipient,
            email_subject=subject,
            email_body=body,
            status="Not Responded",
        )
        db.add(new_email)
    else:
        email_entry = db.query(EmailStatus).filter(EmailStatus.id == tracking_id).first()
        if not email_entry:
            raise HTTPException(status_code=404, detail="Email entry not found")

        try:
            if_old_followup = db.query(FollowupStatus).filter(FollowupStatus.followup_id == tracking_id).first()
            new_followup = FollowupStatus(
                followup_id=tracking_id,
                email_id=email_entry.email_id,
                subject=subject,
                body=body,
                followup_status="Not Responded",
                followup_sent_count=1,
            )
            if if_old_followup:
                db.query(FollowupStatus).filter(FollowupStatus.followup_id == tracking_id).update(
                    {
                        "subject": subject,
                        "body": body,
                        "followup_status": "Not Responded",
                        "followup_sent_count": if_old_followup.followup_sent_count + 1,
                    }
                )
            
            else:
                db.add(new_followup)

            recipient = email_entry.email_id
            subject = subject
            body = body
            recipient_name = email_entry.dm_name
            company_name = email_entry.company_name
            dm_position = email_entry.dm_position


        except Exception as e:
            followup_entry = db.query(FollowupStatus).filter(FollowupStatus.followup_id == tracking_id).first()
            if not followup_entry:
                raise HTTPException(status_code=404, detail="Follow-up entry not found")

            followup_sent_count = followup_entry.followup_sent_count + 1

            db.query(FollowupStatus).filter(FollowupStatus.followup_id == tracking_id).update(
                {
                    "subject": subject,
                    "body": body,
                    "followup_status": "Not Responded",
                    "followup_sent_count": followup_sent_count,
                }
            )

    # Save tracking info in the database
    db.commit()
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
        email_entry.date_opened = datetime.utcnow()
        db.close()

@app.post("/email-reminder")
def get_email_reminder(tracking_id: str):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API Key not configured")
    
    db = SessionLocal()

    email = db.query(EmailStatus).filter(EmailStatus.id == tracking_id).first()

    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    company_name = email.company_name
    decision_maker = email.dm_name
    body = email.email_body


    prompt = f"""
                Given the company {company_name} and the decision maker {decision_maker}, please craft a follow-up email reminder to re-engage the recipient based on the previous mail sent {body}. The email should be polite, concise and should encourage the recipient to take action.

                Output Format:
                ( provide only json of subject and body, strictly without any other extra text or content. )

                NOTE: Strictly Enclose multiple lines of the email body only in a triple quotes( ''' ) and not in double quotes(").
                    
                    """
    
    messages = [
        {
            "role": "system",
            "content": (
                "You are a professional email writer who crafts persuasive and engaging business emails tailored "
                "to the recipient's profile and company context."
            )
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    response = openai.ChatCompletion.create(
        model="gpt-4",  # Best GPT model for this task
        messages=messages,
        max_tokens=400,
        temperature=0.7
    )

    return format_response(response)


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
    followup_statuses = db.query(FollowupStatus).all()
    db.close()

    followup_dict = {followup.followup_id: {'followup_status': followup.followup_status, 'followup_sent_count': followup.followup_sent_count, 'followup_date': followup.followup_date} for followup in followup_statuses}

    print("samble",followup_dict)

    return [
        {
            "id": email.id,
            "dm_name": email.dm_name,
            "company_name": email.company_name,
            "dm_position": email.dm_position,
            "email_id": email.email_id,
            "status": email.status,
            "date_sent": email.date_sent,
            "date_opened": email.date_opened,
            "followup_status": followup_dict.get(email.id, {}).get("followup_status", None),
            "followup_sent_count": followup_dict.get(email.id, {}).get("followup_sent_count", 0),
            "followup_date": followup_dict.get(email.id, {}).get("followup_date", None),
        }
        for email in email_statuses
    ]

@app.get("/email-status-check")
def check_email_status(tracking_id: str):
    current_time = datetime.utcnow()

    # Open the session
    db = SessionLocal()
    try:
        email = db.query(EmailStatus).filter(EmailStatus.id == tracking_id).first()

        if not email:
            return {"error": "Email with the provided tracking ID not found."}

        date_sent = email.date_sent
        time_difference = current_time - date_sent
        days_difference = time_difference.days

        if days_difference > 2 and email.status == "Not Responded":
            email.status = "Send Reminder"
            db.commit()
            return {
                "email_id": email.email_id,
                "status": f"Need to send a reminder as the email was sent {days_difference} days ago",
                "days_since_sent": days_difference
            }
        else:

            if email.status == "Send Reminder":
                followup = db.query(FollowupStatus).filter(FollowupStatus.followup_id == tracking_id).first()

                if not followup:
                    return {"error": "Followup with the provided tracking ID not found."}
                
                date_sent = followup.followup_date
                time_difference = current_time - date_sent
                days_difference = time_difference.days
                followup_sent_count = followup.followup_sent_count

                if days_difference > 2 and (followup.followup_status == "Not Responded" or followup.followup_status == "Send Another Reminder"):
                    followup.followup_status = "Send Another Reminder"
                    db.commit()
                    return {
                        "email_id": followup.email_id,
                        "status": f"Already {followup_sent_count} followups sent. Need to send another reminder as the older followup was sent {days_difference} days ago",
                        "days_since_sent": days_difference
                    }

            return {
                "email_id": email.email_id,
                "status": email.status,
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
