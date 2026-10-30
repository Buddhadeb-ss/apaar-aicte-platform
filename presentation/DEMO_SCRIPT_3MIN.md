# SIH26263 — Presenter Script & Accuracy Checklist
**Team: Sentinels · PS: SIH26263 · AICTE · Software / Smart Automation**

---

## Slide-by-Slide Presenter Script (~30–45 sec each)

---

### Slide 1 — Cover
> *"Good [morning/afternoon]. We are Team Sentinels, and our problem statement is SIH26263 from AICTE.*
>
> *India has thousands of AICTE-approved institutions submitting student enrolment data — but there is no unified, automated way to validate it, detect duplicates, or let an employer confirm a credential. Our platform changes that.*
>
> *The thesis in one line: Trust every record. Verify every enrolment."*

---

### Slide 2 — The Problem
> *"Four interconnected failures define the current state.*
>
> *First: a student can hold active enrolments at multiple institutions simultaneously — there is no cross-institution check. Second: institutions submit data in inconsistent formats with no field-level enforcement. Third: institutions can exceed approved intake limits with no regulatory alert. And fourth: there is no authorised, privacy-respecting channel for employers or admission teams to verify a credential.*
>
> *These are not hypothetical gaps — they are direct consequences of the problem statement's mandate."*

---

### Slide 3 — Our Solution
> *"Our answer is a validation-first pipeline with six stages.*
>
> *An institution uploads CSV data or enters it manually. Before a single record is committed to the database, our server-side engine runs 14 deterministic statutory rules. Flagged rows are surfaced for review. Clean records enter a central registry keyed to a stable UUID per student — separate from enrolment. AICTE administrators get real-time analytics on intake, duplicates and compliance. And authorised verifiers — an employer, a college — can query a signed credential pass through a role-gated endpoint.*
>
> *The bottom row shows three live screens from the running application."*

---

### Slide 4 — Differentiators
> *"The core design choice that separates us is validation before commit — not collection first, fix later.*
>
> *Four dimensions: We separate student identity from enrolment records, which means the same student's history across multiple programmes is traceable. We run normalised exact-match duplicate detection before writing to the database — not as a batch cleanup job. We count active enrolments by institution, programme and year, with supernumerary seats tracked separately. And every endpoint enforces one of five role permissions — there is no flat access model."*

---

### Slide 5 — Technical Architecture
> *"Three tiers. Client tier: React 18 with TypeScript, a role-adaptive UI that renders the AICTE command centre, institution portal, student credential pass and validation workbench based on the authenticated role.*
>
> *Application tier: FastAPI with JWT authentication and bcrypt hashing. The validation engine executes 14 deterministic rules — this is not ML, not AI — and the credential signing service generates signed QR-linked passes. Every write action produces an immutable audit event with no PII in the log fields.*
>
> *Data tier: SQLAlchemy ORM over SQLite for this prototype. SQLite is explicitly not production infrastructure. The dotted box on the right represents planned integrations — APAAR registry, DigiLocker, NAD — which are not active and require AICTE authorisation."*

---

### Slide 6 — Automated Validation Engine
> *"The validation engine is the critical differentiator. Six-step pipeline: upload, parse, validate, categorise, review, then commit or reject.*
>
> *The table shows synthetic demonstration data — not sourced from any official registry. Row one passes all 14 rules. Row two: APAAR ID does not match the configured format pattern — Critical. Row three: APAAR ID already linked to another student in this institution — Critical, duplicate. Row four: programme code is missing — a required field — Critical. Row five: accepting this row would take CS enrolment to 122 against an approved intake of 120 — flagged High.*
>
> *Every issue code is structured: rule number, severity, field name, human-readable explanation, suggested remediation. Nothing is silently modified."*

---

### Slide 7 — Live Product
> *"All four panels are real application screenshots running on this machine.*
>
> *Top left: the AICTE national command centre — KPI cards for total institutions, student identities distinguished from active enrolments, intake utilisation, and cross-institution collision alerts. Top right: the institution intake dashboard for Apex Institute — programme-level gauges. Bottom left: the 14-rule validation workbench with issue codes, severity and an exportable error report. Bottom right: the student verifiable credential pass — APAAR ID is masked by default, full value visible only to authorised roles, and the signed QR links to a live verification endpoint.*
>
> *Demo credentials are shown in the footer. We are happy to demonstrate live."*

