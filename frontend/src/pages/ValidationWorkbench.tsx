import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle2,
  Clock,
  Search,
  Filter,
  RefreshCw,
  Eye,
  SlidersHorizontal,
  ChevronLeft,
  ChevronRight,
  BookOpen,
  Sparkles,
  ExternalLink,
  CheckSquare,
  Square,
  FileCheck2,
  XCircle,
  HelpCircle,
  X,
  UserCheck,
  Building2,
  Layers,
  ArrowRight
} from 'lucide-react';
import {
  ValidationWorkbenchIssue,
  ValidationWorkbenchSummary,
  ValidationWorkbenchResponse,
  IssueStatusUpdateIn,
  BulkIssueReviewIn
} from '../types';
import {
  fetchValidationWorkbench,
  updateValidationIssueStatus,
  bulkReviewValidationIssues,
  runValidationAudit
} from '../services/api';
import { Badge } from '../components/Badge';

interface ValidationWorkbenchProps {
  institutionId?: string;
  userRole?: string;
  onNavigateToStudent?: (studentId: string) => void;
}

const STATUTORY_RULES = [
  { id: 'RULE_01_MISSING_APAAR', name: 'Rule 1: Missing APAAR ID', desc: 'Mandatory national student identity identifier is completely missing.', severity: 'CRITICAL' },
  { id: 'RULE_02_MALFORMED_APAAR', name: 'Rule 2: Malformed APAAR ID', desc: 'Fails Verhoeff checksum or 12-digit format. Format check does NOT prove registry authenticity.', severity: 'CRITICAL' },
  { id: 'RULE_03_INTERNAL_DUPLICATE_APAAR', name: 'Rule 3: Duplicate APAAR (Internal)', desc: 'Identical APAAR assigned to another active student in the same institution.', severity: 'CRITICAL' },
  { id: 'RULE_04_CROSS_INST_DUPLICATE', name: 'Rule 4: Cross-Institution Duplicate', desc: 'Potential anomaly: Concurrent active enrolment detected at another technical institution.', severity: 'HIGH' },
  { id: 'RULE_05_DUPLICATE_INTERNAL_ID', name: 'Rule 5: Duplicate Roll Number', desc: 'Internal institutional roll number already in use within the academic session.', severity: 'CRITICAL' },
  { id: 'RULE_06_MISSING_MANDATORY_FIELD', name: 'Rule 6: Missing Mandatory Fields', desc: 'Legal full name, roll number, course, or date of birth is absent.', severity: 'CRITICAL' },
  { id: 'RULE_07_INVALID_YEAR_OR_STATUS', name: 'Rule 7: Invalid Session or Status', desc: 'Non-consecutive academic year or unapproved admission status code.', severity: 'HIGH' },
  { id: 'RULE_08_INCONSISTENT_PROGRAMME', name: 'Rule 8: Inconsistent Programme / Course', desc: 'Course does not belong to declared programme discipline catalog.', severity: 'CRITICAL' },
  { id: 'RULE_09_INTAKE_EXCEEDED', name: 'Rule 9: Admissions Exceed Intake', desc: 'Active core regular enrolment exceeds statutory sanctioned intake limit.', severity: 'CRITICAL' },
  { id: 'RULE_10_SUPERNUMERARY_VIOLATION', name: 'Rule 10: Supernumerary Quota Cap', desc: 'TFW (5%), NRI (5%), or Foreign National (15%) admissions exceed quota caps.', severity: 'HIGH' },
  { id: 'RULE_11_INCONSISTENT_NATIONALITY', name: 'Rule 11: Inconsistent Nationality / NRI', desc: 'Contradictory supernumerary category, NRI flag, or foreign national documentation.', severity: 'MEDIUM' },
  { id: 'RULE_12_CONFLICTING_ATTRIBUTES', name: 'Rule 12: Conflicting Identity Attributes', desc: 'Potential anomaly: Divergent date of birth or name spelling for same APAAR across records.', severity: 'MEDIUM' },
  { id: 'RULE_13_DUPLICATE_FILE_ROWS', name: 'Rule 13: Duplicate Rows in Batch', desc: 'Duplicate roll numbers or duplicate APAAR IDs within the same uploaded CSV file.', severity: 'CRITICAL' },
  { id: 'RULE_14_SUSPICIOUS_BULK_CHANGE', name: 'Rule 14: Suspicious Bulk Change Surge', desc: 'Potential anomaly: Batch adds >30% of total sanctioned institutional capacity.', severity: 'MEDIUM' }
];

