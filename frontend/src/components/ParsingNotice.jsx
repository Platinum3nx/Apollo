export default function ParsingNotice({ parsedBill }) {
  const confidence = parsedBill?.parsing_confidence;
  if (confidence == null || confidence >= 0.75) {
    return null;
  }

  const inferredCount = (parsedBill?.line_items || []).filter((item) => item.cpt_inferred).length;

  return (
    <div className="bg-warning-light border border-orange-200 rounded-2xl p-4 mb-6 animate-fade-in">
      <h2 className="text-sm font-semibold text-orange-900 mb-1">Review This Parse Carefully</h2>
      <p className="text-sm text-orange-900/80">
        Apollo extracted this bill with {Math.round(confidence * 100)}% confidence.
        {inferredCount > 0 ? ` ${inferredCount} CPT code${inferredCount === 1 ? '' : 's'} were inferred by AI.` : ''}
        Verify the dates, codes, and totals before sending the dispute letter.
      </p>
    </div>
  );
}
