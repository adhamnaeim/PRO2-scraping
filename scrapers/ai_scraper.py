import os
import requests
import json
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get OpenAI API key
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

def parse_selectors_from_ai(ai_response_text: str) -> dict:
    selectors = {}
    for line in ai_response_text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            selectors[key.strip()] = value.strip()
    return selectors

def scrape_with_ai(url: str):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    prompt = f"""
    You are a scraping expert. Given the following HTML snippet, extract the best CSS selectors for:
    - title
    - rent
    - area
    - address
    Only output the field names and selectors like this:
    title: .title-class (string)
    rent: .rent-class (integer)
    area: .area-class (integer)
    address: .address-class (string)

    HTML:
    {soup.prettify()[:8000]}
    """

    ai_response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    selectors = parse_selectors_from_ai(ai_response.choices[0].message.content)
    print("Generated Selectors:", selectors)

    extracted = {}
    for field in ["title", "rent", "area", "address"]:
        element = soup.select_one(selectors.get(field, ""))
        extracted[field] = element.get_text(strip=True) if element else "Not Available"

    extracted["url"] = url

    print("Extracted listing:", extracted)
    return extracted

def send_to_api(item):
    if isinstance(item.get('rent'), int) and isinstance(item.get('address'), str):
        api_url = "http://127.0.0.1:8001/listings"
        response = requests.post(api_url, json=item)
        if response.status_code == 200:
            print("Item sent successfully:", response.json())
        else:
            print("Failed to send item:", response.status_code, response.text)
    else:
        print(f"Skipping invalid item: {item['url']}")

def scrape_ai_listings(listings_page: str):
    response = requests.get(listings_page)
    soup = BeautifulSoup(response.text, "html.parser")

    links = [a['href'] for a in soup.select(".listing__teaserWrapper a.teaserLinkSeo") if a.get('href')]

    for link in links:
        full_url = link if link.startswith("http") else f"https://{link.lstrip('/')}"

        try:
            listing = scrape_with_ai(full_url)
            send_to_api(listing)

        except Exception as e:
            print(f"Error parsing {full_url}: {e}")
            continue
