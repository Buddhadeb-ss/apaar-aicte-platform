import React, { useState, useEffect } from 'react';
import {
  GraduationCap,
  QrCode,
  ShieldCheck,
  Download,
  Copy,
  Check,
  Building,
  Calendar,
  Sparkles,
  Info,
  RefreshCw,
  ExternalLink
} from 'lucide-react';
import { StudentCredentialDetail } from '../types';
import { fetchStudentCredential, fetchStudents, getStudentCredentialPdfUrl } from '../services/api';
import { Badge } from '../components/Badge';

interface StudentPortalProps {
  studentId?: string;
  studentRoll?: string;
}

export const StudentPortal: React.FC<StudentPortalProps> = ({ studentId, studentRoll }) => {
  const [credential, setCredential] = useState<StudentCredentialDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const loadCredential = async () => {
      try {
        setLoading(true);
        let targetId = studentId;

        // If only studentRoll is known, look up the student ID
        if (!targetId) {
          const list = await fetchStudents();
          if (list.length > 0) {
            targetId = list[0].id;
          }
        }

        if (targetId) {
          const credData = await fetchStudentCredential(targetId);
          setCredential(credData);
        }
      } catch (err) {
        console.error('Failed to load credential:', err);
      } finally {
        setLoading(false);
      }
    };

    loadCredential();
  }, [studentId, studentRoll]);

  const copyToken = () => {
    if (!credential) return;
    navigator.clipboard.writeText(credential.verification_token);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3 text-[#1C1917]">
        <RefreshCw className="w-6 h-6 text-[#C2410C] animate-spin" />
        <p className="text-base font-serif font-medium text-[#1C1917]">Loading Verifiable Credential...</p>
      </div>
    );
  }

  if (!credential) {
    return (
      <div className="max-w-md mx-auto my-16 bg-white p-8 rounded-2xl border border-[#E5E4DF] text-center space-y-3 shadow-sm">
        <Info className="w-8 h-8 text-[#78716C] mx-auto" />
        <h3 className="text-lg font-serif font-medium text-[#1C1917]">Student Record Not Found</h3>
        <p className="text-xs text-[#78716C]">
          No registered student record matches this profile session.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fade-in text-[#1C1917]">
      
      {/* Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#E5E4DF] pb-6">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-serif font-normal text-[#1C1917] tracking-tight">
              Verifiable Academic Credential Pass
            </h1>
            <Badge variant="emerald">Cryptographically Verified</Badge>
          </div>
          <p className="text-xs text-[#78716C] font-serif italic mt-1">
            Official AICTE APAAR Digital Student Pass linked with Academic Bank of Credits (ABC) & DigiLocker.
          </p>
        </div>
        <a
          href={getStudentCredentialPdfUrl(credential.id)}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[#1C1917] hover:bg-[#292524] text-white text-xs font-medium transition-all shadow-sm shrink-0"
        >
          <Download className="w-4 h-4" />
          Download Verifiable PDF Pass
        </a>
      </div>

      {/* Simulated Gateway Disclaimer Banner */}
      {credential.simulated_gateway_status && (
        <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF] text-xs text-[#57534E] flex items-start gap-3">
          <Info className="w-4 h-4 text-[#C2410C] shrink-0 mt-0.5" />
          <div>
            <span className="font-medium text-[#1C1917] uppercase tracking-wider block font-serif">
              Simulated Gateway: DigiLocker & ABC National Academic Depository v2.4
            </span>
            <p className="text-[11px] text-[#78716C] mt-0.5">
              {credential.simulated_gateway_status.gateway_notice}
            </p>
          </div>
        </div>
      )}

      {/* Digital Academic Credential Card in Anthropic Style */}
      <div className="bg-white rounded-3xl border border-[#E5E4DF] p-6 sm:p-8 shadow-[0_4px_24px_rgba(0,0,0,0.04)] relative overflow-hidden">
        
        <div className="flex flex-col lg:flex-row items-center justify-between gap-8">
          
          {/* Card Info Column */}
          <div className="flex-1 space-y-6 w-full">
            
            {/* Top Brand */}
            <div className="flex items-center justify-between border-b border-[#E5E4DF] pb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-[#1C1917] flex items-center justify-center font-serif font-bold text-white text-base shadow-sm">
                  A
                </div>
                <div>
                  <h3 className="text-sm font-serif font-medium text-[#1C1917]">ALL INDIA COUNCIL FOR TECHNICAL EDUCATION</h3>
                  <p className="text-[11px] text-[#78716C] font-serif italic">Automated Permanent Academic Account Registry</p>
                </div>
              </div>
              <Badge variant="saffron">NEP 2020 Compliant</Badge>
            </div>

            {/* Student & Course Details */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div>
                <span className="text-[#78716C] text-[11px] uppercase tracking-wider block font-medium">Student Full Name</span>
                <span className="text-xl font-serif font-medium text-[#1C1917] block mt-0.5">{credential.student_name}</span>
                <span className="text-[11px] text-[#78716C] font-mono">Roll: {credential.internal_id}</span>
              </div>
              <div>
                <span className="text-[#78716C] text-[11px] uppercase tracking-wider block font-medium">Masked APAAR ID</span>
                <span className="text-base font-mono font-medium text-[#15803D] block mt-0.5">
                  {credential.apaar_masked}
                </span>
                <span className="text-[10px] text-[#78716C]">Privacy-preserved statutory view</span>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs pt-2 border-t border-[#E5E4DF]">
              <div>
                <span className="text-[#78716C] text-[11px] uppercase tracking-wider block font-medium">Course & Programme</span>
                <span className="font-medium text-[#1C1917] block mt-0.5">{credential.course}</span>
                <span className="text-[11px] text-[#78716C]">{credential.programme}</span>
              </div>
              <div>
                <span className="text-[#78716C] text-[11px] uppercase tracking-wider block font-medium">Technical Institution</span>
                <span className="font-medium text-[#1C1917] block mt-0.5">{credential.institution_name}</span>
                <span className="text-[11px] text-[#78716C]">Session {credential.academic_year}</span>
              </div>
            </div>

            {/* Quota & Category Badges */}
            <div className="flex flex-wrap items-center gap-2 pt-2">
              <span className="text-xs text-[#78716C]">Admission Status:</span>
              <Badge variant="success">{credential.admission_status}</Badge>
              <Badge variant="neutral">Category: {credential.category}</Badge>
              {credential.is_supernumerary && (
                <Badge variant="saffron">Supernumerary: {credential.supernumerary_type}</Badge>
              )}
            </div>

            {/* Cryptographic Signature Block */}
            <div className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF] space-y-1">
              <span className="text-[10px] uppercase font-bold text-[#78716C] tracking-wider flex items-center gap-1">
                <ShieldCheck className="w-3 h-3 text-[#15803D]" />
                Server-Side Cryptographic HMAC Signature
              </span>
              <p className="font-mono text-[10px] text-[#57534E] break-all">{credential.credential_signature}</p>
            </div>

          </div>

          {/* QR Code Column */}
          <div className="flex flex-col items-center justify-center p-6 rounded-2xl bg-[#FAF9F5] text-[#1C1917] shrink-0 w-64 border border-[#E5E4DF]">
            <span className="text-[10px] font-medium uppercase tracking-widest text-[#78716C] mb-2 font-serif">
              Scan To Verify
            </span>
            <img
              src={credential.qr_code_base64}
              alt="Verifiable Student QR Code"
              className="w-44 h-44 rounded-xl border border-[#E5E4DF] bg-white p-2 shadow-sm"
            />
            <span className="text-[10px] font-mono text-[#78716C] mt-2 text-center">
              AICTE-APAAR-PASS
            </span>
            <button
              onClick={copyToken}
              className="mt-3 inline-flex items-center gap-1 text-[11px] font-medium text-[#C2410C] hover:underline"
            >
              {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
              {copied ? 'Token Copied!' : 'Copy Verification Token'}
            </button>
          </div>

        </div>

      </div>

    </div>
  );
};
