from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
import os
from dotenv import load_dotenv
from datetime import datetime, date, timedelta, timezone, time

load_dotenv()

app = FastAPI(title="SbioChat Dashboard API")

KST = timezone(timedelta(hours=9))

# CORS Configuration
FRONTEND_PORT_HOST = os.getenv("FRONTEND_PORT_HOST", "3005")
origins = [
    f"http://localhost:{FRONTEND_PORT_HOST}",
    f"http://127.0.0.1:{FRONTEND_PORT_HOST}",
    "http://localhost:80",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Setup
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_HOST = os.getenv("POSTGRES_HOST", "postgres")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "openwebui")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def read_root():
    return {"message": "Welcome to Open WebUI Dashboard API"}


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")


@app.get("/api/stats/overview")
def get_overview(db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT
            (SELECT count(*) FROM chat) as total_chats,
            (SELECT sum(json_array_length(chat->'messages')) FROM chat) as total_messages,
            (SELECT count(DISTINCT m.value) FROM chat, json_array_elements_text(chat->'models') AS m(value)) as total_models,
            (SELECT count(*) FROM feedback) as total_feedbacks
    """)).mappings().first()
    return {
        "total_chats": result["total_chats"],
        "total_messages": result["total_messages"] or 0,
        "total_models": result["total_models"],
        "total_feedbacks": result["total_feedbacks"],
    }


@app.get("/api/stats/daily")
def get_daily_stats(
    date_from: date = Query(alias="from", default=None),
    date_to: date = Query(alias="to", default=None),
    db: Session = Depends(get_db),
):
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

    return [
        {
            "date": str(row["date"]),
            "chat_count": row["chat_count"],
            "message_count": row["message_count"] or 0,
            "user_count": row["user_count"],
        }
        for row in rows
    ]


@app.get("/api/stats/workspace-ranking")
def get_workspace_ranking(db: Session = Depends(get_db)):
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
        workspace_names AS (
            SELECT id, name FROM model
        )
        SELECT
            wc.workspace as id,
            coalesce(wn.name, wc.workspace) as name,
            wc.chat_count,
            wc.message_count,
            wc.user_count,
            coalesce(wf.positive, 0) as positive,
            coalesce(wf.negative, 0) as negative
        FROM workspace_chats wc
        LEFT JOIN workspace_feedback wf ON wc.workspace = wf.workspace
        LEFT JOIN workspace_names wn ON wc.workspace = wn.id
        ORDER BY wc.chat_count DESC
    """)).mappings().all()

    return [
        {
            "id": row["id"],
            "name": row["name"],
            "user_count": row["user_count"],
            "chat_count": row["chat_count"],
            "message_count": row["message_count"] or 0,
            "positive": row["positive"],
            "negative": row["negative"],
        }
        for row in rows
    ]


@app.get("/api/stats/developer-ranking")
def get_developer_ranking(db: Session = Depends(get_db)):
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
            coalesce(sum(wfb.negative), 0) as total_negative
        FROM developer_workspaces dw
        JOIN "user" u ON dw.user_id = u.id
        LEFT JOIN workspace_metrics wm ON dw.workspace_id = wm.workspace
        LEFT JOIN workspace_fb wfb ON dw.workspace_id = wfb.workspace
        GROUP BY u.id, u.name, u.email
        ORDER BY total_chats DESC
    """)).mappings().all()

    return [
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
    ]


@app.get("/api/stats/group-ranking")
def get_group_ranking(db: Session = Depends(get_db)):
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
                count(*) FILTER (WHERE (f.data->>'rating')::int > 0) as positive,
                count(*) FILTER (WHERE (f.data->>'rating')::int < 0) as negative
            FROM feedback f
            GROUP BY f.user_id
        )
        SELECT
            gm.group_id,
            gm.group_name,
            gm.member_count,
            coalesce(sum(uu.chat_count), 0) as total_chats,
            coalesce(sum(uu.message_count), 0) as total_messages,
            coalesce(sum(ufb.positive), 0) as total_positive,
            coalesce(sum(ufb.negative), 0) as total_negative,
            round(coalesce(sum(uu.chat_count), 0)::numeric
                / NULLIF(gm.member_count, 0), 1) as chats_per_member,
            round(coalesce(sum(uu.message_count), 0)::numeric
                / NULLIF(gm.member_count, 0), 1) as messages_per_member
        FROM group_members gm
        LEFT JOIN user_usage uu ON gm.user_id = uu.user_id
        LEFT JOIN user_fb ufb ON gm.user_id = ufb.user_id
        GROUP BY gm.group_id, gm.group_name, gm.member_count
        ORDER BY chats_per_member DESC NULLS LAST
    """)).mappings().all()

    return [
        {
            "group_id": row["group_id"],
            "group_name": row["group_name"],
            "member_count": row["member_count"],
            "total_chats": int(row["total_chats"]),
            "total_messages": int(row["total_messages"]),
            "total_positive": int(row["total_positive"]),
            "total_negative": int(row["total_negative"]),
            "chats_per_member": float(row["chats_per_member"] or 0),
            "messages_per_member": float(row["messages_per_member"] or 0),
        }
        for row in rows
    ]


@app.get("/api/feedbacks/summary")
def get_feedback_summary(db: Session = Depends(get_db)):
    counts = db.execute(text("""
        SELECT
            count(*) FILTER (WHERE (data->>'rating')::int > 0) as positive,
            count(*) FILTER (WHERE (data->>'rating')::int < 0) as negative
        FROM feedback
    """)).mappings().first()

    recent = db.execute(text("""
        SELECT
            id,
            data->>'model_id' as model_id,
            (data->>'rating')::int as rating,
            data->>'comment' as comment,
            to_timestamp(created_at) AT TIME ZONE 'Asia/Seoul' as created_at
        FROM feedback
        ORDER BY created_at DESC
        LIMIT 10
    """)).mappings().all()

    return {
        "positive": counts["positive"],
        "negative": counts["negative"],
        "recent": [
            {
                "id": row["id"],
                "model_id": row["model_id"],
                "rating": row["rating"],
                "comment": row["comment"],
                "created_at": str(row["created_at"]),
            }
            for row in recent
        ],
    }
