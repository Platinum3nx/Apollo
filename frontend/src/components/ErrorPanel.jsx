import { formatCurrency, errorTypeColor, errorTypeLabel } from '../utils/formatters';

export default function ErrorPanel({ errors }) {
  if (errors.length === 0) {
    return (
      <div className="bg-card rounded-2xl shadow-sm border border-border p-6 mb-6 animate-fade-in">
        <h2 className="text-lg font-semibold text-text mb-4">Billing Error Detection</h2>
        <div className="bg-success-light rounded-xl p-6 text-center">
          <svg className="w-12 h-12 mx-auto text-success mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="font-semibold text-success">No billing errors detected</p>
          <p className="text-sm text-text-light mt-1">Your bill appears to be coded correctly.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card rounded-2xl shadow-sm border border-border p-6 mb-6 animate-fade-in">
      <h2 className="text-lg font-semibold text-text mb-4">
        Billing Errors Detected
        <span className="ml-2 text-sm font-normal text-danger">({errors.length} found)</span>
      </h2>
      <div className="space-y-4">
        {errors.map((error) => {
          const typeColors = errorTypeColor(error.type);
          return (
            <div key={error.id} className="border border-border rounded-xl p-5">
              {/* Header */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${typeColors.bg} ${typeColors.text}`}>
                    {errorTypeLabel(error.type)}
                  </span>
                  <h3 className="font-semibold text-text">{error.title}</h3>
                </div>
                {error.estimated_overcharge != null && error.estimated_overcharge > 0 && (
                  <span className="text-danger font-bold text-lg">{formatCurrency(error.estimated_overcharge)}</span>
                )}
              </div>

              {/* Confidence bar */}
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xs text-text-light">Confidence:</span>
                <div className="flex-1 max-w-[200px] bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-primary h-2 rounded-full"
                    style={{ width: `${(error.confidence || 0) * 100}%` }}
                  />
                </div>
                <span className="text-xs font-medium">{Math.round((error.confidence || 0) * 100)}%</span>
              </div>

              {/* Description */}
              <p className="text-sm text-text-light mb-3">{error.description}</p>

              {/* Affected items */}
              {error.affected_items?.length > 0 && (
                <div className="mb-3">
                  <p className="text-xs font-medium text-text-light mb-1">Affected Items:</p>
                  <div className="flex flex-wrap gap-2">
                    {error.affected_items.map((item, idx) => (
                      <span key={idx} className="text-xs bg-gray-100 px-2 py-1 rounded">
                        {item.cpt_code || 'N/A'}: {item.description || 'N/A'} ({formatCurrency(item.total_charge)})
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Regulation */}
              {error.regulation && (
                <div className="bg-gray-50 rounded-lg px-3 py-2 mb-3">
                  <p className="text-xs text-text-light">{error.regulation}</p>
                </div>
              )}

              {/* Recommendation */}
              {error.recommendation && (
                <p className="text-sm text-success font-medium">{error.recommendation}</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
