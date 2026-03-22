import { useState } from 'react';
import { categoryColor, categoryLabel } from '../utils/formatters';

export default function StateLawPanel({ stateLaws, federalLaws, stateName }) {
  const [isExpanded, setIsExpanded] = useState(true);

  const allLaws = [...(stateLaws || []), ...(federalLaws || [])];
  if (allLaws.length === 0) return null;

  return (
    <div className="bg-card rounded-2xl shadow-sm border border-border p-6 mb-6 animate-fade-in">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between"
      >
        <h2 className="text-lg font-semibold text-text">
          Your Rights{stateName ? ` in ${stateName}` : ''}
        </h2>
        <svg
          className={`w-5 h-5 text-text-light transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isExpanded && (
        <div className="mt-4 space-y-4">
          {/* State laws */}
          {stateLaws?.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-text-light mb-3">State Protections</h3>
              <div className="space-y-3">
                {stateLaws.map((law, idx) => (
                  <LawCard key={`state-${idx}`} law={law} />
                ))}
              </div>
            </div>
          )}

          {/* Federal laws */}
          {federalLaws?.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-text-light mb-3">Federal Protections</h3>
              <div className="space-y-3">
                {federalLaws.map((law, idx) => (
                  <LawCard key={`federal-${idx}`} law={law} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function LawCard({ law }) {
  const colors = categoryColor(law.category);
  return (
    <div className="border border-border rounded-xl p-4">
      <div className="flex items-start justify-between gap-2 mb-2">
        <div>
          <h4 className="font-semibold text-text text-sm">{law.law_name}</h4>
          <code className="text-xs text-text-light font-mono">{law.law_citation}</code>
        </div>
        <span className={`shrink-0 px-2 py-0.5 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}>
          {categoryLabel(law.category)}
        </span>
      </div>
      <p className="text-sm text-text-light mb-2">{law.summary}</p>
      <div className="flex items-center gap-3">
        {law.applies_to && (
          <span className="text-xs bg-gray-100 text-text-light px-2 py-0.5 rounded">
            Applies to: {law.applies_to}
          </span>
        )}
        {law.url && (
          <a
            href={law.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-primary hover:underline"
          >
            View Statute &rarr;
          </a>
        )}
      </div>
    </div>
  );
}
