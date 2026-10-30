import React, { useState, useEffect } from 'react';
import {
  QrCode,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Building,
  User,
  Search,
  Clock,
  Sparkles,
  Info,
  RefreshCw
} from 'lucide-react';
import { VerificationResult } from '../types';
import { verifyCredential, fetchVerificationLogs, fetchStudents } from '../services/api';
import { Badge } from '../components/Badge';

export const VerificationPortal: React.FC = () => {
  const [token, setToken] = useState('');
  const [verifierName, setVerifierName] = useState('Priya Varma');
  const [verifierOrg, setVerifierOrg] = useState('Tata Consultancy Services (TCS)');
  const [purpose, setPurpose] = useState('Pre-Employment Background Verification');

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [logs, setLogs] = useState<any[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);

  // Load past verifications
  const loadLogs = async () => {
    try {
      setLogsLoading(true);
      const data = await fetchVerificationLogs();
      setLogs(data);
    } catch (err) {
      console.error('Failed to load logs:', err);
    } finally {
      setLogsLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, []);

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token.trim()) {
      setErrorMsg('Please input a valid credential verification token or QR payload.');
      return;
    }
    setLoading(true);
    setErrorMsg(null);
    setResult(null);
    try {
      const res = await verifyCredential({
        token: token.trim(),
        verifier_name: verifierName,
        verifier_organization: verifierOrg,
        purpose: purpose
      });
      setResult(res);
      await loadLogs();
    } catch (err: any) {
      setErrorMsg(err.message || 'Verification failed');
    } finally {
      setLoading(false);
    }
  };

  const fillSampleToken = async (tampered: boolean = false) => {
    try {
      const students = await fetchStudents();
      if (students.length > 0) {
        if (tampered) {
          setToken(`AICTE-APAAR-PASS|tampered-fake-token-999|INVALID_SIG|UNKNOWN|INST-000`);
        } else {
          const s = students[0];
          setToken(`AICTE-APAAR-PASS|${s.verification_token}|${s.credential_signature}|${s.internal_id}|${s.institution_id}`);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fade-in text-[#1C1917]">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#E5E4DF] pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-serif font-normal text-[#1C1917] tracking-tight">
              Credential & QR Verifier Portal
            </h1>
            <Badge variant="warning">Third-Party Gateway</Badge>
          </div>
          <p className="text-xs sm:text-sm text-[#57534E] font-serif italic mt-1">
            Real-time server-side HMAC-SHA256 signature verification for employers, universities, and statutory authorities.
          </p>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs font-medium flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-rose-700" />
          {errorMsg}
        </div>
      )}

      {/* Verification Form Card */}
      <div className="bg-white p-6 sm:p-8 rounded-2xl border border-[#E5E4DF] shadow-[0_2px_8px_rgba(0,0,0,0.03)] space-y-6">
        
        {/* Quick Test Payloads Bar Integrated into Form Header */}
        <div className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF] flex flex-wrap items-center justify-between gap-3 text-xs">
          <span className="text-[#57534E] font-medium flex items-center gap-1.5 font-serif">
            <Sparkles className="w-3.5 h-3.5 text-[#C2410C]" />
            Quick Test Payloads:
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => fillSampleToken(false)}
              className="px-3 py-1.5 rounded-lg bg-white border border-[#E5E4DF] text-[#1C1917] hover:bg-[#F4F3EE] font-medium transition-all shadow-sm"
            >
              Load Valid Student QR Token
            </button>
            <button
              type="button"
              onClick={() => fillSampleToken(true)}
              className="px-3 py-1.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 hover:bg-rose-100 font-medium transition-all"
            >
              Load Tampered / Fake Token
            </button>
          </div>
        </div>
        <form onSubmit={handleVerify} className="space-y-4 text-xs text-[#57534E]">
          <div>
            <label className="block font-medium text-[#1C1917] mb-1">
              Credential Token / QR Payload String <span className="text-[#C2410C]">*</span>
            </label>
            <div className="relative">
              <QrCode className="w-4 h-4 text-[#A8A29E] absolute left-3 top-3" />
              <input
                type="text"
                required
                placeholder="Paste verification token UUID or scanned AICTE-APAAR-PASS payload"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                className="w-full bg-[#FAF9F5] border border-[#E5E4DF] rounded-xl pl-9 pr-3 py-2.5 text-xs text-[#1C1917] font-mono focus:outline-none focus:border-[#1C1917]"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block font-medium text-[#57534E] mb-1">Verifier Name <span className="text-[#C2410C]">*</span></label>
              <input
                type="text"
                required
                value={verifierName}
                onChange={(e) => setVerifierName(e.target.value)}
                className="w-full bg-white border border-[#E5E4DF] rounded-xl px-3 py-2 text-[#1C1917] focus:outline-none focus:border-[#1C1917]"
              />
            </div>
            <div>
              <label className="block font-medium text-[#57534E] mb-1">Organization <span className="text-[#C2410C]">*</span></label>
              <input
                type="text"
                required
                value={verifierOrg}
                onChange={(e) => setVerifierOrg(e.target.value)}
                className="w-full bg-white border border-[#E5E4DF] rounded-xl px-3 py-2 text-[#1C1917] focus:outline-none focus:border-[#1C1917]"
              />
            </div>
            <div>
              <label className="block font-medium text-[#57534E] mb-1">Verification Purpose <span className="text-[#C2410C]">*</span></label>
              <input
                type="text"
                required
                value={purpose}
                onChange={(e) => setPurpose(e.target.value)}
                className="w-full bg-white border border-[#E5E4DF] rounded-xl px-3 py-2 text-[#1C1917] focus:outline-none focus:border-[#1C1917]"
              />
            </div>
          </div>

          <div className="pt-2 flex justify-end">
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-[#1C1917] hover:bg-[#292524] text-white font-medium text-xs shadow-sm transition-all disabled:opacity-50"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Verifying Cryptographic Signature...
                </>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4" />
                  Verify Credential Authenticity
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Verification Result Showcase */}
      {result && (
        <div className="animate-fade-in">
          {result.is_valid ? (
            <div className="bg-white p-6 sm:p-8 rounded-2xl border border-emerald-200 shadow-sm space-y-6">
              <div className="flex items-center justify-between border-b border-[#E5E4DF] pb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800">
                    <CheckCircle2 className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="text-lg font-serif font-medium text-[#1C1917]">OFFICIAL AICTE VERIFIED CREDENTIAL</h3>
                    <p className="text-xs text-[#15803D] font-medium">
                      Cryptographic Signature Validated • Issued by Authorized Technical Institution
                    </p>
                  </div>
                </div>
                <Badge variant="success">STATUS: {result.status}</Badge>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs text-[#57534E]">
                <div>
                  <span className="text-[#78716C] block">Student Full Name</span>
                  <span className="font-serif font-medium text-[#1C1917] text-base block mt-0.5">{result.student_name}</span>
                  <span className="text-[11px] text-[#78716C] font-mono">Roll: {result.internal_id}</span>
                </div>
                <div>
                  <span className="text-[#78716C] block">Masked APAAR ID</span>
                  <span className="font-mono font-medium text-[#15803D] text-sm block mt-0.5">
                    {result.apaar_masked}
                  </span>
                  <span className="text-[10px] text-[#78716C]">Privacy-preserved statutory view</span>
                </div>
                <div>
                  <span className="text-[#78716C] block">Technical Institution</span>
                  <span className="font-medium text-[#1C1917] block mt-0.5">{result.institution_name}</span>
                </div>
                <div>
                  <span className="text-[#78716C] block">Programme & Course</span>
                  <span className="font-medium text-[#1C1917] block mt-0.5">{result.course}</span>
                  <span className="text-[10px] text-[#78716C]">{result.programme}</span>
                </div>
                <div>
                  <span className="text-[#78716C] block">Academic Session</span>
                  <span className="font-medium text-[#1C1917] block mt-0.5">{result.academic_year}</span>
                </div>
                <div>
                  <span className="text-[#78716C] block">Admission Status</span>
                  <span className="font-medium text-[#15803D] block mt-0.5">{result.admission_status}</span>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF] text-[11px] font-mono text-[#57534E] break-all space-y-1">
                <span className="text-[10px] font-bold text-[#78716C] uppercase tracking-wider block">
                  Tamper-Evident HMAC Server Signature:
                </span>
                {result.digital_signature}
              </div>
            </div>
          ) : (
            <div className="bg-rose-50/50 p-6 sm:p-8 rounded-2xl border border-rose-200 space-y-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-rose-100 border border-rose-300 text-rose-800">
                  <XCircle className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-base font-serif font-medium text-rose-900">VERIFICATION FAILED / INVALID SIGNATURE</h3>
                  <p className="text-xs text-rose-700">
                    {result.gateway_note || 'The token has been tampered with or does not exist in the AICTE Registry.'}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Verification History Log */}
      <div className="bg-white p-6 rounded-2xl border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-[#78716C]" />
            <h3 className="text-base font-serif font-medium text-[#1C1917]">Immutable Verification Audit Trail</h3>
          </div>
          <span className="text-xs text-[#78716C]">{logs.length} logged inquiries</span>
        </div>

        <div className="overflow-x-auto rounded-xl border border-[#E5E4DF]">
          <table className="w-full text-left text-xs text-[#57534E]">
            <thead className="bg-[#FAF9F5] text-[10px] font-medium uppercase tracking-wider text-[#78716C] border-b border-[#E5E4DF]">
              <tr>
                <th className="py-2.5 px-3">Verifier / Organization</th>
                <th className="py-2.5 px-3">Verification Purpose</th>
                <th className="py-2.5 px-3 text-center">Result</th>
                <th className="py-2.5 px-3">IP Address</th>
                <th className="py-2.5 px-3 text-right">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E5E4DF] font-sans">
              {logs.map((l) => (
                <tr key={l.id} className="hover:bg-[#FAF9F5] transition-colors">
                  <td className="py-2.5 px-3">
                    <p className="font-serif font-medium text-[#1C1917]">{l.verifier_name}</p>
                    <p className="text-[10px] text-[#78716C]">{l.verifier_organization}</p>
                  </td>
                  <td className="py-2.5 px-3 text-[#57534E]">{l.purpose}</td>
                  <td className="py-2.5 px-3 text-center">
                    {l.result === 'VERIFIED' ? (
                      <Badge variant="success">VERIFIED</Badge>
                    ) : (
                      <Badge variant="danger">{l.result}</Badge>
                    )}
                  </td>
                  <td className="py-2.5 px-3 font-mono text-[#78716C] text-[11px]">{l.ip_address}</td>
                  <td className="py-2.5 px-3 text-right font-mono text-[#78716C] text-[11px]">{l.timestamp}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};
