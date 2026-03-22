export function formatCurrency(amount) {
  if (amount == null) return 'N/A';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
}

export function formatPercent(value) {
  if (value == null) return 'N/A';
  return `${Math.round(value * 100)}%`;
}

export function severityColor(severity) {
  switch (severity) {
    case 'fair': return { bg: 'bg-green-100', text: 'text-green-800', border: 'border-green-300', dot: 'bg-green-500' };
    case 'moderate': return { bg: 'bg-yellow-100', text: 'text-yellow-800', border: 'border-yellow-300', dot: 'bg-yellow-500' };
    case 'high': return { bg: 'bg-orange-100', text: 'text-orange-800', border: 'border-orange-300', dot: 'bg-orange-500' };
    case 'critical': return { bg: 'bg-red-100', text: 'text-red-800', border: 'border-red-300', dot: 'bg-red-500' };
    default: return { bg: 'bg-gray-100', text: 'text-gray-800', border: 'border-gray-300', dot: 'bg-gray-500' };
  }
}

export function severityLabel(severity) {
  switch (severity) {
    case 'fair': return 'Fair';
    case 'moderate': return 'Overcharged';
    case 'high': return 'High Overcharge';
    case 'critical': return 'Critical Overcharge';
    default: return 'Unknown';
  }
}

export function errorTypeColor(type) {
  switch (type) {
    case 'duplicate': return { bg: 'bg-red-100', text: 'text-red-800' };
    case 'unbundling': return { bg: 'bg-orange-100', text: 'text-orange-800' };
    case 'upcoding': return { bg: 'bg-purple-100', text: 'text-purple-800' };
    case 'unlikely_combination': return { bg: 'bg-amber-100', text: 'text-amber-800' };
    case 'questionable_charge': return { bg: 'bg-yellow-100', text: 'text-yellow-800' };
    default: return { bg: 'bg-gray-100', text: 'text-gray-800' };
  }
}

export function errorTypeLabel(type) {
  switch (type) {
    case 'duplicate': return 'Duplicate';
    case 'unbundling': return 'Unbundling';
    case 'upcoding': return 'Upcoding';
    case 'unlikely_combination': return 'Unlikely Combo';
    case 'questionable_charge': return 'Questionable';
    default: return type;
  }
}

export function categoryColor(category) {
  switch (category) {
    case 'balance_billing': return { bg: 'bg-blue-100', text: 'text-blue-800' };
    case 'surprise_billing': return { bg: 'bg-purple-100', text: 'text-purple-800' };
    case 'price_transparency': return { bg: 'bg-teal-100', text: 'text-teal-800' };
    case 'dispute_rights': return { bg: 'bg-green-100', text: 'text-green-800' };
    case 'payment_plan': return { bg: 'bg-indigo-100', text: 'text-indigo-800' };
    default: return { bg: 'bg-gray-100', text: 'text-gray-800' };
  }
}

export function categoryLabel(category) {
  switch (category) {
    case 'balance_billing': return 'Balance Billing';
    case 'surprise_billing': return 'Surprise Billing';
    case 'price_transparency': return 'Price Transparency';
    case 'dispute_rights': return 'Dispute Rights';
    case 'payment_plan': return 'Payment Plan';
    default: return category;
  }
}
