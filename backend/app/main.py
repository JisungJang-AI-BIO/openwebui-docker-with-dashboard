from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
import os
from dotenv import load_dotenv
from datetime import datetime, date, timedelta, timezone, time

load_dotenv()

app = FastAPI(title="Open WebUI Dashboard API")

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
            sum(json_array_length(chat->'messages')) as message_count
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
        }
        for row in rows
    ]


@app.get("/api/stats/models")
def get_model_stats(db: Session = Depends(get_db)):
    # Model usage count
    usage_rows = db.execute(text("""
        SELECT m.value as model, count(*) as chat_count
        FROM chat, json_array_elements_text(chat->'models') AS m(value)
        GROUP BY m.value
        ORDER BY chat_count DESC
    """)).mappings().all()

    # Model average response length
    avg_rows = db.execute(text("""
        SELECT
            m_model.value as model,
            round(avg(length(msg.value->>'content'))) as avg_response_length
        FROM chat,
            json_array_elements_text(chat->'models') AS m_model(value),
            json_array_elements(chat->'messages') AS msg(value)
        WHERE msg.value->>'role' = 'assistant'
        GROUP BY m_model.value
    """)).mappings().all()

    avg_map = {row["model"]: row["avg_response_length"] for row in avg_rows}

    return [
        {
            "model": row["model"],
            "chat_count": row["chat_count"],
            "avg_response_length": int(avg_map.get(row["model"], 0) or 0),
        }
        for row in usage_rows
    ]


@app.get("/api/chats/recent")
def get_recent_chats(
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
):
    rows = db.execute(text("""
        SELECT
            id,
            title,
            chat->'models' as models,
            json_array_length(chat->'messages') as message_count,
            to_timestamp(created_at) AT TIME ZONE 'Asia/Seoul' as created_at,
            to_timestamp(updated_at) AT TIME ZONE 'Asia/Seoul' as updated_at
        FROM chat
        ORDER BY updated_at DESC
        LIMIT :limit
    """), {"limit": limit}).mappings().all()

    return [
        {
            "id": row["id"],
            "title": row["title"],
            "models": row["models"],
            "message_count": row["message_count"],
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
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
