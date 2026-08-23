# Student Project Management System — Project Log

Living log of what has been built. Update as features land.

---

## Stack

- **App:** Django 5.2 web app for managing final-year projects: supervisor assigns projects, shares
  resources, reviews progress, grades and approves/declines the final work.
- **Stack:** Django 5.2 (LTS), Python 3.14, Bootstrap 5.3 (CDN), SQLite (dev) → PostgreSQL (prod),
  Whitenoise, django-axes, django-crispy-forms.
- **Deploy:** Render free tier — https://student-project-management-system-0ogg.onrender.com
  (blueprint `render.yaml`, build `build.sh`, health `/health/`).

## Demo Accounts (re-seeded on every deploy)

| Username | Password | Access |
|---|---|---|
| `admin` | `Admin2026!` | Django admin + supervisor role |
| `demo_supervisor` | `Supervisor2026!` | Supervisor dashboard |
| `demo_student1..3` | `Student2026!` | Student dashboard |

## Architecture

```
config/        settings package (base/dev/prod), urls, wsgi/asgi
accounts/      User model (roles STUDENT/SUPERVISOR), profiles, auth, role permissions
core/          Notification, ActivityLog, ContactMessage; landing/about/contact/dashboard
projects/      Project (+approval & grading workflow), ProjectMember, Task
documents/     Document with category (supervisor materials vs student final submission)
progress/      ProgressReport + Feedback (submit → review flow)
templates/     project-level templates by app; partials (sidebar drawer, topbar, footer)
static/        css/js/images (design system in styles.css :root tokens)
```

## Milestones

### Phase 1 — Foundation
- Settings split (base/dev/prod), custom `User` with roles, profiles, auth flows.
- Login with remember-me, password reset/change, django-axes lockout (5 fails → 5 min).
- Global `LoginRequiredMiddleware` with public allowlist; landing/about/contact pages.
- Notification + ActivityLog infrastructure; seed_demo management command.

### Phase 2 — Core features
- Projects, members, tasks (priority/status workflow).
- Documents with type/size validation and download endpoint.
- Weekly progress reports with submit → review → approve/needs-revision flow and feedback.

### Phase 3 — Polish
- UI redesign v3: slate+indigo design system (Sora / DM Sans / JetBrains Mono).
- Off-canvas drawer sidebar (hamburger toggle, backdrop, Escape key); brand logos wired.
- Public registration removed entirely — accounts are created by the administrator only
  (`/accounts/register/` returns 404). Email verification flow removed with it.

### Phase 4 — Supervision workflow (current)
- Project approval lifecycle on `Project`: `approval_status` (PENDING/APPROVED/DECLINED),
  `decision_note/by/at`; supervisor-only Approve/Decline buttons on the project page.
- Final grading on `Project`: `grade`, `grade_comment`, `graded_by/at`; grade form for the
  supervisor, read-only result card for students.
- Document categories: RESOURCE / APPENDIX / GUIDELINE / SUPPORTING uploaded by the supervisor;
  FINAL_SUBMISSION uploaded by students (one per student per project, enforced by constraint).
- Project creation restricted to supervisors (projects are assigned, not self-created).

## Known Limitations

- Media uploads live on Render's ephemeral disk — wire object storage (e.g. Cloudinary) before
  relying on uploads in production.
- Free web service sleeps after ~15 min idle; first request after waking is slow.

## Commands

```powershell
env\Scripts\python.exe manage.py runserver   # dev server
env\Scripts\python.exe manage.py test       # test suite
env\Scripts\python.exe manage.py seed_demo  # idempotent demo data
env\Scripts\python.exe manage.py makemigrations && env\Scripts\python.exe manage.py migrate
```
