export type UserRole =
  | 'AICTE_ADMIN'
  | 'INSTITUTE_ADMIN'
  | 'INSTITUTION_ADMIN'
  | 'INSTITUTION_OPERATOR'
  | 'STUDENT'
  | 'STUDENT_VIEWER'
  | 'VERIFIER'
  | 'AUTHORIZED_VERIFIER';

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  institution_id?: string;
  student_internal_id?: string;
}

export interface DemoProfile {
  role: UserRole;
  email: string;
  label: string;
  name: string;
  institution_id?: string;
  description: string;
  icon: string;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  role: UserRole;
  name: string;
  email: string;
  institution_id?: string;
  student_internal_id?: string;
}

export interface Programme {
  id: string;
  name: string;
  code: string;
  category?: string;
}

export interface Course {
  id: string;
  programme_id: string;
  name: string;
  code: string;
  level: string;
  duration_years: number;
}

export interface CourseIntake {
  id: number;
  institution_id: string;
  academic_year: string;
  programme: string;
  course: string;
  approved_intake: number;
  tfw_supernumerary_quota: number;
  nri_supernumerary_quota: number;
  fn_supernumerary_quota: number;
  status: string;
  actual_enrolment: number;
  actual_supernumerary: number;
  occupancy_rate: number;
  is_over_admitted: boolean;
}

export interface Institution {
  id: string;
  aicte_permanent_id: string;
  name: string;
  state: string;
  district: string;
  address?: string;
  institution_type: string;
  approval_session: string;
  contact_email?: string;
  contact_phone?: string;
  total_approved_intake: number;
  total_enrolled: number;
  intake_status: string;
  intakes: CourseIntake[];
}

export interface Student {
  id: string;
  internal_id: string;
  institution_id: string;
  institution_name: string;
  course_id?: string;
  course_name?: string;
  programme_id?: string;
  programme_name?: string;
  academic_year: string;
  programme: string;
  course: string;
  admission_year: number;
  apaar_masked: string;
  student_name: string;
  date_of_birth: string;
  gender: string;
  category: string;
  is_supernumerary: boolean;
  supernumerary_type: string;
  nri_status: boolean;
  oci_status: boolean;
  foreign_national_status: boolean;
  admission_status: string;
  record_status: string;
  discrepancy_reason?: string;
  verification_token: string;
  credential_signature: string;
}

export interface StudentUpdateIn {
  student_name: string;
  date_of_birth: string;
  gender: string;
  category: string;
  internal_student_id: string;
  course_id: string;
  academic_year: string;
  admission_year: number;
  admission_status: string;
  apaar_id?: string;
  is_supernumerary: boolean;
  supernumerary_type: string;
  nri_status: boolean;
  oci_status: boolean;
  foreign_national_status: boolean;
}

export interface StudentHistoryItem {
  id: number;
  event_type: string;
  actor_email: string;
  actor_role: string;
  timestamp: string;
  details?: string;
}

export interface StudentCredentialDetail extends Student {
  qr_payload: string;
  qr_code_base64: string;
  simulated_gateway_status?: {
    status: string;
    is_valid: boolean;
    aadhaar_linked?: boolean;
    abc_account_id?: string;
    registry_name?: string;
    is_simulated: boolean;
    gateway_notice: string;
  };
}

export interface BulkDryRunRowError {
  row_index: number;
  field_name: string;
  error_code: string;
  error_message: string;
  severity: string;
}

export interface BulkDryRunResult {
  total_rows: number;
  valid_rows_count: number;
  invalid_rows_count: number;
  duplicate_rows_count: number;
  preview_rows: any[];
  errors: BulkDryRunRowError[];
  can_commit: boolean;
}

export interface BulkCommitIn {
  filename: string;
  academic_year: string;
  institution_id?: string;
  rows: any[];
}

export interface BulkCommitSummary {
  job_id: string;
  filename: string;
  academic_year: string;
  total_records: number;
  accepted_count: number;
  rejected_count: number;
  duplicate_count: number;
  status: string;
  message: string;
}

export interface BulkUploadJob {
  id: string;
  institution_id: string;
  filename: string;
  academic_year: string;
  total_records: number;
  valid_records: number;
  error_records: number;
  status: string;
  created_at: string;
}

