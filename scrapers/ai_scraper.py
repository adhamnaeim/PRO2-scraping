import os
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv
from typing import Dict, List

from backend.listing_service import send_to_api

# Load environment variables
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

client = OpenAI(api_key=openai_api_key)

def parse_selectors_from_ai(ai_response_text: str) -> Dict[str, str]:
    """Parse AI response text into a dictionary of selectors."""
    selectors = {}
    for line in ai_response_text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            key, value = key.strip(), value.strip()
            if key and value:
                selectors[key] = value
    return selectors

def scrape_with_ai(url: str) -> Dict[str, str]:
    """Scrape a single listing page using AI-generated selectors."""
    try:
        # Fetch the page
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Try to find a relevant container
        possible_containers = soup.find_all(["article", "section", "div"], limit=10)
        selected_container = None
        for container in possible_containers:
            text = container.get_text(separator=" ", strip=True).lower()
            if any(keyword in text for keyword in ["rent", "area", "address", "m²", "price"]):
                selected_container = container
                break

        # Prepare HTML for AI
        if selected_container:
            print("✅ Found a likely container.")
            html_to_send = selected_container.prettify()
        else:
            print("⚠️ No good container found. Using full page fallback.")
            html_to_send = soup.prettify()[:3000]

        # AI prompt to generate selectors
        prompt = (
            "You are a scraping expert. Given the following HTML snippet, extract the best CSS selectors for:\n"
            "- title\n- rent\n- area\n- address\n"
            "Only output the field names and selectors like this:\n"
            "title: .title-class\nrent: .rent-class\narea: .area-class\naddress: .address-class\n\n"
            f"HTML:\n{html_to_send}"
        )

        # Call OpenAI API
        ai_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )

        # Parse AI-generated selectors
        selectors = parse_selectors_from_ai(ai_response.choices[0].message.content)
        print("Generated Selectors:", selectors)

        # Extract data using selectors
        extraction_soup = selected_container if selected_container else soup
        extracted = {}
        for field in ["title", "rent", "area", "address"]:
            selector = selectors.get(field, "")
            element = extraction_soup.select_one(selector)
            extracted[field] = element.get_text(strip=True) if element else "Not Available"

        extracted["url"] = url
        print("Extracted listing:", extracted)
        return extracted

    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        raise
    except Exception as e:
        print(f"Error processing {url}: {e}")
        raise

def scrape_ai_listings(listings_page: str) -> List[Dict[str, str]]:
    """Scrape multiple listings from a listings page."""
    try:
        response = requests.get(listings_page, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract listing links
        links = [a["href"] for a in soup.select(".listing__teaserWrapper a.teaserLinkSeo") if a.get("href")]
        scraped_listings = []

        for link in links:
            full_url = link if link.startswith("http") else f"https://{link.lstrip('/')}"
            try:
                listing = scrape_with_ai(full_url)
                listing["rent"] = clean_rent(listing.get("rent", ""))
                listing["area"] = clean_area(listing.get("area", ""))
                send_to_api(listing)
                scraped_listings.append(listing)
            except Exception as e:
                print(f"Error parsing {full_url}: {e}")
                continue

        return scraped_listings

    except requests.RequestException as e:
        print(f"Error fetching listings page {listings_page}: {e}")
        raise

def clean_rent(rent_value: str) -> int | None:
    """Clean and convert rent value to an integer."""
    if not rent_value or rent_value == "Not Available":
        return None
    numbers = "".join(c for c in rent_value if c.isdigit())
    return int(numbers) if numbers else None

def clean_area(area_value: str) -> int | None:
    """Clean and convert area value to an integer."""
    if not area_value or area_value == "Not Available":
        return None
    area_value = area_value.replace("•", "").replace(",", ".").replace("m²", "").strip()
    try:
        return int(float(area_value))
    except ValueError:
        return None