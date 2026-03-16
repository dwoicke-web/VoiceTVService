import React, { useState, useEffect } from 'react';
import '../styles/TVLayout.css';

const TVLayout = ({ selectedTV, onSelectTV, tvs, playingContent = {} }) => {
  // Helper function to render TV content (either now playing or default info)
  const renderTVContent = (tvId, tvName, tvSize, tvType) => {
    const playing = playingContent[tvId];

    if (playing) {
      return (
        <div className="tv-content playing">
          <img
            src={playing.poster}
            alt={playing.title}
            className="now-playing-poster"
          />
          <div className="now-playing-info">
            <div className="now-playing-title">{playing.title}</div>
            <div className="now-playing-service">{playing.service}</div>
          </div>
        </div>
      );
    }

    return (
      <div className="tv-content idle">
        <div className="tv-name">{tvName}</div>
        <div className="tv-size">{tvSize}</div>
        <div className="tv-type">{tvType}</div>
      </div>
    );
  };

  return (
    <div className="tv-layout-container">
      <h2>Basement TV Setup</h2>

      <div className="tv-grid">
        {/* Upper Left TV */}
        <div className="tv-slot upper-left">
          <div
            className={`tv ${selectedTV?.id === 'upper_left' ? 'selected' : ''}`}
            onClick={() => onSelectTV(tvs.find(tv => tv.id === 'upper_left'))}
          >
            <div className="tv-frame">
              {renderTVContent('upper_left', 'Upper Left', '32"', 'Fire TV')}
            </div>
          </div>
        </div>

        {/* Upper Right TV */}
        <div className="tv-slot upper-right">
          <div
            className={`tv ${selectedTV?.id === 'upper_right' ? 'selected' : ''}`}
            onClick={() => onSelectTV(tvs.find(tv => tv.id === 'upper_right'))}
          >
            <div className="tv-frame">
              {renderTVContent('upper_right', 'Upper Right', '32"', 'Fire TV')}
            </div>
          </div>
        </div>

        {/* Center Big Screen */}
        <div className="tv-slot center">
          <div
            className={`tv big-screen ${selectedTV?.id === 'big_screen' ? 'selected' : ''}`}
            onClick={() => onSelectTV(tvs.find(tv => tv.id === 'big_screen'))}
          >
            <div className="tv-frame">
              {renderTVContent('big_screen', 'Big Screen', '75"', 'Samsung Smart TV')}
            </div>
          </div>
        </div>

        {/* Lower Left TV */}
        <div className="tv-slot lower-left">
          <div
            className={`tv ${selectedTV?.id === 'lower_left' ? 'selected' : ''}`}
            onClick={() => onSelectTV(tvs.find(tv => tv.id === 'lower_left'))}
          >
            <div className="tv-frame">
              {renderTVContent('lower_left', 'Lower Left', '32"', 'Fire TV')}
            </div>
          </div>
        </div>

        {/* Lower Right TV */}
        <div className="tv-slot lower-right">
          <div
            className={`tv ${selectedTV?.id === 'lower_right' ? 'selected' : ''}`}
            onClick={() => onSelectTV(tvs.find(tv => tv.id === 'lower_right'))}
          >
            <div className="tv-frame">
              {renderTVContent('lower_right', 'Lower Right', '32"', 'Fire TV')}
            </div>
          </div>
        </div>
      </div>

      {selectedTV && (
        <div className="selected-tv-info">
          <h3>Selected: {selectedTV.name}</h3>
          <p>Status: <span className={`status ${selectedTV.status}`}>{selectedTV.status}</span></p>
        </div>
      )}
    </div>
  );
};

export default TVLayout;
