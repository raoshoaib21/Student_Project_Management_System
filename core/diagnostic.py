"""Temporary diagnostic view — REMOVE AFTER DIAGNOSIS."""
import json
import traceback

from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET

DIAG_KEY = "spms-diag"


def _table_exists(cursor, table):
    if settings.DATABASES["default"]["ENGINE"].endswith("sqlite3"):
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=%s", [table])
        return cursor.fetchone() is not None
    cursor.execute(
        "SELECT to_regclass(%s) IS NOT NULL", [table]
    )
    return cursor.fetchone()[0]


@require_GET
def diagnosys(request):
    if request.GET.get("key") != DIAG_KEY:
        return JsonResponse({"error": "bad key"}, status=403)
    out = {"ok": True, "db": settings.DATABASES["default"]["ENGINE"].split(".")[-1]}
    try:
        with connection.cursor() as cur:
            # applied migrations
            cur.execute("SELECT app, name FROM django_migrations ORDER BY app, name")
            out["migrations"] = [f"{a}.{n}" for a, n in cur.fetchall()]
            # key tables
            for t in ["projects_projectproposal", "axes_accessfailurelog", "django_axes_cache", "django_session"]:
                out[f"has_{t}"] = _table_exists(cur, t)
            # columns on projectproposal
            try:
                if settings.DATABASES["default"]["ENGINE"].endswith("sqlite3"):
                    cur.execute("PRAGMA table_info(projects_projectproposal)")
                    cols = [r[1] for r in cur.fetchall()]
                else:
                    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='projects_projectproposal'")
                    cols = [r[0] for r in cur.fetchall()]
                out["proposal_columns"] = cols
                out["has_proposal_document_col"] = "proposal_document" in cols
            except Exception:
                out["proposal_columns"] = traceback.format_exc().splitlines()[-1]
    except Exception:
        out["ok"] = False
        out["error"] = traceback.format_exc()
    return JsonResponse(out)