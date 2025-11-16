import React, { useState,  } from 'react';
import { Search, X, ChevronDown, Loader2, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { KeyboardEvent, ChangeEvent } from 'react'

// 🔹 Tipos
interface ProductItem {
  product_id: string;
  title: string;
  price: number;
  brand?: string;
  category?: string;
  colors?: string[];
  sizes?: string[];
  image_url?: string;
  why?: string;
}

interface Filters {
  category: string;
  price_min: string;
  price_max: string;
  color: string;
  size: string;
  brand: string;
  notes: string;
}

interface AskModelSectionProps {
  setResults: React.Dispatch<React.SetStateAction<ProductItem[]>>;
  setLoading: React.Dispatch<React.SetStateAction<boolean>>;
}

// 🔹 Componente AI Assistant
function AskModelSection({ setResults }: AskModelSectionProps) {
  const [aiQuery, setAiQuery] = useState('');
  const [aiResponse, setAiResponse] = useState('');
  const [aiLoading, setAiLoading] = useState(false);

  const handleAskModel = async () => {
    if (!aiQuery.trim()) return;

    setAiLoading(true);
    setAiResponse('');

    try {
      const response = await fetch('http://localhost:8000/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: aiQuery }),
      });

      const data = await response.json();

      if (data.response) setAiResponse(data.response);

      if (data.items && Array.isArray(data.items)) {
        setResults(data.items);
      }
    } catch (error) {
      console.error('AI query error:', error);
      setAiResponse('Error connecting to AI assistant. Please try again.');
    } finally {
      setAiLoading(false);
    }
  };

  const handleKeyPress = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleAskModel();
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.3 }}
      className="mb-16 border border-black/10 p-8"
    >
      <div className="flex items-start gap-3 mb-6">
        <Sparkles size={20} className="text-gray-400 mt-1" />
        <div className="flex-1">
          <h3 className="text-lg font-light mb-1">AI Assistant</h3>
          <p className="text-sm text-gray-500">
            Ask for personalized recommendations in natural language
          </p>
        </div>
      </div>

      <div className="relative mb-4">
        <input
          type="text"
          value={aiQuery}
          onChange={(e) => setAiQuery(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="e.g., I need running shoes for rainy weather under $100..."
          className="w-full px-0 py-3 text-base border-b border-black/20 focus:outline-none focus:border-black transition-colors bg-transparent placeholder:text-gray-400"
        />
        <button
          onClick={handleAskModel}
          disabled={aiLoading}
          className="absolute right-0 top-2 px-5 py-1.5 bg-black text-white text-sm hover:bg-gray-800 disabled:opacity-50 transition-all"
        >
          {aiLoading ? <Loader2 className="animate-spin" size={16} /> : 'Ask'}
        </button>
      </div>

      <AnimatePresence>
        {aiResponse && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            transition={{ duration: 0.3 }}
            className="mt-6 p-4 bg-gray-50/50 border-l-2 border-black"
          >
            <p className="text-sm leading-relaxed text-gray-700">{aiResponse}</p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// 🔹 Componente principal
export default function ProductSearch() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<ProductItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<Filters>({
    category: '',
    price_min: '',
    price_max: '',
    color: '',
    size: '',
    brand: '',
    notes: '',
  });
  const [k, setK] = useState(8);

  const handleSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);
    try {
      const constraints: Record<string, string | number> = {};

     Object.keys(filters).forEach((key) => {
        const value = (filters as unknown as Record<string, string>)[key];
        if (value) {
            constraints[key] = key.includes('price') ? parseFloat(value) : value;
        }
        });

      const response = await fetch('http://localhost:8000/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          constraints: Object.keys(constraints).length > 0 ? constraints : undefined,
          k,
        }),
      });

      const data = await response.json();
      setResults(Array.isArray(data.items) ? data.items : []);
    } catch (error) {
      console.error('Search error:', error);
      alert('Error al buscar productos');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSearch();
  };

  const clearFilters = () => {
    setFilters({
      category: '',
      price_min: '',
      price_max: '',
      color: '',
      size: '',
      brand: '',
      notes: '',
    });
  };

  return (
    <div className="min-h-screen bg-white text-black">
      {/* Header */}
      <motion.header
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="border-b border-black/10"
      >
        <div className="max-w-6xl mx-auto px-6 py-12">
          <h1 className="text-4xl font-light tracking-tight">Product Search</h1>
        </div>
      </motion.header>

      <main className="max-w-6xl mx-auto px-6 py-16">

        {/* AI Assistant */}
        <AskModelSection setResults={setResults} setLoading={setLoading} />

        {/* Search Input */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mb-16"
        >
          <div className="relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Search for products..."
              className="w-full px-5 py-4 text-lg border border-black/20 focus:outline-none focus:border-black transition-colors placeholder:text-gray-400"
            />
            <button
              onClick={handleSearch}
              disabled={loading}
              className="absolute right-2 top-2 bottom-2 px-6 bg-black text-white hover:bg-gray-800 disabled:opacity-50 transition-all"
            >
              {loading ? <Loader2 className="animate-spin" size={20} /> : <Search size={20} />}
            </button>
          </div>

          {/* Filters */}
          <motion.button
            whileHover={{ x: 4 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setShowFilters(!showFilters)}
            className="mt-6 text-sm font-medium flex items-center gap-2 hover:text-gray-600 transition-colors"
          >
            Advanced filters
            <motion.div animate={{ rotate: showFilters ? 180 : 0 }} transition={{ duration: 0.3 }}>
              <ChevronDown size={16} />
            </motion.div>
          </motion.button>

          <AnimatePresence>
            {showFilters && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
                className="mt-8 overflow-hidden"
              >
                {(Object.keys(filters) as Array<keyof Filters>).map((key) => {
                    if (key === 'notes') return null;
                    return (
                        <div key={key}>
                        <label className="text-xs text-gray-500 mb-2 block capitalize">
                            {key.replace('_', ' ')}
                        </label>
                        <input
                            type={key.includes('price') ? 'number' : 'text'}
                            value={filters[key] ?? ''} // ✅ ya no necesita cast
                            onChange={(e: ChangeEvent<HTMLInputElement>) =>
                            setFilters({ ...filters, [key]: e.target.value })
                            }
                            className="w-full px-0 py-2 text-sm border-b border-black/20 focus:outline-none focus:border-black transition-colors bg-transparent"
                        />
                        </div>
                    );
                    })}


                <div className="mb-6">
                  <label className="text-xs text-gray-500 mb-2 block">Notes</label>
                  <input
                    type="text"
                    value={filters.notes}
                    onChange={(e) => setFilters({ ...filters, notes: e.target.value })}
                    className="w-full px-0 py-2 text-sm border-b border-black/20 focus:outline-none focus:border-black transition-colors bg-transparent"
                  />
                </div>

                <div className="flex items-center justify-between pt-4 border-t border-black/10">
                  <div className="flex items-center gap-3">
                    <label className="text-xs text-gray-500">Results</label>
                    <input
                      type="number"
                      min={1}
                      max={50}
                      value={k}
                      onChange={(e) => setK(parseInt(e.target.value) || 8)}
                      className="w-16 px-0 py-1 text-sm border-b border-black/20 focus:outline-none focus:border-black transition-colors bg-transparent text-center"
                    />
                  </div>

                  <button
                    onClick={clearFilters}
                    className="text-xs text-gray-500 hover:text-black transition-colors flex items-center gap-1"
                  >
                    <X size={12} /> Clear
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Results */}
        <AnimatePresence mode="wait">
          {results.length > 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.4 }}
            >
              <motion.h2
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-2xl font-light mb-8 pb-4 border-b border-black/10"
              >
                {results.length} {results.length === 1 ? 'result' : 'results'}
              </motion.h2>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
                {results.map((item, index) => (
                  <motion.div
                    key={item.product_id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: index * 0.05 }}
                    whileHover={{ y: -4 }}
                    className="group cursor-pointer"
                  >
                    {item.image_url ? (
                      <div className="aspect-square mb-4 overflow-hidden bg-gray-100">
                        <motion.img
                          whileHover={{ scale: 1.05 }}
                          transition={{ duration: 0.3 }}
                          src={item.image_url}
                          alt={item.title}
                          className="w-full h-full object-cover"
                        />
                      </div>
                    ) : (
                      <div className="aspect-square mb-4 bg-gray-100 flex items-center justify-center">
                        <span className="text-4xl font-light text-gray-300">?</span>
                      </div>
                    )}

                    <div>
                      <h3 className="font-medium text-base mb-1 line-clamp-2 group-hover:text-gray-600 transition-colors">
                        {item.title}
                      </h3>
                      {item.brand && <p className="text-sm text-gray-500 mb-2">{item.brand}</p>}
                      <p className="text-lg font-medium mb-3">${item.price.toFixed(2)}</p>
                      {item.category && (
                        <div className="inline-block px-2 py-0.5 border border-black/20 text-xs mb-3">
                          {item.category}
                        </div>
                      )}
                      {item.colors && item.colors.length > 0 && (
                        <div className="mb-2">
                          <p className="text-xs text-gray-500 mb-1">Available colors</p>
                          <div className="flex flex-wrap gap-1">
                            {item.colors.map((color, idx) => (
                              <span key={idx} className="px-2 py-0.5 bg-gray-100 text-xs">
                                {color}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {item.sizes && item.sizes.length > 0 && (
                        <div className="mb-2">
                          <p className="text-xs text-gray-500 mb-1">Available sizes</p>
                          <div className="flex flex-wrap gap-1">
                            {item.sizes.map((size, idx) => (
                              <span key={idx} className="px-2 py-0.5 bg-gray-100 text-xs">
                                {size}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {item.why && (
                        <p className="text-xs text-gray-600 mt-3 pt-3 border-t border-black/10">
                          {item.why}
                        </p>
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* No results */}
        <AnimatePresence>
          {!loading && results.length === 0 && query && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.3 }}
              className="text-center py-20 border border-black/10"
            >
              <motion.p
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="text-6xl font-light mb-4 text-gray-300"
              >
                0
              </motion.p>
              <motion.p
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="text-lg text-gray-500"
              >
                No results found
              </motion.p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Empty state */}
        <AnimatePresence>
          {!loading && results.length === 0 && !query && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              transition={{ duration: 0.5 }}
              className="text-center py-20"
            >
              <p className="text-2xl font-light text-gray-300">Start searching for products</p>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Footer */}
      <footer className="border-t border-black/10 mt-32">
        <div className="max-w-6xl mx-auto px-6 py-8">
          <p className="text-sm text-gray-500">© 2025 Product Search</p>
        </div>
      </footer>
    </div>
  );
}
