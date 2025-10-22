# Conversational Agent API Documentation

## New Endpoint: `/ask` - Conversational Shopping Assistant

### Overview

The `/ask` endpoint provides a natural language conversational interface for product discovery. It uses OpenAI's GPT-4o-mini to understand user intent, extract filters, and provide personalized product recommendations with a conversational response.

---

## Endpoint Details

**URL:** `POST /ask`  
**Description:** Conversational agent that understands natural language queries and provides personalized recommendations

---

## Request Format

```json
{
  "query": "string"
}
```

### Request Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | `string` | **Yes** | Natural language query from the user |

---

## Response Format

```json
{
  "response": "string",
  "items": [
    {
      "product_id": "string",
      "title": "string",
      "brand": "string | null",
      "category": "string | null",
      "price": 0.0,
      "colors": ["string"],
      "sizes": ["string"],
      "image_url": "string | null",
      "why": "string | null"
    }
  ]
}
```

### Response Schema

| Field | Type | Description |
|-------|------|-------------|
| `response` | `string` | Conversational response from the AI agent |
| `items` | `array[ProductCard]` | Array of recommended products (0-6 items) |
| `items[].product_id` | `string` | Unique product identifier |
| `items[].title` | `string` | Product name |
| `items[].brand` | `string \| null` | Brand name |
| `items[].category` | `string \| null` | Product category |
| `items[].price` | `number` | Product price in rupees |
| `items[].colors` | `array[string]` | Available colors |
| `items[].sizes` | `array[string]` | Available sizes |
| `items[].image_url` | `string \| null` | Product image URL |
| `items[].why` | `string \| null` | Why this product matches the query |

---

## Guardrails

The conversational agent has built-in guardrails to ensure appropriate responses:

### ✅ What the Agent WILL Do:
- Provide product recommendations from the inventory
- Extract shopping preferences (color, size, price, category)
- Be supportive and positive
- Focus on product features (comfort, style, fit)
- Suggest alternatives if exact matches aren't found

### ❌ What the Agent WON'T Do:
- Give health, fitness, or lifestyle advice
- Suggest weight loss or exercise
- Make judgmental comments about personal attributes
- Recommend non-product solutions
- Discuss topics unrelated to shopping

### Example Guardrail in Action:

**User Query:**
```
"I am overweight, what do you recommend?"
```

**Agent Response:**
```json
{
  "response": "I'd love to help you find comfortable and stylish clothing! Let me show you some great options with relaxed fits and comfortable fabrics that look amazing.",
  "items": [...]
}
```

**❌ Will NOT say:** "You should lose weight" or "Try exercising more"  
**✅ WILL say:** Focuses on comfortable, stylish clothing options

---

## Example Requests

### Example 1: Personal Attribute + Preference

**Request:**
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I am an overweight person that likes the color black, what can you recommend?"
  }'
```

**Response:**
```json
{
  "response": "I'm here to help you find some stylish and comfortable black clothing options! Let's explore some pieces that will make you feel great and look fantastic.",
  "items": [
    {
      "product_id": "abc123",
      "title": "Comfortable Loose Fit Black Shirt",
      "brand": "Fashion Plus",
      "category": "Clothing",
      "price": 599.0,
      "colors": ["black"],
      "sizes": ["L", "XL", "XXL"],
      "image_url": "https://...",
      "why": "Available in black; Comfortable fit"
    }
  ]
}
```

---

### Example 2: Budget Constraint

**Request:**
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I need something affordable under 500 rupees"
  }'
```

**Response:**
```json
{
  "response": "I can help you find some great affordable options! Let me show you products that fit within your budget of 500 rupees.",
  "items": [
    {
      "product_id": "xyz789",
      "title": "Casual Women's Top",
      "price": 450.0,
      "why": "Within your budget ($500 max)"
    }
  ]
}
```

---

### Example 3: Style & Occasion

**Request:**
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I want something stylish for a party"
  }'
```

**Response:**
```json
{
  "response": "That sounds exciting! Let me help you find some stylish outfits that will make you stand out at the party. You'll look fabulous in no time!",
  "items": [
    {
      "product_id": "party001",
      "title": "Party Wear Dress",
      "category": "Clothing",
      "price": 799.0,
      "why": "Perfect for parties"
    }
  ]
}
```

---

### Example 4: Category + Budget

**Request:**
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me watches under 600 rupees"
  }'
```

**Response:**
```json
{
  "response": "Sure! I can help you find some stylish watches within your budget. Here are some great options under 600 rupees that you might love!",
  "items": [
    {
      "product_id": "watch001",
      "title": "Analog Watch - For Men",
      "category": "Watches",
      "price": 599.0,
      "why": "Within your budget ($600 max)"
    }
  ]
}
```

---

### Example 5: Personal Style

**Request:**
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I am a tall person who loves comfortable casual wear"
  }'
```

**Response:**
```json
{
  "response": "It's wonderful that you love comfortable casual wear! I can help you find some stylish options that are perfect for tall individuals. Let's explore some great choices together!",
  "items": [
    {
      "product_id": "casual001",
      "title": "Casual Comfortable Top",
      "category": "Clothing",
      "price": 349.0
    }
  ]
}
```

---

## JavaScript/TypeScript Example

```typescript
async function askAgent(query: string): Promise<ConversationalResponse> {
  const response = await fetch('http://localhost:8000/ask', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query })
  });
  
  if (!response.ok) {
    throw new Error('Agent request failed');
  }
  
  return await response.json();
}

