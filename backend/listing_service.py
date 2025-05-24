import requests

def send_to_api(item: dict):
    """Send a scraped listing to the API for storage in the database, updating only scraper-specific fields if it already exists."""
    api_url = "http://127.0.0.1:8001/listings"
    try:
        # Prepare the base payload with common fields
        base_payload = {
            "title": item["title"],
            "rent": item["rent"],
            "area": item.get("area"),
            "address": item["address"],
            "url": item["url"],
        }
        
        # Prepare scraper-specific payload
        scraper_type = item.get("scraper_type")
        update_payload = base_payload.copy()
        if scraper_type == "ai":
            update_payload.update({
                "ai_elapsed_time": item["elapsed_time"],
                "ai_selector_time": item.get("selector_time"),
                "ai_memory_usage": item["memory_usage"],
            })
        elif scraper_type == "manual":
            update_payload.update({
                "manual_elapsed_time": item["elapsed_time"],
                "manual_memory_usage": item["memory_usage"],
            })

        # Check if the listing exists
        response = requests.get(f"{api_url}?url={item['url']}", timeout=10)
        if response.status_code == 200:
            existing_listings = response.json()
            if existing_listings:  # If a listing with this URL exists
                listing_id = existing_listings[0]["id"]
                # Get the existing data
                existing_data = existing_listings[0]
                # Merge existing data with new data, preserving other scraper data
                merged_payload = existing_data.copy()
                merged_payload.update(update_payload)
                # Update the existing listing
                response = requests.put(f"{api_url}/{listing_id}", json=merged_payload, timeout=10)
                if response.status_code == 200:
                    print(f"Successfully updated: {item['url']}")
                else:
                    print(f"Failed to update ({item['url']}): {response.status_code} - {response.text}")
                return

        # If no existing listing, create a new one
        response = requests.post(api_url, json=update_payload, timeout=10)
        if response.status_code == 200:
            print(f"Successfully sent: {item['url']}")
        else:
            print(f"Failed to send ({item['url']}): {response.status_code} - {response.text}")
    except requests.RequestException as e:
        print(f"Error sending {item['url']}: {e}")