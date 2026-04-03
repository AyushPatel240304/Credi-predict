"""
Help Desk Blueprint for CrediPredict
Handles FAQ, Chatbot, and Ticket System
"""

from flask import Blueprint, render_template, request, jsonify
from database import get_connection
import os
import re
import random
import string
import requests
from datetime import datetime, timedelta

helpdesk = Blueprint('helpdesk', __name__)

# ─── Ticket ID Generator ───────────────────────────────────────────────────────

def generate_ticket_id():
    """Generate a real-world looking ticket ID like RIQ-2026-AB34X"""
    year = datetime.now().year
    letters = ''.join(random.choices(string.ascii_uppercase, k=2))
    numbers = ''.join(random.choices(string.digits, k=2))
    last = random.choice(string.ascii_uppercase)
    return f"RIQ-{year}-{letters}{numbers}{last}"

# ─── Email Validator ───────────────────────────────────────────────────────────

def is_valid_email(email):
    """Validate real-world email format"""
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False
    # Block fake/disposable domains
    blocked = ['test.com', 'fake.com', 'example.com', 'mailinator.com', 'tempmail.com']
    domain = email.split('@')[1].lower()
    if domain in blocked:
        return False
    return True

# ─── Rate Limit Check ──────────────────────────────────────────────────────────

def check_rate_limit(email):
    """Allow max 2 tickets per email per hour"""
    try:
        conn = get_connection()
        if not conn:
            return True  # Allow if DB fails
        cursor = conn.cursor()
        one_hour_ago = datetime.now() - timedelta(hours=1)
        cursor.execute("""
            SELECT COUNT(*) FROM ticket_rate_limit
            WHERE email = %s AND submitted_at >= %s
        """, (email, one_hour_ago))
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count < 2  # True = allowed
    except Exception as e:
        print(f"Rate limit check error: {e}")
        return True

def record_ticket_submission(email):
    """Record ticket submission for rate limiting"""
    try:
        conn = get_connection()
        if not conn:
            return
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ticket_rate_limit (email, submitted_at)
            VALUES (%s, %s)
        """, (email, datetime.now()))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Rate limit record error: {e}")

# ─── Default FAQs ─────────────────────────────────────────────────────────────

DEFAULT_FAQS = [
    {
        "question": "How does CrediPredict assess my credit eligibility?",
        "answer": "CrediPredict uses an ensemble of machine learning models trained on real credit data. It analyzes factors like your income, age, employment history, family size, assets, and education to calculate a risk probability score. Based on this score, it recommends Approved, Manual Review, or Rejected."
    },
    {
        "question": "What factors affect my credit assessment result?",
        "answer": "Key factors include: Annual income, Years of employment, Age, Number of dependents, Property and vehicle ownership, Education level, Family status, and Housing type. Stable employment and higher income generally improve your score."
    },
    {
        "question": "Is my personal data stored or shared?",
        "answer": "CrediPredict stores only anonymous financial features for model improvement purposes. No personally identifiable information like your name, phone number, or address is stored. Your data is never sold or shared with third parties."
    },
    {
        "question": "What does MANUAL REVIEW mean?",
        "answer": "Manual Review means your application has moderate risk factors that require additional human verification. It is neither fully approved nor rejected. You may need to provide additional documentation such as income proof, bank statements, or employment verification."
    },
    {
        "question": "How accurate is the assessment?",
        "answer": "Our ensemble model achieves approximately 91.9% accuracy. The model is deliberately conservative — it prioritizes catching high-risk applicants to protect lenders, which means some borderline cases may be flagged for review even if they are low risk."
    },
    {
        "question": "Can I reapply after being rejected?",
        "answer": "Yes. We recommend waiting at least 6 months and working on improving your financial profile — increasing income, building employment history, or acquiring assets. You can then reapply for a fresh assessment."
    },
    {
        "question": "What is the Bulk Assessment feature?",
        "answer": "Bulk Assessment is designed for bank employees and financial institutions. It allows uploading a CSV file with multiple applicant records and receiving instant risk assessments for all of them at once. Download our CSV template to format your data correctly."
    },
    {
        "question": "How do I track my support ticket?",
        "answer": "After submitting a ticket, you receive a unique Ticket ID (e.g. RIQ-2026-AB34X). To check your ticket status, go to Help Desk, click 'View Ticket Status', and enter your Ticket ID along with the email you used to submit it."
    }
]

# ─── Chatbot ──────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a helpful support assistant for CrediPredict, an AI-powered credit eligibility assessment platform.

CrediPredict helps individuals check their credit eligibility and allows bank employees to assess multiple applications via CSV upload.

You can ONLY answer questions related to:
- How credit assessment works
- What factors affect credit scores
- How to use the platform (single/batch prediction)
- Understanding assessment results (Approved, Manual Review, Rejected)
- How to submit and track support tickets
- Data privacy and security
- Technical issues with the platform

If someone asks anything unrelated to CrediPredict or credit assessment, politely decline and redirect them to relevant topics.

Keep answers concise, helpful, and professional. Do not reveal any internal system details, model architecture, database structure, API keys, or any sensitive project information."""


