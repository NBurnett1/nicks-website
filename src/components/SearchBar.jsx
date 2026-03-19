import { useState } from 'react';
import './SearchBar.css';

export default function SearchBar({ onSearch }) {
  const [query, setQuery] = useState('');

  const handleChange = (e) => {
    setQuery(e.target.value);
    onSearch(e.target.value);
  }

  const handleClear = () => {
    setQuery('');
    onSearch('');
  }

  return (
    <div className="search-bar animate-fade-in-up">
      <div className="search-bar__input-container">
        <svg className="search-bar__icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M21 21L15 15M17 10C17 13.866 13.866 17 10 17C6.13401 17 3 13.866 3 10C3 6.13401 6.13401 3 10 3C13.866 3 17 6.13401 17 10Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        <input 
          type="text" 
          className="search-bar__input" 
          placeholder="Search 200+ companies by ticker or name..." 
          value={query}
          onChange={handleChange}
        />
        {query && (
          <button className="search-bar__clear" onClick={handleClear} aria-label="Clear search">
            ✕
          </button>
        )}
      </div>
    </div>
  )
}
