import React, { useState, useEffect } from 'react';
import '../styles/TVLayout.css';

const TVLayout = ({ selectedTV, onSelectTV, tvs }) => {
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
              <div className="tv-content">
                <div className="tv-name">Upper Left</div>
                <div className="tv-size">32"</div>
                <div className="tv-type">Fire TV</div>
              </div>
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
              <div className="tv-content">
                <div className="tv-name">Upper Right</div>
                <div className="tv-size">32"</div>
                <div className="tv-type">Fire TV</div>
              </div>
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
              <div className="tv-content">
                <div className="tv-name">Big Screen</div>
                <div className="tv-size">75"</div>
                <div className="tv-type">Samsung Smart TV</div>
              </div>
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
              <div className="tv-content">
                <div className="tv-name">Lower Left</div>
                <div className="tv-size">32"</div>
                <div className="tv-type">Fire TV</div>
              </div>
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
              <div className="tv-content">
                <div className="tv-name">Lower Right</div>
                <div className="tv-size">32"</div>
                <div className="tv-type">Fire TV</div>
              </div>
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
