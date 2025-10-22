from typing import List, Optional

from pydantic import BaseModel, Field


class Constraints(BaseModel):
    category: Optional[str] = None
    price_min: Optional[float] = Field(default=None, ge=0)
    price_max: Optional[float] = Field(default=None, ge=0)
    color: Optional[str] = None
    size: Optional[str] = None
    brand: Optional[str] = None
    notes: Optional[str] = None


class ProductCard(BaseModel):
    product_id: str
    title: str
    brand: Optional[str] = None
    category: Optional[str] = None
    price: float
    colors: List[str] = Field(default_factory=list)
    sizes: List[str] = Field(default_factory=list)
    image_url: Optional[str] = None
    why: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    constraints: Constraints = Field(default_factory=Constraints)
    k: int = Field(default=8, ge=1, le=50)


class SearchResponse(BaseModel):
    items: List[ProductCard]


class AskRequest(BaseModel):
    query: str


class ConversationalResponse(BaseModel):
    response: str
    items: List[ProductCard]
