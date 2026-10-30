import React, { useState, useEffect } from 'react';
import {
  Building2,
  Users,
  AlertTriangle,
  CheckCircle2,
  PlusCircle,
  FileSpreadsheet,
  Download,
  Search,
  Filter,
  Eye,
  EyeOff,
  Edit2,
  FileCheck,
  ShieldCheck,
  ShieldAlert,
  RefreshCw,
  LayoutDashboard,
  Layers,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Info,
  Calendar,
  Sparkles
} from 'lucide-react';
import { Institution, Student, CourseIntake, Programme, Course, InstitutionDashboardSummary } from '../types';
import {
  fetchInstitution,
  fetchIntakeReconciliation,
  fetchStudentsV1,
  fetchProgrammes,
  fetchCourses,
  fetchInstitutionDashboardSummary,
  getIntakeCompliancePdfUrl,
  getExportStudentsUrl
} from '../services/api';
import { StatCard } from '../components/StatCard';
import { Badge } from '../components/Badge';
import { StudentDetailModal } from '../components/StudentDetailModal';
import { StudentFormModal } from '../components/StudentFormModal';

interface InstitutionPortalProps {
  institutionId: string;
  initialTab?: 'overview' | 'directory' | 'reconciliation';
  onViewStudentCredential: (studentId: string) => void;
  onNavigateToImport: () => void;
  onNavigateToWorkbench?: () => void;
}