def get_chatbot_response(user_message):
    """Get chatbot response using Hugging Face API with rule-based fallback"""
    hf_token = os.getenv('HF_API_TOKEN')

    # Rule-based fallback responses
    rules = {
        ('hello', 'hi', 'hey', 'greet'): "Hello! I'm the CrediPredict support assistant. How can I help you today? You can ask me about credit assessments, your results, or how to submit a support ticket.",
        ('how does', 'how it work', 'what is credipredict', 'explain'): "CrediPredict uses an ensemble of ML models to assess credit eligibility. It analyzes income, employment, age, assets, and family details to give you an instant risk assessment — Approved, Manual Review, or Rejected.",
        ('factor', 'affect', 'influence', 'impact'): "Key factors include: income, employment years, age, children count, property/car ownership, education, family status, and housing type. Stable employment and higher income improve your chances.",
        ('reject', 'denied', 'not approved'): "A rejection means high risk was detected. We recommend improving your financial profile over 6 months — increase income, build employment history, or acquire assets — then reapply.",
        ('manual review', 'review mean', 'what is review'): "Manual Review means moderate risk was found. It's not a rejection — it means additional documentation may be needed like bank statements or employment verification.",
        ('data', 'privacy', 'store', 'safe', 'secure'): "CrediPredict stores only anonymous financial features for model improvement. No personal identity data is stored. Your information is never sold or shared.",
        ('batch', 'csv', 'bulk', 'multiple'): "The Bulk Assessment feature lets bank employees upload a CSV file to assess multiple applicants at once. Download our template from the Analytics page for the correct format.",
        ('ticket', 'support', 'help', 'issue', 'problem'): "You can submit a support ticket from this Help Desk page. Fill in your email, subject, and description. You'll get a unique Ticket ID to track your request.",
        ('track', 'status', 'check ticket'): "To check your ticket status, click 'View Ticket Status' on the Help Desk page and enter your Ticket ID and email address.",
        ('accurate', 'accuracy', 'reliable', 'trust'): "Our model achieves ~91.9% accuracy. It's deliberately conservative to protect lenders, so some borderline cases may get flagged for review.",
        ('reapply', 'try again', 'apply again'): "Yes, you can reapply after 6 months. Focus on improving your income, building longer employment history, and acquiring assets like property.",
        ('thank', 'thanks', 'appreciate'): "You're welcome! Feel free to ask if you have any other questions about CrediPredict.",
        ('bye', 'goodbye', 'see you'): "Goodbye! If you have more questions later, don't hesitate to come back. Good luck with your credit assessment!",
    }

    msg_lower = user_message.lower()
    for keywords, response in rules.items():
        if any(kw in msg_lower for kw in keywords):
            return response

    # Try Hugging Face API if token available
    if hf_token and hf_token != 'your_free_huggingface_token_here':
        try:
            prompt = f"{SYSTEM_PROMPT}\n\nUser: {user_message}\nAssistant:"
            response = requests.post(
                "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium",
                headers={"Authorization": f"Bearer {hf_token}"},
                json={"inputs": prompt[:500]},
                timeout=8
            )
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    text = result[0].get('generated_text', '').replace(prompt, '').strip()
                    if text and len(text) > 10:
                        return text
        except Exception as e:
            print(f"HF API error: {e}")

    # Default fallback
    return "I can help you with questions about CrediPredict — credit assessments, results, bulk uploads, tickets, and data privacy. Could you rephrase your question or ask something more specific?"


# ─── Routes ───────────────────────────────────────────────────────────────────

@helpdesk.route('/helpdesk')
def helpdesk_page():
    """Full helpdesk page"""
    faqs = get_faqs()
    return render_template('helpdesk.html', faqs=faqs)