---

### Slide 8 — Security & Impact
> *"Security is not a layer we added at the end — it is in the data model.*
>
> *Role-based access is enforced at every API endpoint. All queries are scoped to the institution's tenant — cross-institution access requires the AICTE admin role. APAAR IDs are masked in the UI to operators and shown only to authorised roles. Signed QR credential passes link to a verification endpoint. And every write action produces an audit event — no PII in log fields.*
>
> *The right column shows system measurements from our synthetic demo environment. These are not claimed production metrics: 21 validation issues detected — 17 critical, 2 high, 2 medium. One cross-institution collision candidate — Vikram Malhotra holding concurrent seats at two colleges. 44 of 44 pytest tests passing. 100% data completeness for the synthetic demo dataset.*
>
> *The banner at the bottom is a hard constraint we set on ourselves: local format check is not registry validation, and it is not identity verification."*

---

### Slide 9 — Closing
> *"Four next steps. Pilot with two or three AICTE institutions on a controlled dataset. Policy validation — aligning our 14 rules with actual AICTE statutory regulations. Official APAAR and DigiLocker integration, subject to authorisation. And finally, scale to production with a proper database and national rollout.*
>
> *The mission is three words: Validate — every record before it enters the system. Monitor — intake, duplicates and compliance in real time. Verify — credentials through an authorised, role-gated channel.*
>
> *We are Team Sentinels. Thank you."*

---

## Accuracy Checklist

| Claim | Slide | Status |
|---|---|---|
| 3 demo institutions (Apex, Beacon, Zenith) | 8, 9 | ✅ Verified from live API |
| 600 total approved intake seats | 8 | ✅ Verified from live API |
| 16 unique student identities | 8 | ✅ Verified from live API |
| 17 active enrolment records | 8 | ✅ Verified from live API |
| 1 cross-institution collision (Vikram Malhotra) | 8 | ✅ Verified from live API |
| 21 pending validation issues (CRITICAL: 17, HIGH: 2, MEDIUM: 2) | 8 | ✅ Verified from live API |
| 44/44 pytest tests passing | 8 | ✅ Verified — run `pytest` in backend |
| 14 deterministic rules (NOT ML/AI) | 5, 6, 8 | ✅ Verified from validation engine code |
| 5 user roles (AICTE Admin, Inst Admin, Operator, Student Viewer, Verifier) | 4, 5, 8 | ✅ Verified from RBAC implementation |
| APAAR ID masked in UI | 7, 8 | ✅ Verified from frontend code |
| Signed QR credential pass | 7, 8 | ✅ Verified — signed metadata in DB |
| Audit event log (no PII) | 5, 8 | ✅ Verified from audit service code |
| Bcrypt hashing + JWT tokens | 5, 8 | ✅ Verified from auth implementation |
| SQLite = prototype only | 5, 9 | ✅ Stated clearly on every relevant slide |
| APAAR registry integration = PLANNED, not active | 5, 8, 9 | ✅ Stated in dashed future box |
| DigiLocker / NAD integration = PLANNED | 5, 9 | ✅ Stated in dashed future box |
| Data completeness = 100% | 8 | ⚠️ Demonstration measurement — synthetic demo data only |
| Intake utilisation = 2.83% | (not on slides) | ⚠️ Excluded — too low to be meaningful to evaluators |
| All screenshots from live app | 7 | ✅ Captured via Playwright from running localhost |
| Synthetic validation table data | 6 | ✅ Labelled "SYNTHETIC DEMONSTRATION DATA" |
| No ML/AI claims anywhere | All | ✅ Explicitly stated on Slides 5, 6 |
| No official APAAR registry integration claimed | All | ✅ Explicitly stated on Slides 5, 8, 9 |
| No performance benchmarks claimed | All | ✅ Response time omitted — not measured |
| No fabricated certifications or partnerships | All | ✅ None mentioned |

> [!IMPORTANT]
> **Before presenting:** Run `pytest` in the backend directory to confirm 44/44 still pass. Confirm the app is running at `http://127.0.0.1:5173`. Have the AICTE admin login (`admin@aicte.gov.in` / `Aicte@2026`) ready to demonstrate live.

> [!CAUTION]
> Do NOT claim the QR code proves government identity — it proves enrolment record integrity only. This distinction is on Slide 8 and must be restated if questioned.
