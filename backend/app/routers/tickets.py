from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from ..models.schemas import Ticket, TicketUpdate
from ..db.postgres import get_postgres_connection
from ..db.mongo import get_mongo_db
from ..core.security import require_admin


router = APIRouter()


@router.get("/tickets", response_model=List[Ticket], dependencies=[Depends(require_admin)])
def list_tickets(
    q: Optional[str] = Query(None, description="Search in name/email/subject"),
    status: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
):
    conn = get_postgres_connection(); cur = conn.cursor()
    where = []
    params = []
    if q:
        where.append("(LOWER(customer_name) LIKE %s OR LOWER(user_email) LIKE %s OR LOWER(subject) LIKE %s)")
        like = f"%{q.lower()}%"; params.extend([like, like, like])
    if status:
        where.append("status = %s"); params.append(status)
    if category:
        where.append("category = %s"); params.append(category)
    if priority:
        where.append("priority = %s"); params.append(priority)
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    cur.execute(
        f"""
        SELECT id, user_email, customer_name, subject, category, description, status, priority, session_id, created_at, updated_at
        FROM tickets {where_sql}
        ORDER BY id DESC
        """,
        params,
    )
    items = [
        Ticket(
            id=r[0], 
            user_email=r[1] if r[1] and '@' in r[1] else 'guest@example.com',  # Handle empty emails
            customer_name=r[2], 
            subject=r[3], 
            category=r[4], 
            description=r[5],
            status=r[6], 
            priority=r[7], 
            session_id=r[8], 
            created_at=str(r[9]) if r[9] else None, 
            updated_at=str(r[10]) if r[10] else None
        )
        for r in cur.fetchall()
    ]
    cur.close(); conn.close()
    return items


@router.post("/tickets", response_model=Ticket)
def create_ticket(ticket: Ticket):
    conn = get_postgres_connection(); cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO tickets (user_email, customer_name, subject, category, description, status, priority, session_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """,
        (
            ticket.user_email, ticket.customer_name, ticket.subject, ticket.category,
            ticket.description, ticket.status or 'open', ticket.priority or 'medium', ticket.session_id
        ),
    )
    ticket.id = cur.fetchone()[0]
    conn.commit(); cur.close(); conn.close()
    return ticket


@router.patch("/tickets/{ticket_id}", response_model=Ticket, dependencies=[Depends(require_admin)])
def update_ticket(ticket_id: int, ticket: TicketUpdate):
    conn = get_postgres_connection(); cur = conn.cursor()
    cur.execute(
        """
        UPDATE tickets
        SET user_email=COALESCE(%s, user_email),
            customer_name=COALESCE(%s, customer_name),
            subject=COALESCE(%s, subject),
            category=COALESCE(%s, category),
            description=COALESCE(%s, description),
            status=COALESCE(%s, status),
            priority=COALESCE(%s, priority),
            session_id=COALESCE(%s, session_id),
            updated_at=NOW()
        WHERE id=%s
        RETURNING id, user_email, customer_name, subject, category, description, status, priority, session_id, created_at, updated_at
        """,
        (
            ticket.user_email, ticket.customer_name, ticket.subject, ticket.category, ticket.description,
            ticket.status, ticket.priority, ticket.session_id, ticket_id
        ),
    )
    row = cur.fetchone()
    conn.commit(); cur.close(); conn.close()
    return Ticket(
        id=row[0], user_email=row[1], customer_name=row[2], subject=row[3], category=row[4], description=row[5],
        status=row[6], priority=row[7], session_id=row[8], created_at=str(row[9]) if row[9] else None, updated_at=str(row[10]) if row[10] else None
    )


@router.get("/tickets/resolution-stats", dependencies=[Depends(require_admin)])
def get_resolution_stats():
    """Get statistics about ticket resolutions"""
    conn = get_postgres_connection(); cur = conn.cursor()
    
    # Get resolution statistics
    cur.execute("""
        SELECT 
            COUNT(*) as total_tickets,
            COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved_tickets,
            COUNT(CASE WHEN status = 'escalated' THEN 1 END) as escalated_tickets,
            COUNT(CASE WHEN status = 'open' THEN 1 END) as open_tickets,
            COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_progress_tickets,
            COUNT(CASE WHEN status = 'closed' THEN 1 END) as closed_tickets,
            AVG(CASE WHEN status = 'resolved' AND updated_at IS NOT NULL 
                THEN EXTRACT(EPOCH FROM (updated_at - created_at))/3600 
                END) as avg_resolution_hours
        FROM tickets
    """)
    
    stats = cur.fetchone()
    cur.close(); conn.close()
    
    return {
        "total_tickets": stats[0],
        "resolved_tickets": stats[1],
        "escalated_tickets": stats[2],
        "open_tickets": stats[3],
        "in_progress_tickets": stats[4],
        "closed_tickets": stats[5],
        "avg_resolution_hours": round(stats[6], 2) if stats[6] else 0,
        "resolution_rate": round((stats[1] / stats[0]) * 100, 2) if stats[0] > 0 else 0
    }


