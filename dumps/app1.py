from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai
import requests
import os
import json
from email_verifier import find_valid_email
import re
from google_api import google_search
from info_gather import get_company_and_person_info, chat_completion
from send_email import send_email

# Load Perplexity API key from environment variables
API_KEY = os.getenv("PERPLEXITY_API_KEY")


BASE_URL = "https://api.perplexity.ai/chat/completions"

# FastAPI app
app = FastAPI()

# Input model for client request
class ProductRequest(BaseModel):
    product_description: str
    icp: dict  # Dictionary containing ICP details like industry, company size, etc.

class DecisionMakerRequest(BaseModel):
    product_description: str
    potential_companies: list



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

    # Prepare the Perplexity API request payload
    payload = {
        "model": "llama-3.1-sonar-large-128k-online",
        "messages": [
            {"role": "system", "content": "Provide only json as the output no other extra text or content"},
            {
                "role": "user",
                "content": prompt
            },
        ],
        "max_tokens": 200,
        "temperature": 0,
        "top_p": 0.9,
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
    # raw_companies = api_response.get("companies", [])

    # # Format the output to only include name and industry
    # formatted_companies = [
    #     {"name": company.get("name", "Unknown"), "industry": company.get("industry", "Unknown")}
    #     for company in raw_companies[:10]  # Limit to the top 10 companies
    # ]

    # Return the formatted output
    return api_response

@app.post("/potential-decision-makers")
def get_potential_decision_makers(request: DecisionMakerRequest):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API Key not configured")
    
    potential_companies = request.potential_companies

    for company in potential_companies:
        print("Fetching decision makers for ", company['name'])
        comp_name = company['name']
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
                {"role": "system", "content": "Provide only json as the output no other extra text or content"},
                {
                    "role": "user",
                    "content": prompt
                },
            ],
            "max_tokens": 70,
            "temperature": 0,
            "top_p": 0.9,
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

        for i in list(api_response.keys()):
            print("Fetching email of ", i," from the company ", comp_name)
            ref_dm = i
            dm_pos = api_response[i]

            valid_mail = find_valid_email(ref_dm.split(' ')[0], ref_dm.split(' ')[1], company['domain'])

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
            
    return potential_companies

# @app.post("/decision-makers")
# def get_decision_makers(request: DecisionMakerRequest):
#     if not API_KEY:
#         raise HTTPException(status_code=500, detail="API Key not configured")
    
#     all_scrapped_docs = []
    
#     for company in request.potential_companies:
#         api_key = 'AIzaSyDWQdpxZHM7Zpft2tMJ_1olqoXthQrlXfo'
#         search_engine_id = '339420fe807de47c2'
#         comp_name = company['name']
#         query = f'''CEO of {comp_name} AND Co-CEO of {comp_name} AND VP of {comp_name} AND site:linkedin.com'''
#         results = google_search(api_key, search_engine_id, query, limit=15)  # Set limit to 5

#         scrapped_docs = []

#         # Process results
#         for item in results.get('items', []):
#             title = item.get('title')
#             snippet = item.get('snippet')
#             scrapped_docs.append({'title': title, 'snippet': snippet})
        
#         all_scrapped_docs.append({comp_name: scrapped_docs})
    
#     print(all_scrapped_docs)

    
#     prompt = f"""
#                 Given the list of Scrapped CEO, Co-CEO and VP of each company from LinkedIn, please analyse identify the top 3 decision makers who would be the responsible for business decisions. For each decision maker, include the name and title only.

#                 List of Scrapped CEO, Co-CEO and VP of each company from LinkedIn: {all_scrapped_docs}

#                 Output Format: 
#                 ( provide only the list of dictionaries as output of company name as key and a dictionary with name and title as the key and corresponding value, strictly without any other extra text or content. )

#                 """

#     # Prepare the Perplexity API request payload
#     payload = {
#         "model": "llama-3.1-sonar-large-128k-online",
#         "messages": [
#             {"role": "system", "content": "Provide only json as the output no other extra text or content"},
#             {
#                 "role": "user",
#                 "content": prompt
#             },
#         ],
#         "max_tokens": 600,
#         "temperature": 0,
#         "top_p": 0.9,
#     }

#     # Make the API request
#     try:
#         response = requests.post(
#             BASE_URL,
#             headers={
#                 "Authorization": f"Bearer {API_KEY}",
#                 "Content-Type": "application/json",
#             },
#             json=payload,
#         )
#         response.raise_for_status()
#     except requests.exceptions.RequestException as e:
#         raise HTTPException(status_code=500, detail=f"API request failed: {str(e)}")

