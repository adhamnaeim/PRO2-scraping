import signal
import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict
import datetime
from dotenv import load_dotenv
import os
import asyncio
import re

load_dotenv()

print(f"OPENAI_API_KEY loaded: {os.getenv('OPENAI_API_KEY') is not None}")
print(f"GROQ_API_KEY loaded: {os.getenv('GROQ_API_KEY') is not None}")

from db.models import Listing
from db.database import SessionLocal, engine, Base
from pydantic import BaseModel

from scrapers.wolf import scrape_wolf, get_manual_processed_count, reset_manual_processed_count
from scrapers.ai_scraper import scrape_ai_listings, get_ai_processed_count, reset_ai_processed_count

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

class ListingBase(BaseModel):
    title: str
    rent: int
    area: int | None = None
    address: str
    url: str
    ai_elapsed_time: float | None = None
    ai_selector_time: float | None = None
    ai_memory_usage: float | None = None
    manual_elapsed_time: float | None = None
    manual_memory_usage: float | None = None

class ListingCreate(BaseModel):
    title: str
    rent: int
    area: int | None = None
    address: str
    url: str
    ai_elapsed_time: float | None = None
    ai_selector_time: float | None = None
    ai_memory_usage: float | None = None
    manual_elapsed_time: float | None = None
    manual_memory_usage: float | None = None

class ListingRead(ListingBase):
    id: int

    class Config:
        from_attributes = True  # Updated for Pydantic V2

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

should_stop = False
scraping_history = []
last_used_model = "gpt-4o-mini"

@app.get("/")
def read_root():
    return {"message": "Welcome to the Property Listings API"}

@app.get("/listings", response_model=List[ListingRead])
def get_listings(url: str | None = None, db: Session = Depends(get_db)):
    if url:
        return db.query(Listing).filter(Listing.url == url).all()
    return db.query(Listing).all()

@app.post("/listings", response_model=ListingRead)
def create_listing(listing: ListingCreate, db: Session = Depends(get_db)):
    db_listing = Listing(**listing.dict())
    db.add(db_listing)
    db.commit()
    db.refresh(db_listing)
    return db_listing

@app.put("/listings/{listing_id}", response_model=ListingRead)
def update_listing(listing_id: int, listing: ListingCreate, db: Session = Depends(get_db)):
    db_listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not db_listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    for key, value in listing.dict().items():
        if key == "rent" and value and isinstance(value, str):
            value = int("".join(filter(str.isdigit, value)))
        elif key == "area" and value and isinstance(value, str):
            if value == "Not Available":
                value = None
            else:
                # Clean area string similar to clean_area
                cleaned_area = re.sub(r'[^\d.]', '', value)
                try:
                    value = int(float(cleaned_area)) if cleaned_area else None
                except ValueError:
                    print(f"Failed to convert area '{value}' to integer in update_listing")
                    value = None
        setattr(db_listing, key, value)
    db.commit()
    db.refresh(db_listing)
    return db_listing

@app.get("/scrape")
async def scrape_endpoint(url: str = "https://wolfnieruchomosci.gratka.pl/nieruchomosci/mieszkania", model: str = "gpt-4o-mini"):
    global should_stop, scraping_history, last_used_model
    if should_stop:
        return {"status": "error", "message": "Scraping stopped by user"}

    valid_models = ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo", "groq"]
    model_to_use = model if model in valid_models else "gpt-4o-mini"
    last_used_model = model_to_use
    
    try:
        ai_listings = await asyncio.to_thread(scrape_ai_listings, url, model=model_to_use)
        manual_listings = scrape_wolf(url)
        
        combined_listings = ai_listings + [l for l in manual_listings if l.get("url") not in [a["url"] for a in ai_listings]]
        
        attempt_stats = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "url": url,
            "used_ai_model": model_to_use,
            "ai_listings_processed": len(ai_listings),
            "manual_listings_processed": len(manual_listings),
            "total_listings_processed": len(combined_listings),
            "ai_average_scraper_time": sum(l["elapsed_time"] for l in ai_listings) / len(ai_listings) if ai_listings else 0,
            "ai_average_selector_time": sum(l["selector_time"] for l in ai_listings) / len(ai_listings) if ai_listings else 0,
            "ai_average_memory_usage_mb": sum(l["memory_usage"] for l in ai_listings) / len(ai_listings) if ai_listings else 0,
            "manual_average_scraper_time": sum(l["elapsed_time"] for l in manual_listings) / len(manual_listings) if manual_listings else 0,
            "manual_average_memory_usage_mb": sum(l["memory_usage"] for l in manual_listings) / len(manual_listings) if manual_listings else 0
        }
        
        scraping_history.append(attempt_stats)
        
        return {
            "status": "success",
            "ai_listings": ai_listings,
            "manual_listings": manual_listings,
            "combined_listings": combined_listings,
            "used_ai_model": model_to_use
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    listings = db.query(Listing).all()
    
    ai_listings = [l for l in listings if l.ai_elapsed_time is not None or l.ai_memory_usage is not None]
    manual_listings = [l for l in listings if l.manual_elapsed_time is not None or l.manual_memory_usage is not None]
    
    overall_stats = {
        "total_listings_processed": len(listings),
        "ai_total_processed": len(ai_listings),
        "manual_total_processed": len(manual_listings),
        "combined_average_time": (
            sum(l.ai_elapsed_time for l in ai_listings if l.ai_elapsed_time) +
            sum(l.manual_elapsed_time for l in manual_listings if l.manual_elapsed_time)
        ) / (len(ai_listings) + len(manual_listings)) if (ai_listings or manual_listings) else 0,
        "combined_average_memory": (
            sum(l.ai_memory_usage for l in ai_listings if l.ai_memory_usage) +
            sum(l.manual_memory_usage for l in manual_listings if l.manual_memory_usage)
        ) / (len(ai_listings) + len(manual_listings)) if (ai_listings or manual_listings) else 0
    }
    
    return {
        "scraping_history": scraping_history,
        "overall_stats": overall_stats
    }

def signal_handler(sig, frame):
    global should_stop
    print("\nReceived Ctrl+C, shutting down gracefully...")
    should_stop = True

class LifespanManager:
    async def __aenter__(self):
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        pass

async def shutdown():
    global should_stop
    should_stop = True
    print("Shutting down server...")

app.add_event_handler("startup", lambda: None)
app.add_event_handler("shutdown", shutdown)

if __name__ == "__main__":
    config = uvicorn.Config(app=app, host="127.0.0.1", port=8001, lifespan="auto")
    server = uvicorn.Server(config)
    asyncio.run(server.serve())