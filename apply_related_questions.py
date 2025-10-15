#!/usr/bin/env python3
"""
Script to automatically add related questions feature to the chat system.
Run this from the project root: python apply_related_questions.py
"""

import re
from pathlib import Path

def update_backend():
    """Update backend/app/services/chat.py"""
    chat_file = Path("backend/app/services/chat.py")
    
    if not chat_file.exists():
        print(f"❌ File not found: {chat_file}")
        return False
    
    content = chat_file.read_text(encoding='utf-8')
    
    # 1. Add helper function after _fetch_related_faqs
    helper_function = '''

def _related_questions(category: str | None, limit: int = 3) -> List[str]:
    """Return only the related FAQ question titles for frontend suggestions."""
    pairs = _fetch_related_faqs(category, limit)
    return [q for q, _ in pairs]
'''
    
    # Find the position after _fetch_related_faqs function
    pattern = r'(def _fetch_related_faqs\(.*?\n(?:.*?\n)*?    return \[\(r\[0\], r\[1\]\) for r in rows\]\n\n)'
    match = re.search(pattern, content)
    
    if match:
        insert_pos = match.end()
        content = content[:insert_pos] + helper_function + content[insert_pos:]
        print("✅ Added _related_questions() helper function")
    else:
        print("⚠️  Could not find insertion point for helper function")
    
    # 2. Update all return statements to include "related" field
    replacements = [
        (
            r'return \{"session_id": session_id, "role": "assistant", "content": msg\}',
            'return {"session_id": session_id, "role": "assistant", "content": msg, "related": _related_questions(category)}'
        ),
        (
            r'return \{"session_id": session_id, "role": "assistant", "content": "Great! I\'ve marked your case as resolved\. Thank you for confirming!"\}',
            'return {"session_id": session_id, "role": "assistant", "content": "Great! I\'ve marked your case as resolved. Thank you for confirming!", "related": _related_questions(category)}'
        ),
        (
            r'return \{"session_id": session_id, "role": "assistant", "content": answer\}',
            'return {"session_id": session_id, "role": "assistant", "content": answer, "related": _related_questions(category)}'
        ),
        (
            r'return \{"session_id": session_id, "role": "assistant", "content": full_answer\}',
            'return {"session_id": session_id, "role": "assistant", "content": full_answer, "related": _related_questions(category)}'
        ),
        (
            r'return \{"session_id": session_id, "role": "assistant", "content": gemini_answer\}',
            'return {"session_id": session_id, "role": "assistant", "content": gemini_answer, "related": _related_questions(category)}'
        ),
        (
            r'return \{"session_id": session_id, "role": "assistant", "content": reply\}',
            'return {"session_id": session_id, "role": "assistant", "content": reply, "related": _related_questions(category)}'
        ),
    ]
    
    count = 0
    for pattern, replacement in replacements:
        new_content, n = re.subn(pattern, replacement, content)
        if n > 0:
            content = new_content
            count += n
    
    print(f"✅ Updated {count} return statements with 'related' field")
    
    # Write back
    chat_file.write_text(content, encoding='utf-8')
    print(f"✅ Backend file updated: {chat_file}")
    return True


def update_frontend():
    """Update frontend/src/pages/Chat.tsx"""
    chat_file = Path("frontend/src/pages/Chat.tsx")
    
    if not chat_file.exists():
        print(f"❌ File not found: {chat_file}")
        return False
    
    content = chat_file.read_text(encoding='utf-8')
    
    # 1. Update message type
    content = re.sub(
        r"type Msg = \{ role: 'user' \| 'assistant', content: string, showResolutionButtons\?: boolean \}",
        "type Msg = { role: 'user' | 'assistant', content: string, showResolutionButtons?: boolean, related?: string[] }",
        content
    )
    print("✅ Updated Msg type definition")
    
    # 2. Update bot_message handler
    old_handler = r"const onBot = \(msg: any\) => \{\s*const showButtons = msg\.content\.includes\('✅ Does this answer resolve your issue\?'\)\s*setMessages\(m => \[\.\.\. m, \{ role: 'assistant', content: msg\.content, showResolutionButtons: showButtons \}\]\)\s*\}"
    new_handler = """const onBot = (msg: any) => {
      const showButtons = msg.content.includes('✅ Does this answer resolve your issue?')
      const related = Array.isArray(msg.related) ? msg.related : []
      setMessages(m => [...m, { role: 'assistant', content: msg.content, showResolutionButtons: showButtons, related }])
    }"""
    
    content = re.sub(old_handler, new_handler, content, flags=re.DOTALL)
    print("✅ Updated bot_message handler")
    
    # 3. Add sendText helper after send function
    send_function_pattern = r"(const send = \(e\?: React\.FormEvent\) => \{[^}]+\}[^}]+\})"
    sendtext_function = """

  const sendText = (text: string) => {
    const t = text.trim()
    if (!t) return
    setMessages(m => [...m, { role: 'user', content: t }])
    socket.emit('chat_message', {
      session_id: sessionIdRef.current,
      content: t,
      user_email: prefill.email,
      customer_name: prefill.name,
      subject: prefill.subject,
      category: prefill.category,
    })
  }"""
    
    if 'const sendText' not in content:
        content = re.sub(send_function_pattern, r'\1' + sendtext_function, content)
        print("✅ Added sendText helper function")
    else:
        print("⚠️  sendText function already exists")
    
    # 4. Add related questions UI before showResolutionButtons
    related_ui = """                  {m.related && m.related.length > 0 && (
                    <div className="mt-3">
                      <div className="text-xs font-semibold text-gray-600 mb-2">Related questions:</div>
                      <div className="flex flex-wrap gap-2">
                        {m.related.map((q, idx) => (
                          <button
                            key={idx}
                            onClick={() => sendText(q)}
                            className="text-xs px-3 py-1.5 rounded-lg border bg-white border-gray-300 text-gray-700 hover:bg-gray-50 hover:border-blue-400 transition-colors"
                          >
                            {q}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
"""
    
    # Insert before showResolutionButtons
    if 'Related questions:' not in content:
        content = re.sub(
            r"(\s+)\{m\.showResolutionButtons &&",
            related_ui + r"\1{m.showResolutionButtons &&",
            content,
            count=1
        )
        print("✅ Added related questions UI")
    else:
        print("⚠️  Related questions UI already exists")
    
    # Write back
    chat_file.write_text(content, encoding='utf-8')
    print(f"✅ Frontend file updated: {chat_file}")
    return True


def main():
    print("🚀 Applying related questions feature...\n")
    
    backend_success = update_backend()
    print()
    frontend_success = update_frontend()
    
    print("\n" + "="*50)
    if backend_success and frontend_success:
        print("✅ All changes applied successfully!")
        print("\n📝 Next steps:")
        print("1. Restart your backend server")
        print("2. Restart your frontend dev server")
        print("3. Test the chat - you should see related question chips after AI responses")
    else:
        print("⚠️  Some changes could not be applied automatically")
        print("Please review the output above and apply remaining changes manually")
    print("="*50)


if __name__ == "__main__":
    main()