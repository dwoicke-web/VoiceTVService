import React, { useState } from 'react';
import '../styles/ResultsList.css';

const ResultsList = ({ results, selectedTV, onLaunchService, isLoading, metadata }) => {
  const [serviceFilter, setServiceFilter] = useState(null);

  if (isLoading) {
    return <div className="results-loading">Loading results...</div>;
  }

  if (!results || results.length === 0) {
    return <div className="results-empty">No results found. Try searching for a show, movie, or sports event.</div>;
  }

  const handleServiceClick = (result, serviceName) => {
    if (!selectedTV) {
      alert('Please select a TV first');
      return;
    }
    onLaunchService(result, serviceName, selectedTV);
  };

  const toggleFilter = (service) => {
    setServiceFilter(prev => prev === service ? null : service);
  };

  // Filter results by selected service
  const filteredResults = serviceFilter
    ? results.filter(r => r.available_services && r.available_services.includes(serviceFilter))
    : results;

  return (
    <div className="results-container">
      <div className="results-header">
        <h2>Search Results ({filteredResults.length}{serviceFilter ? ` of ${results.length}` : ''})</h2>
        {metadata && (
          <div className="search-metadata">
            <span className="metadata-item">⚡ {metadata.searchTime}ms</span>
            <span className="metadata-separator">•</span>
            <span className="metadata-item">From {metadata.serviceBreakdown ? Object.keys(metadata.serviceBreakdown).length : 0} services</span>
          </div>
        )}
      </div>

      {metadata && metadata.serviceBreakdown && (
        <div className="service-breakdown">
          <details open={!!serviceFilter}>
            <summary>Filter by Service</summary>
            <div className="breakdown-grid">
              {Object.entries(metadata.serviceBreakdown).map(([service, count]) => (
                <button
                  key={service}
                  className={`breakdown-item ${serviceFilter === service ? 'active' : ''}`}
                  onClick={() => toggleFilter(service)}
                  title={serviceFilter === service ? 'Clear filter' : `Show only ${service} results`}
                >
                  <span className="service-name">{service}</span>
                  <span className="result-count">{count}</span>
                </button>
              ))}
            </div>
          </details>
        </div>
      )}

      {serviceFilter && (
        <div className="active-filter">
          <span>Showing: <strong>{serviceFilter}</strong></span>
          <button className="clear-filter" onClick={() => setServiceFilter(null)}>✕ Clear</button>
        </div>
      )}

      {!selectedTV && (
        <div className="tv-select-reminder">
          ⬆️ Select a TV above, then click a streaming service below to launch it
        </div>
      )}

      <div className="results-grid">
        {filteredResults.map((result) => (
          <div key={result.id} className="result-card">
            <div className="result-poster">
              <img src={result.poster} alt={result.title} />
            </div>

            <div className="result-info">
              <h3 className="result-title">{result.title}</h3>
              <p className="result-type">{result.type.toUpperCase()}</p>
              <p className="result-description">{result.description}</p>

              <div className="result-services">
                <span className="services-label">
                  {selectedTV ? `Launch on ${selectedTV.name}:` : 'Available on:'}
                </span>
                <div className="service-badges">
                  {result.available_services && result.available_services.map((service) => (
                    <button
                      key={service}
                      className={`service-badge ${selectedTV ? 'launchable' : ''}`}
                      onClick={() => handleServiceClick(result, service)}
                      disabled={!selectedTV || isLoading}
                      title={selectedTV ? `Launch ${service} on ${selectedTV.name}` : 'Select a TV first'}
                    >
                      {service}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ResultsList;
