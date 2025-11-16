// Types
interface SearchPayload {
    query: string;
    previousSearches: string[];
    timestamp: string;
  }
  
  // Store search history for the current session
  let searchHistory: string[] = [];
  
  // Backend API endpoint
  const BACKEND_URL: string = 'http://localhost:8000';
  
  // Function to extract search query from Google URL
  function extractSearchQuery(url: string): string | null {
    try {
      const urlObj = new URL(url);
      
      // Check if it's a Google search
      if (!urlObj.hostname.includes('google.com')) {
        return null;
      }
      
      // Extract the 'q' parameter (search query)
      const query = urlObj.searchParams.get('q');
      return query;
    } catch (error) {
      console.error('Error parsing URL:', error);
      return null;
    }
  }
  
  // Function to send search data to backend
  async function sendSearchToBackend(query: string): Promise<void> {
    try {
      const payload: SearchPayload = {
        query: query,
        previousSearches: [...searchHistory], // Send copy of previous searches
        timestamp: new Date().toISOString()
      };
  
      const response = await fetch(BACKEND_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });
  
      if (response.ok) {
        console.log('Search sent successfully:', query);
      } else {
        console.error('Failed to send search:', response.status);
      }
    } catch (error) {
      console.error('Error sending search to backend:', error);
    }
  }
  
  // Listen for navigation events
  chrome.webNavigation.onCompleted.addListener((details: chrome.webNavigation.WebNavigationFramedCallbackDetails) => {
    // Only track main frame navigations (not iframes)
    if (details.frameId !== 0) {
      return;
    }
  
    const query = extractSearchQuery(details.url);
    
    if (query) {
      // Send to backend immediately
      sendSearchToBackend(query);
      
      // Add to search history (avoid duplicates of the same query in a row)
      if (searchHistory.length === 0 || searchHistory[searchHistory.length - 1] !== query) {
        searchHistory.push(query);
        
        // Optional: Limit history size to last 20 searches
        if (searchHistory.length > 20) {
          searchHistory.shift();
        }
      }
    }
  }, {
    url: [{ hostContains: 'google.com' }]
  });
  
  // Clear search history when browser session ends (optional)
  chrome.runtime.onSuspend.addListener(() => {
    searchHistory = [];
  });