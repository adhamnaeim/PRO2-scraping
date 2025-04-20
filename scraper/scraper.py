import json
from bs4 import BeautifulSoup
import requests

def scrape_site(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Dummy values based on the page title
    title = soup.title.string.strip() if soup.title else "No title"

    # Fake scraped item to match your schema
    scraped_item = {
        "name": title,
        "price": 9.99,
        "rating": 4.2,
        "description": f"Auto scraped from {url}"
    }

    return scraped_item

def send_to_api(item):
    api_url = "http://127.0.0.1:8001/items"
    response = requests.post(api_url, json=item)
    if response.status_code == 200:
        print("Item sent successfully:", response.json())
    else:
        print("Failed to send item:", response.status_code, response.text)

if __name__ == "__main__":
    url = "http://scrapethissite.com"
    item = scrape_site(url)
    send_to_api(item)
