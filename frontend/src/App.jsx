import { useState } from 'react';
import { useAnalysis } from './hooks/useAnalysis';
import UploadScreen from './components/UploadScreen';
import LoadingScreen from './components/LoadingScreen';
import ResultsDashboard from './components/ResultsDashboard';
import CptExplorer from './components/CptExplorer';

const TABS = [
  { id: 'analyze', label: 'Analyze Bill' },
  { id: 'explore', label: 'Price Explorer' },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('analyze');
  const analysis = useAnalysis();
  const handleNewAnalysis = () => {
    setActiveTab('analyze');
    analysis.reset();
  };

  return (
    <div className="min-h-screen">
      {/* Navigation - hidden during loading for cleaner animation */}
      {!analysis.isAnalyzing && (
        <nav className="sticky top-0 z-20 bg-card border-b border-border">
          <div className="max-w-5xl mx-auto px-4 flex items-center justify-between h-14">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <span className="font-bold text-text">Apollo</span>
            </div>
            <div className="flex items-center gap-2">
              {analysis.results && (
                <button
                  onClick={handleNewAnalysis}
                  className="px-3 py-1.5 border border-border rounded-lg text-sm font-medium hover:bg-bg transition-colors mr-2"
                >
                  New Analysis
                </button>
              )}
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    activeTab === tab.id
                      ? 'bg-primary text-white'
                      : 'text-text-light hover:bg-bg'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>
        </nav>
      )}

      {/* Content */}
      {activeTab === 'explore' ? (
        <CptExplorer />
      ) : analysis.results ? (
        <ResultsDashboard results={analysis.results} />
      ) : analysis.isAnalyzing ? (
        <LoadingScreen />
      ) : (
        <UploadScreen
          onFileSelect={analysis.handleFileSelect}
          onAnalyze={analysis.analyze}
          file={analysis.file}
          preview={analysis.preview}
          error={analysis.error}
          state={analysis.state}
          setState={analysis.setState}
          facilityType={analysis.facilityType}
          setFacilityType={analysis.setFacilityType}
        />
      )}
    </div>
  );
}
