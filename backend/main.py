import signal
import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict

from db.models import Listing
from db.database import SessionLocal, engine, Base
from pydantic import BaseModel

from scrapers.wolf import scrape_wolf, get_manual_processed_count, reset_manual_processed_count
from scrapers.ai_scraper import scrape_ai_listings, get_ai_processed_count, reset_ai_processed_count

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
Base.metadata.create_all(bind=engine)

# Pydantic Schemas
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
        orm_mode = True

# Dependency to get DB session
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Global flag to control scraper termination and store last used model
should_stop = False
last_used_model = "gpt-4o-mini"  # Default value

# Routes
@app.get("/")
def read_root():
    """Return a welcome message for the root endpoint."""
    return {"message": "Welcome to the Property Listings API"}

@app.get("/listings", response_model=List[ListingRead])
def get_listings(url: str | None = None, db: Session = Depends(get_db)):
    """Retrieve all listings from the database, optionally filtering by URL."""
    if url:
        return db.query(Listing).filter(Listing.url == url).all()
    return db.query(Listing).all()

@app.post("/listings", response_model=ListingRead)
def create_listing(listing: ListingCreate, db: Session = Depends(get_db)):
    """Create a new listing in the database."""
    db_listing = Listing(**listing.dict())
    db.add(db_listing)
    db.commit()
    db.refresh(db_listing)
    return db_listing

@app.put("/listings/{listing_id}", response_model=ListingRead)
def update_listing(listing_id: int, listing: ListingCreate, db: Session = Depends(get_db)):
    """Update an existing listing in the database."""
    db_listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not db_listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    for key, value in listing.dict().items():
        if key in ["rent", "area"] and value and isinstance(value, str):
            if key == "rent":
                value = int("".join(filter(str.isdigit, value)))
            elif key == "area" and value != "Not Available":
                value = int(float("".join(filter(str.isdigit, value))))
            elif value == "Not Available":
                value = None
        setattr(db_listing, key, value)
    db.commit()
    db.refresh(db_listing)
    return db_listing

@app.get("/scrape")
def scrape_endpoint(url: str = "https://wolfnieruchomosci.gratka.pl/nieruchomosci/mieszkania", model: str = "gpt-4o-mini"):
    """Scrape listings using both AI and manual scrapers with a configurable AI model."""
    global should_stop, last_used_model
    if should_stop:
        return {"status": "error", "message": "Scraping stopped by user"}

    # Valid models list
    valid_models = ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"]
    # Use provided model if valid, otherwise fallback to default
    model_to_use = model if model in valid_models else "gpt-4o-mini"
    last_used_model = model_to_use  # Update the last used model
    
    try:
        # Run AI scraper with the validated model
        ai_listings = scrape_ai_listings(url, model=model_to_use)
        
        # Run manual scraper
        manual_listings = scrape_wolf(url)
        
        # Combine results, avoiding duplicates by URL
        combined_listings = ai_listings + [l for l in manual_listings if l.get("url") not in [a["url"] for a in ai_listings]]
        
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
    """Calculate detailed metrics for both AI and manual scrapers."""
    listings = db.query(Listing).all()
    
    # AI scraper metrics
    ai_listings = [l for l in listings if l.ai_elapsed_time is not None or l.ai_memory_usage is not None]
    ai_elapsed_times = [l.ai_elapsed_time for l in ai_listings if l.ai_elapsed_time is not None]
    ai_selector_times = [l.ai_selector_time for l in ai_listings if l.ai_selector_time is not None]
    ai_memory_usages = [l.ai_memory_usage for l in ai_listings if l.ai_memory_usage is not None]
    
    # Manual scraper metrics
    manual_listings = [l for l in listings if l.manual_elapsed_time is not None or l.manual_memory_usage is not None]
    manual_elapsed_times = [l.manual_elapsed_time for l in manual_listings if l.manual_elapsed_time is not None]
    manual_memory_usages = [l.manual_memory_usage for l in manual_listings if l.manual_memory_usage is not None]
    
    # Calculate detailed stats
    stats = {
        "ai_scraper": {
            "total_processed": len(ai_listings),
            "average_scraper_time": sum(ai_elapsed_times) / len(ai_elapsed_times) if ai_elapsed_times else 0,
            "average_selector_time": sum(ai_selector_times) / len(ai_selector_times) if ai_selector_times else 0,
            "average_memory_usage_mb": sum(ai_memory_usages) / len(ai_memory_usages) if ai_memory_usages else 0,
            "last_used_model": last_used_model  # Use the dynamically updated model
        },
        "manual_scraper": {
            "total_processed": len(manual_listings),
            "average_scraper_time": sum(manual_elapsed_times) / len(manual_elapsed_times) if manual_elapsed_times else 0,
            "average_memory_usage_mb": sum(manual_memory_usages) / len(manual_memory_usages) if manual_memory_usages else 0
        },
        "overall": {
            "total_listings_processed": len(listings),
            "combined_average_time": (sum(ai_elapsed_times) + sum(manual_elapsed_times)) / (len(ai_elapsed_times) + len(manual_elapsed_times)) if (ai_elapsed_times or manual_elapsed_times) else 0,
            "combined_average_memory": (sum(ai_memory_usages) + sum(manual_memory_usages)) / (len(ai_memory_usages) + len(manual_memory_usages)) if (ai_memory_usages or manual_memory_usages) else 0
        }
    }
    
    return stats

# Signal handler for Ctrl+C
def signal_handler(sig, frame):
    global should_stop
    print("\nReceived Ctrl+C, shutting down gracefully...")
    should_stop = True
    # Additional cleanup if needed (e.g., close database sessions)

# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    # Run the server with Uvicorn on port 8001
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8001, reload=True)