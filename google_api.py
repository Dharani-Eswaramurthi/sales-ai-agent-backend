import requests

def google_search(api_key, search_engine_id, query, limit):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'key': api_key,
        'cx': search_engine_id,
        'q': query,
        'num': limit  # Set the number of results per request (max 10)
    }
    response = requests.get(url, params=params)
    return response.json()

# Example usage
# api_key = 'AIzaSyDWQdpxZHM7Zpft2tMJ_1olqoXthQrlXfo'
# search_engine_id = '82bd22c03bc644768'
# comp_name = 'Whoop'
# position = 'VP'
# query = f'''Present {position} at {comp_name} AND site:linkedin.com'''
# results = google_search(api_key, search_engine_id, query, limit=5)  # Set limit to 5

# # Process results
# for item in results.get('items', []):
#     title = item.get('title')
#     snippet = item.get('snippet')
#     print(f'Title: {title}\nSnippet: {snippet}\n')



