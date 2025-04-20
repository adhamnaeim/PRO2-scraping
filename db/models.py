from sqlalchemy import Column, Integer, String, Float
from db.database import Base

class ScrapedItem(Base):
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    price = Column(Float)
    rating = Column(Float)
    description = Column(String)