"""
generate_note.py
----------------
Generates a polished submission PDF using ReportLab for the Bodhrik assessment.
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
    leftMargin=2.2 * cm,
    rightMargin=2.2 * cm,
    topMargin=2.2 * cm,
    bottomMargin=2.2 * cm,
)

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "Title",
    parent=styles["Heading1"],
    fontSize=20,
    leading=24,
    textColor=colors.HexColor("#1A2B4C"),
    spaceAfter=4,
    alignment=TA_CENTER,
)

subtitle_style = ParagraphStyle(
    "Subtitle",
    parent=styles["Normal"],
    fontSize=11,
    leading=15,
    textColor=colors.HexColor("#4A5568"),
    spaceAfter=10,
    alignment=TA_CENTER,
)

meta_style = ParagraphStyle(
    "Meta",
    parent=styles["Normal"],
    fontSize=10,
    leading=14,
    textColor=colors.HexColor("#2D3748"),
    alignment=TA_CENTER,
    spaceAfter=8,
)

h2_style = ParagraphStyle(
    "H2",
    parent=styles["Heading2"],
    fontSize=12.5,
    leading=16,
    textColor=colors.HexColor("#1A2B4C"),
    spaceBefore=12,
    spaceAfter=5,
)

body_style = ParagraphStyle(
    "Body",
    parent=styles["Normal"],
    fontSize=10,
    leading=14.5,
    spaceAfter=6,
    alignment=TA_JUSTIFY,
    textColor=colors.HexColor("#2D3748"),
)

bullet_style = ParagraphStyle(
    "Bullet",
    parent=styles["Normal"],
    fontSize=9.5,
    leading=14,
    leftIndent=14,
    spaceAfter=4,
    textColor=colors.HexColor("#2D3748"),
)

content = []

# ── Title & Metadata ─────────────────────────────────────────────────────────
content.append(Paragraph("<b>Education Evaluation Service</b>", title_style))
content.append(Paragraph("Technical Note — Bodhrik Full Stack Assessment", subtitle_style))
content.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2B6CB0")))
content.append(Spacer(1, 0.3 * cm))

github_link = '<a href="https://github.com/Pavithra8805/ed-eval-service" color="#2B6CB0"><u>https://github.com/Pavithra8805/ed-eval-service</u></a>'
content.append(
    Paragraph(
        f"<b>Candidate:</b> G Sai Pavithra &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"<b>GitHub Repository:</b> {github_link}<br/>"
        f"<b>Tech Stack:</b> FastAPI · PostgreSQL · Redis · Docker · Pytest",
        meta_style,
    )
)
content.append(Spacer(1, 0.2 * cm))

# ── Section 1 ─────────────────────────────────────────────────────────────────
content.append(Paragraph("1. Database Schema Design &amp; Normalization", h2_style))
content.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E0")))
content.append(Spacer(1, 0.15 * cm))

content.append(
    Paragraph(
        "The database follows <b>Third Normal Form (3NF)</b> to ensure data consistency and eliminate redundancy. "
        "The system consists of four primary entities: <b>users</b>, <b>students</b>, <b>sessions</b>, and <b>evaluations</b>.",
        body_style,
    )
)

content.append(
    Paragraph(
        "• <b>users Table:</b> Acts as the central identity system storing authentication credentials and account roles "
        "(<i>admin</i>, <i>teacher</i>, <i>parent</i>). Enforcing roles at the database level prevents invalid authorization states.",
        bullet_style,
    )
)

content.append(
    Paragraph(
        "• <b>students Table:</b> Modeled separately from users because students are learners, not login accounts. "
        "Each student references their parent's account via a <i>parent_id</i> foreign key, enabling clear ownership and parental access controls.",
        bullet_style,
    )
)

content.append(
    Paragraph(
        "• <b>sessions Table:</b> Represents 1:1 tutoring sessions between a teacher and a student. "
        "Direct foreign keys (<i>teacher_id</i>, <i>student_id</i>) eliminate unneeded complexity while making schedule queries fast.",
        bullet_style,
    )
)

content.append(
    Paragraph(
        "• <b>evaluations Table:</b> Kept distinct from sessions to allow multiple evaluation attempts per session (e.g. re-grading). "
        "Each evaluation tracks its own asynchronous lifecycle: <i>pending → processing → completed / failed</i>.",
        bullet_style,
    )
)

content.append(
    Paragraph(
        "• <b>UUID Primary Keys:</b> Using UUIDs instead of auto-incrementing integers prevents ID guessing in public API endpoints "
        "and allows reliable, distributed primary key generation across services.",
        bullet_style,
    )
)

# ── Section 2 ─────────────────────────────────────────────────────────────────
content.append(Paragraph("2. Scaling Role-Based Access Control (RBAC)", h2_style))
content.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E0")))
content.append(Spacer(1, 0.15 * cm))

content.append(
    Paragraph(
        "The current RBAC model implements role checks directly at the endpoint level. "
        "To scale this system for additional roles (e.g., <i>school_admin</i>) or multi-tenant organizational hierarchies, "
        "the architecture can evolve as follows:",
        body_style,
    )
)

content.append(
    Paragraph(
        "• <b>Organization Hierarchy:</b> Add an <i>organisations</i> table with parent-child relationships (e.g. School → District). "
        "Assigning an <i>org_id</i> foreign key to users, students, and sessions enables enterprise multi-tenancy.",
        bullet_style,
    )
)

content.append(
    Paragraph(
        "• <b>Granular Permissions System:</b> Decouple roles from endpoints by introducing a permission-based system "
        "(e.g. <i>session:read</i>, <i>evaluation:create</i>). Endpoints verify specific permissions rather than hardcoded roles.",
        bullet_style,
    )
)

content.append(
    Paragraph(
        "• <b>Database Row-Level Security (RLS):</b> Use PostgreSQL RLS policies to enforce organizational data boundaries "
        "directly inside the database engine for seamless security across all queries.",
        bullet_style,
    )
)

# ── Section 3 ─────────────────────────────────────────────────────────────────
content.append(Paragraph("3. Production Safety &amp; Engineering Readiness", h2_style))
content.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E0")))
content.append(Spacer(1, 0.15 * cm))

content.append(
    Paragraph(
        "To prepare this evaluation platform for high-traffic production environments, the following production enhancements are recommended:",
        body_style,
    )
)

content.append(
    Paragraph(
        "• <b>Automated Migration Workflows:</b> Run Alembic schema migrations (`alembic upgrade head`) via CI/CD release pipelines or Kubernetes init-containers, "
        "disabling automatic runtime table creation in production.",
        bullet_style,
    )
)

content.append(
    Paragraph(
        "• <b>Secure Secrets Management:</b> Load sensitive configurations (database URI, JWT secret key, Redis password) from environment secret managers "
        "(AWS Secrets Manager, HashiCorp Vault, or Kubernetes Secrets).",
        bullet_style,
    )
)

content.append(
    Paragraph(
        "• <b>Reliable Job Queuing:</b> Enhance the Redis evaluation worker with reliable queue patterns (e.g. Redis Streams or Celery with RabbitMQ) "
        "to support job retries, dead-letter queues, and at-least-once task delivery.",
        bullet_style,
    )
)

content.append(
    Paragraph(
        "• <b>Enhanced Security &amp; Observability:</b> Implement rate limiting, HTTP CORS domain restrictions, short-lived JWT access tokens with refresh tokens, "
        "and structured JSON logging for monitoring and alerting.",
        bullet_style,
    )
)

# Build PDF document
doc.build(content)
print(f"Clean, professional PDF successfully generated: {OUTPUT}")
