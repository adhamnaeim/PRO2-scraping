import requests
from bs4 import BeautifulSoup
import json

def scrape_wolf():
    base_url = "https://wolfnieruchomosci.gratka.pl"
    # listings_page = base_url
    listings_page = "https://wolfnieruchomosci.gratka.pl/nieruchomosci/domy/wynajem"
    # listings_page = f"{base_url}/nieruchomosci/mieszkania/wynajem"

    # Fetch the main listings page
    response = requests.get(listings_page)
    soup = BeautifulSoup(response.text, "html.parser")

    # Extract links for all property listings
    links = [a['href'] for a in soup.select(".listing__teaserWrapper a.teaserLinkSeo") if a.get('href')]

    listings = []

    for link in links:
        full_url = link if link.startswith("http") else f"https://{link.lstrip('/')}"

        # Fetch each individual listing page
        listing_response = requests.get(full_url)
        listing_soup = BeautifulSoup(listing_response.text, "html.parser")

        try:
            # Get raw HTML content for debugging
            raw_html = listing_soup.prettify()

            # Parse the listing data from JSON embedded in the page
            nuxt_data_script = listing_soup.select_one("#__NUXT_DATA__")
            if not nuxt_data_script:
                print(f"Error: Could not find JSON data on {full_url}")
                continue
            nuxt_data = json.loads(nuxt_data_script.text)

            # Extract property details from the JSON data
            property_dict = [x for x in nuxt_data if isinstance(x, dict) and x.get('adKeywords')]
            if not property_dict:
                print(f"Error: Property data not found in JSON on {full_url}")
                continue
            property_info = property_dict[0] if property_dict else {}

            # Extract basic property details
            title_tag = listing_soup.select_one("title")
            title = title_tag.text.strip() if title_tag else None

            # Rent extraction - more simple and reliable approach
            rent_text = listing_soup.find("span", string=lambda text: "zł" in text if text else False)
            rent = None
            if rent_text:
                rent = int(float("".join(filter(str.isdigit, rent_text.text))))

            # Address extraction
            address_tag = listing_soup.select_one(".location-row__second_column")
            address = address_tag.text.strip() if address_tag else None

            # Area extraction
            area = None
            area_tag = listing_soup.select_one("#basic-info-price-row + div span")
            if area_tag and "m²" in area_tag.text:
                area = int(float("".join(filter(str.isdigit, area_tag.text))))

            # External link to the listing
            external_link = full_url

            # Print extracted data for debugging
            print(f"Title: {title}")
            print(f"Rent: {rent}")
            print(f"Address: {address}")
            print(f"Area: {area}")
            print(f"Link: {external_link}")

            

            item = {
                "title": title,
                "rent": rent,
                "area": area,
                "address": address,
                "url": external_link,
            }

            listings.append(item)

            send_to_api(item)

        except Exception as e:
            print(f"Error parsing {full_url}: {e}")
            continue

    return listings

def send_to_api(item):
    api_url = "http://127.0.0.1:8001/listings"
    response = requests.post(api_url, json=item)
    if response.status_code == 200:
        print("Item sent successfully:", response.json())
    else:
        print("Failed to send item:", response.status_code, response.text)

# if __name__ == "__main__":
#     url = "http://scrapethissite.com"
#     item = send_to_api(url)
#     send_to_api(item)