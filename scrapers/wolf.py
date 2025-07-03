import requests
from bs4 import BeautifulSoup
import json
from typing import List, Dict
import time
import tracemalloc
import csv

from backend.listing_service import send_to_api

# Global counter for processed listings
manual_processed_count = 0

# Default CSV file path
DEFAULT_CSV_FILE = "manual_telemetry.csv"
csv_headers = ["url", "elapsed_time", "memory_usage", "scraper_type"]

def save_to_csv(data: Dict, csv_file: str = DEFAULT_CSV_FILE):
    """Save telemetry data to a CSV file."""
    try:
        with open(csv_file, mode='a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=csv_headers)
            if file.tell() == 0:  # Write headers only if file is new
                writer.writeheader()
            writer.writerow(data)
        print(f"Successfully wrote telemetry to {csv_file}: {data}")
    except Exception as e:
        print(f"Error writing to {csv_file}: {e}")

def scrape_wolf(listings_page: str) -> List[Dict[str, str | int | float | None]]:
    """Scrape property listings from a specific website using the provided listings page URL."""
    global manual_processed_count
    try:
        # Fetch the main listings page
        response = requests.get(listings_page, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract listing links
        links = [a["href"] for a in soup.select(".listing__teaserWrapper a.teaserLinkSeo") if a.get("href")]
        listings = []

        for link in links:
            full_url = link if link.startswith("http") else f"https://{link.lstrip('/')}"
            try:
                # Start timing and memory tracking
                start_time = time.time()
                tracemalloc.start()

                # Fetch individual listing page
                listing_response = requests.get(full_url, timeout=10)
                listing_response.raise_for_status()
                listing_soup = BeautifulSoup(listing_response.text, "html.parser")

                # Parse JSON data
                nuxt_data_script = listing_soup.select_one("#__NUXT_DATA__")
                if not nuxt_data_script:
                    print(f"Error: Could not find JSON data on {full_url}")
                    continue
                nuxt_data = json.loads(nuxt_data_script.text)

                # Extract property details from JSON
                property_dict = next((x for x in nuxt_data if isinstance(x, dict) and x.get("adKeywords")), None)
                if not property_dict:
                    print(f"Error: Property data not found in JSON on {full_url}")
                    continue

                # Extract details
                title_tag = listing_soup.select_one("title")
                title = title_tag.text.strip() if title_tag else None

                # Rent extraction
                rent_text = listing_soup.find("span", string=lambda text: "zł" in text if text else False)
                rent = int(float("".join(filter(str.isdigit, rent_text.text)))) if rent_text else None

                # Address extraction
                address_tag = listing_soup.select_one(".location-row__second_column")
                address = address_tag.text.strip() if address_tag else None

                # Area extraction
                area = None
                area_tag = listing_soup.select_one("#basic-info-price-row + div span")
                if area_tag and "m²" in area_tag.text:
                    area = int(float("".join(filter(str.isdigit, area_tag.text))))

                # Clean extracted data
                rent = clean_rent(str(rent) if rent is not None else "Not Available")
                area = clean_area(str(area) if area is not None else "Not Available")

                # Stop timing and memory tracking
                elapsed_time = time.time() - start_time
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()

                # Create listing item
                item = {
                    "title": title,
                    "rent": rent,
                    "area": area,
                    "address": address,
                    "url": full_url,
                    "elapsed_time": elapsed_time,
                    "memory_usage": peak / 1024 / 1024,
                    "scraper_type": "manual",
                }

                listings.append(item)
                send_to_api(item)

                # Save to CSV
                csv_data = {
                    "url": full_url,
                    "elapsed_time": elapsed_time,
                    "memory_usage": peak / 1024 / 1024,
                    "scraper_type": "manual"
                }
                save_to_csv(csv_data)

                # Increment processed count
                manual_processed_count += 1

            except requests.RequestException as e:
                print(f"Error fetching {full_url}: {e}")
                tracemalloc.stop()
                continue
            except Exception as e:
                print(f"Error parsing {full_url}: {e}")
                tracemalloc.stop()
                continue

        return listings

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

def get_manual_processed_count() -> int:
    """Return the number of listings processed by the manual scraper."""
    return manual_processed_count

def reset_manual_processed_count():
    """Reset the manual processed count."""
    global manual_processed_count
    manual_processed_count = 0