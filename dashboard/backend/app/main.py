from fastapi import FastAPI, Depends, HTTPException, Query, Request, Response, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import Optional
import os, re, logging
from dotenv import load_dotenv
from datetime import datetime, date, timedelta, timezone, time

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("dashboard")

app = FastAPI(title="SbioChat Dashboard API")
v1 = APIRouter(prefix="/api/v1")

KST = timezone(timedelta(hours=9))

# CORS Configuration
origins = [
    "https://openwebui.sbiologics.com",
    "https://openwebui.sbiologics.com:30088",
    "http://localhost:3005",
    "http://127.0.0.1:3005",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Auth-User", "Authorization"],
)

# Database Setup
DB_USER = os.getenv("POSTGRES_USER", "webui_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_HOST = os.getenv("POSTGRES_HOST", "webui-db")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "webui")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

AUTH_MODE = os.getenv("AUTH_MODE", "mock")
ADMIN_USERS = [u.strip() for u in os.getenv("ADMIN_USERS", "jisung.jang").split(",") if u.strip()]

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(request: Request) -> str:
    if AUTH_MODE == "mock":
        user = request.headers.get("X-Auth-User", "").strip()
        if not user:
            raise HTTPException(status_code=401, detail="X-Auth-User header required in mock mode")
        if "@" in user:
            parts = user.split("@")
            if parts[1] != "samsung.com":
                raise HTTPException(status_code=403, detail="Only @samsung.com emails are allowed")
            return parts[0]
        return user
    else:
        # SSO mode: Keycloak OIDC token validation (to be implemented)
        raise HTTPException(status_code=501, detail="SSO auth not yet implemented")


class PackageCreate(BaseModel):
    package_name: str

class PackageStatusUpdate(BaseModel):
    status: str
    status_note: Optional[str] = None

class ReportCreate(BaseModel):
    title: str
    description: str
    category: str = "bug"
    is_anonymous: bool = False

class ReportStatusUpdate(BaseModel):
    status: str
    admin_note: Optional[str] = None


@app.on_event("startup")
def create_tables():
    """Create application tables if they don't exist."""
    logger.info("Starting dashboard API, AUTH_MODE=%s, ADMIN_USERS=%s", AUTH_MODE, ADMIN_USERS)
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS python_packages (
                id SERIAL PRIMARY KEY,
                package_name VARCHAR(255) NOT NULL UNIQUE,
                added_by VARCHAR(255) NOT NULL,
                added_at TIMESTAMPTZ DEFAULT NOW(),
                status VARCHAR(20) DEFAULT 'pending',
                status_note TEXT,
                status_updated_by VARCHAR(255),
                status_updated_at TIMESTAMPTZ
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS package_audit_log (
                id SERIAL PRIMARY KEY,
                package_id INTEGER,
                package_name VARCHAR(255) NOT NULL,
                action VARCHAR(50) NOT NULL,
                performed_by VARCHAR(255) NOT NULL,
                detail TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS issue_reports (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                category VARCHAR(50) DEFAULT 'bug',
                reported_by VARCHAR(255),
                is_anonymous BOOLEAN DEFAULT false,
                status VARCHAR(20) DEFAULT 'open',
                admin_note TEXT,
                status_updated_by VARCHAR(255),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        conn.commit()


def log_audit(db: Session, package_id: int, package_name: str, action: str, user: str, detail: str = None):
    """Insert a record into the package audit log."""
    db.execute(
        text("""INSERT INTO package_audit_log (package_id, package_name, action, performed_by, detail)
                VALUES (:pid, :pname, :action, :user, :detail)"""),
        {"pid": package_id, "pname": package_name, "action": action, "user": user, "detail": detail},
    )


# ─── Root & Health ────────────────────────────────────────────────────

@app.get("/")
def read_root():
    return {"message": "Welcome to Open WebUI Dashboard API"}


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        logger.exception("Health check failed")
        raise HTTPException(status_code=500, detail="Database connection failed")


# ─── Statistics ───────────────────────────────────────────────────────

@v1.get("/stats/overview")
def get_overview(response: Response, db: Session = Depends(get_db)):
    """Return aggregate stats across all chats, models, and feedback."""
    response.headers["Cache-Control"] = "public, max-age=60"
    result = db.execute(text("""
        WITH
            chat_stats AS (
                SELECT count(*) as total_chats,
                       sum(json_array_length(chat->'messages')) as total_messages
                FROM chat
            ),
            model_stats AS (
                SELECT count(DISTINCT m.value) as total_models
                FROM chat, json_array_elements_text(chat->'models') AS m(value)
            ),
            feedback_stats AS (
                SELECT count(*) as total_feedbacks FROM feedback
            ),
            tool_stats AS (
                SELECT count(*) as total_tools FROM tool
            ),
            function_stats AS (
                SELECT count(*) as total_functions FROM function
            ),
            skill_stats AS (
                SELECT count(*) as total_skills FROM skill
            )
        SELECT cs.total_chats, cs.total_messages, ms.total_models, fs.total_feedbacks,
               ts.total_tools, fns.total_functions, ss.total_skills
        FROM chat_stats cs, model_stats ms, feedback_stats fs, tool_stats ts, function_stats fns, skill_stats ss
    """)).mappings().first()
    return {
        "total_chats": result["total_chats"],
        "total_messages": result["total_messages"] or 0,
        "total_models": result["total_models"],
        "total_feedbacks": result["total_feedbacks"],
        "total_tools": result["total_tools"],
        "total_functions": result["total_functions"],
        "total_skills": result["total_skills"],
    }


@v1.get("/stats/daily")
def get_daily_stats(
    response: Response,
    date_from: date = Query(alias="from", default=None),
    date_to: date = Query(alias="to", default=None),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "public, max-age=60"
    # Default: last 30 days in KST
    if date_to is None:
        date_to = datetime.now(KST).date()
    if date_from is None:
        date_from = date_to - timedelta(days=29)

    # Convert KST date range to UTC epoch range
    from_utc = datetime.combine(date_from, time.min, tzinfo=KST).timestamp()
    to_utc = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=KST).timestamp()

    rows = db.execute(text("""
        SELECT
            (to_timestamp(created_at) AT TIME ZONE 'Asia/Seoul')::date as date,
            count(*) as chat_count,
            sum(json_array_length(chat->'messages')) as message_count,
            count(DISTINCT user_id) as user_count
        FROM chat
        WHERE created_at >= :from_ts AND created_at < :to_ts
        GROUP BY date
        ORDER BY date
    """), {"from_ts": from_utc, "to_ts": to_utc}).mappings().all()

    # Fill missing dates with zeros
    data_by_date = {str(row["date"]): row for row in rows}
    result = []
    current = date_from
    while current <= date_to:
        key = str(current)
        if key in data_by_date:
            row = data_by_date[key]
            result.append({
                "date": key,
                "chat_count": row["chat_count"],
                "message_count": row["message_count"] or 0,
                "user_count": row["user_count"],
            })
        else:
            result.append({
                "date": key,
                "chat_count": 0,
                "message_count": 0,
                "user_count": 0,
            })
        current += timedelta(days=1)

    return result


@v1.get("/stats/workspace-ranking")
def get_workspace_ranking(
    response: Response,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "public, max-age=60"
    rows = db.execute(text("""
        WITH workspace_chats AS (
            SELECT
                m.value as workspace,
                count(*) as chat_count,
                sum(json_array_length(c.chat->'messages')) as message_count,
                count(DISTINCT c.user_id) as user_count
            FROM chat c, json_array_elements_text(c.chat->'models') AS m(value)
            GROUP BY m.value
        ),
        workspace_feedback AS (
            SELECT
                f.data->>'model_id' as workspace,
                count(*) FILTER (WHERE (f.data->>'rating')::int > 0) as positive,
                count(*) FILTER (WHERE (f.data->>'rating')::int < 0) as negative
            FROM feedback f
            GROUP BY f.data->>'model_id'
        ),
        workspace_info AS (
            SELECT m.id, m.name, u.email as developer_email
            FROM model m
            LEFT JOIN "user" u ON m.user_id = u.id
        )
        SELECT
            wc.workspace as id,
            coalesce(wi.name, wc.workspace) as name,
            wi.developer_email,
            wc.chat_count,
            wc.message_count,
            wc.user_count,
            coalesce(wf.positive, 0) as positive,
            coalesce(wf.negative, 0) as negative,
            count(*) OVER() as _total
        FROM workspace_chats wc
        JOIN workspace_info wi ON wc.workspace = wi.id
        LEFT JOIN workspace_feedback wf ON wc.workspace = wf.workspace
        ORDER BY wc.chat_count DESC
        LIMIT :limit OFFSET :offset
    """), {"limit": limit, "offset": offset}).mappings().all()

    total = rows[0]["_total"] if rows else 0
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "id": row["id"],
                "name": row["name"],
                "developer_email": row["developer_email"] or "",
                "user_count": row["user_count"],
                "chat_count": row["chat_count"],
                "message_count": row["message_count"] or 0,
                "positive": row["positive"],
                "negative": row["negative"],
            }
            for row in rows
        ],
    }


@v1.get("/stats/developer-ranking")
def get_developer_ranking(
    response: Response,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "public, max-age=60"
    rows = db.execute(text("""
        WITH developer_workspaces AS (
            SELECT m.user_id, m.id as workspace_id
            FROM model m
        ),
        workspace_metrics AS (
            SELECT
                mv.value as workspace,
                count(*) as chat_count,
                sum(json_array_length(c.chat->'messages')) as message_count,
                count(DISTINCT c.user_id) as user_count
            FROM chat c, json_array_elements_text(c.chat->'models') AS mv(value)
            GROUP BY mv.value
        ),
        workspace_fb AS (
            SELECT
                f.data->>'model_id' as workspace,
                count(*) FILTER (WHERE (f.data->>'rating')::int > 0) as positive,
                count(*) FILTER (WHERE (f.data->>'rating')::int < 0) as negative
            FROM feedback f
            GROUP BY f.data->>'model_id'
        )
        SELECT
            u.id as user_id,
            u.name as user_name,
            u.email,
            count(DISTINCT dw.workspace_id) as workspace_count,
            coalesce(sum(wm.user_count), 0) as total_users,
            coalesce(sum(wm.chat_count), 0) as total_chats,
            coalesce(sum(wm.message_count), 0) as total_messages,
            coalesce(sum(wfb.positive), 0) as total_positive,
            coalesce(sum(wfb.negative), 0) as total_negative,
            count(*) OVER() as _total
        FROM developer_workspaces dw
        JOIN "user" u ON dw.user_id = u.id
        LEFT JOIN workspace_metrics wm ON dw.workspace_id = wm.workspace
        LEFT JOIN workspace_fb wfb ON dw.workspace_id = wfb.workspace
        GROUP BY u.id, u.name, u.email
        ORDER BY total_chats DESC
        LIMIT :limit OFFSET :offset
    """), {"limit": limit, "offset": offset}).mappings().all()

    total = rows[0]["_total"] if rows else 0
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "user_id": row["user_id"],
                "user_name": row["user_name"],
                "email": row["email"],
                "workspace_count": row["workspace_count"],
                "total_users": int(row["total_users"]),
                "total_chats": int(row["total_chats"]),
                "total_messages": int(row["total_messages"]),
                "total_positive": int(row["total_positive"]),
                "total_negative": int(row["total_negative"]),
            }
            for row in rows
        ],
    }


