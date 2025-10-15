#!/usr/bin/env python3
"""
Fix related questions to always show 3 diverse FAQs.
Run: python fix_related_faqs_v2.py
"""

from pathlib import Path
import re

def fix_related_faqs():
    chat_file = Path("backend/app/services/chat.py")
    
    if not chat_file.exists():
        print(f"❌ File not found: {chat_file}")
        return False
    
    content = chat_file.read_text(encoding='utf-8')
    
    # Find the function and replace it
    pattern = r'def _fetch_related_faqs\(category: str \| None, limit: int = 3\) -> List\[Tuple\[str, str\]\]:.*?(?=\n\ndef |\nclass |\Z)'
    
    new_function = '''def _fetch_related_faqs(category: str | None, limit: int = 3) -> List[Tuple[str, str]]:
    conn = get_postgres_connection(); cur = conn.cursor()
    rows = []
    matched_ids = set()
    
    # Try category-based search first if category is provided
    if category:
        keyword = category.split()[0] if ' ' in category else category
        try:
            cur.execute("SELECT id, question, answer FROM faqs WHERE LOWER(question) LIKE %s ORDER BY id DESC LIMIT %s", (f"%{keyword.lower()}%", limit))
            category_rows = cur.fetchall()
            rows.extend([(r[1], r[2]) for r in category_rows])
            matched_ids.update([r[0] for r in category_rows])
        except Exception:
            pass
    
    # If we need more FAQs to reach the limit, get latest ones (excluding already matched)
    if len(rows) < limit:
        try:
            remaining = limit - len(rows)
            if matched_ids:
                placeholders = ','.join(['%s'] * len(matched_ids))
                cur.execute(f"SELECT question, answer FROM faqs WHERE id NOT IN ({placeholders}) ORDER BY id DESC LIMIT %s", (*matched_ids, remaining))
            else:
                cur.execute("SELECT question, answer FROM faqs ORDER BY id DESC LIMIT %s", (remaining,))
            additional_rows = cur.fetchall()
            rows.extend([(r[0], r[1]) for r in additional_rows])
        except Exception:
            pass
    
    cur.close()
    conn.close()
    return rows[:limit]  # Ensure we don't exceed limit
'''
    
    match = re.search(pattern, content, re.DOTALL)
    if match:
        content = content[:match.start()] + new_function + content[match.end():]
        chat_file.write_text(content, encoding='utf-8')
        print("✅ Fixed _fetch_related_faqs function")
        print("✅ Now it will always show 3 diverse related questions")
        return True
    else:
        print("⚠️  Could not find the function to replace")
        return False

if __name__ == "__main__":
    print("🔧 Fixing related questions to show 3 diverse FAQs...\n")
    
    if fix_related_faqs():
        print("\n" + "="*50)
        print("✅ Fix applied successfully!")
        print("\n📝 Next step:")
        print("Run: docker compose restart backend")
        print("\nNow you'll see 3 different questions every time!")
        print("="*50)
    else:
        print("\n⚠️  Manual fix required")