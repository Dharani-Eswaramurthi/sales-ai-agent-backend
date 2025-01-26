import PyPDF2
from sentence_transformers import SentenceTransformer, util
import faiss
import numpy as np
import os
import requests

# Step 1: Extract content from PDFs
def extract_text_from_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ''
        for page in reader.pages:
            text += page.extract_text()
    return text

# Load and process PDFs
pdf_paths = {
    "email": "email-template.pdf",
    "followup": "followup-template.pdf",
    "breakup": "breakup-template.pdf"
}
documents = {key: extract_text_from_pdf(path) for key, path in pdf_paths.items()}

# Step 2: Create a knowledge base
model = SentenceTransformer('all-MiniLM-L6-v2')
index = faiss.IndexFlatL2(384)

# Store embeddings in FAISS
doc_embeddings = [model.encode(documents[key]) for key in documents]
for embedding in doc_embeddings:
    index.add(np.array([embedding]))

def retrieve_relevant_content(query):
    query_embedding = model.encode(query)
    D, I = index.search(np.array([query_embedding]), k=1)
    relevant_doc_key = list(documents.keys())[I[0][0]]
    return documents[relevant_doc_key]

# Step 3: Efficient prompting with retrieval using Perplexity
API_KEY = os.getenv("PERPLEXITY_API_KEY")
BASE_URL = "https://api.perplexity.ai/chat/completions"

def generate_email(query, situation, **kwargs):
    # Retrieve relevant content
    context = retrieve_relevant_content(situation)

    print("Context:", context)
    
    # Extract additional inputs
    product_description = kwargs.get("product_description", "")
    company_name = kwargs.get("company_name", "")
    decision_maker = kwargs.get("decision_maker", "")
    decision_maker_position = kwargs.get("decision_maker_position", "")
    req_info = kwargs.get("req_info", "")
    sender_name = kwargs.get("sender_name", "")
    sender_position = kwargs.get("sender_position", "")
    sender_company = kwargs.get("sender_company", "")

    # Dynamic prompt construction
    prompt = f"""
                You are an expert email composer, skilled in creating professional and engaging business emails tailored to specific situations. 

                ### Context:
                Refer to the provided document on crafting the {situation}: {context}

                ### Inputs:
                - **Product Description**: {product_description}
                - **Target Company Name**: {company_name}
                - **Decision Maker Name**: {decision_maker}
                - **Decision Maker Position**: {decision_maker_position}
                - **Target Company and Decision Maker Details**: {req_info}
                - **Sender Name**: {sender_name}
                - **Sender Position**: {sender_position}
                - **Sender Company**: {sender_company}

                ### Instructions:
                1. Analyze the context and input details thoroughly.
                2. Compose a professional email tailored specifically to the situation: **{situation}**.
                3. Ensure the email maintains a persuasive and engaging tone, suitable for professional communication.
                4. Structure the email using appropriate HTML tags for formatting and clarity like <br/>, <strong>, for bulletings, and other necessary tags. Include proper spacing and alignment based on the context.

                ### Output Format:
                Return the email content in JSON format with the following structure:
                
                "subject": "Customized Subject Based on Situation",
                "body": "(Craft the email body on behalf of the sender based on the situation, inputs, and context. Use the best approach for the given scenario.)"
                
                Important: Ensure that only the JSON response is returned without any additional text or content with proper JSON formatting so that it is ready to conevrt from string response to json.
                """

    payload = {
        "model": "llama-3.1-sonar-large-128k-online",
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": query}
        ],
        "max_tokens": 650,
        "temperature": 0.7
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(BASE_URL, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None

# Usage example
# query = "Breakup on our previous discussion"
# situation = "breakup"
# kwargs = {
#     "product_description": "A cutting-edge AI-powered analytics tool.",
#     "company_name": "Acme Corp",
#     "decision_maker": "Jane Doe",
#     "decision_maker_position": "CTO",
#     "req_info": "Company website: www.acmecorp.com"
# }
# email_output = generate_email(query, situation, **kwargs)
# print(email_output)
