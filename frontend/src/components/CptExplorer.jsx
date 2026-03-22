import { useState, useEffect } from 'react';
import { searchCpt } from '../api/client';
import { formatCurrency } from '../utils/formatters';

const POPULAR_SEARCHES = [
  { label: 'MRI', query: 'MRI' },
  { label: 'X-Ray', query: 'x-ray' },
  { label: 'Blood Work', query: 'blood' },
  { label: 'Office Visit', query: 'office visit' },
  { label: 'Physical Therapy', query: 'physical therapy' },
  { label: 'Colonoscopy', query: 'colonoscopy' },
  { label: 'CT Scan', query: 'CT' },
  { label: 'Emergency Room', query: 'emergency' },
];

export default function CptExplorer() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [expandedCode, setExpandedCode] = useState(null);
  const [searchError, setSearchError] = useState(null);

  useEffect(() => {
    if (query.length < 2) {
      setResults([]);
      setSearchError(null);
      return;
    }
    const timer = setTimeout(async () => {
      setLoading(true);
      setSearchError(null);
      try {
        const data = await searchCpt(query, 20);
        setResults(data.results);
      } catch {
        setSearchError('Search failed. Make sure the backend is running.');
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  return (
    <div className="min-h-screen bg-bg p-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8 pt-8">
          <h1 className="text-3xl font-bold text-text mb-2">Price Explorer</h1>
          <p className="text-text-light">Look up the fair price for any medical procedure</p>
        </div>

        {/* Search bar */}
        <div className="relative mb-6">
          <svg className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-light" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search any procedure — try 'MRI', 'knee replacement', 'colonoscopy'..."
            className="w-full pl-12 pr-4 py-4 rounded-xl border border-border bg-card shadow-sm text-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
          />
          {loading && (
            <div className="absolute right-4 top-1/2 -translate-y-1/2">
              <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
          )}
        </div>

        {/* Popular searches (shown when no query) */}
        {query.length < 2 && (
          <div className="mb-8">
            <p className="text-sm text-text-light mb-3 text-center">Popular searches:</p>
            <div className="flex flex-wrap justify-center gap-2">
              {POPULAR_SEARCHES.map((item) => (
                <button
                  key={item.query}
                  onClick={() => setQuery(item.query)}
                  className="px-4 py-2 bg-card border border-border rounded-full text-sm hover:border-primary hover:text-primary transition-colors"
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Error */}
        {searchError && (
          <div className="bg-danger-light text-danger rounded-xl p-4 mb-4 text-sm">{searchError}</div>
        )}

        {/* Results */}
        {results.length > 0 && (
          <div className="space-y-3">
            {results.map((item) => {
              const isExpanded = expandedCode === item.cpt_code;
              const basePrice = item.medicare_non_facility || item.medicare_facility || 0;
              const fairHigh = item.fair_price_range?.high || 0;

              return (
                <div
                  key={item.cpt_code}
                  className="bg-card border border-border rounded-xl p-5 cursor-pointer hover:shadow-md transition-shadow"
                  onClick={() => setExpandedCode(isExpanded ? null : item.cpt_code)}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <code className="text-sm font-bold font-mono bg-primary/10 text-primary px-2 py-0.5 rounded">
                          {item.cpt_code}
                        </code>
                      </div>
                      <p className="text-sm text-text">{item.description}</p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-xs text-text-light">Medicare Rate</p>
                      <p className="font-bold text-primary">{formatCurrency(basePrice)}</p>
                    </div>
                  </div>

                  {/* Price bar visualization */}
                  {basePrice > 0 && (
                    <div className="mt-3">
                      <div className="flex justify-between text-xs text-text-light mb-1">
                        <span>Fair Range: {formatCurrency(item.fair_price_range?.low)} – {formatCurrency(item.fair_price_range?.high)}</span>
                      </div>
                      <div className="bg-gray-100 rounded-full h-3 relative overflow-hidden">
                        <div
                          className="bg-success/30 h-full absolute"
                          style={{
                            left: `${(item.fair_price_range?.low / (fairHigh * 1.5)) * 100}%`,
                            width: `${((item.fair_price_range?.high - item.fair_price_range?.low) / (fairHigh * 1.5)) * 100}%`
                          }}
                        />
                        <div
                          className="bg-primary h-full rounded-full absolute w-1"
                          style={{ left: `${(basePrice / (fairHigh * 1.5)) * 100}%` }}
                          title="Medicare Rate"
                        />
                      </div>
                      <p className="text-xs text-text-light mt-1">
                        If charged more than <span className="font-semibold text-danger">{formatCurrency(fairHigh)}</span>, you're likely being overcharged
                      </p>
                    </div>
                  )}

                  {/* Expanded details */}
                  {isExpanded && (
                    <div className="mt-4 pt-4 border-t border-border grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="text-text-light">Non-Facility (Office)</p>
                        <p className="font-semibold">{formatCurrency(item.medicare_non_facility)}</p>
                      </div>
                      <div>
                        <p className="text-text-light">Facility (Hospital)</p>
                        <p className="font-semibold">{formatCurrency(item.medicare_facility)}</p>
                      </div>
                      <div>
                        <p className="text-text-light">Fair Price (1.5x–2.5x Medicare)</p>
                        <p className="font-semibold text-success">
                          {formatCurrency(item.fair_price_range?.low)} – {formatCurrency(item.fair_price_range?.high)}
                        </p>
                      </div>
                      <div>
                        <p className="text-text-light">Typical Commercial (2x)</p>
                        <p className="font-semibold">{formatCurrency(item.fair_price_range?.mid)}</p>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* No results */}
        {query.length >= 2 && !loading && results.length === 0 && !searchError && (
          <div className="text-center py-12 text-text-light">
            <p className="text-lg mb-1">No procedures found matching &ldquo;{query}&rdquo;</p>
            <p className="text-sm">Try broader terms — e.g., &ldquo;MRI&rdquo; instead of &ldquo;MRI of left knee with contrast&rdquo;</p>
          </div>
        )}
      </div>
    </div>
  );
}