@v1.get("/stats/user-ranking")
def get_user_ranking(
    response: Response,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Rank individual users by their personal chat activity."""
    response.headers["Cache-Control"] = "public, max-age=60"
    rows = db.execute(text("""
        WITH user_chats AS (
            SELECT
                c.user_id,
                count(*) as chat_count,
                sum(json_array_length(c.chat->'messages')) as message_count,
                count(DISTINCT m.value) as workspace_count
            FROM chat c, json_array_elements_text(c.chat->'models') AS m(value)
            GROUP BY c.user_id
        ),
        user_fb AS (
            SELECT
                f.user_id,
                count(*) as total_feedbacks
            FROM feedback f
            GROUP BY f.user_id
        )
        SELECT
            u.id as user_id,
            u.name as user_name,
            u.email,
            coalesce(uc.chat_count, 0) as chat_count,
            coalesce(uc.message_count, 0) as message_count,
            coalesce(uc.workspace_count, 0) as workspace_count,
            coalesce(ufb.total_feedbacks, 0) as total_feedbacks,
            count(*) OVER() as _total
        FROM "user" u
        LEFT JOIN user_chats uc ON u.id = uc.user_id
        LEFT JOIN user_fb ufb ON u.id = ufb.user_id
        WHERE coalesce(uc.chat_count, 0) > 0
        ORDER BY chat_count DESC
        LIMIT :limit OFFSET :offset
    """), {"limit": limit, "offset": offset}).mappings().all()

    total = rows[0]["_total"] if rows else 0
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "user_id": row["user_id"],
                "user_name": row["user_name"],
                "email": row["email"],
                "chat_count": int(row["chat_count"]),
                "message_count": int(row["message_count"]),
                "workspace_count": int(row["workspace_count"]),
                "total_feedbacks": int(row["total_feedbacks"]),
            }
            for row in rows
        ],
    }


@v1.get("/stats/group-ranking")
def get_group_ranking(
    response: Response,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "public, max-age=60"
    rows = db.execute(text("""
        WITH group_members AS (
            SELECT
                g.id as group_id,
                g.name as group_name,
                gm.user_id,
                count(*) OVER (PARTITION BY g.id) as member_count
            FROM "group" g
            JOIN group_member gm ON g.id = gm.group_id
        ),
        workspace_ids AS (
            SELECT id FROM model
        ),
        user_usage AS (
            SELECT
                c.user_id,
                m.value as workspace,
                count(*) as chat_count,
                sum(json_array_length(c.chat->'messages')) as message_count
            FROM chat c, json_array_elements_text(c.chat->'models') AS m(value)
            GROUP BY c.user_id, m.value
        ),
        user_fb AS (
            SELECT
                f.user_id,
                count(*) as total_feedbacks
            FROM feedback f
            WHERE f.data->>'model_id' IN (SELECT id FROM workspace_ids)
            GROUP BY f.user_id
        )
        SELECT
            gm.group_id,
            gm.group_name,
            gm.member_count,
            coalesce(sum(uu.chat_count), 0) as total_chats,
            coalesce(sum(uu.message_count), 0) as total_messages,
            coalesce(sum(ufb.total_feedbacks), 0) as total_feedbacks,
            round(coalesce(sum(uu.chat_count), 0)::numeric
                / NULLIF(gm.member_count, 0), 1) as chats_per_member,
            round(coalesce(sum(uu.message_count), 0)::numeric
                / NULLIF(gm.member_count, 0), 1) as messages_per_member,
            count(*) OVER() as _total
        FROM group_members gm
        LEFT JOIN user_usage uu ON gm.user_id = uu.user_id
        LEFT JOIN user_fb ufb ON gm.user_id = ufb.user_id
        GROUP BY gm.group_id, gm.group_name, gm.member_count
        ORDER BY chats_per_member DESC NULLS LAST
        LIMIT :limit OFFSET :offset
    """), {"limit": limit, "offset": offset}).mappings().all()

    total = rows[0]["_total"] if rows else 0
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "group_id": row["group_id"],
                "group_name": row["group_name"],
                "member_count": row["member_count"],
                "total_chats": int(row["total_chats"]),
                "total_messages": int(row["total_messages"]),
                "total_feedbacks": int(row["total_feedbacks"]),
                "chats_per_member": float(row["chats_per_member"] or 0),
                "messages_per_member": float(row["messages_per_member"] or 0),
            }
            for row in rows
        ],
    }


# ─── Tool & Function Registry ─────────────────────────────────────────

@v1.get("/stats/tool-ranking")
def get_tool_ranking(
    response: Response,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List registered tools with creator info."""
    response.headers["Cache-Control"] = "public, max-age=60"
    rows = db.execute(text("""
        SELECT
            t.id,
            t.name,
            u.name as creator_name,
            u.email as creator_email,
            to_timestamp(t.created_at) AT TIME ZONE 'Asia/Seoul' as created_at,
            to_timestamp(t.updated_at) AT TIME ZONE 'Asia/Seoul' as updated_at,
            count(*) OVER() as _total
        FROM tool t
        LEFT JOIN "user" u ON t.user_id = u.id
        ORDER BY t.updated_at DESC
        LIMIT :limit OFFSET :offset
    """), {"limit": limit, "offset": offset}).mappings().all()

    total = rows[0]["_total"] if rows else 0
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "id": row["id"],
                "name": row["name"],
                "creator_name": row["creator_name"] or "",
                "creator_email": row["creator_email"] or "",
                "created_at": str(row["created_at"]),
                "updated_at": str(row["updated_at"]),
            }
            for row in rows
        ],
    }


