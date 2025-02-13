import requests
import os
from dotenv import load_dotenv

load_dotenv()

# def google_search(api_key, search_engine_id, query, limit):
#     url = "https://www.googleapis.com/customsearch/v1"
#     params = {
#         'key': api_key,
#         'cx': search_engine_id,
#         'q': query,
#         'num': limit  # Set the number of results per request (max 10)
#     }
#     response = requests.get(url, params=params)
#     return response.json()

def google_search(query, limit):
    url = "https://duckduckgo8.p.rapidapi.com/"
    querystring = {"q": query }

    headers = {
        "x-rapidapi-host": "duckduckgo8.p.rapidapi.com",
        "x-rapidapi-key": os.getenv("GOOGLE_API_KEY")
    }

    response = requests.get(url, headers=headers, params=querystring)
    print(response.json().keys())

    # print(response.json()['message'])
    return response.json()['results'][:limit]

# Example usage
api_key = 'AIzaSyDWQdpxZHM7Zpft2tMJ_1olqoXthQrlXfo'
search_engine_id = '82bd22c03bc644768'
comp_name = 'Whoop'
position = 'VP'
query = f'''Present {position} at {comp_name} AND site:linkedin.com'''
results = google_search(query, limit=5)  # Set limit to 5

print(results)
# Process results
# for item in results.get('items', []):
#     title = item.get('title')
#     snippet = item.get('snippet')
#     print(f'Title: {title}\nSnippet: {snippet}\n')