#     # Parse the API response
#     api_response = format_response(response.json())
#     # raw_companies = api_response.get("companies", [])

#     # # Format the output to only include name and industry
#     # formatted_companies = [
#     #     {"name": company.get("name", "Unknown"), "industry": company.get("industry", "Unknown")}
#     #     for company in raw_companies[:10]  # Limit to the top 10 companies
#     # ]

#     # Return the formatted output
#     return api_response

def format_response(response):
    # Extract the JSON string from the content field
    json_string = response["choices"][0]["message"]["content"]
    
    # Remove the surrounding Markdown formatting (```json ... ```)
    cleaned_json_string = json_string.strip("```json").strip("```").strip()
    
    # Check if the cleaned string is empty
    if not cleaned_json_string:
        raise ValueError("The cleaned JSON string is empty.")
    
    # Remove comments (anything after // in the JSON string)
    cleaned_json_string = re.sub(r'//.*$', '', cleaned_json_string, flags=re.MULTILINE)
    
    # Check if the cleaned string is still empty after removing comments
    if not cleaned_json_string:
        raise ValueError("The cleaned JSON string is empty after removing comments.")
    
    # Parse the JSON string into a Python object
    try:
        formatted_list = json.loads(cleaned_json_string)
    except json.JSONDecodeError as e:
        raise ValueError(f"Error decoding JSON: {e} | Response: {cleaned_json_string}")
    
    # Return the result
    return formatted_list

# @app.post("/email-finder")
# def find_email(request: EmailFinderRequest):
#     decision_makers = request.potential_decision_makers
#     valid_emails=[]
#     dm = 0
#     for i in range(len(decision_makers)):
#         first_name = decision_makers[i][list(decision_makers[i].keys())[dm]]["name"].strip().split(" ")[0]
#         last_name = decision_makers[i][list(decision_makers[i].keys())[dm]]["name"].strip().split(" ")[1]
#         domain = ""
#         print(i+1,' emails fetching')
#         for j in range(len(request.potential_companies)):
#             if(list(decision_makers[i].keys())[dm] == request.potential_companies[j]["name"]):
#                 domain = request.potential_companies[j]["domain"]
#                 break
#         print("For ",list(decision_makers[i].keys())[dm]," domain is ",domain)
#         email = find_valid_email(first_name, last_name, domain)
#         while email == None and dm<3:
#             dm+=1
#             break
        
#         else:
#             print(i+1,' emails fetched')
#             ref_dict = {
#                 "company": list(decision_makers[i].keys())[dm],
#                 "name": decision_makers[i][list(decision_makers[i].keys())[dm]]["name"],
#                 "email": email
#             }
#             valid_emails.append(ref_dict)
            
            

#     if valid_emails:
#         return valid_emails
#     else:
#         raise HTTPException(status_code=404, detail="Email not found")

@app.post("/email-proposal")
def get_email_proposal(request: DecisionMakerRequest):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API Key not configured")
    
    potential_decision_makers = request.potential_companies

    for decision_maker in potential_decision_makers:
        print("Fetching email for ", decision_maker['name'])
        company_name = decision_maker['name']
        ref_dm = decision_maker['decision_maker']

        print("Finding the type of Decision maker")

        #find the datatype of decision_maker['decision_maker']
        if type(ref_dm) == str:
            print("True")
            dm_pos = decision_maker['decision_maker_position']
            # domain = decision_maker['domain']

            response = get_company_and_person_info(decision_maker['name'], ref_dm, dm_pos, request.product_description)

            req_info = format_response(response)

            print("Information fetched for ", ref_dm)

            prompt = f"""
                        Product Description: {request.product_description}
                        Pain Points of {company_name}: {req_info['pain points']}
                        Target Company details and Decision Maker details: {req_info}

                        Follow the below steps to get the necessary information:
                        1. Understand the provided product description alongwith the company {company_name}'s pain points.
                        2. Now understand the gathered information of the target company {company_name} and the target decision maker {ref_dm} who is the {dm_pos} of the company {company_name}.
                        3. Now craft a casual engaging yet human-like business email tailored to the recipient's profile and company's latest news and updates that enhance their existing feature or overcome an issue. The mail should be tailored to only the target decision maker preferences and interests.

                        Output Format:
                        ( provide only the email content, strictly without any other extra text or content. )

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

            print(response['choices'][0]['message']['content'])
            
            return response['choices'][0]['message']['content']



# Run the FastAPI application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
