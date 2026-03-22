import { useState, useCallback, useEffect, useMemo } from 'react';
import { generateLetter } from '../api/client';
import { formatCurrency } from '../utils/formatters';

function slugify(value) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
}

export default function DisputeLetter({ letter, parsedBill, benchmarks, errors, patientState }) {
  const [copied, setCopied] = useState(false);
  const [editorOpen, setEditorOpen] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [pdfError, setPdfError] = useState(null);
  const [regenerating, setRegenerating] = useState(false);
  const [regenerateError, setRegenerateError] = useState(null);
  const [currentLetter, setCurrentLetter] = useState(letter);
  const flaggedBenchmarks = useMemo(
    () => benchmarks.filter((benchmark) => ['moderate', 'high', 'critical'].includes(benchmark.severity)),
    [benchmarks]
  );
  const [selectedBenchmarkIds, setSelectedBenchmarkIds] = useState([]);
  const [selectedErrorIds, setSelectedErrorIds] = useState([]);
  const [draftLetter, setDraftLetter] = useState(letter);

  useEffect(() => {
    setCurrentLetter(letter);
    setDraftLetter(letter);
  }, [letter]);

  useEffect(() => {
    setSelectedBenchmarkIds(flaggedBenchmarks.map((benchmark) => benchmark.line_item_id));
  }, [flaggedBenchmarks]);

  useEffect(() => {
    setSelectedErrorIds(errors.map((error) => error.id));
  }, [errors]);

  const selectedBenchmarks = flaggedBenchmarks.filter((benchmark) => selectedBenchmarkIds.includes(benchmark.line_item_id));
  const selectedErrors = errors.filter((error) => selectedErrorIds.includes(error.id));

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(currentLetter);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement('textarea');
      textarea.value = currentLetter;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [currentLetter]);

  const handleDownloadPdf = useCallback(async () => {
    setPdfError(null);
    setDownloadingPdf(true);

    try {
      const { jsPDF } = await import('jspdf');
      const doc = new jsPDF({ unit: 'pt', format: 'letter' });
      const margin = 54;
      const lineHeight = 18;
      const pageWidth = doc.internal.pageSize.getWidth();
      const pageHeight = doc.internal.pageSize.getHeight();
      const maxWidth = pageWidth - margin * 2;
      const lines = doc.splitTextToSize(currentLetter, maxWidth);
      let y = margin;

      doc.setFont('times', 'normal');
      doc.setFontSize(12);

      for (const line of lines) {
        if (y > pageHeight - margin) {
          doc.addPage();
          y = margin;
        }
        doc.text(line, margin, y);
        y += lineHeight;
      }

      const patientName = parsedBill?.patient?.name || 'patient';
      doc.save(`${slugify(patientName)}-apollo-dispute-letter.pdf`);
    } catch (error) {
      setPdfError(error.message || 'Could not create the PDF.');
    } finally {
      setDownloadingPdf(false);
    }
  }, [currentLetter, parsedBill]);

  const toggleBenchmark = useCallback((lineItemId) => {
    setSelectedBenchmarkIds((current) =>
      current.includes(lineItemId)
        ? current.filter((id) => id !== lineItemId)
        : [...current, lineItemId]
    );
  }, []);

  const toggleError = useCallback((errorId) => {
    setSelectedErrorIds((current) =>
      current.includes(errorId)
        ? current.filter((id) => id !== errorId)
        : [...current, errorId]
    );
  }, []);

  const handleRegenerate = useCallback(async () => {
    setRegenerateError(null);
    setRegenerating(true);
    try {
      const context = draftLetter.trim()
        ? `Please use the following edited draft as wording guidance while preserving factual accuracy and only the selected issues:\n\n${draftLetter.trim()}`
        : '';
      const response = await generateLetter(
        parsedBill,
        selectedBenchmarks,
        selectedErrors,
        patientState,
        context
      );
      setCurrentLetter(response.dispute_letter);
      setDraftLetter(response.dispute_letter);
      setEditorOpen(false);
    } catch (error) {
      setRegenerateError(error.response?.data?.detail || error.message || 'Could not regenerate the letter.');
    } finally {
      setRegenerating(false);
    }
  }, [draftLetter, parsedBill, patientState, selectedBenchmarks, selectedErrors]);

  if (!currentLetter) return null;

  return (
    <div className="bg-card rounded-2xl shadow-sm border border-border p-6 mb-6 animate-fade-in">
      <h2 className="text-lg font-semibold text-text mb-4">Dispute Letter</h2>

      {/* Letter content */}
      <div className="bg-white border border-border rounded-xl p-8 shadow-inner mb-4 max-h-[600px] overflow-y-auto">
        <pre className="whitespace-pre-wrap font-serif text-sm leading-relaxed text-text">{currentLetter}</pre>
      </div>

      {/* Action buttons */}
      <div className="flex flex-wrap gap-3">
        <button
          onClick={handleDownloadPdf}
          disabled={downloadingPdf}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors text-sm font-medium"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 16v-8m0 8l-3-3m3 3l3-3M5 20h14" />
          </svg>
          {downloadingPdf ? 'Preparing PDF...' : 'Download PDF'}
        </button>
        <button
          onClick={handleCopy}
          className="flex items-center gap-2 px-4 py-2 border border-border rounded-lg hover:bg-bg transition-colors text-sm font-medium"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          {copied ? 'Copied!' : 'Copy to Clipboard'}
        </button>
        <button
          onClick={() => setEditorOpen((open) => !open)}
          className="flex items-center gap-2 px-4 py-2 border border-border rounded-lg hover:bg-bg transition-colors text-sm font-medium"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M11 5h2m-1 0v14m-7-4h14" />
          </svg>
          {editorOpen ? 'Close Editor' : 'Edit & Regenerate'}
        </button>
      </div>

      {editorOpen && (
        <div className="mt-5 border border-border rounded-2xl p-5 bg-bg">
          <h3 className="text-base font-semibold text-text mb-1">Edit & Regenerate</h3>
          <p className="text-sm text-text-light mb-4">
            Choose which issues to include, then adjust the draft below. Apollo will regenerate the letter from the selected facts and your wording guidance.
          </p>

          <div className="grid gap-4 md:grid-cols-2 mb-4">
            <div className="bg-white border border-border rounded-xl p-4">
              <h4 className="text-sm font-semibold text-text mb-3">Pricing Issues</h4>
              <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
                {flaggedBenchmarks.map((benchmark) => (
                  <label key={benchmark.line_item_id} className="flex items-start gap-3 text-sm">
                    <input
                      type="checkbox"
                      checked={selectedBenchmarkIds.includes(benchmark.line_item_id)}
                      onChange={() => toggleBenchmark(benchmark.line_item_id)}
                      className="mt-0.5"
                    />
                    <span>
                      <span className="font-medium text-text">CPT {benchmark.cpt_code}</span>
                      <span className="text-text-light"> · {benchmark.description}</span>
                      <span className="block text-xs text-success">
                        Charged {formatCurrency(benchmark.charged)} vs fair {formatCurrency(benchmark.fair_price_mid)}
                      </span>
                    </span>
                  </label>
                ))}
              </div>
            </div>

            <div className="bg-white border border-border rounded-xl p-4">
              <h4 className="text-sm font-semibold text-text mb-3">Billing Errors</h4>
              <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
                {errors.map((error) => (
                  <label key={error.id} className="flex items-start gap-3 text-sm">
                    <input
                      type="checkbox"
                      checked={selectedErrorIds.includes(error.id)}
                      onChange={() => toggleError(error.id)}
                      className="mt-0.5"
                    />
                    <span>
                      <span className="font-medium text-text">{error.title}</span>
                      <span className="block text-xs text-danger">
                        Estimated correction {formatCurrency(error.estimated_overcharge)}
                      </span>
                    </span>
                  </label>
                ))}
              </div>
            </div>
          </div>

          <label className="block text-sm font-medium text-text mb-2">Letter Draft / Guidance</label>
          <textarea
            value={draftLetter}
            onChange={(event) => setDraftLetter(event.target.value)}
            rows={16}
            className="w-full rounded-xl border border-border bg-white p-4 text-sm font-serif leading-relaxed focus:outline-none focus:ring-2 focus:ring-primary"
          />

          {regenerateError && (
            <div className="mt-3 p-3 bg-danger-light rounded-lg text-danger text-sm">
              {regenerateError}
            </div>
          )}

          <div className="mt-4 flex flex-wrap justify-end gap-3">
            <button
              onClick={() => setEditorOpen(false)}
              className="px-4 py-2 border border-border rounded-lg hover:bg-white transition-colors text-sm font-medium"
            >
              Cancel
            </button>
            <button
              onClick={handleRegenerate}
              disabled={regenerating}
              className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors text-sm font-medium disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {regenerating ? 'Regenerating...' : 'Regenerate Letter'}
            </button>
          </div>
        </div>
      )}

      {pdfError && (
        <div className="mt-3 p-3 bg-danger-light rounded-lg text-danger text-sm">
          {pdfError}
        </div>
      )}
    </div>
  );
}
