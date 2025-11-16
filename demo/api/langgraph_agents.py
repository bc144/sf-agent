"""
LangGraph Multi-Agent Orchestration System
Handles Chrome extension requests with search history context.
"""

import json
import os
from typing import Literal, List, TypedDict, Annotated
import operator

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from openai import OpenAI
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from sentence_transformers import SentenceTransformer

try:  # pragma: no cover
    from .models import (
        AgentState,
        Constraints,
        IntentClassification,
        ProductCard,
        ProductIdeas,
    )
    from .qdrant_setup import COLLECTION_NAME, VECTOR_NAME, ensure_collection
except ImportError:  # pragma: no cover
    from models import (  # type: ignore
        AgentState,
        Constraints,
        IntentClassification,
        ProductCard,
        ProductIdeas,
    )
    from qdrant_setup import COLLECTION_NAME, VECTOR_NAME, ensure_collection  # type: ignore

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Initialize global resources
_openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
_embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
_qdrant_client: QdrantClient = ensure_collection()


# ============ State Definition for LangGraph ============

class GraphState(TypedDict):
    """State schema for LangGraph workflow"""
    raw_query: str
    previous_searches: List[str]
    timestamp: str
    intent: IntentClassification | None
    product_ideas: ProductIdeas | None
    final_products: List[ProductCard]
    response_message: str
    notification_sent: bool


# ============ NODE 1: Router Agent (Intent Classification) ============

def classify_intent(state: dict) -> dict:
    """
    Router Agent: Classifies user intent using LLM with search history context.
    Analyzes patterns across searches to identify shopping opportunities.
    Returns IntentClassification model.
    """
    raw_query = state["raw_query"]
    previous_searches = state.get("previous_searches", [])
    timestamp = state.get("timestamp", "")
    
    # Build context-aware prompt
    history_context = ""
    if previous_searches:
        history_context = f"\n\nUser's recent search history (chronological):\n" + "\n".join(
            f"{i+1}. {search}" for i, search in enumerate(previous_searches)
        )
    
    system_prompt = f"""You are an intelligent intent classification agent for an e-commerce platform specializing in clothing, footwear, accessories, electronics, and home goods.

Your job is to analyze search patterns and identify shopping opportunities, even from non-shopping queries.

CLASSIFICATION RULES:
1. **direct_product_search**: User explicitly searches for products (e.g., "red shoes", "laptop under $1000")

2. **contextual_use_case**: Infer shopping needs from context and search patterns:
   - Life events: "vacation in rainy place" → rain gear needed
   - Weather/season: "is it going to rain" → raincoats, boots
   - Activities: "going to wedding" → formal wear
   - Situations: "started gym" → activewear
   IMPORTANT: Look at the PATTERN of searches, not just the current query!

3. **off_topic**: Queries unrelated to our product categories:
   - Auto parts (tires, car batteries)
   - Services (plumber, dentist)
   - Pure information seeking with no shopping context
   - Food/restaurants

PRODUCT CATEGORIES WE CARRY:
- Clothing (dresses, shirts, pants, jackets, activewear, formal wear)
- Footwear (shoes, boots, sandals, sneakers)
- Accessories (watches, bags, jewelry, sunglasses)
- Electronics (laptops, phones, gadgets)
- Home goods

Current Query: "{raw_query}"
Timestamp: {timestamp}{history_context}

EXAMPLES:
❌ "new tires toyota tacoma" → off_topic (auto parts, not in our inventory)
✅ "is it going to rain in november" + "vacation in rainy place" → contextual_use_case (rain gear needed)
✅ "started running" + "best running shoes" → direct_product_search
✅ "beach vacation" → contextual_use_case (swimwear, sunglasses, beach accessories)

Output ONLY a valid JSON object:
{{
    "intent_type": "direct_product_search" | "contextual_use_case" | "off_topic",
    "confidence": 0.0-1.0,
    "reasoning": "Explain your classification considering search history patterns",
    "extracted_keywords": ["keyword1", "keyword2"],
    "inferred_constraints": {{
        "category": "category from our inventory",
        "price_max": optional_number,
        "price_min": optional_number,
        "color": "optional color",
        "size": "optional size",
        "brand": "optional brand"
    }}
}}"""
    
    try:
        response = _openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": system_prompt}],
            temperature=0.3,
            max_tokens=500
        )
        
        result_text = response.choices[0].message.content.strip()
        parsed = json.loads(result_text)
        
        # Build IntentClassification
        intent = IntentClassification(
            intent_type=parsed["intent_type"],
            confidence=parsed["confidence"],
            reasoning=parsed["reasoning"],
            extracted_keywords=parsed.get("extracted_keywords", []),
            inferred_constraints=Constraints(**parsed.get("inferred_constraints", {}))
        )
        
        print(f"\n🎯 ROUTER AGENT: {intent.intent_type} (confidence: {intent.confidence})")
        print(f"   Reasoning: {intent.reasoning}")
        
        return {"intent": intent}
        
    except Exception as e:
        print(f"Error in classify_intent: {e}")
        # Fallback: assume direct product search
        return {
            "intent": IntentClassification(
                intent_type="direct_product_search",
                confidence=0.5,
                reasoning="Fallback classification due to error",
                extracted_keywords=[raw_query],
                inferred_constraints=Constraints()
            )
        }


