import { useEffect, useState } from 'react';
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

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function highlightMatch(text, query) {
  if (!text) return 'Procedure description unavailable';

  const terms = query
    .trim()
    .split(/\s+/)
    .filter(Boolean);

  if (!terms.length) return text;

  const pattern = new RegExp(`(${terms.map(escapeRegExp).join('|')})`, 'ig');
  const parts = text.split(pattern);
  const isMatch = (part) => terms.some((term) => part.toLowerCase() === term.toLowerCase());

  return parts.map((part, index) => (
    isMatch(part)
      ? (
        <mark
          key={`${part}-${index}`}
          className="rounded bg-primary/10 px-0.5 text-primary"
        >
          {part}
        </mark>
      )
      : <span key={`${part}-${index}`}>{part}</span>
  ));
}

function MetricCard({ label, value, hint, tone = 'neutral' }) {
  const toneClasses = {
    neutral: 'border-border bg-bg text-text',
    primary: 'border-primary/15 bg-primary/5 text-primary-dark',
    danger: 'border-danger/15 bg-danger-light/50 text-danger',
  };

  return (
    <div className={`rounded-2xl border p-4 ${toneClasses[tone] || toneClasses.neutral}`}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-text-light">{label}</p>
      <p className="mt-2 text-xl font-semibold text-text">{value}</p>
      <p className="mt-1 text-sm text-text-light">{hint}</p>
    </div>
  );
}

