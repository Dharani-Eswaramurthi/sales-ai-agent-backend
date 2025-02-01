import requests
from bs4 import BeautifulSoup

search_query = "Python programming tutorials"
url = f"https://www.google.com/search?q={search_query}"

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
response = requests.get(url, headers=headers)

soup = BeautifulSoup(response.text, 'html.parser')
search_results = soup.find_all('a', href=True)

for link in search_results:
    href = link['href']
    if href.startswith('/url?q='):
        title = link.get_text()
        url = href.split('&')[0].replace('/url?q=', '')
        print(f"Title: {title}")
        print(f"URL: {url}")
        print("-" * 80)
