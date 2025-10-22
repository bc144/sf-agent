# Frontend Developer Handoff 🚀

## 📦 What's Included

Your backend API is ready! Here's everything you need to build the frontend:

### Documentation Files

1. **`API_DOCUMENTATION.md`** - Complete API reference with all details
2. **`API_QUICK_REFERENCE.md`** - Quick lookup guide (start here!)
3. **`api-types.ts`** - TypeScript types and React hooks
4. **`api-test.html`** - Interactive test page (open in browser)

### API Endpoint

- **Base URL:** `http://localhost:8000`
- **Endpoint:** `POST /search`
- **Status:** ✅ CORS enabled for all origins
- **Docs:** http://localhost:8000/docs (interactive)

---

## 🚀 Quick Start (5 minutes)

### Step 1: Start the API

```bash
cd /Users/bruno/Desktop/agent-ia-oracle
source .venv/bin/activate
cd demo/api
uvicorn main:app --port 8000 --reload
```

### Step 2: Test the API

Open `api-test.html` in your browser to verify the API works.

### Step 3: Build Your Frontend

Use the TypeScript types in `api-types.ts` for type safety.

---

## 📱 What to Build

### Core Features

1. **Search Bar**
   - Natural language input
   - Debounce (300ms recommended)
   - Loading state while searching

2. **Filters Panel**
   - Category dropdown/select
   - Brand input/select
   - Color selector
   - Size selector
   - Price range (min/max)
   - "Clear all filters" button

3. **Results Grid**
   - Responsive product cards
   - Show: image, title, brand, price, colors, sizes
   - Display the AI-generated "why" explanation
   - Empty state when no results

4. **Product Card**
   - Display product image (or fallback icon)
   - Title and brand
   - Price (formatted)
   - Available colors and sizes
   - "Why this matches" explanation

---

## 💻 Code Examples

### Basic Fetch Request

```javascript
async function searchProducts(query, filters = {}) {
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
}

// Usage
const products = await searchProducts("running shoes", {
  price_max: 150,
  size: "10"
});
```

### React Hook (TypeScript)

Copy this to your React project:

```typescript
import { useState, useCallback } from 'react';
import { ProductCard, Constraints } from './api-types';

export function useProductSearch() {
  const [products, setProducts] = useState<ProductCard[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = useCallback(async (
    query: string,
    constraints?: Constraints,
    k: number = 8
  ) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('http://localhost:8000/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, constraints: constraints || {}, k })
      });
      
      if (!response.ok) throw new Error('Search failed');
      
      const data = await response.json();
      setProducts(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
      setProducts([]);
    } finally {
      setLoading(false);
    }
  }, []);

  return { products, loading, error, search };
}
```

---

## 🎨 UI/UX Recommendations

### Layout Suggestion

```
┌─────────────────────────────────────────────┐
│  🔍 [Search bar.....................] [🔍]  │
├─────────────────────────────────────────────┤
│ Filters: [Category▾] [Brand▾] [Color] [$]  │
├─────────────────────────────────────────────┤
│  ┌────────┐ ┌────────┐ ┌────────┐          │
│  │ [IMG]  │ │ [IMG]  │ │ [IMG]  │          │
│  │ Title  │ │ Title  │ │ Title  │          │
│  │ $99.99 │ │ $79.99 │ │ $129   │          │
│  │ Colors │ │ Colors │ │ Colors │          │
│  │ 💡Why  │ │ 💡Why  │ │ 💡Why  │          │
│  └────────┘ └────────┘ └────────┘          │
└─────────────────────────────────────────────┘
```

### Design Tips

1. **Emphasize the "Why" field** - This is a key differentiator showing AI-powered matching
2. **Make filters discoverable** - Use dropdowns or tags for common options
3. **Show active filters** - Display chips/tags for active filters with remove option
4. **Loading states** - Show skeleton screens or spinners during search
5. **Empty states** - Suggest "try relaxing your filters" when no results
6. **Mobile-first** - Ensure responsive design (filters collapse on mobile)

