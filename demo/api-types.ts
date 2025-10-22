/**
 * TypeScript Type Definitions for Product Search API
 * 
 * Copy this file to your frontend project and import the types as needed.
 * 
 * Example usage:
 * import { SearchRequest, SearchResponse, ProductCard } from './api-types';
 */

// ============================================================================
// Request Types
// ============================================================================

/**
 * Optional constraints/filters for product search
 */
export interface Constraints {
  /** Filter by product category (e.g., "Shoes", "Clothing") */
  category?: string | null;
  
  /** Minimum price (must be >= 0) */
  price_min?: number | null;
  
  /** Maximum price (must be >= 0) */
  price_max?: number | null;
  
  /** Filter by color (e.g., "black", "blue") */
  color?: string | null;
  
  /** Filter by size (e.g., "M", "10", "Large") */
  size?: string | null;
  
  /** Filter by brand name */
  brand?: string | null;
  
  /** Additional notes or context (not currently used in filtering) */
  notes?: string | null;
}

/**
 * Product search request
 */
export interface SearchRequest {
  /** Natural language search query (e.g., "black running shoes") */
  query: string;
  
  /** Optional filter constraints */
  constraints?: Constraints;
  
  /** Number of results to return (min: 1, max: 50, default: 8) */
  k?: number;
}

// ============================================================================
// Response Types
// ============================================================================

/**
 * Individual product result
 */
export interface ProductCard {
  /** Unique product identifier */
  product_id: string;
  
  /** Product title/name */
  title: string;
  
  /** Brand name */
  brand?: string | null;
  
  /** Product category */
  category?: string | null;
  
  /** Product price */
  price: number;
  
  /** Available colors */
  colors: string[];
  
  /** Available sizes */
  sizes: string[];
  
  /** Product image URL */
  image_url?: string | null;
  
  /** AI-generated explanation of why this product matches the search */
  why?: string | null;
}

/**
 * Product search response
 */
export interface SearchResponse {
  /** Array of matching products */
  items: ProductCard[];
}

// ============================================================================
// API Error Types
// ============================================================================

/**
 * Validation error detail (422 response)
 */
export interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

/**
 * API error response
 */
export interface APIError {
  detail: ValidationError[] | string;
}

// ============================================================================
// API Client Configuration
// ============================================================================

/**
 * Configuration for the API client
 */
export interface APIConfig {
  /** Base URL of the API (default: http://localhost:8000) */
  baseURL?: string;
  
  /** Request timeout in milliseconds (default: 30000) */
  timeout?: number;
}

// ============================================================================
// Utility Types
// ============================================================================

/**
 * Price range for filtering
 */
export interface PriceRange {
  min?: number;
  max?: number;
}

/**
 * Available filter options (for building UI)
 */
export interface FilterOptions {
  categories: string[];
  brands: string[];
  colors: string[];
  sizes: string[];
  priceRange: PriceRange;
}

// ============================================================================
// API Client Example
// ============================================================================

/**
 * Example API client class
 * 
 * Usage:
 * ```typescript
 * const api = new ProductSearchAPI();
 * const results = await api.search("black hoodie", { price_max: 50 });
 * ```
 */
export class ProductSearchAPI {
  private baseURL: string;
  private timeout: number;

  constructor(config: APIConfig = {}) {
    this.baseURL = config.baseURL || 'http://localhost:8000';
    this.timeout = config.timeout || 30000;
  }

  /**
   * Search for products
   */
  async search(
    query: string,
    constraints?: Constraints,
    k: number = 8
  ): Promise<ProductCard[]> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(`${this.baseURL}/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query,
          constraints: constraints || {},
          k,
        } as SearchRequest),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const error: APIError = await response.json();
        throw new Error(
          typeof error.detail === 'string'
            ? error.detail
            : 'Search request failed'
        );
      }

      const data: SearchResponse = await response.json();
      return data.items;
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error('Request timeout');
      }
      throw error;
    }
  }
}

// ============================================================================
// React Hook Example
// ============================================================================

/**
 * Example React hook for product search (copy to your React project)
 * 
 * Usage:
 * ```typescript
 * function SearchPage() {
 *   const { products, loading, error, search } = useProductSearch();
 *   
 *   const handleSearch = () => {
 *     search("black hoodie", { price_max: 50 });
 *   };
 *   
 *   return (
 *     <div>
 *       {loading && <div>Loading...</div>}
 *       {error && <div>Error: {error}</div>}
 *       {products.map(p => <ProductCard key={p.product_id} product={p} />)}
 *     </div>
 *   );
 * }
 * ```
 */
export interface UseProductSearchReturn {
  products: ProductCard[];
  loading: boolean;
  error: string | null;
  search: (query: string, constraints?: Constraints, k?: number) => Promise<void>;
  clear: () => void;
}

// Note: This is just a type definition. For the actual React hook implementation,
// use the following template in your React project:
/*
import { useState, useCallback } from 'react';
import { ProductCard, Constraints, ProductSearchAPI } from './api-types';

const api = new ProductSearchAPI();

export function useProductSearch(): UseProductSearchReturn {
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
      const results = await api.search(query, constraints, k);
      setProducts(results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
      setProducts([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const clear = useCallback(() => {
    setProducts([]);
    setError(null);
  }, []);

  return { products, loading, error, search, clear };
}
*/

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Format price for display
 */
export function formatPrice(price: number): string {
  return `$${price.toFixed(2)}`;
}

/**
 * Format colors list for display
 */
export function formatColors(colors: string[]): string {
  if (colors.length === 0) return 'N/A';
  if (colors.length <= 3) return colors.join(', ');
  return `${colors.slice(0, 3).join(', ')} +${colors.length - 3}`;
}

/**
 * Format sizes list for display
 */
export function formatSizes(sizes: string[]): string {
  if (sizes.length === 0) return 'N/A';
  return sizes.join(', ');
}

/**
 * Check if product matches a specific filter
 */
export function matchesFilter(
  product: ProductCard,
  constraints: Constraints
): boolean {
  if (constraints.category && product.category !== constraints.category) {
    return false;
  }
  
  if (constraints.brand && product.brand !== constraints.brand) {
    return false;
  }
  
  if (constraints.color && !product.colors.includes(constraints.color)) {
    return false;
  }
  
  if (constraints.size && !product.sizes.includes(constraints.size)) {
    return false;
  }
  
  if (constraints.price_min && product.price < constraints.price_min) {
    return false;
  }
  
  if (constraints.price_max && product.price > constraints.price_max) {
    return false;
  }
  
  return true;
}