@helpdesk.route('/api/helpdesk/faqs')
def get_faqs_api():
    """API to get FAQs"""
    return jsonify({'faqs': get_faqs()})


def get_faqs():
    """Get FAQs from DB or fallback to defaults"""
    try:
        conn = get_connection()
        if not conn:
            return DEFAULT_FAQS
        cursor = conn.cursor()
        cursor.execute("""
            SELECT question, answer FROM faqs
            WHERE is_active = TRUE
            ORDER BY display_order ASC, id ASC
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        if rows:
            return [{'question': r[0], 'answer': r[1]} for r in rows]
        return DEFAULT_FAQS
    except Exception:
        return DEFAULT_FAQS


@helpdesk.route('/api/helpdesk/chat', methods=['POST'])
def chat():
    """Chatbot endpoint"""
    data = request.get_json()
    if not data or not data.get('message'):
        return jsonify({'error': 'No message provided'}), 400
    user_message = data['message'].strip()
    if len(user_message) > 500:
        return jsonify({'error': 'Message too long'}), 400
    response = get_chatbot_response(user_message)
    return jsonify({'response': response})


@helpdesk.route('/api/helpdesk/submit_ticket', methods=['POST'])
def submit_ticket():
    """Submit a new support ticket"""
    data = request.get_json()

    email = data.get('email', '').strip()
    subject = data.get('subject', '').strip()
    description = data.get('description', '').strip()

    # Validate fields
    if not email or not subject or not description:
        return jsonify({'success': False, 'error': 'All fields are required'}), 400

    if not is_valid_email(email):
        return jsonify({'success': False, 'error': 'Please enter a valid email address'}), 400

    if len(subject) < 5:
        return jsonify({'success': False, 'error': 'Subject must be at least 5 characters'}), 400

    if len(description) < 20:
        return jsonify({'success': False, 'error': 'Description must be at least 20 characters'}), 400

    # Rate limit check
    if not check_rate_limit(email):
        return jsonify({'success': False, 'error': 'You can only submit 2 tickets per hour. Please wait before submitting again.'}), 429

    try:
        conn = get_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        cursor = conn.cursor()

        # Generate unique ticket ID
        ticket_id = generate_ticket_id()
        # Ensure uniqueness
        for _ in range(5):
            cursor.execute("SELECT id FROM tickets WHERE ticket_id = %s", (ticket_id,))
            if not cursor.fetchone():
                break
            ticket_id = generate_ticket_id()

        cursor.execute("""
            INSERT INTO tickets (ticket_id, email, subject, description, status)
            VALUES (%s, %s, %s, %s, 'Open')
        """, (ticket_id, email, subject, description))

        record_ticket_submission(email)
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'ticket_id': ticket_id,
            'message': f'Ticket submitted successfully! Your Ticket ID is {ticket_id}'
        })

    except Exception as e:
        print(f"Ticket submission error: {e}")
        return jsonify({'success': False, 'error': 'Failed to submit ticket. Please try again.'}), 500


@helpdesk.route('/api/helpdesk/view_ticket', methods=['POST'])
def view_ticket():
    """View ticket status by ID and email"""
    data = request.get_json()

    ticket_id = data.get('ticket_id', '').strip().upper()
    email = data.get('email', '').strip()

    if not ticket_id or not email:
        return jsonify({'success': False, 'error': 'Ticket ID and email are required'}), 400

    if not is_valid_email(email):
        return jsonify({'success': False, 'error': 'Please enter a valid email address'}), 400

    try:
        conn = get_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        cursor.execute("""
            SELECT ticket_id, subject, description, status, admin_reply, created_at, updated_at
            FROM tickets
            WHERE ticket_id = %s AND email = %s
        """, (ticket_id, email))

        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            return jsonify({'success': False, 'error': 'No ticket found with this ID and email combination'}), 404

        return jsonify({
            'success': True,
            'ticket': {
                'ticket_id': row[0],
                'subject': row[1],
                'description': row[2],
                'status': row[3],
                'admin_reply': row[4],
                'created_at': row[5].strftime('%d %b %Y, %I:%M %p') if row[5] else None,
                'updated_at': row[6].strftime('%d %b %Y, %I:%M %p') if row[6] else None,
            }
        })

    except Exception as e:
        print(f"View ticket error: {e}")
        return jsonify({'success': False, 'error': 'Failed to fetch ticket. Please try again.'}), 500