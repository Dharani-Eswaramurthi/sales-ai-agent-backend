import requests
import os

# Set your API key
API_KEY = os.getenv("PERPLEXITY_API_KEY")

# Function to call the chat completions endpoint
def chat_completion(messages):
    url = "https://api.perplexity.ai/chat/completions"  # Replace with the correct Perplexity chat completions endpoint

    payload = {
            "model": "llama-3.1-sonar-large-128k-online",
            "messages": messages,
            "max_tokens": 300,
            "temperature": 0,
            "top_p": 0.9,
        }
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None

# Function to create chat messages and retrieve information
def get_company_and_person_info(company_name, person_name, position, product_description):
    # Craft the system and user prompts
    prompt = f'''
    
                Product Description: {product_description}

                Follow the below steps to get the necessary information:
                1. Understand the provided product description.
                2. Now gather the company {company_name}'s latest news, updates and mainly the pain points if any from various sources and their official website.
                3. Now gather the information about the person {person_name} who is the {position} of the company {company_name}. Focus on the person's background, achievements and contributions.
                4. Based on the gathered information of {person_name}, indentify the person's behaviour, mindset, preferred communication style and tone, personal interest and way of working.
                5. Now, based on the gathered information of the company {company_name} and the person {person_name} who is the {position}, provide the all the necessary information about the company and the person.

                Output Format:
                ( provide a json of 3 keys namely {company_name}, {person_name} and pain points, and their relevant information with only 50 words for each of string datatype as their values, no other key should be present in the json )

                NOTE: Enclose response only in triple quotes.
'''
    messages = [
        {"role": "system", "content": "You are a helpful assistant that provides detailed information about companies and individuals."},
        {"role": "user", "content": prompt},
    ]

    # Call the chat completions endpoint
    response = chat_completion(messages)

    return response

# # Example usage
# if __name__ == "__main__":
#     company = "Microsoft"
#     person = "Satya Nadella"
#     position = "CEO"
    
#     result = get_company_and_person_info(company, person, position)
    
#     if result:
#         print("Response from Chat Completions API:")
#         print(result)
#     else:
#         print("Failed to fetch information.")
