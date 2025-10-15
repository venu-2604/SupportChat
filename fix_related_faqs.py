#!/usr/bin/env python3
"""
Fix related questions to show multiple FAQs instead of just one.
Run: python fix_related_faqs.py
"""

from pathlib import Path

def fix_related_faqs():
    chat_file = Path("backend/app/services/chat.py")
    
    if not chat_file.exists():
        print(f"❌ File not found: {chat_file}")
        return False
    
    content = chat_file.read_text(encoding='utf-8')
    
    # Find and replace the _fetch_related_faqs function
    old_function = '''def _fetch_related_faqs(category: str | None, limit: int = 3) -> List[Tuple[str, str]]:
    conn = get_postgres_connection(); cur = conn.cursor()
    if category:
        try:
            cur.execute("SELECT question, answer FROM faqs WHERE LOWER(question) LIKE %s ORDER BY id DESC LIMIT %s", (f"%{category.lower()}%", limit))
            rows = cur.fetchall()
        finally:
            cur.close(); conn.close()
        return [(r[0], r[1]) for r in rows]
    try:
        cur.execute("SELECT question, answer FROM faqs ORDER BY id DESC LIMIT %s", (limit,))
        rows = cur.fetchall()
    finally:
        cur.close(); conn.close()
    return [(r[0], r[1]) for r in rows]'''
    
    new_function = '''def _fetch_related_faqs(category: str | None, limit: int = 3) -> List[Tuple[str, str]]:
    conn = get_postgres_connection(); cur = conn.cursor()
    rows = []
    
    # Try category-based search first if category is provided
    if category:
        try:
            cur.execute("SELECT question, answer FROM faqs WHERE LOWER(question) LIKE %s ORDER BY id DESC LIMIT %s", (f"%{category.lower()}%", limit))
            rows = cur.fetchall()
        except Exception:
            pass
    
    # If no category or category search returned too few results, get latest FAQs
    if len(rows) < limit:
        try:
            cur.execute("SELECT question, answer FROM faqs ORDER BY id DESC LIMIT %s", (limit,))
            rows = cur.fetchall()
        except Exception:
            pass
    
    cur.close()
    conn.close()
    return [(r[0], r[1]) for r in rows]'''
    
    if old_function in content:
        content = content.replace(old_function, new_function)
        chat_file.write_text(content, encoding='utf-8')
        print("✅ Fixed _fetch_related_faqs function")
        print("✅ Now it will show 3 related questions instead of just 1")
        return True
    else:
        print("⚠️  Could not find the exact function to replace")
        print("The function may have already been modified")
        return False

if __name__ == "__main__":
    print("🔧 Fixing related questions feature...\n")
    
    if fix_related_faqs():
        print("\n" + "="*50)
        print("✅ Fix applied successfully!")
        print("\n📝 Next step:")
        print("Run: docker compose restart backend")
        print("\nThen test the chat - you should see 3 different related questions")
        print("="*50)
    else:
        print("\n⚠️  Manual fix required")