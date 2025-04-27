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

### 4. Run the FastAPI Backend

```bash
uvicorn backend.main:app --reload --port 8000
uvicorn backend.main:app --reload --port 8001

```

- Access API at: `http://127.0.0.1:8000`
- Swagger Docs at: `http://127.0.0.1:8000/docs`

### 5. Run the Scraper Script (optional)

```bash
python scrapers/scraper.py
```

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
```

---

Happy scraping!
