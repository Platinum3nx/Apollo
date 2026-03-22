import { useState, useEffect } from 'react';
import { formatCurrency } from '../utils/formatters';

export default function SavingsSummary({ summary }) {
  const [displayAmount, setDisplayAmount] = useState(0);
  const target = summary.total_potential_savings || 0;

  useEffect(() => {
    if (target === 0) return;
    const duration = 1500;
    const steps = 60;
    const increment = target / steps;
    let current = 0;
    const timer = setInterval(() => {
      current += increment;
      if (current >= target) {
        setDisplayAmount(target);
        clearInterval(timer);
      } else {
        setDisplayAmount(current);
      }
    }, duration / steps);
    return () => clearInterval(timer);
  }, [target]);

  return (
    <div className="rounded-2xl p-6 text-white mb-6 animate-fade-in" style={{ background: 'linear-gradient(135deg, #16A34A 0%, #2563EB 100%)' }}>
      <div className="text-center">
        <p className="text-green-100 text-sm font-medium mb-1">Apollo found</p>
        <p className="text-5xl font-bold mb-2">{formatCurrency(displayAmount)}</p>
        <p className="text-green-100 text-sm">in potential savings</p>
      </div>

      <div className="flex justify-center gap-6 mt-4 text-sm">
        <span>{summary.items_flagged} items flagged</span>
        <span className="opacity-50">|</span>
        <span>{summary.errors_found} billing errors</span>
        <span className="opacity-50">|</span>
        <span>{summary.items_fair} items fair</span>
      </div>

      <div className="flex justify-center gap-4 mt-4">
        <span className="bg-white/20 px-3 py-1 rounded-full text-xs">
          Overcharges: {formatCurrency(summary.savings_from_overcharges)}
        </span>
        <span className="bg-white/20 px-3 py-1 rounded-full text-xs">
          Errors: {formatCurrency(summary.savings_from_errors)}
        </span>
      </div>
    </div>
  );
}
