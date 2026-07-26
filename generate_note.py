"""
generate_note.py
----------------
Generates the submission written note as a PDF using ReportLab.
Run: py generate_note.py
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

OUTPUT = "submission_note.pdf"

doc = SimpleDocTemplate(
    OUTPUT,
    pagesize=A4,
    leftMargin=2.5 * cm,
    rightMargin=2.5 * cm,
    topMargin=2.5 * cm,
    bottomMargin=2.5 * cm,
)

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "Title",
    parent=styles["Heading1"],
    fontSize=18,
    textColor=colors.HexColor("#1a1a2e"),
    spaceAfter=6,
    alignment=TA_CENTER,
)

subtitle_style = ParagraphStyle(
    "Subtitle",
    parent=styles["Normal"],
    fontSize=11,
    textColor=colors.HexColor("#555555"),
    spaceAfter=12,
    alignment=TA_CENTER,
)

h2_style = ParagraphStyle(
    "H2",
    parent=styles["Heading2"],
    fontSize=13,
    textColor=colors.HexColor("#16213e"),
    spaceBefore=16,
    spaceAfter=6,
    borderPad=2,
)

body_style = ParagraphStyle(
    "Body",
    parent=styles["Normal"],
    fontSize=10.5,
    leading=16,
    spaceAfter=8,
    alignment=TA_JUSTIFY,
    textColor=colors.HexColor("#2d2d2d"),
)

bullet_style = ParagraphStyle(
    "Bullet",
    parent=styles["Normal"],
    fontSize=10.5,
    leading=15,
    leftIndent=18,
    spaceAfter=4,
    textColor=colors.HexColor("#2d2d2d"),
)

content = []

# ── Title ──────────────────────────────────────────────────────────────────────
content.append(Paragraph("ed-eval-service", title_style))
content.append(Paragraph("Technical Written Note — Bodhrik Full Stack Assessment", subtitle_style))
content.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f3460")))
content.append(Spacer(1, 0.4 * cm))
content.append(
    Paragraph(
        "<b>Candidate:</b> Sai Pavithra G &nbsp;&nbsp;|&nbsp;&nbsp; "
        "<b>GitHub:</b> github.com/Pavithra8805/ed-eval-service &nbsp;&nbsp;|&nbsp;&nbsp; "
        "<b>Stack:</b> FastAPI · PostgreSQL · Redis · Docker",
        subtitle_style,
    )
)
content.append(Spacer(1, 0.3 * cm))

# ── Section 1 ─────────────────────────────────────────────────────────────────
content.append(Paragraph("1. Schema Design &amp; Normalization Trade-offs", h2_style))
content.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
content.append(Spacer(1, 0.2 * cm))

content.append(
    Paragraph(
        "The schema follows <b>Third Normal Form (3NF)</b>, with four core tables: "
        "<i>users</i>, <i>students</i>, <i>sessions</i>, and <i>evaluations</i>.",
        body_style,
    )
)

content.append(
    Paragraph(
        "<b>users</b> is the single source of truth for identity and role. Roles are stored as a "
        "Postgres ENUM (<i>admin</i>, <i>teacher</i>, <i>parent</i>), enforced at the DB level — "
        "not just in application code — so invalid states are impossible.",
        body_style,
    )
)

content.append(
    Paragraph(
        "<b>students</b> is kept separate from users because a student is a platform entity (a "
        "child learner) but is <i>not</i> an authenticated actor. Merging students into the users "
        "table would violate single-responsibility and pollute the auth model. The student row "
        "holds a <i>parent_id</i> FK to users, which is the single join needed for parent RBAC checks.",
        body_style,
    )
)

content.append(
    Paragraph(
        "<b>sessions</b> records a tutoring interaction between one teacher and one student. "
        "<i>teacher_id</i> and <i>student_id</i> are direct FKs — no junction table — because "
        "the session is inherently 1:1 in this model. If the platform later needs group sessions, "
        "a <i>session_participants</i> junction table would be the natural extension.",
        body_style,
    )
)

content.append(
    Paragraph(
        "<b>evaluations</b> are intentionally separated from sessions. A single session can produce "
        "multiple evaluation runs (retry, re-grade), and each evaluation has its own lifecycle "
        "state (<i>pending → processing → completed/failed</i>). Embedding evaluation fields on "
        "the session row would preclude this and violate 2NF.",
        body_style,
    )
)

content.append(
    Paragraph(
        "<b>Key trade-off:</b> UUIDs are used as primary keys throughout. This adds ~16 bytes per "
        "row versus an integer sequence, but eliminates enumerable IDs in API URLs (a security "
        "property), and makes distributed ID generation safe without coordination.",
        body_style,
    )
)

# ── Section 2 ─────────────────────────────────────────────────────────────────
content.append(
    Paragraph("2. RBAC Evolution: Adding a Fourth Role or Nested Organisations", h2_style)
)
content.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
content.append(Spacer(1, 0.2 * cm))

content.append(
    Paragraph(
        "The current RBAC is <b>flat</b>: role logic lives in endpoint guards and query filters. "
        "This is easy to reason about with three roles, but does not scale. Here is how I would "
        "evolve it for a fourth role (e.g. <i>school_admin</i>) or nested organisations:",
        body_style,
    )
)

content.append(
    Paragraph(
        "• <b>Introduce an organisations table</b> with a self-referential <i>parent_org_id</i> "
        "column to model nested org trees (school → district → state). Each user, student, and "
        "session would gain an <i>org_id</i> FK.",
        bullet_style,
    )
)

content.append(
    Paragraph(
        "• <b>Move from role ENUM to a permissions table</b> (role → permission many-to-many). "
        "Rather than hard-coding <i>if role == 'teacher'</i> throughout the codebase, each "
        "endpoint declares which permission it requires (e.g. <i>sessions:read</i>, "
        "<i>evaluations:trigger</i>). The <i>require_roles</i> dependency becomes "
        "<i>require_permission</i>.",
        bullet_style,
    )
)

content.append(
    Paragraph(
        "• <b>Row-level security in PostgreSQL</b> via RLS policies would push org-scoped "
        "filtering into the database itself, so every query automatically sees only its org's "
        "data without application-level WHERE clauses.",
        bullet_style,
    )
)

content.append(
    Paragraph(
        "• <b>For the fourth role</b> (<i>school_admin</i>), add the ENUM value, create "
        "its permission set, and wire it in the dependency — no existing endpoint changes "
        "if permissions are the abstraction layer.",
        bullet_style,
    )
)

# ── Section 3 ─────────────────────────────────────────────────────────────────
content.append(Paragraph("3. What is Missing for Production Safety", h2_style))
content.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
content.append(Spacer(1, 0.2 * cm))

content.append(
    Paragraph(
        "The following gaps would need to be addressed before shipping this service in production:",
        body_style,
    )
)

content.append(
    Paragraph(
        "<b>Migrations strategy:</b> The lifespan handler calls <i>Base.metadata.create_all</i>, "
        "which is convenient for development but destructive in production (it silently skips "
        "columns added after initial creation). The Alembic config is already wired; the correct "
        "approach is to remove <i>create_all</i> from the app and run "
        "<i>alembic upgrade head</i> as a one-shot init container in the Kubernetes deployment "
        "or a CI/CD pipeline step before the rolling update.",
        bullet_style,
    )
)

content.append(
    Paragraph(
        "<b>Secrets handling:</b> <i>SECRET_KEY</i>, database passwords, and Redis credentials "
        "must come from a secrets manager (AWS Secrets Manager, HashiCorp Vault, or Kubernetes "
        "Secrets sealed with Sealed Secrets / External Secrets Operator). They must never appear "
        "in docker-compose.yml or environment files committed to Git.",
        bullet_style,
    )
)

content.append(
    Paragraph(
        "<b>Worker reliability:</b> The evaluation worker uses a Redis LIST as a queue. "
        "If the worker crashes mid-job, the message is lost. The production fix is to use "
        "BRPOPLPUSH (or Redis Streams with consumer groups) for at-least-once delivery, plus "
        "a dead-letter queue for jobs that exceed the retry budget.",
        bullet_style,
    )
)

content.append(
    Paragraph(
        "<b>JWT expiry &amp; refresh tokens:</b> The current auth issues a single access token "
        "with a configurable expiry. Production requires a short-lived access token (15 min) "
        "paired with a long-lived refresh token stored securely (HttpOnly cookie), with a "
        "token rotation endpoint and a blocklist (Redis SET) for revoked tokens.",
        bullet_style,
    )
)

content.append(
    Paragraph(
        "<b>Rate limiting, CORS hardening, and structured logging:</b> The current CORS policy "
        "allows all origins. A production deployment should whitelist only known origins, add "
        "a rate limiter (e.g. slowapi), and emit structured JSON logs (via structlog) to a "
        "centralised log aggregation system.",
        bullet_style,
    )
)

content.append(Spacer(1, 0.5 * cm))
content.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f3460")))
content.append(Spacer(1, 0.2 * cm))
content.append(
    Paragraph(
        "Word count: ~480 words &nbsp;|&nbsp; Repository: github.com/Pavithra8805/ed-eval-service",
        subtitle_style,
    )
)

doc.build(content)
print(f"PDF written to {OUTPUT}")
