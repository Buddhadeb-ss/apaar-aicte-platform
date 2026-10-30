# AICTE APAAR Platform | SIH26263
**APAAR ID-Based Student Data Management & Verification Platform for AICTE-Approved Institutions**

A secure, interoperable, statutory regulatory platform engineered for Smart India Hackathon problem statement **SIH26263**. The platform enforces AICTE Approval Process Handbook (APH) sanctioned intake capacities, manages student enrolments tied to 12-digit APAAR IDs, detects concurrent cross-institutional duplicate enrolments, and enables instant cryptographic QR-based credential verifications.

---

## 1. Core Architectural Pillars

### A. Separation of Sanctioned Core Intake vs Student Records
Under statutory AICTE regulations, **approved intake is never represented as a student-level property**. 
- Approved intake limits and supernumerary caps (TFW 5%, NRI 5%, Foreign National 15%) are defined strictly at the institutional course level in `institution_intakes`.
- Student records are modeled through separate student identity records (`students`) and enrolment records (`student_enrolments`).
- Actual confirmed enrolments are aggregated dynamically, and courses where regular admissions exceed sanctioned seats are flagged with an **`OVER_ADMISSION_VIOLATION`**.

### B. Multiple Enrolments Modeled Separately from Student Identity
A student holds a single permanent identity and 12-digit APAAR ID with a stable UUID. Academic enrolments are modeled in a distinct relational table `student_enrolments`. This enables:
- Detecting multi-college concurrent enrolment collisions in real-time.
- Tracking academic history across programmes and sessions.
- Associating distinct roll numbers and credentials with individual programmes.

### C. APAAR ID Privacy & Collision Hashing
- **Never Cleartext in UI/Logs**: APAAR IDs are strictly encrypted/salted at rest. All dashboards, public verification endpoints, and logs return privacy-masked identifiers (`•••• •••• 1098`).
- **Verhoeff & Luhn Checksums**: 12-digit numbers are validated against the Verhoeff algorithm before entry.
- **Salted SHA-256 Collision Index**: An indexed `apaar_hash` enables instantaneous detection of students registered across multiple technical colleges simultaneously without revealing raw national IDs.

### D. Cryptographic HMAC-SHA256 Signatures & Verifiable QR Passes
- Every student enrolment is issued a tamper-evident digital credential signed by the server (`HMAC-SHA256`).
- QR codes encode signed payloads that third-party verifiers can authenticate offline or online.

---

## 2. Pre-Configured Demonstration Accounts & Personas

The platform includes 5 working demonstration accounts with PBKDF2-HMAC-SHA256 password hashing. You can log in with credentials or use the **1-Click Evaluation Switcher** in the UI:

| Persona | Role | Email | Password | Scope & Permitted Actions |
| :--- | :--- | :--- | :--- | :--- |
| **AICTE National Director** | `AICTE_ADMIN` | `admin@aicte.gov.in` | `Aicte@2026` | National scrutiny console, intake compliance across all colleges, multi-college duplicate collision detector, and statutory audit logs. |
| **Apex Institute Registrar** | `INSTITUTION_ADMIN` | `registrar@apex.edu` | `Apex@2026` | Apex Institute of Technology (`inst-apex-1001`), course intake reconciliation, student roster, single onboarding, and official PDF certificate download. |
| **Apex Data Operator** | `INSTITUTION_OPERATOR` | `operator@apex.edu` | `Operator@2026` | Apex Institute of Technology (`inst-apex-1001`), CSV bulk onboarding, and inline staging error resolution queue. |
| **Enrolled Student (Aarav)** | `STUDENT_VIEWER` | `student@apex.edu` | `Student@2026` | Personal academic record (Roll: `AIT-2024-CSE-007`), privacy-masked APAAR view, and signed verifiable QR pass. |
| **TCS Background Verifier** | `AUTHORIZED_VERIFIER` | `verifier@tcs.com` | `Tcs@2026` | Third-party verifier console, QR token verification, HMAC signature validation, and immutable audit logging. |

---

## 3. Directory Layout

```text
apaar-aicte-platform/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/                       # Versioned REST API endpoints
│   │   │   │   ├── health.py             # Liveness & readiness probes
│   │   │   │   ├── auth.py               # Authentication & 5 demo personas
│   │   │   │   ├── institutions.py       # Institutions & programmes CRUD
│   │   │   │   ├── intakes.py            # Intake limits & reconciliation
│   │   │   │   ├── students.py           # Student CRUD, search, credential pass
│   │   │   │   ├── upload_jobs.py        # Bulk CSV upload jobs & staging
│   │   │   │   ├── validation.py         # Validation issues & inline resolution
│   │   │   │   ├── dashboard.py          # AICTE national metrics & collisions
│   │   │   │   ├── verifications.py      # QR verification & consent checks
│   │   │   │   └── reports.py            # ReportLab PDF & CSV exports
│   │   │   └── deps.py                   # RBAC & multi-tenant scoping
│   │   ├── core/
│   │   │   ├── config.py                 # Settings, secrets & database URL
│   │   │   ├── identifiers.py            # UUIDs, normalization, Verhoeff, masking
│   │   │   └── security.py               # PBKDF2 hashing, JWT & HMAC signatures
│   │   ├── database/
│   │   │   ├── session.py                # SQLite engine, WAL mode & foreign keys
│   │   │   ├── models.py                 # SQLAlchemy relational schema
│   │   │   └── seed_data.py              # Synthetic realistic seeder
│   │   └── main.py                       # FastAPI entrypoint & SPA static mount
│   ├── tests/
│   │   ├── test_v1_api.py                # Comprehensive integration test suite
│   │   └── test_api.py                   # Baseline tests
│   ├── init_db.py                        # Standalone database initialization script
│   ├── run_server.py                     # Uvicorn launcher
│   ├── requirements.txt                  # Python dependencies
│   └── .env.example                      # Backend environment template
├── frontend/
│   ├── src/
│   │   ├── components/                   # Navbar, StatCard, Badge, Modal
│   │   ├── pages/                        # Role dashboards & verification portal
│   │   ├── services/api.ts               # API client
│   │   ├── types.ts                      # TypeScript interfaces
│   │   ├── App.tsx                       # Global state & persona router
│   │   └── main.tsx                      # Vite React entrypoint
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── .env.example
└── README.md
```

