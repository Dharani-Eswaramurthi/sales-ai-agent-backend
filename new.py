import requests

url = "https://duckduckgo8.p.rapidapi.com/"
querystring = {"q": "Current Sales Person at AstroSure.ai site:linkedin.com", "limit": 1}

headers = {
    "x-rapidapi-host": "duckduckgo8.p.rapidapi.com",
    "x-rapidapi-key": "6362c7eaf4msh749d60ec4afaa8ap18f2d7jsnd7bab901e8a5"
}

response = requests.get(url, headers=headers, params=querystring)

print(response.json())