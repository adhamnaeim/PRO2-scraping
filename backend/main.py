from fastapi import FastAPI, HTTPException, Depends
from db.models import Listing
from db.database import SessionLocal, engine, Base
from typing import List
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from scrapers.wolf import scrape_wolf  # manual scraper

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
    id: int  # <- MATCH the database (INTEGER id)
    title: str
    rent: int
    area: Optional[int] = None  # <- allow area to be missing (null)
    address: str
    url: str

class ListingCreate(ListingBase):
    pass

class ListingRead(ListingBase):
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

    if not listings:
        scraped = scrape_wolf()
        for l in scraped:
            listing = Listing(**l)
            db.add(listing)
        db.commit()
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
def scrape_wolf_listings(db: Session = Depends(get_db)):
    listings = scrape_wolf()
    for l in listings:
        listing = Listing(**l)
        db.add(listing)
    db.commit()
    return {"status": "success", "listings_added": len(listings)}

@app.get("/scrape_wolf")
def scrape_wolf_get():
    listings = scrape_wolf()
    return {"status": "success", "listings": listings}
