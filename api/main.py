import json
import os
import sys
from pathlib import Path
from typing import List, Optional

# Add parent directory to path to allow importing kapso
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from kapso.client import KapsoClient
# from kapso.utils import normalize_kapso_webhook
from kapso.use_kapso import use_kapso
from agent.ask_agent import ask_agent_logic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from sentence_transformers import SentenceTransformer
import stripe

try:  # pragma: no cover - import shim for script/module execution
    from .models import AskRequest, Constraints, ConversationalResponse, ProductCard, SearchRequest, SearchResponse, WhatsAppRequest
    from .qdrant_setup import COLLECTION_NAME, VECTOR_NAME, ensure_collection
except ImportError:  # pragma: no cover
    from models import AskRequest, Constraints, ConversationalResponse, ProductCard, SearchRequest, SearchResponse, WhatsAppRequest  # type: ignore
    from qdrant_setup import COLLECTION_NAME, VECTOR_NAME, ensure_collection  # type: ignore

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

app = FastAPI(title="Product Search API", version="1.0.0")

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
_client: QdrantClient = ensure_collection()
_openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@app.get("/")
def root():
    """Root endpoint"""
    return {"status": "ok", "service": "Product Search API"}


@app.get("/health")
def health():
    """Health check for Render"""
    return {"status": "healthy"}


def _build_filter(constraints: Constraints) -> rest.Filter:
    must: List[rest.FieldCondition] = []

    must.append(rest.FieldCondition(key="in_stock", match=rest.MatchValue(value=True)))

    if constraints.category:
        must.append(rest.FieldCondition(key="category", match=rest.MatchValue(value=constraints.category)))

    if constraints.brand:
        must.append(rest.FieldCondition(key="brand", match=rest.MatchValue(value=constraints.brand)))

    if constraints.color:
        must.append(rest.FieldCondition(key="colors", match=rest.MatchValue(value=constraints.color)))

    if constraints.size:
        must.append(rest.FieldCondition(key="sizes", match=rest.MatchValue(value=constraints.size)))

    range_conditions = {}
    if constraints.price_min is not None:
        range_conditions["gte"] = constraints.price_min
    if constraints.price_max is not None:
        range_conditions["lte"] = constraints.price_max
    if range_conditions:
        must.append(rest.FieldCondition(key="price", range=rest.Range(**range_conditions)))

    return rest.Filter(must=must)


def _build_why(payload: dict, constraints: Constraints, colors: List[str], sizes: List[str], price: float) -> str:
    reasons: List[str] = []

    if constraints.category and payload.get("category") == constraints.category:
        reasons.append(f"Matches the {constraints.category} category")

    if constraints.color and constraints.color in colors:
        reasons.append(f"Available in {constraints.color}")

    if constraints.size and constraints.size in sizes:
        reasons.append(f"Offered in size {constraints.size}")

    if constraints.price_max is not None and price <= constraints.price_max:
        reasons.append(f"Within your budget (${constraints.price_max:.0f} max)")

    if not reasons:
        reasons.append("Matches your style")

    return "; ".join(reasons)


@app.post("/search", response_model=SearchResponse)
def search_products(request: SearchRequest) -> SearchResponse:
    vector = _model.encode([request.query], normalize_embeddings=True)[0].tolist()
    qdrant_filter = _build_filter(request.constraints)

    hits = _client.search(
        collection_name=COLLECTION_NAME,
        query_vector=(VECTOR_NAME, vector),
        limit=request.k,
        query_filter=qdrant_filter,
    )

    items: List[ProductCard] = []
    for hit in hits:
        payload = hit.payload or {}
        colors = payload.get("colors") or []
        if isinstance(colors, str):
            colors = [c.strip() for c in colors.split(";") if c.strip()]
        sizes = payload.get("sizes") or []
        if isinstance(sizes, str):
            sizes = [s.strip() for s in sizes.split(";") if s.strip()]
        price = float(payload.get("price", 0.0))
        items.append(
            ProductCard(
                product_id=payload.get("product_id", str(hit.id)),
                title=payload.get("title", "Unknown Product"),
                brand=payload.get("brand"),
                category=payload.get("category"),
                price=price,
                colors=colors,
                sizes=sizes,
                image_url=payload.get("image_url"),
                why=_build_why(payload, request.constraints, colors, sizes, price),
            )
        )

    return SearchResponse(items=items)


@app.post("/ask", response_model=ConversationalResponse)
def ask_agent(request: AskRequest) -> ConversationalResponse:
    """
    Conversational agent endpoint that understands natural language queries
    and provides personalized product recommendations.
    """
    return ask_agent_logic(request)


# ============= STRIPE ROUTES =============

