import json
import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from sentence_transformers import SentenceTransformer

try:  # pragma: no cover - import shim for script/module execution
    from .models import AskRequest, Constraints, ConversationalResponse, ProductCard, SearchRequest, SearchResponse
    from .qdrant_setup import COLLECTION_NAME, VECTOR_NAME, ensure_collection
except ImportError:  # pragma: no cover
    from models import AskRequest, Constraints, ConversationalResponse, ProductCard, SearchRequest, SearchResponse  # type: ignore
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
    
    # System prompt with guardrails
    system_prompt = """You are a helpful shopping assistant for an e-commerce platform.

IMPORTANT GUARDRAILS:
1. ONLY recommend products from the available inventory
2. NEVER give health, fitness, or lifestyle advice (like "lose weight", "exercise more", etc.)
3. If someone mentions personal attributes (overweight, tall, short, etc.), ONLY suggest clothing/products that might fit or suit them
4. Focus on product features: comfort, style, fit, size availability, color preferences
5. Be supportive and positive about helping them find great products
6. If asked about non-product topics, politely redirect to product recommendations

Your task:
1. Understand the user's needs from their query
2. Extract search keywords and filters (category, price, color, size, etc.)
3. Provide a friendly, helpful response
4. You will be given search results to reference

Output ONLY a valid JSON object with this structure:
{
    "search_query": "keywords to search products",
    "filters": {
        "category": "optional category like Clothing, Footwear, etc.",
        "price_max": optional_number,
        "color": "optional color",
        "size": "optional size"
    },
    "conversational_response": "A warm, helpful response to the user (2-3 sentences max)"
}

Examples:
User: "I'm overweight, what do you recommend?"
Response: {
    "search_query": "comfortable loose fit clothing",
    "filters": {"category": "Clothing"},
    "conversational_response": "I'd love to help you find comfortable and stylish clothing! Let me show you some great options with relaxed fits and comfortable fabrics that look amazing."
}

User: "I like black, what shoes do you have?"
Response: {
    "search_query": "black shoes",
    "filters": {"color": "black", "category": "Footwear"},
    "conversational_response": "Great choice! Black shoes are versatile and stylish. Here are some fantastic black footwear options for you."
}"""

    try:
        # Step 1: Use OpenAI to parse the query and generate intent
        chat_response = _openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.query}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        agent_output = chat_response.choices[0].message.content
        
        # Parse the JSON response
        try:
            parsed = json.loads(agent_output)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            parsed = {
                "search_query": request.query,
                "filters": {},
                "conversational_response": "Let me find some great products for you!"
            }
        
        search_query = parsed.get("search_query", request.query)
        filters_dict = parsed.get("filters", {})
        conversational_text = parsed.get("conversational_response", "Here are some products I think you'll love!")
        
        # Step 2: Build constraints from filters
        constraints = Constraints(
            category=filters_dict.get("category"),
            price_max=filters_dict.get("price_max"),
            price_min=filters_dict.get("price_min"),
            color=filters_dict.get("color"),
            size=filters_dict.get("size"),
            brand=filters_dict.get("brand")
        )
        
        # Step 3: Search for products
        vector = _model.encode([search_query], normalize_embeddings=True)[0].tolist()
        qdrant_filter = _build_filter(constraints)
        
        hits = _client.search(
            collection_name=COLLECTION_NAME,
            query_vector=(VECTOR_NAME, vector),
            limit=6,  # Return up to 6 products
            query_filter=qdrant_filter,
        )
        
        # Step 4: Build product cards with AI-generated "why"
        items: List[ProductCard] = []
        product_summaries = []
        
        for hit in hits:
            payload = hit.payload or {}
            colors = payload.get("colors") or []
            if isinstance(colors, str):
                colors = [c.strip() for c in colors.split(";") if c.strip()]
            sizes = payload.get("sizes") or []
            if isinstance(sizes, str):
                sizes = [s.strip() for s in sizes.split(";") if s.strip()]
            price = float(payload.get("price", 0.0))
            
            product_summaries.append({
                "title": payload.get("title", "Unknown Product"),
                "price": price,
                "category": payload.get("category"),
                "colors": colors,
                "sizes": sizes
            })
            
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
                    why=_build_why(payload, constraints, colors, sizes, price),
                )
            )
        
        # Step 5: Enhance the response with product context if no products found
        if not items:
            conversational_text += " Unfortunately, I couldn't find products matching those exact criteria. Try browsing our catalog or adjusting your preferences!"
        
        return ConversationalResponse(
            response=conversational_text,
            items=items
        )
        
    except Exception as e:
        # Fallback to basic search if AI fails
        vector = _model.encode([request.query], normalize_embeddings=True)[0].tolist()
        hits = _client.search(
            collection_name=COLLECTION_NAME,
            query_vector=(VECTOR_NAME, vector),
            limit=6,
            query_filter=rest.Filter(must=[
                rest.FieldCondition(key="in_stock", match=rest.MatchValue(value=True))
            ]),
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
                    why="Matches your search"
                )
            )
        
        return ConversationalResponse(
            response="Here are some products I found for you!",
            items=items
        )
