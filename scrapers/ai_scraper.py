import os
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

from backend.listing_service import send_to_api

# Load environment variables
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

def parse_selectors_from_ai(ai_response_text: str) -> dict:
    selectors = {}
    for line in ai_response_text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            key, value = key.strip(), value.strip()
            if key and value and isinstance(key, str) and isinstance(value, str):
                selectors[key] = value
    return selectors


def scrape_with_ai(url: str):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Try to auto-detect a container
    possible_containers = soup.find_all(["article", "section", "div"], limit=10)
    selected_container = None

    for container in possible_containers:
        text = container.get_text(separator=" ", strip=True).lower()
        if any(keyword in text for keyword in ["rent", "area", "address", "m²", "price"]):
            selected_container = container
            break

    if selected_container:
        print("✅ Found a likely container.")
        html_to_send = selected_container.prettify()
    else:
        print("⚠️ No good container found. Using full page fallback.")
        html_to_send = soup.prettify()[:3000]

    prompt = f"""
    You are a scraping expert. Given the following HTML snippet, extract the best CSS selectors for:
    - title
    - rent
    - area
    - address
    Only output the field names and selectors like this:
    title: .title-class
    rent: .rent-class
    area: .area-class
    address: .address-class

    HTML:
    {html_to_send}
    """

    ai_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    selectors = parse_selectors_from_ai(ai_response.choices[0].message.content)
    print("Generated Selectors:", selectors)

    # Now extract info
    extraction_soup = selected_container if selected_container else soup
    extracted = {}
    for field in ["title", "rent", "area", "address"]:
        selector = selectors.get(field, "")
        element = extraction_soup.select_one(selector)
        extracted[field] = element.get_text(strip=True) if element else "Not Available"

    extracted["url"] = url

    print("Extracted listing:", extracted)
    return extracted


# def send_to_api(item):
#     item['rent'] = clean_rent(item.get('rent', ""))
#     item['area'] = clean_area(item.get('area', ""))

#     if item['rent'] and isinstance(item.get('address'), str):
#         api_url = "http://127.0.0.1:8001/listings"
#         response = requests.post(api_url, json=item)
#         if response.status_code == 200:
#             print("Item sent successfully:", response.json())
#         else:
#             print("Failed to send item:", response.status_code, response.text)
#     else:
#         print(f"Skipping invalid item: {item['url']}")


def scrape_ai_listings(listings_page: str):
    response = requests.get(listings_page)
    soup = BeautifulSoup(response.text, "html.parser")

    links = [a['href'] for a in soup.select(".listing__teaserWrapper a.teaserLinkSeo") if a.get('href')]

    scraped_listings = []

    for link in links:
        full_url = link if link.startswith("http") else f"https://{link.lstrip('/')}"

        try:
            listing = scrape_with_ai(full_url)
            listing['rent'] = clean_rent(listing.get('rent', ""))
            listing['area'] = clean_area(listing.get('area', ""))
            send_to_api(listing)
        
            scraped_listings.append(listing)

        except Exception as e:
            print(f"Error parsing {full_url}: {e}")
            continue

    return scraped_listings


def clean_rent(rent_value: str) -> int:
    if not rent_value or rent_value == "Not Available":
        return None

    numbers = ''.join(c for c in rent_value if c.isdigit())
    return int(numbers) if numbers else None

    
def clean_area(area_value: str) -> int:
    if not area_value or area_value == "Not Available":
        return None
    area_value = area_value.replace("•", "").replace(",", ".").replace("m²", "").strip()
    try:
        return int(float(area_value))
    except ValueError:
        return None
