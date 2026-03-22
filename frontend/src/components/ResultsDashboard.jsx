import SavingsSummary from './SavingsSummary';
import BillSummary from './BillSummary';
import PriceComparison from './PriceComparison';
import ErrorPanel from './ErrorPanel';
import StateLawPanel from './StateLawPanel';
import DisputeLetter from './DisputeLetter';
import ParsingNotice from './ParsingNotice';

export default function ResultsDashboard({ results }) {
  const { parsed_bill, benchmarks, errors, dispute_letter, state_laws, federal_laws, summary, patient_state } = results;

  // Try to get state name from state_laws data
  const stateName = state_laws?.[0]?.state_name || null;
  const patientState = patient_state || state_laws?.[0]?.state_code || 'VA';

  return (
    <div className="bg-bg">
      <div className="max-w-5xl mx-auto p-6">
        <ParsingNotice parsedBill={parsed_bill} />
        <SavingsSummary summary={summary} />
        <BillSummary parsedBill={parsed_bill} benchmarks={benchmarks} errors={errors} summary={summary} />
        <PriceComparison benchmarks={benchmarks} />
        <ErrorPanel errors={errors} />
        <StateLawPanel stateLaws={state_laws} federalLaws={federal_laws} stateName={stateName} />
        <DisputeLetter
          letter={dispute_letter}
          parsedBill={parsed_bill}
          benchmarks={benchmarks}
          errors={errors}
          patientState={patientState}
        />
      </div>
    </div>
  );
}
