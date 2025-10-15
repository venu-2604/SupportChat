from fastapi import APIRouter, Depends, Query
from datetime import datetime, timedelta
from ..core.security import require_admin
from ..db.mongo import get_case_memory_collection
from ..db.postgres import get_postgres_connection


router = APIRouter()


@router.get("/admin/chats", dependencies=[Depends(require_admin)])
def get_chat_history(limit: int = 50):
    col = get_case_memory_collection()
    docs = list(col.find({}, {"_id": 0}).sort("_id", -1).limit(limit))
    return docs


@router.get("/admin/users-live", dependencies=[Depends(require_admin)])
def get_users_live():
    """Aggregate active chat sessions with user metadata and latest status/priority from tickets."""
    col = get_case_memory_collection()
    # Gather latest doc per session
    pipeline = [
        {"$sort": {"ts": -1}},
        {"$group": {
            "_id": "$session_id",
            "last": {"$first": "$$ROOT"},
            "started_at": {"$last": "$ts"},
        }},
    ]
    items = list(col.aggregate(pipeline))

    # Map by session
    sessions = []
    conn = get_postgres_connection(); cur = conn.cursor()
    for it in items:
        last = it.get("last", {})
        sess = {
            "session_id": last.get("session_id"),
            "user_email": last.get("user_email"),
            "customer_name": last.get("customer_name"),
            "subject": last.get("subject"),
            "category": last.get("category"),
            "last_message_role": last.get("role"),
            "last_message": last.get("content"),
            "last_at": str(last.get("ts")) if last.get("ts") else None,
            "started_at": str(it.get("started_at")) if it.get("started_at") else None,
            "status": None,
            "priority": None,
            "has_prefill": bool(last.get("user_email") or last.get("customer_name") or last.get("subject")),
        }
        # Try to enrich with ticket info
        try:
            cur.execute(
                "SELECT status, priority FROM tickets WHERE session_id=%s ORDER BY id DESC LIMIT 1",
                (sess["session_id"],)
            )
            row = cur.fetchone()
            if row:
                sess["status"], sess["priority"] = row[0], row[1]
        except Exception:
            pass
        sessions.append(sess)
    cur.close(); conn.close()
    return {"sessions": sessions}


@router.get("/admin/cases-table", dependencies=[Depends(require_admin)])
def get_cases_table(limit: int = 200):
    """Return tickets with enriched messages and resolution summary for table view."""
    conn = get_postgres_connection(); cur = conn.cursor()
    cur.execute(
        """
        SELECT id, customer_name, user_email, subject, category, priority, status, description, session_id
        FROM tickets
        ORDER BY id DESC
        LIMIT %s
        """,
        (limit,)
    )
    rows = cur.fetchall()
    cur.close(); conn.close()

    col = get_case_memory_collection()
    items = []
    for r in rows:
        _id, customer_name, user_email, subject, category, priority, status, description, session_id = r
        # messages from mongo for this session
        messages = []
        if session_id:
            try:
                for d in col.find({"session_id": session_id}, {"_id": 0}).sort("_id", 1):
                    messages.append({"role": d.get("role"), "content": d.get("content")})
            except Exception:
                pass
        # extract resolution summary
        resolution_summary = None
        if description and "--- RESOLUTION SUMMARY ---" in description:
            try:
                resolution_summary = description.split("--- RESOLUTION SUMMARY ---", 1)[1].strip()
            except Exception:
                pass
        items.append({
            "customer_name": customer_name,
            "customer_email": user_email,
            "subject": subject,
            "category": category,
            "priority": priority,
            "status": status,
            "messages": messages,
            "resolution_summary": resolution_summary,
        })
    return {"items": items}


