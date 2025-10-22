# API Documentation - Product Search Service

## Overview

This API provides intelligent product search functionality powered by semantic search and vector similarity. It allows users to search for products using natural language queries with optional filters/constraints.

**Base URL:** `http://localhost:8000`  
**Protocol:** REST API  
**Data Format:** JSON  
**Framework:** FastAPI

---

## Quick Start

### Starting the API Server

```bash
cd /Users/bruno/Desktop/agent-ia-oracle
source .venv/bin/activate
cd demo/api
uvicorn main:app --port 8000 --reload
```

### Health Check

Once running, visit:
- **API Root:** http://localhost:8000
- **Interactive Docs:** http://localhost:8000/docs
- **OpenAPI Schema:** http://localhost:8000/openapi.json

---

## Endpoints

### POST /search

Search for products using natural language queries with optional filters.

**Endpoint:** `POST /search`

### POST /ask

🆕 **NEW!** Conversational shopping assistant that understands natural language and provides personalized recommendations.

**Endpoint:** `POST /ask`  
**See:** [Full Conversational Agent Documentation](./CONVERSATIONAL_AGENT_DOCS.md)

---

## POST /search Endpoint Details

#### Request Body

```json
{
  "query": "string",
  "constraints": {
    "category": "string | null",
    "price_min": "number | null",
    "price_max": "number | null",
    "color": "string | null",
    "size": "string | null",
    "brand": "string | null",
    "notes": "string | null"
  },
  "k": 8
}
```

#### Request Schema Details

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `query` | `string` | **Yes** | - | Natural language search query (e.g., "black hoodie for running") |
| `constraints` | `object` | No | `{}` | Filter criteria for products |
| `constraints.category` | `string` | No | `null` | Product category filter |
| `constraints.price_min` | `number` | No | `null` | Minimum price (>= 0) |
| `constraints.price_max` | `number` | No | `null` | Maximum price (>= 0) |
| `constraints.color` | `string` | No | `null` | Color filter |
| `constraints.size` | `string` | No | `null` | Size filter |
| `constraints.brand` | `string` | No | `null` | Brand filter |
| `constraints.notes` | `string` | No | `null` | Additional notes/context |
| `k` | `integer` | No | `8` | Number of results to return (min: 1, max: 50) |

#### Response Body

```json
{
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

#### Response Schema Details

| Field | Type | Description |
|-------|------|-------------|
| `items` | `array` | Array of product cards matching the search |
| `items[].product_id` | `string` | Unique product identifier |
| `items[].title` | `string` | Product title/name |
| `items[].brand` | `string \| null` | Brand name |
| `items[].category` | `string \| null` | Product category |
| `items[].price` | `number` | Product price |
| `items[].colors` | `array[string]` | Available colors |
| `items[].sizes` | `array[string]` | Available sizes |
| `items[].image_url` | `string \| null` | Product image URL |
| `items[].why` | `string \| null` | AI-generated explanation of why this product matches the query |

#### Response Codes

| Code | Description |
|------|-------------|
| `200` | Success - Returns matching products |
| `422` | Validation Error - Invalid request body |
| `500` | Internal Server Error |

---

## Example Requests

### Example 1: Simple Search

**Request:**
```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "comfortable running shoes"
  }'
```

**Response:**
```json
{
  "items": [
    {
      "product_id": "12345",
      "title": "Nike Air Zoom Pegasus",
      "brand": "Nike",
      "category": "Shoes",
      "price": 129.99,
      "colors": ["black", "white", "blue"],
      "sizes": ["8", "9", "10", "11"],
      "image_url": "https://example.com/nike-pegasus.jpg",
      "why": "Matches your style"
    }
  ]
}
```

### Example 2: Search with Price Filter

**Request:**
```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "black hoodie",
    "constraints": {
      "price_max": 50,
      "size": "M"
    },
    "k": 5
  }'
```

**Response:**
```json
{
  "items": [
    {
      "product_id": "67890",
      "title": "Classic Black Hoodie",
      "brand": "Urban Basics",
      "category": "Clothing",
      "price": 45.00,
      "colors": ["black"],
      "sizes": ["S", "M", "L", "XL"],
      "image_url": "https://example.com/black-hoodie.jpg",
      "why": "Available in black; Offered in size M; Within your budget ($50 max)"
    }
  ]
}
```

### Example 3: Search with Multiple Filters

**Request:**
```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "athletic wear for gym",
    "constraints": {
      "category": "Clothing",
      "brand": "Nike",
      "color": "black",
      "price_min": 20,
      "price_max": 100
    },
    "k": 10
  }'
