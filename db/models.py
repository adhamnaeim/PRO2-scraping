from sqlalchemy import Column, Integer, String, Float
from db.database import Base

class Listing(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True)
    title = Column(String, nullable=True)
    rent = Column(Integer, nullable=True)
    area = Column(Integer, nullable=True)
    address = Column(String, nullable=True)
    # AI scraper telemetry
    ai_elapsed_time = Column(Float, nullable=True)
    ai_selector_time = Column(Float, nullable=True)
    ai_memory_usage = Column(Float, nullable=True)
    # Manual scraper telemetry
    manual_elapsed_time = Column(Float, nullable=True)
    manual_memory_usage = Column(Float, nullable=True)