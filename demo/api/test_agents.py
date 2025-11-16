"""
Test script for LangGraph Multi-Agent System
Simulates Chrome extension requests and validates agent workflows
"""

import json
import requests
from typing import List, Dict

API_BASE_URL = "http://localhost:8000"

# Test scenarios
TEST_CASES = [
    {
        "name": "OFF-TOPIC: Auto Parts (Should be rejected)",
        "query": "new tires toyota tacoma",
        "previousSearches": ["car maintenance", "oil change near me"],
        "timestamp": "2025-11-05T15:00:00.000Z",
        "expected_intent": "off_topic",
        "expected_products": 0,
        "expected_notification": False
    },
    {
        "name": "OFF-TOPIC: Restaurant Search (Should be rejected)",
        "query": "best pizza near me",
        "previousSearches": ["italian restaurants"],
        "timestamp": "2025-11-05T15:05:00.000Z",
        "expected_intent": "off_topic",
        "expected_products": 0,
        "expected_notification": False
    },
    {
        "name": "DIRECT SEARCH: Black Shirt",
        "query": "black shirt",
        "previousSearches": [],
        "timestamp": "2025-11-05T15:10:00.000Z",
        "expected_intent": "direct_product_search",
        "expected_products": ">0",
        "expected_notification": True
    },
    {
        "name": "DIRECT SEARCH: Laptop Under Budget",
        "query": "laptop under 2000",
        "previousSearches": [],
        "timestamp": "2025-11-05T15:15:00.000Z",
        "expected_intent": "direct_product_search",
        "expected_products": ">=0",
        "expected_notification": "if_products_found"
    },
    {
        "name": "DIRECT SEARCH: Women's Shoes",
        "query": "women shoes",
        "previousSearches": [],
        "timestamp": "2025-11-05T15:20:00.000Z",
        "expected_intent": "direct_product_search",
        "expected_products": ">0",
        "expected_notification": True
    },
    {
        "name": "CONTEXTUAL: Rainy Vacation Pattern",
        "query": "vacation in seattle november",
        "previousSearches": [
            "is it going to rain in november",
            "seattle weather forecast",
            "things to do in seattle"
        ],
        "timestamp": "2025-11-05T15:25:00.000Z",
        "expected_intent": "contextual_use_case",
        "expected_products": ">0",
        "expected_notification": True,
        "description": "Should recognize need for rain gear (jackets, boots)"
    },
    {
        "name": "CONTEXTUAL: Wedding Event",
        "query": "wedding next month",
        "previousSearches": [
            "formal dress code",
            "what to wear to a wedding"
        ],
        "timestamp": "2025-11-05T15:30:00.000Z",
        "expected_intent": "contextual_use_case",
        "expected_products": ">0",
        "expected_notification": True,
        "description": "Should recommend formal wear"
    },
    {
        "name": "CONTEXTUAL: Beach Vacation",
        "query": "beach vacation florida",
        "previousSearches": [
            "best beaches in florida",
            "summer vacation ideas"
        ],
        "timestamp": "2025-11-05T15:35:00.000Z",
        "expected_intent": "contextual_use_case",
        "expected_products": ">0",
        "expected_notification": True,
        "description": "Should recommend beachwear, sunglasses, sandals"
    },
    {
        "name": "CONTEXTUAL: Gym/Fitness",
        "query": "started going to gym",
        "previousSearches": [
            "gym near me",
            "workout routines for beginners"
        ],
        "timestamp": "2025-11-05T15:40:00.000Z",
        "expected_intent": "contextual_use_case",
        "expected_products": ">0",
        "expected_notification": True,
        "description": "Should recommend activewear, sports shoes"
    },
    {
        "name": "CONTEXTUAL: Gift Shopping",
        "query": "gift for my dad who loves tech",
        "previousSearches": [
            "birthday gift ideas",
            "tech gifts for men"
        ],
        "timestamp": "2025-11-05T15:45:00.000Z",
        "expected_intent": "contextual_use_case",
        "expected_products": ">=0",
        "expected_notification": "if_products_found",
        "description": "Should recommend electronics/gadgets"
    }
]


