import React, { useState, useEffect } from 'react';
import axios from 'axios';
import '../styles/YTVChannelManager.css';

const YTVChannelManager = () => {
  const [mappings, setMappings] = useState({});
  const [count, setCount] = useState(0);
  const [updatedAt, setUpdatedAt] = useState(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    fetchMappings();
  }, []);

  const fetchMappings = async () => {
    try {
      const response = await axios.get('/api/tv/ytv-channels');
      setMappings(response.data.channels || {});
      setCount(response.data.count || 0);
      setUpdatedAt(response.data.updated_at);
    } catch (err) {
      console.error('Error fetching YTV mappings:', err);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setIsUploading(true);
    setUploadStatus(null);

    try {
      const text = await file.text();
      const json = JSON.parse(text);

      const response = await axios.post('/api/tv/ytv-channels/upload', json);
      setMappings(response.data.channels || {});
      setCount(response.data.count || 0);
      setUpdatedAt(response.data.updated_at);
      setUploadStatus({ type: 'success', message: `Extracted ${response.data.count} channels` });
    } catch (err) {
      const msg = err.response?.data?.message || err.response?.data?.error || 'Upload failed';
      setUploadStatus({ type: 'error', message: msg });
    } finally {
      setIsUploading(false);
      e.target.value = '';
    }
  };

  const handlePasteUpload = async () => {
    try {
      const text = await navigator.clipboard.readText();
      const json = JSON.parse(text);

      setIsUploading(true);
      setUploadStatus(null);

      const response = await axios.post('/api/tv/ytv-channels/upload', json);
      setMappings(response.data.channels || {});
      setCount(response.data.count || 0);
      setUpdatedAt(response.data.updated_at);
      setUploadStatus({ type: 'success', message: `Extracted ${response.data.count} channels` });
    } catch (err) {
      const msg = err.response?.data?.message || err.response?.data?.error || 'Invalid JSON in clipboard';
      setUploadStatus({ type: 'error', message: msg });
    } finally {
      setIsUploading(false);
    }
  };

  const formatDate = (isoString) => {
    if (!isoString) return 'Never';
    const d = new Date(isoString);
    return d.toLocaleDateString() + ' ' + d.toLocaleTimeString();
  };

  const sortedChannels = Object.entries(mappings).sort((a, b) => a[0].localeCompare(b[0]));

  return (
    <div className="ytv-manager">
      <div className="ytv-header" onClick={() => setIsExpanded(!isExpanded)}>
        <h3>
          <span className="ytv-icon">📡</span>
          YouTube TV Deep Link Channels
          <span className="ytv-badge">{count} mapped</span>
        </h3>
        <span className="ytv-toggle">{isExpanded ? '▼' : '▶'}</span>
      </div>

      {isExpanded && (
        <div className="ytv-content">
          <div className="ytv-info">
            <p>
              Deep linking lets you tune channels <strong>instantly</strong> without navigating YouTube TV's menus.
              Upload your <code>browse.json</code> from YouTube TV DevTools to enable it.
            </p>
            <div className="ytv-status">
              <span>Last updated: <strong>{formatDate(updatedAt)}</strong></span>
              <span>Channels: <strong>{count}</strong></span>
            </div>
          </div>

          <div className="ytv-upload">
            <h4>Update Channel Mappings</h4>
            <div className="ytv-instructions">
              <ol>
                <li>Go to <a href="https://tv.youtube.com" target="_blank" rel="noreferrer">tv.youtube.com</a> and log in</li>
                <li>Press <kbd>F12</kbd> to open DevTools, click the <strong>Network</strong> tab</li>
                <li>Click <strong>Live</strong> in YouTube TV to load the channel guide</li>
                <li>Filter for <code>browse</code> in the Network tab</li>
                <li>Right-click the request, <strong>Copy &gt; Copy response</strong></li>
                <li>Click "Paste from Clipboard" below, or save as .json and upload</li>
              </ol>
            </div>
            <div className="ytv-upload-buttons">
              <button
                onClick={handlePasteUpload}
                disabled={isUploading}
                className="ytv-paste-btn"
              >
                {isUploading ? 'Processing...' : 'Paste from Clipboard'}
              </button>
              <label className="ytv-file-btn">
                {isUploading ? 'Processing...' : 'Upload browse.json'}
                <input
                  type="file"
                  accept=".json"
                  onChange={handleFileUpload}
                  disabled={isUploading}
                  hidden
                />
              </label>
            </div>
            {uploadStatus && (
              <div className={`ytv-upload-status ${uploadStatus.type}`}>
                {uploadStatus.type === 'success' ? '✓' : '✗'} {uploadStatus.message}
              </div>
            )}
          </div>

          {sortedChannels.length > 0 && (
            <div className="ytv-channels-list">
              <h4>Mapped Channels ({count})</h4>
              <div className="ytv-channels-grid">
                {sortedChannels.map(([name, videoId]) => (
                  <div key={name} className="ytv-channel-item">
                    <span className="ytv-channel-name">{name}</span>
                    <span className="ytv-channel-id" title={videoId}>{videoId}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default YTVChannelManager;
