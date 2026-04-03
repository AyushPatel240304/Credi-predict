"""
Admin Blueprint for CrediPredict
Secure admin panel with brute force protection
Hidden URL: /xK9mP2-dashboard/auth
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from database import get_connection
from functools import wraps
import os
import hashlib
from datetime import datetime, timedelta

admin = Blueprint('admin', __name__, url_prefix='/xK9mP2-dashboard')

ADMIN_URL_PREFIX = '/xK9mP2-dashboard'
MAX_ATTEMPTS = 3
LOCKOUT_MINUTES = 30
SESSION_TIMEOUT_HOURS = 2

# ── Security Helpers ───────────────────────────────────────────────────────────

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_client_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr)

def is_locked_out(ip):
    try:
        conn = get_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        lockout_time = datetime.now() - timedelta(minutes=LOCKOUT_MINUTES)
        cursor.execute("""
            SELECT COUNT(*) FROM admin_login_attempts
            WHERE ip_address = %s AND attempted_at >= %s AND success = FALSE
        """, (ip, lockout_time))
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count >= MAX_ATTEMPTS
    except:
        return False

def record_login_attempt(ip, success):
    try:
        conn = get_connection()
        if not conn:
            return
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO admin_login_attempts (ip_address, success, attempted_at)
            VALUES (%s, %s, %s)
        """, (ip, success, datetime.now()))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Login attempt record error: {e}")

def clear_login_attempts(ip):
    try:
        conn = get_connection()
        if not conn:
            return
        cursor = conn.cursor()
        cursor.execute("DELETE FROM admin_login_attempts WHERE ip_address = %s", (ip,))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Clear attempts error: {e}")

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin.login'))
        # Session timeout check
        last_active = session.get('last_active')
        if last_active:
            last_active_dt = datetime.fromisoformat(last_active)
            if datetime.now() - last_active_dt > timedelta(hours=SESSION_TIMEOUT_HOURS):
                session.clear()
                flash('Session expired. Please login again.', 'warning')
                return redirect(url_for('admin.login'))
        session['last_active'] = datetime.now().isoformat()
        return f(*args, **kwargs)
    return decorated

# ── Auth Routes ────────────────────────────────────────────────────────────────

@admin.route('/auth', methods=['GET', 'POST'])
def login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        ip = get_client_ip()

        if is_locked_out(ip):
            flash(f'Too many failed attempts. Try again after {LOCKOUT_MINUTES} minutes.', 'danger')
            return render_template('admin_login.html')

        admin_username = os.getenv('ADMIN_USERNAME', 'admin')
        admin_password = os.getenv('ADMIN_PASSWORD', '')

        if username == admin_username and password == admin_password:
            record_login_attempt(ip, True)
            clear_login_attempts(ip)
            session['admin_logged_in'] = True
            session['admin_username'] = username
            session['last_active'] = datetime.now().isoformat()
            session.permanent = True
            return redirect(url_for('admin.dashboard'))
        else:
            record_login_attempt(ip, False)
            # Count remaining attempts
            try:
                conn = get_connection()
                cursor = conn.cursor()
                lockout_time = datetime.now() - timedelta(minutes=LOCKOUT_MINUTES)
                cursor.execute("""
                    SELECT COUNT(*) FROM admin_login_attempts
                    WHERE ip_address = %s AND attempted_at >= %s AND success = FALSE
                """, (ip, lockout_time))
                count = cursor.fetchone()[0]
                cursor.close()
                conn.close()
                remaining = MAX_ATTEMPTS - count
                if remaining <= 0:
                    flash(f'Account locked for {LOCKOUT_MINUTES} minutes due to too many failed attempts.', 'danger')
                else:
                    flash(f'Invalid credentials. {remaining} attempt(s) remaining.', 'danger')
            except:
                flash('Invalid credentials.', 'danger')

    return render_template('admin_login.html')


@admin.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin.login'))