export const InstitutionPortal: React.FC<InstitutionPortalProps> = ({
  institutionId,
  initialTab = 'overview',
  onViewStudentCredential,
  onNavigateToImport,
  onNavigateToWorkbench
}) => {
  const [institution, setInstitution] = useState<Institution | null>(null);
  const [dashboardSummary, setDashboardSummary] = useState<InstitutionDashboardSummary | null>(null);
  const [reconciliation, setReconciliation] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'directory' | 'reconciliation'>(initialTab);

  // Student Directory State
  const [students, setStudents] = useState<Student[]>([]);
  const [totalStudents, setTotalStudents] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [limit, setLimit] = useState<number>(10);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [directoryLoading, setDirectoryLoading] = useState<boolean>(false);

  // Filter States
  const [search, setSearch] = useState<string>('');
  const [programmeFilter, setProgrammeFilter] = useState<string>('ALL');
  const [courseFilter, setCourseFilter] = useState<string>('ALL');
  const [academicYearFilter, setAcademicYearFilter] = useState<string>('ALL');
  const [admissionStatusFilter, setAdmissionStatusFilter] = useState<string>('ALL');
  const [recordStatusFilter, setRecordStatusFilter] = useState<string>('ALL');

  // Metadata dropdowns
  const [programmes, setProgrammes] = useState<Programme[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);

  // Modals state
  const [selectedStudentForDetail, setSelectedStudentForDetail] = useState<string | null>(null);
  const [isFormModalOpen, setIsFormModalOpen] = useState<boolean>(false);
  const [studentToEdit, setStudentToEdit] = useState<Student | null>(null);

  // Load institutional overview & metadata
  const loadOverview = async () => {
    try {
      setLoading(true);
      const [instData, recData, progs, crs, sumData] = await Promise.all([
        fetchInstitution(institutionId),
        fetchIntakeReconciliation(institutionId).catch(() => ({ reconciliation_rows: [] })),
        fetchProgrammes().catch(() => []),
        fetchCourses().catch(() => []),
        fetchInstitutionDashboardSummary(institutionId).catch(() => null)
      ]);
      setInstitution(instData);
      setReconciliation(recData.reconciliation_rows || []);
      setProgrammes(progs);
      setCourses(crs);
      setDashboardSummary(sumData);
    } catch (err) {
      console.error('Failed to load institution profile:', err);
    } finally {
      setLoading(false);
    }
  };

  // Load student directory with server-side filters & pagination
  const loadDirectory = async () => {
    try {
      setDirectoryLoading(true);
      const params: any = {
        institution_id: institutionId,
        page: currentPage,
        limit: limit
      };

      if (search.trim()) params.search = search.trim();
      if (programmeFilter !== 'ALL') params.programme_id = programmeFilter;
      if (courseFilter !== 'ALL') params.course_id = courseFilter;
      if (academicYearFilter !== 'ALL') params.academic_year = academicYearFilter;
      if (admissionStatusFilter !== 'ALL') params.admission_status = admissionStatusFilter;
      if (recordStatusFilter !== 'ALL') params.record_status = recordStatusFilter;

      const res = await fetchStudentsV1(params);
      setStudents(res.items);
      setTotalStudents(res.total);
      setTotalPages(res.total_pages);
    } catch (err) {
      console.error('Failed to fetch students roster:', err);
    } finally {
      setDirectoryLoading(false);
    }
  };

  useEffect(() => {
    loadOverview();
  }, [institutionId]);

  useEffect(() => {
    loadDirectory();
  }, [
    institutionId,
    currentPage,
    limit,
    search,
    programmeFilter,
    courseFilter,
    academicYearFilter,
    admissionStatusFilter,
    recordStatusFilter
  ]);

  useEffect(() => {
    if (initialTab) {
      setActiveTab(initialTab);
    }
  }, [initialTab]);

  const handleOpenAdd = () => {
    setStudentToEdit(null);
    setIsFormModalOpen(true);
  };

  const handleOpenEdit = (student: Student) => {
    setStudentToEdit(student);
    setIsFormModalOpen(true);
  };

  const handleFormSuccess = () => {
    loadOverview();
    loadDirectory();
  };

  const handleResetFilters = () => {
    setSearch('');
    setProgrammeFilter('ALL');
    setCourseFilter('ALL');
    setAcademicYearFilter('ALL');
    setAdmissionStatusFilter('ALL');
    setRecordStatusFilter('ALL');
    setCurrentPage(1);
  };

  if (loading && !institution) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3 text-[#1C1917]">
        <RefreshCw className="w-6 h-6 text-[#C2410C] animate-spin" />
        <p className="text-base font-serif font-medium text-[#1C1917]">Loading Institutional Workspace...</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fade-in text-[#1C1917]">
      
      {/* Institution Header Banner in Anthropic Minimalist Style */}
      <div className="bg-white p-6 sm:p-8 rounded-2xl border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.03)] relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="font-mono text-xs text-[#78716C] uppercase tracking-wider">
                Permanent AICTE ID: {institution?.aicte_permanent_id}
              </span>
              <Badge variant="info">{(institution?.institution_type || 'TECHNICAL_COLLEGE').replace(/_/g, ' ')}</Badge>
              <Badge variant={institution?.intake_status === 'COMPLIANT' ? 'success' : 'warning'}>
                {institution?.intake_status === 'COMPLIANT' ? 'APH Compliant' : 'Discrepancy Detected'}
              </Badge>
            </div>
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-serif font-normal text-[#1C1917] tracking-tight">{institution?.name}</h1>
            <p className="text-xs text-[#78716C] font-serif italic mt-1">
              {institution?.address || `${institution?.district}, ${institution?.state}`} • Academic Session {institution?.approval_session} • {institution?.contact_email}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {onNavigateToWorkbench && (
              <button
                onClick={onNavigateToWorkbench}
                className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-rose-50 hover:bg-rose-100 text-rose-800 text-xs font-medium transition-all border border-rose-200 shadow-sm"
              >
                <ShieldAlert className="w-3.5 h-3.5 text-rose-700" />
                Validation Workbench
              </button>
            )}
            <a
              href={getIntakeCompliancePdfUrl(institutionId)}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#FAF9F5] hover:bg-[#F4F3EE] text-[#57534E] text-xs font-medium transition-all border border-[#E5E4DF] shadow-sm"
            >
              <Download className="w-3.5 h-3.5 text-[#78716C]" />
              AICTE Compliance PDF
            </a>
            <button
              onClick={onNavigateToImport}
              className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#C2410C] hover:bg-[#9A3412] text-white text-xs font-medium transition-all shadow-sm"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              CSV Bulk Import
            </button>
            <button
              onClick={handleOpenAdd}
              className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#1C1917] hover:bg-[#292524] text-white text-xs font-medium transition-all shadow-sm"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              Onboard Student
            </button>
          </div>
        </div>
      </div>

      {/* Main Tab Switcher in Segmented Control Style */}
      <div className="flex flex-wrap items-center gap-2 p-1.5 rounded-2xl bg-[#F4F3EE] border border-[#E5E4DF] max-w-fit">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-medium transition-all flex items-center gap-2 ${
            activeTab === 'overview'
              ? 'bg-white text-[#1C1917] font-semibold shadow-sm border border-[#E5E4DF]'
              : 'text-[#78716C] hover:text-[#1C1917]'
          }`}
        >
          <LayoutDashboard className="w-4 h-4" />
          Campus Overview
        </button>
        <button
          onClick={() => setActiveTab('directory')}
          className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-medium transition-all flex items-center gap-2 ${
            activeTab === 'directory'
              ? 'bg-white text-[#1C1917] font-semibold shadow-sm border border-[#E5E4DF]'
              : 'text-[#78716C] hover:text-[#1C1917]'
          }`}
        >
          <Users className="w-4 h-4" />
          Student Directory ({totalStudents})
        </button>
        <button
          onClick={() => setActiveTab('reconciliation')}
          className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-medium transition-all flex items-center gap-2 ${
            activeTab === 'reconciliation'
              ? 'bg-white text-[#1C1917] font-semibold shadow-sm border border-[#E5E4DF]'
              : 'text-[#78716C] hover:text-[#1C1917]'
          }`}
        >
          <Layers className="w-4 h-4" />
          Intake & Quota Monitoring
        </button>
      </div>

      {/* ========================================================
          TAB 1: INSTITUTION OVERVIEW
         ======================================================== */}
      {activeTab === 'overview' && (
        <div className="space-y-8 animate-fade-in">
          
          {/* Institutional KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            
            {/* KPI 1: Sanctioned Intake */}
            <StatCard
              title="Approved Intake"
              value={dashboardSummary?.total_approved_intake || institution?.total_approved_intake || 0}
              subtitle="AICTE Sanctioned Core Pool"
              icon={<Building2 className="w-5 h-5" />}
              accent="blue"
            />

            {/* KPI 2: Confirmed Regular Enrolment & Occupancy */}
            <StatCard
              title="Confirmed Enrolled"
              value={dashboardSummary?.total_actual_enrolled || institution?.total_enrolled || 0}
              subtitle={`${dashboardSummary?.intake_utilization_pct || 0}% Capacity Filled`}
              icon={<Users className="w-5 h-5" />}
              accent="emerald"
            />

            {/* KPI 3: Supernumerary Admissions */}
            <StatCard
              title="Supernumerary"
              value={dashboardSummary?.total_supernumerary_enrolled || 0}
              subtitle="TFW (5%), NRI, FN Quotas"
              icon={<CheckCircle2 className="w-5 h-5" />}
              accent="amber"
            />

            {/* KPI 4: Unresolved Issues by Severity */}
            <div
              onClick={() => {
                if (onNavigateToWorkbench) onNavigateToWorkbench();
              }}
              className="cursor-pointer group bg-white p-5 rounded-xl border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.03)] hover:border-[#D5D3CA] transition-all space-y-2"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-[#78716C] uppercase tracking-wider">Unresolved Issues</span>
                <div className="p-2 rounded-lg bg-rose-50 border border-rose-200/60 text-rose-700">
                  <ShieldAlert className="w-5 h-5" />
                </div>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl sm:text-3xl font-serif font-medium text-[#1C1917]">
                  {dashboardSummary?.unresolved_issues_count || 0}
                </span>
                <span className="text-xs text-[#78716C]">Flags</span>
              </div>
              <div className="flex items-center gap-1 pt-1 text-[10px]">
                <span className="px-1.5 py-0.5 rounded-full bg-rose-50 text-rose-800 border border-rose-200 font-medium">
                  {dashboardSummary?.unresolved_issues_by_severity.critical || 0} Crit
                </span>
                <span className="px-1.5 py-0.5 rounded-full bg-amber-50 text-amber-900 border border-amber-200 font-medium">
                  {dashboardSummary?.unresolved_issues_by_severity.high || 0} High
                </span>
                <span className="px-1.5 py-0.5 rounded-full bg-[#F4F3EE] text-[#57534E] border border-[#E5E4DF] font-medium">
                  {dashboardSummary?.unresolved_issues_by_severity.medium || 0} Med
                </span>
              </div>
            </div>

            {/* KPI 5: Student Record Completeness Score */}
            <StatCard
              title="Record Quality"
              value={`${dashboardSummary?.student_record_completeness_pct || 0}%`}
              subtitle="Mandatory Regulatory Fields"
              icon={<ShieldCheck className="w-5 h-5" />}
              accent="blue"
            />

          </div>

          {/* Missing Fields Remediation Alert */}
          {dashboardSummary && dashboardSummary.student_record_completeness_pct < 100 && (
            <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2.5">
                <Info className="w-4 h-4 text-[#C2410C] shrink-0" />
                <div>
                  <span className="font-medium text-[#1C1917]">Student Record Completeness Remediation:</span>
                  <span className="text-[#57534E] ml-1.5">
                    Certain student identity fields require completion for 100% statutory compliance.
                  </span>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-1.5">
                {Object.entries(dashboardSummary.missing_fields_breakdown).map(([field, count]) => {
                  if (count === 0) return null;
                  return (
                    <span key={field} className="px-2 py-0.5 rounded text-[10px] font-mono bg-white text-[#57534E] border border-[#E5E4DF]">
                      {field.replace(/_/g, ' ')}: {count} missing
                    </span>
                  );
                })}
              </div>
            </div>
          )}

          {/* Capacity Utilization & Quick Action Hub */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Left 2 Cols: Capacity Breakdown */}
            <div className="lg:col-span-2 bg-white p-6 rounded-2xl border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-serif font-medium text-[#1C1917]">Sanctioned Course Capacity Allocation</h3>
                  <p className="text-xs text-[#78716C]">
                    AICTE core approved seats strictly separated from supernumerary quotas (TFW 5%, NRI 5%, FN 15%).
                  </p>
                </div>
                <button
                  onClick={() => setActiveTab('reconciliation')}
                  className="text-xs font-medium text-[#C2410C] hover:underline flex items-center gap-1"
                >
                  Detailed Audit
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>

              {/* Progress Bar of Overall Capacity */}
              <div className="space-y-2 pt-2">
                <div className="flex items-center justify-between text-xs font-medium text-[#57534E]">
                  <span>Overall Seat Capacity Occupancy</span>
                  <span className="text-[#1C1917] font-semibold">
                    {dashboardSummary?.intake_utilization_pct || 0}%
                  </span>
                </div>
                <div className="h-2.5 w-full bg-[#FAF9F5] border border-[#E5E4DF] rounded-full overflow-hidden flex">
                  <div
                    className="bg-[#1C1917] h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.min(100, dashboardSummary?.intake_utilization_pct || 0)}%`
                    }}
                  />
                </div>
                <div className="flex items-center justify-between text-[11px] text-[#78716C] pt-1">
                  <span>Sanctioned: {dashboardSummary?.total_approved_intake || 0} Seats</span>
                  <span>Enrolled: {dashboardSummary?.total_actual_enrolled || 0} Regular Students</span>
                  <span>Supernumerary: {dashboardSummary?.total_supernumerary_enrolled || 0}</span>
                </div>
              </div>

              {/* Course-level highlights */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-3">
                {(dashboardSummary?.programme_breakdown || reconciliation).map((r: any, i: number) => (
                  <div key={i} className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF] space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-serif font-medium text-[#1C1917] text-xs truncate max-w-[180px]">
                        {r.course_name || r.course}
                      </span>
                      <Badge variant={r.is_over_admitted ? 'danger' : 'success'}>
                        {r.is_over_admitted ? 'Over-Admitted' : 'Valid'}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-[#78716C]">
                      <span>Regular: {r.regular_enrolled} / {r.approved_intake}</span>
                      <span>Occupancy: {r.utilization_pct || r.occupancy_rate || 0}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Right 1 Col: Quick Workflow Actions */}
            <div className="bg-white p-6 rounded-2xl border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-4">
              <h3 className="text-base font-serif font-medium text-[#1C1917] flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-[#C2410C]" />
                Administrative Actions
              </h3>
              <p className="text-xs text-[#78716C]">
                Institutional student management operations integrated with central AICTE verification services.
              </p>

              <div className="space-y-2.5 pt-2">
                <button
                  onClick={handleOpenAdd}
                  className="w-full flex items-center justify-between p-3 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF] hover:border-[#D5D3CA] hover:bg-white text-left transition-all group shadow-sm"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-200/60 flex items-center justify-center text-emerald-800">
                      <PlusCircle className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="font-medium text-[#1C1917] text-xs">Onboard Single Student</p>
                      <p className="text-[10px] text-[#78716C]">Individual APAAR Verhoeff verification</p>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-[#A8A29E] group-hover:text-[#1C1917] transition-colors" />
                </button>

                <button
                  onClick={onNavigateToImport}
                  className="w-full flex items-center justify-between p-3 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF] hover:border-[#D5D3CA] hover:bg-white text-left transition-all group shadow-sm"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-sky-50 border border-sky-200/60 flex items-center justify-center text-sky-800">
                      <FileSpreadsheet className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="font-medium text-[#1C1917] text-xs">CSV Bulk Import Wizard</p>
                      <p className="text-[10px] text-[#78716C]">Column mapping & dry-run validation</p>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-[#A8A29E] group-hover:text-[#1C1917] transition-colors" />
                </button>

                <button
                  onClick={() => setActiveTab('directory')}
                  className="w-full flex items-center justify-between p-3 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF] hover:border-[#D5D3CA] hover:bg-white text-left transition-all group shadow-sm"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-stone-100 border border-stone-200 flex items-center justify-center text-stone-800">
                      <Users className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="font-medium text-[#1C1917] text-xs">Search Student Directory</p>
                      <p className="text-[10px] text-[#78716C]">Multi-criteria search & record audit</p>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-[#A8A29E] group-hover:text-[#1C1917] transition-colors" />
                </button>

                <a
                  href={getIntakeCompliancePdfUrl(institutionId)}
                  target="_blank"
                  rel="noreferrer"
                  className="w-full flex items-center justify-between p-3 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF] hover:border-[#D5D3CA] hover:bg-white text-left transition-all group shadow-sm"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-amber-50 border border-amber-200/60 flex items-center justify-center text-amber-900">
                      <Download className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="font-medium text-[#1C1917] text-xs">Download Compliance PDF</p>
                      <p className="text-[10px] text-[#78716C]">Official AICTE statutory schedule</p>
                    </div>
                  </div>
                  <ExternalLink className="w-4 h-4 text-[#A8A29E] group-hover:text-[#1C1917] transition-colors" />
                </a>
              </div>
            </div>

          </div>

          {/* Operational Feeds */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            
            {/* Feed 1: Recent Upload Jobs */}
            <div className="bg-white p-6 rounded-2xl border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-serif font-medium text-[#1C1917] flex items-center gap-2">
                    <FileSpreadsheet className="w-4 h-4 text-[#78716C]" />
                    Recent Upload Jobs & Ingestions
                  </h3>
                  <p className="text-xs text-[#78716C]">
                    Bulk admission rosters submitted by this institution
                  </p>
                </div>
                {dashboardSummary && dashboardSummary.failed_import_jobs_count > 0 && (
                  <Badge variant="danger">{dashboardSummary.failed_import_jobs_count} Requires Attention</Badge>
                )}
              </div>

              <div className="space-y-2.5">
                {dashboardSummary && dashboardSummary.recent_uploads.length > 0 ? (
                  dashboardSummary.recent_uploads.map((job) => (
                    <div
                      key={job.id}
                      className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF] flex items-center justify-between text-xs"
                    >
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-[#1C1917] font-mono">{job.filename}</span>
                          <Badge
                            variant={
                              job.status === 'COMPLETED'
                                ? 'success'
                                : job.status === 'FAILED'
                                ? 'danger'
                                : 'warning'
                            }
                          >
                            {job.status}
                          </Badge>
                        </div>
                        <p className="text-[11px] text-[#78716C]">
                          Session {job.academic_year} • {job.created_at}
                        </p>
                      </div>
                      <div className="text-right">
                        <span className="font-medium text-[#1C1917]">{job.total_records} Records</span>
                        <p className="text-[10px] text-[#78716C]">
                          <span className="text-[#15803D] font-medium">{job.valid_records} Valid</span>
                          {job.error_records > 0 && (
                            <span className="text-rose-700 font-medium ml-1.5">({job.error_records} Errors)</span>
                          )}
                        </p>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-6 text-center text-xs text-[#78716C]">
                    No bulk upload jobs recorded yet.
                  </div>
                )}
              </div>
            </div>

            {/* Feed 2: Recent Verifications */}
            <div className="bg-white p-6 rounded-2xl border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-serif font-medium text-[#1C1917] flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-[#15803D]" />
                    Recent Verifications for this Campus
                  </h3>
                  <p className="text-xs text-[#78716C]">
                    Employer and authorized third-party credential checks
                  </p>
                </div>
                <Badge variant="info">Verified Credentials</Badge>
              </div>

              <div className="space-y-2.5">
                {dashboardSummary && dashboardSummary.recent_verifications.length > 0 ? (
                  dashboardSummary.recent_verifications.map((verif) => (
                    <div
                      key={verif.id}
                      className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF] flex items-center justify-between text-xs"
                    >
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-[#1C1917]">{verif.verifier_name}</span>
                          <Badge variant={verif.verification_result === 'VERIFIED' ? 'success' : 'danger'}>
                            {verif.verification_result}
                          </Badge>
                        </div>
                        <p className="text-[11px] text-[#78716C]">
                          {verif.verifier_organization} • {verif.purpose}
                        </p>
                        <p className="text-[10px] text-[#57534E] font-mono">
                          Student: {verif.student_name} ({verif.apaar_masked})
                        </p>
                      </div>
                      <div className="text-right text-[10px] text-[#A8A29E]">
                        {verif.created_at}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-6 text-center text-xs text-[#78716C]">
                    No recent verification inquiries on record.
                  </div>
                )}
              </div>
            </div>

          </div>

        </div>
      )}

      {/* ========================================================
          TAB 2: STUDENT DIRECTORY
         ======================================================== */}
      {activeTab === 'directory' && (
        <div className="bg-white p-6 rounded-2xl border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-6 animate-fade-in">
          
          {/* Header Bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-serif font-medium text-[#1C1917] flex items-center gap-2">
                <Users className="w-5 h-5 text-[#78716C]" />
                Institutional Student Directory
              </h2>
              <p className="text-xs text-[#78716C] mt-0.5">
                Multi-dimensional search with privacy-masked APAAR IDs (•••• •••• XXXX) and full audit history.
              </p>
            </div>

            <div className="flex items-center gap-2.5">
              <a
                href={getExportStudentsUrl(institutionId)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#FAF9F5] hover:bg-[#F4F3EE] text-[#57534E] text-xs font-medium border border-[#E5E4DF] transition-all shrink-0"
              >
                <Download className="w-3.5 h-3.5 text-[#78716C]" />
                Export CSV
              </a>
              <button
                onClick={handleOpenAdd}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[#1C1917] hover:bg-[#292524] text-white text-xs font-medium transition-all shadow-sm shrink-0"
              >
                <PlusCircle className="w-3.5 h-3.5" />
                Add Student
              </button>
            </div>
          </div>

          {/* Multi-Criteria Filters Bar */}
          <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF] space-y-3">
            <div className="flex items-center justify-between text-xs font-medium text-[#1C1917]">
              <span className="flex items-center gap-1.5 font-serif">
                <Filter className="w-3.5 h-3.5 text-[#78716C]" />
                Multi-Criteria Directory Filters
              </span>
              {(search || programmeFilter !== 'ALL' || courseFilter !== 'ALL' || academicYearFilter !== 'ALL' || admissionStatusFilter !== 'ALL' || recordStatusFilter !== 'ALL') && (
                <button
                  onClick={handleResetFilters}
                  className="text-xs text-[#C2410C] hover:underline font-medium"
                >
                  Clear All Filters
                </button>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
              {/* Search input */}
              <div className="lg:col-span-2 relative">
                <Search className="w-4 h-4 text-[#A8A29E] absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Search name, roll no, APAAR..."
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="w-full bg-white border border-[#E5E4DF] rounded-xl pl-9 pr-3 py-1.5 text-xs text-[#1C1917] focus:outline-none focus:border-[#1C1917]"
                />
              </div>

              {/* Programme Filter */}
              <div>
                <select
                  value={programmeFilter}
                  onChange={(e) => {
                    setProgrammeFilter(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="w-full bg-white border border-[#E5E4DF] rounded-xl px-2.5 py-1.5 text-xs text-[#57534E] focus:outline-none focus:border-[#1C1917]"
                >
                  <option value="ALL">All Programmes</option>
                  {programmes.map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>

              {/* Course Filter */}
              <div>
                <select
                  value={courseFilter}
                  onChange={(e) => {
                    setCourseFilter(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="w-full bg-white border border-[#E5E4DF] rounded-xl px-2.5 py-1.5 text-xs text-[#57534E] focus:outline-none focus:border-[#1C1917]"
                >
                  <option value="ALL">All Courses</option>
                  {courses.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>

              {/* Academic Year Filter */}
              <div>
                <select
                  value={academicYearFilter}
                  onChange={(e) => {
                    setAcademicYearFilter(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="w-full bg-white border border-[#E5E4DF] rounded-xl px-2.5 py-1.5 text-xs text-[#57534E] focus:outline-none focus:border-[#1C1917]"
                >
                  <option value="ALL">All Sessions</option>
                  <option value="2024-2025">2024-2025</option>
                  <option value="2023-2024">2023-2024</option>
                </select>
              </div>

              {/* Admission Status Filter */}
              <div>
                <select
                  value={admissionStatusFilter}
                  onChange={(e) => {
                    setAdmissionStatusFilter(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="w-full bg-white border border-[#E5E4DF] rounded-xl px-2.5 py-1.5 text-xs text-[#57534E] focus:outline-none focus:border-[#1C1917]"
                >
                  <option value="ALL">All Statuses</option>
                  <option value="ENROLLED">Enrolled</option>
                  <option value="ADMITTED">Admitted</option>
                  <option value="PROVISIONAL">Provisional</option>
                  <option value="SUSPENDED">Suspended</option>
                  <option value="COMPLETED">Completed</option>
                </select>
              </div>
            </div>
          </div>

          {/* Directory Table */}
          <div className="overflow-x-auto rounded-xl border border-[#E5E4DF]">
            <table className="w-full text-left text-xs text-[#57534E]">
              <thead className="bg-[#FAF9F5] text-[11px] font-medium uppercase tracking-wider text-[#78716C] border-b border-[#E5E4DF]">
                <tr>
                  <th className="py-3 px-4">Roll No</th>
                  <th className="py-3 px-4">Student Name</th>
                  <th className="py-3 px-4">Course & Domain</th>
                  <th className="py-3 px-4 font-mono">Masked APAAR ID</th>
                  <th className="py-3 px-3 text-center">Session</th>
                  <th className="py-3 px-3 text-center">Quota / Category</th>
                  <th className="py-3 px-3 text-center">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E4DF] font-sans">
                {directoryLoading ? (
                  <tr>
                    <td colSpan={8} className="py-12 text-center text-[#78716C]">
                      <RefreshCw className="w-5 h-5 animate-spin mx-auto text-[#C2410C] mb-2" />
                      Loading filtered roster...
                    </td>
                  </tr>
                ) : students.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-12 text-center text-[#78716C]">
                      No student records match the active search and filter criteria.
                    </td>
                  </tr>
                ) : (
                  students.map((s) => (
                    <tr key={s.id} className="hover:bg-[#FAF9F5] transition-colors">
                      <td className="py-3 px-4 font-mono font-medium text-[#1C1917]">{s.internal_id}</td>
                      <td className="py-3 px-4">
                        <p className="font-serif font-medium text-[#1C1917] text-sm">{s.student_name}</p>
                        <p className="text-[10px] text-[#78716C]">DOB: {s.date_of_birth} • {s.gender}</p>
                      </td>
                      <td className="py-3 px-4">
                        <p className="text-[#1C1917] font-medium">{s.course}</p>
                        <p className="text-[10px] text-[#78716C]">{s.programme}</p>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-1.5 font-mono text-[#15803D] font-medium">
                          <span>{s.apaar_masked}</span>
                        </div>
                      </td>
                      <td className="py-3 px-3 text-center font-mono text-[#78716C]">
                        {s.academic_year}
                      </td>
                      <td className="py-3 px-3 text-center">
                        {s.is_supernumerary ? (
                          <Badge variant="saffron">{s.supernumerary_type}</Badge>
                        ) : (
                          <Badge variant="neutral">{s.category}</Badge>
                        )}
                      </td>
                      <td className="py-3 px-3 text-center">
                        <Badge
                          variant={
                            s.admission_status === 'ENROLLED'
                              ? 'success'
                              : s.admission_status === 'ADMITTED'
                              ? 'info'
                              : 'warning'
                          }
                        >
                          {s.admission_status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => setSelectedStudentForDetail(s.id)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-white border border-[#E5E4DF] text-[#1C1917] hover:bg-[#F4F3EE] text-xs font-medium transition-all shadow-sm"
                            title="View Record Details & Change History"
                          >
                            <Eye className="w-3 h-3" />
                            Details
                          </button>
                          <button
                            onClick={() => handleOpenEdit(s)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-[#FAF9F5] border border-[#E5E4DF] text-[#57534E] hover:bg-[#F4F3EE] text-xs font-medium transition-all"
                            title="Edit Student Information"
                          >
                            <Edit2 className="w-3 h-3" />
                            Edit
                          </button>
                          <button
                            onClick={() => onViewStudentCredential(s.id)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 hover:bg-emerald-100 text-xs font-medium transition-all"
                            title="View Verifiable Credential Pass"
                          >
                            Pass
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-2 border-t border-[#E5E4DF]">
            <div className="flex items-center gap-3 text-xs text-[#78716C]">
              <span>
                Showing {students.length === 0 ? 0 : (currentPage - 1) * limit + 1} to{' '}
                {Math.min(currentPage * limit, totalStudents)} of {totalStudents} records
              </span>
              <span>•</span>
              <div className="flex items-center gap-1">
                <span>Per Page:</span>
                <select
                  value={limit}
                  onChange={(e) => {
                    setLimit(Number(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="bg-[#FAF9F5] border border-[#E5E4DF] rounded-lg px-2 py-1 text-xs text-[#57534E] focus:outline-none"
                >
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                </select>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                disabled={currentPage <= 1 || directoryLoading}
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-white border border-[#E5E4DF] hover:bg-[#F4F3EE] text-xs text-[#57534E] disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-sm"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                Previous
              </button>
              <span className="text-xs font-medium text-[#1C1917] px-2 font-mono">
                {currentPage} / {totalPages || 1}
              </span>
              <button
                disabled={currentPage >= totalPages || directoryLoading}
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-white border border-[#E5E4DF] hover:bg-[#F4F3EE] text-xs text-[#57534E] disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-sm"
              >
                Next
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

        </div>
      )}

      {/* ========================================================
          TAB 3: INTAKE AND ENROLMENT MONITORING
         ======================================================== */}
      {activeTab === 'reconciliation' && (
        <div className="bg-white p-6 rounded-2xl border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-4 animate-fade-in">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-serif font-medium text-[#1C1917] flex items-center gap-2">
                <Layers className="w-5 h-5 text-[#78716C]" />
                Course-by-Course Intake Audit & Reconciliation
              </h2>
              <p className="text-xs text-[#78716C]">
                Statutory AICTE reconciliation: Core Approved Intake is strictly separated from Supernumerary Quotas (TFW 5%, NRI 5%, FN 15%).
              </p>
            </div>
            <a
              href={getIntakeCompliancePdfUrl(institutionId)}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-[#FAF9F5] hover:bg-[#F4F3EE] text-[#1C1917] text-xs font-medium border border-[#E5E4DF] shadow-sm transition-all shrink-0"
            >
              <Download className="w-3.5 h-3.5 text-[#78716C]" />
              Formal Audit Schedule (PDF)
            </a>
          </div>

          <div className="overflow-x-auto rounded-xl border border-[#E5E4DF]">
            <table className="w-full text-left text-xs text-[#57534E]">
              <thead className="bg-[#FAF9F5] text-[11px] font-medium uppercase tracking-wider text-[#78716C] border-b border-[#E5E4DF]">
                <tr>
                  <th className="py-3 px-4">Course Title & Domain</th>
                  <th className="py-3 px-3 text-center">Approved Intake</th>
                  <th className="py-3 px-3 text-center">Regular Enrolled</th>
                  <th className="py-3 px-3 text-center">Vacancy / Variance</th>
                  <th className="py-3 px-3 text-center">TFW Enrolled (5%)</th>
                  <th className="py-3 px-3 text-center">NRI / FN Enrolled</th>
                  <th className="py-3 px-3 text-center font-medium">Total Confirmed</th>
                  <th className="py-3 px-4 text-center">Compliance Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E4DF] font-sans">
                {reconciliation.map((row, idx) => (
                  <tr key={idx} className="hover:bg-[#FAF9F5] transition-colors">
                    <td className="py-3 px-4">
                      <p className="font-serif font-medium text-[#1C1917] text-sm">{row.course}</p>
                      <p className="text-[10px] text-[#78716C]">{row.programme}</p>
                    </td>
                    <td className="py-3 px-3 text-center font-medium text-[#1C1917]">{row.approved_intake}</td>
                    <td className="py-3 px-3 text-center font-medium text-[#15803D]">{row.regular_enrolled}</td>
                    <td className="py-3 px-3 text-center">
                      <span className={`font-medium ${row.variance < 0 ? 'text-rose-700 font-bold' : 'text-[#57534E]'}`}>
                        {row.variance < 0 ? `Over by ${Math.abs(row.variance)}` : `${row.variance} Seats`}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-center text-[#57534E]">
                      {row.tfw_enrolled} / <span className="text-[#A8A29E]">{row.tfw_quota}</span>
                    </td>
                    <td className="py-3 px-3 text-center text-[#57534E]">
                      {row.nri_enrolled + row.fn_enrolled} / <span className="text-[#A8A29E]">{row.nri_quota + row.fn_quota}</span>
                    </td>
                    <td className="py-3 px-3 text-center font-medium text-[#1C1917]">{row.total_students}</td>
                    <td className="py-3 px-4 text-center">
                      {row.is_over_admitted ? (
                        <Badge variant="danger">Over-Admission Warning</Badge>
                      ) : (
                        <Badge variant="success">APH Compliant</Badge>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Student Record Detail Modal with Change History */}
      {selectedStudentForDetail && (
        <StudentDetailModal
          studentId={selectedStudentForDetail}
          onClose={() => setSelectedStudentForDetail(null)}
          onEditStudent={handleOpenEdit}
          onViewCredentialPass={onViewStudentCredential}
        />
      )}

      {/* Add / Edit Student Form Modal */}
      {isFormModalOpen && (
        <StudentFormModal
          isOpen={isFormModalOpen}
          onClose={() => setIsFormModalOpen(false)}
          onSuccess={handleFormSuccess}
          institutionId={institutionId}
          studentToEdit={studentToEdit}
        />
      )}

    </div>
  );
};
