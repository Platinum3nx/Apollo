import { useCallback, useEffect, useState } from 'react';
import { analyzeBill } from '../api/client';

function buildPreviewItem(selectedFile, index) {
  const isBlob = typeof Blob !== 'undefined' && selectedFile instanceof Blob;
  const isImage = isBlob && selectedFile.type?.startsWith('image/');

  return {
    id: `${selectedFile.name || 'file'}-${selectedFile.lastModified || 'mock'}-${index}`,
    kind: isImage ? 'image' : selectedFile.type === 'application/pdf' ? 'pdf' : 'file',
    name: selectedFile.name || `File ${index + 1}`,
    size: typeof selectedFile.size === 'number' ? selectedFile.size : null,
    previewUrl: isImage ? URL.createObjectURL(selectedFile) : null,
  };
}

export function useAnalysis() {
  const [files, setFiles] = useState([]);
  const [previews, setPreviews] = useState([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [state, setState] = useState('VA');
  const [facilityType, setFacilityType] = useState('non_facility');

  useEffect(() => {
    return () => {
      previews.forEach((preview) => {
        if (preview.previewUrl) {
          URL.revokeObjectURL(preview.previewUrl);
        }
      });
    };
  }, [previews]);

  const handleFileSelect = useCallback((selectedInput) => {
    const selectedFiles = Array.isArray(selectedInput)
      ? selectedInput.filter(Boolean)
      : selectedInput
        ? [selectedInput]
        : [];

    setFiles(selectedFiles);
    setError(null);
    setResults(null);
    setPreviews(selectedFiles.map(buildPreviewItem));
  }, []);

  const analyze = useCallback(async (filesToAnalyze, isMock = false, mockId = null) => {
    const targetFiles = Array.isArray(filesToAnalyze)
      ? filesToAnalyze
      : filesToAnalyze
        ? [filesToAnalyze]
        : files;

    if (targetFiles.length === 0 && !isMock) {
      setError('Please select at least one file to analyze.');
      return;
    }

    setIsAnalyzing(true);
    setError(null);
    setResults(null);

    try {
      if (isMock && mockId) {
        const response = await fetch(`/mock/sample-${mockId}-results.json`);
        if (!response.ok) throw new Error('Failed to load mock data');
        
        // Artificial delay to demonstrate loading screen in demo
        await new Promise(resolve => setTimeout(resolve, 2500));
        
        const data = await response.json();
        setResults(data);
      } else {
        const data = await analyzeBill(targetFiles, state, facilityType);
        setResults(data);
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Analysis failed. Please try again.';
      setError(msg);
    } finally {
      setIsAnalyzing(false);
    }
  }, [files, state, facilityType]);

  const reset = useCallback(() => {
    setFiles([]);
    setPreviews([]);
    setIsAnalyzing(false);
    setResults(null);
    setError(null);
  }, []);

  return {
    files,
    previews,
    isAnalyzing,
    results,
    error,
    state,
    facilityType,
    setState,
    setFacilityType,
    handleFileSelect,
    analyze,
    reset,
  };
}
