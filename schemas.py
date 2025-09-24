import enum
from pydantic import BaseModel, HttpUrl, Field, conint
from typing import Literal, Optional, List

# --- Enum 정의 ---
class SexEnum(str, enum.Enum):
    male = "male"
    female = "female"

class DrinkCount(int, enum.Enum):
    ZERO = 0
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR_OR_MORE = 4

# --- API 요청 스키마 ---
class RecommendationRequest(BaseModel):
    age: conint(ge=1) = Field(..., description="사용자 나이 (1 이상의 자연수)", example=30)
    sex: SexEnum = Field(..., description="사용자 성별")
    drinkCount: DrinkCount = Field(..., description="주량")
    userQuery: str = Field(..., description="사용자의 추천 요청 질문", example="포도랑 같이 마실 산뜻한 술 추천해줘")

# --- API 응답 스키마 ---
class RecommendationResponseItem(BaseModel):
    id: int
    liquorName: str
    reason: str

    class Config:
        from_attributes = True

class FoodPairingResponse(BaseModel):
    foodName: str = Field(..., description="추천 페어링 음식 이름")

class LiquorSchema(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    alcohol_content: Optional[float] = None
    volume: Optional[int] = None
    ingredients: Optional[str] = None
    notes: Optional[str] = None
    features: Optional[str] = None
    brewery_name: Optional[str] = None
    homepage_url: Optional[HttpUrl] = None
    awards: Optional[str] = None

    class Config:
        from_attributes = True

class Recommendation(BaseModel):
    id: int
    age: int
    sex: SexEnum
    drinkCount: int
    liquorName: str
    reason: str
    userQuery: Optional[str] = None

    class Config:
        from_attributes = True