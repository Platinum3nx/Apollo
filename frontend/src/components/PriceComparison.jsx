import { formatCurrency } from '../utils/formatters';

export default function PriceComparison({ benchmarks }) {
  const chartData = benchmarks
    .filter(b => b.fair_price_mid != null && b.medicare_rate != null)
    .sort((a, b) => (b.overcharge_ratio || 0) - (a.overcharge_ratio || 0))
    .map(b => ({
      name: b.description.length > 30 ? b.description.slice(0, 30) + '...' : b.description,
      fullName: b.description,
      cpt: b.cpt_code,
      charged: b.charged,
      fairPrice: b.fair_price_mid,
      fairLow: b.fair_price_low,
      fairHigh: b.fair_price_high,
      medicare: b.medicare_rate,
      severity: b.severity,
    }));

  if (chartData.length === 0) {
    return null;
  }

  const maxValue = Math.max(
    ...chartData.map((item) => Math.max(item.charged || 0, item.fairHigh || 0, item.medicare || 0)),
    1
  );

  const widthFor = (value) => `${Math.min((value / maxValue) * 100, 100)}%`;
  const leftFor = (value) => `${Math.min((value / maxValue) * 100, 100)}%`;

  const getChargedFill = (severity) => {
    switch (severity) {
      case 'fair': return '#16A34A55';
      case 'moderate': return '#EAB30866';
      case 'high': return '#EA580C66';
      case 'critical': return '#DC262666';
      default: return '#6B728055';
    }
  };

  return (
    <div className="bg-card rounded-2xl shadow-sm border border-border p-6 mb-6 animate-fade-in">
      <h2 className="text-lg font-semibold text-text mb-4">Price Comparison</h2>
      <div className="flex flex-wrap gap-3 text-xs text-text-light mb-5">
        <LegendItem color="#DC262666" label="Your Charge" />
        <LegendItem color="#16A34A" label="Fair Price Target" />
        <LegendItem color="#BBF7D0" label="Fair Price Range" />
        <LegendItem color="#2563EB" label="Medicare Rate" dashed />
      </div>
      <div className="space-y-2">
        {chartData.map((item) => (
          <div key={item.cpt} className="grid gap-4 md:grid-cols-[220px_minmax(0,1fr)] md:items-center p-3 rounded-xl hover:bg-slate-50 even:bg-slate-50/40 transition-colors">
            <div>
              <p className="font-medium text-sm text-text">{item.name}</p>
              <p className="text-xs text-text-light">CPT {item.cpt}</p>
            </div>
            <div>
              <div className="relative h-14 rounded-xl border border-border bg-slate-50 overflow-hidden">
                <div
                  className="absolute top-1/2 -translate-y-1/2 left-0 h-10 rounded-r-xl z-10"
                  style={{ width: widthFor(item.charged), backgroundColor: getChargedFill(item.severity) }}
                />
                <div
                  className="absolute top-1/2 -translate-y-1/2 h-8 rounded-xl z-20 bg-green-200/80"
                  style={{ left: leftFor(item.fairLow), width: widthFor(Math.max((item.fairHigh || 0) - (item.fairLow || 0), 0)) }}
                />
                <div
                  className="absolute top-1/2 -translate-y-1/2 left-0 h-4 rounded-r-xl z-30 bg-green-600"
                  style={{ width: widthFor(item.fairPrice) }}
                />
                <div
                  className="absolute inset-y-1 z-40 border-l-2 border-dashed border-blue-600"
                  style={{ left: leftFor(item.medicare) }}
                />
              </div>
              <div className="mt-2 flex flex-wrap gap-3 text-xs text-text-light">
                <span className="font-medium text-danger">Charged {formatCurrency(item.charged)}</span>
                <span className="font-medium text-success">Fair {formatCurrency(item.fairPrice)}</span>
                <span>Range {formatCurrency(item.fairLow)} - {formatCurrency(item.fairHigh)}</span>
                <span className="text-primary">Medicare {formatCurrency(item.medicare)}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function LegendItem({ color, label, dashed = false }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span
        className={`inline-block w-5 ${dashed ? 'border-t-2 border-dashed' : 'h-3 rounded-sm'}`}
        style={dashed ? { borderColor: color } : { backgroundColor: color }}
      />
      {label}
    </span>
  );
}
