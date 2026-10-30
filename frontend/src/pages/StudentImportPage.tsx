import React, { useState, useEffect } from 'react';
import {
  Upload,
  FileSpreadsheet,
  Download,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
  Edit2,
  Trash2,
  Check,
  ChevronRight,
  ChevronLeft,
  FileText,
  Clock,
  History,
  ShieldCheck,
  Layers,
  ArrowUpRight,
  Database
} from 'lucide-react';
import {
  BulkDryRunResult,
  BulkDryRunRowError,
  BulkCommitSummary,
  BulkUploadJob,
  StagedErrorRow,
  ImportBatchResult
} from '../types';
import {
  getCsvTemplateUrl,
  validateBulkUpload,
  commitBulkUpload,
  fetchUploadJobs,
  getJobErrorExportUrl,
  resolveBatchErrors
} from '../services/api';
import { Badge } from '../components/Badge';

interface StudentImportPageProps {
  institutionId?: string;
  initialTab?: 'wizard' | 'history';
  onViewRoster: () => void;
}

// Target schema fields for column mapping
const TARGET_FIELDS: Array<{ key: string; label: string; required: boolean; description: string }> = [
  { key: 'internal_id', label: 'Roll / Internal Student ID', required: true, description: 'Institutional unique identifier' },
  { key: 'student_name', label: 'Student Full Name', required: true, description: 'Official legal name' },
  { key: 'apaar_id', label: '12-Digit APAAR ID', required: true, description: 'Verhoeff checksum checked' },
  { key: 'course', label: 'Course Allocation', required: true, description: 'AICTE approved course title' },
  { key: 'date_of_birth', label: 'Date of Birth (YYYY-MM-DD)', required: true, description: 'Standard ISO format' },
  { key: 'gender', label: 'Gender', required: false, description: 'MALE, FEMALE, or OTHER' },
  { key: 'category', label: 'Social Category', required: false, description: 'GENERAL, OBC, SC, ST, EWS' },
  { key: 'academic_year', label: 'Academic Session', required: false, description: 'e.g. 2024-2025' },
  { key: 'admission_year', label: 'Admission Year', required: false, description: 'e.g. 2024' },
  { key: 'is_supernumerary', label: 'Supernumerary Seat (TRUE/FALSE)', required: false, description: 'Outside core approved pool' },
  { key: 'supernumerary_type', label: 'Quota Type', required: false, description: 'TFW, NRI, FOREIGN_NATIONAL' },
  { key: 'nri_status', label: 'NRI Category (TRUE/FALSE)', required: false, description: 'Non-Resident Indian' },
  { key: 'oci_status', label: 'OCI Status (TRUE/FALSE)', required: false, description: 'Overseas Citizen of India' },
  { key: 'foreign_national_status', label: 'Foreign National (TRUE/FALSE)', required: false, description: 'Foreign student status' }
];