@app.post("/create-checkout-session")
async def create_checkout_session(request: Request):
    """
    Crea una sesión de pago de Stripe para pago único.
    Espera: { 
        "cart": [
            {
                "product_id": "id1",
                "quantity": 1,
                "color": "red",
                "size": "M"
            }
        ],
        "customer_name": "Juan Pérez",
        "customer_phone": "+52 123 456 7890"
    }
    """
    try:
        data = await request.json()
        cart = data.get("cart", [])
        customer_name = data.get("customer_name")
        customer_phone = data.get("customer_phone")
        
        if not cart:
            raise HTTPException(status_code=400, detail="Cart is empty")
        
        if not customer_name or not customer_phone:
            raise HTTPException(status_code=400, detail="Customer name and phone are required")
        
        # Construir line_items y metadata
        line_items = []
        product_ids = []
        
        for item in cart:
            product_id = item.get("product_id")
            quantity = item.get("quantity", 1)
            
            if not product_id:
                continue
                
            product_ids.append(product_id)
            
            # Buscar el producto en Qdrant
            results = _client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=rest.Filter(
                    must=[
                        rest.FieldCondition(
                            key="product_id",
                            match=rest.MatchValue(value=product_id)
                        )
                    ]
                ),
                limit=1
            )
            
            if results[0]:
                product = results[0][0].payload
                
                # Descripción con color y talla si están disponibles
                description_parts = [product.get("category", "")]
                if item.get("color"):
                    description_parts.append(f"Color: {item['color']}")
                if item.get("size"):
                    description_parts.append(f"Size: {item['size']}")
                
                line_items.append({
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": product.get("title", "Product"),
                            "description": " | ".join(filter(None, description_parts)),
                            "images": [product.get("image_url")] if product.get("image_url") else [],
                        },
                        "unit_amount": int(float(product.get("price", 0)) * 100),
                    },
                    "quantity": quantity,
                })
        
        if not line_items:
            raise HTTPException(status_code=404, detail="No valid products found")
        
        # Crear sesión de Stripe
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=line_items,
            mode="payment",
            success_url=f"{os.getenv('DOMAIN', 'http://localhost:8000')}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{os.getenv('DOMAIN', 'http://localhost:8000')}/cancel",
            metadata={
                "product_ids": ",".join(product_ids),
                "cart_json": json.dumps(cart),
                "customer_name": customer_name,
                "customer_phone": customer_phone
            }
        )
        
        return JSONResponse({
            "checkout_url": checkout_session.url,
            "session_id": checkout_session.id
        })
        
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/payment-success")
async def payment_success(session_id: str):
    """
    Procesa el pago exitoso después de que Stripe redirija aquí.
    Guarda la orden con el carrito completo y datos del cliente de WhatsApp.
    """
    try:
        # Recuperar la sesión de Stripe
        session = stripe.checkout.Session.retrieve(
            session_id,
            expand=['line_items']
        )
        
        if session.payment_status != "paid":
            return JSONResponse({
                "status": "pending",
                "message": "Payment is still processing",
                "payment_status": session.payment_status
            })
        
        # Obtener datos del cliente desde metadata
        customer_name = session.metadata.get("customer_name", "Unknown")
        customer_phone = session.metadata.get("customer_phone", "Unknown")
        
        # Recuperar el carrito del metadata
        cart_json = session.metadata.get("cart_json", "[]")
        cart_data = json.loads(cart_json)
        
        # Construir el carrito con información completa de los productos
        cart_items = []
        for item in cart_data:
            product_id = item.get("product_id")
            if not product_id:
                continue
                
            # Buscar el producto en Qdrant
            results = _client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=rest.Filter(
                    must=[
                        rest.FieldCondition(
                            key="product_id",
                            match=rest.MatchValue(value=product_id)
                        )
                    ]
                ),
                limit=1
            )
            
            if results[0]:
                product = results[0][0].payload
                
                # Parsear colors y sizes si son strings
                colors = product.get("colors") or []
                if isinstance(colors, str):
                    colors = [c.strip() for c in colors.split(";") if c.strip()]
                
                sizes = product.get("sizes") or []
                if isinstance(sizes, str):
                    sizes = [s.strip() for s in sizes.split(";") if s.strip()]
                
                cart_item = {
                    "product_id": product_id,
                    "title": product.get("title", "Unknown Product"),
                    "brand": product.get("brand"),
                    "category": product.get("category"),
                    "price": float(product.get("price", 0)),
                    "quantity": item.get("quantity", 1),
                    "color": item.get("color") or (colors[0] if colors else None),
                    "size": item.get("size") or (sizes[0] if sizes else None),
                    "image_url": product.get("image_url")
                }
                cart_items.append(cart_item)
        
        # Crear el objeto de orden completo
        order_data = {
            "order_id": f"ORD-{session_id[:8].upper()}",
            "session_id": session_id,
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "cart": cart_items,
            "amount_total": session.amount_total / 100,
            "currency": session.currency.upper(),
            "status": "completed",
            "payment_status": session.payment_status,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Guardar en archivo JSON (puedes cambiar esto a tu DB)
        orders_dir = Path(__file__).parent / "orders"
        orders_dir.mkdir(exist_ok=True)
        order_file = orders_dir / f"{order_data['order_id']}.json"
        
        with open(order_file, "w", encoding="utf-8") as f:
            json.dump(order_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Order saved: {order_data['order_id']}")
        print(f"   Customer: {customer_name} ({customer_phone})")
        print(f"   Items: {len(cart_items)}")
        print(f"   Total: ${order_data['amount_total']:.2f} {order_data['currency']}")
        
        return JSONResponse({
            "status": "success",
            "message": "Payment completed successfully",
            "order": order_data
        })
            
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")
    except Exception as e:
        print(f"❌ Error processing order: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

# ============= END STRIPE ROUTES =============


@app.post("/whatsapp", response_model=ConversationalResponse)
async def whatsapp_agent(request: Request) -> ConversationalResponse:
    """
    Endpoint that receives a query, processes it using the agent logic,
    sends the response via Kapso (WhatsApp), and returns the response.
    """
    webhook_data = await request.json()
    
    result = await use_kapso(webhook_data)
    
    # Verificar el resultado
    if result.get("status") == "success":
        return result
    else:
        return HTTPException(status_code=500, detail=result.get("message", "Error procesando webhook"))