import requests
import os
import json

# Set your API key
API_KEY = os.getenv("PERPLEXITY_API_KEY")

# Function to call the chat completions endpoint
def chat_completion(messages, tokens):
    url = "https://api.perplexity.ai/chat/completions"  # Replace with the correct Perplexity chat completions endpoint

    payload = {
            "model": "llama-3.1-sonar-large-128k-online",
            "messages": messages,
            "max_tokens": tokens,
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
    """Enhanced information gathering for hyper-personalized emails"""
    prompt = f'''
    As a Business Intelligence Analyst, analyze these entities:

    **Product**: {product_description}

    **Analysis Steps**:
    1. Company Analysis ({company_name}):
    - Recent news/updates (past 6 months)
    - Financial trends/earnings reports
    - Current challenges/pain points related to: 
      * Operational efficiency
      * Market competition
      * Technological adoption
    - Industry position/ranking
    - Strategic initiatives

    2. Decision Maker Profile ({person_name}, {position}):
    - Communication style preferences (data-driven, visionary, pragmatic)
    - Personality indicators (Myers-Briggs type if inferrable)
    - Career milestones/achievements
    - Public speaking topics/interests
    - Leadership style indicators
    - Recent professional moves/awards

    3. Synergy Analysis:
    - Map product capabilities to {company_name}'s verified needs
    - Align value proposition with {person_name}'s decision-making patterns
    - Identify 3 key persuasion leverage points

    **Output Format** (strictly provide JSON format and no extra text or comments):
    {{
        "company_analysis": {{
            "recent_news": "str",
            "financial_health": "str",
            "verified_challenges": ["str"],
            "strategic_priorities": ["str"]
        }},
        "decision_maker_profile": {{
            "communication_style": "str",
            "personality_indicators": "str",
            "personality_type": "str", ( give in 4 to 5 words, also if your giving in Myers-Briggs type, include the full form of it )
            "key_achievements": "str",
            "recent_activities": "str"
        }},
        "synergy_points": {{
            "product_fit": "str",
            "persuasion_levers": ["str"],
            "urgency_factors": ["str"]
        }}
    }}
    '''.strip()

    messages = [
        {
            "role": "system",
            "content": "You are a senior business analyst with expertise in enterprise decision-making dynamics."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    try:
        response = chat_completion(messages, 900)

        data = response
        usage = data.get("usage", {})
        print(f"Input tokens: {usage.get('prompt_tokens', 'N/A') * 0.0000002}")
        print(f"Output tokens: {usage.get('completion_tokens', 'N/A') * 0.0000002}")
        print(f"Total tokens: {usage.get('total_tokens', 'N/A')}")

        return response
    except (json.JSONDecodeError, KeyError) as e:
        return {"error": f"Analysis failed: {str(e)}"}

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
