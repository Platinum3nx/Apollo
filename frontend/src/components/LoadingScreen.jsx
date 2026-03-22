import { useState, useEffect } from 'react';

const STEPS = [
  { label: 'Reading your bill...', icon: '1' },
  { label: 'Identifying procedure codes...', icon: '2' },
  { label: 'Checking fair market prices...', icon: '3' },
  { label: 'Scanning for billing errors...', icon: '4' },
  { label: 'Looking up your state protections...', icon: '5' },
  { label: 'Generating your report...', icon: '6' },
];

export default function LoadingScreen() {
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentStep((prev) => {
        if (prev < STEPS.length - 1) return prev + 1;
        return prev;
      });
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ background: 'linear-gradient(135deg, #EFF6FF 0%, #F0FDF4 100%)' }}>
      <div className="w-full max-w-md text-center">
        {/* Logo with pulse */}
        <div className="mb-8">
          <div className="inline-flex items-center gap-3 animate-pulse-soft">
            <div className="w-12 h-12 bg-primary rounded-xl flex items-center justify-center">
              <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h1 className="text-3xl font-bold text-text">Apollo</h1>
          </div>
        </div>

        {/* Progress steps */}
        <div className="bg-card rounded-2xl shadow-lg border border-border p-6">
          <div className="space-y-3">
            {STEPS.map((step, index) => (
              <div
                key={index}
                className={`flex items-center gap-3 p-3 rounded-lg transition-all duration-500 ${
                  index === currentStep
                    ? 'bg-blue-50 border border-primary/20'
                    : index < currentStep
                    ? 'opacity-60'
                    : 'opacity-30'
                }`}
              >
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium shrink-0 ${
                  index < currentStep
                    ? 'bg-success text-white'
                    : index === currentStep
                    ? 'bg-primary text-white'
                    : 'bg-gray-200 text-gray-500'
                }`}>
                  {index < currentStep ? (
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    step.icon
                  )}
                </div>
                <span className={`text-sm ${index === currentStep ? 'font-medium text-text' : 'text-text-light'}`}>
                  {step.label}
                </span>
                {index === currentStep && (
                  <div className="ml-auto">
                    <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Progress bar */}
          <div className="mt-6 bg-gray-200 rounded-full h-2 overflow-hidden">
            <div
              className="bg-primary h-full rounded-full transition-all duration-500 ease-out"
              style={{ width: `${((currentStep + 1) / STEPS.length) * 100}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
