# #!/usr/bin/env python3
# """
# Diagnostic and seed script for FAQ database.
# This will check how many FAQs exist and add sample FAQs if needed.
# Run: python diagnose_and_seed_faqs.py
# """

# import psycopg2

# # Database connection settings (matching your docker-compose.yml)
# DB_CONFIG = {
#     'host': 'localhost',
#     'port': 5432,
#     'dbname': 'csupport',
#     'user': 'postgres',
#     'password': 'saniya9900'
# }

# # Sample FAQs across different categories
# SAMPLE_FAQS = [
#     # General Questions
#     ("How do I reset my password?", "To reset your password, click on 'Forgot Password' on the login page. Enter your email address and you'll receive a password reset link within 5 minutes."),
#     ("What are your business hours?", "Our customer support is available 24/7. For urgent issues, you can reach us anytime through this chat or email support@example.com."),
#     ("How do I contact customer support?", "You can contact us through this live chat, email us at support@example.com, or call us at 1-800-SUPPORT during business hours."),
#     ("Where can I find my account settings?", "Click on your profile icon in the top right corner, then select 'Account Settings' from the dropdown menu."),
#     ("How do I update my profile information?", "Go to Account Settings > Profile, make your changes, and click 'Save Changes' at the bottom of the page."),
    
#     # Technical Issues
#     ("Why is the website loading slowly?", "Slow loading can be caused by your internet connection, browser cache, or server load. Try clearing your browser cache, using a different browser, or checking your internet speed."),
#     ("I'm getting an error message, what should I do?", "Please take a screenshot of the error message and send it to our support team. In the meantime, try refreshing the page or clearing your browser cache."),
#     ("The app keeps crashing, how can I fix it?", "Try these steps: 1) Update the app to the latest version, 2) Clear app cache, 3) Restart your device, 4) Reinstall the app if the issue persists."),
#     ("How do I enable two-factor authentication?", "Go to Account Settings > Security > Two-Factor Authentication. Click 'Enable', scan the QR code with your authenticator app, and enter the verification code."),
#     ("Why can't I log in to my account?", "Common login issues: 1) Check if Caps Lock is on, 2) Verify your email/username is correct, 3) Reset your password if needed, 4) Clear browser cookies and try again."),
    
#     # Billing Questions
#     ("How do I update my payment method?", "Go to Account Settings > Billing > Payment Methods. Click 'Add Payment Method' or 'Edit' next to your existing method to update your card details."),
#     ("When will I be charged for my subscription?", "You'll be charged on the same day each billing cycle. You can view your next billing date in Account Settings > Billing > Subscription Details."),
#     ("How do I cancel my subscription?", "Go to Account Settings > Billing > Subscription. Click 'Cancel Subscription' and follow the prompts. Your access will continue until the end of your current billing period."),
#     ("Can I get a refund?", "Refunds are available within 30 days of purchase if you're not satisfied. Contact our billing team at billing@example.com with your order number."),
#     ("How do I download my invoice?", "Go to Account Settings > Billing > Invoices. Click the download icon next to any invoice to save it as a PDF."),
    
#     # Account Management
#     ("How do I delete my account?", "Go to Account Settings > Privacy > Delete Account. Please note this action is permanent and cannot be undone. All your data will be permanently deleted."),
#     ("Can I change my email address?", "Yes, go to Account Settings > Profile > Email Address. Enter your new email and verify it through the confirmation link we'll send you."),
#     ("How do I export my data?", "Go to Account Settings > Privacy > Data Export. Click 'Request Export' and you'll receive a download link via email within 24 hours."),
#     ("What happens if I forget my username?", "Click 'Forgot Username' on the login page and enter your email address. We'll send your username to your registered email."),
#     ("How do I enable email notifications?", "Go to Account Settings > Notifications. Toggle on the types of emails you want to receive and click 'Save Preferences'."),
# ]

# def diagnose_and_seed():
#     print("🔍 Diagnosing FAQ database...\n")
    
#     try:
#         # Connect to database
#         conn = psycopg2.connect(**DB_CONFIG)
#         cur = conn.cursor()
        
