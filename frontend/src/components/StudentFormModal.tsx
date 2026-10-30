import React, { useState, useEffect } from 'react';
import {
  X,
  AlertTriangle,
  CheckCircle2,
  UserPlus,
  Edit3,
  ShieldCheck,
  RefreshCw,
  Globe,
  Award
} from 'lucide-react';
import { Student, Programme, Course, StudentUpdateIn } from '../types';
import { fetchProgrammes, fetchCourses, createStudent, updateStudent } from '../services/api';
import { validateApaarId, cleanApaar } from '../utils/verhoeff';
import { Badge } from './Badge';

interface StudentFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  institutionId: string;
  studentToEdit?: Student | null;
}

export const StudentFormModal: React.FC<StudentFormModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  institutionId,
  studentToEdit
}) => {
  const isEdit = Boolean(studentToEdit);

  const [programmes, setProgrammes] = useState<Programme[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [loadingData, setLoadingData] = useState<boolean>(true);

  // Form State
  const [studentName, setStudentName] = useState('');
  const [internalStudentId, setInternalStudentId] = useState('');
  const [apaarId, setApaarId] = useState('');
  const [selectedProgramme, setSelectedProgramme] = useState('ENGINEERING_AND_TECHNOLOGY');
  const [selectedCourseId, setSelectedCourseId] = useState('');
  const [admissionYear, setAdmissionYear] = useState<number>(2024);
  const [academicYear, setAcademicYear] = useState('2024-2025');
  const [admissionStatus, setAdmissionStatus] = useState('ENROLLED');
  const [dateOfBirth, setDateOfBirth] = useState('2004-05-15');
  const [gender, setGender] = useState('MALE');
  const [category, setCategory] = useState('GENERAL');
  const [isSupernumerary, setIsSupernumerary] = useState(false);
  const [supernumeraryType, setSupernumeraryType] = useState('NONE');
  const [nriStatus, setNriStatus] = useState(false);
  const [ociStatus, setOciStatus] = useState(false);
  const [foreignNationalStatus, setForeignNationalStatus] = useState(false);

  // Validation & UI State
  const [apaarValidation, setApaarValidation] = useState<{ isValid: boolean; error?: string }>({ isValid: false });
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Initialize data and pre-fill if editing
  useEffect(() => {
    if (!isOpen) return;

    const init = async () => {
      try {
        setLoadingData(true);
        const [progs, crs] = await Promise.all([
          fetchProgrammes().catch(() => [
            { id: 'prog-eng', name: 'Engineering & Technology', code: 'ENGINEERING_AND_TECHNOLOGY' },
            { id: 'prog-mgmt', name: 'Management', code: 'MANAGEMENT' }
          ]),
          fetchCourses().catch(() => [
            { id: 'course-apex-cse', programme_id: 'prog-eng', name: 'Computer Science & Engineering', code: 'CSE', level: 'UG', duration_years: 4 },
            { id: 'course-apex-ece', programme_id: 'prog-eng', name: 'Electronics & Communication', code: 'ECE', level: 'UG', duration_years: 4 }
          ])
        ]);
        setProgrammes(progs);
        setCourses(crs);

        if (crs.length > 0 && !selectedCourseId) {
          setSelectedCourseId(crs[0].id);
        }

        if (studentToEdit) {
          setStudentName(studentToEdit.student_name);
          setInternalStudentId(studentToEdit.internal_id);
          setApaarId(''); // Keep blank unless updating
          setApaarValidation({ isValid: true });
          setSelectedProgramme(studentToEdit.programme || 'ENGINEERING_AND_TECHNOLOGY');
          
          const matchCourse = crs.find(c => c.name.toLowerCase() === studentToEdit.course.toLowerCase());
          if (matchCourse) {
            setSelectedCourseId(matchCourse.id);
          } else if (crs.length > 0) {
            setSelectedCourseId(crs[0].id);
          }

          setAdmissionYear(studentToEdit.admission_year || 2024);
          setAcademicYear(studentToEdit.academic_year || '2024-2025');
          setAdmissionStatus(studentToEdit.admission_status || 'ENROLLED');
          setDateOfBirth(studentToEdit.date_of_birth || '2004-05-15');
          setGender(studentToEdit.gender || 'MALE');
          setCategory(studentToEdit.category || 'GENERAL');
          setIsSupernumerary(Boolean(studentToEdit.is_supernumerary));
          setSupernumeraryType(studentToEdit.supernumerary_type || 'NONE');
          setNriStatus(Boolean(studentToEdit.nri_status));
          setOciStatus(Boolean(studentToEdit.oci_status));
          setForeignNationalStatus(Boolean(studentToEdit.foreign_national_status));
        } else {
          // Reset form for fresh creation
          setStudentName('');
          setInternalStudentId('');
          setApaarId('');
          setApaarValidation({ isValid: false });
          setAdmissionYear(2024);
          setAcademicYear('2024-2025');
          setAdmissionStatus('ENROLLED');
          setDateOfBirth('2004-05-15');
          setGender('MALE');
          setCategory('GENERAL');
          setIsSupernumerary(false);
          setSupernumeraryType('NONE');
          setNriStatus(false);
          setOciStatus(false);
          setForeignNationalStatus(false);
        }
      } catch (err: any) {
        console.error('Failed to init student form:', err);
      } finally {
        setLoadingData(false);
      }
    };

    init();
  }, [isOpen, studentToEdit]);

  const handleApaarChange = (val: string) => {
    setApaarId(val);
    const cleaned = cleanApaar(val);
    if (!cleaned) {
      setApaarValidation({ isValid: false, error: 'APAAR ID cannot be empty' });
      return;
    }
    const check = validateApaarId(cleaned);
    setApaarValidation(check);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    // Validate mandatory fields
    if (!studentName.trim()) {
      setFormError('Student full legal name is required.');
      return;
    }
    if (!internalStudentId.trim()) {
      setFormError('Institutional Roll No / Internal Student ID is required.');
      return;
    }
    if (!selectedCourseId) {
      setFormError('Please select a course allocation.');
      return;
    }

    if (!isEdit && !apaarValidation.isValid) {
      setFormError(apaarValidation.error || 'A valid 12-digit APAAR ID passing Verhoeff checksum is required.');
      return;
    }

    try {
      setSubmitting(true);

      if (isEdit && studentToEdit) {
        const updatePayload: StudentUpdateIn = {
          student_name: studentName.trim(),
          internal_student_id: internalStudentId.trim(),
          course_id: selectedCourseId,
          date_of_birth: dateOfBirth,
          gender: gender,
          category: category,
          admission_year: admissionYear,
          academic_year: academicYear,
          admission_status: admissionStatus,
          is_supernumerary: isSupernumerary,
          supernumerary_type: isSupernumerary ? supernumeraryType : 'NONE',
          nri_status: nriStatus,
          oci_status: ociStatus,
          foreign_national_status: foreignNationalStatus
        };

        if (apaarId.trim() && apaarValidation.isValid) {
          updatePayload.apaar_id = cleanApaar(apaarId);
        }

        await updateStudent(studentToEdit.id, updatePayload);
      } else {
        const createPayload = {
          internal_id: internalStudentId.trim(),
          student_name: studentName.trim(),
          apaar_id: cleanApaar(apaarId),
          programme: selectedProgramme,
          course: courses.find(c => c.id === selectedCourseId)?.name || 'Computer Science & Engineering',
          course_id: selectedCourseId,
          date_of_birth: dateOfBirth,
          gender: gender,
          category: category,
          admission_year: admissionYear,
          academic_year: academicYear,
          admission_status: admissionStatus,
          is_supernumerary: isSupernumerary,
          supernumerary_type: isSupernumerary ? supernumeraryType : 'NONE',
          nri_status: nriStatus,
          oci_status: ociStatus,
          foreign_national_status: foreignNationalStatus
        };

        await createStudent(createPayload, institutionId);
      }

      onSuccess();
      onClose();
    } catch (err: any) {
      setFormError(err.message || 'Operation failed. Please review the highlighted fields.');
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-stone-900/40 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-2xl bg-white border border-[#E5E4DF] rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.12)] overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E5E4DF] bg-[#FAF9F5]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-white border border-[#E5E4DF] flex items-center justify-center text-[#1C1917] shadow-sm">
              {isEdit ? <Edit3 className="w-5 h-5" /> : <UserPlus className="w-5 h-5" />}
            </div>
            <div>
              <h2 className="text-lg font-serif font-medium text-[#1C1917]">
                {isEdit ? `Edit Student: ${studentToEdit?.student_name}` : 'Onboard New Student Record'}
              </h2>
              <p className="text-xs text-[#78716C]">
                AICTE statutory verification with live Verhoeff APAAR checksum validation.
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

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-5 text-xs text-[#57534E]">
          
          {formError && (
            <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600" />
              <span>{formError}</span>
            </div>
          )}

          {/* Section 1: Core Student Identification */}
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-[#E5E4DF] pb-1.5">
              <span className="font-serif font-medium text-[#1C1917] uppercase tracking-wider text-xs">
                1. Identification & Name
              </span>
              <span className="text-[10px] text-[#78716C]">
                <span className="text-[#C2410C] font-bold">*</span> Mandatory fields
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block font-medium text-[#57534E] mb-1">
                  Student Full Name <span className="text-[#C2410C]">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Priyanshu Sharma"
                  value={studentName}
                  onChange={(e) => setStudentName(e.target.value)}
                  className="w-full bg-white border border-[#E5E4DF] rounded-xl px-3 py-2 text-[#1C1917] focus:outline-none focus:border-[#1C1917] font-medium"
                />
              </div>

              <div>
                <label className="block font-medium text-[#57534E] mb-1">
                  Internal Student ID / Roll No <span className="text-[#C2410C]">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. AIT-2024-CSE-099"
                  value={internalStudentId}
                  onChange={(e) => setInternalStudentId(e.target.value)}
                  className="w-full bg-white border border-[#E5E4DF] rounded-xl px-3 py-2 text-[#1C1917] focus:outline-none focus:border-[#1C1917] font-mono font-medium"
                />
              </div>
            </div>
          </div>

          {/* Section 2: National APAAR ID with Verhoeff Validation */}
          <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF] space-y-2">
            <div className="flex items-center justify-between">
              <label className="font-serif font-medium text-[#1C1917] flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-[#15803D]" />
                12-Digit National APAAR ID {isEdit ? '(Optional to Change)' : <span className="text-[#C2410C]">*</span>}
              </label>

              {apaarId.trim() && (
                apaarValidation.isValid ? (
                  <span className="inline-flex items-center gap-1 text-[11px] text-[#15803D] font-medium">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Valid Verhoeff Checksum
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-[11px] text-rose-700 font-medium">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    {apaarValidation.error || 'Invalid Checksum'}
                  </span>
                )
              )}
            </div>

            <input
              type="text"
              maxLength={14}
              required={!isEdit}
              placeholder={isEdit ? `Current: ${studentToEdit?.apaar_masked} (Leave blank to keep)` : 'e.g. 829104829202'}
              value={apaarId}
              onChange={(e) => handleApaarChange(e.target.value)}
              className={`w-full bg-white border rounded-xl px-3 py-2 text-[#1C1917] font-mono text-sm tracking-wider focus:outline-none ${
                apaarId.trim()
                  ? apaarValidation.isValid
                    ? 'border-emerald-500 focus:border-emerald-600'
                    : 'border-rose-400 focus:border-rose-500'
                  : 'border-[#E5E4DF] focus:border-[#1C1917]'
              }`}
            />
            <p className="text-[10px] text-[#78716C]">
              The 12th digit represents the Verhoeff checksum. The raw ID is encrypted and masked immediately upon saving.
            </p>
          </div>

          {/* Section 3: Academic Allocation & Course */}
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-[#E5E4DF] pb-1.5">
              <span className="font-serif font-medium text-[#1C1917] uppercase tracking-wider text-xs">
                2. Academic Allocation & Session
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block font-medium text-[#57534E] mb-1">
                  Programme Domain <span className="text-[#C2410C]">*</span>
                </label>
                <select
                  value={selectedProgramme}
                  onChange={(e) => setSelectedProgramme(e.target.value)}
                  className="w-full bg-white border border-[#E5E4DF] rounded-xl px-3 py-2 text-[#1C1917] focus:outline-none focus:border-[#1C1917]"
                >
                  <option value="ENGINEERING_AND_TECHNOLOGY">Engineering & Technology</option>
                  <option value="MANAGEMENT">Management (MBA/PGDM)</option>
                  <option value="PHARMACY">Pharmacy</option>
                  <option value="APPLIED_ARTS">Applied Arts & Crafts</option>
                </select>
              </div>

              <div>
                <label className="block font-medium text-[#57534E] mb-1">
                  Course Allocation <span className="text-[#C2410C]">*</span>
                </label>
                <select
                  value={selectedCourseId}
                  onChange={(e) => setSelectedCourseId(e.target.value)}
                  className="w-full bg-white border border-[#E5E4DF] rounded-xl px-3 py-2 text-[#1C1917] focus:outline-none focus:border-[#1C1917]"
                >
                  {courses.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.code})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-medium text-[#57534E] mb-1">
                  Academic Session <span className="text-[#C2410C]">*</span>
                </label>
                <select
                  value={academicYear}
                  onChange={(e) => setAcademicYear(e.target.value)}
                  className="w-full bg-white border border-[#E5E4DF] rounded-xl px-3 py-2 text-[#1C1917] focus:outline-none focus:border-[#1C1917]"
                >
                  <option value="2024-2025">2024-2025</option>
                  <option value="2023-2024">2023-2024</option>
                </select>
              </div>

              <div>
                <label className="block font-medium text-[#57534E] mb-1">
                  Admission Status <span className="text-[#C2410C]">*</span>
                </label>
                <select
                  value={admissionStatus}
                  onChange={(e) => setAdmissionStatus(e.target.value)}
                  className="w-full bg-white border border-[#E5E4DF] rounded-xl px-3 py-2 text-[#1C1917] focus:outline-none focus:border-[#1C1917]"
                >
                  <option value="ENROLLED">Enrolled (Active)</option>
                  <option value="ADMITTED">Admitted (Pending Class Start)</option>
                  <option value="PROVISIONAL">Provisional</option>
                  <option value="SUSPENDED">Suspended</option>
                  <option value="COMPLETED">Completed</option>
                </select>
              </div>
            </div>
          </div>

          {/* Section 4: Demographics */}
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-[#E5E4DF] pb-1.5">
              <span className="font-serif font-medium text-[#1C1917] uppercase tracking-wider text-xs">
                3. Personal Demographics
              </span>
              <span className="text-[10px] text-[#78716C]">(Optional for Reconciliation)</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block font-medium text-[#57534E] mb-1">
                  Date of Birth <span className="text-[#C2410C]">*</span>
                </label>
                <input
                  type="date"
                  required
                  value={dateOfBirth}
                  onChange={(e) => setDateOfBirth(e.target.value)}
                  className="w-full bg-white border border-[#E5E4DF] rounded-xl px-3 py-2 text-[#1C1917] focus:outline-none focus:border-[#1C1917]"
                />
              </div>

              <div>
                <label className="block font-medium text-[#57534E] mb-1">Gender</label>
                <select
                  value={gender}
                  onChange={(e) => setGender(e.target.value)}
                  className="w-full bg-white border border-[#E5E4DF] rounded-xl px-3 py-2 text-[#1C1917] focus:outline-none focus:border-[#1C1917]"
                >
                  <option value="MALE">Male</option>
                  <option value="FEMALE">Female</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>

              <div>
                <label className="block font-medium text-[#57534E] mb-1">Category</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full bg-white border border-[#E5E4DF] rounded-xl px-3 py-2 text-[#1C1917] focus:outline-none focus:border-[#1C1917]"
                >
                  <option value="GENERAL">General</option>
                  <option value="OBC">OBC</option>
                  <option value="SC">SC</option>
                  <option value="ST">ST</option>
                  <option value="EWS">EWS</option>
                </select>
              </div>
            </div>
          </div>

          {/* Section 5: Supernumerary Seat & Quota */}
          <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF] space-y-3">
            <div className="flex items-center gap-2.5">
              <input
                type="checkbox"
                id="is_supernumerary_checkbox"
                checked={isSupernumerary}
                onChange={(e) => setIsSupernumerary(e.target.checked)}
                className="w-4 h-4 rounded border-[#E5E4DF] text-[#1C1917] focus:ring-0"
              />
              <label htmlFor="is_supernumerary_checkbox" className="font-serif font-medium text-[#1C1917] cursor-pointer">
                Supernumerary Quota Seat
              </label>
              <span className="text-[10px] text-[#78716C]">
                (Audited outside core approved intake pool)
              </span>
            </div>

            {isSupernumerary && (
              <div className="pt-2">
                <label className="block text-[#57534E] font-medium mb-1">
                  Supernumerary Quota Type <span className="text-[#C2410C]">*</span>
                </label>
                <select
                  value={supernumeraryType}
                  onChange={(e) => setSupernumeraryType(e.target.value)}
                  className="w-full bg-white border border-[#E5E4DF] rounded-xl px-3 py-2 text-[#1C1917] focus:outline-none focus:border-[#1C1917]"
                >
                  <option value="TFW">TFW (Tuition Fee Waiver - 5%)</option>
                  <option value="NRI">NRI Quota (5%)</option>
                  <option value="FOREIGN_NATIONAL">Foreign National / PIO (15%)</option>
                  <option value="J_AND_K_PMSSS">J&K PMSSS</option>
                  <option value="PM_CARES">PM-CARES</option>
                  <option value="SPORTS">Sports Quota</option>
                </select>
              </div>
            )}
          </div>

          {/* Section 6: Non-Mutually Exclusive Nationality Categories */}
          <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#E5E4DF] space-y-2">
            <span className="block font-serif font-medium text-[#1C1917]">
              Nationality & Domicile Indicators (Non-Mutually Exclusive)
            </span>
            <p className="text-[10px] text-[#78716C] mb-2">
              Select all statuses that apply according to student documentation.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <label className="flex items-center gap-2 p-2.5 rounded-lg bg-white border border-[#E5E4DF] cursor-pointer hover:border-[#D5D3CA]">
                <input
                  type="checkbox"
                  checked={nriStatus}
                  onChange={(e) => setNriStatus(e.target.checked)}
                  className="w-4 h-4 rounded border-[#E5E4DF] text-[#1C1917] focus:ring-0"
                />
                <span className="font-medium text-[#57534E] text-xs">NRI Category</span>
              </label>

              <label className="flex items-center gap-2 p-2.5 rounded-lg bg-white border border-[#E5E4DF] cursor-pointer hover:border-[#D5D3CA]">
                <input
                  type="checkbox"
                  checked={ociStatus}
                  onChange={(e) => setOciStatus(e.target.checked)}
                  className="w-4 h-4 rounded border-[#E5E4DF] text-[#1C1917] focus:ring-0"
                />
                <span className="font-medium text-[#57534E] text-xs">OCI Status</span>
              </label>

              <label className="flex items-center gap-2 p-2.5 rounded-lg bg-white border border-[#E5E4DF] cursor-pointer hover:border-[#D5D3CA]">
                <input
                  type="checkbox"
                  checked={foreignNationalStatus}
                  onChange={(e) => setForeignNationalStatus(e.target.checked)}
                  className="w-4 h-4 rounded border-[#E5E4DF] text-[#1C1917] focus:ring-0"
                />
                <span className="font-medium text-[#57534E] text-xs">Foreign National</span>
              </label>
            </div>
          </div>

          {/* Submit Buttons */}
          <div className="pt-4 border-t border-[#E5E4DF] flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="px-4 py-2 rounded-lg bg-white hover:bg-[#F4F3EE] text-[#57534E] border border-[#E5E4DF] font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex items-center gap-2 px-5 py-2 rounded-lg bg-[#1C1917] hover:bg-[#292524] text-white font-medium transition-all shadow-sm disabled:opacity-50"
            >
              {submitting ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Saving & Re-validating...
                </>
              ) : (
                isEdit ? 'Save Changes' : 'Confirm Student Onboarding'
              )}
            </button>
          </div>

        </form>

      </div>
    </div>
  );
};