# ============ NODE 2: Creative Agent (Generate Product Ideas) ============

def generate_ideas(state: dict) -> dict:
    """
    Creative Agent: Maps contextual use cases to product types and search queries.
    Only called for contextual_use_case intent.
    """
    raw_query = state["raw_query"]
    previous_searches = state.get("previous_searches", [])
    intent: IntentClassification = state["intent"]
    
    # Build comprehensive context from search history
    history_context = ""
    if previous_searches:
        history_context = f"\n\nSearch pattern analysis (chronological):\n" + "\n".join(
            f"{i+1}. {search}" for i, search in enumerate(previous_searches)
        )
        history_context += f"\n\nCurrent query: {raw_query}"
    
    system_prompt = f"""You are a creative product recommendation agent for an e-commerce platform.

Your task: Analyze the user's search pattern and current situation to recommend relevant products from our inventory.

CONTEXT:
- User's situation: {raw_query}
- Intent classification: {intent.reasoning}
- Confidence: {intent.confidence}
- Keywords identified: {', '.join(intent.extracted_keywords)}{history_context}

OUR PRODUCT CATEGORIES:
- Clothing: dresses, shirts, pants, jackets, raincoats, activewear, formal wear
- Footwear: shoes, boots, sandals, sneakers, rain boots
- Accessories: watches, bags, jewelry, sunglasses, umbrellas
- Electronics: laptops, phones, gadgets, cameras
- Home goods

YOUR JOB:
1. Map the user's context/pattern to specific product types we carry
2. Generate 2-4 optimized search queries that will find relevant products
3. Prioritize products that match the inferred need

Output ONLY a valid JSON object:
{{
    "product_types": ["specific_type1", "specific_type2", "specific_type3"],
    "search_queries": ["query1", "query2", "query3"],
    "user_context": "Clear summary of shopping need based on pattern"
}}

EXAMPLES:
Input: "is it going to rain in november" + "vacation in rainy place"
Output: {{
    "product_types": ["jackets", "boots", "waterproof clothing"],
    "search_queries": ["jacket", "boots", "waterproof", "coat"],
    "user_context": "User planning vacation in rainy climate, needs rain gear"
}}

Input: "beach vacation next month" + "sunscreen recommendations"
Output: {{
    "product_types": ["swimwear", "sunglasses", "bags", "sandals"],
    "search_queries": ["dress", "sunglasses", "sandals", "bag"],
    "user_context": "User preparing for beach vacation, needs summer/beach attire"
}}

Input: "started going to gym" + "workout tips"
Output: {{
    "product_types": ["activewear", "sports shoes", "bags"],
    "search_queries": ["sports", "shoes", "bag", "fitness"],
    "user_context": "User starting fitness journey, needs workout gear"
}}

IMPORTANT: Use BROAD, GENERIC terms that will match many products in our database. Avoid overly specific terms like "raincoat" - use "jacket" or "coat" instead.
"""
    
    try:
        response = _openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": system_prompt}],
            temperature=0.7,
            max_tokens=400
        )
        
        result_text = response.choices[0].message.content.strip()
        parsed = json.loads(result_text)
        
        product_ideas = ProductIdeas(
            product_types=parsed["product_types"],
            search_queries=parsed["search_queries"],
            user_context=parsed["user_context"]
        )
        
        print(f"\n💡 CREATIVE AGENT:")
        print(f"   Context: {product_ideas.user_context}")
        print(f"   Search queries: {product_ideas.search_queries}")
        
        return {"product_ideas": product_ideas}
        
    except Exception as e:
        print(f"Error in generate_ideas: {e}")
        # Fallback
        return {
            "product_ideas": ProductIdeas(
                product_types=["general"],
                search_queries=[raw_query],
                user_context="General product search"
            )
        }