export const StudentImportPage: React.FC<StudentImportPageProps> = ({
  institutionId = 'inst-apex-1001',
  initialTab = 'wizard',
  onViewRoster
}) => {
  const [activeMainTab, setActiveMainTab] = useState<'wizard' | 'history'>(initialTab);

  // Wizard state
  const [wizardStep, setWizardStep] = useState<number>(1);
  const [academicYear, setAcademicYear] = useState<string>('2024-2025');
  const [file, setFile] = useState<File | null>(null);
  const [fileReadError, setFileReadError] = useState<string | null>(null);
  const [csvHeaders, setCsvHeaders] = useState<string[]>([]);
  const [parsedRawRows, setParsedRawRows] = useState<any[]>([]);
  const [columnMapping, setColumnMapping] = useState<Record<string, string>>({});

  // Validation state
  const [validating, setValidating] = useState<boolean>(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [dryRunResult, setDryRunResult] = useState<BulkDryRunResult | null>(null);

  // Commit state
  const [committing, setCommitting] = useState<boolean>(false);
  const [commitError, setCommitError] = useState<string | null>(null);
  const [commitSummary, setCommitSummary] = useState<BulkCommitSummary | null>(null);

  // History state
  const [uploadJobs, setUploadJobs] = useState<BulkUploadJob[]>([]);
  const [loadingJobs, setLoadingJobs] = useState<boolean>(false);

  useEffect(() => {
    if (activeMainTab === 'history') {
      loadJobHistory();
    }
  }, [activeMainTab, institutionId]);

  const loadJobHistory = async () => {
    try {
      setLoadingJobs(true);
      const jobs = await fetchUploadJobs(institutionId);
      setUploadJobs(jobs);
    } catch (err) {
      console.error('Failed to load upload history:', err);
    } finally {
      setLoadingJobs(false);
    }
  };

  // Robust CSV parser handling quotes
  const parseCSVLine = (text: string): string[] => {
    const result: string[] = [];
    let cur = '';
    let inQuotes = false;
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (c === '"') {
        if (inQuotes && text[i + 1] === '"') {
          cur += '"';
          i++;
        } else {
          inQuotes = !inQuotes;
        }
      } else if (c === ',' && !inQuotes) {
        result.push(cur.trim());
        cur = '';
      } else {
        cur += c;
      }
    }
    result.push(cur.trim());
    return result;
  };

  // Handle file drop/selection
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (!selected) return;
    setFile(selected);
    setFileReadError(null);

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const text = event.target?.result as string;
        const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
        if (lines.length < 2) {
          setFileReadError('CSV file must contain a header row and at least one student data row.');
          return;
        }

        const headers = parseCSVLine(lines[0]);
        setCsvHeaders(headers);

        const rows: any[] = [];
        for (let i = 1; i < lines.length; i++) {
          const values = parseCSVLine(lines[i]);
          const rowObj: Record<string, string> = {};
          headers.forEach((h, idx) => {
            rowObj[h] = values[idx] || '';
          });
          rows.push(rowObj);
        }
        setParsedRawRows(rows);

        // Pre-fill smart mapping based on header similarity
        const initialMapping: Record<string, string> = {};
        TARGET_FIELDS.forEach((tf) => {
          const match = headers.find(
            (h) =>
              h.toLowerCase() === tf.key.toLowerCase() ||
              h.toLowerCase() === tf.label.toLowerCase() ||
              h.toLowerCase().replace(/[^a-z0-9]/g, '') === tf.key.toLowerCase().replace(/[^a-z0-9]/g, '')
          );
          if (match) {
            initialMapping[tf.key] = match;
          }
        });
        setColumnMapping(initialMapping);
      } catch (err: any) {
        setFileReadError('Failed to parse CSV file: ' + err.message);
      }
    };
    reader.onerror = () => setFileReadError('Could not read the uploaded CSV file.');
    reader.readAsText(selected);
  };

  // Convert raw rows to mapped payload
  const getMappedRows = () => {
    return parsedRawRows.map((row) => {
      const mapped: Record<string, any> = {};
      TARGET_FIELDS.forEach((tf) => {
        const mappedCol = columnMapping[tf.key];
        if (mappedCol && row[mappedCol] !== undefined) {
          mapped[tf.key] = row[mappedCol];
        }
      });
      if (!mapped.academic_year) mapped.academic_year = academicYear;
      return mapped;
    });
  };

  // Step 2 -> Step 3: Run Server-Side Dry-Run Validation
  const handleRunValidation = async () => {
    setValidationError(null);

    const missingRequired = TARGET_FIELDS.filter(
      (tf) => tf.required && (!columnMapping[tf.key] || columnMapping[tf.key] === '__IGNORE__')
    );
    if (missingRequired.length > 0) {
      setValidationError(
        `Please map all mandatory columns: ${missingRequired.map((m) => m.label).join(', ')}`
      );
      return;
    }

    setValidating(true);
    try {
      const mappedRows = getMappedRows();
      const payload = {
        academic_year: academicYear,
        institution_id: institutionId,
        rows: mappedRows
      };

      const result = await validateBulkUpload(payload);
      setDryRunResult(result);
      setWizardStep(3);
    } catch (err: any) {
      setValidationError(err.message || 'Server dry-run validation failed.');
    } finally {
      setValidating(false);
    }
  };

  const handleProceedToConfirmation = () => {
    setWizardStep(4);
  };

  const handleCommitImport = async () => {
    if (!dryRunResult || dryRunResult.valid_rows_count === 0) {
      setCommitError('Cannot commit batch without valid rows.');
      return;
    }

    setCommitting(true);
    setCommitError(null);
    try {
      const mappedRows = getMappedRows();
      const payload = {
        filename: file?.name || 'bulk_students.csv',
        academic_year: academicYear,
        institution_id: institutionId,
        rows: mappedRows
      };

      const summary = await commitBulkUpload(payload);
      setCommitSummary(summary);
      loadJobHistory();
    } catch (err: any) {
      setCommitError(err.message || 'Import commit transaction failed.');
    } finally {
      setCommitting(false);
    }
  };

  const handleDownloadDryRunErrors = () => {
    if (!dryRunResult || dryRunResult.errors.length === 0) return;

    let csv = 'Row Number,Field Name,Error Code,Severity,Error Message\n';
    dryRunResult.errors.forEach((e) => {
      csv += `${e.row_index},"${e.field_name}","${e.error_code}","${e.severity}","${e.error_message.replace(/"/g, '""')}"\n`;
    });

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `validation_errors_${file?.name || 'batch'}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleResetWizard = () => {
    setFile(null);
    setCsvHeaders([]);
    setParsedRawRows([]);
    setColumnMapping({});
    setDryRunResult(null);
    setCommitSummary(null);
    setWizardStep(1);
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fade-in text-[#1C1917]">
      
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#E5E4DF] pb-6">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-serif font-normal text-[#1C1917] tracking-tight">
              Institutional Bulk Data Import & Validation
            </h1>
            <Badge variant="info">AICTE Pipeline</Badge>
          </div>
          <p className="text-xs text-[#78716C] font-serif italic mt-1">
            Automated server-side validation against APAAR Verhoeff checksums, duplicate roll detection, and intake caps.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <a
            href={getCsvTemplateUrl()}
            download="aicte_student_bulk_template.csv"
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-white hover:bg-[#F4F3EE] text-[#1C1917] border border-[#E5E4DF] text-xs font-medium transition-all shadow-sm shrink-0"
          >
            <Download className="w-4 h-4 text-[#78716C]" />
            Standard CSV Template
          </a>
        </div>
      </div>

      {/* Main Mode Tabs */}
      <div className="flex border-b border-[#E5E4DF]">
        <button
          onClick={() => setActiveMainTab('wizard')}
          className={`pb-3 text-sm font-medium border-b-2 transition-all flex items-center gap-2 ${
            activeMainTab === 'wizard'
              ? 'border-[#1C1917] text-[#1C1917] font-semibold'
              : 'border-transparent text-[#78716C] hover:text-[#1C1917]'
          }`}
        >
          <FileSpreadsheet className="w-4 h-4" />
          Bulk Upload Wizard
        </button>
        <button
          onClick={() => setActiveMainTab('history')}
          className={`pb-3 text-sm font-medium border-b-2 transition-all flex items-center gap-2 ml-6 ${
            activeMainTab === 'history'
              ? 'border-[#1C1917] text-[#1C1917] font-semibold'
              : 'border-transparent text-[#78716C] hover:text-[#1C1917]'
          }`}
        >
          <History className="w-4 h-4" />
          Upload Job History & Error Review
        </button>
      </div>

      {/* ========================================================
          MODE 1: BULK UPLOAD WIZARD
         ======================================================== */}
      {activeMainTab === 'wizard' && (
        <div className="space-y-6">
          
          {/* Wizard Step Progress Tracker */}
          <div className="bg-white p-4 rounded-2xl border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.02)]">
            <div className="grid grid-cols-4 gap-2 text-xs">
              <div
                className={`flex items-center gap-2 p-2 rounded-xl transition-all ${
                  wizardStep === 1
                    ? 'bg-[#1C1917] text-white font-medium shadow-sm'
                    : wizardStep > 1
                    ? 'text-[#15803D] font-medium'
                    : 'text-[#A8A29E]'
                }`}
              >
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                    wizardStep > 1 ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-[#FAF9F5] text-[#57534E]'
                  }`}
                >
                  {wizardStep > 1 ? <Check className="w-3.5 h-3.5" /> : '1'}
                </div>
                <span>1. File Selection</span>
              </div>

              <div
                className={`flex items-center gap-2 p-2 rounded-xl transition-all ${
                  wizardStep === 2
                    ? 'bg-[#1C1917] text-white font-medium shadow-sm'
                    : wizardStep > 2
                    ? 'text-[#15803D] font-medium'
                    : 'text-[#A8A29E]'
                }`}
              >
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                    wizardStep > 2 ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-[#FAF9F5] text-[#57534E]'
                  }`}
                >
                  {wizardStep > 2 ? <Check className="w-3.5 h-3.5" /> : '2'}
                </div>
                <span>2. Column Mapping</span>
              </div>

              <div
                className={`flex items-center gap-2 p-2 rounded-xl transition-all ${
                  wizardStep === 3
                    ? 'bg-[#1C1917] text-white font-medium shadow-sm'
                    : wizardStep > 3
                    ? 'text-[#15803D] font-medium'
                    : 'text-[#A8A29E]'
                }`}
              >
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                    wizardStep > 3 ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-[#FAF9F5] text-[#57534E]'
                  }`}
                >
                  {wizardStep > 3 ? <Check className="w-3.5 h-3.5" /> : '3'}
                </div>
                <span>3. Pre-Validation</span>
              </div>

              <div
                className={`flex items-center gap-2 p-2 rounded-xl transition-all ${
                  wizardStep === 4
                    ? 'bg-[#1C1917] text-white font-medium shadow-sm'
                    : 'text-[#A8A29E]'
                }`}
              >
                <div className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium bg-[#FAF9F5] text-[#57534E]">
                  4
                </div>
                <span>4. Confirm & Commit</span>
              </div>
            </div>
          </div>

          {/* STEP 1: File Selection & Parsing */}
          {wizardStep === 1 && (
            <div className="bg-white p-6 sm:p-8 rounded-2xl border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-[#57534E] mb-1">
                    Target Academic Session
                  </label>
                  <select
                    value={academicYear}
                    onChange={(e) => setAcademicYear(e.target.value)}
                    className="w-full bg-[#FAF9F5] border border-[#E5E4DF] rounded-xl px-3 py-2 text-xs text-[#1C1917] focus:outline-none focus:border-[#1C1917]"
                  >
                    <option value="2024-2025">2024-2025 (Current Session)</option>
                    <option value="2023-2024">2023-2024 (Prior Session)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-[#57534E] mb-1">
                    Standard AICTE Roster Format
                  </label>
                  <div className="flex items-center gap-2 text-xs text-[#78716C] py-1.5">
                    <span>Includes 12-digit APAARs, quotas, and demographics.</span>
                  </div>
                </div>
              </div>

              {/* Drag & Drop Area */}
              <div className="border-2 border-dashed border-[#E5E4DF] hover:border-[#1C1917] rounded-2xl p-8 text-center transition-all bg-[#FAF9F5]/60">
                <input
                  type="file"
                  id="csv-wizard-file-input"
                  accept=".csv"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <label
                  htmlFor="csv-wizard-file-input"
                  className="cursor-pointer flex flex-col items-center justify-center gap-3"
                >
                  <div className="w-12 h-12 rounded-xl bg-white border border-[#E5E4DF] flex items-center justify-center text-[#1C1917] shadow-sm">
                    <Upload className="w-6 h-6 text-[#78716C]" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-[#1C1917]">
                      {file ? file.name : 'Click to select or drag and drop student CSV file'}
                    </p>
                    <p className="text-xs text-[#78716C] mt-1 font-serif italic">
                      Supports comma-separated UTF-8 rosters. Headers will be mapped in Step 2.
                    </p>
                  </div>
                </label>
              </div>

              {fileReadError && (
                <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 text-rose-700" />
                  {fileReadError}
                </div>
              )}

              {file && parsedRawRows.length > 0 && (
                <div className="flex items-center justify-between p-4 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF]">
                  <div className="flex items-center gap-3">
                    <FileText className="w-5 h-5 text-[#78716C]" />
                    <div>
                      <p className="text-xs font-medium text-[#1C1917] font-mono">{file.name}</p>
                      <p className="text-[11px] text-[#78716C]">
                        Detected {parsedRawRows.length} student rows • {csvHeaders.length} columns found
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => setWizardStep(2)}
                    className="flex items-center gap-2 px-5 py-2 rounded-xl bg-[#1C1917] hover:bg-[#292524] text-white text-xs font-medium transition-all shadow-sm"
                  >
                    Proceed to Column Mapping
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          )}

          {/* STEP 2: Interactive Column Mapping */}
          {wizardStep === 2 && (
            <div className="bg-white p-6 sm:p-8 rounded-2xl border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-6">
              <div className="flex items-center justify-between border-b border-[#E5E4DF] pb-3">
                <div>
                  <h3 className="text-base font-serif font-medium text-[#1C1917]">Map CSV Headers to AICTE Schema</h3>
                  <p className="text-xs text-[#78716C]">
                    If your CSV headers differ, select which column matches each required target field.
                  </p>
                </div>
                <button
                  onClick={() => setWizardStep(1)}
                  className="flex items-center gap-1 text-xs text-[#78716C] hover:text-[#1C1917]"
                >
                  <ChevronLeft className="w-4 h-4" />
                  Back to File
                </button>
              </div>

              {validationError && (
                <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 text-rose-700" />
                  {validationError}
                </div>
              )}

              <div className="overflow-x-auto rounded-xl border border-[#E5E4DF]">
                <table className="w-full text-left text-xs text-[#57534E]">
                  <thead className="bg-[#FAF9F5] text-[11px] font-medium uppercase tracking-wider text-[#78716C] border-b border-[#E5E4DF]">
                    <tr>
                      <th className="py-3 px-4">Target AICTE Field</th>
                      <th className="py-3 px-4">Description</th>
                      <th className="py-3 px-4">Required</th>
                      <th className="py-3 px-4">Mapped CSV Column</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E5E4DF] font-sans">
                    {TARGET_FIELDS.map((tf) => (
                      <tr key={tf.key} className="hover:bg-[#FAF9F5]">
                        <td className="py-3 px-4 font-serif font-medium text-[#1C1917]">
                          {tf.label}
                        </td>
                        <td className="py-3 px-4 text-[#78716C] text-[11px]">
                          {tf.description}
                        </td>
                        <td className="py-3 px-4">
                          {tf.required ? (
                            <Badge variant="danger">Required</Badge>
                          ) : (
                            <Badge variant="neutral">Optional</Badge>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          <select
                            value={columnMapping[tf.key] || '__IGNORE__'}
                            onChange={(e) =>
                              setColumnMapping({
                                ...columnMapping,
                                [tf.key]: e.target.value
                              })
                            }
                            className="bg-white border border-[#E5E4DF] rounded-lg px-3 py-1.5 text-xs text-[#1C1917] focus:outline-none focus:border-[#1C1917] w-56"
                          >
                            <option value="__IGNORE__">&lt;Ignore / Unmapped&gt;</option>
                            {csvHeaders.map((h, hIdx) => (
                              <option key={hIdx} value={h}>
                                {h}
                              </option>
                            ))}
                          </select>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="flex items-center justify-between pt-2">
                <button
                  onClick={() => setWizardStep(1)}
                  className="px-4 py-2 rounded-xl bg-white border border-[#E5E4DF] text-[#57534E] text-xs font-medium hover:bg-[#F4F3EE]"
                >
                  Previous
                </button>
                <button
                  onClick={handleRunValidation}
                  disabled={validating}
                  className="flex items-center gap-2 px-6 py-2 rounded-xl bg-[#1C1917] hover:bg-[#292524] text-white text-xs font-medium transition-all shadow-sm disabled:opacity-50"
                >
                  {validating ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Running Server-Side Pre-Validation...
                    </>
                  ) : (
                    <>
                      Run Pre-Validation (Dry Run)
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* STEP 3: Server Dry-Run Pre-Validation & Row-Level Error Review */}
          {wizardStep === 3 && dryRunResult && (
            <div className="space-y-6">
              
              {/* Metrics Summary */}
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                <div className="bg-white p-4 rounded-xl border border-[#E5E4DF] shadow-sm">
                  <span className="text-[#78716C] text-xs font-medium">Total Rows Parsed</span>
                  <p className="text-2xl font-serif font-medium text-[#1C1917] mt-1">{dryRunResult.total_rows}</p>
                </div>
                <div className="bg-white p-4 rounded-xl border border-emerald-200 shadow-sm">
                  <span className="text-emerald-800 text-xs font-medium">Valid & Ready to Commit</span>
                  <p className="text-2xl font-serif font-medium text-[#15803D] mt-1">{dryRunResult.valid_rows_count}</p>
                </div>
                <div className="bg-white p-4 rounded-xl border border-rose-200 shadow-sm">
                  <span className="text-rose-800 text-xs font-medium">Invalid / Failed Rows</span>
                  <p className="text-2xl font-serif font-medium text-rose-800 mt-1">{dryRunResult.invalid_rows_count}</p>
                </div>
                <div className="bg-white p-4 rounded-xl border border-amber-200 shadow-sm">
                  <span className="text-amber-800 text-xs font-medium">Duplicate Collisions</span>
                  <p className="text-2xl font-serif font-medium text-amber-900 mt-1">{dryRunResult.duplicate_rows_count}</p>
                </div>
              </div>

              {/* Action Bar */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-white border border-[#E5E4DF] shadow-sm">
                <div>
                  <h3 className="text-sm font-serif font-medium text-[#1C1917]">Pre-Validation Results Summary</h3>
                  <p className="text-xs text-[#78716C]">
                    Review row-level validity before writing any records to the persistent database.
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  {dryRunResult.errors.length > 0 && (
                    <button
                      onClick={handleDownloadDryRunErrors}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-50 hover:bg-rose-100 text-rose-800 text-xs font-medium border border-rose-200 shadow-sm transition-all"
                    >
                      <Download className="w-3.5 h-3.5" />
                      Download Error Report (CSV)
                    </button>
                  )}
                  <button
                    onClick={() => setWizardStep(2)}
                    className="px-3 py-1.5 rounded-xl bg-white border border-[#E5E4DF] text-[#57534E] text-xs font-medium"
                  >
                    Back to Mapping
                  </button>
                  <button
                    onClick={handleProceedToConfirmation}
                    disabled={!dryRunResult.can_commit}
                    className="flex items-center gap-1.5 px-5 py-2 rounded-xl bg-[#1C1917] hover:bg-[#292524] text-white text-xs font-medium transition-all shadow-sm disabled:opacity-50"
                  >
                    Proceed to Commit ({dryRunResult.valid_rows_count} Records)
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Preview of First Rows */}
              <div className="bg-white p-6 rounded-2xl border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-3">
                <h4 className="text-xs font-serif font-medium uppercase tracking-wider text-[#78716C]">
                  Preview of First Records with Pre-Validation Tags
                </h4>
                <div className="overflow-x-auto rounded-xl border border-[#E5E4DF]">
                  <table className="w-full text-left text-xs text-[#57534E]">
                    <thead className="bg-[#FAF9F5] text-[11px] font-medium uppercase tracking-wider text-[#78716C] border-b border-[#E5E4DF]">
                      <tr>
                        <th className="py-2.5 px-3 text-center">Row #</th>
                        <th className="py-2.5 px-3">Roll ID</th>
                        <th className="py-2.5 px-3">Student Name</th>
                        <th className="py-2.5 px-3 font-mono">APAAR ID</th>
                        <th className="py-2.5 px-3">Course</th>
                        <th className="py-2.5 px-3 text-center">Pre-Validation Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#E5E4DF] font-sans">
                      {dryRunResult.preview_rows.map((r, i) => (
                        <tr key={i} className="hover:bg-[#FAF9F5]">
                          <td className="py-2.5 px-3 text-center font-mono text-[#78716C]">{r.row_index}</td>
                          <td className="py-2.5 px-3 font-mono font-medium text-[#1C1917]">{r.internal_id || '-'}</td>
                          <td className="py-2.5 px-3 font-serif font-medium text-[#1C1917]">{r.student_name || '-'}</td>
                          <td className="py-2.5 px-3 font-mono text-[#15803D]">{r.apaar_id || '-'}</td>
                          <td className="py-2.5 px-3 text-[#57534E]">{r.course || '-'}</td>
                          <td className="py-2.5 px-3 text-center">
                            <Badge
                              variant={
                                r._status === 'VALID'
                                  ? 'success'
                                  : r._status === 'DUPLICATE_COLLISION'
                                  ? 'warning'
                                  : 'danger'
                              }
                            >
                              {r._status}
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Row-Level Errors Table */}
              {dryRunResult.errors.length > 0 && (
                <div className="bg-white p-6 rounded-2xl border border-rose-200 space-y-3 shadow-sm">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-serif font-medium uppercase tracking-wider text-rose-800 flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4 text-rose-700" />
                      Row-Level Validation Error Details ({dryRunResult.errors.length} Issues)
                    </h4>
                    <button
                      onClick={handleDownloadDryRunErrors}
                      className="text-xs text-[#C2410C] hover:underline font-medium"
                    >
                      Export Error Report (CSV)
                    </button>
                  </div>

                  <div className="overflow-x-auto rounded-xl border border-[#E5E4DF] max-h-60 overflow-y-auto">
                    <table className="w-full text-left text-xs text-[#57534E]">
                      <thead className="bg-[#FAF9F5] text-[11px] font-medium uppercase tracking-wider text-[#78716C] border-b border-[#E5E4DF] sticky top-0">
                        <tr>
                          <th className="py-2 px-3 text-center">Row</th>
                          <th className="py-2 px-3">Field</th>
                          <th className="py-2 px-3">Severity</th>
                          <th className="py-2 px-3">Error Code</th>
                          <th className="py-2 px-3">Message</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#E5E4DF] font-sans">
                        {dryRunResult.errors.map((err, errIdx) => (
                          <tr key={errIdx} className="hover:bg-[#FAF9F5]">
                            <td className="py-2 px-3 text-center font-mono text-amber-900 font-medium">
                              #{err.row_index}
                            </td>
                            <td className="py-2 px-3 font-mono text-[#57534E]">{err.field_name}</td>
                            <td className="py-2 px-3">
                              <Badge variant={err.severity === 'CRITICAL' ? 'danger' : 'warning'}>
                                {err.severity}
                              </Badge>
                            </td>
                            <td className="py-2 px-3 font-mono text-[#78716C] text-[10px]">{err.error_code}</td>
                            <td className="py-2 px-3 text-rose-800 font-medium">{err.error_message}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

            </div>
          )}

          {/* STEP 4: Explicit Confirmation & Commit */}
          {wizardStep === 4 && (
            <div className="bg-white p-6 sm:p-8 rounded-2xl border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-6">
              {!commitSummary ? (
                <div className="space-y-6 max-w-xl mx-auto text-center py-4">
                  <div className="w-14 h-14 rounded-2xl bg-[#FAF9F5] border border-[#E5E4DF] flex items-center justify-center text-[#1C1917] mx-auto shadow-sm">
                    <Database className="w-7 h-7 text-[#57534E]" />
                  </div>
                  <div>
                    <h3 className="text-xl font-serif font-medium text-[#1C1917] tracking-tight">
                      Confirm Import to AICTE Central Registry
                    </h3>
                    <p className="text-xs text-[#78716C] mt-2">
                      You are about to commit <span className="font-medium text-[#15803D]">{dryRunResult?.valid_rows_count} valid records</span> into the persistent institutional database.
                    </p>
                  </div>

                  {commitError && (
                    <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2 text-left">
                      <AlertTriangle className="w-4 h-4 shrink-0 text-rose-700" />
                      {commitError}
                    </div>
                  )}

                  <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF] text-left text-xs space-y-2 text-[#57534E]">
                    <div className="flex items-center justify-between border-b border-[#E5E4DF] pb-2">
                      <span className="text-[#78716C]">Target Session:</span>
                      <span className="font-medium text-[#1C1917]">{academicYear}</span>
                    </div>
                    <div className="flex items-center justify-between border-b border-[#E5E4DF] pb-2">
                      <span className="text-[#78716C]">Records to Commit:</span>
                      <span className="font-medium text-[#15803D]">{dryRunResult?.valid_rows_count} Students</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[#78716C]">Records Staged for Error Correction:</span>
                      <span className="font-medium text-rose-800">{dryRunResult?.invalid_rows_count} Students</span>
                    </div>
                  </div>

                  <div className="flex items-center justify-center gap-4 pt-2">
                    <button
                      onClick={() => setWizardStep(3)}
                      disabled={committing}
                      className="px-4 py-2 rounded-xl bg-white border border-[#E5E4DF] text-[#57534E] text-xs font-medium hover:bg-[#F4F3EE]"
                    >
                      Back to Pre-Validation
                    </button>
                    <button
                      onClick={handleCommitImport}
                      disabled={committing}
                      className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-[#1C1917] hover:bg-[#292524] text-white text-xs font-medium transition-all shadow-sm disabled:opacity-50"
                    >
                      {committing ? (
                        <>
                          <RefreshCw className="w-4 h-4 animate-spin" />
                          Committing Atomic Transaction...
                        </>
                      ) : (
                        <>
                          <Check className="w-4 h-4" />
                          Confirm & Commit Batch
                        </>
                      )}
                    </button>
                  </div>
                </div>
              ) : (
                /* Import Completed Summary */
                <div className="space-y-6 max-w-xl mx-auto text-center py-6">
                  <div className="w-14 h-14 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-800 mx-auto shadow-sm">
                    <CheckCircle2 className="w-7 h-7" />
                  </div>
                  <div>
                    <h3 className="text-xl font-serif font-medium text-[#1C1917] tracking-tight">
                      Batch Import Completed Successfully
                    </h3>
                    <p className="text-xs text-[#78716C] mt-1 font-mono">
                      Job ID: {commitSummary.job_id}
                    </p>
                  </div>

                  <div className="grid grid-cols-3 gap-3">
                    <div className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF]">
                      <span className="text-[10px] text-[#78716C] uppercase tracking-wider block font-medium">Total In File</span>
                      <span className="text-xl font-serif font-medium text-[#1C1917] mt-1 block">{commitSummary.total_records}</span>
                    </div>
                    <div className="p-3.5 rounded-xl bg-emerald-50/50 border border-emerald-200">
                      <span className="text-[10px] text-emerald-800 uppercase tracking-wider block font-medium">Accepted</span>
                      <span className="text-xl font-serif font-medium text-[#15803D] mt-1 block">{commitSummary.accepted_count}</span>
                    </div>
                    <div className="p-3.5 rounded-xl bg-amber-50/50 border border-amber-200">
                      <span className="text-[10px] text-amber-800 uppercase tracking-wider block font-medium">Staged / Errors</span>
                      <span className="text-xl font-serif font-medium text-amber-900 mt-1 block">{commitSummary.rejected_count}</span>
                    </div>
                  </div>

                  <div className="flex items-center justify-center gap-3 pt-4">
                    <button
                      onClick={onViewRoster}
                      className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#1C1917] hover:bg-[#292524] text-white text-xs font-medium transition-all shadow-sm"
                    >
                      View Confirmed Student Directory
                      <ArrowRight className="w-4 h-4" />
                    </button>
                    <button
                      onClick={handleResetWizard}
                      className="px-4 py-2.5 rounded-xl bg-white hover:bg-[#F4F3EE] text-[#57534E] text-xs font-medium border border-[#E5E4DF]"
                    >
                      Upload Another Batch
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

        </div>
      )}

      {/* ========================================================
          MODE 2: UPLOAD JOB HISTORY & ERROR REVIEW
         ======================================================== */}
      {activeMainTab === 'history' && (
        <div className="bg-white p-6 rounded-2xl border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-6 animate-fade-in">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-serif font-medium text-[#1C1917] flex items-center gap-2">
                <History className="w-5 h-5 text-[#78716C]" />
                Upload Job History & Error Review
              </h2>
              <p className="text-xs text-[#78716C]">
                Audited archive of all bulk import runs with downloadable error reports and staging metrics.
              </p>
            </div>
            <button
              onClick={loadJobHistory}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white hover:bg-[#F4F3EE] text-[#57534E] text-xs font-medium border border-[#E5E4DF] transition-all shadow-sm"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingJobs ? 'animate-spin' : ''}`} />
              Refresh Jobs
            </button>
          </div>

          <div className="overflow-x-auto rounded-xl border border-[#E5E4DF]">
            <table className="w-full text-left text-xs text-[#57534E]">
              <thead className="bg-[#FAF9F5] text-[11px] font-medium uppercase tracking-wider text-[#78716C] border-b border-[#E5E4DF]">
                <tr>
                  <th className="py-3 px-4">Filename & Job ID</th>
                  <th className="py-3 px-3 text-center">Session</th>
                  <th className="py-3 px-3 text-center">Total Rows</th>
                  <th className="py-3 px-3 text-center">Accepted</th>
                  <th className="py-3 px-3 text-center">Failed / Staged</th>
                  <th className="py-3 px-3 text-center">Status</th>
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4 text-right">Error Review</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E4DF] font-sans">
                {loadingJobs ? (
                  <tr>
                    <td colSpan={8} className="py-12 text-center text-[#78716C]">
                      <RefreshCw className="w-5 h-5 animate-spin mx-auto text-[#C2410C] mb-2" />
                      Loading job history...
                    </td>
                  </tr>
                ) : uploadJobs.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-12 text-center text-[#78716C]">
                      No upload jobs recorded yet for this institution.
                    </td>
                  </tr>
                ) : (
                  uploadJobs.map((j) => (
                    <tr key={j.id} className="hover:bg-[#FAF9F5] transition-colors">
                      <td className="py-3 px-4">
                        <p className="font-medium text-[#1C1917] flex items-center gap-1.5 font-mono">
                          <FileText className="w-3.5 h-3.5 text-[#78716C]" />
                          {j.filename}
                        </p>
                        <p className="text-[10px] text-[#A8A29E] font-mono mt-0.5">{j.id}</p>
                      </td>
                      <td className="py-3 px-3 text-center font-mono text-[#78716C]">{j.academic_year}</td>
                      <td className="py-3 px-3 text-center font-medium text-[#1C1917]">{j.total_records}</td>
                      <td className="py-3 px-3 text-center font-medium text-[#15803D]">{j.valid_records}</td>
                      <td className="py-3 px-3 text-center font-medium text-rose-800">{j.error_records}</td>
                      <td className="py-3 px-3 text-center">
                        <Badge
                          variant={
                            j.status === 'COMPLETED'
                              ? 'success'
                              : j.status === 'FAILED'
                              ? 'danger'
                              : 'warning'
                          }
                        >
                          {j.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-[#78716C] font-mono text-[11px]">{j.created_at}</td>
                      <td className="py-3 px-4 text-right">
                        {j.error_records > 0 ? (
                          <a
                            href={getJobErrorExportUrl(j.id)}
                            download={`error_report_${j.id}.csv`}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 hover:bg-rose-100 text-xs font-medium transition-all"
                          >
                            <Download className="w-3 h-3" />
                            Error CSV
                          </a>
                        ) : (
                          <span className="text-[#A8A29E] text-[11px]">No Errors</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

    </div>
  );
};