```

### Example 4: JavaScript/Fetch

```javascript
async function searchProducts(query, constraints = {}, k = 8) {
  const response = await fetch('http://localhost:8000/search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query,
      constraints,
      k
    })
  });
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  
  const data = await response.json();
  return data.items;
}

// Usage
const products = await searchProducts(
  "blue running shoes",
  { price_max: 150, size: "10" },
  5
);
```

### Example 5: Python

```python
import requests

def search_products(query, constraints=None, k=8):
    url = "http://localhost:8000/search"
    payload = {
        "query": query,
        "constraints": constraints or {},
        "k": k
    }
    
    response = requests.post(url, json=payload)
    response.raise_for_status()
    
    return response.json()["items"]

# Usage
products = search_products(
    query="winter jacket",
    constraints={"color": "navy", "price_max": 200},
    k=5
)
```

---

## Data Models

### SearchRequest

```typescript
interface SearchRequest {
  query: string;                    // Required: search query
  constraints?: Constraints;        // Optional: filter criteria
  k?: number;                       // Optional: number of results (1-50)
}
```

### Constraints

```typescript
interface Constraints {
  category?: string | null;         // Filter by category
  price_min?: number | null;        // Minimum price (>= 0)
  price_max?: number | null;        // Maximum price (>= 0)
  color?: string | null;            // Filter by color
  size?: string | null;             // Filter by size
  brand?: string | null;            // Filter by brand
  notes?: string | null;            // Additional context
}
```

### ProductCard

```typescript
interface ProductCard {
  product_id: string;               // Unique product ID
  title: string;                    // Product name
  brand?: string | null;            // Brand name
  category?: string | null;         // Product category
  price: number;                    // Price
  colors: string[];                 // Available colors
  sizes: string[];                  // Available sizes
  image_url?: string | null;        // Product image URL
  why?: string | null;              // Why this matches the search
}
```

### SearchResponse

```typescript
interface SearchResponse {
  items: ProductCard[];             // Array of matching products
}
```

---

## Error Handling

### Validation Error (422)

When the request body doesn't match the expected schema:

```json
{
  "detail": [
    {
      "loc": ["body", "k"],
      "msg": "ensure this value is greater than or equal to 1",
      "type": "value_error.number.not_ge"
    }
  ]
}
```

### Error Response Example

```javascript
try {
  const response = await fetch('http://localhost:8000/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: 'shoes' })
  });
  
  if (!response.ok) {
    const error = await response.json();
    console.error('API Error:', error);
  }
  
  const data = await response.json();
  // Handle success
} catch (error) {
  console.error('Network Error:', error);
}
```

---

## Important Notes

### Search Behavior

1. **Semantic Search:** The API uses AI-powered semantic search, so queries can be natural language (e.g., "shoes for running in the rain")
2. **Auto-filtering:** All results automatically filter to only show products that are `in_stock: true`
3. **Ranking:** Results are ranked by semantic similarity to the query combined with the constraints
4. **Why Field:** Each product includes a `why` field explaining why it matches the search criteria

### Constraints Behavior

- All constraints are **optional** and work as **AND** filters (all must match)
- `price_min` and `price_max` can be used together or separately
- Colors and sizes are matched exactly (case-sensitive)
- An empty constraints object `{}` means no filtering (except in-stock)

### Performance

- Average response time: **< 500ms** for typical queries
- The API uses vector embeddings for fast similarity search
- Maximum results (`k`) is capped at 50

---

## CORS Configuration

**Note for Frontend Developers:** If you need to call this API from a browser-based frontend on a different port/domain, CORS needs to be enabled. Let your backend developer know which origins to whitelist.

Example origins that may need access:
- `http://localhost:3000` (React default)
- `http://localhost:5173` (Vite default)
- `http://localhost:8501` (Streamlit)

---

## Testing

### Using cURL

```bash
# Simple test
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test product"}'
```

### Using Postman

1. Create a new POST request
2. URL: `http://localhost:8000/search`
3. Headers: `Content-Type: application/json`
4. Body (raw JSON):
```json
{
  "query": "running shoes",
  "k": 5
}
```

### Using the Interactive Docs

Visit http://localhost:8000/docs for automatic interactive API documentation with a built-in testing interface.

---

## Support & Contact

For questions or issues with the API:
- Check the FastAPI automatic docs at `/docs`
- Review the logs in the terminal where the API is running
- Check that Qdrant is properly configured and running

---

## Version History

- **v1.0** - Initial release with `/search` endpoint

