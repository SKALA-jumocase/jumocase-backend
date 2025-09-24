import enum
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, Enum
from pgvector.sqlalchemy import Vector
from database import Base

# --- Liquor 테이블 정의 ---
class Liquor(Base):
    __tablename__ = "liquors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True, nullable=False)
    description = Column(Text)
    alcohol_content = Column(Float)
    volume = Column(Integer)
    ingredients = Column(Text)
    notes = Column(Text)
    features = Column(Text)
    is_for_sale = Column(Boolean, default=True)
    brewery_name = Column(String)
    brewery_address = Column(String)
    homepage_url = Column(String)
    awards = Column(Text)
    feature_embedding = Column(Vector(1536))

# --- Recommendation 테이블 정의 ---
class SexEnum(enum.Enum):
    male = "male"
    female = "female"

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    age = Column(Integer, nullable=False)
    sex = Column(Enum(SexEnum), nullable=False)
    drinkCount = Column(Integer, nullable=False)
    liquorName = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    userQuery = Column(Text, nullable=True)