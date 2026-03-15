import React, { useState, useEffect } from 'react';
import axios from 'axios';
import TVLayout from '../components/TVLayout';
import SearchBar from '../components/SearchBar';
import ResultsList from '../components/ResultsList';
import '../styles/Dashboard.css';

const Dashboard = () => {
  const [tvs, setTVs] = useState([]);
  const [selectedTV, setSelectedTV] = useState(null);
  const [searchResults, setSearchResults] = useState([]);
  const [searchMetadata, setSearchMetadata] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastSearchQuery, setLastSearchQuery] = useState('');

  // Fetch available TVs on component mount
  useEffect(() => {
    fetchTVs();
  }, []);

  const fetchTVs = async () => {
    try {
      setIsLoading(true);
      const response = await axios.get('/api/tvs');
      setTVs(response.data.tvs);
      setError(null);
    } catch (err) {
      console.error('Error fetching TVs:', err);
      setError('Failed to load TV configuration');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = async (query, contentType) => {
    setLastSearchQuery(query);
    try {
      setIsLoading(true);
      setError(null);

      const params = new URLSearchParams({
        query: query,
        ...(contentType !== 'all' && { content_type: contentType })
      });

      const response = await axios.get(`/api/search/all?${params}`);
      setSearchResults(response.data.results);

      // Store metadata for display
      setSearchMetadata({
        searchTime: response.data.search_time_ms,
        serviceBreakdown: response.data.service_breakdown,
        total: response.data.total,
        timestamp: response.data.timestamp
      });

      if (response.data.results.length === 0) {
        setError(`No results found for "${query}"`);
      }
    } catch (err) {
      console.error('Error searching:', err);
      setError('Failed to search for content');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLaunchContent = async (content, tv) => {
    try {
      setIsLoading(true);
      const response = await axios.post('/api/tv/launch', {
        tv_id: tv.id,
        content_id: content.id,
        service: content.available_services[0] // Use first available service
      });

      alert(`Launching "${content.title}" on ${tv.name}!`);
      setError(null);
    } catch (err) {
      console.error('Error launching content:', err);
      setError('Failed to launch content on TV');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectTV = (tv) => {
    setSelectedTV(tv);
  };

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <h1>🎬 Dan's Basement TV Control Service</h1>
        <p className="subtitle">Control your entertainment system with style</p>
      </header>

      {error && <div className="error-message">{error}</div>}

      <div className="dashboard-layout">
        <div className="tv-section">
          {tvs.length > 0 ? (
            <TVLayout
              tvs={tvs}
              selectedTV={selectedTV}
              onSelectTV={handleSelectTV}
            />
          ) : (
            <div className="loading">Loading TV configuration...</div>
          )}
        </div>

        <div className="search-section">
          <SearchBar onSearch={handleSearch} isLoading={isLoading} />

          {searchResults.length > 0 || lastSearchQuery ? (
            <ResultsList
              results={searchResults}
              selectedTV={selectedTV}
              onLaunchContent={handleLaunchContent}
              isLoading={isLoading}
              metadata={searchMetadata}
            />
          ) : (
            <div className="no-search">
              <p>📺 Select a TV above and search for your favorite shows, movies, or sports!</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
