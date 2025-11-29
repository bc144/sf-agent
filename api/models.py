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


class WhatsAppRequest(BaseModel):
    query: str
    conversation_id: str
    phone_number: Optional[str] = None

class CartItem(BaseModel):
    product_id: str
    title: str
    brand: Optional[str] = None
    category: Optional[str] = None
    price: float
    quantity: int = 1
    color: Optional[str] = None
    size: Optional[str] = None
    image_url: Optional[str] = None

# Agregar este modelo en models.py o al inicio
class CheckoutRequest(BaseModel):
    cart: List[Dict[str, Any]]
    customer_name: str  # Nombre de WhatsApp
    customer_phone: str  # Número de teléfono

class Order(BaseModel):
    order_id: str
    session_id: str
    customer_name: str
    customer_phone: str
    cart: List[CartItem]
    amount_total: float
    currency: str
    status: str
    payment_status: str
    created_at: str