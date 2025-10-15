from typing import Dict, Any, List, Tuple
from ..db.mongo import get_case_memory_collection
from ..db.redis_client import get_redis_client
from ..db.postgres import get_postgres_connection
from ..core.config import settings
from openai import OpenAI
import httpx
import google.generativeai as genai
from datetime import datetime
import asyncio
import time


async def handle_incoming_message(data: Dict[str, Any]) -> Dict[str, Any]:
    session_id = data.get("session_id")
    content = data.get("content", "").strip()
    user_email = data.get("user_email", "guest@example.com")
    customer_name = data.get("customer_name")
    subject = data.get("subject")
    category = data.get("category")
    is_related_question = data.get("is_related_question", False)  # Track if this came from clicking a related question

    # Track if this is a related question click
    if is_related_question and content:
        _track_related_question_click(content)

    # Immediately record the user's message with metadata so admin views/analytics see activity
    if session_id and content:
        _store_chat(
            session_id,
            role="user",
            content=content,
            meta={
                "user_email": user_email,
                "customer_name": customer_name,
                "subject": subject,
                "category": category,
            },
        )

    # Ensure there is an open ticket for this session on the first user message
    try:
        _ensure_open_ticket(
            session_id=session_id,
            user_email=user_email,
            customer_name=customer_name,
            subject=subject,
            category=category,
            first_message=content,
        )
    except Exception:
        # Do not block the chat flow if ticket creation fails
        pass

    # Track user activity timestamp for auto-resolve logic
    redis = get_redis_client()
    try:
        redis.set(f"last_user:{session_id}", str(int(time.time())))
        # Any new user message cancels pending auto-resolve
        redis.delete(f"pending_resolve:{session_id}")
    except Exception:
        pass

    # Immediate escalation trigger (manual override)
    if content.lower().strip() in {"!escalate", "/escalate", "escalate now", "please escalate"}:
        try:
            _escalate_ticket(session_id=session_id, user_email=user_email, customer_name=customer_name, subject=subject, category=category, reason="Manual escalation trigger")
            _reset_failure_counter(session_id)
        except Exception:
            pass
        msg = "I've escalated this case to a human agent. You'll be contacted shortly."
        _store_chat(session_id, role="assistant", content=msg)
        return {"session_id": session_id, "role": "assistant", "content": msg, "related": _related_questions(category)}

    # Check for resolution confirmation keywords
    if _is_resolution_confirmation(content):
        _mark_ticket_resolved(session_id, user_email)
        _store_chat(session_id, role="assistant", content="Great! I've marked your case as resolved. Thank you for confirming!")
        return {"session_id": session_id, "role": "assistant", "content": "Great! I've marked your case as resolved. Thank you for confirming!", "related": _related_questions(category)}

    cached = redis.get(f"faq:{content.lower()}")
    if cached:
        answer = cached
        _store_chat(session_id, role="assistant", content=answer)
        # Check if this FAQ answer might resolve the issue
        if _should_suggest_resolution(answer, content):
            answer += "\n\n✅ Does this answer resolve your issue? If so, please let me know by saying 'yes, resolved' or 'that helps, thanks'."
            _schedule_auto_resolve(session_id, user_email, delay_seconds=120)
        return {"session_id": session_id, "role": "assistant", "content": answer, "related": _related_questions(category)}

    # naive answer using FAQs in Postgres
    answer = _lookup_faq_answer(content)
    if answer:
        redis.setex(f"faq:{content.lower()}", 3600, answer)
        # Check if this FAQ answer might resolve the issue
        if _should_suggest_resolution(answer, content):
            answer += "\n\n✅ Does this answer resolve your issue? If so, please let me know by saying 'yes, resolved' or 'that helps, thanks'."
            _schedule_auto_resolve(session_id, user_email, delay_seconds=120)
        _store_chat(session_id, role="assistant", content=answer)
        return {"session_id": session_id, "role": "assistant", "content": answer, "related": _related_questions(category)}

    # Always try Google Gemini next and store as new FAQ on success
    gemini_answer = _gemini_answer(content)
    if gemini_answer:
        try:
            _create_faq(question=content, answer=gemini_answer)
        except Exception:
            pass
        try:
            redis.setex(f"faq:{content.lower()}", 3600, gemini_answer)
        except Exception:
            pass
        _store_chat(session_id, role="assistant", content=gemini_answer)
        return {"session_id": session_id, "role": "assistant", "content": gemini_answer, "related": _related_questions(category)}

    # handle fallback; try OpenAI if key provided
    if settings.OPENAI_API_KEY:
        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            history = _load_chat_history(session_id)
            messages = ([{"role": "system", "content": "You are a helpful customer support assistant. Use FAQs if relevant."}] +
                        [{"role": m["role"], "content": m["content"]} for m in history] +
                        [{"role": "user", "content": content}])
            completion = client.chat.completions.create(model="gpt-4o-mini", messages=messages, temperature=0.3)
            answer = completion.choices[0].message.content.strip()
            if answer:
                # Check if this AI answer might resolve the issue
                if _should_suggest_resolution(answer, content):
                    answer += "\n\n✅ Does this answer resolve your issue? If so, please let me know by saying 'yes, resolved' or 'that helps, thanks'."
                    _schedule_auto_resolve(session_id, user_email, delay_seconds=120)
                _store_chat(session_id, role="assistant", content=answer)
                return {"session_id": session_id, "role": "assistant", "content": answer, "related": _related_questions(category)}
        except Exception:
            pass
    else:
        # Fallback local LLM via Ollama if available (no API key needed)
        try:
            history = _load_chat_history(session_id)
            prompt = _format_prompt(history, content)
            with httpx.Client(timeout=10) as client:
                resp = client.post("http://localhost:11434/api/generate", json={"model": "llama3.1:8b", "prompt": prompt, "stream": False})
                if resp.status_code == 200:
                    data = resp.json()
                    answer = data.get("response", "").strip()
                    if answer:
                        # Check if this AI answer might resolve the issue
                        if _should_suggest_resolution(answer, content):
                            answer += "\n\n✅ Does this answer resolve your issue? If so, please let me know by saying 'yes, resolved' or 'that helps, thanks'."
                            _schedule_auto_resolve(session_id, user_email, delay_seconds=120)
                        _store_chat(session_id, role="assistant", content=answer)
                        return {"session_id": session_id, "role": "assistant", "content": answer, "related": _related_questions(category)}
        except Exception:
            pass

    # handle fallback; count failures and escalate after many tries (avoid premature escalation)
    failures = _increment_failure_counter(session_id)
    if failures >= 5:
        _create_ticket(user_email, subject=subject or f"Escalation for session {session_id}", description=f"User asked: {content}", category=category, customer_name=customer_name, session_id=session_id, status="escalated")
        _reset_failure_counter(session_id)
        msg = "I'm escalating your request to a human agent. You'll be contacted soon."
        _store_chat(session_id, role="assistant", content=msg)
        return {"session_id": session_id, "role": "assistant", "content": msg, "related": _related_questions(category)}

    reply = "I'm not sure about that. Could you rephrase or provide more details?"
    _store_chat(session_id, role="assistant", content=reply)
    return {"session_id": session_id, "role": "assistant", "content": reply, "related": _related_questions(category)}