# ── Dashboard ──────────────────────────────────────────────────────────────────

@admin.route('/dashboard')
@admin_required
def dashboard():
    stats = get_dashboard_stats()
    return render_template('admin_dashboard.html', stats=stats)


@admin.route('/api/chart-data')
@admin_required
def chart_data():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Predictions over last 7 days
        cursor.execute("""
            SELECT DATE(created_at) as day, COUNT(*) as count
            FROM individual_predictions
            WHERE created_at >= NOW() - INTERVAL '7 days'
            GROUP BY day ORDER BY day
        """)
        individual_by_day = cursor.fetchall()

        cursor.execute("""
            SELECT DATE(created_at) as day, COUNT(*) as count
            FROM batch_jobs
            WHERE created_at >= NOW() - INTERVAL '7 days'
            GROUP BY day ORDER BY day
        """)
        batch_by_day = cursor.fetchall()

        # Approved vs Rejected
        cursor.execute("""
            SELECT decision, COUNT(*) FROM individual_predictions GROUP BY decision
        """)
        individual_decisions = dict(cursor.fetchall())

        cursor.execute("""
            SELECT decision, COUNT(*) FROM batch_predictions GROUP BY decision
        """)
        batch_decisions = dict(cursor.fetchall())

        # Ticket status breakdown
        cursor.execute("""
            SELECT status, COUNT(*) FROM tickets GROUP BY status
        """)
        ticket_status = dict(cursor.fetchall())

        cursor.close()
        conn.close()

        # Build 7-day labels
        from datetime import date, timedelta
        days = [(date.today() - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
        ind_map = {str(r[0]): r[1] for r in individual_by_day}
        batch_map = {str(r[0]): r[1] for r in batch_by_day}

        return jsonify({
            'predictions_trend': {
                'labels': days,
                'individual': [ind_map.get(d, 0) for d in days],
                'batch': [batch_map.get(d, 0) for d in days]
            },
            'individual_decisions': {
                'approved': individual_decisions.get('APPROVED', 0),
                'rejected': individual_decisions.get('REJECTED', 0),
                'review': individual_decisions.get('MANUAL REVIEW', 0)
            },
            'batch_decisions': {
                'approved': batch_decisions.get('APPROVED', 0),
                'rejected': batch_decisions.get('REJECTED', 0),
                'review': batch_decisions.get('MANUAL REVIEW', 0)
            },
            'ticket_status': {
                'open': ticket_status.get('Open', 0),
                'in_progress': ticket_status.get('In Progress', 0),
                'resolved': ticket_status.get('Resolved', 0)
            }
        })
    except Exception as e:
        print(f"Chart data error: {e}")
        return jsonify({'error': str(e)}), 500


def get_dashboard_stats():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Individual predictions total
        cursor.execute("SELECT COUNT(*) FROM individual_predictions")
        total_individual = cursor.fetchone()[0]

        # Batch predictions total (sum of all batch job records)
        cursor.execute("SELECT COALESCE(SUM(total_records), 0) FROM batch_jobs")
        total_batch = cursor.fetchone()[0]

        # Today individual
        cursor.execute("SELECT COUNT(*) FROM individual_predictions WHERE DATE(created_at) = CURRENT_DATE")
        today_individual = cursor.fetchone()[0]

        # Today batch
        cursor.execute("SELECT COALESCE(SUM(total_records), 0) FROM batch_jobs WHERE DATE(created_at) = CURRENT_DATE")
        today_batch = cursor.fetchone()[0]

        # Tickets
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'Open'")
        open_tickets = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'Resolved'")
        resolved_tickets = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tickets")
        total_tickets = cursor.fetchone()[0]

        # Approved vs Rejected (individual)
        cursor.execute("SELECT COUNT(*) FROM individual_predictions WHERE decision = 'APPROVED'")
        approved_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM individual_predictions WHERE decision = 'REJECTED'")
        rejected_count = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return {
            'total_individual': total_individual,
            'total_batch': total_batch,
            'today_individual': today_individual,
            'today_batch': today_batch,
            'open_tickets': open_tickets,
            'resolved_tickets': resolved_tickets,
            'total_tickets': total_tickets,
            'approved_count': approved_count,
            'rejected_count': rejected_count
        }
    except Exception as e:
        print(f"Dashboard stats error: {e}")
        return {
            'total_individual': 0, 'total_batch': 0,
            'today_individual': 0, 'today_batch': 0,
            'open_tickets': 0, 'resolved_tickets': 0,
            'total_tickets': 0, 'approved_count': 0, 'rejected_count': 0
        }


# ── Tickets Management ─────────────────────────────────────────────────────────

@admin.route('/tickets')
@admin_required
def tickets():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ticket_id, email, subject, status, created_at, updated_at
            FROM tickets ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        tickets_list = [{
            'ticket_id': r[0], 'email': r[1], 'subject': r[2],
            'status': r[3],
            'created_at': r[4].strftime('%d %b %Y, %I:%M %p') if r[4] else '',
            'updated_at': r[5].strftime('%d %b %Y, %I:%M %p') if r[5] else ''
        } for r in rows]
        return render_template('admin_tickets.html', tickets=tickets_list)
    except Exception as e:
        flash(f'Error loading tickets: {e}', 'danger')
        return render_template('admin_tickets.html', tickets=[])


@admin.route('/api/ticket/<ticket_id>', methods=['GET'])
@admin_required
def get_ticket(ticket_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ticket_id, email, subject, description, status, admin_reply, created_at
            FROM tickets WHERE ticket_id = %s
        """, (ticket_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if not row:
            return jsonify({'error': 'Ticket not found'}), 404
        return jsonify({
            'ticket_id': row[0], 'email': row[1], 'subject': row[2],
            'description': row[3], 'status': row[4], 'admin_reply': row[5],
            'created_at': row[6].strftime('%d %b %Y, %I:%M %p') if row[6] else ''
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin.route('/api/ticket/<ticket_id>/update', methods=['POST'])
@admin_required
def update_ticket(ticket_id):
    try:
        data = request.get_json()
        status = data.get('status')
        admin_reply = data.get('admin_reply', '')

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tickets
            SET status = %s, admin_reply = %s, updated_at = %s
            WHERE ticket_id = %s
        """, (status, admin_reply, datetime.now(), ticket_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'message': 'Ticket updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Predictions ────────────────────────────────────────────────────────────────

@admin.route('/predictions')
@admin_required
def predictions():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, code_gender, amt_income_total, age_years, employed_years,
                   risk_probability, risk_level, decision, created_at
            FROM individual_predictions
            ORDER BY created_at DESC LIMIT 100
        """)
        individual = cursor.fetchall()

        cursor.execute("""
            SELECT id, total_records, approved_count, rejected_count, review_count, created_at
            FROM batch_jobs ORDER BY created_at DESC LIMIT 50
        """)
        batches = cursor.fetchall()

        cursor.close()
        conn.close()

        individual_list = [{
            'id': r[0], 'gender': r[1], 'income': f"${r[2]:,.0f}",
            'age': r[3], 'employed_years': r[4],
            'risk_probability': r[5], 'risk_level': r[6],
            'decision': r[7],
            'created_at': r[8].strftime('%d %b %Y, %I:%M %p') if r[8] else ''
        } for r in individual]

        batch_list = [{
            'id': r[0], 'total': r[1], 'approved': r[2],
            'rejected': r[3], 'review': r[4],
            'created_at': r[5].strftime('%d %b %Y, %I:%M %p') if r[5] else ''
        } for r in batches]

        return render_template('admin_predictions.html',
                               individual=individual_list, batches=batch_list)
    except Exception as e:
        flash(f'Error loading predictions: {e}', 'danger')
        return render_template('admin_predictions.html', individual=[], batches=[])