@v1.get("/stats/function-ranking")
def get_function_ranking(
    response: Response,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List registered functions (pipes, filters, actions) with creator info."""
    response.headers["Cache-Control"] = "public, max-age=60"
    rows = db.execute(text("""
        SELECT
            f.id,
            f.name,
            f.type,
            f.is_active,
            f.is_global,
            u.name as creator_name,
            u.email as creator_email,
            to_timestamp(f.created_at) AT TIME ZONE 'Asia/Seoul' as created_at,
            to_timestamp(f.updated_at) AT TIME ZONE 'Asia/Seoul' as updated_at,
            count(*) OVER() as _total
        FROM function f
        LEFT JOIN "user" u ON f.user_id = u.id
        ORDER BY f.updated_at DESC
        LIMIT :limit OFFSET :offset
    """), {"limit": limit, "offset": offset}).mappings().all()

    total = rows[0]["_total"] if rows else 0
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "id": row["id"],
                "name": row["name"],
                "type": row["type"],
                "is_active": row["is_active"],
                "is_global": row["is_global"],
                "creator_name": row["creator_name"] or "",
                "creator_email": row["creator_email"] or "",
                "created_at": str(row["created_at"]),
                "updated_at": str(row["updated_at"]),
            }
            for row in rows
        ],
    }


@v1.get("/stats/skill-ranking")
def get_skill_ranking(
    response: Response,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List registered skills with creator info."""
    response.headers["Cache-Control"] = "public, max-age=60"
    rows = db.execute(text("""
        SELECT
            s.id,
            s.name,
            s.description,
            s.is_active,
            u.name as creator_name,
            u.email as creator_email,
            to_timestamp(s.created_at) AT TIME ZONE 'Asia/Seoul' as created_at,
            to_timestamp(s.updated_at) AT TIME ZONE 'Asia/Seoul' as updated_at,
            count(*) OVER() as _total
        FROM skill s
        LEFT JOIN "user" u ON s.user_id = u.id
        ORDER BY s.updated_at DESC
        LIMIT :limit OFFSET :offset
    """), {"limit": limit, "offset": offset}).mappings().all()

    total = rows[0]["_total"] if rows else 0
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "id": row["id"],
                "name": row["name"],
                "description": (row["description"] or "")[:120],
                "is_active": row["is_active"],
                "creator_name": row["creator_name"] or "",
                "creator_email": row["creator_email"] or "",
                "created_at": str(row["created_at"]),
                "updated_at": str(row["updated_at"]),
            }
            for row in rows
        ],
    }