def _lookup_faq_answer(query: str) -> str | None:
    if not query:
        return None
    conn = get_postgres_connection(); cur = conn.cursor()
    cur.execute("SELECT answer FROM faqs WHERE LOWER(question) = LOWER(%s) LIMIT 1", (query,))
    row = cur.fetchone()
    cur.close(); conn.close()
    if row:
        return row[0]
    return None


def _create_faq(question: str, answer: str) -> None:
    conn = get_postgres_connection(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO faqs (question, answer) VALUES (%s, %s)", (question, answer))
        conn.commit()
    finally:
        cur.close(); conn.close()


def _gemini_answer(query: str) -> str | None:
    if not settings.GOOGLE_API_KEY or not query:
        return None
    try:
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        # Try multiple model ids for compatibility across API versions
        model_ids = [
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
        ]
        last_err: Exception | None = None
        for mid in model_ids:
            try:
                model = genai.GenerativeModel(mid)
                resp = model.generate_content([
                    "You are a customer support assistant. Answer clearly and concisely. If steps are needed, provide them as a short list.",
                    query,
                ])
                if resp and resp.candidates:
                    text = resp.candidates[0].content.parts[0].text.strip()
                    if text:
                        return text
            except Exception as e:  # try next model id
                last_err = e
                continue
        if last_err:
            return None
        return None
    except Exception:
        return None


def _get_example_questions(category: str) -> str:
    """Get example questions for a category to guide Gemini."""
    examples = {
        'Billing': '- How do I update my payment method?\n- When will I be charged for my subscription?\n- Can I get a refund for my purchase?',
        'Technical': '- Why is the website loading slowly?\n- How do I fix this error message?\n- The app keeps crashing, what should I do?',
        'Account': '- How do I change my email address?\n- How do I delete my account?\n- How do I enable two-factor authentication?',
        'General': '- How do I reset my password?\n- What are your business hours?\n- How do I contact customer support?'
    }
    return examples.get(category, examples['General'])


def _generate_related_questions_online(query: str, category: str | None, limit: int = 3) -> List[str]:
    """Generate related questions using Gemini API based on the user's query."""
    if not settings.GOOGLE_API_KEY or not query:
        return []
    try:
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        model_ids = [
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
        ]
        
        # Normalize category
        cat_keyword = category.split()[0] if category else 'General'
        
        prompt = f"""You are a customer support assistant. Generate {limit} common customer questions about {cat_keyword} category.

Category: {cat_keyword}
Topic: {query}

Requirements:
- Questions MUST be directly related to {cat_keyword} category
- Questions should be practical and commonly asked by customers
- Each question should be 8-15 words
- Questions must end with a question mark
- Do NOT include numbering, bullets, or extra formatting

Examples for {cat_keyword}:
{_get_example_questions(cat_keyword)}

Generate {limit} similar questions, one per line:"""
        
        for mid in model_ids:
            try:
                model = genai.GenerativeModel(mid)
                resp = model.generate_content([prompt])
                if resp and resp.candidates:
                    text = resp.candidates[0].content.parts[0].text.strip()
                    if text:
                        # Parse the response to extract questions
                        questions = []
                        for line in text.split('\n'):
                            line = line.strip()
                            # Remove numbering, bullets, and extra whitespace
                            line = line.lstrip('0123456789.-*• ').strip()
                            if line and len(line) > 5:  # Basic validation
                                questions.append(line)
                        return questions[:limit]
            except Exception:
                continue
        return []
    except Exception:
        return []


def _store_chat(session_id: str, role: str, content: str, meta: Dict[str, Any] | None = None) -> None:
    try:
        col = get_case_memory_collection()
        doc: Dict[str, Any] = {"session_id": session_id, "role": role, "content": content, "ts": datetime.utcnow()}
        if meta:
            # only store simple serializable fields
            for k in ["user_email", "customer_name", "subject", "category"]:
                v = meta.get(k)
                if v is not None:
                    doc[k] = v
        col.insert_one(doc)
    except Exception:
        # Do not block responses if Mongo is temporarily unavailable
        pass

def _load_chat_history(session_id: str):
    try:
        col = get_case_memory_collection()
        return list(col.find({"session_id": session_id}, {"_id": 0, "session_id": 0}))
    except Exception:
        return []


def _format_prompt(history, user_input: str) -> str:
    lines = ["You are a helpful support agent. Be concise."]
    for h in history[-10:]:
        lines.append(f"{h['role']}: {h['content']}")
    lines.append(f"user: {user_input}")
    return "\n".join(lines)
def _append_related_faqs(answer: str, category: str | None) -> str:
    related: List[Tuple[str, str]] = _fetch_related_faqs(category, limit=3)
    if not related:
        return answer
    lines = [answer, "", "Frequently Asked Questions:"]
    for i, (q, a) in enumerate(related, start=1):
        lines.append(f"{i}. {q}\n   {a}")
    return "\n".join(lines)


# def _fetch_related_faqs(category: str | None, limit: int = 3) -> List[Tuple[str, str]]:
#     conn = get_postgres_connection(); cur = conn.cursor()
#     rows = []
#     matched_ids = set()
    
#     # Try category-based search first if category is provided
#     if category:
#         keyword = category.split()[0] if ' ' in category else category
#         try:
#             cur.execute("SELECT id, question, answer FROM faqs WHERE LOWER(question) LIKE %s ORDER BY id DESC LIMIT %s", (f"%{keyword.lower()}%", limit))
#             category_rows = cur.fetchall()
#             rows.extend([(r[1], r[2]) for r in category_rows])
#             matched_ids.update([r[0] for r in category_rows])
#         except Exception:
#             pass
    
#     # If we need more FAQs to reach the limit, get latest ones (excluding already matched)
#     if len(rows) < limit:
#         try:
#             remaining = limit - len(rows)
#             if matched_ids:
#                 placeholders = ','.join(['%s'] * len(matched_ids))
#                 cur.execute(f"SELECT question, answer FROM faqs WHERE id NOT IN ({placeholders}) ORDER BY id DESC LIMIT %s", (*matched_ids, remaining))
#             else:
#                 cur.execute("SELECT question, answer FROM faqs ORDER BY id DESC LIMIT %s", (remaining,))
#             additional_rows = cur.fetchall()
#             rows.extend([(r[0], r[1]) for r in additional_rows])
#         except Exception:
#             pass
    
#     cur.close()
#     conn.close()
#     return rows[:limit]  # Ensure we don't exceed limit

def _fetch_related_faqs(category: str | None, limit: int = 3) -> List[Tuple[str, str]]:
    """Fetch FAQs filtered by category keywords."""
    conn = get_postgres_connection()
    cur = conn.cursor()
    try:
        # Normalize category to get the main keyword
        category_keyword = None
        if category:
            category_keyword = category.split()[0].lower()  # "General Question" -> "general"
        
        print(f"🔍 DEBUG: _fetch_related_faqs - category_keyword='{category_keyword}'", flush=True)
        
        # Try to fetch category-specific FAQs first
        if category_keyword:
            # Map categories to relevant keywords
            keyword_map = {
                'general': ['password', 'login', 'account', 'contact', 'support', 'help'],
                'technical': ['error', 'loading', 'crash', 'bug', 'issue', 'problem', 'fix'],
                'billing': ['bill', 'payment', 'subscription', 'invoice', 'refund', 'charge', 'price', 'cost'],
                'account': ['profile', 'settings', 'username', 'delete', 'export', 'privacy']
            }
            
            keywords = keyword_map.get(category_keyword, [])
            if keywords:
                # Build a query to find FAQs matching any of the keywords
                keyword_conditions = ' OR '.join(['LOWER(question) LIKE %s'] * len(keywords))
                keyword_params = [f'%{kw}%' for kw in keywords]
                
                cur.execute(
                    f"SELECT question, answer FROM faqs WHERE {keyword_conditions} ORDER BY RANDOM() LIMIT %s",
                    (*keyword_params, limit)
                )
                rows = cur.fetchall()
                print(f"🔍 DEBUG: Found {len(rows)} FAQs matching category keywords", flush=True)
                if rows:
                    return [(r[0], r[1]) for r in rows]
        
        # Don't fallback to random FAQs - return empty so Gemini can generate
        print(f"🔍 DEBUG: No category-specific FAQs found, returning empty", flush=True)
        return []
    except Exception as e:
        print(f"Error fetching FAQs: {e}", flush=True)
        return []
    finally:
        cur.close()
        conn.close()


# def _related_questions(category: str | None, limit: int = 3) -> List[str]:
#     """Return only the related FAQ question titles for frontend suggestions."""
#     pairs = _fetch_related_faqs(category, limit)
#     return [q for q, _ in pairs]

def _related_questions(category: str | None, limit: int = 3) -> List[str]:
    """Return related FAQ questions: prioritize Gemini for fresh questions, then fallback."""
    result = []
    
    print(f"🔍 DEBUG: _related_questions called with category='{category}'", flush=True)
    
    # Step 1: Try Gemini FIRST for fresh, relevant questions (avoid repetition)
    category_prompts = {
        'billing': 'customer billing, payments, subscriptions, invoices, and refunds',
        'technical': 'technical issues, errors, bugs, and troubleshooting',
        'account': 'user account management, profile settings, and security',
        'general': 'general customer support and common questions'
    }
    
    category_keyword = category.split()[0].lower() if category else 'general'
    topic = category_prompts.get(category_keyword, 'general customer support')
    
    gemini_questions = _generate_related_questions_online(
        query=f"Generate common customer questions about {topic}",
        category=category,
        limit=limit
    )
    
    # Add Gemini questions (with validation)
    for q in gemini_questions:
        if len(q) > 10 and '?' in q and len(result) < limit:
            result.append(q)
    print(f"🔍 DEBUG: Got {len(result)} questions from Gemini", flush=True)
    
    # Step 2: If Gemini didn't provide enough, try database
    if len(result) < limit:
        remaining = limit - len(result)
        pairs = _fetch_related_faqs(category, remaining)
        for q, _ in pairs:
            if q not in result and len(result) < limit:
                result.append(q)
        print(f"🔍 DEBUG: Added {len([q for q, _ in pairs if q in result])} questions from database", flush=True)
    
    # Step 3: If still not enough, use hardcoded fallback questions
    if len(result) < limit:
        fallback_questions = _get_fallback_questions(category)
        for q in fallback_questions:
            if q not in result and len(result) < limit:
                result.append(q)
        print(f"🔍 DEBUG: Added fallback questions, total now: {len(result)}", flush=True)
    
    print(f"🔍 DEBUG: _related_questions returning {len(result)} questions: {result}", flush=True)
    return result[:limit]  # Ensure we don't exceed limit


def _increment_failure_counter(session_id: str) -> int:
    redis = get_redis_client()
    key = f"fail:{session_id}"
    val = redis.incr(key)
    # set ttl for rolling window
    if val == 1:
        redis.expire(key, 900)
    return int(val)


def _reset_failure_counter(session_id: str) -> None:
    redis = get_redis_client()
    redis.delete(f"fail:{session_id}")


def _create_ticket(user_email: str, subject: str, description: str, category: str | None = None, customer_name: str | None = None, session_id: str | None = None, status: str = 'open') -> None:
    conn = get_postgres_connection(); cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO tickets (user_email, customer_name, subject, category, description, status, priority, session_id)
        VALUES (%s, %s, %s, %s, %s, %s, 'high', %s)
        """,
        (user_email, customer_name, subject, category, description, status, session_id),
    )
    conn.commit(); cur.close(); conn.close()


def _escalate_ticket(session_id: str | None, user_email: str, customer_name: str | None, subject: str | None, category: str | None, reason: str | None = None) -> None:
    """Escalate an existing open/in_progress ticket for the session or create one if missing."""
    if not session_id:
        return
    conn = get_postgres_connection(); cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE tickets 
            SET status = 'escalated', updated_at = NOW(), description = CONCAT(description, '\n\n[Escalated] ', %s)
            WHERE session_id = %s AND user_email = %s AND status IN ('open','in_progress')
            RETURNING id
            """,
            (reason or 'Manual escalation', session_id, user_email),
        )
        row = cur.fetchone()
        if not row:
            # create new escalated ticket
            ticket_subject = subject or (f"Escalation for {customer_name}" if customer_name else f"Escalation {session_id}")
            desc = (reason or 'Manual escalation triggered by user/admin').strip()
            _create_ticket(
                user_email=user_email,
                customer_name=customer_name,
                subject=ticket_subject,
                category=category,
                description=desc,
                status='escalated',
                session_id=session_id,
            )
        conn.commit()
    finally:
        cur.close(); conn.close()


