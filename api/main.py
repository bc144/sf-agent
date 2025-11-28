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
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from sentence_transformers import SentenceTransformer

try:  # pragma: no cover - import shim for script/module execution
    from .models import AskRequest, Constraints, ConversationalResponse, ProductCard, SearchRequest, SearchResponse, WhatsAppRequest
    from .qdrant_setup import COLLECTION_NAME, VECTOR_NAME, ensure_collection
except ImportError:  # pragma: no cover
    from models import AskRequest, Constraints, ConversationalResponse, ProductCard, SearchRequest, SearchResponse, WhatsAppRequest  # type: ignore
    from qdrant_setup import COLLECTION_NAME, VECTOR_NAME, ensure_collection  # type: ignore

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


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
        
    
    
    
    # 1. Process the query using the shared ask_agent logic
    ask_req = AskRequest(query=request.query)
    agent_response = ask_agent_logic(ask_req)
    
    # 2. Send the response via Kapso
    try:
        # Initialize Kapso client
        with KapsoClient() as kapso:
            # Send the conversational text response
            kapso.send_message(
                conversation_id=request.conversation_id,
                message=agent_response.response
            )
            
            # Send product details if available
            if agent_response.items:
                products_text = "Here are the products I found:\n\n"
                for item in agent_response.items[:3]: # Limit to top 3
                    products_text += f"*{item.title}*\n"
                    products_text += f"Price: ${item.price}\n"
                    products_text += f"Why: {item.why}\n\n"
                
                kapso.send_message(
                    conversation_id=request.conversation_id,
                    message=products_text
                )
                
    except Exception as e:
        # We log the error but still return the response to the caller
    
    return agent_response