---

## 4. Quick Startup Instructions

### Prerequisites
- Python 3.12 or 3.13
- Node.js LTS (v20+ or v24+)

### 1. Initialize and Seed the Database
```powershell
cd c:\All_Projects\apaar-aicte-platform\backend
python init_db.py
```
This drops any existing temporary state, builds the full relational schema, and seeds realistic synthetic AICTE colleges, programmes, course intakes, student enrolments, signed credentials, and collision alert scenarios.

### 2. Start the Backend API Server
```powershell
python run_server.py
```
The server will start at **`http://127.0.0.1:8000`**.
- Interactive OpenAPI documentation: **[`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs)**
- Health & Readiness endpoint: **[`http://127.0.0.1:8000/api/v1/health`](http://127.0.0.1:8000/api/v1/health)**

### 3. Run Automated Tests
```powershell
python -m pytest tests/test_v1_api.py -v
```

### 4. Build or Run the Frontend
The backend automatically serves the compiled production build from `frontend/dist` at `http://127.0.0.1:8000/`.
To rebuild the frontend:
```powershell
cd c:\All_Projects\apaar-aicte-platform\frontend
npm run build
```
Or start Vite dev server:
```powershell
npm run dev
```

---

## 5. API Route Specification (/api/v1)

### Health & Readiness
- `GET /api/v1/health`: Checks database persistence, counts loaded institutions & enrolments, verifies gateway simulation.

### Authentication & Current User
- `GET /api/v1/auth/demo-profiles`: Lists 5 pre-configured demo personas.
- `POST /api/v1/auth/demo-login/{index}`: 1-click evaluation login returning JWT bearer token.
- `POST /api/v1/auth/login`: Standard credential login.
- `GET /api/v1/auth/me`: Authenticated user profile and institutional scope.

### Institutions & Programmes
- `GET /api/v1/institutions`: Paginated, searchable institution directory.
- `GET /api/v1/institutions/{id}`: Detailed institution profile with sanctioned course intakes.
- `GET /api/v1/institutions/programmes`: Statutory AICTE programmes (Engineering, Management, Pharmacy).
- `GET /api/v1/institutions/courses`: Courses list with optional programme filter.

### Intake Limits & Reconciliation
- `GET /api/v1/intakes/reconciliation/{institution_id}`: Course-by-course Approved Intake vs Enrolled Students reconciliation schedule, with supernumerary breakdowns (TFW, NRI, FN).

### Students & Enrolments
- `GET /api/v1/students`: Filterable student roster with pagination; masked APAAR IDs (`•••• •••• XXXX`).
- `POST /api/v1/students`: Single student onboarding with Verhoeff validation, unique internal roll check, duplicate APAAR collision check, and intake cap check in an atomic transaction.
- `GET /api/v1/students/{id}/credential`: Generates verifiable digital credential pass with QR code and HMAC signature.

### Bulk Upload Jobs & Validation
- `GET /api/v1/upload-jobs`: Lists bulk upload jobs.
- `POST /api/v1/upload-jobs`: Transactional CSV upload processing, immediately accepting valid records and logging validation issues for malformed rows.
- `GET /api/v1/validation/issues/{job_id}`: Lists staged validation issues for a job.
- `POST /api/v1/validation/resolve`: Inline error resolution queue to fix and commit staged errors row-by-row.

### Dashboard Metrics & Duplicate Collisions
- `GET /api/v1/dashboard/metrics`: AICTE National metrics (approved intake, actual enrolled, occupancy %, over-admissions, duplicate APAAR collisions).
- `GET /api/v1/dashboard/duplicates`: Scans central registry for multi-institution concurrent enrolment collisions.

### Verification Requests
- `POST /api/v1/verifications/verify`: Third-party QR / token verification with student consent verification, HMAC signature validation, and immutable audit logging.
- `GET /api/v1/verifications/history`: Audit trail of verification queries.

### Statutory Reports & PDF Generation
- `GET /api/v1/reports/intake-compliance-pdf/{institution_id}`: Official ReportLab PDF AICTE Intake Compliance Certificate.
- `GET /api/v1/reports/student-credential-pdf/{enrolment_id}`: Official ReportLab PDF Verifiable Digital Student Pass with embedded QR code.
- `GET /api/v1/reports/audit-events`: Immutable audit trail.
- `GET /api/v1/reports/export-students-csv`: Export confirmed student roster with masked APAARs.