# ============ NODE 3: RAG Agent (Search Vector Database) ============

def search_rag(state: dict) -> dict:
    """
    RAG Agent: Searches Qdrant vector database using query or product ideas.
    Returns validated final_products.
    """
    intent: IntentClassification = state["intent"]
    product_ideas: ProductIdeas | None = state.get("product_ideas")
    raw_query = state["raw_query"]
    
    # Determine search queries
    if intent.intent_type == "contextual_use_case" and product_ideas:
        # Use Creative Agent's optimized queries
        search_queries = product_ideas.search_queries
        constraints = intent.inferred_constraints
    elif intent.intent_type == "direct_product_search":
        # Use Router Agent's extracted keywords
        search_queries = intent.extracted_keywords or [raw_query]
        constraints = intent.inferred_constraints
    else:
        # Off-topic: no search
        return {
            "final_products": [],
            "response_message": "I'm here to help you find products! Please ask about items you'd like to purchase."
        }
    
    # Build Qdrant filter
    must_conditions = [
        rest.FieldCondition(key="in_stock", match=rest.MatchValue(value=True))
    ]
    
    if constraints.category:
        must_conditions.append(
            rest.FieldCondition(key="category", match=rest.MatchValue(value=constraints.category))
        )
    if constraints.brand:
        must_conditions.append(
            rest.FieldCondition(key="brand", match=rest.MatchValue(value=constraints.brand))
        )
    if constraints.color:
        must_conditions.append(
            rest.FieldCondition(key="colors", match=rest.MatchValue(value=constraints.color))
        )
    if constraints.size:
        must_conditions.append(
            rest.FieldCondition(key="sizes", match=rest.MatchValue(value=constraints.size))
        )
    
    # Price range
    if constraints.price_min is not None or constraints.price_max is not None:
        range_params = {}
        if constraints.price_min is not None:
            range_params["gte"] = constraints.price_min
        if constraints.price_max is not None:
            range_params["lte"] = constraints.price_max
        must_conditions.append(
            rest.FieldCondition(key="price", range=rest.Range(**range_params))
        )
    
    qdrant_filter = rest.Filter(must=must_conditions)
    
    # Perform searches for all queries
    all_products: List[ProductCard] = []
    seen_ids = set()
    
    for query in search_queries[:3]:  # Limit to top 3 queries
        try:
            vector = _embedding_model.encode([query], normalize_embeddings=True)[0].tolist()
            
            hits = _qdrant_client.search(
                collection_name=COLLECTION_NAME,
                query_vector=(VECTOR_NAME, vector),
                limit=4,  # 4 products per query
                query_filter=qdrant_filter,
            )
            
            for hit in hits:
                product_id = hit.payload.get("product_id", str(hit.id))
                if product_id in seen_ids:
                    continue
                seen_ids.add(product_id)
                
                payload = hit.payload or {}
                colors = payload.get("colors") or []
                if isinstance(colors, str):
                    colors = [c.strip() for c in colors.split(";") if c.strip()]
                sizes = payload.get("sizes") or []
                if isinstance(sizes, str):
                    sizes = [s.strip() for s in sizes.split(";") if s.strip()]
                
                # Build "why" reasoning
                why_parts = []
                if constraints.category and payload.get("category") == constraints.category:
                    why_parts.append(f"Matches {constraints.category}")
                if constraints.price_max and payload.get("price", 0) <= constraints.price_max:
                    why_parts.append(f"Within budget (${constraints.price_max})")
                if not why_parts:
                    why_parts.append("Relevant to your search")
                
                all_products.append(
                    ProductCard(
                        product_id=product_id,
                        title=payload.get("title", "Unknown Product"),
                        brand=payload.get("brand"),
                        category=payload.get("category"),
                        price=float(payload.get("price", 0.0)),
                        colors=colors,
                        sizes=sizes,
                        image_url=payload.get("image_url"),
                        why="; ".join(why_parts)
                    )
                )
                
                if len(all_products) >= 8:  # Max 8 products total
                    break
        except Exception as e:
            print(f"Error searching for '{query}': {e}")
            continue
    
    # Generate response message
    if all_products:
        if intent.intent_type == "contextual_use_case" and product_ideas:
            response_msg = f"Based on your interest in {product_ideas.user_context.lower()}, here are some great options!"
        else:
            response_msg = f"I found {len(all_products)} products matching your search!"
    else:
        response_msg = "I couldn't find products matching your criteria. Try adjusting your preferences!"
    
    print(f"\n🔍 RAG AGENT: Found {len(all_products)} products")
    if search_queries:
        print(f"   Searched: {', '.join(search_queries[:3])}")
    
    return {
        "final_products": all_products,
        "response_message": response_msg
    }


