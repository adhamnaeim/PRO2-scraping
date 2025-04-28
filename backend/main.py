from fastapi import FastAPI, HTTPException, Depends
from db.models import Listing
from db.database import SessionLocal, engine, Base
from typing import List
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from scrapers.wolf import scrape_wolf  # manual scraper
from scrapers.ai_scraper import scrape_ai_listings # ai scraper

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # can restrict to specific domains later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic Schemas
from typing import Optional

class ListingBase(BaseModel):
    title: str
    rent: int
    area: Optional[int] = None  
    address: str
    url: str

class ListingCreate(ListingBase):
    pass

class ListingRead(ListingBase):
    id:int #auto id
    class Config:
        orm_mode = True  # for automatic serializing from ORM objects

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Routes

@app.get("/listings", response_model=List[ListingRead])
def get_listings(db: Session = Depends(get_db)):
    listings = db.query(Listing).all()
    return listings


@app.post("/listings", response_model=ListingRead)
def create_listing(listing: ListingCreate, db: Session = Depends(get_db)):
    db_listing = Listing(**listing.dict())
    db.add(db_listing)
    db.commit()
    db.refresh(db_listing)
    return db_listing

@app.post("/scrape_wolf")
def scrape_wolf_listings():
    db = SessionLocal()
    listings = scrape_wolf()
    added_count = 0

    for l in listings:
        existing_listing = db.query(Listing).filter_by(url=l["url"]).first()
        if not existing_listing:
            listing = Listing(**l)
            db.add(listing)
            added_count += 1

    db.commit()
    db.close()

    return {"status": "success", "listings_added": added_count}

@app.get("/scrape_wolf")
def scrape_wolf_get():
    listings = scrape_wolf()
    return {"status": "success", "listings": listings}

@app.get("/scrape_ai")
def scrape_ai_endpoint():
    try:
        listings_page = "https://wolfnieruchomosci.gratka.pl"
        listings = scrape_ai_listings(listings_page)
        return {"status": "success", "listings": listings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
