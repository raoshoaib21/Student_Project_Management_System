# AGENTS.md

## Project Overview
- **Student Project Management System** — Django 5.2 LTS web app
- Project path: `D:\Webapps\Student_Project_Management_System`
- Virtual env: `env\` (use `env\Scripts\python.exe`)

## Running Commands (PowerShell)
```powershell
# Run server
env\Scripts\python.exe manage.py runserver

# Tests
env\Scripts\python.exe manage.py test

# Migrations
env\Scripts\python.exe manage.py makemigrations
env\Scripts\python.exe manage.py migrate

# Seed demo data (supervisor, students, project, tasks)
env\Scripts\python.exe manage.py seed_demo

# Admin user
env\Scripts\python.exe manage.py createsuperuser
```

## Deployment (Render — free tier)
- Blueprint: `render.yaml` (web service `student-pms` + free Postgres `student-pms-db`).
- `build.sh` (Linux only): pip install → migrate → createcachetable → collectstatic. Do NOT run on Windows.
- Start command: `gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 2 --timeout 120`.
- Env injected by Render: `DJANGO_SETTINGS_MODULE=config.settings.prod`, `DATABASE_URL`, `SECRET_KEY`, `DEBUG=false`, `ALLOWED_HOSTS=student-pms.onrender.com`.
- Add SMTP keys (`EMAIL_HOST*`, `DEFAULT_FROM_EMAIL`) for live verification/reset emails.
- Free web service sleeps after ~15 min idle; wakes on first request (slow first load).
- Media uploads use local disk (ephemeral on Render — wiped on redeploy). Wire Cloudinary/object storage before relying on uploads in prod.
- To deploy: push repo to GitHub, then connect it at https://dashboard.render.com/blueprints. Create superuser via the Render Shell after first deploy.

## Structure
- **config**: project settings split as a package — `settings/base.py`, `dev.py`, `prod.py` (`config.settings.dev` is the default; prod uses `config.settings.prod`)
- **accounts**: custom `User` (roles STUDENT/SUPERVISOR, email verification), profiles, auth views, `permissions.py` (role decorators/mixins), `tokens.py`
- **core**: `Notification`, `ActivityLog`, `log_activity()`, landing/dashboard views, `LoginRequiredMiddleware`, context processor, `core/permissions` object-level mixins live in each app's `permissions.py`
- **projects**: `Project`, `ProjectMember`, `Task` + `permissions.py` (scoping + access mixins)
- **documents**: `Document` (file validation in models/views)
- **progress**: `ProgressReport`, `Feedback` + `permissions.py`
- **templates**: project-level (base.html + partials, accounts, core, registration)
- **static/css/styles.css**, **media/** (user uploads)

## Conventions
- Class-based generic views + `django-crispy-forms` (bootstrap5) for forms
- All views guarded: global `core.middleware.LoginRequiredMiddleware` + public allowlist (`LOGIN_REQUIRED_IGNORE_PATHS`/`_VIEW_NAMES` in base settings)
- Role checks via `RoleRequiredMixin`/`@role_required`; object access via mixins in `projects/permissions.py` etc.; queryset scoping via `scoped_projects()`
- Notifications + audit via `core.models.log_activity()`; auth events logged on login/logout/verification/password change
- `.env` holds secrets (`.env.example` committed); `db.sqlite3` and `media/` are gitignored
- Database: SQLite in dev; production switches via `DATABASE_URL` (PostgreSQL) in `config/settings/prod.py`
- Do NOT commit to git unless the user explicitly asks
