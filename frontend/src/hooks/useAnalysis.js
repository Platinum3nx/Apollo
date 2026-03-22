import { useState, useCallback } from 'react';
import { analyzeBill } from '../api/client';

export function useAnalysis() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [state, setState] = useState('VA');
  const [facilityType, setFacilityType] = useState('non_facility');

  const handleFileSelect = useCallback((selectedFile) => {
    setFile(selectedFile);
    setError(null);
    setResults(null);

    if (selectedFile && selectedFile.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => setPreview(e.target.result);
      reader.readAsDataURL(selectedFile);
    } else {
      setPreview(null);
    }
  }, []);

  const analyze = useCallback(async (fileToAnalyze) => {
    const targetFile = fileToAnalyze || file;
    if (!targetFile) {
      setError('Please select a file to analyze.');
      return;
    }

    setIsAnalyzing(true);
    setError(null);
    setResults(null);

    try {
      const data = await analyzeBill(targetFile, state, facilityType);
      setResults(data);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Analysis failed. Please try again.';
      setError(msg);
    } finally {
      setIsAnalyzing(false);
    }
  }, [file, state, facilityType]);

  const reset = useCallback(() => {
    setFile(null);
    setPreview(null);
    setIsAnalyzing(false);
    setResults(null);
    setError(null);
  }, []);

  return {
    file,
    preview,
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