@router.get("/admin/analytics", dependencies=[Depends(require_admin)])
def get_analytics(start_date: str = Query(None), end_date: str = Query(None)):
    conn = get_postgres_connection(); cur = conn.cursor()
    
    # Build date filter
    date_filter = ""
    params = []
    if start_date and end_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
            date_filter = " WHERE created_at >= %s AND created_at <= %s"
            params = [start_dt, end_dt]
        except ValueError:
            pass
    
    # Basic counts with date filter
    cur.execute(f"SELECT COUNT(*) FROM faqs{date_filter}" if not date_filter else f"SELECT COUNT(*) FROM faqs")
    faq_count = cur.fetchone()[0]
    
    cur.execute(
        f"SELECT COUNT(*) FROM tickets WHERE status IN ('open','in_progress','escalated'){' AND ' + date_filter.lstrip(' WHERE') if date_filter else ''}",
        params,
    )
    active_tickets = cur.fetchone()[0]
    
    cur.execute(f"SELECT COUNT(*) FROM tickets WHERE status = 'escalated'{' AND ' + date_filter.lstrip(' WHERE') if date_filter else ''}", params)
    escalated_count = cur.fetchone()[0]
    
    cur.execute(f"SELECT COUNT(*) FROM tickets WHERE status = 'resolved'{' AND ' + date_filter.lstrip(' WHERE') if date_filter else ''}", params)
    resolved_count = cur.fetchone()[0]
    
    # Get unique users from tickets
    cur.execute(f"SELECT COUNT(DISTINCT user_email) FROM tickets{date_filter}", params)
    unique_users = cur.fetchone()[0]
    
    # Get tickets by category
    cur.execute(f"SELECT category, COUNT(*) FROM tickets{date_filter} {'GROUP BY category' if not date_filter else 'GROUP BY category'}", params)
    category_counts = dict(cur.fetchall())
    
    # Get period tickets for usage data
    if start_date and end_date:
        cur.execute("SELECT COUNT(*) FROM tickets WHERE created_at >= %s AND created_at <= %s", params)
        period_tickets = cur.fetchone()[0]
    else:
        cur.execute("SELECT COUNT(*) FROM tickets WHERE created_at >= NOW() - INTERVAL '7 days'")
        period_tickets = cur.fetchone()[0]
    
    cur.close(); conn.close()

    # Get chat session data from mongo
    col = get_case_memory_collection()
    sessions = set()
    for doc in col.find({}, {"_id": 0, "session_id": 1}):
        if doc.get("session_id"):
            sessions.add(doc["session_id"])
    
    total_sessions = len(sessions)
    
    return {
        "faq_count": faq_count,
        "active_tickets": active_tickets,
        "escalated_count": escalated_count,
        "resolved_count": resolved_count,
        "unique_users": unique_users,
        "total_sessions": total_sessions,
        "weekly_tickets": period_tickets,
        "category_counts": category_counts,
        "series": [period_tickets, active_tickets, escalated_count, resolved_count, unique_users]
    }


@router.get("/admin/users", dependencies=[Depends(require_admin)])
def get_registered_users():
    """Get all registered users from the database."""
    conn = get_postgres_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, email, is_admin, created_at 
        FROM users 
        ORDER BY created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    users = []
    for row in rows:
        users.append({
            "id": row[0],
            "email": row[1],
            "is_admin": row[2],
            "created_at": str(row[3]) if row[3] else None
        })
    
    return {"users": users}


@router.get("/admin/user-analytics", dependencies=[Depends(require_admin)])
def get_user_analytics(start_date: str = Query(None), end_date: str = Query(None)):
    conn = get_postgres_connection(); cur = conn.cursor()
    
    # Top users by ticket count
    cur.execute("""
        SELECT customer_name, user_email, COUNT(*) as ticket_count 
        FROM tickets 
        WHERE customer_name IS NOT NULL 
        GROUP BY customer_name, user_email 
        ORDER BY ticket_count DESC 
        LIMIT 5
    """)
    top_users = cur.fetchall()
    
    cur.close(); conn.close()
    
    return {
        "top_users": [
            {
                "name": user[0] or user[1].split('@')[0],
                "email": user[1].split('@')[0] + '@...' if len(user[1]) > 15 else user[1],
                "tickets": user[2]
            }
            for user in top_users
        ]
    }


