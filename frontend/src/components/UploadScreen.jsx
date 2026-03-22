import { useCallback, useRef, useState } from 'react';
import CaduceusIcon from './CaduceusIcon';

const SAMPLE_BILLS = [
  { id: 'a', label: 'ER Visit with Labs', desc: 'Has billing errors', file: '/sample-bills/sample-a.png' },
  { id: 'b', label: 'Routine Checkup', desc: 'Has overcharges', file: '/sample-bills/sample-b.png' },
  { id: 'c', label: 'Clean Bill', desc: 'Passes all checks', file: '/sample-bills/sample-c.png' },
];

const US_STATES = [
  'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA',
  'KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
  'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT',
  'VA','WA','WV','WI','WY','DC'
];

export default function UploadScreen({ onFileSelect, onAnalyze, file, preview, error, state, setState, facilityType, setFacilityType }) {
  const inputRef = useRef(null);
  const [isDragActive, setIsDragActive] = useState(false);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragActive(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) {
      onFileSelect(dropped);
      onAnalyze(dropped);
    }
  }, [onFileSelect, onAnalyze]);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragActive(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragActive(false);
  }, []);

  const handleFileInput = useCallback((e) => {
    const selected = e.target.files[0];
    if (selected) {
      onFileSelect(selected);
      onAnalyze(selected);
    }
  }, [onFileSelect, onAnalyze]);

  const handleSampleClick = useCallback(async (sample) => {
    try {
      const response = await fetch(sample.file);
      const blob = await response.blob();
      const sampleFile = new File([blob], `${sample.id}.png`, { type: 'image/png' });
      onFileSelect(sampleFile);
      onAnalyze(sampleFile, true, sample.id);
    } catch {
      // Fallback if image fails to load during offline mode
      onFileSelect({ name: `${sample.label} (Mock)` });
      onAnalyze(null, true, sample.id);
    }
  }, [onFileSelect, onAnalyze]);

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ background: 'linear-gradient(135deg, #EFF6FF 0%, #F0FDF4 100%)' }}>
      <div className="w-full max-w-2xl">
        {/* Logo and tagline */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-3 mb-3">
            <div className="w-12 h-12 bg-primary rounded-xl flex items-center justify-center">
              <CaduceusIcon className="w-7 h-7 text-white" />
            </div>
            <h1 className="text-4xl font-bold text-text">Apollo</h1>
          </div>
          <p className="text-lg text-text-light">Get a second opinion on your medical bill.</p>
        </div>

        {/* Upload card */}
        <div className="bg-card rounded-2xl shadow-lg border border-border p-8">
          {/* Settings row */}
          <div className="flex gap-4 mb-6">
            <div className="flex-1">
              <label className="block text-sm font-medium text-text-light mb-1">Your State</label>
              <select
                value={state}
                onChange={(e) => setState(e.target.value)}
                className="w-full border border-border rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {US_STATES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium text-text-light mb-1">Facility Type</label>
              <select
                value={facilityType}
                onChange={(e) => setFacilityType(e.target.value)}
                className="w-full border border-border rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="non_facility">Office / Outpatient</option>
                <option value="facility">Hospital / Facility</option>
              </select>
            </div>
          </div>

          {/* Drop zone */}
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => inputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-200 active:scale-[0.99]
              ${isDragActive 
                ? 'border-primary bg-primary/5 ring-4 ring-primary/10' 
                : 'border-blue-300 hover:border-primary hover:bg-blue-50/50'}`}
          >
            <input
              ref={inputRef}
              type="file"
              accept="image/png,image/jpeg,image/jpg,application/pdf"
              onChange={handleFileInput}
              className="hidden"
            />
            {preview ? (
              <div>
                <img src={preview} alt="Bill preview" className="max-h-48 mx-auto rounded-lg mb-3" />
                <p className="text-sm text-text-light">{file?.name}</p>
              </div>
            ) : (
              <>
                <svg className="w-12 h-12 mx-auto text-blue-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                </svg>
                <p className="text-lg font-medium text-text mb-1">Drop your bill here or click to upload</p>
                <p className="text-sm text-text-light">Supports PNG, JPG, PDF</p>
              </>
            )}
          </div>

          {error && (
            <div className="mt-6 flex items-start gap-3 p-4 bg-orange-50 border border-orange-200 rounded-xl text-orange-800 text-sm">
              <svg className="w-5 h-5 text-orange-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <div>
                <p className="font-semibold text-orange-900 mb-1">Upload failed</p>
                <p>{error}</p>
                <p className="mt-2 text-xs text-orange-700/80">Tip: Click "Try a sample bill" below to see a demo without the backend.</p>
              </div>
            </div>
          )}

          {/* Sample bills */}
          <div className="mt-6">
            <p className="text-sm text-text-light text-center mb-3">Or try a sample bill:</p>
            <div className="grid grid-cols-3 gap-3">
              {SAMPLE_BILLS.map((sample) => (
                <button
                  key={sample.id}
                  onClick={() => handleSampleClick(sample)}
                  className="p-3 border border-border rounded-lg hover:border-primary hover:bg-blue-50/50 transition-colors text-left"
                >
                  <p className="text-sm font-medium text-text">{sample.label}</p>
                  <p className="text-xs text-text-light mt-0.5">{sample.desc}</p>
                </button>
              ))}
            </div>
          </div>
        </div>

        <p className="text-center text-xs text-text-light mt-4">
          Apollo uses AI to analyze your bill. Results are estimates and should be verified.
        </p>
      </div>
    </div>
  );
}