def _is_resolution_confirmation(content: str) -> bool:
    """Check if user message indicates they're satisfied with the solution"""
    resolution_keywords = [
        'yes, resolved', 'that helps, thanks', 'resolved', 'solved', 'fixed', 
        'that works', 'perfect', 'thank you', 'thanks', 'great', 'awesome',
        'that answers it', 'that\'s what i needed', 'exactly what i needed',
        'problem solved', 'issue resolved', 'all set', 'good to go'
    ]
    content_lower = content.lower().strip()
    return any(keyword in content_lower for keyword in resolution_keywords)


def _should_suggest_resolution(answer: str, user_question: str) -> bool:
    """Determine if the answer is comprehensive enough to suggest resolution"""
    # Check if answer contains solution indicators
    solution_indicators = [
        'here\'s how', 'follow these steps', 'to fix this', 'solution is',
        'you need to', 'try this', 'do the following', 'here\'s what',
        'the issue is', 'this should resolve', 'this will fix'
    ]
    
    # Check if user question seems like a problem statement
    problem_indicators = [
        'how do i', 'how can i', 'why is', 'what\'s wrong', 'not working',
        'error', 'problem', 'issue', 'trouble', 'help', 'fix', 'solve'
    ]
    
    answer_lower = answer.lower()
    question_lower = user_question.lower()
    
    has_solution = any(indicator in answer_lower for indicator in solution_indicators)
    is_problem = any(indicator in question_lower for indicator in problem_indicators)
    
    # Suggest resolution if we have a solution for what seems like a problem
    return has_solution and is_problem and len(answer) > 50  # Substantial answer