export interface PaginatedStudents {
  items: Student[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export interface NationalAnalytics {
  total_institutions: number;
  total_programmes: number;
  total_approved_intake: number;
  total_actual_enrolled: number;
  total_supernumerary_enrolled: number;
  overall_occupancy_rate: number;
  over_admission_violations: number;
  duplicate_apaar_violations: number;
  total_verifications_performed: number;
  recent_audit_actions: Array<{
    id: number;
    action: string;
    role: string;
    user_email: string;
    institution_id?: string;
    details: string;
    timestamp: string;
  }>;
}

// Replaced by unified DuplicateCollisionAlert

export interface StagedErrorRow {
  row_index: number;
  internal_id: string;
  student_name: string;
  date_of_birth: string;
  course: string;
  programme: string;
  apaar_id: string;
  errors: string[];
  category: string;
  supernumerary_type: string;
}

export interface ImportBatchResult {
  batch_id: string;
  filename: string;
  total_rows: number;
  valid_rows: number;
  error_rows: number;
  status: string;
  staged_errors: StagedErrorRow[];
}

export interface VerificationResult {
  status: 'VERIFIED' | 'INVALID_SIGNATURE' | 'NOT_FOUND' | 'REVOKED';
  is_valid: boolean;
  verification_code: string;
  student_name?: string;
  internal_id?: string;
  apaar_masked?: string;
  institution_name?: string;
  programme?: string;
  course?: string;
  academic_year?: string;
  admission_status?: string;
  digital_signature?: string;
  signature_verified: boolean;
  issued_on?: string;
  gateway_note: string;
}

export interface ValidationWorkbenchIssue {
  id: number;
  job_id?: string;
  institution_id?: string;
  institution_name?: string;
  student_id?: string;
  enrolment_id?: string;
  row_number?: number;
  rule_id: string;
  field_name: string;
  error_code: string;
  error_message: string;
  suggested_remediation?: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  anomaly_score: number;
  is_potential_anomaly: boolean;
  resolution_status: 'NEW' | 'UNDER_REVIEW' | 'RESOLVED' | 'DISMISSED';
  raw_data?: Record<string, any>;
  reviewed_by_user_id?: string;
  reviewed_by_email?: string;
  reviewed_at?: string;
  resolution_reason?: string;
  created_at?: string;
  updated_at?: string;
  student_name?: string;
  internal_student_id?: string;
  apaar_masked?: string;
}

export interface ValidationWorkbenchSummary {
  total_issues: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  new_count: number;
  under_review_count: number;
  resolved_count: number;
  dismissed_count: number;
  anomaly_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  is_potential_anomaly: boolean;
  rule_breakdown: Record<string, number>;
}

export interface ValidationWorkbenchResponse {
  items: ValidationWorkbenchIssue[];
  summary: ValidationWorkbenchSummary;
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export interface IssueStatusUpdateIn {
  resolution_status: string;
  resolution_reason: string;
  remediation_action?: string;
}

export interface BulkIssueReviewIn {
  issue_ids: number[];
  resolution_status: string;
  resolution_reason: string;
}

export interface ValidationAuditResponse {
  status: string;
  institution_id: string;
  academic_year: string;
  total_issues_found: number;
  new_issues_persisted: number;
  anomaly_score: number;
  risk_level: string;
  is_potential_anomaly: boolean;
  explanation: string;
}

// ----------------- AICTE COMMAND CENTER & ANALYTICS TYPES -----------------

export interface DuplicateCollisionAlert {
  apaar_hash: string;
  apaar_masked: string;
  student_name: string;
  student_id?: string;
  enrolments: Array<{
    institution_id: string;
    institution_name: string;
    course: string;
    internal_id: string;
    academic_year: string;
    status: string;
  }>;
  institutions_involved?: string[];
  courses_involved?: string[];
  academic_year?: string;
  flag: string;
}

export type DuplicateApaarAlert = DuplicateCollisionAlert;

export interface SeverityCounts {
  critical: number;
  high: number;
  medium: number;
  low: number;
  total: number;
}

export interface RecentUploadJobSummary {
  id: string;
  filename: string;
  institution_id: string;
  institution_name: string;
  academic_year: string;
  status: string;
  total_records: number;
  valid_records: number;
  error_records: number;
  created_at: string;
}

export interface RecentVerificationSummary {
  id: string;
  token: string;
  verifier_name: string;
  verifier_organization: string;
  purpose: string;
  verification_result: string;
  student_name?: string;
  apaar_masked?: string;
  institution_name?: string;
  created_at: string;
}

export interface ExcessInstitutionSummary {
  institution_id: string;
  institution_name: string;
  aicte_id: string;
  state: string;
  approved_intake: number;
  enrolled_count: number;
  excess_count: number;
}

export interface AicteCommandCenterSummary {
  total_registered_institutions: number;
  total_student_identities: number;  // Physical unique students
  total_active_enrolments: number;   // Active seat enrolments
  total_approved_intake: number;
  intake_utilization_pct: number;
  total_supernumerary_admissions: number;
  pending_validation_issues: SeverityCounts;
  duplicate_alerts_count: number;
  institutions_with_excess_enrolment: number;
  excess_institutions: ExcessInstitutionSummary[];
  recent_uploads: RecentUploadJobSummary[];
  failed_import_jobs_count: number;
  recent_verification_requests: RecentVerificationSummary[];
  data_completeness_pct: number;
  is_synthetic_data: boolean;
}

export interface StateEnrolmentStat {
  state: string;
  approved_intake: number;
  actual_enrolment: number;
  supernumerary_enrolment: number;
  institutions_count: number;
  utilization_rate: number;
}

export interface ProgrammeEnrolmentStat {
  programme_id: string;
  programme_name: string;
  programme_code: string;
  approved_intake: number;
  actual_enrolment: number;
  supernumerary_enrolment: number;
  utilization_rate: number;
}

export interface AcademicYearTrendStat {
  academic_year: string;
  approved_intake: number;
  actual_enrolment: number;
  supernumerary: number;
  utilization_rate: number;
}

export interface InstitutionIntakeVsEnrolmentStat {
  institution_id: string;
  institution_name: string;
  aicte_id: string;
  state: string;
  approved_intake: number;
  actual_enrolment: number;
  supernumerary: number;
  utilization_rate: number;
  is_over_admitted: boolean;
}

export interface CategoryBreakdownStat {
  category: string;
  count: number;
  percentage: number;
}

export interface QuotaBreakdownStat {
  quota: string;
  count: number;
  percentage: number;
}

export interface ValidationIssueTrendStat {
  rule_id: string;
  rule_name: string;
  severity: string;
  total_count: number;
  unresolved_count: number;
}

export interface InstitutionDataCompletenessStat {
  institution_id: string;
  institution_name: string;
  aicte_id: string;
  total_students: number;
  completeness_pct: number;
}

export interface TopInstitutionReviewStat {
  institution_id: string;
  institution_name: string;
  aicte_id: string;
  state: string;
  risk_score: number;
  risk_level: string;
  flags: string[];
  over_admitted_count: number;
  critical_issues_count: number;
  collision_count: number;
  completeness_pct: number;
}

export interface AicteAnalyticsResponse {
  academic_year_filter?: string;
  programme_filter?: string;
  state_filter?: string;
  enrolment_by_state: StateEnrolmentStat[];
  programme_wise_enrolment: ProgrammeEnrolmentStat[];
  academic_year_trends: AcademicYearTrendStat[];
  institution_intake_vs_enrolment: InstitutionIntakeVsEnrolmentStat[];
  category_breakdown: CategoryBreakdownStat[];
  quota_breakdown: QuotaBreakdownStat[];
  validation_issue_trends: ValidationIssueTrendStat[];
  data_completeness_by_institution: InstitutionDataCompletenessStat[];
  top_institutions_requiring_review: TopInstitutionReviewStat[];
  is_synthetic_data: boolean;
}

// ----------------- INSTITUTION DASHBOARD TYPES -----------------

export interface CourseIntakeOccupancyStat {
  course_id: string;
  course_name: string;
  degree: string;
  programme_name: string;
  approved_intake: number;
  regular_enrolled: number;
  supernumerary_enrolled: number;
  utilization_pct: number;
  is_over_admitted: boolean;
}

export interface InstitutionDashboardSummary {
  institution_id: string;
  institution_name: string;
  aicte_permanent_id: string;
  state: string;
  district: string;
  approval_session: string;
  institution_type: string;
  contact_email?: string;
  total_approved_intake: number;
  total_actual_enrolled: number;
  total_supernumerary_enrolled: number;
  intake_utilization_pct: number;
  intake_compliance_status: string;
  programme_breakdown: CourseIntakeOccupancyStat[];
  recent_uploads: RecentUploadJobSummary[];
  failed_import_jobs_count: number;
  unresolved_issues_count: number;
  unresolved_issues_by_severity: SeverityCounts;
  student_record_completeness_pct: number;
  missing_fields_breakdown: Record<string, number>;
  recent_verifications: RecentVerificationSummary[];
  is_synthetic_data: boolean;
}