// Usage
const result = await askAgent("I am overweight and like black clothes");
console.log(result.response); // Conversational response
console.log(result.items);    // Product recommendations
```

---

## React Hook Example

```typescript
import { useState } from 'react';

interface ConversationalResponse {
  response: string;
  items: ProductCard[];
}

export function useConversationalAgent() {
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<string>('');
  const [products, setProducts] = useState<ProductCard[]>([]);

  const ask = async (query: string) => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });
      
      const data: ConversationalResponse = await res.json();
      setResponse(data.response);
      setProducts(data.items);
    } catch (error) {
      console.error('Agent error:', error);
    } finally {
      setLoading(false);
    }
  };

  return { ask, loading, response, products };
}

// Usage in component
function ChatShop() {
  const { ask, loading, response, products } = useConversationalAgent();
  
  const handleSubmit = (query: string) => {
    ask(query);
  };
  
  return (
    <div>
      {loading && <Spinner />}
      {response && <p>{response}</p>}
      {products.map(p => <ProductCard key={p.product_id} product={p} />)}
    </div>
  );
}
```

---

## How It Works

1. **User Query** → Natural language input
2. **AI Processing** → OpenAI GPT-4o-mini parses intent
3. **Filter Extraction** → Extracts category, price, color, etc.
4. **Vector Search** → Searches Qdrant with semantic similarity
5. **Response Generation** → Creates conversational response
6. **Product Recommendations** → Returns up to 6 relevant products

---

## AI Model Details

- **Model:** GPT-4o-mini
- **Temperature:** 0.7 (balanced creativity)
- **Max Tokens:** 300
- **Approach:** Intent extraction + structured output

---

## Error Handling

If the AI fails or returns invalid JSON, the endpoint falls back to:
- Basic semantic search without filters
- Generic response: "Here are some products I found for you!"

---

## Response Codes

| Code | Description |
|------|-------------|
| `200` | Success |
| `422` | Validation Error (invalid request format) |
| `500` | Internal Server Error |

---

## Best Practices for Frontend Integration

### 1. Display the Conversational Response
Show the `response` field prominently - it's personalized and contextual

```tsx
<div className="agent-response">
  <p>{data.response}</p>
</div>
```

### 2. Handle Empty Results
```typescript
if (data.items.length === 0) {
  // Show "No products found" message
  // Suggest browsing categories or adjusting preferences
}
```

### 3. Loading States
Conversational queries take 1-3 seconds due to AI processing
```tsx
{loading && <div>Finding the perfect products for you...</div>}
```

### 4. Error Fallback
```typescript
try {
  const data = await askAgent(query);
  // Handle success
} catch (error) {
  // Show friendly error message
  setError("Sorry, I couldn't process that request. Please try again!");
}
```

### 5. Example UI Flow
```
User types: "I'm overweight and like black"
↓
[Loading spinner: "Finding perfect products..."]
↓
Agent Response: "I'd love to help you find comfortable..."
↓
[Product Grid: 6 product cards]
```

---

## Differences from `/search` Endpoint

| Feature | `/search` | `/ask` |
|---------|-----------|--------|
| **Input** | Structured query + filters | Natural language |
| **Response** | Products only | Conversational + Products |
| **AI Used** | Semantic search only | GPT-4o-mini + Semantic search |
| **Filters** | Explicit in request | Extracted from text |
| **Use Case** | Traditional search | Conversational shopping |
| **Guardrails** | None needed | Built-in safety |

---

## Testing the Endpoint

### Using cURL
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "I am overweight and like black clothes"}'
```

### Using Python
```python
import requests

response = requests.post(
    'http://localhost:8000/ask',
    json={'query': 'I am overweight and like black clothes'}
)
data = response.json()
print(data['response'])
for item in data['items']:
    print(f"- {item['title']}: Rs.{item['price']}")
```

### Interactive Docs
Visit http://localhost:8000/docs and test the `/ask` endpoint directly

---

## Configuration

### Environment Variables Required
```bash
OPENAI_API_KEY=your-openai-api-key-here
```

### Optional Configuration
- Model can be changed in `main.py` (default: `gpt-4o-mini`)
- Temperature can be adjusted (default: 0.7)
- Max products returned (default: 6)

---

## Performance

- **Typical Response Time:** 1-3 seconds
- **AI Processing:** ~500ms - 1.5s
- **Vector Search:** ~200-500ms
- **Total:** ~1-3 seconds

---

## Guardrails Summary

✅ **Appropriate:**
- "I'd love to help you find comfortable clothing"
- "Let me show you some great options"
- "Here are products that might suit you"

❌ **Inappropriate (Prevented):**
- "You should lose weight"
- "Try exercising"
- "Go on a diet"

The agent is **product-focused, supportive, and helpful** without crossing into personal advice.

---

## Support

For questions or issues:
- Check `/docs` for interactive testing
- Review system prompt in `main.py` to adjust guardrails
- Monitor OpenAI API usage for costs

---

**Ready to provide a conversational shopping experience! 🛍️💬**

