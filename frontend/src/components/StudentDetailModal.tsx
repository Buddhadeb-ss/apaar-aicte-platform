import React, { useState, useEffect } from 'react';
import {
  X,
  User,
  ShieldCheck,
  History,
  Calendar,
  Building2,
  Award,
  Globe,
  CheckCircle2,
  AlertTriangle,
  QrCode,
  FileCheck,
  Clock,
  Eye,
  EyeOff
} from 'lucide-react';
import { Student, StudentHistoryItem } from '../types';
import { fetchStudentDetail, fetchStudentHistory, getStudentCredentialPdfUrl } from '../services/api';
import { Badge } from './Badge';

interface StudentDetailModalProps {
  studentId: string | null;
  onClose: () => void;
  onEditStudent: (student: Student) => void;
  onViewCredentialPass: (studentId: string) => void;
}

export const StudentDetailModal: React.FC<StudentDetailModalProps> = ({
  studentId,
  onClose,
  onEditStudent,
  onViewCredentialPass
}) => {
  const [student, setStudent] = useState<Student | null>(null);
  const [history, setHistory] = useState<StudentHistoryItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'details' | 'history'>('details');
  const [showFullApaar, setShowFullApaar] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!studentId) return;
    const loadDetails = async () => {
      try {
        setLoading(true);
        setError(null);
        const [detailData, historyData] = await Promise.all([
          fetchStudentDetail(studentId),
          fetchStudentHistory(studentId).catch(() => [])
        ]);
        setStudent(detailData);
        setHistory(historyData);
      } catch (err: any) {
        setError(err.message || 'Failed to load student details.');
      } finally {
        setLoading(false);
      }
    };

    loadDetails();
  }, [studentId]);

  if (!studentId) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-stone-900/40 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-3xl bg-white border border-[#E5E4DF] rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.12)] overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E5E4DF] bg-[#FAF9F5]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-white border border-[#E5E4DF] flex items-center justify-center text-[#1C1917] font-serif font-bold text-base shadow-sm">
              <User className="w-5 h-5 text-[#57534E]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-serif font-medium text-[#1C1917]">
                  {student?.student_name || 'Student Record Details'}
                </h2>
                {student && (
                  <Badge variant={student.record_status === 'ACCEPTED' ? 'success' : 'warning'}>
                    {student.record_status}
                  </Badge>
                )}
              </div>
              <p className="text-xs text-[#78716C] font-mono">
                Roll No: {student?.internal_id} • AICTE Institution Record
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#78716C] hover:text-[#1C1917] hover:bg-[#F4F3EE] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Navigation Tabs */}
        <div className="flex border-b border-[#E5E4DF] px-6 bg-white">
          <button
            onClick={() => setActiveTab('details')}
            className={`py-3 px-4 text-xs font-medium border-b-2 transition-all flex items-center gap-2 ${
              activeTab === 'details'
                ? 'border-[#1C1917] text-[#1C1917] font-semibold'
                : 'border-transparent text-[#78716C] hover:text-[#1C1917]'
            }`}
          >
            <FileCheck className="w-3.5 h-3.5" />
            Enrolment & Identity Profile
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`py-3 px-4 text-xs font-medium border-b-2 transition-all flex items-center gap-2 ${
              activeTab === 'history'
                ? 'border-[#1C1917] text-[#1C1917] font-semibold'
                : 'border-transparent text-[#78716C] hover:text-[#1C1917]'
            }`}
          >
            <History className="w-3.5 h-3.5" />
            Statutory Change History ({history.length})
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6 text-xs text-[#57534E]">
          {error && (
            <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600" />
              {error}
            </div>
          )}

          {loading ? (
            <div className="py-12 flex flex-col items-center justify-center gap-2 text-[#78716C]">
              <Clock className="w-6 h-6 animate-spin text-[#C2410C]" />
              <p className="font-serif">Loading record and audit log...</p>
            </div>
          ) : student && activeTab === 'details' ? (
            <div className="space-y-5">
              
              {/* Primary Identity Card */}
              <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF] space-y-3">
                <div className="flex items-center justify-between border-b border-[#E5E4DF] pb-2">
                  <span className="font-serif font-medium text-[#1C1917] text-xs flex items-center gap-1.5">
                    <ShieldCheck className="w-4 h-4 text-[#15803D]" />
                    Verified APAAR Identity Token
                  </span>
                  <span className="font-mono text-[11px] text-[#15803D] bg-emerald-50 px-2.5 py-0.5 rounded-md border border-emerald-200 font-semibold">
                    {student.apaar_masked}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
                  <div>
                    <span className="text-[10px] text-[#78716C] uppercase tracking-wider block font-medium">Full Legal Name</span>
                    <span className="font-serif font-medium text-[#1C1917] text-base">{student.student_name}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-[#78716C] uppercase tracking-wider block font-medium">Date of Birth</span>
                    <span className="font-medium text-[#1C1917]">{student.date_of_birth}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-[#78716C] uppercase tracking-wider block font-medium">Gender & Category</span>
                    <span className="font-medium text-[#1C1917]">{student.gender} • {student.category}</span>
                  </div>
                </div>
              </div>

              {/* Programme & Academic Details */}
              <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF] space-y-3">
                <span className="font-serif font-medium text-[#1C1917] text-xs flex items-center gap-1.5 border-b border-[#E5E4DF] pb-2">
                  <Building2 className="w-4 h-4 text-sky-700" />
                  Academic Allocation & Intake Classification
                </span>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
                  <div>
                    <span className="text-[10px] text-[#78716C] uppercase tracking-wider block font-medium">Course Title</span>
                    <span className="font-medium text-[#1C1917]">{student.course}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-[#78716C] uppercase tracking-wider block font-medium">Programme Domain</span>
                    <span className="font-medium text-[#1C1917]">{student.programme}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-[#78716C] uppercase tracking-wider block font-medium">Admission & Academic Session</span>
                    <span className="font-medium text-[#1C1917]">{student.academic_year} (Admitted: {student.admission_year})</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-[#78716C] uppercase tracking-wider block font-medium">Admission Status</span>
                    <span className="inline-block mt-0.5">
                      <Badge variant="info">{student.admission_status}</Badge>
                    </span>
                  </div>
                </div>
              </div>

              {/* Supernumerary & Nationality Categories */}
              <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF] space-y-3">
                <span className="font-serif font-medium text-[#1C1917] text-xs flex items-center gap-1.5 border-b border-[#E5E4DF] pb-2">
                  <Globe className="w-4 h-4 text-[#C2410C]" />
                  Quota Allocation & Nationality Categorization
                </span>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
                  <div>
                    <span className="text-[10px] text-[#78716C] uppercase tracking-wider block font-medium">Supernumerary Seat Status</span>
                    {student.is_supernumerary ? (
                      <span className="inline-flex items-center gap-1.5 mt-1 font-medium text-amber-900">
                        <CheckCircle2 className="w-3.5 h-3.5 text-amber-700" />
                        Supernumerary Seat: {student.supernumerary_type}
                      </span>
                    ) : (
                      <span className="inline-block mt-1 text-[#78716C]">Regular Sanctioned Core Pool</span>
                    )}
                  </div>

                  <div>
                    <span className="text-[10px] text-[#78716C] uppercase tracking-wider block font-medium">Nationality Indicators</span>
                    <div className="flex flex-wrap gap-1.5 mt-1">
                      {student.nri_status && <Badge variant="saffron">NRI Category</Badge>}
                      {student.oci_status && <Badge variant="info">OCI Status</Badge>}
                      {student.foreign_national_status && <Badge variant="warning">Foreign National</Badge>}
                      {!student.nri_status && !student.oci_status && !student.foreign_national_status && (
                        <span className="text-[#78716C]">Domestic Indian National</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Cryptographic Signature & Verification Token */}
              <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF] space-y-2">
                <span className="text-[10px] font-bold text-[#78716C] uppercase tracking-wider block">
                  Tamper-Evident HMAC Server Signature
                </span>
                <p className="font-mono text-[10px] text-[#1C1917] break-all bg-white p-2.5 rounded-lg border border-[#E5E4DF]">
                  {student.credential_signature}
                </p>
                <div className="flex items-center justify-between pt-1">
                  <span className="text-[10px] text-[#78716C] font-mono">
                    Token: {student.verification_token}
                  </span>
                  <a
                    href={getStudentCredentialPdfUrl(student.id)}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-[#C2410C] hover:underline font-medium"
                  >
                    Download Verifiable Credential PDF
                  </a>
                </div>
              </div>

            </div>
          ) : activeTab === 'history' ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-[#E5E4DF]">
                <p className="text-xs text-[#78716C]">
                  Statutory audit trail of all lifecycle events for roll <span className="font-mono font-medium text-[#1C1917]">{student?.internal_id}</span>.
                </p>
              </div>

              {history.length === 0 ? (
                <div className="py-8 text-center text-[#78716C]">
                  No previous audit events recorded for this student.
                </div>
              ) : (
                <div className="relative pl-6 space-y-4 border-l border-[#E5E4DF]">
                  {history.map((item) => (
                    <div key={item.id} className="relative group">
                      {/* Timeline dot */}
                      <div className="absolute -left-[31px] top-1.5 w-2.5 h-2.5 rounded-full bg-[#1C1917] border-2 border-white" />

                      <div className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF] hover:border-[#D5D3CA] transition-colors space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-medium text-[#1C1917] text-xs">
                            {item.event_type.replace(/_/g, ' ')}
                          </span>
                          <span className="text-[10px] font-mono text-[#78716C]">
                            {item.timestamp}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-[11px] text-[#78716C]">
                          <span className="px-1.5 py-0.5 rounded bg-white font-mono text-[10px] text-[#57534E] border border-[#E5E4DF]">
                            {item.actor_role}
                          </span>
                          <span>{item.actor_email}</span>
                        </div>
                        {item.details && (
                          <div className="text-[11px] text-[#57534E] bg-white p-2 rounded-lg font-mono border border-[#E5E4DF] mt-1.5">
                            {item.details}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : null}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 border-t border-[#E5E4DF] bg-[#FAF9F5] flex items-center justify-between">
          <div className="flex items-center gap-2">
            {student && (
              <button
                onClick={() => onViewCredentialPass(student.id)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-[#E5E4DF] text-[#1C1917] hover:bg-[#F4F3EE] text-xs font-medium transition-all shadow-sm"
              >
                <QrCode className="w-3.5 h-3.5 text-[#78716C]" />
                View Verifiable Pass
              </button>
            )}
          </div>

          <div className="flex items-center gap-2.5">
            {student && (
              <button
                onClick={() => {
                  onClose();
                  onEditStudent(student);
                }}
                className="px-4 py-2 rounded-lg bg-[#1C1917] hover:bg-[#292524] text-white text-xs font-medium transition-all shadow-sm"
              >
                Edit Student Data
              </button>
            )}
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-white hover:bg-[#F4F3EE] text-[#57534E] text-xs font-medium border border-[#E5E4DF]"
            >
              Close
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
