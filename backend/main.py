from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

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
        setattr(db_listing, key, value)
    db.commit()
    db.refresh(db_listing)
    return db_listing

@app.get("/scrape_wolf")
def scrape_wolf_endpoint():
    """Scrape listings using the manual scraper."""
    listings_page = "https://wolfnieruchomosci.gratka.pl/nieruchomosci/mieszkania"
    try:
        listings = scrape_wolf(listings_page)
        return {"status": "success", "listings": listings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

@app.get("/scrape_ai")
def scrape_ai_endpoint():
    """Scrape listings using the AI-powered scraper."""
    listings_page = "https://wolfnieruchomosci.gratka.pl/nieruchomosci/mieszkania"
    try:
        listings = scrape_ai_listings(listings_page)
        return {"status": "success", "listings": listings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Calculate average elapsed time, selector time, and memory usage for AI and manual scrapers."""
    listings = db.query(Listing).all()
    
    ai_elapsed_times = [l.ai_elapsed_time for l in listings if l.ai_elapsed_time is not None]
    ai_selector_times = [l.ai_selector_time for l in listings if l.ai_selector_time is not None]
    ai_memory_usages = [l.ai_memory_usage for l in listings if l.ai_memory_usage is not None]
    manual_elapsed_times = [l.manual_elapsed_time for l in listings if l.manual_elapsed_time is not None]
    manual_memory_usages = [l.manual_memory_usage for l in listings if l.manual_memory_usage is not None]
    
    avg_ai_time = sum(ai_elapsed_times) / len(ai_elapsed_times) if ai_elapsed_times else 0
    avg_ai_selector_time = sum(ai_selector_times) / len(ai_selector_times) if ai_selector_times else 0
    avg_ai_memory = sum(ai_memory_usages) / len(ai_memory_usages) if ai_memory_usages else 0
    avg_manual_time = sum(manual_elapsed_times) / len(manual_elapsed_times) if manual_elapsed_times else 0
    avg_manual_memory = sum(manual_memory_usages) / len(manual_memory_usages) if manual_memory_usages else 0
    
    return {
        "average_ai_scraper_time": avg_ai_time,
        "average_manual_scraper_time": avg_manual_time,
        "average_ai_selector_time": avg_ai_selector_time,
        "average_ai_memory_usage_mb": avg_ai_memory,
        "average_manual_memory_usage_mb": avg_manual_memory,
        "ai_scraper_count": get_ai_processed_count(),
        "manual_scraper_count": get_manual_processed_count(),
    }