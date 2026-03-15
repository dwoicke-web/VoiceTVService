import React, { useState } from 'react';
import '../styles/SearchBar.css';

const SearchBar = ({ onSearch, isLoading }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [contentType, setContentType] = useState('all');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      onSearch(searchQuery, contentType);
    }
  };

  const handleChange = (e) => {
    setSearchQuery(e.target.value);
  };

  const handleContentTypeChange = (e) => {
    setContentType(e.target.value);
  };

  return (
    <div className="search-bar-container">
      <h2>Search Content</h2>
      <form onSubmit={handleSubmit} className="search-form">
        <div className="search-input-group">
          <input
            type="text"
            className="search-input"
            placeholder="Search for shows, movies, or sports..."
            value={searchQuery}
            onChange={handleChange}
            disabled={isLoading}
          />
          <button type="submit" className="search-button" disabled={isLoading}>
            {isLoading ? 'Searching...' : 'Search'}
          </button>
        </div>

        <div className="filter-group">
          <label htmlFor="content-type">Filter by type:</label>
          <select
            id="content-type"
            value={contentType}
            onChange={handleContentTypeChange}
            disabled={isLoading}
            className="filter-select"
          >
            <option value="all">All</option>
            <option value="show">TV Shows</option>
            <option value="movie">Movies</option>
            <option value="sports">Sports</option>
          </select>
        </div>
      </form>
    </div>
  );
};

export default SearchBar;
