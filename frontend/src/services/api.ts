import {
  AuthTokenResponse,
  DemoProfile,
  UserProfile,
  NationalAnalytics,
  DuplicateApaarAlert,
  Institution,
  Student,
  StudentCredentialDetail,
  StudentUpdateIn,
  StudentHistoryItem,
  Programme,
  Course,
  BulkDryRunResult,
  BulkCommitIn,
  BulkCommitSummary,
  BulkUploadJob,
  PaginatedStudents,
  ImportBatchResult,
  VerificationResult,
  ValidationWorkbenchIssue,
  ValidationWorkbenchSummary,
  ValidationWorkbenchResponse,
  IssueStatusUpdateIn,
  BulkIssueReviewIn,
  ValidationAuditResponse,
  AicteCommandCenterSummary,
  AicteAnalyticsResponse,
  InstitutionDashboardSummary,
  DuplicateCollisionAlert
} from '../types';

const API_BASE = '/api';
const API_V1 = '/api/v1';

export const getAuthToken = (): string | null => {
  return localStorage.getItem('apaar_auth_token');
};

export const setAuthToken = (token: string): void => {
  localStorage.setItem('apaar_auth_token', token);
};

export const removeAuthToken = (): void => {
  localStorage.removeItem('apaar_auth_token');
};

const authHeaders = (): HeadersInit => {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

// ---------------- AUTH ----------------
export async function fetchDemoProfiles(): Promise<DemoProfile[]> {
  const res = await fetch(`${API_BASE}/auth/demo-profiles`);
  if (!res.ok) throw new Error('Failed to load demo evaluation profiles');
  return res.json();
}

export async function loginWithCredentials(email: string, password: string): Promise<AuthTokenResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Authentication failed');
  }
  const data: AuthTokenResponse = await res.json();
  setAuthToken(data.access_token);
  return data;
}

export async function quickDemoLogin(index: number): Promise<AuthTokenResponse> {
  const res = await fetch(`${API_BASE}/auth/demo-login/${index}`, { method: 'POST' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Demo login failed');
  }
  const data: AuthTokenResponse = await res.json();
  setAuthToken(data.access_token);
  return data;
}

export async function fetchCurrentUser(): Promise<UserProfile> {
  const res = await fetch(`${API_BASE}/auth/me`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Session expired');
  return res.json();
}

// ---------------- AICTE SCRUTINY ----------------
export async function fetchNationalAnalytics(): Promise<NationalAnalytics> {
  const res = await fetch(`${API_BASE}/aicte/analytics`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to fetch AICTE national analytics');
  return res.json();
}

export async function fetchInstitutionsCompliance(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/aicte/institutions`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to fetch institutions');
  return res.json();
}

export async function fetchDuplicateApaarAlerts(): Promise<DuplicateCollisionAlert[]> {
  const res = await fetch(`${API_V1}/dashboard/duplicates`, { headers: authHeaders() });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchAuditLogs(limit: number = 50): Promise<any[]> {
  const res = await fetch(`${API_BASE}/aicte/audit-logs?limit=${limit}`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to fetch audit trails');
  return res.json();
}

// ---------------- INSTITUTION & RECONCILIATION ----------------
export async function fetchInstitution(id: string): Promise<Institution> {
  const res = await fetch(`${API_BASE}/institutions/${id}`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to fetch institution profile');
  return res.json();
}

export async function fetchIntakeReconciliation(id: string): Promise<any> {
  const res = await fetch(`${API_BASE}/institutions/${id}/reconciliation`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to fetch intake reconciliation');
  return res.json();
}

export async function fetchProgrammes(): Promise<Programme[]> {
  const res = await fetch(`${API_V1}/institutions/programmes`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to load academic programmes');
  return res.json();
}

export async function fetchCourses(programmeId?: string): Promise<Course[]> {
  const url = programmeId
    ? `${API_V1}/institutions/courses?programme_id=${programmeId}`
    : `${API_V1}/institutions/courses`;
  const res = await fetch(url, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to load course offerings');
  return res.json();
}

// ---------------- STUDENTS ----------------
export async function fetchStudents(params?: {
  institution_id?: string;
  course?: string;
  course_id?: string;
  programme_id?: string;
  academic_year?: string;
  admission_status?: string;
  record_status?: string;
  search?: string;
}): Promise<Student[]> {
  const query = new URLSearchParams();
  if (params?.institution_id) query.append('institution_id', params.institution_id);
  if (params?.course) query.append('course', params.course);
  if (params?.search) query.append('search', params.search);
  if (params?.record_status) query.append('record_status', params.record_status);

  const res = await fetch(`${API_BASE}/students?${query.toString()}`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to fetch students');
  const data = await res.json();
  // Normalize internal_id / internal_student_id
  return data.map((s: any) => ({
    ...s,
    internal_id: s.internal_id || s.internal_student_id
  }));
}

export async function fetchStudentsV1(params?: {
  institution_id?: string;
  programme_id?: string;
  course_id?: string;
  academic_year?: string;
  admission_status?: string;
  record_status?: string;
  search?: string;
  page?: number;
  limit?: number;
}): Promise<PaginatedStudents> {
  const query = new URLSearchParams();
  if (params?.institution_id) query.append('institution_id', params.institution_id);
  if (params?.programme_id) query.append('programme_id', params.programme_id);
  if (params?.course_id) query.append('course_id', params.course_id);
  if (params?.academic_year) query.append('academic_year', params.academic_year);
  if (params?.admission_status) query.append('admission_status', params.admission_status);
  if (params?.record_status) query.append('record_status', params.record_status);
  if (params?.search) query.append('search', params.search);
  if (params?.page) query.append('page', String(params.page));
  if (params?.limit) query.append('limit', String(params.limit));

  const res = await fetch(`${API_V1}/students?${query.toString()}`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to fetch filtered student roster');
  const data = await res.json();
  return {
    items: data.items.map((s: any) => ({
      ...s,
      internal_id: s.internal_id || s.internal_student_id,
      programme: s.programme || s.programme_name,
      course: s.course || s.course_name
    })),
    total: data.total,
    page: data.page,
    limit: data.limit,
    total_pages: data.total_pages
  };
}

export async function fetchStudentDetail(id: string): Promise<Student> {
  const res = await fetch(`${API_V1}/students/${id}`, { headers: authHeaders() });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch student record details');
  }
  const s = await res.json();
  return {
    ...s,
    internal_id: s.internal_id || s.internal_student_id,
    programme: s.programme || s.programme_name,
    course: s.course || s.course_name
  };
}

export async function updateStudent(id: string, data: StudentUpdateIn): Promise<Student> {
  const res = await fetch(`${API_V1}/students/${id}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders()
    },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to update student record');
  }
  const s = await res.json();
  return {
    ...s,
    internal_id: s.internal_id || s.internal_student_id,
    programme: s.programme || s.programme_name,
    course: s.course || s.course_name
  };
}

export async function fetchStudentHistory(id: string): Promise<StudentHistoryItem[]> {
  const res = await fetch(`${API_V1}/students/${id}/history`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to load student change history');
  return res.json();
}

export async function createStudent(data: any, institutionId?: string): Promise<Student> {
  const url = institutionId ? `${API_BASE}/students?institution_id=${institutionId}` : `${API_BASE}/students`;
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders()
    },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to onboard student');
  }
  return res.json();
}

