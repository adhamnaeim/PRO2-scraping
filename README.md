# PRO2-scraping

## First-Time Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/your-repo.git
cd your-repo
```

### 2. Create and Activate Virtual Environment

```bash
# Windows
python -m venv .venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create .env file

```bash
- Create a new file and call it .env
- Add OPENAI_API_KEY=key-here
```

### 5. Run the FastAPI Backend

```bash
uvicorn backend.main:app --reload --port 8001

```

- Access API at: `http://127.0.0.1:8001`
- Swagger Docs at: `http://127.0.0.1:8001/docs`
- Scraped Items (DB) at: `http://127.0.0.1:8001/listings`
- Scraper at: `http://127.0.0.1:8001/scrape`
- Stats at: `http://127.0.0.1:8001/stats`

---

## Using the Scraper

### Scrape Endpoint

The `/scrape` endpoint allows you to scrape property listings from a specified URL using different OpenAI models for the AI scraper.

#### Base URL

```url
    http://127.0.0.1:8001/scrape
```

#### Parameters

- `url` (optional): The URL to scrape (default: `"https://wolfnieruchomosci.gratka.pl/nieruchomosci/mieszkania"`).
- `model` (optional): The OpenAI model to use for the AI scraper (default: `"gpt-4o-mini"`).

#### Supported Models

- `gpt-4o`
- `gpt-4o-mini`
- `gpt-3.5-turbo`

#### Example Requests

1. **Scrape with `gpt-4o` (default URL):**

   ```url
   http://127.0.0.1:8001/scrape?model=gpt-4o
   ```

2. **Scrape with `gpt-4o-mini` (custom URL):**

   ```url
   http://127.0.0.1:8001/scrape?url=https://gratka.pl/nieruchomosci/mieszkania&model=gpt-4o-mini
   ```

3. **Scrape with `gpt-3.5-turbo` (default URL):**

   ```url
   http://127.0.0.1:8001/scrape?model=gpt-3.5-turbo
   ```

4. **Scrape with `groq` (default URL):**

   ```url
   http://127.0.0.1:8001/scrape?model=groq
   ```

#### Response

The response includes:

- `status`: `"success"` or `"error"`.
- `ai_listings`: Listings scraped by the AI scraper.
- `manual_listings`: Listings scraped by the manual scraper.
- `combined_listings`: Combined unique listings.
- `used_ai_model`: The model used for the AI scraper.

---

## Notes

- Make sure to configure your `.env` with the OpenAI API key.
- The `.gitignore` file prevents `.db`, `.env`, and IDE configs from being tracked.

---

## Dependencies (`requirements.txt`)

```txt
fastapi[all]==0.115.12
uvicorn[standard]==0.34.2
sqlalchemy==2.0.40
requests==2.32.3
beautifulsoup4==4.13.4
openai==1.75.0
python-dotenv==1.1.0
groq==0.13.0
```

---

Happy scraping!
