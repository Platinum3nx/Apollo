import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_URL,
  timeout: 120000, // 2 min timeout for Gemini calls
});

export async function analyzeBill(file, state = 'VA', facilityType = 'non_facility') {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('state', state);
  formData.append('facility_type', facilityType);

  const response = await api.post('/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function generateLetter(parsedBill, selectedBenchmarks, selectedErrors, patientState = 'VA', additionalContext = '') {
  const response = await api.post('/generate-letter', {
    parsed_bill: parsedBill,
    selected_benchmarks: selectedBenchmarks,
    selected_errors: selectedErrors,
    patient_state: patientState,
    additional_context: additionalContext,
  });
  return response.data;
}

export async function lookupCpt(cptCode) {
  const response = await api.get(`/lookup/${cptCode}`);
  return response.data;
}

export async function searchCpt(query, limit = 20) {
  const response = await api.get('/search-cpt', {
    params: { q: query, limit },
  });
  return response.data;
}

export async function getStateLaws(stateCode) {
  const response = await api.get(`/state-laws/${stateCode}`);
  return response.data;
}

export default api;