export default function CptExplorer() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [expandedCode, setExpandedCode] = useState(null);
  const [searchError, setSearchError] = useState(null);
  const trimmedQuery = query.trim();
  const hasSearch = trimmedQuery.length >= 2;

  useEffect(() => {
    if (!hasSearch) {
      setResults([]);
      setExpandedCode(null);
      setSearchError(null);
      return;
    }

    const timer = setTimeout(async () => {
      setLoading(true);
      setSearchError(null);

      try {
        const data = await searchCpt(trimmedQuery, 20);
        setResults(data.results);
        setExpandedCode((currentCode) => (
          data.results.some((item) => item.cpt_code === currentCode) ? currentCode : null
        ));
      } catch {
        setSearchError('Search failed. Make sure the backend is running.');
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [hasSearch, trimmedQuery]);

  return (
    <div className="min-h-screen bg-bg p-4">
      <div className="mx-auto max-w-5xl">
        <div className="pt-8 text-center">
          <h1 className="text-3xl font-bold text-text mb-2">Price Explorer</h1>
          <p className="text-text-light">Look up the fair price for any medical procedure</p>
        </div>

        <div className="mt-8 mb-6">
          <div className="relative">
            <svg className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-text-light" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by procedure or CPT code — try 'MRI', 'knee replacement', or '70553'"
              className="w-full rounded-2xl border border-border bg-card py-4 pl-12 pr-4 text-lg shadow-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-primary"
            />
            {loading && (
              <div className="absolute right-4 top-1/2 -translate-y-1/2">
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              </div>
            )}
          </div>
          <p className="mt-3 text-sm text-text-light">
            Results are sorted by relevance first. The procedure names come from official CMS billing data, so they can look abbreviated.
          </p>
        </div>

        {!hasSearch && (
          <div className="mb-8 rounded-3xl border border-border bg-card p-5 shadow-sm">
            <p className="mb-3 text-sm font-medium text-text-light">Popular searches</p>
            <div className="flex flex-wrap gap-2">
              {POPULAR_SEARCHES.map((item) => (
                <button
                  key={item.query}
                  onClick={() => setQuery(item.query)}
                  className="rounded-full border border-border bg-bg px-4 py-2 text-sm transition-colors hover:border-primary hover:text-primary"
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {searchError && (
          <div className="mb-6 flex flex-col items-center justify-center rounded-3xl border border-orange-200 bg-orange-50 p-8 text-center shadow-sm">
            <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-orange-100 text-orange-500">
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
            </div>
            <h3 className="mb-1 text-lg font-semibold text-orange-900">Network Disconnected</h3>
            <p className="text-sm text-orange-800/80">Search failed. Please ensure the Apollo backend is running to search CMS databases.</p>
          </div>
        )}

        {results.length > 0 && (
          <div className="mb-4 rounded-3xl border border-border bg-card p-5 shadow-sm">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-sm font-semibold text-text">
                  {results.length} match{results.length === 1 ? '' : 'es'} for &ldquo;{trimmedQuery}&rdquo;
                </p>
                <p className="text-sm text-text-light">
                  Use the CPT code to compare against your bill. Open a card if you want the underlying Medicare rate details.
                </p>
              </div>
              <div className="flex flex-wrap gap-2 text-xs">
                <span className="rounded-full bg-primary/10 px-3 py-1 font-medium text-primary">Most relevant first</span>
                <span className="rounded-full bg-bg px-3 py-1 font-medium text-text-light">Official CMS wording</span>
              </div>
            </div>
          </div>
        )}

        {results.length > 0 && (
          <div className="space-y-4">
            {results.map((item, index) => {
              const isExpanded = expandedCode === item.cpt_code;
              const basePrice = item.medicare_non_facility || item.medicare_facility || 0;
              const fairLow = item.fair_price_range?.low;
              const fairMid = item.fair_price_range?.mid;
              const fairHigh = item.fair_price_range?.high;

              return (
                <div key={item.cpt_code} className="rounded-3xl border border-border bg-card p-5 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-lg">
                  <button
                    type="button"
                    onClick={() => setExpandedCode(isExpanded ? null : item.cpt_code)}
                    aria-expanded={isExpanded}
                    className="w-full text-left"
                  >
                    <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
                      <div className="flex-1">
                        <div className="mb-3 flex flex-wrap items-center gap-2">
                          <code className="rounded-lg bg-primary/10 px-3 py-1 text-sm font-bold text-primary">
                            {item.cpt_code}
                          </code>
                          {index === 0 && (
                            <span className="rounded-full bg-success-light px-3 py-1 text-xs font-semibold text-success">
                              Best match
                            </span>
                          )}
                          <span className="rounded-full bg-bg px-3 py-1 text-xs font-medium text-text-light">
                            Official CMS label
                          </span>
                        </div>
                        <h2 className="text-xl font-semibold leading-snug text-text">
                          {highlightMatch(item.description, trimmedQuery)}
                        </h2>
                        <p className="mt-2 text-sm text-text-light">
                          Compare this CPT code to the line item on your bill or to a hospital estimate before you negotiate.
                        </p>
                      </div>

                      <div className="rounded-2xl border border-success/20 bg-success-light p-4 lg:w-80">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-success">Likely fair billed range</p>
                        <p className="mt-2 text-2xl font-bold text-text">
                          {formatCurrency(fairLow)} - {formatCurrency(fairHigh)}
                        </p>
                        <p className="mt-2 text-sm text-text-light">
                          Bills above <span className="font-semibold text-danger">{formatCurrency(fairHigh)}</span> are worth a closer review.
                        </p>
                      </div>
                    </div>

                    <div className="mt-5 grid gap-3 md:grid-cols-3">
                      <MetricCard
                        label="Medicare baseline"
                        value={formatCurrency(basePrice)}
                        hint="Apollo anchors its pricing range to this reference amount."
                        tone="primary"
                      />
                      <MetricCard
                        label="Typical commercial midpoint"
                        value={formatCurrency(fairMid)}
                        hint="A simple mid-market checkpoint based on 2x Medicare."
                      />
                      <MetricCard
                        label="Review if bill exceeds"
                        value={formatCurrency(fairHigh)}
                        hint="Higher charges are more likely to be inflated."
                        tone="danger"
                      />
                    </div>

                    <div className="mt-4 flex items-center justify-between border-t border-border pt-4 text-sm">
                      <span className="font-medium text-text">
                        {isExpanded ? 'Hide rate details' : 'Show rate details'}
                      </span>
                      <svg
                        className={`h-5 w-5 text-text-light transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2}
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                      </svg>
                    </div>
                  </button>

                  {isExpanded && (
                    <div className="mt-4 grid gap-3 border-t border-border pt-4 md:grid-cols-2 xl:grid-cols-4">
                      <div className="rounded-2xl bg-bg p-4">
                        <p className="text-sm text-text-light">Office / non-facility Medicare rate</p>
                        <p className="mt-1 text-lg font-semibold text-text">{formatCurrency(item.medicare_non_facility)}</p>
                      </div>
                      <div className="rounded-2xl bg-bg p-4">
                        <p className="text-sm text-text-light">Hospital / facility Medicare rate</p>
                        <p className="mt-1 text-lg font-semibold text-text">{formatCurrency(item.medicare_facility)}</p>
                      </div>
                      <div className="rounded-2xl bg-bg p-4">
                        <p className="text-sm text-text-light">Apollo fair-price range</p>
                        <p className="mt-1 text-lg font-semibold text-success">
                          {formatCurrency(fairLow)} - {formatCurrency(fairHigh)}
                        </p>
                      </div>
                      <div className="rounded-2xl bg-bg p-4">
                        <p className="text-sm text-text-light">Why this matters</p>
                        <p className="mt-1 text-sm text-text">
                          Commercial bills often land around 1.5x to 2.5x Medicare. Large gaps above that range are a useful negotiation signal.
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {hasSearch && !loading && results.length === 0 && !searchError && (
          <div className="py-12 text-center text-text-light">
            <p className="mb-1 text-lg">No procedures found matching &ldquo;{trimmedQuery}&rdquo;</p>
            <p className="text-sm">Try a broader term like &ldquo;MRI&rdquo; or search directly by CPT code.</p>
          </div>
        )}
      </div>
    </div>
  );
}
