import React from 'react';
import '../styles/ResultsList.css';

const ResultsList = ({ results, selectedTV, onLaunchContent, isLoading }) => {
  if (isLoading) {
    return <div className="results-loading">Loading results...</div>;
  }

  if (!results || results.length === 0) {
    return <div className="results-empty">No results found. Try searching for a show, movie, or sports event.</div>;
  }

  const handleLaunch = (result) => {
    if (!selectedTV) {
      alert('Please select a TV first');
      return;
    }
    onLaunchContent(result, selectedTV);
  };

  return (
    <div className="results-container">
      <h2>Search Results ({results.length})</h2>

      <div className="results-grid">
        {results.map((result) => (
          <div key={result.id} className="result-card">
            <div className="result-poster">
              <img src={result.poster} alt={result.title} />
              <div className="result-overlay">
                <button
                  className="launch-button"
                  onClick={() => handleLaunch(result)}
                  disabled={!selectedTV}
                >
                  {selectedTV ? `Play on ${selectedTV.name}` : 'Select TV First'}
                </button>
              </div>
            </div>

            <div className="result-info">
              <h3 className="result-title">{result.title}</h3>
              <p className="result-type">{result.type.toUpperCase()}</p>
              <p className="result-description">{result.description}</p>

              <div className="result-services">
                <span className="services-label">Available on:</span>
                <div className="service-badges">
                  {result.available_services && result.available_services.map((service) => (
                    <span key={service} className="service-badge">
                      {service}
                    </span>
                  ))}
                </div>
              </div>

              <div className="result-tvs">
                <span className="tvs-label">Can play on:</span>
                <div className="tv-list">
                  {result.available_tvs && result.available_tvs.map((tv_id) => (
                    <span key={tv_id} className="tv-chip">
                      {tv_id.replace(/_/g, ' ')}
                    </span>
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