export const ValidationWorkbench: React.FC<ValidationWorkbenchProps> = ({
  institutionId,
  userRole,
  onNavigateToStudent
}) => {
  const [loading, setLoading] = useState<boolean>(true);
  const [data, setData] = useState<ValidationWorkbenchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Filters
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [ruleFilter, setRuleFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const [limit] = useState<number>(15);

  // Selection for bulk review
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  // Modals
  const [selectedIssue, setSelectedIssue] = useState<ValidationWorkbenchIssue | null>(null);
  const [reviewModalOpen, setReviewModalOpen] = useState<boolean>(false);
  const [reviewTargetStatus, setReviewTargetStatus] = useState<string>('UNDER_REVIEW');
  const [reviewReason, setReviewReason] = useState<string>('');
  const [submittingReview, setSubmittingReview] = useState<boolean>(false);

  // Bulk review modal
  const [bulkModalOpen, setBulkModalOpen] = useState<boolean>(false);
  const [bulkTargetStatus, setBulkTargetStatus] = useState<string>('UNDER_REVIEW');
  const [bulkReason, setBulkReason] = useState<string>('');

  // Rules catalog modal
  const [rulesCatalogOpen, setRulesCatalogOpen] = useState<boolean>(false);

  // Audit triggering state
  const [runningAudit, setRunningAudit] = useState<boolean>(false);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchValidationWorkbench({
        institution_id: institutionId,
        severity: severityFilter || undefined,
        status: statusFilter || undefined,
        rule_id: ruleFilter || undefined,
        search: searchQuery || undefined,
        page: page,
        limit: limit
      });
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to load validation workbench');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [institutionId, severityFilter, statusFilter, ruleFilter, page]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadData();
  };

  const handleTriggerAudit = async () => {
    try {
      setRunningAudit(true);
      setError(null);
      setActionSuccess(null);
      const result = await runValidationAudit(institutionId);
      setActionSuccess(`Audit Completed: Found ${result.total_issues_found} issues (${result.new_issues_persisted} newly recorded). Risk Level: ${result.risk_level}. ${result.explanation}`);
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Diagnostic audit execution failed');
    } finally {
      setRunningAudit(false);
    }
  };

  const openSingleReview = (issue: ValidationWorkbenchIssue) => {
    setSelectedIssue(issue);
    setReviewTargetStatus(issue.resolution_status || 'UNDER_REVIEW');
    setReviewReason(issue.resolution_reason || '');
    setReviewModalOpen(true);
  };

  const handleSingleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedIssue) return;
    try {
      setSubmittingReview(true);
      setError(null);
      await updateValidationIssueStatus(selectedIssue.id, {
        resolution_status: reviewTargetStatus,
        resolution_reason: reviewReason.trim()
      });
      setActionSuccess(`Issue #${selectedIssue.id} updated to ${reviewTargetStatus}.`);
      setReviewModalOpen(false);
      setSelectedIssue(null);
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Status update failed');
    } finally {
      setSubmittingReview(false);
    }
  };

  const handleBulkReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedIds.length === 0) return;
    try {
      setSubmittingReview(true);
      setError(null);
      const res = await bulkReviewValidationIssues({
        issue_ids: selectedIds,
        resolution_status: bulkTargetStatus,
        resolution_reason: bulkReason.trim()
      });
      setActionSuccess(`Bulk Review Executed: ${res.updated_count} issues updated to ${bulkTargetStatus}.`);
      setBulkModalOpen(false);
      setSelectedIds([]);
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Bulk review execution failed');
    } finally {
      setSubmittingReview(false);
    }
  };

  const toggleSelectAll = () => {
    if (!data?.items) return;
    if (selectedIds.length === data.items.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(data.items.map((i) => i.id));
    }
  };

  const toggleSelectRow = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-50 text-rose-800 border border-rose-200">
            <ShieldAlert className="w-3 h-3 text-rose-700" />
            CRITICAL
          </span>
        );
      case 'HIGH':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-900 border border-amber-200">
            <AlertTriangle className="w-3 h-3 text-amber-700" />
            HIGH
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-[#F4F3EE] text-[#57534E] border border-[#E5E4DF]">
            <AlertCircle className="w-3 h-3 text-[#78716C]" />
            MEDIUM
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-sky-50 text-sky-800 border border-sky-200">
            <Info className="w-3 h-3 text-sky-700" />
            LOW
          </span>
        );
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'NEW':
        return <Badge variant="warning"><Clock className="w-3 h-3" /> New Issue</Badge>;
      case 'UNDER_REVIEW':
        return <Badge variant="info"><Eye className="w-3 h-3" /> Under Review</Badge>;
      case 'RESOLVED':
        return <Badge variant="emerald"><CheckCircle2 className="w-3 h-3" /> Resolved</Badge>;
      case 'DISMISSED':
        return <Badge variant="neutral"><XCircle className="w-3 h-3" /> Dismissed</Badge>;
      default:
        return <Badge variant="neutral">{status}</Badge>;
    }
  };

  const summary = data?.summary;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6 text-[#1C1917]">
      
      {/* 1. Header & Quick Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#E5E4DF] pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl sm:text-3xl font-serif font-normal text-[#1C1917] flex items-center gap-2">
                Validation Workbench
                <span className="text-[11px] font-sans font-medium px-2 py-0.5 rounded-full bg-rose-50 text-rose-800 border border-rose-200">
                  CORE ENGINE
                </span>
              </h1>
              <p className="text-xs sm:text-sm text-[#57534E] font-serif italic mt-0.5">
                Deterministic validation across 14 statutory AICTE rules • Intake & supernumerary reconciliation
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setRulesCatalogOpen(true)}
            className="px-3.5 py-2 rounded-xl text-xs font-medium bg-[#FAF9F5] hover:bg-[#F4F3EE] text-[#1C1917] border border-[#E5E4DF] transition-all flex items-center gap-1.5 shadow-sm"
          >
            <BookOpen className="w-3.5 h-3.5 text-[#78716C]" />
            14 Rules Reference
          </button>

          <button
            onClick={handleTriggerAudit}
            disabled={runningAudit}
            className="px-4 py-2 rounded-xl text-xs font-medium bg-[#1C1917] hover:bg-[#292524] text-white shadow-sm flex items-center gap-2 transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${runningAudit ? 'animate-spin' : ''}`} />
            {runningAudit ? 'Executing Engine Audit...' : 'Run Diagnostic Audit'}
          </button>
        </div>
      </div>

      {/* Notifications */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs sm:text-sm flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-rose-700 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-semibold">Validation Error:</span> {error}
          </div>
          <button onClick={() => setError(null)} className="text-rose-700 hover:text-rose-900">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {actionSuccess && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs sm:text-sm flex items-start gap-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-700 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-semibold">Audit Action Recorded:</span> {actionSuccess}
          </div>
          <button onClick={() => setActionSuccess(null)} className="text-emerald-700 hover:text-emerald-900">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* 2. Anomaly Engine & Explainable Risk Banner */}
      {summary && (
        <div className="rounded-2xl bg-white p-5 border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-4">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-serif font-medium uppercase tracking-wider text-[#78716C]">
                  Deterministic Anomaly Risk Assessment
                </span>
                {summary.is_potential_anomaly && (
                  <span className="text-[11px] font-sans font-medium px-2 py-0.5 rounded-full bg-amber-50 text-amber-900 border border-amber-200 flex items-center gap-1">
                    <Sparkles className="w-3 h-3 text-[#C2410C]" />
                    Potential Anomaly Flagged
                  </span>
                )}
              </div>
              <p className="text-sm text-[#57534E]">
                Rule-based risk score: <strong className="font-serif text-[#1C1917] text-base">{summary.anomaly_score} / 100</strong>.
                Calculated deterministically from active statutory issues. No unverified black-box ML claims.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <div className="text-right">
                <span className="text-[10px] text-[#78716C] uppercase tracking-wider block font-medium">Risk Level</span>
                <span
                  className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border inline-block mt-0.5 ${
                    summary.risk_level === 'CRITICAL'
                      ? 'bg-rose-50 text-rose-800 border-rose-200'
                      : summary.risk_level === 'HIGH'
                      ? 'bg-amber-50 text-amber-900 border-amber-200'
                      : summary.risk_level === 'MEDIUM'
                      ? 'bg-[#F4F3EE] text-[#57534E] border-[#E5E4DF]'
                      : 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                  }`}
                >
                  {summary.risk_level} RISK
                </span>
              </div>
            </div>
          </div>

          {/* Anomaly Progress Meter */}
          <div className="w-full bg-[#FAF9F5] rounded-full h-2 overflow-hidden border border-[#E5E4DF]">
            <div
              className="h-full transition-all duration-500 rounded-full bg-[#1C1917]"
              style={{ width: `${Math.max(5, Math.min(100, summary.anomaly_score))}%` }}
            />
          </div>
        </div>
      )}

      {/* 3. Severity & Lifecycle KPI Metrics Grid */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
          <div className="p-3 rounded-xl bg-white border border-[#E5E4DF] shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
            <span className="text-[10px] font-medium text-[#78716C] uppercase tracking-wider block">Total</span>
            <span className="text-xl font-serif font-medium text-[#1C1917]">{summary.total_issues}</span>
          </div>

          <div
            onClick={() => { setSeverityFilter('CRITICAL'); setPage(1); }}
            className={`p-3 rounded-xl border cursor-pointer transition-all ${
              severityFilter === 'CRITICAL'
                ? 'bg-rose-50 border-rose-300 shadow-sm'
                : 'bg-white border-[#E5E4DF] hover:border-[#D5D3CA]'
            }`}
          >
            <span className="text-[10px] font-medium text-rose-700 uppercase tracking-wider block">Critical</span>
            <span className="text-xl font-serif font-medium text-rose-800">{summary.critical_count}</span>
          </div>

          <div
            onClick={() => { setSeverityFilter('HIGH'); setPage(1); }}
            className={`p-3 rounded-xl border cursor-pointer transition-all ${
              severityFilter === 'HIGH'
                ? 'bg-amber-50 border-amber-300 shadow-sm'
                : 'bg-white border-[#E5E4DF] hover:border-[#D5D3CA]'
            }`}
          >
            <span className="text-[10px] font-medium text-amber-800 uppercase tracking-wider block">High</span>
            <span className="text-xl font-serif font-medium text-amber-900">{summary.high_count}</span>
          </div>

          <div
            onClick={() => { setSeverityFilter('MEDIUM'); setPage(1); }}
            className={`p-3 rounded-xl border cursor-pointer transition-all ${
              severityFilter === 'MEDIUM'
                ? 'bg-[#F4F3EE] border-[#D5D3CA] shadow-sm'
                : 'bg-white border-[#E5E4DF] hover:border-[#D5D3CA]'
            }`}
          >
            <span className="text-[10px] font-medium text-[#57534E] uppercase tracking-wider block">Medium</span>
            <span className="text-xl font-serif font-medium text-[#1C1917]">{summary.medium_count}</span>
          </div>

          <div
            onClick={() => { setStatusFilter('NEW'); setPage(1); }}
            className={`p-3 rounded-xl border cursor-pointer transition-all ${
              statusFilter === 'NEW'
                ? 'bg-amber-50 border-amber-300 shadow-sm'
                : 'bg-white border-[#E5E4DF] hover:border-[#D5D3CA]'
            }`}
          >
            <span className="text-[10px] font-medium text-amber-800 uppercase tracking-wider block">New</span>
            <span className="text-xl font-serif font-medium text-[#1C1917]">{summary.new_count}</span>
          </div>

          <div
            onClick={() => { setStatusFilter('UNDER_REVIEW'); setPage(1); }}
            className={`p-3 rounded-xl border cursor-pointer transition-all ${
              statusFilter === 'UNDER_REVIEW'
                ? 'bg-sky-50 border-sky-300 shadow-sm'
                : 'bg-white border-[#E5E4DF] hover:border-[#D5D3CA]'
            }`}
          >
            <span className="text-[10px] font-medium text-sky-800 uppercase tracking-wider block">Reviewing</span>
            <span className="text-xl font-serif font-medium text-sky-900">{summary.under_review_count}</span>
          </div>

          <div
            onClick={() => { setStatusFilter('RESOLVED'); setPage(1); }}
            className={`p-3 rounded-xl border cursor-pointer transition-all ${
              statusFilter === 'RESOLVED'
                ? 'bg-emerald-50 border-emerald-300 shadow-sm'
                : 'bg-white border-[#E5E4DF] hover:border-[#D5D3CA]'
            }`}
          >
            <span className="text-[10px] font-medium text-emerald-800 uppercase tracking-wider block">Resolved</span>
            <span className="text-xl font-serif font-medium text-emerald-900">{summary.resolved_count}</span>
          </div>

          <div
            onClick={() => { setStatusFilter('DISMISSED'); setPage(1); }}
            className={`p-3 rounded-xl border cursor-pointer transition-all ${
              statusFilter === 'DISMISSED'
                ? 'bg-[#F4F3EE] border-[#D5D3CA] shadow-sm'
                : 'bg-white border-[#E5E4DF] hover:border-[#D5D3CA]'
            }`}
          >
            <span className="text-[10px] font-medium text-[#78716C] uppercase tracking-wider block">Dismissed</span>
            <span className="text-xl font-serif font-medium text-[#57534E]">{summary.dismissed_count}</span>
          </div>
        </div>
      )}

      {/* 4. Filter Toolbar & Search */}
      <div className="bg-white p-4 rounded-xl border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.02)] flex flex-col md:flex-row items-center justify-between gap-4">
        <form onSubmit={handleSearchSubmit} className="flex-1 w-full flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-[#A8A29E] absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search error code, student name, roll number, or explanation..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#FAF9F5] border border-[#E5E4DF] rounded-xl pl-9 pr-4 py-2 text-xs text-[#1C1917] placeholder-[#A8A29E] focus:outline-none focus:border-[#1C1917]"
            />
          </div>
          <button
            type="submit"
            className="px-3.5 py-2 rounded-xl text-xs font-medium bg-[#1C1917] hover:bg-[#292524] text-white"
          >
            Search
          </button>
        </form>

        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          {/* Severity selector */}
          <select
            value={severityFilter}
            onChange={(e) => { setSeverityFilter(e.target.value); setPage(1); }}
            className="bg-[#FAF9F5] border border-[#E5E4DF] rounded-xl px-3 py-2 text-xs text-[#57534E] focus:outline-none focus:border-[#1C1917]"
          >
            <option value="">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>

          {/* Status selector */}
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="bg-[#FAF9F5] border border-[#E5E4DF] rounded-xl px-3 py-2 text-xs text-[#57534E] focus:outline-none focus:border-[#1C1917]"
          >
            <option value="">All Statuses</option>
            <option value="NEW">New</option>
            <option value="UNDER_REVIEW">Under Review</option>
            <option value="RESOLVED">Resolved</option>
            <option value="DISMISSED">Dismissed</option>
          </select>

          {/* Rule Filter */}
          <select
            value={ruleFilter}
            onChange={(e) => { setRuleFilter(e.target.value); setPage(1); }}
            className="bg-[#FAF9F5] border border-[#E5E4DF] rounded-xl px-3 py-2 text-xs text-[#57534E] focus:outline-none focus:border-[#1C1917] max-w-[200px]"
          >
            <option value="">All 14 Rules</option>
            {STATUTORY_RULES.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>

          {(severityFilter || statusFilter || ruleFilter || searchQuery) && (
            <button
              onClick={() => {
                setSeverityFilter('');
                setStatusFilter('');
                setRuleFilter('');
                setSearchQuery('');
                setPage(1);
              }}
              className="text-xs text-[#C2410C] hover:underline px-2 py-1"
            >
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {/* 5. Bulk Review Action Bar */}
      {selectedIds.length > 0 && (
        <div className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF] flex flex-wrap items-center justify-between gap-3 shadow-sm animate-fadeIn">
          <div className="flex items-center gap-2 text-xs text-[#1C1917]">
            <CheckSquare className="w-4 h-4 text-[#1C1917]" />
            <span>Selected <strong>{selectedIds.length}</strong> issue(s) on current page.</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => { setBulkTargetStatus('UNDER_REVIEW'); setBulkModalOpen(true); }}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-sky-50 text-sky-800 border border-sky-200 hover:bg-sky-100"
            >
              Mark Under Review
            </button>
            <button
              onClick={() => { setBulkTargetStatus('RESOLVED'); setBulkModalOpen(true); }}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-50 text-emerald-800 border border-emerald-200 hover:bg-emerald-100"
            >
              Mark Resolved
            </button>
            <button
              onClick={() => { setBulkTargetStatus('DISMISSED'); setBulkModalOpen(true); }}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-stone-100 text-stone-700 border border-stone-200 hover:bg-stone-200"
            >
              Dismiss
            </button>
            <button
              onClick={() => setSelectedIds([])}
              className="px-2 py-1.5 text-xs text-[#78716C] hover:text-[#1C1917] underline ml-2"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* 6. Issues Table */}
      <div className="rounded-2xl bg-white border border-[#E5E4DF] overflow-hidden shadow-[0_1px_3px_rgba(0,0,0,0.03)]">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-[#57534E]">
            <thead className="bg-[#FAF9F5] border-b border-[#E5E4DF] text-[11px] uppercase tracking-wider text-[#78716C] font-medium">
              <tr>
                <th className="p-3.5 w-10 text-center">
                  <button onClick={toggleSelectAll} className="text-[#78716C] hover:text-[#1C1917]">
                    {data?.items && selectedIds.length === data.items.length && data.items.length > 0 ? (
                      <CheckSquare className="w-4 h-4 text-[#1C1917]" />
                    ) : (
                      <Square className="w-4 h-4" />
                    )}
                  </button>
                </th>
                <th className="p-3.5">Severity</th>
                <th className="p-3.5">Rule / Issue Code</th>
                <th className="p-3.5">Entity / Student</th>
                <th className="p-3.5">Statutory Explanation</th>
                <th className="p-3.5">Suggested Action</th>
                <th className="p-3.5">Status</th>
                <th className="p-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E5E4DF] font-sans">
              {loading ? (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-[#78716C]">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-[#C2410C]" />
                    Evaluating statutory validation rules...
                  </td>
                </tr>
              ) : !data || data.items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-[#78716C]">
                    <CheckCircle2 className="w-8 h-8 text-[#15803D] mx-auto mb-2" />
                    <p className="font-serif font-medium text-[#1C1917] text-base">No Validation Issues Found</p>
                    <p className="text-[#78716C] text-xs mt-0.5">
                      All student enrolments and intake quotas conform to AICTE statutory standards.
                    </p>
                  </td>
                </tr>
              ) : (
                data.items.map((issue) => {
                  const isSelected = selectedIds.includes(issue.id);
                  return (
                    <tr
                      key={issue.id}
                      className={`hover:bg-[#FAF9F5] transition-colors ${
                        isSelected ? 'bg-[#F4F3EE]' : ''
                      }`}
                    >
                      <td className="p-3.5 text-center">
                        <button onClick={() => toggleSelectRow(issue.id)} className="text-[#78716C] hover:text-[#1C1917]">
                          {isSelected ? (
                            <CheckSquare className="w-4 h-4 text-[#1C1917]" />
                          ) : (
                            <Square className="w-4 h-4" />
                          )}
                        </button>
                      </td>

                      <td className="p-3.5 whitespace-nowrap">
                        {getSeverityBadge(issue.severity)}
                      </td>

                      <td className="p-3.5">
                        <div className="font-mono text-xs font-semibold text-[#1C1917]">
                          {issue.error_code}
                        </div>
                        <div className="text-[10px] text-[#78716C] font-mono">
                          {issue.rule_id}
                        </div>
                      </td>

                      <td className="p-3.5">
                        <div className="font-serif font-medium text-[#1C1917] text-sm">
                          {issue.student_name || 'N/A'}
                        </div>
                        <div className="text-[10px] text-[#78716C] font-mono">
                          {issue.internal_student_id ? `Roll: ${issue.internal_student_id}` : ''}
                          {issue.apaar_masked ? ` • ${issue.apaar_masked}` : ''}
                        </div>
                        {issue.institution_name && (
                          <div className="text-[10px] text-[#A8A29E] truncate max-w-[160px]">
                            {issue.institution_name}
                          </div>
                        )}
                      </td>

                      <td className="p-3.5 max-w-xs">
                        <p className="text-[#57534E] text-xs leading-relaxed">
                          {issue.error_message}
                        </p>
                        {issue.is_potential_anomaly && (
                          <span className="inline-block mt-1 text-[10px] text-amber-900 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded font-medium">
                            Potential Anomaly
                          </span>
                        )}
                      </td>

                      <td className="p-3.5 max-w-xs">
                        <div className="p-2 rounded-lg bg-[#FAF9F5] border border-[#E5E4DF] text-[11px] text-[#57534E]">
                          {issue.suggested_remediation}
                        </div>
                      </td>

                      <td className="p-3.5 whitespace-nowrap">
                        {getStatusBadge(issue.resolution_status)}
                        {issue.reviewed_by_email && (
                          <div className="text-[9px] text-[#A8A29E] mt-1 font-mono">
                            By: {issue.reviewed_by_email.split('@')[0]}
                          </div>
                        )}
                      </td>

                      <td className="p-3.5 text-right whitespace-nowrap">
                        <button
                          onClick={() => openSingleReview(issue)}
                          className="px-2.5 py-1.5 rounded-lg text-xs font-medium bg-white hover:bg-[#F4F3EE] text-[#1C1917] border border-[#E5E4DF] transition-all shadow-sm"
                        >
                          Review & Resolve
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination controls */}
        {data && data.total_pages > 1 && (
          <div className="p-4 border-t border-[#E5E4DF] flex items-center justify-between text-xs text-[#78716C]">
            <div>
              Showing {data.items.length} of {data.total} issues (Page {data.page} of {data.total_pages})
            </div>
            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1.5 rounded-lg bg-white border border-[#E5E4DF] text-[#57534E] hover:bg-[#F4F3EE] disabled:opacity-40 shadow-sm"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                disabled={page >= data.total_pages}
                onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                className="px-3 py-1.5 rounded-lg bg-white border border-[#E5E4DF] text-[#57534E] hover:bg-[#F4F3EE] disabled:opacity-40 shadow-sm"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 7. Single Issue Review Modal */}
      {reviewModalOpen && selectedIssue && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-stone-900/40 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-2xl bg-white rounded-2xl border border-[#E5E4DF] p-6 space-y-5 shadow-[0_20px_50px_rgba(0,0,0,0.12)]">
            <div className="flex items-center justify-between border-b border-[#E5E4DF] pb-3">
              <div className="flex items-center gap-2">
                <FileCheck2 className="w-5 h-5 text-[#C2410C]" />
                <h3 className="text-lg font-serif font-medium text-[#1C1917]">
                  Issue Review & Resolution #{selectedIssue.id}
                </h3>
              </div>
              <button
                onClick={() => { setReviewModalOpen(false); setSelectedIssue(null); }}
                className="text-[#78716C] hover:text-[#1C1917]"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4 text-xs text-[#57534E]">
              {/* Meta details */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 p-3 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF]">
                <div>
                  <span className="text-[10px] text-[#78716C] uppercase tracking-wider block font-medium">Rule ID</span>
                  <span className="font-medium text-[#1C1917] font-mono">{selectedIssue.rule_id}</span>
                </div>
                <div>
                  <span className="text-[10px] text-[#78716C] uppercase tracking-wider block font-medium">Error Code</span>
                  <span className="font-medium text-rose-800 font-mono">{selectedIssue.error_code}</span>
                </div>
                <div>
                  <span className="text-[10px] text-[#78716C] uppercase tracking-wider block font-medium">Severity</span>
                  <div>{getSeverityBadge(selectedIssue.severity)}</div>
                </div>
                <div>
                  <span className="text-[10px] text-[#78716C] uppercase tracking-wider block font-medium">Target Student</span>
                  <span className="font-serif font-medium text-[#1C1917] text-sm">{selectedIssue.student_name || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-[10px] text-[#78716C] uppercase tracking-wider block font-medium">Internal Roll No</span>
                  <span className="font-medium text-[#1C1917]">{selectedIssue.internal_student_id || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-[10px] text-[#78716C] uppercase tracking-wider block font-medium">Masked APAAR</span>
                  <span className="font-mono font-medium text-[#15803D]">{selectedIssue.apaar_masked || 'N/A'}</span>
                </div>
              </div>

              {/* Statutory Explanation */}
              <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800">
                <span className="font-medium block mb-1">Violation Explanation:</span>
                <p className="leading-relaxed">{selectedIssue.error_message}</p>
              </div>

              {/* Remediation */}
              <div className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF] text-[#57534E]">
                <span className="font-medium text-[#1C1917] block mb-1">Statutory Suggested Remediation:</span>
                <p className="leading-relaxed">{selectedIssue.suggested_remediation}</p>
              </div>

              {/* Review Form */}
              <form onSubmit={handleSingleReviewSubmit} className="space-y-4 pt-2">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-[#57534E] block">
                    Update Resolution Status
                  </label>
                  <select
                    value={reviewTargetStatus}
                    onChange={(e) => setReviewTargetStatus(e.target.value)}
                    className="w-full bg-white border border-[#E5E4DF] rounded-xl px-3 py-2 text-xs text-[#1C1917] focus:outline-none focus:border-[#1C1917]"
                  >
                    <option value="NEW">New (Unresolved)</option>
                    <option value="UNDER_REVIEW">Under Review (Administrative In-Progress)</option>
                    <option value="RESOLVED">Resolved (Discrepancy Remedied / Validated)</option>
                    <option value="DISMISSED">Dismissed (Statutory Exemption Confirmed)</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-[#57534E] block">
                    Resolution Reason & Remediation Note <span className="text-rose-700">*</span>
                  </label>
                  <textarea
                    rows={3}
                    placeholder="Document the administrative remediation actions taken or regulatory justification..."
                    value={reviewReason}
                    onChange={(e) => setReviewReason(e.target.value)}
                    className="w-full bg-white border border-[#E5E4DF] rounded-xl p-3 text-xs text-[#1C1917] placeholder-[#A8A29E] focus:outline-none focus:border-[#1C1917]"
                    required
                  />
                  <p className="text-[10px] text-[#78716C]">
                    Mandatory audit trail. Your identity ({userRole}) and timestamp will be logged immutably.
                  </p>
                </div>

                <div className="flex items-center justify-end gap-2.5 pt-2">
                  <button
                    type="button"
                    onClick={() => { setReviewModalOpen(false); setSelectedIssue(null); }}
                    className="px-4 py-2 rounded-xl text-xs font-medium text-[#57534E] hover:bg-[#F4F3EE] bg-white border border-[#E5E4DF]"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submittingReview}
                    className="px-5 py-2 rounded-xl text-xs font-medium bg-[#1C1917] hover:bg-[#292524] text-white shadow-sm disabled:opacity-50"
                  >
                    {submittingReview ? 'Committing...' : 'Commit Status Transition'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* 8. Bulk Review Modal */}
      {bulkModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-stone-900/40 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-lg bg-white rounded-2xl border border-[#E5E4DF] p-6 space-y-4 shadow-[0_20px_50px_rgba(0,0,0,0.12)]">
            <div className="flex items-center justify-between border-b border-[#E5E4DF] pb-3">
              <h3 className="text-base font-serif font-medium text-[#1C1917]">
                Bulk Transition for {selectedIds.length} Issue(s)
              </h3>
              <button onClick={() => setBulkModalOpen(false)} className="text-[#78716C] hover:text-[#1C1917]">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleBulkReviewSubmit} className="space-y-4 text-xs text-[#57534E]">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-[#57534E] block">
                  Select Target Resolution Status
                </label>
                <select
                  value={bulkTargetStatus}
                  onChange={(e) => setBulkTargetStatus(e.target.value)}
                  className="w-full bg-white border border-[#E5E4DF] rounded-xl px-3 py-2 text-xs text-[#1C1917] focus:outline-none focus:border-[#1C1917]"
                >
                  <option value="UNDER_REVIEW">Mark Under Review</option>
                  <option value="RESOLVED">Mark Resolved</option>
                  <option value="DISMISSED">Dismiss Issues</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-[#57534E] block">
                  Audit Trail Reason <span className="text-rose-700">*</span>
                </label>
                <textarea
                  rows={3}
                  placeholder="State the regulatory justification or batch verification evidence..."
                  value={bulkReason}
                  onChange={(e) => setBulkReason(e.target.value)}
                  className="w-full bg-white border border-[#E5E4DF] rounded-xl p-3 text-xs text-[#1C1917] placeholder-[#A8A29E] focus:outline-none focus:border-[#1C1917]"
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-2">
                <button
                  type="button"
                  onClick={() => setBulkModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-medium text-[#57534E] hover:bg-[#F4F3EE] bg-white border border-[#E5E4DF]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingReview}
                  className="px-5 py-2 rounded-xl text-xs font-medium bg-[#1C1917] hover:bg-[#292524] text-white shadow-sm disabled:opacity-50"
                >
                  {submittingReview ? 'Applying...' : 'Apply to Selected'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 9. 14 Statutory Rules Catalog Modal */}
      {rulesCatalogOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-stone-900/40 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-3xl bg-white rounded-2xl border border-[#E5E4DF] p-6 space-y-4 shadow-[0_20px_50px_rgba(0,0,0,0.12)] max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-[#E5E4DF] pb-3">
              <div>
                <h3 className="text-lg font-serif font-medium text-[#1C1917] flex items-center gap-2">
                  <BookOpen className="w-5 h-5 text-[#C2410C]" />
                  AICTE Statutory Data Quality & Validation Rules Catalog
                </h3>
                <p className="text-xs text-[#78716C]">
                  Comprehensive 14 statutory checks evaluated deterministically by SIH26263 validation engine.
                </p>
              </div>
              <button onClick={() => setRulesCatalogOpen(false)} className="text-[#78716C] hover:text-[#1C1917]">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="overflow-y-auto space-y-2.5 pr-2 flex-1 text-xs">
              {STATUTORY_RULES.map((r) => (
                <div
                  key={r.id}
                  className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF] flex items-start justify-between gap-3"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-serif font-medium text-[#1C1917] text-sm">{r.name}</span>
                      <span className="text-[10px] text-[#78716C] font-mono">({r.id})</span>
                    </div>
                    <p className="text-[#57534E]">{r.desc}</p>
                  </div>
                  <div className="shrink-0">{getSeverityBadge(r.severity)}</div>
                </div>
              ))}
            </div>

            <div className="pt-2 border-t border-[#E5E4DF] text-right">
              <button
                onClick={() => setRulesCatalogOpen(false)}
                className="px-4 py-2 rounded-xl text-xs font-medium bg-[#1C1917] hover:bg-[#292524] text-white shadow-sm"
              >
                Close Reference
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
