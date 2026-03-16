import React, { useState, useEffect } from 'react';
import '../styles/TVLayout.css';

const TVLayout = ({ selectedTV, onSelectTV, tvs, playingContent = {}, onResetChannel }) => {
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
          {onResetChannel && (
            <button
              className="reset-channel-btn"
              onClick={() => onResetChannel(tvs.find(tv => tv.id === 'upper_left'))}
              title="Reset to antenna channel 7"
            >
              📡 Reset Antenna 7
            </button>
          )}
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
          {onResetChannel && (
            <button
              className="reset-channel-btn"
              onClick={() => onResetChannel(tvs.find(tv => tv.id === 'upper_right'))}
              title="Reset to antenna channel 10"
            >
              📡 Reset Antenna 10
            </button>
          )}
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
          {onResetChannel && (
            <button
              className="reset-channel-btn"
              onClick={() => onResetChannel(tvs.find(tv => tv.id === 'lower_left'))}
              title="Reset to antenna channel 8"
            >
              📡 Reset Antenna 8
            </button>
          )}
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
          {onResetChannel && (
            <button
              className="reset-channel-btn"
              onClick={() => onResetChannel(tvs.find(tv => tv.id === 'lower_right'))}
              title="Reset to antenna channel 11"
            >
              📡 Reset Antenna 11
            </button>
          )}
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