def _schedule_auto_resolve(session_id: str, user_email: str, delay_seconds: int = 120) -> None:
    """Mark resolved after delay if no new user message arrives."""
    try:
        redis = get_redis_client()
        redis.setex(f"pending_resolve:{session_id}", delay_seconds + 5, "1")
        last_key = f"last_user:{session_id}"
        # Capture the timestamp snapshot
        last_seen = int(redis.get(last_key) or 0)

        async def _task():
            await asyncio.sleep(delay_seconds)
            r = get_redis_client()
            # Abort if user interacted or flag cleared
            flag = r.get(f"pending_resolve:{session_id}")
            current_last = int(r.get(last_key) or 0)
            if not flag or current_last > last_seen:
                return
            _mark_ticket_resolved(session_id, user_email)
            _store_chat(session_id, role="assistant", content="Marking this case as resolved due to inactivity. If you still need help, just reply and we'll reopen.")

        # Fire and forget; FastAPI + uvicorn allows background tasks via asyncio.create_task
        try:
            asyncio.get_event_loop().create_task(_task())
        except RuntimeError:
            # If no loop, run synchronously with a detached thread-like sleep (best effort)
            pass
    except Exception:
        # Non-blocking; if scheduling fails, do nothing
        pass


def _mark_ticket_resolved(session_id: str, user_email: str) -> None:
    """Mark the ticket as resolved for this session and generate summary"""
    conn = get_postgres_connection(); cur = conn.cursor()
    
    # Get conversation history for summary
    history = _load_chat_history(session_id)
    summary = _generate_resolution_summary(history)
    
    cur.execute(
        """
        UPDATE tickets 
        SET status = 'resolved', updated_at = NOW(), description = CONCAT(description, '\n\n--- RESOLUTION SUMMARY ---\n', %s)
        WHERE session_id = %s AND user_email = %s AND status IN ('open', 'escalated')
        """,
        (summary, session_id, user_email)
    )
    conn.commit(); cur.close(); conn.close()