# ─── Auth ──────────────────────────────────────────────────────────────

@v1.get("/auth/me")
def get_me(current_user: str = Depends(get_current_user)):
    return {"user": current_user, "is_admin": current_user in ADMIN_USERS}


# ─── Python Packages ──────────────────────────────────────────────────

@v1.get("/packages")
def list_packages(
    response: Response,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-cache"
    rows = db.execute(text("""
        SELECT id, package_name, added_by,
               added_at AT TIME ZONE 'Asia/Seoul' as added_at,
               status, status_note,
               count(*) OVER() as _total
        FROM python_packages
        ORDER BY added_at DESC
        LIMIT :limit OFFSET :offset
    """), {"limit": limit, "offset": offset}).mappings().all()
    total = rows[0]["_total"] if rows else 0
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "id": row["id"],
                "package_name": row["package_name"],
                "added_by": row["added_by"],
                "added_at": str(row["added_at"]),
                "status": row["status"],
                "status_note": row["status_note"],
            }
            for row in rows
        ],
    }


@v1.post("/packages", status_code=201)
def add_package(
    body: PackageCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    name = body.package_name.strip().lower()
    if not name:
        raise HTTPException(status_code=400, detail="Package name cannot be empty")
    if not re.match(r'^[a-zA-Z0-9._\-\[\]>=<!, ]+$', name):
        raise HTTPException(status_code=400, detail="Invalid package name format")
    try:
        result = db.execute(
            text("""INSERT INTO python_packages (package_name, added_by)
                    VALUES (:name, :user)
                    RETURNING id, package_name, added_by,
                              added_at AT TIME ZONE 'Asia/Seoul' as added_at,
                              status, status_note"""),
            {"name": name, "user": current_user},
        )
        row = result.mappings().first()
        log_audit(db, row["id"], name, "added", current_user)
        db.commit()
        return {
            "id": row["id"],
            "package_name": row["package_name"],
            "added_by": row["added_by"],
            "added_at": str(row["added_at"]),
            "status": row["status"],
            "status_note": row["status_note"],
        }
    except Exception as e:
        db.rollback()
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=409, detail=f"Package '{name}' already exists")
        logger.exception("Failed to add package '%s'", name)
        raise HTTPException(status_code=500, detail="Internal server error")


