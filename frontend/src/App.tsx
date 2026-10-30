import React, { useState, useEffect } from 'react';
import { UserProfile, DemoProfile } from './types';
import {
  fetchCurrentUser,
  fetchDemoProfiles,
  quickDemoLogin,
  loginWithCredentials,
  removeAuthToken
} from './services/api';
import { Navbar } from './components/Navbar';
import { LoginPage } from './pages/LoginPage';
import { AicteDashboard } from './pages/AicteDashboard';
import { InstitutionPortal } from './pages/InstitutionPortal';
import { StudentImportPage } from './pages/StudentImportPage';
import { StudentPortal } from './pages/StudentPortal';
import { VerificationPortal } from './pages/VerificationPortal';
import { ValidationWorkbench } from './pages/ValidationWorkbench';
import { RefreshCw } from 'lucide-react';

export const App: React.FC = () => {
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [demoProfiles, setDemoProfiles] = useState<DemoProfile[]>([]);
  const [activeTab, setActiveTab] = useState<string>('login');
  const [selectedInstitutionId, setSelectedInstitutionId] = useState<string>('inst-apex-1001');
  const [selectedStudentId, setSelectedStudentId] = useState<string | undefined>(undefined);
  const [loading, setLoading] = useState<boolean>(true);
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    const initApp = async () => {
      try {
        setLoading(true);
        // Load demo profiles
        const profiles = await fetchDemoProfiles();
        setDemoProfiles(profiles);

        // Try getting active user
        try {
          const user = await fetchCurrentUser();
          setCurrentUser(user);
          routeUser(user);
        } catch {
          // If not logged in, auto-login into demo profile 0 (AICTE Admin) for immediate evaluation readiness!
          const tokenRes = await quickDemoLogin(0);
          const initialUser: UserProfile = {
            id: 'user-aicte-admin',
            email: tokenRes.email,
            name: tokenRes.name,
            role: tokenRes.role,
            institution_id: tokenRes.institution_id,
            student_internal_id: tokenRes.student_internal_id
          };
          setCurrentUser(initialUser);
          routeUser(initialUser);
        }
      } catch (err: any) {
        console.error('Initialization error:', err);
      } finally {
        setLoading(false);
      }
    };

    initApp();
  }, []);

  const routeUser = (user: UserProfile) => {
    switch (user.role) {
      case 'AICTE_ADMIN':
        setActiveTab('aicte-overview');
        break;
      case 'INSTITUTE_ADMIN':
      case 'INSTITUTION_ADMIN':
      case 'INSTITUTION_OPERATOR':
        setSelectedInstitutionId(user.institution_id || 'inst-apex-1001');
        setActiveTab('overview');
        break;
      case 'STUDENT':
      case 'STUDENT_VIEWER':
        setActiveTab('my-credential');
        break;
      case 'VERIFIER':
      case 'AUTHORIZED_VERIFIER':
        setActiveTab('verify-qr');
        break;
      default:
        setActiveTab('login');
    }
  };

  const handleDemoLogin = async (index: number) => {
    try {
      setLoading(true);
      setAuthError(null);
      const tokenRes = await quickDemoLogin(index);
      const user = await fetchCurrentUser();
      setCurrentUser(user);
      routeUser(user);
    } catch (err: any) {
      setAuthError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleCredentialLogin = async (email: string, pass: string) => {
    try {
      setLoading(true);
      setAuthError(null);
      await loginWithCredentials(email, pass);
      const user = await fetchCurrentUser();
      setCurrentUser(user);
      routeUser(user);
    } catch (err: any) {
      setAuthError(err.message || 'Invalid credentials');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    removeAuthToken();
    setCurrentUser(null);
    setActiveTab('login');
  };

  const handleSelectInstitution = (instId: string) => {
    setSelectedInstitutionId(instId);
    setActiveTab('institution-view');
  };

  const handleViewStudentCredential = (studentId: string) => {
    setSelectedStudentId(studentId);
    setActiveTab('my-credential');
  };

  if (loading && !currentUser) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-[#FAF9F5] text-[#1C1917] gap-3">
        <div className="w-12 h-12 rounded-xl bg-[#1C1917] text-white flex items-center justify-center font-serif font-bold text-xl shadow-sm border border-[#44403C]/30 animate-pulse">
          A
        </div>
        <p className="text-sm font-serif font-medium text-[#1C1917]">
          AICTE APAAR Student Data Platform
        </p>
        <RefreshCw className="w-4 h-4 text-[#C2410C] animate-spin mt-1" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#FAF9F5] text-[#1C1917] selection:bg-[#CC785C]/20 selection:text-[#1C1917]">
      
      {/* Top Navbar */}
      <Navbar
        user={currentUser}
        demoProfiles={demoProfiles}
        onSwitchPersona={handleDemoLogin}
        onLogout={handleLogout}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />

      {/* Main Dynamic View Content */}
      <main className="flex-1">
        {activeTab === 'login' && (
          <LoginPage
            demoProfiles={demoProfiles}
            onDemoLogin={handleDemoLogin}
            onCredentialLogin={handleCredentialLogin}
            loading={loading}
            error={authError}
          />
        )}

        {activeTab === 'aicte-overview' && (
          <AicteDashboard
            onSelectInstitution={handleSelectInstitution}
            onNavigateToWorkbench={() => setActiveTab('workbench')}
          />
        )}

        {activeTab === 'workbench' && (
          <ValidationWorkbench
            institutionId={
              (currentUser?.role === 'INSTITUTE_ADMIN' ||
                currentUser?.role === 'INSTITUTION_ADMIN' ||
                currentUser?.role === 'INSTITUTION_OPERATOR') &&
              currentUser.institution_id
                ? currentUser.institution_id
                : selectedInstitutionId
            }
            userRole={currentUser?.role}
            onNavigateToStudent={handleViewStudentCredential}
          />
        )}

        {(activeTab === 'overview' || activeTab === 'institution-view' || activeTab === 'reconciliation' || activeTab === 'students') && (
          <InstitutionPortal
            institutionId={
              (currentUser?.role === 'INSTITUTE_ADMIN' ||
                currentUser?.role === 'INSTITUTION_ADMIN' ||
                currentUser?.role === 'INSTITUTION_OPERATOR') &&
              currentUser.institution_id
                ? currentUser.institution_id
                : selectedInstitutionId
            }
            initialTab={activeTab === 'students' ? 'directory' : activeTab === 'reconciliation' ? 'reconciliation' : 'overview'}
            onViewStudentCredential={handleViewStudentCredential}
            onNavigateToImport={() => setActiveTab('import')}
            onNavigateToWorkbench={() => setActiveTab('workbench')}
          />
        )}

        {(activeTab === 'import' || activeTab === 'upload-jobs') && (
          <StudentImportPage
            institutionId={currentUser?.institution_id || selectedInstitutionId}
            initialTab={activeTab === 'upload-jobs' ? 'history' : 'wizard'}
            onViewRoster={() => setActiveTab('students')}
          />
        )}

        {activeTab === 'my-credential' && (
          <StudentPortal
            studentId={selectedStudentId}
            studentRoll={currentUser?.student_internal_id}
          />
        )}

        {activeTab === 'verify-qr' && (
          <VerificationPortal />
        )}
      </main>

      {/* Institutional Footer in Anthropic Clean Style */}
      <footer className="border-t border-[#E5E4DF] bg-white py-6 px-4 text-center text-xs text-[#78716C]">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="font-serif">
            © 2026 All India Council for Technical Education (AICTE). Statutory Verification Platform.
          </p>
          <div className="flex items-center gap-4">
            <span className="font-mono text-[#A8A29E]">SIH26263 • v1.0.0</span>
            <span className="text-[#D5D3CA]">•</span>
            <span className="text-[#15803D] font-medium font-serif italic">Simulated ABC/DigiLocker Gateway v2.4</span>
          </div>
        </div>
      </footer>

    </div>
  );
};
