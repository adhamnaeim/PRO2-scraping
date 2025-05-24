from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from db.models import Listing
from db.database import SessionLocal, engine, Base
from pydantic import BaseModel
from scrapers.wolf import scrape_wolf
from scrapers.ai_scraper import scrape_ai_listings

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

class ListingCreate(ListingBase):
    pass

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
def get_listings(db: Session = Depends(get_db)):
    """Retrieve all listings from the database."""
    return db.query(Listing).all()

@app.post("/listings", response_model=ListingRead)
def create_listing(listing: ListingCreate, db: Session = Depends(get_db)):
    """Create a new listing in the database."""
    db_listing = Listing(**listing.dict())
    db.add(db_listing)
    db.commit()
    db.refresh(db_listing)
    return db_listing

@app.get("/scrape_wolf")
def scrape_wolf_endpoint():
    """Scrape listings using the manual scraper."""
    listings_page = "https://wolfnieruchomosci.gratka.pl/nieruchomosci/domy/wynajem"
    try:
        listings = scrape_wolf(listings_page)
        return {"status": "success", "listings": listings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

@app.get("/scrape_ai")
def scrape_ai_endpoint():
    """Scrape listings using the AI-powered scraper."""
    listings_page = "https://wolfnieruchomosci.gratka.pl/"
    try:
        listings = scrape_ai_listings(listings_page)
        return {"status": "success", "listings": listings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")