@v1.delete("/packages/{package_id}")
def delete_package(
    package_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    row = db.execute(
        text("SELECT id, added_by, package_name FROM python_packages WHERE id = :id"),
        {"id": package_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Package not found")
    if row["added_by"] != current_user and current_user not in ADMIN_USERS:
        raise HTTPException(status_code=403, detail="You can only delete packages you added")
    db.execute(text("DELETE FROM python_packages WHERE id = :id"), {"id": package_id})
    log_audit(db, package_id, row["package_name"], "deleted", current_user)
    db.commit()
    return {"ok": True}


@v1.patch("/packages/{package_id}/status")
def update_package_status(
    package_id: int,
    body: PackageStatusUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    if current_user not in ADMIN_USERS:
        raise HTTPException(status_code=403, detail="Only admins can change package status")
    if body.status not in ("pending", "installed", "rejected", "uninstalled"):
        raise HTTPException(status_code=400, detail="Status must be pending, installed, rejected, or uninstalled")
    row = db.execute(
        text("SELECT id, package_name FROM python_packages WHERE id = :id"),
        {"id": package_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Package not found")
    db.execute(
        text("""UPDATE python_packages
                SET status = :status, status_note = :note,
                    status_updated_by = :user, status_updated_at = NOW()
                WHERE id = :id"""),
        {"id": package_id, "status": body.status, "note": body.status_note, "user": current_user},
    )
    log_audit(db, package_id, row["package_name"], f"status:{body.status}", current_user, body.status_note)
    db.commit()
    return {"ok": True}


# ─── Package Audit Log ───────────────────────────────────────────────

@v1.get("/packages/audit-log")
def get_audit_log(
    response: Response,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Admin-only endpoint to query the package audit log."""
    if current_user not in ADMIN_USERS:
        raise HTTPException(status_code=403, detail="Admin access required")
    response.headers["Cache-Control"] = "no-cache"
    rows = db.execute(text("""
        SELECT id, package_id, package_name, action, performed_by, detail,
               created_at AT TIME ZONE 'Asia/Seoul' as created_at,
               count(*) OVER() as _total
        FROM package_audit_log
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """), {"limit": limit, "offset": offset}).mappings().all()
    total = rows[0]["_total"] if rows else 0
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "id": row["id"],
                "package_id": row["package_id"],
                "package_name": row["package_name"],
                "action": row["action"],
                "performed_by": row["performed_by"],
                "detail": row["detail"],
                "created_at": str(row["created_at"]),
            }
            for row in rows
        ],
    }


# ─── Issue Reports ────────────────────────────────────────────────────

VALID_REPORT_CATEGORIES = ("bug", "feature", "question", "other")
VALID_REPORT_STATUSES = ("open", "in_progress", "resolved", "rejected", "wontfix")


@v1.get("/reports")
def list_reports(
    response: Response,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-cache"
    rows = db.execute(text("""
        SELECT id, title, description, category, reported_by, is_anonymous,
               status, admin_note,
               created_at AT TIME ZONE 'Asia/Seoul' as created_at,
               updated_at AT TIME ZONE 'Asia/Seoul' as updated_at,
               count(*) OVER() as _total
        FROM issue_reports
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """), {"limit": limit, "offset": offset}).mappings().all()
    total = rows[0]["_total"] if rows else 0
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "category": row["category"],
                "reported_by": "Anonymous" if row["is_anonymous"] else (row["reported_by"] or "Unknown"),
                "is_anonymous": row["is_anonymous"],
                "status": row["status"],
                "admin_note": row["admin_note"],
                "created_at": str(row["created_at"]),
                "updated_at": str(row["updated_at"]),
            }
            for row in rows
        ],
    }


@v1.post("/reports", status_code=201)
def create_report(
    body: ReportCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    if not body.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    if not body.description.strip():
        raise HTTPException(status_code=400, detail="Description cannot be empty")
    if body.category not in VALID_REPORT_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Category must be one of: {', '.join(VALID_REPORT_CATEGORIES)}")
    try:
        result = db.execute(
            text("""INSERT INTO issue_reports (title, description, category, reported_by, is_anonymous)
                    VALUES (:title, :desc, :cat, :user, :anon)
                    RETURNING id, title, description, category, reported_by, is_anonymous,
                              status, admin_note,
                              created_at AT TIME ZONE 'Asia/Seoul' as created_at,
                              updated_at AT TIME ZONE 'Asia/Seoul' as updated_at"""),
            {
                "title": body.title.strip(),
                "desc": body.description.strip(),
                "cat": body.category,
                "user": current_user,
                "anon": body.is_anonymous,
            },
        )
        row = result.mappings().first()
        db.commit()
        return {
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "category": row["category"],
            "reported_by": "Anonymous" if row["is_anonymous"] else row["reported_by"],
            "is_anonymous": row["is_anonymous"],
            "status": row["status"],
            "admin_note": row["admin_note"],
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }
    except Exception as e:
        db.rollback()
        logger.exception("Failed to create report")
        raise HTTPException(status_code=500, detail="Internal server error")


@v1.patch("/reports/{report_id}/status")
def update_report_status(
    report_id: int,
    body: ReportStatusUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    if current_user not in ADMIN_USERS:
        raise HTTPException(status_code=403, detail="Only admins can change report status")
    if body.status not in VALID_REPORT_STATUSES:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {', '.join(VALID_REPORT_STATUSES)}")
    row = db.execute(
        text("SELECT id FROM issue_reports WHERE id = :id"),
        {"id": report_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    db.execute(
        text("""UPDATE issue_reports
                SET status = :status, admin_note = :note,
                    status_updated_by = :user, updated_at = NOW()
                WHERE id = :id"""),
        {"id": report_id, "status": body.status, "note": body.admin_note, "user": current_user},
    )
    db.commit()
    return {"ok": True}


@v1.delete("/reports/{report_id}")
def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    row = db.execute(
        text("SELECT id, reported_by FROM issue_reports WHERE id = :id"),
        {"id": report_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    if row["reported_by"] != current_user and current_user not in ADMIN_USERS:
        raise HTTPException(status_code=403, detail="You can only delete your own reports")
    db.execute(text("DELETE FROM issue_reports WHERE id = :id"), {"id": report_id})
    db.commit()
    return {"ok": True}


app.include_router(v1)