#         # Check current FAQ count
#         cur.execute("SELECT COUNT(*) FROM faqs")
#         count = cur.fetchone()[0]
#         print(f"📊 Current FAQ count: {count}")
        
#         # Get sample FAQs
#         cur.execute("SELECT question FROM faqs LIMIT 10")
#         existing = cur.fetchall()
#         if existing:
#             print(f"\n📝 Sample existing FAQs:")
#             for i, (q,) in enumerate(existing[:5], 1):
#                 print(f"   {i}. {q[:60]}...")
        
#         print(f"\n{'='*60}")
        
#         if count < 10:
#             print(f"⚠️  WARNING: Only {count} FAQ(s) found!")
#             print(f"   This is why you're only seeing 1 related question.")
#             print(f"\n💡 Solution: Adding {len(SAMPLE_FAQS)} sample FAQs...\n")
            
#             added = 0
#             for question, answer in SAMPLE_FAQS:
#                 try:
#                     # Check if FAQ already exists
#                     cur.execute("SELECT id FROM faqs WHERE question = %s", (question,))
#                     if cur.fetchone():
#                         print(f"   ⏭️  Skipped (exists): {question[:50]}...")
#                         continue
                    
#                     cur.execute(
#                         "INSERT INTO faqs (question, answer) VALUES (%s, %s)",
#                         (question, answer)
#                     )
#                     added += 1
#                     print(f"   ✅ Added: {question[:50]}...")
#                 except Exception as e:
#                     print(f"   ❌ Error adding FAQ: {e}")
            
#             conn.commit()
#             print(f"\n{'='*60}")
#             print(f"✅ Successfully added {added} new FAQs!")
            
#             # Verify new count
#             cur.execute("SELECT COUNT(*) FROM faqs")
#             new_count = cur.fetchone()[0]
#             print(f"📊 New FAQ count: {new_count}")
            
#         else:
#             print(f"✅ Good! You have {count} FAQs in the database.")
#             print(f"\n🔍 Checking FAQ diversity across categories...")
            
#             # Check FAQ diversity
#             cur.execute("""
#                 SELECT 
#                     CASE 
#                         WHEN LOWER(question) LIKE '%billing%' OR LOWER(question) LIKE '%payment%' OR LOWER(question) LIKE '%subscription%' THEN 'Billing'
#                         WHEN LOWER(question) LIKE '%technical%' OR LOWER(question) LIKE '%error%' OR LOWER(question) LIKE '%crash%' THEN 'Technical'
#                         WHEN LOWER(question) LIKE '%account%' OR LOWER(question) LIKE '%profile%' OR LOWER(question) LIKE '%settings%' THEN 'Account'
#                         ELSE 'General'
#                     END as category,
#                     COUNT(*) as count
#                 FROM faqs
#                 GROUP BY category
#             """)
#             categories = cur.fetchall()
#             print(f"\n📊 FAQ distribution by category:")
#             for cat, cnt in categories:
#                 print(f"   - {cat}: {cnt} FAQs")
        
#         cur.close()
#         conn.close()
        
#         print(f"\n{'='*60}")
#         print(f"✅ Diagnostic complete!")
#         print(f"\n📝 Next steps:")
#         print(f"   1. Restart your backend: docker compose restart backend")
#         print(f"   2. Test the chat - you should now see 3 related questions")
#         print(f"   3. If still seeing only 1, check browser console for errors")
#         print(f"{'='*60}")
        
#         return True
        
#     except psycopg2.OperationalError as e:
#         print(f"❌ Database connection error!")
#         print(f"   Error: {e}")
#         print(f"\n💡 Make sure:")
#         print(f"   1. Docker containers are running: docker compose ps")
#         print(f"   2. PostgreSQL is accessible on localhost:5432")
#         print(f"   3. Database credentials are correct")
#         return False
#     except Exception as e:
#         print(f"❌ Unexpected error: {e}")
#         return False

# if __name__ == "__main__":
#     print("🚀 FAQ Database Diagnostic & Seed Tool\n")
#     diagnose_and_seed()