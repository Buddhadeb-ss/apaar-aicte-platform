import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  Building,
  Users,
  CheckCircle2,
  AlertTriangle,
  ArrowUpRight,
  Search,
  FileText,
  Clock,
  Download,
  Eye,
  RefreshCw,
  Filter,
  BarChart2,
  PieChart as PieIcon,
  ShieldCheck,
  AlertCircle,
  FileCheck,
  ExternalLink,
  ChevronRight,
  Info,
  Award
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
  CartesianGrid
} from 'recharts';
import {
  AicteCommandCenterSummary,
  AicteAnalyticsResponse,
  Institution,
  DuplicateCollisionAlert,
  Programme
} from '../types';
import {
  fetchAicteCommandCenter,
  fetchAicteAnalytics,
  fetchInstitutionsCompliance,
  fetchDuplicateApaarAlerts,
  fetchProgrammes,
  getIntakeCompliancePdfUrl
} from '../services/api';
import { StatCard } from '../components/StatCard';
import { Badge } from '../components/Badge';
import { Modal } from '../components/Modal';

interface AicteDashboardProps {
  onSelectInstitution: (institutionId: string) => void;
  onNavigateToWorkbench?: () => void;
}

export const AicteDashboard: React.FC<AicteDashboardProps> = ({
  onSelectInstitution,
  onNavigateToWorkbench
}) => {
  const [summary, setSummary] = useState<AicteCommandCenterSummary | null>(null);
  const [analytics, setAnalytics] = useState<AicteAnalyticsResponse | null>(null);
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [duplicates, setDuplicates] = useState<DuplicateCollisionAlert[]>([]);
  const [programmes, setProgrammes] = useState<Programme[]>([]);
  
  const [loading, setLoading] = useState<boolean>(true);
  const [analyticsLoading, setAnalyticsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [academicYear, setAcademicYear] = useState<string>('2024-2025');
  const [programmeFilter, setProgrammeFilter] = useState<string>('ALL');
  const [stateFilter, setStateFilter] = useState<string>('ALL');
  const [search, setSearch] = useState<string>('');
  const [complianceFilter, setComplianceFilter] = useState<string>('ALL');

  // Modals
  const [selectedDuplicate, setSelectedDuplicate] = useState<DuplicateCollisionAlert | null>(null);

  // Load initial Command Center & Static Rosters
  const loadCommandCenterData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [sumData, instData, dupData, progData] = await Promise.all([
        fetchAicteCommandCenter(),
        fetchInstitutionsCompliance(),
        fetchDuplicateApaarAlerts().catch(() => []),
        fetchProgrammes().catch(() => [])
      ]);
      setSummary(sumData);
      setInstitutions(instData);
      setDuplicates(dupData);
      setProgrammes(progData);
    } catch (err: any) {
      console.error('Failed to load command center data:', err);
      setError(err.message || 'Failed to connect to national registry services.');
    } finally {
      setLoading(false);
    }
  };

  // Load filtered Analytics from dynamic backend aggregation
  const loadAnalyticsData = async () => {
    try {
      setAnalyticsLoading(true);
      const data = await fetchAicteAnalytics({
        academic_year: academicYear,
        programme_id: programmeFilter,
        state: stateFilter
      });
      setAnalytics(data);
    } catch (err: any) {
      console.error('Failed to load analytics aggregation:', err);
    } finally {
      setAnalyticsLoading(false);
    }
  };

  useEffect(() => {
    loadCommandCenterData();
  }, []);

  useEffect(() => {
    loadAnalyticsData();
  }, [academicYear, programmeFilter, stateFilter]);

  // Unique States list for filter
  const availableStates = Array.from(new Set(institutions.map(i => i.state))).sort();

  // Filtered Technical Institutions for Directory Table
  const filteredInstitutions = institutions.filter((inst) => {
    const matchesSearch =
      inst.name.toLowerCase().includes(search.toLowerCase()) ||
      inst.aicte_permanent_id.toLowerCase().includes(search.toLowerCase()) ||
      inst.state.toLowerCase().includes(search.toLowerCase()) ||
      inst.district.toLowerCase().includes(search.toLowerCase());
    const statusVal = inst.intake_status || (inst as any).compliance_status || '';
    const matchesCompliance =
      complianceFilter === 'ALL' ||
      (complianceFilter === 'OVER_ADMITTED' && statusVal.includes('OVER_ADMISSION')) ||
      (complianceFilter === 'COMPLIANT' && statusVal === 'COMPLIANT');
    const matchesState = stateFilter === 'ALL' || inst.state === stateFilter;
    return matchesSearch && matchesCompliance && matchesState;
  });

  // Palette mappings for Charts in clean editorial tones
  const CATEGORY_COLORS: Record<string, string> = {
    GENERAL: '#1C1917',
    OBC: '#15803D',
    SC: '#C2410C',
    ST: '#B45309',
    EWS: '#4338CA'
  };

  const QUOTA_COLORS: Record<string, string> = {
    'Core Regular Intake': '#1C1917',
    'Tuition Fee Waiver (TFW)': '#15803D',
    'NRI Quota': '#C2410C',
    'Foreign National / PIO': '#B45309',
    'Other Supernumerary': '#4338CA'
  };

  if (loading && !summary) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[65vh] gap-3 text-[#1C1917]">
        <RefreshCw className="w-6 h-6 text-[#C2410C] animate-spin" />
        <p className="text-base font-serif font-medium text-[#1C1917]">Loading AICTE National Regulatory Directorate...</p>
        <span className="text-xs text-[#78716C] font-serif italic">Aggregating statutory intakes and APAAR collisions</span>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fade-in text-[#1C1917]">
      
      {/* 1. Unified Master Header & Analytics Filter Panel */}
      <div className="bg-white p-6 sm:p-7 rounded-2xl border border-[#E5E4DF] shadow-[0_2px_8px_rgba(0,0,0,0.03)] space-y-6">
        
        {/* Top Row: Title, Subtitle & Primary Actions */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 rounded-full text-xs font-medium bg-[#FDF8F6] text-[#C2410C] border border-[#EBDBD5]">
                Government of India • AICTE
              </span>
              <span className="px-3 py-1 rounded-full text-xs font-medium bg-[#F4F3EE] text-[#57534E] border border-[#E5E4DF]">
                National Regulatory Scrutiny
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-serif font-normal text-[#1C1917] tracking-tight">
              AICTE National Command Center
            </h1>
            <p className="text-xs sm:text-sm text-[#57534E] font-serif leading-relaxed">
              Real-time oversight of technical college seat capacities, student enrolments, and duplicate APAAR ID detection across India.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            {onNavigateToWorkbench && (
              <button
                onClick={onNavigateToWorkbench}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-rose-50 hover:bg-rose-100 text-rose-800 text-xs sm:text-sm font-medium transition-all border border-rose-200 shadow-sm"
              >
                <ShieldAlert className="w-4 h-4 text-rose-700" />
                <span>Validation Workbench ({summary?.pending_validation_issues.total || 0})</span>
              </button>
            )}
            <button
              onClick={() => {
                loadCommandCenterData();
                loadAnalyticsData();
              }}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#FAF9F5] hover:bg-[#F4F3EE] text-[#1C1917] text-xs sm:text-sm font-medium border border-[#E5E4DF] transition-all shadow-sm"
            >
              <RefreshCw className={`w-4 h-4 ${loading || analyticsLoading ? 'animate-spin' : ''}`} />
              <span>Refresh Console</span>
            </button>
          </div>
        </div>

        {/* Integrated Filter & System Status Row */}
        <div className="pt-5 border-t border-[#F4F3EE] flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-4 text-xs">
            <div className="flex items-center gap-2 font-medium text-[#1C1917]">
              <Filter className="w-4 h-4 text-[#78716C]" />
              <span className="font-serif">Filter Overview by:</span>
            </div>

            {/* Academic Year Filter */}
            <div className="flex items-center gap-1.5">
              <span className="text-[#78716C]">Session:</span>
              <select
                value={academicYear}
                onChange={(e) => setAcademicYear(e.target.value)}
                className="bg-[#FAF9F5] border border-[#E5E4DF] rounded-lg px-3 py-1.5 text-xs text-[#1C1917] font-medium focus:outline-none focus:border-[#1C1917]"
              >
                <option value="ALL">All Academic Years</option>
                <option value="2024-2025">2024-2025 (Current Session)</option>
                <option value="2023-2024">2023-2024</option>
                <option value="2022-2023">2022-2023</option>
              </select>
            </div>

            {/* Programme Filter */}
            <div className="flex items-center gap-1.5">
              <span className="text-[#78716C]">Programme:</span>
              <select
                value={programmeFilter}
                onChange={(e) => setProgrammeFilter(e.target.value)}
                className="bg-[#FAF9F5] border border-[#E5E4DF] rounded-lg px-3 py-1.5 text-xs text-[#1C1917] font-medium focus:outline-none focus:border-[#1C1917]"
              >
                <option value="ALL">All Programmes</option>
                {programmes.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>

            {/* State Filter */}
            <div className="flex items-center gap-1.5">
              <span className="text-[#78716C]">State:</span>
              <select
                value={stateFilter}
                onChange={(e) => setStateFilter(e.target.value)}
                className="bg-[#FAF9F5] border border-[#E5E4DF] rounded-lg px-3 py-1.5 text-xs text-[#1C1917] font-medium focus:outline-none focus:border-[#1C1917]"
              >
                <option value="ALL">All States</option>
                {availableStates.map((st) => (
                  <option key={st} value={st}>
                    {st}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs text-[#78716C]">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#FAF9F5] border border-[#E5E4DF] font-mono text-[11px]">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
              Live Relational DB • RFC 4122 Checksum
            </span>
          </div>
        </div>

      </div>

      {/* 3. Executive KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* KPI 1: Total Registered Institutions */}
        <StatCard
          title="Approved Institutions"
          value={summary?.total_registered_institutions || 0}
          subtitle="AICTE Permanent Affiliated IDs"
          icon={<Building className="w-5 h-5" />}
          accent="blue"
        />

        {/* KPI 2: Approved Intake vs Enrolment */}
        <StatCard
          title="Approved Intake vs Active"
          value={`${summary?.total_approved_intake || 0}`}
          subtitle={`${summary?.total_active_enrolments || 0} Active Seats Enrolled (${summary?.intake_utilization_pct || 0}%)`}
          icon={<Users className="w-5 h-5" />}
          accent="orange"
        />

        {/* KPI 3: Student Identities vs Seat Enrolments */}
        <StatCard
          title="Unique Students"
          value={summary?.total_student_identities || 0}
          subtitle={`${summary?.total_active_enrolments || 0} Total Active Program Enrolments`}
          icon={<CheckCircle2 className="w-5 h-5" />}
          accent="emerald"
        />

        {/* KPI 4: Supernumerary Admissions */}
        <StatCard
          title="Supernumerary Seats"
          value={summary?.total_supernumerary_admissions || 0}
          subtitle="TFW (5%), NRI (5%), Foreign National (15%)"
          icon={<Award className="w-5 h-5" />}
          accent="amber"
        />

        {/* KPI 5: Pending Validation Issues */}
        <div
          onClick={onNavigateToWorkbench}
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
              {summary?.pending_validation_issues.total || 0}
            </span>
            <span className="text-xs text-[#78716C]">Rules Flagged</span>
          </div>
          <div className="flex items-center gap-1.5 pt-1 text-[11px]">
            <span className="px-2 py-0.5 rounded-full bg-rose-50 text-rose-800 border border-rose-200 font-medium">
              {summary?.pending_validation_issues.critical || 0} Crit
            </span>
            <span className="px-2 py-0.5 rounded-full bg-amber-50 text-amber-900 border border-amber-200 font-medium">
              {summary?.pending_validation_issues.high || 0} High
            </span>
            <span className="px-2 py-0.5 rounded-full bg-[#F4F3EE] text-[#57534E] border border-[#E5E4DF] font-medium">
              {summary?.pending_validation_issues.medium || 0} Med
            </span>
          </div>
        </div>

        {/* KPI 6: Concurrent Multi-Institution Enrolment Collision Alert */}
        <div
          onClick={() => {
            if (duplicates.length > 0) setSelectedDuplicate(duplicates[0]);
          }}
          className={`cursor-pointer group p-5 rounded-xl border transition-all space-y-2 ${
            (summary?.duplicate_alerts_count || 0) > 0
              ? 'border-amber-300 bg-amber-50/40 hover:border-amber-400'
              : 'border-[#E5E4DF] bg-white'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-[#78716C] uppercase tracking-wider">Cross-College Collisions</span>
            <div className="p-2 rounded-lg bg-amber-50 border border-amber-200 text-amber-800">
              <AlertTriangle className="w-5 h-5" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-serif font-medium text-amber-900">
              {summary?.duplicate_alerts_count || 0}
            </span>
            <span className="text-xs text-[#78716C]">Active Violations</span>
          </div>
          <p className="text-[11px] text-amber-900/90 pt-1 flex items-center justify-between font-serif">
            <span>Identical APAAR multi-campus</span>
            <span className="text-[11px] underline font-sans text-amber-800 font-medium">Click to Audit</span>
          </p>
        </div>

        {/* KPI 7: Institutions with Excess Enrolment */}
        <div
          onClick={() => {
            setComplianceFilter('OVER_ADMITTED');
            const el = document.getElementById('institutions-directory-section');
            if (el) el.scrollIntoView({ behavior: 'smooth' });
          }}
          className="cursor-pointer group bg-white p-5 rounded-xl border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.03)] hover:border-[#D5D3CA] transition-all space-y-2"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-[#78716C] uppercase tracking-wider">Excess Enrolment Campuses</span>
            <div className="p-2 rounded-lg bg-[#FAF9F5] border border-[#E5E4DF] text-[#1C1917]">
              <AlertCircle className="w-5 h-5" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-serif font-medium text-[#1C1917]">
              {summary?.institutions_with_excess_enrolment || 0}
            </span>
            <span className="text-xs text-[#78716C]">Campuses Flagged</span>
          </div>
          <p className="text-[11px] text-[#78716C] pt-1 flex items-center justify-between font-serif">
            <span>Seat cap overflow violations</span>
            <span className="text-[11px] text-[#C2410C] font-sans font-medium">Filter Roster</span>
          </p>
        </div>

        {/* KPI 8: Data Completeness Score */}
        <StatCard
          title="Data Completeness"
          value={`${summary?.data_completeness_pct || 0}%`}
          subtitle="Mandatory Demographic & Intake Fields"
          icon={<ShieldCheck className="w-5 h-5" />}
          accent="blue"
        />

      </div>

      {/* 4. Visual Statutory Analytics Section */}
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl sm:text-2xl font-serif font-medium text-[#1C1917] flex items-center gap-2">
              <BarChart2 className="w-5 h-5 text-[#C2410C]" />
              National Seat Capacity & Enrolment Analytics
            </h2>
            <p className="text-xs sm:text-sm text-[#57534E] font-serif italic mt-0.5">
              Live server-side charts showing college capacity utilization, quota distributions, and demographic trends.
            </p>
          </div>
          {analyticsLoading && (
            <div className="flex items-center gap-1.5 text-xs text-[#C2410C]">
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              <span>Updating charts...</span>
            </div>
          )}
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Chart 1: Institution Intake vs Actual Enrolment */}
          <div className="lg:col-span-2 bg-white p-6 rounded-2xl border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-serif font-medium text-[#1C1917]">
                  College Seats vs. Enrolled Students
                </h3>
                <p className="text-xs text-[#78716C]">
                  Sanctioned government seat limits compared against regular and supernumerary admissions.
                </p>
              </div>
              <Badge variant="info">Session {academicYear}</Badge>
            </div>
            
            <div className="h-72 w-full">
              {analytics && analytics.institution_intake_vs_enrolment.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={analytics.institution_intake_vs_enrolment}
                    margin={{ top: 10, right: 10, left: -20, bottom: 25 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#E5E4DF" />
                    <XAxis
                      dataKey="institution_name"
                      stroke="#78716C"
                      fontSize={11}
                      interval={0}
                      tickFormatter={(val) => val.length > 18 ? `${val.slice(0, 15)}...` : val}
                      angle={-15}
                      textAnchor="end"
                    />
                    <YAxis stroke="#78716C" fontSize={11} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#FFFFFF',
                        borderColor: '#E5E4DF',
                        borderRadius: '12px',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.06)',
                        color: '#1C1917',
                        fontSize: '12px'
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                    <Bar dataKey="approved_intake" fill="#1C1917" radius={[4, 4, 0, 0]} name="Sanctioned Intake" />
                    <Bar dataKey="actual_enrolment" fill="#15803D" radius={[4, 4, 0, 0]} name="Regular Enrolled" />
                    <Bar dataKey="supernumerary" fill="#C2410C" radius={[4, 4, 0, 0]} name="Supernumerary" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-[#78716C] text-xs">
                  <BarChart2 className="w-8 h-8 mb-2 opacity-40" />
                  No institution records found for current filter criteria.
                </div>
              )}
            </div>
          </div>

          {/* Chart 2: Quota Breakdown Donut Chart */}
          <div className="bg-white p-6 rounded-2xl border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.03)] flex flex-col justify-between space-y-4">
            <div>
              <h3 className="text-sm font-serif font-medium text-[#1C1917]">
                Statutory Quota Distribution
              </h3>
              <p className="text-xs text-[#78716C]">
                Core Approved Seats vs TFW (5%), NRI (5%), FN (15%) Quotas
              </p>
            </div>

            <div className="h-56 w-full my-auto">
              {analytics && analytics.quota_breakdown.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={analytics.quota_breakdown}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={3}
                      dataKey="count"
                      nameKey="quota"
                    >
                      {analytics.quota_breakdown.map((entry, index) => (
                        <Cell
                          key={`quota-cell-${index}`}
                          fill={QUOTA_COLORS[entry.quota] || '#C2410C'}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#FFFFFF',
                        borderColor: '#E5E4DF',
                        borderRadius: '12px',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.06)',
                        color: '#1C1917',
                        fontSize: '12px'
                      }}
                      formatter={(val: any, name: any, item: any) => [
                        `${val} Students (${item.payload.percentage}%)`,
                        item.payload.quota
                      ]}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-[#78716C] text-xs">
                  No quota distribution data available.
                </div>
              )}
            </div>

            {/* Quota Legend */}
            <div className="text-[11px] text-[#57534E] space-y-1.5 pt-2 border-t border-[#E5E4DF]">
              {analytics?.quota_breakdown.map((q, i) => (
                <div key={i} className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5 truncate max-w-[190px]">
                    <span
                      className="w-2.5 h-2.5 rounded-full shrink-0"
                      style={{ backgroundColor: QUOTA_COLORS[q.quota] || '#C2410C' }}
                    />
                    {q.quota}
                  </span>
                  <span className="font-semibold text-[#1C1917]">
                    {q.count} ({q.percentage}%)
                  </span>
                </div>
              ))}
            </div>
          </div>

        </div>

        {/* Secondary Charts: State Distribution & Category Breakdown */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Chart 3: Regional Enrolment by State */}
          <div className="bg-white p-6 rounded-2xl border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-4">
            <div>
              <h3 className="text-sm font-serif font-medium text-[#1C1917]">
                State / Regional Enrolment
              </h3>
              <p className="text-xs text-[#78716C]">
                Approved seats vs actual active admissions by state
              </p>
            </div>

            <div className="h-60 w-full">
              {analytics && analytics.enrolment_by_state.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={analytics.enrolment_by_state}
                    layout="vertical"
                    margin={{ top: 5, right: 20, left: 20, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#E5E4DF" />
                    <XAxis type="number" stroke="#78716C" fontSize={10} />
                    <YAxis dataKey="state" type="category" stroke="#78716C" fontSize={11} width={80} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#FFFFFF',
                        borderColor: '#E5E4DF',
                        borderRadius: '12px',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.06)',
                        color: '#1C1917',
                        fontSize: '12px'
                      }}
                    />
                    <Bar dataKey="approved_intake" fill="#1C1917" radius={[0, 4, 4, 0]} name="Approved Intake" />
                    <Bar dataKey="actual_enrolment" fill="#15803D" radius={[0, 4, 4, 0]} name="Enrolled" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-[#78716C] text-xs">
                  No state distribution data available.
                </div>
              )}
            </div>
          </div>

          {/* Chart 4: Academic Year Trends */}
          <div className="bg-white p-6 rounded-2xl border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-4">
            <div>
              <h3 className="text-sm font-serif font-medium text-[#1C1917]">
                Academic Session Trends
              </h3>
              <p className="text-xs text-[#78716C]">
                Intake capacity progression across academic sessions
              </p>
            </div>

            <div className="h-60 w-full">
              {analytics && analytics.academic_year_trends.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={analytics.academic_year_trends}
                    margin={{ top: 10, right: 10, left: -20, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#E5E4DF" />
                    <XAxis dataKey="academic_year" stroke="#78716C" fontSize={11} />
                    <YAxis stroke="#78716C" fontSize={11} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#FFFFFF',
                        borderColor: '#E5E4DF',
                        borderRadius: '12px',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.06)',
                        color: '#1C1917',
                        fontSize: '12px'
                      }}
                    />
                    <Bar dataKey="approved_intake" fill="#1C1917" radius={[4, 4, 0, 0]} name="Sanctioned Intake" />
                    <Bar dataKey="actual_enrolment" fill="#15803D" radius={[4, 4, 0, 0]} name="Enrolled" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-[#78716C] text-xs">
                  No academic trend data available.
                </div>
              )}
            </div>
          </div>

          {/* Chart 5: Category Breakdown */}
          <div className="bg-white p-6 rounded-2xl border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-4 flex flex-col justify-between">
            <div>
              <h3 className="text-sm font-serif font-medium text-[#1C1917]">
                Student Demographic Categories
              </h3>
              <p className="text-xs text-[#78716C]">
                National representation across statutory categories
              </p>
            </div>

            <div className="h-48 w-full my-auto">
              {analytics && analytics.category_breakdown.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={analytics.category_breakdown}
                      cx="50%"
                      cy="50%"
                      innerRadius={45}
                      outerRadius={75}
                      paddingAngle={3}
                      dataKey="count"
                      nameKey="category"
                    >
                      {analytics.category_breakdown.map((entry, index) => (
                        <Cell
                          key={`cat-cell-${index}`}
                          fill={CATEGORY_COLORS[entry.category] || '#78716C'}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#FFFFFF',
                        borderColor: '#E5E4DF',
                        borderRadius: '12px',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.06)',
                        color: '#1C1917',
                        fontSize: '12px'
                      }}
                      formatter={(val: any, name: any, item: any) => [
                        `${val} Students (${item.payload.percentage}%)`,
                        item.payload.category
                      ]}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-[#78716C] text-xs">
                  No category data available.
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-2 text-[11px] text-[#57534E] pt-2 border-t border-[#E5E4DF]">
              {analytics?.category_breakdown.map((c, i) => (
                <div key={i} className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: CATEGORY_COLORS[c.category] || '#78716C' }}
                    />
                    {c.category}
                  </span>
                  <span className="font-semibold text-[#1C1917]">
                    {c.percentage}%
                  </span>
                </div>
              ))}
            </div>
          </div>

        </div>
      </div>

      {/* 5. Top Institutions Requiring Review */}
      <div className="bg-white p-6 rounded-2xl border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-serif font-medium text-[#1C1917] flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-amber-700" />
              Institutions Requiring Regulatory Review
            </h3>
            <p className="text-xs text-[#78716C]">
              Transparent, explainable risk ranking based on over-intake, critical validation issues, cross-college collisions, and roster completeness.
            </p>
          </div>
          <span className="text-[11px] font-mono text-[#57534E] bg-[#FAF9F5] px-3 py-1 rounded-lg border border-[#E5E4DF]">
            Rule-Based Audit Scoring
          </span>
        </div>

        <div className="overflow-x-auto rounded-xl border border-[#E5E4DF]">
          <table className="w-full text-left text-xs text-[#57534E]">
            <thead className="bg-[#FAF9F5] text-[11px] font-medium uppercase tracking-wider text-[#78716C] border-b border-[#E5E4DF]">
              <tr>
                <th className="py-3 px-4">Permanent ID</th>
                <th className="py-3 px-4">Institution Name & State</th>
                <th className="py-3 px-4 text-center">Risk Level</th>
                <th className="py-3 px-4">Explainable Regulatory Flags</th>
                <th className="py-3 px-4 text-center">Completeness</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E5E4DF] font-sans">
              {analytics?.top_institutions_requiring_review.map((item) => (
                <tr key={item.institution_id} className="hover:bg-[#FAF9F5] transition-colors">
                  <td className="py-3 px-4 font-mono text-[#1C1917] font-medium">{item.aicte_id}</td>
                  <td className="py-3 px-4">
                    <p className="font-serif font-medium text-[#1C1917] text-sm">{item.institution_name}</p>
                    <p className="text-[11px] text-[#78716C]">{item.state}</p>
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span
                      className={`inline-block px-2.5 py-0.5 rounded-full text-[10px] font-medium tracking-wide ${
                        item.risk_level === 'CRITICAL'
                          ? 'bg-rose-50 text-rose-800 border border-rose-200'
                          : item.risk_level === 'HIGH'
                          ? 'bg-amber-50 text-amber-900 border border-amber-200'
                          : item.risk_level === 'MEDIUM'
                          ? 'bg-[#F4F3EE] text-[#57534E] border border-[#E5E4DF]'
                          : 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                      }`}
                    >
                      {item.risk_level} ({item.risk_score} pts)
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex flex-wrap gap-1.5">
                      {item.flags.map((flag, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-0.5 rounded text-[10px] bg-[#FAF9F5] border border-[#E5E4DF] text-[#57534E]"
                        >
                          {flag}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span className="font-medium text-[#1C1917]">{item.completeness_pct}%</span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={() => onSelectInstitution(item.institution_id)}
                      className="inline-flex items-center gap-1 px-3 py-1 rounded-lg bg-white hover:bg-[#F4F3EE] text-[#1C1917] text-xs font-medium border border-[#E5E4DF] transition-all shadow-sm"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 6. Operational Feeds: Bulk Uploads & Verifications */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Feed A: Recent Uploads */}
        <div className="bg-white p-6 rounded-2xl border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-serif font-medium text-[#1C1917] flex items-center gap-2">
                <FileText className="w-4 h-4 text-[#78716C]" />
                Recent Bulk Upload Jobs
              </h3>
              <p className="text-xs text-[#78716C]">
                Audited ingestion batches from participating institutions
              </p>
            </div>
            {summary && summary.failed_import_jobs_count > 0 && (
              <Badge variant="danger">{summary.failed_import_jobs_count} Requires Resolution</Badge>
            )}
          </div>

          <div className="space-y-2.5">
            {summary?.recent_uploads.map((job) => (
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
                    {job.institution_name} • Session {job.academic_year} • {job.created_at}
                  </p>
                </div>
                <div className="text-right">
                  <span className="font-medium text-[#1C1917]">{job.total_records} Total</span>
                  <p className="text-[10px] text-[#78716C]">
                    <span className="text-[#15803D] font-medium">{job.valid_records} Valid</span>
                    {job.error_records > 0 && (
                      <span className="text-rose-700 font-medium ml-1.5">({job.error_records} Errors)</span>
                    )}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Feed B: Recent Credential Verifications */}
        <div className="bg-white p-6 rounded-2xl border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-serif font-medium text-[#1C1917] flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-[#15803D]" />
                Recent Credential Verifications
              </h3>
              <p className="text-xs text-[#78716C]">
                Authorized third-party and employer background checks
              </p>
            </div>
            <Badge variant="info">Active Inquiries</Badge>
          </div>

          <div className="space-y-2.5">
            {summary?.recent_verification_requests.map((verif) => (
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
                    Candidate: {verif.student_name} ({verif.apaar_masked})
                  </p>
                </div>
                <div className="text-right text-[10px] text-[#A8A29E]">
                  <Clock className="w-3 h-3 inline mr-1" />
                  {verif.created_at}
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>

      {/* 7. Technical Institutions Directory Table */}
      <div id="institutions-directory-section" className="bg-white p-6 rounded-2xl border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-serif font-medium text-[#1C1917]">AICTE Technical Institutions Directory</h3>
            <p className="text-xs text-[#78716C]">
              Audit institutional seat caps, confirmed student rosters, and download official compliance certificates.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2.5">
            <div className="relative">
              <Search className="w-4 h-4 text-[#A8A29E] absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search college, ID, state..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="bg-[#FAF9F5] border border-[#E5E4DF] rounded-xl pl-9 pr-3 py-1.5 text-xs text-[#1C1917] focus:outline-none focus:border-[#1C1917] w-56"
              />
            </div>
            <select
              value={complianceFilter}
              onChange={(e) => setComplianceFilter(e.target.value)}
              className="bg-[#FAF9F5] border border-[#E5E4DF] rounded-xl px-3 py-1.5 text-xs text-[#57534E] focus:outline-none focus:border-[#1C1917]"
            >
              <option value="ALL">All Compliance</option>
              <option value="COMPLIANT">APH Compliant Only</option>
              <option value="OVER_ADMITTED">Over-Admissions Only</option>
            </select>
          </div>
        </div>

        {/* Institutions Table */}
        <div className="overflow-x-auto rounded-xl border border-[#E5E4DF]">
          <table className="w-full text-left text-xs text-[#57534E]">
            <thead className="bg-[#FAF9F5] text-[11px] font-medium uppercase tracking-wider text-[#78716C] border-b border-[#E5E4DF]">
              <tr>
                <th className="py-3 px-4">Permanent ID</th>
                <th className="py-3 px-4">Institution Name</th>
                <th className="py-3 px-4">State / District</th>
                <th className="py-3 px-4 text-center">Approved Intake</th>
                <th className="py-3 px-4 text-center">Confirmed Enrolled</th>
                <th className="py-3 px-4 text-center">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E5E4DF] font-sans">
              {filteredInstitutions.map((inst) => (
                <tr key={inst.id} className="hover:bg-[#FAF9F5] transition-colors">
                  <td className="py-3 px-4 font-mono text-[#1C1917] font-medium">{inst.aicte_permanent_id}</td>
                  <td className="py-3 px-4">
                    <p className="font-serif font-medium text-[#1C1917] text-sm">{inst.name}</p>
                    <p className="text-[10px] text-[#78716C]">{(inst.institution_type || 'TECHNICAL_COLLEGE').replace(/_/g, ' ')}</p>
                  </td>
                  <td className="py-3 px-4">{inst.state}, {inst.district}</td>
                  <td className="py-3 px-4 text-center font-medium text-[#1C1917]">{inst.total_approved_intake}</td>
                  <td className="py-3 px-4 text-center font-medium text-[#15803D]">{inst.total_enrolled}</td>
                  <td className="py-3 px-4 text-center">
                    {(inst.intake_status || (inst as any).compliance_status || '').includes('OVER_ADMISSION') ? (
                      <Badge variant="danger">Over-Admission</Badge>
                    ) : (
                      <Badge variant="success">APH Compliant</Badge>
                    )}
                  </td>
                  <td className="py-3 px-4 text-right space-x-2">
                    <button
                      onClick={() => onSelectInstitution(inst.id)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-white border border-[#E5E4DF] text-[#1C1917] hover:bg-[#F4F3EE] text-xs font-medium transition-all shadow-sm"
                    >
                      <Eye className="w-3 h-3" />
                      Inspect Dashboard
                    </button>
                    <a
                      href={getIntakeCompliancePdfUrl(inst.id)}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-[#FAF9F5] hover:bg-[#F4F3EE] text-[#57534E] text-xs font-medium transition-all border border-[#E5E4DF]"
                    >
                      <Download className="w-3 h-3" />
                      PDF Report
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 8. Concurrent Multi-Institution Enrolment Collision Modal */}
      <Modal
        isOpen={selectedDuplicate !== null}
        onClose={() => setSelectedDuplicate(null)}
        title="Concurrent Enrolment Collision Investigation"
      >
        {selectedDuplicate && (
          <div className="space-y-4 text-sm text-[#57534E]">
            <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
              <div>
                <h4 className="font-serif font-medium text-amber-900">Statutory Violation: Multi-College Enrolment</h4>
                <p className="text-xs text-amber-800/90 mt-1">
                  Under AICTE Approval Process Handbook (APH) rules, a full-time regular student cannot hold concurrent active admissions across multiple institutions under the same national APAAR ID.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 p-4 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF] text-xs">
              <div>
                <span className="text-[#78716C] block">Student Identity</span>
                <span className="font-serif font-medium text-[#1C1917] text-base">{selectedDuplicate.student_name}</span>
              </div>
              <div>
                <span className="text-[#78716C] block">Masked APAAR ID</span>
                <span className="font-mono font-medium text-[#15803D] text-sm">{selectedDuplicate.apaar_masked}</span>
              </div>
            </div>

            <div>
              <h5 className="text-xs font-medium text-[#1C1917] uppercase tracking-wider mb-2 font-serif">
                Active Concurrent Enrolments ({selectedDuplicate.enrolments.length}):
              </h5>
              <div className="space-y-2">
                {selectedDuplicate.enrolments.map((enr: any, i: number) => (
                  <div key={i} className="p-3 rounded-lg bg-[#FAF9F5] border border-[#E5E4DF] flex items-center justify-between text-xs">
                    <div>
                      <p className="font-medium text-[#1C1917]">{enr.institution_name}</p>
                      <p className="text-[10px] text-[#78716C]">
                        Course: {enr.course} • Roll: {enr.internal_id} • Session {enr.academic_year}
                      </p>
                    </div>
                    <Badge variant="danger">Concurrent Seat</Badge>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-4 border-t border-[#E5E4DF] flex justify-end gap-3">
              <button
                onClick={() => {
                  alert('Formal Clarification Notice issued to Registrars of both institutions via DigiLocker Gateway.');
                  setSelectedDuplicate(null);
                }}
                className="px-4 py-2 rounded-xl bg-[#1C1917] text-white font-medium text-xs hover:bg-[#292524] transition-all shadow-sm"
              >
                Issue Formal AICTE Inquiry Notice
              </button>
            </div>
          </div>
        )}
      </Modal>

    </div>
  );
};
