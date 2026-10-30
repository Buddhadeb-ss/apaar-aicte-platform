import React, { useState } from 'react';
import {
  ShieldCheck,
  Building2,
  GraduationCap,
  QrCode,
  Lock,
  Mail,
  ArrowRight,
  Sparkles,
  Info,
  Layers,
  FileSpreadsheet,
  CheckCircle2,
  KeyRound,
  Users
} from 'lucide-react';
import { DemoProfile } from '../types';

interface LoginPageProps {
  demoProfiles: DemoProfile[];
  onDemoLogin: (index: number) => void;
  onCredentialLogin: (email: string, pass: string) => Promise<void>;
  loading: boolean;
  error: string | null;
}

export const LoginPage: React.FC<LoginPageProps> = ({
  demoProfiles,
  onDemoLogin,
  onCredentialLogin,
  loading,
  error
}) => {
  const [email, setEmail] = useState('admin@aicte.gov.in');
  const [password, setPassword] = useState('Aicte@2026');
  const [tab, setTab] = useState<'quick' | 'credentials'>('quick');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onCredentialLogin(email, password);
  };

  // Plain-English metadata and friendly labels for each persona
  const getPersonaMeta = (profile: DemoProfile) => {
    if (profile.email === 'admin@aicte.gov.in' || profile.role === 'AICTE_ADMIN') {
      return {
        title: 'AICTE Central Council',
        tag: 'National Regulator',
        badgeBg: 'bg-[#FDF8F6] text-[#C2410C] border-[#EBDBD5]',
        iconBg: 'bg-[#FDF8F6] text-[#C2410C] border-[#EBDBD5]',
        icon: <ShieldCheck className="w-6 h-6" />,
        actionText: 'Explore National Scrutiny',
        whatItDoes: 'View nation-wide college seat quotas, detect colleges exceeding allowed seats, and catch duplicate students registered across multiple colleges.',
        highlights: ['National Dashboard', 'Over-Admission Alerts', 'Multi-College Collisions']
      };
    }

    if (profile.email === 'registrar@apex.edu') {
      return {
        title: 'Apex Institute of Technology',
        tag: 'College Registrar',
        badgeBg: 'bg-blue-50 text-blue-900 border-blue-200',
        iconBg: 'bg-blue-50 text-blue-900 border-blue-200',
        icon: <Building2 className="w-6 h-6" />,
        actionText: 'Manage College Portal',
        whatItDoes: 'Track approved course seat limits, upload new student admission rosters via CSV, and download official AICTE compliance certificates.',
        highlights: ['Approved Seat Caps', 'CSV Bulk Import', 'Course Capacities']
      };
    }

    if (profile.email === 'principal@beacon.ac.in') {
      return {
        title: 'Beacon College of Engineering',
        tag: 'College Dean (Govt Aided)',
        badgeBg: 'bg-indigo-50 text-indigo-900 border-indigo-200',
        iconBg: 'bg-indigo-50 text-indigo-900 border-indigo-200',
        icon: <Building2 className="w-6 h-6" />,
        actionText: 'Inspect Beacon Campus',
        whatItDoes: 'Review government-aided college seat quotas, resolve cross-institution duplicate enrollment flags with Apex Tech, and manage admissions.',
        highlights: ['Cross-College Collisions', 'Seat Quotas', 'APH Compliance']
      };
    }

    if (profile.email === 'operator@apex.edu' || profile.role === 'INSTITUTION_OPERATOR') {
      return {
        title: 'Admissions Data Operator',
        tag: 'Admissions Staff',
        badgeBg: 'bg-stone-50 text-stone-800 border-stone-200',
        iconBg: 'bg-stone-50 text-stone-800 border-stone-200',
        icon: <FileSpreadsheet className="w-6 h-6" />,
        actionText: 'Open Admissions Wizard',
        whatItDoes: 'Upload batches of student records, preview and correct missing or invalid fields in a dry-run before submitting.',
        highlights: ['CSV Batch Staging', 'Error Correction', 'Row Verification']
      };
    }

    if (profile.email === 'student@apex.edu' || profile.role === 'STUDENT' || profile.role === 'STUDENT_VIEWER') {
      return {
        title: 'College Student (Aarav Sharma)',
        tag: 'Student Pass',
        badgeBg: 'bg-emerald-50 text-emerald-900 border-emerald-200',
        iconBg: 'bg-emerald-50 text-emerald-900 border-emerald-200',
        icon: <GraduationCap className="w-6 h-6" />,
        actionText: 'View Student Pass',
        whatItDoes: 'View official APAAR digital student ID card with privacy-masked details and a scannable tamper-proof QR verification code.',
        highlights: ['Masked APAAR ID', 'Verifiable QR Pass', 'DigiLocker Linked']
      };
    }

    if (profile.email === 'verifier@tcs.com' || profile.role === 'VERIFIER' || profile.role === 'AUTHORIZED_VERIFIER') {
      return {
        title: 'Employer & Background Verifier',
        tag: 'Third-Party Verifier (TCS)',
        badgeBg: 'bg-amber-50 text-amber-900 border-amber-200',
        iconBg: 'bg-amber-50 text-amber-900 border-amber-200',
        icon: <QrCode className="w-6 h-6" />,
        actionText: 'Test QR Verifier',
        whatItDoes: 'Scan student QR codes or paste digital tokens to instantly verify college enrolment authenticity with cryptographic proof.',
        highlights: ['Instant QR Scan', 'Tamper Detection', 'Verification Log']
      };
    }

    return {
      title: profile.label || 'System User',
      tag: 'System User',
      badgeBg: 'bg-[#F4F3EE] text-[#57534E] border-[#E5E4DF]',
      iconBg: 'bg-[#F4F3EE] text-[#57534E] border-[#E5E4DF]',
      icon: <Lock className="w-6 h-6" />,
      actionText: 'Launch Role',
      whatItDoes: 'Access system capabilities configured for this profile.',
      highlights: ['Secure Access']
    };
  };

  return (
    <div className="min-h-[calc(100vh-5rem)] flex flex-col justify-center px-4 sm:px-6 lg:px-8 py-10 sm:py-16">
      <div className="w-full max-w-4xl mx-auto space-y-10">
        
        {/* 1. Welcoming Hero Section with Generous Breathing Room */}
        <div className="text-center space-y-4">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#FAF9F5] border border-[#E5E4DF] text-xs font-serif text-[#78716C] shadow-sm">
            <span className="w-2 h-2 rounded-full bg-[#C2410C]"></span>
            <span>All India Council for Technical Education • SIH26263</span>
          </div>

          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-serif font-normal text-[#1C1917] tracking-tight">
            National Student Registry & Verification Platform
          </h1>

          <p className="text-base sm:text-lg text-[#57534E] font-serif max-w-2xl mx-auto leading-relaxed">
            One Student, One Verified Identity. AICTE monitors approved college seats to prevent over-admissions, detects duplicate enrolments across campuses, and provides students with tamper-proof QR credentials.
          </p>
        </div>

        {/* 2. Clear, High-Visibility Mode Switcher */}
        <div className="flex flex-col items-center gap-3">
          <div className="inline-flex p-1.5 rounded-2xl bg-[#F4F3EE] border border-[#E5E4DF] shadow-inner">
            <button
              onClick={() => setTab('quick')}
              className={`px-5 py-2.5 rounded-xl text-xs sm:text-sm font-medium transition-all flex items-center gap-2 ${
                tab === 'quick'
                  ? 'bg-white text-[#1C1917] font-semibold shadow-sm border border-[#E5E4DF]'
                  : 'text-[#78716C] hover:text-[#1C1917]'
              }`}
            >
              <Sparkles className="w-4 h-4 text-[#C2410C]" />
              <span>1-Click Live Demo Personas</span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 font-semibold">
                No Password Required
              </span>
            </button>
            <button
              onClick={() => setTab('credentials')}
              className={`px-5 py-2.5 rounded-xl text-xs sm:text-sm font-medium transition-all flex items-center gap-2 ${
                tab === 'credentials'
                  ? 'bg-white text-[#1C1917] font-semibold shadow-sm border border-[#E5E4DF]'
                  : 'text-[#78716C] hover:text-[#1C1917]'
              }`}
            >
              <KeyRound className="w-4 h-4 text-[#78716C]" />
              <span>Standard Password Login</span>
            </button>
          </div>

          {tab === 'quick' && (
            <p className="text-xs text-[#78716C] font-serif italic text-center">
              Click any of the 5 roles below to immediately test the platform from that person's perspective:
            </p>
          )}
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs font-medium flex items-center gap-2 max-w-xl mx-auto">
            <Info className="w-4 h-4 shrink-0 text-rose-600" />
            <span>{error}</span>
          </div>
        )}

        {/* 3. 1-Click Evaluation Personas Grid */}
        {tab === 'quick' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {demoProfiles.slice(0, 5).map((profile, idx) => {
              const meta = getPersonaMeta(profile);
              return (
                <div
                  key={profile.email}
                  onClick={() => !loading && onDemoLogin(idx)}
                  className="bg-white p-6 rounded-2xl border border-[#E5E4DF] shadow-[0_2px_8px_rgba(0,0,0,0.03)] hover:border-[#D5D3CA] hover:shadow-[0_6px_20px_rgba(0,0,0,0.06)] transition-all duration-200 cursor-pointer group flex flex-col justify-between space-y-5"
                >
                  <div className="space-y-4">
                    {/* Header Row: Icon + Role Tag */}
                    <div className="flex items-start justify-between gap-3">
                      <div className={`w-12 h-12 rounded-xl flex items-center justify-center border ${meta.iconBg}`}>
                        {meta.icon}
                      </div>
                      <span className={`text-xs font-medium px-3 py-1 rounded-full border ${meta.badgeBg}`}>
                        {meta.tag}
                      </span>
                    </div>

                    {/* Role Title & Name */}
                    <div>
                      <h3 className="text-xl font-serif font-medium text-[#1C1917] group-hover:text-[#C2410C] transition-colors">
                        {meta.title}
                      </h3>
                      <p className="text-xs font-mono text-[#78716C] mt-0.5">{profile.name}</p>
                    </div>

                    {/* Plain English Description for Non-Technical Evaluators */}
                    <p className="text-xs sm:text-sm text-[#57534E] leading-relaxed">
                      {meta.whatItDoes}
                    </p>

                    {/* Feature Pills */}
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {meta.highlights.map((h, i) => (
                        <span key={i} className="text-[11px] px-2 py-0.5 rounded-md bg-[#FAF9F5] text-[#78716C] border border-[#E5E4DF]">
                          {h}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Action Link Footer */}
                  <div className="pt-4 border-t border-[#F4F3EE] flex items-center justify-between text-xs font-medium text-[#1C1917] group-hover:text-[#C2410C]">
                    <span className="font-serif font-medium text-sm">{meta.actionText}</span>
                    <div className="flex items-center gap-1">
                      <span className="text-[11px] font-mono text-[#78716C] group-hover:text-[#C2410C]">1-Click Launch</span>
                      <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          /* Standard Login Form */
          <div className="bg-white max-w-md mx-auto p-8 rounded-2xl border border-[#E5E4DF] shadow-[0_4px_16px_rgba(0,0,0,0.04)] space-y-6">
            <div>
              <h2 className="text-2xl font-serif font-medium text-[#1C1917]">Registered User Login</h2>
              <p className="text-xs text-[#78716C] mt-1">Sign in with your registered institutional credentials to access your administrative workspace.</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#57534E] mb-1.5">Registered Email</label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-[#A8A29E] absolute left-3.5 top-3" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="w-full bg-[#FAF9F5] border border-[#E5E4DF] rounded-xl pl-10 pr-3 py-2.5 text-sm text-[#1C1917] focus:outline-none focus:border-[#1C1917] focus:bg-white transition-all"
                    placeholder="name@institute.edu"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-[#57534E] mb-1.5">Password</label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-[#A8A29E] absolute left-3.5 top-3" />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="w-full bg-[#FAF9F5] border border-[#E5E4DF] rounded-xl pl-10 pr-3 py-2.5 text-sm text-[#1C1917] focus:outline-none focus:border-[#1C1917] focus:bg-white transition-all"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-2 py-3 rounded-xl bg-[#1C1917] text-white font-medium text-sm hover:bg-[#292524] transition-all disabled:opacity-50 shadow-sm"
              >
                {loading ? 'Authenticating...' : 'Sign In to Workspace'}
              </button>
            </form>

            <div className="pt-2 border-t border-[#E5E4DF] text-center">
              <p className="text-[11px] text-[#78716C]">
                Need to evaluate quickly? <button onClick={() => setTab('quick')} className="text-[#C2410C] font-medium hover:underline">Use 1-Click Demo Personas</button>
              </p>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};