def _generate_resolution_summary(history: List[Dict[str, str]]) -> str:
    """Generate a summary of how the issue was resolved"""
    if not history:
        return "Issue resolved - no conversation history available."
    
    # Extract key information
    user_messages = [h['content'] for h in history if h['role'] == 'user']
    assistant_messages = [h['content'] for h in history if h['role'] == 'assistant']
    
    if not user_messages or not assistant_messages:
        return "Issue resolved - limited conversation history."
    
    # Simple summary based on conversation flow
    initial_issue = user_messages[0] if user_messages else "Unknown issue"
    final_response = assistant_messages[-1] if assistant_messages else "No final response"
    
    summary = f"""
RESOLUTION SUMMARY:
- Initial Issue: {initial_issue[:100]}{'...' if len(initial_issue) > 100 else ''}
- Resolution Method: {'FAQ-based solution' if 'FAQ' in final_response else 'AI-generated solution'}
- Conversation Length: {len(history)} messages
- Resolution Time: {datetime.now().isoformat()}
- Customer Confirmed: Yes
"""
    return summary.strip()



def _get_fallback_questions(category: str | None) -> List[str]:
    """Return fallback questions when database has insufficient FAQs."""
    fallback_by_category = {
        "General": [
            "How do I reset my password?",
            "What are your business hours?",
            "How do I contact customer support?",
            "Where can I find my account settings?",
            "How do I update my profile information?"
        ],
        "Technical": [
            "Why is the website loading slowly?",
            "I'm getting an error message, what should I do?",
            "How do I enable two-factor authentication?",
            "The app keeps crashing, how can I fix it?",
            "Why can't I log in to my account?"
        ],
        "Billing": [
            "How do I update my payment method?",
            "When will I be charged for my subscription?",
            "How do I cancel my subscription?",
            "Can I get a refund?",
            "How do I download my invoice?"
        ],
        "Account": [
            "How do I delete my account?",
            "Can I change my email address?",
            "How do I export my data?",
            "What happens if I forget my username?",
            "How do I enable email notifications?"
        ]
    }
    
    # Normalize category name (handle "General Question" -> "General")
    normalized_category = None
    if category:
        # Extract first word and capitalize
        normalized_category = category.split()[0].capitalize()
    
    # Get category-specific questions or general ones
    if normalized_category and normalized_category in fallback_by_category:
        return fallback_by_category[normalized_category]
    
    # Return general questions as default
    return fallback_by_category["General"]


def _ensure_open_ticket(
    session_id: str | None,
    user_email: str,
    customer_name: str | None,
    subject: str | None,
    category: str | None,
    first_message: str | None,
) -> None:
    """Create an open ticket for this session if none exists yet.

    This ensures admin Tickets/Analytics reflect activity as soon as the user starts chatting.
    """
    if not session_id:
        return
    conn = get_postgres_connection(); cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id FROM tickets
            WHERE session_id = %s AND status IN ('open','in_progress','escalated')
            ORDER BY id DESC LIMIT 1
            """,
            (session_id,),
        )
        row = cur.fetchone()
        if row:
            return  # Ticket already open for this session

        # Create a new open ticket
        ticket_subject = subject or (f"Support request from {customer_name}" if customer_name else f"Support request {session_id}")
        description = (first_message or "").strip() or "User started a chat session."
        cur.execute(
            """
            INSERT INTO tickets (user_email, customer_name, subject, category, description, status, priority, session_id)
            VALUES (%s, %s, %s, %s, %s, 'open', 'medium', %s)
            """,
            (user_email, customer_name, ticket_subject, category, description, session_id),
        )
        conn.commit()
    finally:
        cur.close(); conn.close()

