#!/usr/bin/env python3
"""
Test the related questions function directly.
Run: python test_related_questions.py
"""

import psycopg2

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'csupport',
    'user': 'postgres',
    'password': 'saniya9900'
}

def test_fetch_related_faqs(category=None, limit=3):
    """Test the _fetch_related_faqs function"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    rows = []
    matched_ids = set()
    
    print(f"🔍 Testing with category='{category}', limit={limit}\n")
    
    # Try category-based search first if category is provided
    if category:
        keyword = category.split()[0] if ' ' in category else category
        print(f"📝 Searching for keyword: '{keyword}'")
        try:
            query = "SELECT id, question, answer FROM faqs WHERE LOWER(question) LIKE %s ORDER BY id DESC LIMIT %s"
            cur.execute(query, (f"%{keyword.lower()}%", limit))
            category_rows = cur.fetchall()
            print(f"   Found {len(category_rows)} category matches")
            rows.extend([(r[1], r[2]) for r in category_rows])
            matched_ids.update([r[0] for r in category_rows])
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # If we need more FAQs to reach the limit, get latest ones
    if len(rows) < limit:
        print(f"\n📝 Need {limit - len(rows)} more FAQs, fetching latest...")
        try:
            remaining = limit - len(rows)
            if matched_ids:
                placeholders = ','.join(['%s'] * len(matched_ids))
                query = f"SELECT question, answer FROM faqs WHERE id NOT IN ({placeholders}) ORDER BY id DESC LIMIT %s"
                cur.execute(query, (*matched_ids, remaining))
            else:
                query = "SELECT question, answer FROM faqs ORDER BY id DESC LIMIT %s"
                cur.execute(query, (remaining,))
            additional_rows = cur.fetchall()
            print(f"   Found {len(additional_rows)} additional FAQs")
            rows.extend([(r[0], r[1]) for r in additional_rows])
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    cur.close()
    conn.close()
    
    result = rows[:limit]
    
    print(f"\n{'='*60}")
    print(f"✅ Total FAQs returned: {len(result)}")
    print(f"\n📋 Related Questions:")
    for i, (q, a) in enumerate(result, 1):
        print(f"   {i}. {q}")
    print(f"{'='*60}")
    
    return [q for q, _ in result]

if __name__ == "__main__":
    print("🚀 Testing Related Questions Function\n")
    
    # Test with different categories
    print("\n" + "="*60)
    print("Test 1: General Question category")
    print("="*60)
    test_fetch_related_faqs("General Question", 3)
    
    print("\n" + "="*60)
    print("Test 2: Technical category")
    print("="*60)
    test_fetch_related_faqs("Technical", 3)
    
    print("\n" + "="*60)
    print("Test 3: Billing category")
    print("="*60)
    test_fetch_related_faqs("Billing", 3)
    
    print("\n" + "="*60)
    print("Test 4: No category (should return latest 3)")
    print("="*60)
    test_fetch_related_faqs(None, 3)