export async function fetchStudentCredential(id: string): Promise<StudentCredentialDetail> {
  const res = await fetch(`${API_BASE}/students/${id}/credential`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to fetch student credential pass');
  return res.json();
}

// ---------------- BULK IMPORT WIZARD & JOB HISTORY ----------------
export async function validateBulkUpload(payload: {
  academic_year: string;
  institution_id?: string;
  rows: any[];
}): Promise<BulkDryRunResult> {
  const res = await fetch(`${API_V1}/upload-jobs/validate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders()
    },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Server-side bulk validation failed');
  }
  return res.json();
}

export async function commitBulkUpload(payload: BulkCommitIn): Promise<BulkCommitSummary> {
  const res = await fetch(`${API_V1}/upload-jobs/commit`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders()
    },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Bulk import commit failed');
  }
  return res.json();
}

export async function fetchUploadJobs(institutionId?: string): Promise<BulkUploadJob[]> {
  const url = institutionId
    ? `${API_V1}/upload-jobs?institution_id=${institutionId}`
    : `${API_V1}/upload-jobs`;
  const res = await fetch(url, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to fetch upload jobs history');
  return res.json();
}

export const getJobErrorExportUrl = (jobId: string): string =>
  `${API_V1}/upload-jobs/${jobId}/export-errors`;

export const getCsvTemplateUrl = (): string => `${API_V1}/upload-jobs/template`;

export async function uploadStudentCsv(file: File, academicYear: string, institutionId?: string): Promise<ImportBatchResult> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('academic_year', academicYear);
  if (institutionId) formData.append('institution_id', institutionId);

  const res = await fetch(`${API_BASE}/import/upload`, {
    method: 'POST',
    headers: authHeaders(),
    body: formData
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'CSV Import failed');
  }
  return res.json();
}

export async function resolveBatchErrors(batchId: string, resolvedRows: any[]): Promise<any> {
  const res = await fetch(`${API_BASE}/import/resolve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders()
    },
    body: JSON.stringify({ batch_id: batchId, resolved_rows: resolvedRows })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to resolve errors');
  }
  return res.json();
}

export const getExportStudentsUrl = (institutionId?: string): string =>
  institutionId ? `${API_BASE}/import/export-students?institution_id=${institutionId}` : `${API_BASE}/import/export-students`;