# ============ NODE 4: Notification Tool (Send Notification) ============

def send_notification(state: dict) -> dict:
    """
    Notification Tool: Triggers external notification only when relevant products are found.
    Sends email with product recommendations based on user's search pattern.
    """
    final_products = state["final_products"]
    response_message = state["response_message"]
    intent: IntentClassification | None = state.get("intent")
    product_ideas: ProductIdeas | None = state.get("product_ideas")
    raw_query = state["raw_query"]
    previous_searches = state.get("previous_searches", [])
    
    # Only send notification if:
    # 1. Products were found
    # 2. Intent confidence is high enough (>0.6)
    # 3. It's not an off-topic query
    should_notify = (
        len(final_products) > 0 
        and intent 
        and intent.confidence >= 0.6 
        and intent.intent_type != "off_topic"
    )
    
    if not should_notify:
        print(f"⏭️  Notification skipped: {len(final_products)} products, confidence: {intent.confidence if intent else 0}")
        return {"notification_sent": False}
    
    # Build email content
    email_subject = "🛍️ We Found Perfect Products For You!"
    
    if product_ideas:
        context = product_ideas.user_context
    else:
        context = f"your search for {raw_query}"
    
    email_body = f"""
Hi there! 👋

Based on {context}, we thought you might be interested in these products:

{response_message}

RECOMMENDED PRODUCTS:
"""
    
    for i, product in enumerate(final_products[:6], 1):
        email_body += f"""
{i}. {product.title}
   Price: ${product.price}
   {product.why or 'Perfect for your needs'}
   {f'Brand: {product.brand}' if product.brand else ''}
   {f'View: {product.image_url}' if product.image_url else ''}
"""
    
    email_body += """

Click here to view all products: http://localhost:8000

Happy shopping! 🛒

---
This notification was triggered by your recent browsing pattern.
"""
    
    # Log the notification (in production, actually send email)
    print(f"\n📧 ═══════════════════════════════════════")
    print(f"📧 EMAIL NOTIFICATION SENT")
    print(f"📧 ═══════════════════════════════════════")
    print(f"To: user@example.com")
    print(f"Subject: {email_subject}")
    print(f"Products: {len(final_products)} items")
    print(f"Context: {context}")
    if previous_searches:
        print(f"Triggered by search pattern:")
        for search in previous_searches:
            print(f"  - {search}")
        print(f"  → {raw_query}")
    print(f"📧 ═══════════════════════════════════════\n")
    
    # TODO: Integrate with actual email service
    # Example with SendGrid:
    # from sendgrid import SendGridAPIClient
    # from sendgrid.helpers.mail import Mail
    # 
    # message = Mail(
    #     from_email='noreply@yourstore.com',
    #     to_emails='user@example.com',
    #     subject=email_subject,
    #     html_content=email_body.replace('\n', '<br>')
    # )
    # sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
    # response = sg.send(message)
    
    return {"notification_sent": True}