### Color Palette Suggestions

- **Primary:** #667eea (purple-blue)
- **Secondary:** #764ba2 (purple)
- **Success:** #28a745 (green)
- **Text:** #333 / #666
- **Background:** #f8f9fa

---

## ✅ Frontend Checklist

### Must Have
- [ ] Search input with submit button
- [ ] Display product cards (title, price, image)
- [ ] Show loading state
- [ ] Show error messages
- [ ] Display empty state

### Should Have
- [ ] Price range filter (min/max)
- [ ] Category filter
- [ ] Color filter
- [ ] Size filter
- [ ] Brand filter
- [ ] "Clear filters" button
- [ ] Number of results returned display
- [ ] Display the "why" explanation on each card

### Nice to Have
- [ ] Search debouncing
- [ ] Filter suggestions (show available options)
- [ ] Sort results (price, relevance)
- [ ] Save recent searches
- [ ] Product detail modal/page
- [ ] Add to cart functionality
- [ ] Responsive design (mobile, tablet, desktop)
- [ ] Dark mode

---

## 🔧 Technical Details

### Request Format

```json
POST /search
{
  "query": "black running shoes",
  "constraints": {
    "price_max": 150,
    "size": "10",
    "color": "black"
  },
  "k": 8
}
```

### Response Format

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

---

## 🐛 Troubleshooting

### API Not Responding?

```bash
# Check if API is running
curl http://localhost:8000/docs

# If not, start it
cd /Users/bruno/Desktop/agent-ia-oracle/demo/api
source ../../.venv/bin/activate
uvicorn main:app --port 8000 --reload
```

### CORS Errors?

CORS is already enabled for all origins. If you still see errors:
- Check that the API URL is exactly `http://localhost:8000`
- Verify the API is running
- Check browser console for specific error messages

### No Results Returned?

- Test with simple query: `"shoes"`
- Remove all filters
- Check that products are ingested in Qdrant
- Verify response in `/docs` endpoint

### TypeScript Errors?

Copy `api-types.ts` to your project and import types:
```typescript
import { ProductCard, SearchRequest, Constraints } from './api-types';
```

---

## 📚 Resources

1. **Interactive API Docs:** http://localhost:8000/docs
2. **Test Page:** Open `api-test.html` in browser
3. **Full Documentation:** `API_DOCUMENTATION.md`
4. **Quick Reference:** `API_QUICK_REFERENCE.md`
5. **TypeScript Types:** `api-types.ts`

---

## 🎯 Example User Flows

### Flow 1: Simple Search
1. User types "running shoes"
2. Clicks search
3. Sees grid of relevant shoes
4. Each card shows why it matches

### Flow 2: Filtered Search
1. User types "hoodie"
2. Sets filters: color=black, price_max=50, size=M
3. Clicks search
4. Sees black hoodies under $50 in size M
5. "Why" field explains: "Available in black; Offered in size M; Within your budget"

### Flow 3: No Results
1. User types "laptop"
2. Sets filters: price_max=100
3. Clicks search
4. No results found
5. Show message: "No products found. Try increasing your budget or removing some filters"

---

## 📞 Support

If you have questions about:
- **API behavior**: Check `API_DOCUMENTATION.md`
- **Request/response format**: Check `API_QUICK_REFERENCE.md`
- **TypeScript types**: Check `api-types.ts`
- **Live testing**: Open `api-test.html` or visit http://localhost:8000/docs

---

## 🚢 Ready to Ship!

Your backend is fully configured with:
- ✅ CORS enabled for cross-origin requests
- ✅ Semantic AI-powered search
- ✅ Flexible filtering system
- ✅ Type-safe TypeScript definitions
- ✅ Interactive documentation
- ✅ Test interface

**Happy coding! 🎉**