// ---------------- VERIFICATION ----------------
export async function verifyCredential(payload: {
  token: string;
  verifier_name: string;
  verifier_organization: string;
  purpose: string;
}): Promise<VerificationResult> {
  const res = await fetch(`${API_BASE}/verification/verify-qr`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Verification request failed');
  }
  return res.json();
}

export async function fetchVerificationLogs(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/verification/logs`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to fetch verification logs');
  return res.json();
}

// ---------------- PDF REPORTS ----------------
export const getIntakeCompliancePdfUrl = (institutionId: string): string =>
  `${API_BASE}/reports/institution-intake-pdf/${institutionId}`;

export const getStudentCredentialPdfUrl = (studentId: string): string =>
  `${API_BASE}/reports/student-credential-pdf/${studentId}`;

// ---------------- VALIDATION WORKBENCH ----------------
export async function fetchValidationWorkbench(params?: {
  institution_id?: string;
  severity?: string;
  status?: string;
  rule_id?: string;
  search?: string;
  page?: number;
  limit?: number;
}): Promise<ValidationWorkbenchResponse> {
  const query = new URLSearchParams();
  if (params?.institution_id) query.append('institution_id', params.institution_id);
  if (params?.severity) query.append('severity', params.severity);
  if (params?.status) query.append('status', params.status);
  if (params?.rule_id) query.append('rule_id', params.rule_id);
  if (params?.search) query.append('search', params.search);
  if (params?.page) query.append('page', String(params.page));
  if (params?.limit) query.append('limit', String(params.limit));

  const qs = query.toString();
  const url = `${API_V1}/validation/workbench${qs ? `?${qs}` : ''}`;
  const res = await fetch(url, { headers: authHeaders() });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch validation workbench issues');
  }
  return res.json();
}

export async function fetchValidationIssueDetail(issueId: number): Promise<ValidationWorkbenchIssue> {
  const res = await fetch(`${API_V1}/validation/issues/${issueId}`, { headers: authHeaders() });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch validation issue details');
  }
  return res.json();
}

export async function updateValidationIssueStatus(
  issueId: number,
  payload: IssueStatusUpdateIn
): Promise<ValidationWorkbenchIssue> {
  const res = await fetch(`${API_V1}/validation/issues/${issueId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders()
    },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to update validation issue status');
  }
  return res.json();
}

export async function bulkReviewValidationIssues(
  payload: BulkIssueReviewIn
): Promise<{ status: string; updated_count: number }> {
  const res = await fetch(`${API_V1}/validation/issues/bulk-review`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders()
    },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to bulk review validation issues');
  }
  return res.json();
}

export async function runValidationAudit(
  institutionId?: string,
  academicYear: string = '2024-2025'
): Promise<ValidationAuditResponse> {
  const query = new URLSearchParams();
  if (institutionId) query.append('institution_id', institutionId);
  query.append('academic_year', academicYear);

  const res = await fetch(`${API_V1}/validation/run-audit?${query.toString()}`, {
    method: 'POST',
    headers: authHeaders()
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to execute statutory validation audit scan');
  }
  return res.json();
}

export async function fetchAicteCommandCenter(): Promise<AicteCommandCenterSummary> {
  const res = await fetch(`${API_V1}/dashboard/command-center`, { headers: authHeaders() });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to load central AICTE command center metrics');
  }
  return res.json();
}

export async function fetchAicteAnalytics(params?: {
  academic_year?: string;
  programme_id?: string;
  state?: string;
}): Promise<AicteAnalyticsResponse> {
  const query = new URLSearchParams();
  if (params?.academic_year && params.academic_year !== 'ALL') {
    query.append('academic_year', params.academic_year);
  }
  if (params?.programme_id && params.programme_id !== 'ALL') {
    query.append('programme_id', params.programme_id);
  }
  if (params?.state && params.state !== 'ALL') {
    query.append('state', params.state);
  }

  const qs = query.toString();
  const url = qs ? `${API_V1}/dashboard/analytics?${qs}` : `${API_V1}/dashboard/analytics`;
  const res = await fetch(url, { headers: authHeaders() });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to load statutory regulatory analytics');
  }
  return res.json();
}

export async function fetchInstitutionDashboardSummary(
  institutionId: string,
  academicYear: string = '2024-2025'
): Promise<InstitutionDashboardSummary> {
  const query = new URLSearchParams();
  if (academicYear && academicYear !== 'ALL') {
    query.append('academic_year', academicYear);
  }
  const qs = query.toString();
  const url = `${API_V1}/institutions/${institutionId}/dashboard-summary?${qs}`;
  const res = await fetch(url, { headers: authHeaders() });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to load institutional executive dashboard summary');
  }
  return res.json();
}