# ============ Routing Logic ============

def route_after_intent(state: dict) -> Literal["generate_ideas", "search_rag", "off_topic_end"]:
    """
    Router function: decides next node based on intent classification.
    """
    intent: IntentClassification = state["intent"]
    
    if intent.intent_type == "contextual_use_case":
        return "generate_ideas"
    elif intent.intent_type == "direct_product_search":
        return "search_rag"
    else:
        return "off_topic_end"


def off_topic_handler(state: dict) -> dict:
    """Handle off-topic queries"""
    return {
        "final_products": [],
        "response_message": "I'm here to help you find products! Please ask about items you'd like to purchase.",
        "notification_sent": False
    }


# ============ Build LangGraph Workflow ============

def create_agent_graph():
    """
    Creates and returns the LangGraph StateGraph for multi-agent orchestration.
    """
    # Define the state graph with proper TypedDict
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("generate_ideas", generate_ideas)
    workflow.add_node("search_rag", search_rag)
    workflow.add_node("send_notification", send_notification)
    workflow.add_node("off_topic_end", off_topic_handler)
    
    # Set entry point
    workflow.set_entry_point("classify_intent")
    
    # Add conditional routing after intent classification
    workflow.add_conditional_edges(
        "classify_intent",
        route_after_intent,
        {
            "generate_ideas": "generate_ideas",
            "search_rag": "search_rag",
            "off_topic_end": "off_topic_end"
        }
    )
    
    # Creative Agent → RAG Agent
    workflow.add_edge("generate_ideas", "search_rag")
    
    # RAG Agent → Notification Tool
    workflow.add_edge("search_rag", "send_notification")
    
    # All paths end after notification or off-topic
    workflow.add_edge("send_notification", END)
    workflow.add_edge("off_topic_end", END)
    
    return workflow.compile()


# Initialize the compiled graph
agent_graph = create_agent_graph()


# ============ Main Execution Function ============

def run_agent_workflow(query: str, previous_searches: List[str], timestamp: str) -> dict:
    """
    Main entry point to run the LangGraph workflow.
    
    Args:
        query: User's current search query
        previous_searches: List of previous search queries
        timestamp: ISO timestamp of the current query
        
    Returns:
        dict with final_products, response_message, and notification_sent
    """
    try:
        initial_state: GraphState = {
            "raw_query": query,
            "previous_searches": previous_searches,
            "timestamp": timestamp,
            "intent": None,
            "product_ideas": None,
            "final_products": [],
            "response_message": "",
            "notification_sent": False
        }
        
        # Run the graph
        result: GraphState = agent_graph.invoke(initial_state)
        
        return {
            "response": result.get("response_message", "Here are some products for you!"),
            "items": result.get("final_products", []),
            "intent": result.get("intent"),
            "notification_sent": result.get("notification_sent", False)
        }
    except Exception as e:
        print(f"Error in run_agent_workflow: {e}")
        import traceback
        traceback.print_exc()
        raise

