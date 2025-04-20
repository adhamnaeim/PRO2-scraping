from fastapi import FastAPI, HTTPException
from db.models import ScrapedItem
from db.database import SessionLocal, engine, Base
from typing import List
from pydantic import BaseModel

app = FastAPI()

Base.metadata.create_all(bind=engine)

class ItemCreate(BaseModel):
    name: str
    price: float
    rating: float
    description: str

@app.get("/items")
def get_items():
    db = SessionLocal()
    items = db.query(ScrapedItem).all()
    db.close()
    return items

@app.post("/items")
def create_item(item: ItemCreate):
    db = SessionLocal()
    db_item = ScrapedItem(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    db.close()
    return db_item