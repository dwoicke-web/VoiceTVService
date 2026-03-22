import React, { useState } from 'react';
import axios from 'axios';
import '../styles/ChannelPicker.css';

const CHANNELS = [
  { name: 'ESPN', icon: '⚽' },
  { name: 'ESPN2', icon: '⚽' },
  { name: 'ESPN News', icon: '⚽' },
  { name: 'Fox News', icon: '📰' },
  { name: 'CNN', icon: '📰' },
  { name: 'MSNBC', icon: '📰' },
  { name: 'Newsmax', icon: '📰' },
  { name: 'CBS', icon: '📺' },
  { name: 'NBC', icon: '📺' },
  { name: 'ABC', icon: '📺' },
  { name: 'FOX', icon: '📺' },
  { name: 'TBS', icon: '📺' },
  { name: 'TNT', icon: '📺' },
  { name: 'truTV', icon: '📺' },
  { name: 'FS1', icon: '🏈' },
  { name: 'NFL Network', icon: '🏈' },
  { name: 'MLB Network', icon: '⚾' },
  { name: 'NBA TV', icon: '🏀' },
  { name: 'Golf Channel', icon: '⛳' },
  { name: 'SEC Network', icon: '🏈' },
  { name: 'Big Ten Network', icon: '🏈' },
  { name: 'ACC Network', icon: '🏈' },
  { name: 'USA Network', icon: '📺' },
  { name: 'Bravo', icon: '📺' },
  { name: 'HGTV', icon: '🏠' },
  { name: 'Food Network', icon: '🍳' },
  { name: 'Discovery', icon: '🔬' },
  { name: 'History', icon: '📜' },
  { name: 'Comedy Central', icon: '😂' },
  { name: 'FX', icon: '📺' },
  { name: 'AMC', icon: '🎬' },
  { name: 'Syfy', icon: '👽' },
  { name: 'Nickelodeon', icon: '🧒' },
  { name: 'Disney Channel', icon: '🏰' },
  { name: 'Cartoon Network', icon: '🖍️' },
  { name: 'The CW', icon: '📺' },
  { name: 'National Geographic', icon: '🌍' },
  { name: 'Animal Planet', icon: '🐾' },
];

const ChannelPicker = ({ selectedTV, tvs }) => {
  const [tuningChannel, setTuningChannel] = useState(null);
  const [isCollapsed, setIsCollapsed] = useState(true);

  const handleTuneChannel = async (channelName, tvId) => {
    if (!tvId) {
      alert('Please select a TV first');
      return;
    }

    setTuningChannel(channelName);
    try {
      await axios.post('/api/tv/tune', {
        tv_id: tvId,
        channel: channelName
      });
    } catch (err) {
      console.error('Error tuning channel:', err);
      alert(`Failed to tune to ${channelName}`);
    } finally {
      setTimeout(() => setTuningChannel(null), 2000);
    }
  };

  return (
    <div className="channel-picker">
      <div className="channel-picker-header" onClick={() => setIsCollapsed(!isCollapsed)}>
        <h3>📡 YouTube TV Channels</h3>
        <button className="collapse-btn" onClick={(e) => { e.stopPropagation(); setIsCollapsed(!isCollapsed); }}>
          {isCollapsed ? '▼ Show' : '▲ Hide'}
        </button>
      </div>

      {!isCollapsed && (
        <div className="channel-grid">
          {CHANNELS.map((channel) => (
            <div key={channel.name} className="channel-item">
              {selectedTV ? (
                <button
                  className={`channel-btn ${tuningChannel === channel.name ? 'tuning' : ''}`}
                  onClick={() => handleTuneChannel(channel.name, selectedTV.id)}
                  disabled={tuningChannel !== null}
                  title={`Tune ${channel.name} on ${selectedTV.name}`}
                >
                  <span className="channel-icon">{channel.icon}</span>
                  <span className="channel-name">{channel.name}</span>
                </button>
              ) : tvs && tvs.length > 0 ? (
                <div className="channel-multi">
                  <span className="channel-label">{channel.icon} {channel.name}</span>
                  <div className="channel-tv-btns" style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'3px'}}>
                    {['upper_left', 'upper_right', 'lower_left', 'lower_right'].map(tvId => {
                      const tv = tvs.find(t => t.id === tvId);
                      if (!tv) return <span key={tvId} className="channel-tv-btn-empty" />;
                      const label = { upper_left: 'UL', upper_right: 'UR', lower_left: 'LL', lower_right: 'LR' }[tvId];
                      return (
                        <button
                          key={tv.id}
                          className="channel-tv-btn"
                          onClick={() => handleTuneChannel(channel.name, tv.id)}
                          disabled={tuningChannel !== null}
                          title={`Tune ${channel.name} on ${tv.name}`}
                        >
                          {label}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <div className="channel-btn disabled">
                  <span className="channel-icon">{channel.icon}</span>
                  <span className="channel-name">{channel.name}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ChannelPicker;