def run_test(test_case: Dict) -> Dict:
    """Run a single test case"""
    print(f"\n{'='*70}")
    print(f"TEST: {test_case['name']}")
    print(f"{'='*70}")
    
    if test_case.get('description'):
        print(f"📝 {test_case['description']}")
    
    print(f"Query: \"{test_case['query']}\"")
    if test_case['previousSearches']:
        print(f"Previous searches:")
        for i, search in enumerate(test_case['previousSearches'], 1):
            print(f"  {i}. {search}")
    else:
        print(f"Previous searches: None")
    
    # Make request
    try:
        response = requests.post(
            f"{API_BASE_URL}/chrome-extension",
            json={
                "query": test_case['query'],
                "previousSearches": test_case['previousSearches'],
                "timestamp": test_case['timestamp']
            },
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ ERROR: Status {response.status_code}")
            print(f"   {response.text}")
            return {"success": False, "error": response.text}
        
        result = response.json()
        
        # Display results
        print(f"\n📊 RESULTS:")
        print(f"   Response: {result.get('response', 'N/A')}")
        print(f"   Products found: {len(result.get('items', []))}")
        
        if result.get('items'):
            print(f"\n   Top products:")
            for i, item in enumerate(result['items'][:3], 1):
                print(f"   {i}. {item['title']} - ${item['price']}")
                if item.get('why'):
                    print(f"      Why: {item['why']}")
        
        # Validate expectations
        num_products = len(result.get('items', []))
        expected_products = test_case['expected_products']
        
        if expected_products == 0:
            success = num_products == 0
        elif expected_products == ">0":
            success = num_products > 0
        elif expected_products == ">=0":
            success = num_products >= 0
        elif isinstance(expected_products, int):
            success = num_products == expected_products
        else:
            success = True
        
        if success:
            print(f"\n✅ TEST PASSED")
        else:
            print(f"\n⚠️  TEST WARNING: Expected {expected_products} products, got {num_products}")
        
        return {
            "success": success,
            "products_found": num_products,
            "response": result.get('response'),
            "items": result.get('items', [])
        }
        
    except requests.exceptions.Timeout:
        print(f"❌ ERROR: Request timeout")
        return {"success": False, "error": "timeout"}
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return {"success": False, "error": str(e)}


def main():
    """Run all tests"""
    print(f"\n{'#'*70}")
    print(f"# LANGGRAPH MULTI-AGENT SYSTEM - TEST SUITE")
    print(f"{'#'*70}")
    print(f"\nTesting endpoint: {API_BASE_URL}/chrome-extension")
    
    # Check server health
    try:
        health = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if health.status_code == 200:
            print(f"✅ Server is healthy\n")
        else:
            print(f"⚠️  Server responded with status {health.status_code}\n")
    except:
        print(f"❌ ERROR: Cannot connect to server at {API_BASE_URL}")
        print(f"   Make sure the server is running: uvicorn main:app --reload")
        return
    
    # Run tests
    results = []
    for test_case in TEST_CASES:
        result = run_test(test_case)
        results.append({
            "name": test_case['name'],
            "success": result.get('success', False),
            "products": result.get('products_found', 0)
        })
    
    # Summary
    print(f"\n{'='*70}")
    print(f"TEST SUMMARY")
    print(f"{'='*70}")
    
    total = len(results)
    passed = sum(1 for r in results if r['success'])
    
    for result in results:
        status = "✅ PASS" if result['success'] else "⚠️  WARN"
        print(f"{status} - {result['name']} ({result['products']} products)")
    
    print(f"\n{'='*70}")
    print(f"Results: {passed}/{total} tests passed")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()


