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
  const [playingContent, setPlayingContent] = useState({}); // Track what's playing on each TV

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

  const handleLaunchService = async (content, serviceName, tv) => {
    try {
      setIsLoading(true);
      const response = await axios.post('/api/tv/launch', {
        tv_id: tv.id,
        content_id: content.id,
        title: content.title,
        service: serviceName
      });

      // Update the playing content for this TV
      setPlayingContent(prev => ({
        ...prev,
        [tv.id]: {
          title: content.title,
          poster: content.poster,
          service: serviceName
        }
      }));

      alert(`Launching ${serviceName} on ${tv.name}!`);
      setError(null);
    } catch (err) {
      console.error('Error launching content:', err);
      setError(`Failed to launch ${serviceName} on ${tv.name}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectTV = (tv) => {
    setSelectedTV(tv);
  };

  const handleLaunchApp = async (appName) => {
    if (!selectedTV) {
      alert('Please select a TV first');
      return;
    }

    try {
      setIsLoading(true);
      const response = await axios.post('/api/tv/launch', {
        tv_id: selectedTV.id,
        content_id: appName.toLowerCase(),
        service: appName
      });

      alert(`Launching ${appName} on ${selectedTV.name}!`);
      setError(null);
    } catch (err) {
      console.error('Error launching app:', err);
      setError(`Failed to launch ${appName} on TV`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetChannel = async (tv) => {
    // Map TV IDs to their antenna channels
    const channelMap = {
      'upper_left': 7,
      'lower_left': 8,
      'upper_right': 10,
      'lower_right': 11
    };

    const channel = channelMap[tv.id];
    if (!channel) {
      setError(`Channel not configured for ${tv.name}`);
      return;
    }

    try {
      setIsLoading(true);
      const response = await axios.post('/api/tv/reset-channel', {
        tv_id: tv.id,
        channel: channel
      });

      alert(`✅ Reset ${tv.name} to antenna channel ${channel}`);
      setError(null);
    } catch (err) {
      console.error('Error resetting channel:', err);
      setError(`Failed to reset channel on ${tv.name}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePowerAll = async (action) => {
    try {
      console.log(`[DEBUG] Power ${action} button clicked`);
      setIsLoading(true);
      console.log(`[DEBUG] Making API call to /api/tv/power-all with action: ${action}`);

      const response = await axios.post('/api/tv/power-all', {
        action: action  // 'on' or 'off'
      });

      console.log(`[DEBUG] API response:`, response.data);
      const devicesAffected = response.data.devices_affected;
      const actionText = action === 'on' ? 'powered on' : 'powered off';
      alert(`✅ All ${devicesAffected} Fire TVs ${actionText}`);
      setError(null);
    } catch (err) {
      console.error('Error with power command:', err);
      console.error('Error details:', err.response?.data || err.message);
      setError(`Failed to ${action === 'on' ? 'power on' : 'power off'} Fire TVs - Check console for details`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <h1>🎬 Dan's Basement TV Control Service</h1>
        <p className="subtitle">Control your entertainment system with style</p>
      </header>

      {error && <div className="error-message">{error}</div>}

      <div className="power-controls">
        <button
          onClick={() => handlePowerAll('on')}
          disabled={isLoading}
          className="power-on-btn"
          title="Power on all 4 Fire TVs"
        >
          🔌 Power On All
        </button>
        <button
          onClick={() => handlePowerAll('off')}
          disabled={isLoading}
          className="power-off-btn"
          title="Power off all 4 Fire TVs"
        >
          ⏹️ Power Off All
        </button>
      </div>

      {selectedTV && (
        <div className="app-launcher">
          <h3>📱 Launch Apps</h3>
          <div className="quick-launch-section">
            <div className="app-buttons-section">
              <label>Select an app to launch directly on {selectedTV.name}</label>
              <div className="app-buttons">
                <button onClick={() => handleLaunchApp('YouTubeTV')} disabled={isLoading}>🎬 YouTube TV</button>
                <button onClick={() => handleLaunchApp('Netflix')} disabled={isLoading}>🎥 Netflix</button>
                <button onClick={() => handleLaunchApp('ESPN')} disabled={isLoading}>⚽ ESPN</button>
                <button onClick={() => handleLaunchApp('Prime Video')} disabled={isLoading}>📦 Prime Video</button>
                <button onClick={() => handleLaunchApp('HBO Max')} disabled={isLoading}>🎭 HBO Max</button>
                <button onClick={() => handleLaunchApp('MLB')} disabled={isLoading}>⚾ MLB</button>
                <button onClick={() => handleLaunchApp('Disney+')} disabled={isLoading}>🏰 Disney+</button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="dashboard-layout">
        <div className="tv-section">
          {tvs.length > 0 ? (
            <TVLayout
              tvs={tvs}
              selectedTV={selectedTV}
              onSelectTV={handleSelectTV}
              playingContent={playingContent}
              onResetChannel={handleResetChannel}
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
              onLaunchService={handleLaunchService}
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
