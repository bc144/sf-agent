# API Quick Reference

## 🚀 Start the API

```bash
cd /Users/bruno/Desktop/agent-ia-oracle
source .venv/bin/activate
cd demo/api
uvicorn main:app --port 8000 --reload
```

**Base URL:** `http://localhost:8000`  
**Docs:** http://localhost:8000/docs

---

## 📍 Endpoint

### `POST /search` - Search for products

**URL:** `http://localhost:8000/search`

---

## 📤 Request Format

```json
{
  "query": "black running shoes",
  "constraints": {
    "category": "Shoes",
    "price_max": 150,
    "color": "black",
    "size": "10",
    "brand": "Nike"
  },
  "k": 8
}
```

### Request Fields

| Field | Required | Type | Default | Notes |
|-------|----------|------|---------|-------|
| `query` | ✅ Yes | string | - | Natural language search |
| `constraints` | ❌ No | object | `{}` | Filters (all optional) |
| `constraints.category` | ❌ No | string | null | |
| `constraints.price_min` | ❌ No | number | null | Min: 0 |
| `constraints.price_max` | ❌ No | number | null | Min: 0 |
| `constraints.color` | ❌ No | string | null | |
| `constraints.size` | ❌ No | string | null | |
| `constraints.brand` | ❌ No | string | null | |
| `k` | ❌ No | integer | 8 | Min: 1, Max: 50 |

---

## 📥 Response Format

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
      "image_url": "https://...",
      "why": "Available in black; Offered in size 10; Within your budget ($150 max)"
    }
  ]
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `items` | array | Product cards |
| `items[].product_id` | string | Unique ID |
| `items[].title` | string | Product name |
| `items[].brand` | string\|null | Brand |
| `items[].category` | string\|null | Category |
| `items[].price` | number | Price |
| `items[].colors` | string[] | Colors available |
| `items[].sizes` | string[] | Sizes available |
| `items[].image_url` | string\|null | Image URL |
| `items[].why` | string\|null | Match explanation |

---

## 💻 Code Examples

### JavaScript/React

```javascript
const searchProducts = async (query, filters = {}) => {
  const response = await fetch('http://localhost:8000/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      constraints: filters,
      k: 8
    })
  });
  
  const data = await response.json();
  return data.items;
};

// Usage
const products = await searchProducts(
  "blue jeans",
  { size: "32", price_max: 100 }
);
```

### Python

```python
import requests

response = requests.post(
    'http://localhost:8000/search',
    json={
        'query': 'blue jeans',
        'constraints': {'size': '32', 'price_max': 100},
        'k': 8
    }
)
products = response.json()['items']
```

### cURL

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "blue jeans",
    "constraints": {"size": "32", "price_max": 100},
    "k": 8
  }'
```

---

## ⚡ Quick Tips

1. **Natural Language Queries**: Use conversational queries like "comfortable shoes for running"
2. **Auto In-Stock Filter**: All results are automatically filtered to in-stock items
3. **Semantic Search**: The AI understands context - "affordable jacket" will match budget-friendly items
4. **Why Field**: Use the `why` field to show users why products match their search
5. **Empty Results**: If no results, suggest relaxing filters (price, color, size)

---

## 🎨 UI/UX Recommendations

### Search Bar
- Show loading state while searching
- Add debounce (300ms) for better performance
- Allow users to clear search easily

### Filters Panel
- Display available filters: Category, Brand, Color, Size, Price Range
- Show active filters with remove option
- Consider a "Clear All" button

### Results Display
- Show product cards in a responsive grid
- Display the `why` field prominently to build trust
- Show price, available colors/sizes clearly
- Add "No results" state with suggestions

### Product Card Template
```
┌─────────────────────┐
│    [Image]          │
│                     │
├─────────────────────┤
│ Title               │
│ Brand • Category    │
│ $129.99             │
│ Colors: ● ● ●       │
│ Sizes: 8 9 10 11    │
│                     │
│ 💡 Why: Matches...  │
└─────────────────────┘
```

---

## 🚨 Error Handling

### Response Codes
- `200` - Success
- `422` - Invalid request (check request format)
- `500` - Server error

### Example Error Handler
```javascript
try {
  const response = await fetch(url, options);
  
  if (!response.ok) {
    if (response.status === 422) {
      throw new Error('Invalid search parameters');
    }
    throw new Error('Search failed. Please try again.');
  }
  
  const data = await response.json();
  return data.items;
} catch (error) {
  console.error('Search error:', error);
  // Show user-friendly error message
}
```

---

## 🔐 CORS

CORS is **enabled** for all origins in development.  
The frontend can call the API from any localhost port.

---

## 📊 Response Times

- **Typical:** < 500ms
- **First request:** ~2-3s (model loading)
- **Max results:** 50 items per request

---

## 🎯 Common Use Cases

### Basic Search
```json
{ "query": "running shoes" }
```

### Price Filter
```json
{
  "query": "laptop",
  "constraints": { "price_max": 1000 }
}
```

### Multiple Filters
```json
{
  "query": "hoodie",
  "constraints": {
    "color": "black",
    "size": "M",
    "price_min": 20,
    "price_max": 60
  }
}
```

### More Results
```json
{
  "query": "sneakers",
  "k": 20
}
```

---

## 📱 Frontend Checklist

- [ ] Implement search input with debounce
- [ ] Add loading states
- [ ] Display product cards with all fields
- [ ] Show the "why" explanation
- [ ] Implement filter UI (category, price, color, size, brand)
- [ ] Add error handling
- [ ] Show empty state when no results
- [ ] Make layout responsive (mobile, tablet, desktop)
- [ ] Add "Clear filters" functionality
- [ ] Test with various queries

---

## 🆘 Troubleshooting

**API not responding?**
- Check if the API is running: `curl http://localhost:8000/docs`
- Restart: `uvicorn main:app --port 8000 --reload`

**CORS errors?**
- CORS is enabled for all origins in development
- Check browser console for specific errors

**No results returned?**
- Try a simpler query without filters
- Check that products are ingested: visit `/docs` and try the API directly

---

For full documentation, see [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)

