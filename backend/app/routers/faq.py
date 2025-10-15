from fastapi import APIRouter, HTTPException, Depends
from typing import List
from ..models.schemas import FAQ
from ..db.postgres import get_postgres_connection
from ..core.security import require_admin
from ..core.config import settings
from openai import OpenAI


router = APIRouter()


@router.get("/faq", response_model=List[FAQ])
def list_faq():
    conn = get_postgres_connection(); cur = conn.cursor()
    cur.execute("SELECT id, question, answer FROM faqs ORDER BY id DESC")
    items = [FAQ(id=r[0], question=r[1], answer=r[2]) for r in cur.fetchall()]
    cur.close(); conn.close()
    return items


@router.post("/faq", response_model=FAQ, dependencies=[Depends(require_admin)])
def create_faq(item: FAQ):
    conn = get_postgres_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO faqs (question, answer) VALUES (%s, %s) RETURNING id", (item.question, item.answer))
    new_id = cur.fetchone()[0]
    conn.commit(); cur.close(); conn.close()
    item.id = new_id
    return item


@router.put("/faq/{faq_id}", response_model=FAQ, dependencies=[Depends(require_admin)])
def update_faq(faq_id: int, item: FAQ):
    conn = get_postgres_connection(); cur = conn.cursor()
    cur.execute("UPDATE faqs SET question=%s, answer=%s, updated_at=NOW() WHERE id=%s", (item.question, item.answer, faq_id))
    if cur.rowcount == 0:
        cur.close(); conn.close()
        raise HTTPException(status_code=404, detail="FAQ not found")
    conn.commit(); cur.close(); conn.close()
    item.id = faq_id
    return item


@router.delete("/faq/{faq_id}", dependencies=[Depends(require_admin)])
def delete_faq(faq_id: int):
    conn = get_postgres_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM faqs WHERE id=%s", (faq_id,))
    if cur.rowcount == 0:
        cur.close(); conn.close()
        raise HTTPException(status_code=404, detail="FAQ not found")
    conn.commit(); cur.close(); conn.close()
    return {"deleted": True}


@router.post("/faq/generate", dependencies=[Depends(require_admin)])
def generate_faqs_from_resolved(limit: int = 10, max_new: int = 5):
    conn = get_postgres_connection(); cur = conn.cursor()
    cur.execute(
        "SELECT id, subject, category, description FROM tickets WHERE status='resolved' ORDER BY updated_at DESC LIMIT %s",
        (limit,),
    )
    cases = cur.fetchall()
    cur.close(); conn.close()

    if not cases:
        return {"created": 0}

    prompts = []
    for _id, subject, category, description in cases:
        prompts.append(f"Subject: {subject}\nCategory: {category}\nResolution: {description}")

    qa: List[FAQ] = []
    if settings.OPENAI_API_KEY:
        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            system = "You are a support knowledge base curator. Produce concise FAQ pairs from successful resolutions in 'Question: Answer' lines."
            user = "\n\n".join(prompts)
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.2,
            )
            text = completion.choices[0].message.content.strip()
            for line in text.split("\n"):
                if ":" in line:
                    q, a = line.split(":", 1)
                    qa.append(FAQ(question=q.strip(), answer=a.strip()))
        except Exception:
            pass

    if not qa:
        for _id, subject, category, description in cases[:max_new]:
            qa.append(FAQ(question=subject, answer=description))

    conn = get_postgres_connection(); cur = conn.cursor()
    created = 0
    for item in qa[:max_new]:
        cur.execute("INSERT INTO faqs (question, answer) VALUES (%s, %s)", (item.question, item.answer))
        created += 1
    conn.commit(); cur.close(); conn.close()
    return {"created": created}


