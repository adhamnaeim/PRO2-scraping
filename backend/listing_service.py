import requests

def send_to_api(item: dict):
    api_url = "http://127.0.0.1:8001/listings"
    try:
        response = requests.post(api_url, json=item, timeout=10)
        if response.status_code == 200:
            print(f"Successfully sent: {item['url']}")
        else:
            print(f"Failed to send ({item['url']}): {response.status_code} - {response.text}")
    except requests.RequestException as e:
        print(f"Error sending {item['url']}: {e}")