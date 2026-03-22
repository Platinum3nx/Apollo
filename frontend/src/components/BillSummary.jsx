import { useState } from 'react';
import { formatCurrency, severityColor, severityLabel } from '../utils/formatters';

export default function BillSummary({ parsedBill, benchmarks, errors, summary }) {
  const [expandedRow, setExpandedRow] = useState(null);

  const benchmarkMap = {};
  for (const b of benchmarks) {
    benchmarkMap[b.line_item_id] = b;
  }

  const errorMap = {};
  for (const error of errors) {
    for (const item of error.affected_items || []) {
      if (!item?.id) continue;
      if (!errorMap[item.id]) errorMap[item.id] = [];
      errorMap[item.id].push(error);
    }
  }

  return (
    <div className="bg-card rounded-2xl shadow-sm border border-border p-6 mb-6 animate-fade-in">
      <h2 className="text-lg font-semibold text-text mb-4">Parsed Bill</h2>

      {/* Provider & Patient info */}
      <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
        <div className="bg-bg rounded-lg p-3">
          <p className="font-medium text-text-light mb-1">Provider</p>
          <p className="font-semibold">{parsedBill.provider?.name || 'Unknown'}</p>
          {parsedBill.provider?.address && <p className="text-text-light text-xs">{parsedBill.provider.address}</p>}
        </div>
        <div className="bg-bg rounded-lg p-3">
          <p className="font-medium text-text-light mb-1">Patient</p>
          <p className="font-semibold">{parsedBill.patient?.name || 'Unknown'}</p>
          {parsedBill.patient?.date_of_service && <p className="text-text-light text-xs">Service: {parsedBill.patient.date_of_service}</p>}
          {parsedBill.patient?.insurance && <p className="text-text-light text-xs">Insurance: {parsedBill.patient.insurance}</p>}
        </div>
      </div>

      {/* Line items table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 px-3 text-text-light font-medium">Description</th>
              <th className="text-left py-2 px-3 text-text-light font-medium">CPT</th>
              <th className="text-left py-2 px-3 text-text-light font-medium">Date</th>
              <th className="text-right py-2 px-3 text-text-light font-medium">Charged</th>
              <th className="text-right py-2 px-3 text-text-light font-medium">Fair Price</th>
              <th className="text-center py-2 px-3 text-text-light font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {parsedBill.line_items?.map((item) => {
              const benchmark = benchmarkMap[item.id];
              const relatedErrors = errorMap[item.id] || [];
              const colors = benchmark ? severityColor(benchmark.severity) : severityColor('unknown');
              const isExpanded = expandedRow === item.id;
              const statusLabel = relatedErrors.length > 0 ? 'Error' : (benchmark ? severityLabel(benchmark.severity) : 'Unknown');
              const statusClasses = relatedErrors.length > 0
                ? 'bg-red-100 text-red-800'
                : `${colors.bg} ${colors.text}`;

              return (
                <Fragment key={item.id}>
                  <tr
                    className="border-b border-border/50 hover:bg-bg cursor-pointer transition-colors"
                    onClick={() => setExpandedRow(isExpanded ? null : item.id)}
                  >
                    <td className="py-2.5 px-3">
                      <span className="font-medium">{item.description}</span>
                      {item.quantity > 1 && <span className="text-text-light ml-1">x{item.quantity}</span>}
                    </td>
                    <td className="py-2.5 px-3">
                      <code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">{item.cpt_code}</code>
                      {item.cpt_inferred && (
                        <span className="ml-1 text-xs text-text-light" title="CPT code was inferred by AI">*</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-text-light">{item.date || '—'}</td>
                    <td className="py-2.5 px-3 text-right font-medium">{formatCurrency(item.total_charge)}</td>
                    <td className="py-2.5 px-3 text-right">
                      {benchmark?.fair_price_mid ? formatCurrency(benchmark.fair_price_mid) : '—'}
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${statusClasses}`}>
                        {statusLabel}
                      </span>
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr>
                      <td colSpan={6} className="bg-bg p-4">
                        <div className="grid md:grid-cols-4 gap-4 text-xs">
                          <div>
                            <p className="text-text-light">Medicare Rate</p>
                            <p className="font-semibold">{benchmark?.medicare_rate ? formatCurrency(benchmark.medicare_rate) : 'N/A'}</p>
                          </div>
                          <div>
                            <p className="text-text-light">Fair Range</p>
                            <p className="font-semibold">
                              {benchmark?.fair_price_low ? `${formatCurrency(benchmark.fair_price_low)} – ${formatCurrency(benchmark.fair_price_high)}` : 'N/A'}
                            </p>
                          </div>
                          <div>
                            <p className="text-text-light">Overcharge Ratio</p>
                            <p className="font-semibold">{benchmark?.overcharge_ratio ? `${benchmark.overcharge_ratio}x` : 'N/A'}</p>
                          </div>
                          <div>
                            <p className="text-text-light">Potential Savings</p>
                            <p className="font-semibold text-success">{formatCurrency(benchmark?.potential_savings ?? null)}</p>
                          </div>
                        </div>
                        {benchmark?.note && <p className="text-xs text-text-light mt-2">{benchmark.note}</p>}
                        {relatedErrors.length > 0 && (
                          <div className="mt-3 bg-red-50 border border-red-100 rounded-xl p-3">
                            <p className="text-xs font-medium text-red-900 mb-2">Billing Errors Affecting This Line Item</p>
                            <div className="space-y-2">
                              {relatedErrors.map((error) => (
                                <div key={error.id} className="text-xs text-red-900/80">
                                  <span className="font-semibold">{error.title}</span>
                                  {error.estimated_overcharge != null && (
                                    <span> · Estimated correction {formatCurrency(error.estimated_overcharge)}</span>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-border font-semibold">
              <td className="py-3 px-3" colSpan={3}>Total</td>
              <td className="py-3 px-3 text-right">{formatCurrency(parsedBill.total_billed)}</td>
              <td className="py-3 px-3 text-right text-success">
                {formatCurrency(summary?.estimated_fair_total ?? benchmarks.reduce((sum, b) => sum + (b.fair_price_mid || b.charged), 0))}
              </td>
              <td />
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}

// Need Fragment import
import { Fragment } from 'react';
