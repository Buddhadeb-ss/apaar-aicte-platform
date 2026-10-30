import React, { useState } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  Building2,
  GraduationCap,
  QrCode,
  User,
  LogOut,
  ChevronDown,
  Sparkles,
  ExternalLink,
  FileSpreadsheet,
  FileCheck
} from 'lucide-react';
import { UserProfile, DemoProfile } from '../types';
import { Badge } from './Badge';

interface NavbarProps {
  user: UserProfile | null;
  demoProfiles: DemoProfile[];
  onSwitchPersona: (index: number) => void;
  onLogout: () => void;
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  user,
  demoProfiles,
  onSwitchPersona,
  onLogout,
  activeTab,
  setActiveTab
}) => {
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const getRoleBadge = (role: string) => {
    switch (role) {
      case 'AICTE_ADMIN':
        return <Badge variant="saffron"><ShieldCheck className="w-3 h-3" /> AICTE National Scrutiny</Badge>;
      case 'INSTITUTE_ADMIN':
      case 'INSTITUTION_ADMIN':
        return <Badge variant="info"><Building2 className="w-3 h-3" /> Institution Registrar</Badge>;
      case 'INSTITUTION_OPERATOR':
        return <Badge variant="info"><FileSpreadsheet className="w-3 h-3" /> Institution Operator</Badge>;
      case 'STUDENT':
      case 'STUDENT_VIEWER':
        return <Badge variant="emerald"><GraduationCap className="w-3 h-3" /> Verified Student</Badge>;
      case 'VERIFIER':
      case 'AUTHORIZED_VERIFIER':
        return <Badge variant="warning"><QrCode className="w-3 h-3" /> Authorized Verifier</Badge>;
      default:
        return <Badge variant="neutral">{role}</Badge>;
    }
  };

  return (
    <header className="sticky top-0 z-40 w-full bg-[#FAF9F5]/95 backdrop-blur-md border-b border-[#E5E4DF] shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-18 py-3">
          
          {/* AICTE Logo & Branding in Anthropic Editorial Style */}
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-[#1C1917] text-white flex items-center justify-center font-serif font-bold text-base shadow-sm border border-[#44403C]/30 shrink-0">
              A
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-base sm:text-lg font-serif font-semibold tracking-tight text-[#1C1917]">
                  AICTE APAAR Platform
                </span>
                <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-full bg-[#F4F3EE] text-[#57534E] border border-[#E5E4DF]">
                  SIH26263
                </span>
              </div>
              <p className="text-xs text-[#78716C] font-serif italic hidden sm:block">
                National Student Registry • Approved Intake Monitoring • Instant Credential Verification
              </p>
            </div>
          </div>

          {/* Navigation Items */}
          {user && (
            <nav className="hidden md:flex items-center gap-1.5 bg-[#F4F3EE] p-1 rounded-xl border border-[#E5E4DF]">
              {user.role === 'AICTE_ADMIN' && (
                <>
                  <button
                    onClick={() => setActiveTab('aicte-overview')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      activeTab === 'aicte-overview'
                        ? 'bg-white text-[#1C1917] font-semibold shadow-sm border border-[#E5E4DF]'
                        : 'text-[#57534E] hover:text-[#1C1917]'
                    }`}
                  >
                    National Scrutiny
                  </button>
                  <button
                    onClick={() => setActiveTab('institution-view')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      activeTab === 'institution-view'
                        ? 'bg-white text-[#1C1917] font-semibold shadow-sm border border-[#E5E4DF]'
                        : 'text-[#57534E] hover:text-[#1C1917]'
                    }`}
                  >
                    Institutions
                  </button>
                  <button
                    onClick={() => setActiveTab('workbench')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
                      activeTab === 'workbench'
                        ? 'bg-rose-50 text-rose-800 font-semibold shadow-sm border border-rose-200'
                        : 'text-rose-700 hover:bg-rose-50/50'
                    }`}
                  >
                    <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />
                    Validation Workbench
                  </button>
                </>
              )}

              {(user.role === 'INSTITUTE_ADMIN' || user.role === 'INSTITUTION_ADMIN' || user.role === 'INSTITUTION_OPERATOR') && (
                <>
                  <button
                    onClick={() => setActiveTab('overview')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      activeTab === 'overview'
                        ? 'bg-white text-[#1C1917] font-semibold shadow-sm border border-[#E5E4DF]'
                        : 'text-[#57534E] hover:text-[#1C1917]'
                    }`}
                  >
                    Overview
                  </button>
                  <button
                    onClick={() => setActiveTab('students')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      activeTab === 'students'
                        ? 'bg-white text-[#1C1917] font-semibold shadow-sm border border-[#E5E4DF]'
                        : 'text-[#57534E] hover:text-[#1C1917]'
                    }`}
                  >
                    Student Directory
                  </button>
                  <button
                    onClick={() => setActiveTab('workbench')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
                      activeTab === 'workbench'
                        ? 'bg-rose-50 text-rose-800 font-semibold shadow-sm border border-rose-200'
                        : 'text-rose-700 hover:bg-rose-50/50'
                    }`}
                  >
                    <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />
                    Validation
                  </button>
                  <button
                    onClick={() => setActiveTab('import')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
                      activeTab === 'import'
                        ? 'bg-white text-[#1C1917] font-semibold shadow-sm border border-[#E5E4DF]'
                        : 'text-[#57534E] hover:text-[#1C1917]'
                    }`}
                  >
                    <FileSpreadsheet className="w-3.5 h-3.5 text-[#78716C]" />
                    Bulk Import
                  </button>
                  <button
                    onClick={() => setActiveTab('upload-jobs')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      activeTab === 'upload-jobs'
                        ? 'bg-white text-[#1C1917] font-semibold shadow-sm border border-[#E5E4DF]'
                        : 'text-[#57534E] hover:text-[#1C1917]'
                    }`}
                  >
                    Job History
                  </button>
                  <button
                    onClick={() => setActiveTab('reconciliation')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      activeTab === 'reconciliation'
                        ? 'bg-white text-[#1C1917] font-semibold shadow-sm border border-[#E5E4DF]'
                        : 'text-[#57534E] hover:text-[#1C1917]'
                    }`}
                  >
                    Intake Monitoring
                  </button>
                </>
              )}

              {(user.role === 'STUDENT' || user.role === 'STUDENT_VIEWER') && (
                <button
                  onClick={() => setActiveTab('my-credential')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
                    activeTab === 'my-credential'
                      ? 'bg-emerald-50 text-emerald-800 font-semibold shadow-sm border border-emerald-200'
                      : 'text-emerald-700 hover:bg-emerald-50/50'
                  }`}
                >
                  <GraduationCap className="w-3.5 h-3.5" />
                  My APAAR Credential
                </button>
              )}

              {/* QR Verification Portal */}
              <button
                onClick={() => setActiveTab('verify-qr')}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
                  activeTab === 'verify-qr'
                    ? 'bg-amber-50 text-amber-900 font-semibold shadow-sm border border-amber-200'
                    : 'text-[#57534E] hover:text-[#1C1917]'
                }`}
              >
                <QrCode className="w-3.5 h-3.5 text-[#78716C]" />
                QR Verifier
              </button>
            </nav>
          )}

          {/* User Profile & Demo Switcher */}
          <div className="flex items-center gap-3">
            {user ? (
              <div className="relative">
                <button
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl bg-white border border-[#E5E4DF] hover:border-[#D5D3CA] transition-all text-left shadow-[0_1px_2px_rgba(0,0,0,0.03)]"
                >
                  <div className="w-7 h-7 rounded-lg bg-[#FAF9F5] border border-[#E5E4DF] flex items-center justify-center text-[#1C1917] font-serif font-bold text-xs">
                    {user.name.charAt(0)}
                  </div>
                  <div className="hidden sm:block">
                    <p className="text-xs font-medium text-[#1C1917] leading-tight">{user.name}</p>
                    <div className="mt-0.5">{getRoleBadge(user.role)}</div>
                  </div>
                  <ChevronDown className="w-3.5 h-3.5 text-[#78716C] ml-1" />
                </button>

                {/* Dropdown Menu */}
                {dropdownOpen && (
                  <div className="absolute right-0 mt-2 w-80 rounded-2xl bg-white border border-[#E5E4DF] shadow-xl p-2 z-50">
                    <div className="p-3 border-b border-[#E5E4DF]">
                      <p className="text-[10px] font-bold text-[#78716C] uppercase tracking-wider">Active Evaluation Profile</p>
                      <p className="text-sm font-serif font-semibold text-[#1C1917] mt-0.5">{user.name}</p>
                      <p className="text-xs text-[#78716C] font-mono mt-0.5">{user.email}</p>
                    </div>

                    <div className="py-2">
                      <p className="text-[10px] font-bold text-[#78716C] uppercase tracking-wider px-3 mb-1.5 flex items-center gap-1.5">
                        <Sparkles className="w-3 h-3 text-[#C2410C]" />
                        Quick 1-Click Persona Switcher
                      </p>
                      {demoProfiles.map((p, idx) => (
                        <button
                          key={p.email}
                          onClick={() => {
                            setDropdownOpen(false);
                            onSwitchPersona(idx);
                          }}
                          className={`w-full text-left p-2 rounded-xl text-xs transition-all flex items-start gap-2.5 ${
                            user.email === p.email
                              ? 'bg-[#FAF9F5] border border-[#E5E4DF] text-[#1C1917] font-medium'
                              : 'hover:bg-[#F4F3EE] text-[#57534E]'
                          }`}
                        >
                          <div className="w-6 h-6 rounded-md bg-[#FAF9F5] border border-[#E5E4DF] flex items-center justify-center text-[#1C1917] shrink-0 mt-0.5">
                            {p.role === 'AICTE_ADMIN' && <ShieldCheck className="w-3.5 h-3.5 text-[#C2410C]" />}
                            {(p.role === 'INSTITUTE_ADMIN' || p.role === 'INSTITUTION_ADMIN') && <Building2 className="w-3.5 h-3.5 text-[#1E3A8A]" />}
                            {p.role === 'INSTITUTION_OPERATOR' && <FileSpreadsheet className="w-3.5 h-3.5 text-[#1E3A8A]" />}
                            {(p.role === 'STUDENT' || p.role === 'STUDENT_VIEWER') && <GraduationCap className="w-3.5 h-3.5 text-emerald-700" />}
                            {(p.role === 'VERIFIER' || p.role === 'AUTHORIZED_VERIFIER') && <QrCode className="w-3.5 h-3.5 text-amber-800" />}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-[#1C1917] truncate">{p.label}</p>
                            <p className="text-[10px] text-[#78716C] line-clamp-1">{p.name}</p>
                          </div>
                        </button>
                      ))}
                    </div>

                    <div className="pt-2 border-t border-[#E5E4DF]">
                      <button
                        onClick={() => {
                          setDropdownOpen(false);
                          onLogout();
                        }}
                        className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium text-rose-700 hover:bg-rose-50 rounded-xl transition-all"
                      >
                        <LogOut className="w-4 h-4" />
                        Sign Out
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2.5">
                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-[#F4F3EE] text-[#57534E] border border-[#E5E4DF]">
                  <span className="w-2 h-2 rounded-full bg-emerald-600 animate-pulse"></span>
                  Live Demo Portal
                </span>
              </div>
            )}
          </div>

        </div>
      </div>
    </header>
  );
};
