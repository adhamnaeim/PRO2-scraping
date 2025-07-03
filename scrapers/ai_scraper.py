import time
import tracemalloc
import requests
from bs4 import BeautifulSoup
import csv
import os
import re
from openai import OpenAI
from groq import Groq
from typing import Dict, List

# Initialize clients with error handling and fallback
try:
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception as e:
    print(f"Failed to initialize OpenAI client: {e}")
    openai_client = None

try:
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
except Exception as e:
    print(f"Failed to initialize Groq client: {e}")
    groq_client = None

# Counter for processed listings
ai_processed_count = 0

def clean_rent(rent: str) -> int:
    """Clean the rent string and convert to integer."""
    if not rent or rent == "Not Available":
        return 0
    return int("".join(filter(str.isdigit, rent)))

def clean_area(area: str) -> int | None:
    """Clean the area string and convert to integer, handling special characters."""
    if not area or area == "Not Available":
        return None
    cleaned_area = re.sub(r'[^\d.]', '', area)
    try:
        return int(float(cleaned_area))
    except ValueError:
        print(f"Failed to convert area '{area}' to integer after cleaning to '{cleaned_area}'")
        return None

def parse_selectors_from_ai(ai_response: str) -> Dict[str, str]:
    """Parse the AI response into a dictionary of selectors."""
    selectors = {}
    for line in ai_response.split("\n"):
        if ":" in line:
            field, selector = line.split(":", 1)
            selectors[field.strip()] = selector.strip()
    return selectors

def save_to_csv(data: Dict[str, float | str]):
    """Save scraping stats to CSV."""
    with open("scraper_stats.csv", mode="a", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["url", "elapsed_time", "selector_time", "memory_usage", "scraper_type"])
        if file.tell() == 0:
            writer.writeheader()
        writer.writerow(data)

def send_to_api(data: Dict[str, str | float | int | None]):
    """Send extracted data to the API for database storage."""
    requests.post("http://127.0.0.1:8001/listings", json={
        "title": data.get("title", "Not Available"),
        "rent": data.get("rent", 0),
        "area": data.get("area", None),
        "address": data.get("address", "Not Available"),
        "url": data.get("url", ""),
        "ai_elapsed_time": data.get("elapsed_time", None),
        "ai_selector_time": data.get("selector_time", None),
        "ai_memory_usage": data.get("memory_usage", None),
        "manual_elapsed_time": None,
        "manual_memory_usage": None
    })

def scrape_with_ai(url: str, model: str = "gpt-4o-mini") -> Dict[str, str | float | int | None]:
    """Scrape a single listing page using AI-generated selectors."""
    global ai_processed_count
    tracemalloc.start()
    start_time = time.time()

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        possible_containers = soup.find_all(["article", "section", "div"], limit=10)
        selected_container = None
        for container in possible_containers:
            text = container.get_text(separator=" ", strip=True).lower()
            if any(keyword in text for keyword in ["rent", "area", "address", "m²", "price"]):
                selected_container = container
                break

        if selected_container:
            print("✅ Found a likely container.")
            html_to_send = selected_container.prettify()[:1000]  # Truncate to 1000 characters
        else:
            print("⚠️ No good container found. Using full page fallback.")
            html_to_send = soup.prettify()[:1000]  # Truncate to 1000 characters

        selector_start_time = time.time()
        print(f"Using model: {model} for API call")
        prompt = (
            "You are a scraping expert. Given the following HTML snippet, extract the best CSS selectors for:\n"
            "- title\n- rent\n- area\n- address\n"
            "Only output the field names and selectors like this:\n"
            "title: .title-class\nrent: .rent-class\narea: .area-class\naddress: .address-class\n\n"
            f"HTML:\n{html_to_send}"
        )

        ai_response = None
        try:
            if model == "groq":
                if groq_client is None:
                    print("Falling back to gpt-4o-mini due to Groq client failure.")
                    model = "gpt-4o-mini"
                else:
                    groq_response = groq_client.chat.completions.create(
                        model="llama3-70b-8192",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.2
                    )
                    ai_response = groq_response.choices[0].message.content
            if model != "groq" or ai_response is None:
                if openai_client is None:
                    raise ValueError("OpenAI client is not initialized. Check OPENAI_API_KEY.")
                openai_response = openai_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2
                )
                ai_response = openai_response.choices[0].message.content
        except Exception as e:
            print(f"Error during AI model call: {e}")
            raise RuntimeError(f"Failed to get AI response: {str(e)}")

        if ai_response is None:
            raise RuntimeError("AI response was not generated.")

        selector_time = time.time() - selector_start_time

        selectors = parse_selectors_from_ai(ai_response)
        print("Generated Selectors:", selectors)

        extraction_soup = selected_container if selected_container else soup
        extracted = {}
        for field in ["title", "rent", "area", "address"]:
            selector = selectors.get(field, "")
            element = extraction_soup.select_one(selector)
            extracted[field] = element.get_text(strip=True) if element else "Not Available"

        extracted["rent"] = clean_rent(extracted.get("rent", ""))
        extracted["area"] = clean_area(extracted.get("area", ""))

        elapsed_time = time.time() - start_time
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        extracted["url"] = url
        extracted["elapsed_time"] = elapsed_time
        extracted["selector_time"] = selector_time
        extracted["memory_usage"] = peak / 1024 / 1024
        extracted["scraper_type"] = "ai"
        print("Extracted listing:", extracted)

        csv_data = {
            "url": url,
            "elapsed_time": elapsed_time,
            "selector_time": selector_time,
            "memory_usage": peak / 1024 / 1024,
            "scraper_type": "ai"
        }
        save_to_csv(csv_data)

        ai_processed_count += 1

        send_to_api(extracted)

        return extracted

    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        tracemalloc.stop()
        raise
    except Exception as e:
        print(f"Error processing {url}: {e}")
        tracemalloc.stop()
        raise

def scrape_ai_listings(url: str, model: str = "gpt-4o-mini") -> List[Dict[str, str | float | int | None]]:
    """Scrape multiple listings from a given URL using AI."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        listing_links = soup.find_all("a", href=re.compile(r"/mieszkanie-[^/]+/ob/\d+"))
        print(f"Found {len(listing_links)} listing links.")
        listing_urls = [link["href"] for link in listing_links][:5]
        listings = []
        for listing_url in listing_urls:
            if not listing_url.startswith("http"):
                listing_url = "https://wolfnieruchomosci.gratka.pl" + listing_url
            print(f"Scraping AI listing: {listing_url}")
            listing = scrape_with_ai(listing_url, model=model)
            listings.append(listing)
        return listings
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        raise
    except Exception as e:
        print(f"Error in scrape_ai_listings: {e}")
        raise

def get_ai_processed_count() -> int:
    """Return the total number of AI-processed listings."""
    return ai_processed_count

def reset_ai_processed_count():
    """Reset the AI processed count."""
    global ai_processed_count
    ai_processed_count = 0