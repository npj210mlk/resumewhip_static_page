# Final - Professional UI Version
import os
import sqlite3
import re
import gradio as gr
import stripe
import pdfplumber
import uuid
import json
import threading
import uvicorn

from dotenv import load_dotenv
from datetime import datetime
from new_functions import (
    extract_resume_text,
    sanitize_input,
    prompt_creator,
    career_pivot_prompt_creator,
    get_resume_response,
    process_resume,
    export_resume,
    cover_letter_prompt_creator,
    get_cover_response,
    save_cover_letter,
    is_posting_recent,
    template_detector,
    mentioned_on_socials,
    detect_urgency_language
)

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse

load_dotenv()

# Professional Modern CSS Theme
custom_css = """
/* ============================================
   PROFESSIONAL MODERN TECH STARTUP THEME
   ============================================ */

:root {
    --primary: #6366f1;           /* Indigo - primary actions */
    --primary-hover: #4f46e5;
    --secondary: #8b5cf6;          /* Purple - secondary elements */
    --accent: #34d399;             /* Softer emerald - success/premium */
    --accent-hover: #10b981;
    --accent-light: #6ee7b7;       /* Light emerald for gradients */
    --warning: #f59e0b;            /* Amber - alerts */
    --danger: #ef4444;             /* Red - errors */
    --text-primary: #1f2937;       /* Dark gray */
    --text-secondary: #6b7280;     /* Medium gray */
    --bg-primary: #ffffff;
    --bg-secondary: #f9fafb;
    --bg-tertiary: #f3f4f6;
    --border: #e5e7eb;
    --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.1);
    --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
    --shadow-lg: 0 10px 25px rgba(0, 0, 0, 0.15);
}

/* Reset and Base */
* {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

body {
    background: var(--bg-secondary);
    color: var(--text-primary);
}

/* ============================================
   HEADER & BRANDING
   ============================================ */

.header-container {
    background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
    padding: 40px 20px;
    border-radius: 16px;
    margin-bottom: 30px;
    box-shadow: var(--shadow-lg);
}

.header-container h1 {
    color: white;
    font-size: 2.5em;
    font-weight: 800;
    margin: 0 0 10px 0;
    text-align: center;
}

.header-container h2 {
    color: rgba(255, 255, 255, 0.95);
    font-size: 1.3em;
    font-weight: 500;
    margin: 0;
    text-align: center;
}

.header-container h3 {
    color: rgba(255, 255, 255, 0.85);
    font-size: 1.1em;
    font-weight: 400;
    margin: 15px 0 0 0;
    text-align: center;
}

/* ============================================
   TAB NAVIGATION - PROFESSIONAL STYLE
   ============================================ */

.tab-nav {
    display: flex;
    justify-content: center;
    margin: 30px 0;
    background: var(--bg-primary);
    border-radius: 12px;
    padding: 6px;
    box-shadow: var(--shadow-md);
    gap: 8px;
}

.tab-nav button {
    background: transparent;
    color: var(--text-secondary);
    font-weight: 600;
    font-size: 1em;
    border-radius: 8px;
    padding: 14px 24px;
    border: none;
    cursor: pointer;
    transition: all 0.2s ease;
    flex: 1;
    max-width: 220px;
}

.tab-nav button:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
}

.tab-nav button.selected {
    background: linear-gradient(135deg, var(--primary), var(--secondary));
    color: white;
    box-shadow: var(--shadow-md);
}

/* ============================================
   BUTTONS - CLEAN HIERARCHY
   ============================================ */

button[variant="primary"], .primary-btn {
    background: linear-gradient(135deg, var(--primary), var(--secondary)) !important;
    color: white !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 14px 28px !important;
    font-size: 1.05em !important;
    transition: all 0.3s ease !important;
    box-shadow: var(--shadow-md) !important;
}

button[variant="primary"]:hover, .primary-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: var(--shadow-lg) !important;
}

button[variant="secondary"], .secondary-btn {
    background: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    font-weight: 500 !important;
    border: 2px solid var(--border) !important;
    border-radius: 10px !important;
    padding: 12px 24px !important;
    transition: all 0.2s ease !important;
}

button[variant="secondary"]:hover {
    border-color: var(--primary) !important;
    color: var(--primary) !important;
}

/* Download/Export Buttons - Success Style */
.download-btn {
    background: linear-gradient(135deg, var(--accent-light) 0%, var(--accent) 50%, var(--accent-hover) 100%) !important;
    color: white !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 14px 28px !important;
    font-size: 1.05em !important;
    transition: all 0.3s ease !important;
    box-shadow: var(--shadow-md) !important;
}

.download-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 20px rgba(52, 211, 153, 0.4) !important;
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent-hover) 50%, #059669 100%) !important;
}

/* ============================================
   SIDEBAR - CLEAN & FOCUSED
   ============================================ */

.sidebar-container {
    background: var(--bg-primary);
    border-radius: 12px;
    padding: 24px;
    box-shadow: var(--shadow-sm);
}

.status-badge {
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent-hover) 100%);
    color: white;
    padding: 16px;
    border-radius: 10px;
    text-align: center;
    font-weight: 600;
    font-size: 1.1em;
    margin-bottom: 20px;
    box-shadow: var(--shadow-sm);
}

.status-badge.premium {
    background: linear-gradient(135deg, var(--accent-light) 0%, var(--accent) 50%, var(--accent-hover) 100%);
    box-shadow: 0 4px 12px rgba(52, 211, 153, 0.3);
}

.status-badge.free {
    background: linear-gradient(135deg, var(--warning) 0%, #d97706 100%);
}

/* ============================================
   INPUT FIELDS - PROFESSIONAL STYLE
   ============================================ */

#email-box input {
    border: 2px solid var(--primary) !important;
    background-color: var(--bg-primary) !important;
    font-size: 1.05em !important;
    padding: 12px !important;
    border-radius: 8px !important;
    transition: all 0.2s ease !important;
}

#email-box input:focus {
    border-color: var(--secondary) !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1) !important;
}

#email-box label {
    color: var(--text-primary) !important;
    font-size: 1em !important;
    font-weight: 600 !important;
}

/* ============================================
   CARDS & CONTAINERS
   ============================================ */

.info-card {
    background: var(--bg-primary);
    border-radius: 12px;
    padding: 20px;
    margin: 15px 0;
    border: 1px solid var(--border);
    box-shadow: var(--shadow-sm);
}

.tip-box {
    background: linear-gradient(135deg, #dbeafe 0%, #e0e7ff 100%);
    border-left: 4px solid var(--primary);
    padding: 16px 20px;
    border-radius: 8px;
    margin: 20px 0;
    color: var(--text-primary);
}

/* ============================================
   PREMIUM INDICATORS
   ============================================ */

.premium-badge {
    background: linear-gradient(135deg, var(--accent-light), var(--accent) 50%, var(--accent-hover));
    color: white;
    padding: 12px 20px;
    border-radius: 25px;
    font-weight: 600;
    text-align: center;
    box-shadow: 0 4px 12px rgba(52, 211, 153, 0.3);
    display: inline-block;
}

.upgrade-cta {
    background: linear-gradient(135deg, var(--warning) 0%, #d97706 100%);
    color: white;
    padding: 16px 24px;
    border-radius: 12px;
    text-align: center;
    font-weight: 600;
    font-size: 1.05em;
    text-decoration: none;
    display: block;
    margin: 20px 0;
    box-shadow: var(--shadow-md);
    transition: all 0.3s ease;
}

.upgrade-cta:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-lg);
}

/* ============================================
   ACCORDIONS
   ============================================ */

.accordion-header {
    background: var(--bg-tertiary);
    border-radius: 8px;
    padding: 12px 16px;
    font-weight: 600;
    color: var(--text-primary);
}

/* ============================================
   FOOTER
   ============================================ */

footer {
    margin-top: 60px;
    padding: 40px 20px;
    border-top: 1px solid var(--border);
    background: var(--bg-primary);
    border-radius: 12px;
}

footer a {
    color: var(--primary);
    text-decoration: none;
    font-weight: 500;
    transition: color 0.2s ease;
}

footer a:hover {
    color: var(--secondary);
}

/* ============================================
   RESPONSIVE DESIGN
   ============================================ */

@media (max-width: 768px) {
    .tab-nav {
        flex-direction: column;
    }
    
    .tab-nav button {
        max-width: 100%;
    }
    
    .header-container h1 {
        font-size: 2em;
    }
}

/* Hide upgrade elements for premium users */
body[data-user-status="premium"] .upgrade-cta,
body[data-user-status="premium"] .upgrade-prompt {
    display: none !important;
}
"""

# Environment variables
DATABASE_PATH = os.getenv("DATABASE_PATH", "resumewhip.db")
ADMIN_INCOGNITO = os.getenv("ADMIN_INCOGNITO", "change_this_secret_key")

thread_local = threading.local()

def get_db_connection():
    render_path = "/var/data/resumewhip.db"
    local_path = "resumewhip.db"
    db_path = render_path if os.path.exists("/var/data") else local_path
    
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

# Stripe setup
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
PRICE_ID = os.getenv("PRICE_ID")

fastapi_app = FastAPI()

@fastapi_app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@fastapi_app.post("/webhook")
async def stripe_webhook(request: Request):
    try:
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")

        if not sig_header or not WEBHOOK_SECRET:
            raise HTTPException(status_code=400, detail="Missing signature or webhook secret")

        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            user_id = session.get("client_reference_id")
            customer_id = session.get("customer")
            
            if user_id and customer_id:
                store_stripe_customer_id(user_id, customer_id)
                grant_unlimited_access(user_id)
        
        elif event["type"] == "invoice.payment_succeeded":
            invoice = event["data"]["object"]
            customer_id = invoice["customer"]
            user_id = get_user_id_by_customer_id(customer_id)
            if user_id:
                grant_unlimited_access(user_id)

        elif event["type"] == "invoice.payment_failed":
            invoice = event["data"]["object"]
            customer_id = invoice["customer"]
            user_id = get_user_id_by_customer_id(customer_id)
            if user_id:
                print(f"⚠️ Payment failed for user: {user_id}")

        elif event["type"] == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            customer_id = subscription["customer"]
            user_id = get_user_id_by_customer_id(customer_id)
            if user_id:
                revoke_unlimited_access(user_id)

        return JSONResponse(content={"status": "success"}, status_code=200)

    except Exception as e:
        print(f"🚨 Webhook error: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=400)

user_sessions = {}
FREE_CREDITS = 3

def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            subscription_status TEXT DEFAULT 'free',
            credits_remaining INTEGER DEFAULT 3,
            stripe_customer_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_payment_date TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ip_usage (
            ip TEXT NOT NULL,
            date TEXT NOT NULL,
            count INTEGER DEFAULT 0,
            PRIMARY KEY (ip, date)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_or_create_user(email: str):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, credits_remaining, subscription_status FROM users WHERE email = ?",
            (email,)
        )
        row = cursor.fetchone()

        if row:
            user_id, credits, status = row
        else:
            user_id = str(uuid.uuid4())
            credits = 3
            status = "free"
            cursor.execute(
                "INSERT INTO users (user_id, email, credits_remaining, subscription_status) VALUES (?, ?, ?, ?)",
                (user_id, email, credits, status)
            )
            conn.commit()
        
        return user_id, credits, status
    
    except sqlite3.Error as db_error:
        print(f"🚨 Database error: {db_error}")
        if conn:
            conn.rollback()
        return str(uuid.uuid4()), 0, "free"
    
    finally:
        if conn:
            conn.close()

def ensure_user_logged(email):
    if not email or not email.strip():
        raise ValueError("Email required.")
    return get_or_create_user(email)

def get_user_status(email):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, subscription_status, credits_remaining FROM users WHERE email = ?", 
            (email,)
        )
        row = cursor.fetchone()

        if not row:
            return "As a free user, you have 3 complimentary resume optimizations"
    
        user_id, status, credits = row["user_id"], row["subscription_status"], row["credits_remaining"]

        if status in ["paid", "premium"] or credits == -1:
            return "Premium Member - Unlimited Access"
        else:
            return f"Free Plan: {credits if credits is not None else 3} optimizations remaining"
            
    except sqlite3.Error as db_error:
        print(f"🚨 Database error: {db_error}")
        return "Unable to load user status"
    
    finally:
        if conn:
            conn.close()

def get_user_credits(user_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, credits_remaining, subscription_status)
            VALUES (?, 3, 'free')
            ON CONFLICT(user_id) DO NOTHING
        """, (user_id,))

        cursor.execute(
            "SELECT credits_remaining, subscription_status FROM users WHERE user_id = ?", 
            (user_id,)
        )
        row = cursor.fetchone()
        conn.commit()

        if row:
            return row["credits_remaining"], row["subscription_status"]
        else:
            return 3, "free"
    
    except sqlite3.Error as db_error:
        print(f"🚨 Database error: {db_error}")
        return 3, "free"
    
    finally:
        if conn:
            conn.close()

def update_user_credits(user_id, credits, subscription_status='free'):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users SET credits_remaining = ?, subscription_status = ? WHERE user_id = ?", 
            (credits, subscription_status, user_id)
        )
        conn.commit()
    
    except sqlite3.Error as db_error:
        print(f"🚨 Database error: {db_error}")
        if conn:
            conn.rollback()
    
    finally:
        if conn:
            conn.close()

def get_credits_display(email):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, credits_remaining, subscription_status FROM users WHERE email = ?",
            (email,)
        )
        row = cursor.fetchone()
        
        if not row:
            return """
            <div class="status-badge free">
                <strong>Free Plan: 3 Optimizations Remaining</strong>
            </div>
            """
        
        user_id, credits, status = row
        
        if status in ["paid", "premium"]:
            return """
            <div class="status-badge premium" style="background: linear-gradient(135deg, #6ee7b7 0%, #34d399 50%, #10b981 100%);
                                                      box-shadow: 0 4px 12px rgba(52, 211, 153, 0.3);">
                <strong>Premium: Unlimited Access</strong>
            </div>
            """
        else:
            return f"""
            <div class="status-badge free">
                <strong>Free Plan: {credits} Optimizations Remaining</strong>
            </div>
            """
    
    except sqlite3.Error as db_error:
        print(f"🚨 Database error: {db_error}")
        return """
        <div class="status-badge" style="background: var(--danger);">
            <strong>Unable to load status</strong>
        </div>
        """
    
    finally:
        if conn:
            conn.close()

def refresh_user_display(email):
    if not email or not email.strip():
        return (
            """<div style='text-align:center; color: var(--text-secondary);'>Please enter your email to get started</div>""",
            """<div class="status-badge free"><strong>Free Plan: 3 Optimizations Remaining</strong></div>""",
            gr.HTML("")
        )
    
    user_id, credits, status = get_or_create_user(email)
    
    return (
        get_user_status(email),
        get_credits_display(email),
        get_sidebar_content(email)
    )

def get_sidebar_content(email):
    user_id, credits, status = get_or_create_user(email)
    is_premium = (status in ['paid', 'premium'])
    
    if is_premium:
        return """
        <div style="text-align:center; margin:20px 0;">
            <div class="premium-badge" style="background: linear-gradient(135deg, #6ee7b7 0%, #34d399 50%, #10b981 100%);
                                               box-shadow: 0 4px 12px rgba(52, 211, 153, 0.3);">
                Premium Member - Unlimited Access Active
            </div>
        </div>
        """
    else:
        return """
        <div style="text-align:center; margin:20px 0;">
            <a href="https://buy.stripe.com/cNi9ASgWl6C614l3Ja1Jm00" 
               target="_blank" 
               class="upgrade-cta">
                Upgrade to Premium - Just $5.99/month
            </a>
        </div>
        """

def create_checkout_session(email):
    try:
        user_id, credits, status = get_or_create_user(email)

        if not PRICE_ID or not PRICE_ID.strip():
            return "⚠️ Payment system not configured. Contact support@resumewhip.com"

        if not stripe.api_key or stripe.api_key == "":
            return "⚠️ Payment system not configured. Contact support@resumewhip.com"

        customer_id = get_stripe_customer_id_from_db(user_id)
        
        session = stripe.checkout.Session.create(
            client_reference_id=user_id,
            customer=customer_id if customer_id else None,
            customer_email=email if not customer_id else None,
            payment_method_types=['card'],
            line_items=[{
                'price': PRICE_ID,
                'quantity': 1,
            }],
            mode='subscription',
            success_url="https://www.resumewhip.com?payment=success",
            cancel_url="https://www.resumewhip.com?canceled=true"
        )
        
        return session.url
    
    except Exception as e:
        print(f"🚨 Checkout error: {e}")
        return f"⚠️ Unable to start checkout. Contact support@resumewhip.com"

def store_stripe_customer_id(user_id, customer_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET stripe_customer_id = ? WHERE user_id = ?",
            (customer_id, user_id)
        )
        conn.commit()
    
    except sqlite3.Error as db_error:
        print(f"🚨 Database error: {db_error}")
        if conn:
            conn.rollback()
    
    finally:
        if conn:
            conn.close()

def get_user_id_by_customer_id(customer_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id FROM users WHERE stripe_customer_id = ?", 
            (customer_id,)
        )
        row = cursor.fetchone()
        return row["user_id"] if row else None
    
    except sqlite3.Error as db_error:
        print(f"🚨 Database error: {db_error}")
        return None
    
    finally:
        if conn:
            conn.close()

def get_stripe_customer_id_from_db(user_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT stripe_customer_id FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        return row["stripe_customer_id"] if row else None
    
    except sqlite3.Error as db_error:
        print(f"🚨 Database error: {db_error}")
        return None
    
    finally:
        if conn:
            conn.close()

def grant_unlimited_access(user_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        user_exists = cursor.fetchone()
        
        if user_exists is None:
            cursor.execute(
                "INSERT INTO users (user_id, credits_remaining, subscription_status) VALUES (?, ?, ?)",
                (user_id, -1, 'premium')
            )
        else:
            cursor.execute(
                "UPDATE users SET credits_remaining = -1, subscription_status = 'premium' WHERE user_id = ?",
                (user_id,)
            )
        conn.commit()
    
    except sqlite3.Error as db_error:
        print(f"🚨 Database error: {db_error}")
        if conn:
            conn.rollback()
    
    finally:
        if conn:
            conn.close()

def revoke_unlimited_access(user_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        user_exists = cursor.fetchone()
        
        if user_exists is None:
            cursor.execute(
                "INSERT INTO users (user_id, credits_remaining, subscription_status) VALUES (?, ?, ?)",
                (user_id, 1, 'free')
            )
        else:
            cursor.execute(
                "UPDATE users SET credits_remaining = 1, subscription_status = 'free' WHERE user_id = ?",
                (user_id,)
            )
        conn.commit()
    
    except sqlite3.Error as db_error:
        print(f"🚨 Database error: {db_error}")
        if conn:
            conn.rollback()
    
    finally:
        if conn:
            conn.close()

def run_resume_with_credits_with_scoring(resume_file, job_input, email):
    if not email or not email.strip():
        return ("Please enter your email address to continue.", "", "", "", "")
    
    if not resume_file or not job_input.strip():
        return ("Please upload your resume and paste the job description.", "", "", "", get_credits_display(email))
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, credits_remaining, subscription_status FROM users WHERE email = ?",
            (email,)
        )
        row = cursor.fetchone()
        
        if not row:
            user_id, credits, status = get_or_create_user(email)
        else:
            user_id = row["user_id"]
            credits = row["credits_remaining"]
            status = row["subscription_status"]
            
    finally:
        if conn:
            conn.close()
    
    is_premium = (status in ["paid", "premium"])

    if is_premium:
        try:
            original_text = extract_resume_text(resume_file)
            original_score, original_feedback = calculate_resume_score(original_text, job_input)
            
            prompt = prompt_creator(original_text, job_input)
            response = get_resume_response(prompt)

            if not response or response.startswith("⚠️ Error"):
                return (response or "Error generating resume", "", "", "", get_credits_display(email))
            
            parts = re.split(r"^#+ (Additional Suggestions)", response, flags=re.IGNORECASE | re.MULTILINE)
            optimized_text = parts[0].strip() if parts else response
            suggestions = parts[-1].strip() if len(parts) > 1 else "No additional suggestions."

            optimized_score, optimized_feedback = calculate_resume_score(optimized_text, job_input)

            score_comparison = create_score_comparison(
                original_score, optimized_score,
                original_feedback, optimized_feedback
            )

            return (optimized_text, optimized_text, suggestions, score_comparison, get_credits_display(email))
        
        except Exception as e:
            return (f"Error processing resume: {e}", "", "", "", get_credits_display(email))
    
    else:
        if credits <= 0:
            checkout_url = create_checkout_session(email)
            
            if checkout_url.startswith("http"):
                return(
                    f"You've used all free optimizations. [Upgrade here]({checkout_url}) for unlimited access.",
                    "", "", "", get_credits_display(email)
                )
            else:
                return(checkout_url, "", "", "", get_credits_display(email))
        
        try:
            original_text = extract_resume_text(resume_file)
            original_score, original_feedback = calculate_resume_score(original_text, job_input)
            
            prompt = prompt_creator(original_text, job_input)
            response = get_resume_response(prompt)
            
            parts = re.split(r"^#+ (Additional Suggestions)", response, flags=re.IGNORECASE | re.MULTILINE)
            optimized_text = parts[0].strip() if parts else response
            suggestions = parts[-1].strip() if len(parts) > 1 else "No additional suggestions."

            optimized_score, optimized_feedback = calculate_resume_score(optimized_text, job_input)

            score_comparison = create_score_comparison(
                original_score, optimized_score,
                original_feedback, optimized_feedback
            )
            
            update_user_credits(user_id, credits - 1)

            return (optimized_text, optimized_text, suggestions, score_comparison, get_credits_display(email))
        
        except Exception as e:
            return (f"Error processing resume: {e}", "", "", "", get_credits_display(email))

def run_career_change_resume(resume_file, job_input, email, current_field, target_field):
    if not email or not email.strip():
        return ("Please enter your email address to continue.", "", "", "", "")
    
    if not resume_file or not job_input.strip():
        return ("Please upload your resume and paste the job description.", "", "", "", get_credits_display(email))
    
    if not current_field.strip() or not target_field.strip():
        return ("Please fill in both your current field and target field for career transition optimization.", 
                "", "", "", get_credits_display(email))
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, credits_remaining, subscription_status FROM users WHERE email = ?",
            (email,)
        )
        row = cursor.fetchone()
        
        if not row:
            user_id, credits, status = get_or_create_user(email)
        else:
            user_id = row["user_id"]
            credits = row["credits_remaining"]
            status = row["subscription_status"]
            
    finally:
        if conn:
            conn.close()
    
    is_premium = (status in ["paid", "premium"])

    if is_premium:
        try:
            original_text = extract_resume_text(resume_file)
            original_score, original_feedback = calculate_resume_score(original_text, job_input)
            
            prompt = career_pivot_prompt_creator(original_text, job_input, current_field, target_field)
            response = get_resume_response(prompt)

            if not response or response.startswith("⚠️ Error"):
                return (response or "Error generating resume", "", "", "", get_credits_display(email))
            
            parts = re.split(r"^#+ (Career Transition Coaching)", response, flags=re.IGNORECASE | re.MULTILINE)
            optimized_text = parts[0].strip() if parts else response
            suggestions = parts[-1].strip() if len(parts) > 1 else "No additional coaching provided."

            optimized_score, optimized_feedback = calculate_resume_score(optimized_text, job_input)

            score_comparison = create_score_comparison(
                original_score, optimized_score,
                original_feedback, optimized_feedback
            )

            return (optimized_text, optimized_text, suggestions, score_comparison, get_credits_display(email))
        
        except Exception as e:
            return (f"Error processing resume: {e}", "", "", "", get_credits_display(email))
    
    else:
        if credits <= 0:
            checkout_url = create_checkout_session(email)
            
            if checkout_url.startswith("http"):
                return(
                    f"You've used all free optimizations. [Upgrade here]({checkout_url}) for unlimited access.",
                    "", "", "", get_credits_display(email)
                )
            else:
                return(checkout_url, "", "", "", get_credits_display(email))
        
        try:
            original_text = extract_resume_text(resume_file)
            original_score, original_feedback = calculate_resume_score(original_text, job_input)
            
            prompt = career_pivot_prompt_creator(original_text, job_input, current_field, target_field)
            response = get_resume_response(prompt)
            
            parts = re.split(r"^#+ (Career Transition Coaching)", response, flags=re.IGNORECASE | re.MULTILINE)
            optimized_text = parts[0].strip() if parts else response
            suggestions = parts[-1].strip() if len(parts) > 1 else "No additional coaching provided."

            optimized_score, optimized_feedback = calculate_resume_score(optimized_text, job_input)

            score_comparison = create_score_comparison(
                original_score, optimized_score,
                original_feedback, optimized_feedback
            )
            
            update_user_credits(user_id, credits - 1)

            return (optimized_text, optimized_text, suggestions, score_comparison, get_credits_display(email))
        
        except Exception as e:
            return (f"Error processing resume: {e}", "", "", "", get_credits_display(email))

def generate_cover_letter(resume_file, job_input):
    if not resume_file or not job_input.strip():
        return "Please upload a resume and paste the job description."
    
    try:
        resume_txt = extract_resume_text(resume_file)
        if not resume_txt:
            return "Could not extract text from resume. Please try again."
        
        prompt = cover_letter_prompt_creator(resume_txt, job_input)
        return get_cover_response(prompt)
    except Exception as e:
        return f"Error generating cover letter: {e}"

def quick_job_summary(score):
    if score >= 80:
        color = "#10b981"
        text = "Legitimate Posting - This job looks authentic and worth applying to"
    elif score >= 50:
        color = "#f59e0b"
        text = "Proceed with Caution - Some red flags detected, verify company legitimacy"
    else:
        color = "#ef4444"
        text = "High Risk - Multiple warning signs suggest this may not be legitimate"
    
    return f"""
    <div style="background:{color}; color:white; padding:16px; 
                border-radius:10px; text-align:center; 
                font-weight:600; font-size:1.1em; margin-bottom:15px;
                box-shadow: var(--shadow-md);">
        {text}
    </div>
    """

def validate_job_posting(job_description, company_name=None, job_title=None):
    if not job_description.strip():
        return "Please paste a job description before validating.", ""

    score = 100
    warnings = []

    if "wire money" in job_description.lower() or "gift cards" in job_description.lower():
        score -= 50
        warnings.append("⚠️ Mentions money transfer or gift cards")
    if "no experience required" in job_description.lower():
        score -= 15
        warnings.append("⚠️ Very low barrier to entry")
    if "urgent hire" in job_description.lower() or "act fast" in job_description.lower():
        score -= 10
        warnings.append("⚠️ Excessive urgency language")
    if "training fee" in job_description.lower():
        score -= 30
        warnings.append("⚠️ Mentions paying fees")
    if job_description.lower().count("team player") > 2:
        score -= 5
        warnings.append("⚠️ Overuse of generic phrases")

    score = max(score, 0)

    summary_html = quick_job_summary(score)

    report_lines = []
    if company_name:
        report_lines.append(f"**Company:** {company_name}")
    if job_title:
        report_lines.append(f"**Job Title:** {job_title}")

    report_lines.append(f"**Legitimacy Score:** {score}/100")
    if warnings:
        report_lines.append("\n".join(warnings))
    else:
        report_lines.append("✅ No major red flags detected")

    full_report = "\n".join(report_lines)

    return summary_html, full_report

def calculate_resume_score(resume_text, job_description):
    score = 0
    max_score = 100
    feedback = []
    
    stop_words = {'the', 'and', 'for', 'with', 'this', 'that', 'from', 'have', 'will', 'your', 'our', 'their'}
    job_keywords = set(word.lower() for word in job_description.split() 
                      if len(word) > 4 and word.isalpha() and word.lower() not in stop_words)
    resume_words = set(word.lower() for word in resume_text.split() 
                       if len(word) > 4 and word.isalpha())
    
    keyword_matches = job_keywords.intersection(resume_words)
    match_rate = len(keyword_matches) / len(job_keywords) if job_keywords else 0
    keyword_score = min(50, int(match_rate * 50))
    score += keyword_score
    feedback.append(f"**Keywords:** {keyword_score}/50 - {int(match_rate*100)}% match")
    
    action_verbs = ['achieved', 'improved', 'increased', 'reduced', 'led', 'managed', 
                   'developed', 'created', 'designed', 'implemented', 'delivered', 
                   'optimized', 'generated', 'established', 'coordinated', 'executed']
    action_verb_count = sum(1 for verb in action_verbs if verb in resume_text.lower())
    action_score = min(20, action_verb_count * 3)
    score += action_score
    feedback.append(f"**Impact Language:** {action_score}/20")
    
    import re
    metrics = re.findall(r'\d+[%$,]|\$\d+|\d+\+|\d+x', resume_text)
    quant_score = min(20, len(metrics) * 4)
    score += quant_score
    feedback.append(f"**Quantifiable Results:** {quant_score}/20")
    
    word_count = len(resume_text.split())
    if 250 <= word_count <= 600:
        length_score = 10
        feedback.append(f"**Length:** 10/10 - Optimal")
    elif 200 <= word_count < 250 or 600 < word_count <= 750:
        length_score = 7
        feedback.append(f"**Length:** 7/10 - Good")
    else:
        length_score = 3
        feedback.append(f"**Length:** 3/10 - Needs adjustment")
    score += length_score
    
    return score, feedback

def create_score_comparison(original_score, optimized_score, original_feedback, optimized_feedback):
    def get_grade(score):
        if score >= 90: return "A+", "#10b981"
        elif score >= 80: return "A", "#10b981"
        elif score >= 70: return "B", "#f59e0b"
        elif score >= 60: return "C", "#f59e0b"
        else: return "D", "#ef4444"
    
    orig_grade, orig_color = get_grade(original_score)
    opt_grade, opt_color = get_grade(optimized_score)
    improvement = optimized_score - original_score
    
    comparison_html = f"""
    <div style="background: var(--bg-primary); padding: 25px; border-radius: 15px; 
                margin: 20px 0; box-shadow: var(--shadow-md);">
        <h3 style="text-align: center; color: var(--text-primary); margin-bottom: 20px;">
            Resume Analysis Report
        </h3>
        
        <div style="display: flex; justify-content: space-around; gap: 20px; margin-bottom: 25px;">
            <div style="flex: 1; background: white; padding: 20px; border-radius: 12px; 
                        text-align: center; border: 2px solid {orig_color};">
                <h4 style="color: var(--text-secondary); margin: 0 0 10px 0;">Original</h4>
                <div style="font-size: 3em; font-weight: 800; color: {orig_color}; margin: 10px 0;">
                    {original_score}
                </div>
                <div style="font-size: 1.2em; color: {orig_color}; font-weight: 700;">
                    Grade: {orig_grade}
                </div>
            </div>
            
            <div style="display: flex; align-items: center; justify-content: center; flex-direction: column;">
                <div style="font-size: 2em; color: #10b981;">→</div>
                <div style="background: #10b981; color: white; padding: 8px 16px; 
                            border-radius: 20px; margin-top: 10px; font-weight: 700;">
                    +{improvement} points
                </div>
            </div>
            
            <div style="flex: 1; background: white; padding: 20px; border-radius: 12px; 
                        text-align: center; border: 2px solid {opt_color};">
                <h4 style="color: var(--text-secondary); margin: 0 0 10px 0;">Optimized</h4>
                <div style="font-size: 3em; font-weight: 800; color: {opt_color}; margin: 10px 0;">
                    {optimized_score}
                </div>
                <div style="font-size: 1.2em; color: {opt_color}; font-weight: 700;">
                    Grade: {opt_grade}
                </div>
            </div>
        </div>
        
        <div style="background: var(--bg-secondary); padding: 20px; border-radius: 12px; margin-top: 20px;">
            <h4 style="color: var(--text-primary); margin-bottom: 15px;">Improvement Breakdown</h4>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                <div>
                    <h5 style="color: var(--text-secondary); margin-bottom: 10px;">Original:</h5>
                    {'<br>'.join(original_feedback)}
                </div>
                <div>
                    <h5 style="color: #10b981; margin-bottom: 10px;">Optimized:</h5>
                    {'<br>'.join(optimized_feedback)}
                </div>
            </div>
        </div>
    </div>
    """
    return comparison_html

# Gradio Interface
with gr.Blocks(title="ResumeWhip - Professional ATS Resume Optimizer", theme=gr.themes.Soft(), css=custom_css) as app:
    
    # Header
    gr.HTML("""
    <div class="header-container">
        <h1>ResumeWhip</h1>
        <h2>AI-Powered ATS Resume Optimization</h2>
        <h3>First 3 Optimizations Free - Professional Results in 30 Seconds</h3>
    </div>
    """)

    with gr.Row():
        # Sidebar
        with gr.Column(scale=1, elem_classes="sidebar-container"):
            user_status = gr.Markdown("Please enter your email to get started")
            refresh_btn = gr.Button("Refresh Status", variant="secondary", size="sm")

            with gr.Accordion("How It Works", open=False):
                gr.Markdown("""
                **Simple 4-Step Process:**
                
                1. Enter your email and upload your resume
                2. Paste the job description you're targeting
                3. Choose your optimization tool (standard, career change, cover letter, or job validator)
                4. Download your optimized resume as PDF and apply
                
                Our AI analyzes job descriptions and tailors your resume to match ATS requirements while highlighting your relevant experience.
                """)
                
            with gr.Accordion("Formatting Guide", open=False):
                gr.Code("""
# Headers
# = Large Header
## = Medium Header
### = Small Header

Text Formatting:
<b>Bold text</b>
<i>Italic text</i>
<u>Underlined text</u>

Lists:
- Bullet point
1. Numbered list

Links:
[Link Text](https://url.com)

Section Break:
---

Page Break:
<div style="page-break-after: always;"></div>
                """, language="markdown")
                
            with gr.Accordion("FAQ", open=False):
                gr.Markdown("""
                **What is ATS?**  
                Applicant Tracking Systems filter resumes before humans see them. Our optimizer ensures yours gets through.
                
                **Why does it work better?**  
                Built by job seekers who understand the struggle. Outperforms LinkedIn's premium tools in blind tests.
                
                **File formats supported?**  
                PDF, DOCX, MD, and TXT files.
                
                **Free trial details?**  
                3 free optimizations, then $5.99/month for unlimited access.
                
                **Data privacy?**  
                We never sell your data. Ever.
                """)

            sidebar_content = gr.HTML("")
            resume_counter = gr.HTML()

        # Main content
        with gr.Column(scale=5):
            # Input section
            with gr.Row():
                email_input = gr.Textbox(
                    label="Email Address (Required)",
                    placeholder="you@example.com",
                    elem_id="email-box"
                )
                
                resume_input = gr.File(
                    label="Upload Resume", 
                    file_types=[".pdf", ".docx", ".md", ".txt"]
                )
                company_input = gr.Textbox(
                    label="Company Name", 
                    placeholder="e.g., Amazon, Google"
                )
            
            job_input = gr.Textbox(
                label="Job Description (Full Text)", 
                lines=6,
                placeholder="Paste the complete job posting here..."
            )

            # 4-Tab System
            gr.HTML("""
            <div style="text-align: center; margin: 30px 0;">
                <h2 style="font-size: 1.8em; color: var(--text-primary); font-weight: 700; margin-bottom: 10px;">
                    Choose Your Tool
                </h2>
                <p style="font-size: 1.05em; color: var(--text-secondary);">
                    Select the optimization tool that fits your needs
                </p>
            </div>
            """)
            
            with gr.Tabs():
                with gr.TabItem("Job Validator"):
                    gr.Markdown("### Verify Job Posting Legitimacy")
                    gr.Markdown("Check if a job posting shows red flags for scams or data harvesting before investing time in your application.")
                    
                    with gr.Row():
                        jd_date = gr.Textbox(
                            label="Posting Date", 
                            placeholder="YYYY-MM-DD"
                        )
                        jd_title = gr.Textbox(
                            label="Job Title", 
                            placeholder="e.g., Software Engineer"
                        )
                    
                    validate_btn = gr.Button("Validate Job Posting", variant="primary")
                    summary_output = gr.HTML()
                    report_output = gr.Markdown()

                with gr.TabItem("Resume Optimizer"):
                    gr.Markdown("### Standard ATS Optimization")
                    gr.Markdown("Perfect for optimizing your resume for a specific job posting in your current field.")
                    
                    run_resume = gr.Button(
                        "Optimize Resume (Takes ~30 Seconds)", 
                        variant="primary"
                    )
                    
                    resume_md = gr.Markdown(label="Optimized Resume Preview")
                    resume_edit = gr.Textbox(label="Edit Your Resume (Optional)", lines=15)
                    suggestions = gr.Markdown(label="Optimization Tips")
                    score_comparison = gr.HTML(label="ATS Compatibility Score")
                    
                    export_resume_btn = gr.Button(
                        "Download as PDF",
                        elem_classes="download-btn"
                    )
                    export_resume_result = gr.File()

                with gr.TabItem("Career Transition"):
                    gr.Markdown("### Career Change Optimization")
                    gr.Markdown("Specialized optimization for professionals transitioning between industries or roles. Emphasizes transferable skills.")
                    
                    with gr.Row():
                        current_field_input = gr.Textbox(
                            label="Current/Previous Field",
                            placeholder="e.g., Teaching, Military, Retail",
                            info="What industry are you coming from?"
                        )
                        target_field_input = gr.Textbox(
                            label="Target Field",
                            placeholder="e.g., Data Analytics, Project Management",
                            info="What industry are you moving into?"
                        )
                    
                    run_career_resume = gr.Button(
                        "Optimize for Career Transition (~30 Seconds)", 
                        variant="primary"
                    )
                    
                    career_md = gr.Markdown(label="Optimized Resume Preview")
                    career_edit = gr.Textbox(label="Edit Your Resume (Optional)", lines=15)
                    career_suggestions = gr.Markdown(label="Career Transition Coaching")
                    career_score = gr.HTML(label="ATS Compatibility Score")
                    
                    export_career_btn = gr.Button(
                        "Download as PDF",
                        elem_classes="download-btn"
                    )
                    export_career_result = gr.File()

                with gr.TabItem("Cover Letter"):
                    gr.Markdown("### Professional Cover Letter Generator")
                    gr.Markdown("Generate a tailored, ATS-friendly cover letter based on your resume and the job description.")
                    
                    run_cover = gr.Button("Generate Cover Letter", variant="primary")
                    cover_output = gr.Textbox(
                        label="Your Cover Letter (Edit as Needed)", 
                        lines=15
                    )
                    
                    export_cover_btn = gr.Button(
                        "Download as PDF",
                        elem_classes="download-btn"
                    )
                    export_cover_result = gr.File()

            # Tip box
            gr.HTML("""
            <div class="tip-box">
                <strong>Pro Tip:</strong> Always validate job postings before spending time on applications. 
                Our Job Validator can spot common scam patterns and save you time.
            </div>
            """)

    # Footer
    gr.HTML("""
    <footer>
        <div style="max-width: 1200px; margin: 0 auto; text-align: center;">
            <div style="margin-bottom: 25px;">
                <a href="mailto:support@resumewhip.com" style="margin: 0 20px;">Contact Support</a>
                <a href="https://buy.stripe.com/cNi9ASgWl6C614l3Ja1Jm00" style="margin: 0 20px;">Upgrade to Premium</a>
                <a href="https://resumewhip.com/blog" style="margin: 0 20px;">Resume Tips Blog</a>
            </div>
            
            <div style="margin-bottom: 20px; color: var(--text-secondary);">
                <h3 style="color: var(--text-primary); margin-bottom: 10px;">
                    ResumeWhip - Professional ATS Optimization
                </h3>
                <p style="line-height: 1.6; max-width: 600px; margin: 0 auto;">
                    Built by job seekers who understand the ATS struggle. Our AI optimizer 
                    consistently outperforms premium job platform tools, helping you get past 
                    the bots and land interviews.
                </p>
            </div>
            
            <div style="display: flex; justify-content: center; gap: 30px; margin-bottom: 25px;
                        flex-wrap: wrap; color: var(--text-secondary); font-size: 0.9em;">
                <div>We never sell your data</div>
                <div>30-second optimization</div>
                <div>40% higher ATS compatibility</div>
                <div>Works with all job boards</div>
            </div>

            <div style="border-top: 1px solid var(--border); padding-top: 20px;">
                <p style="color: var(--text-secondary); margin: 0;">
                    © 2025 ResumeWhip - AI-Powered Resume Optimization
                </p>
            </div>
        </div>
    </footer>
    """)
    
    # Event handlers
    email_input.submit(
        fn=refresh_user_display,
        inputs=[email_input],
        outputs=[user_status, resume_counter, sidebar_content]
    )
    
    refresh_btn.click(
        fn=refresh_user_display,
        inputs=[email_input],
        outputs=[user_status, resume_counter, sidebar_content]
    )
    
    validate_btn.click(
        fn=lambda job_desc, company, title, email: (
            ensure_user_logged(email) if email else None,
            validate_job_posting(job_desc, company, title)
        )[1] if email else ("Please enter your email first", ""),
        inputs=[job_input, company_input, jd_title, email_input],
        outputs=[summary_output, report_output]
    )
    
    run_resume.click(
        fn=run_resume_with_credits_with_scoring,
        inputs=[resume_input, job_input, email_input],
        outputs=[resume_md, resume_edit, suggestions, score_comparison, resume_counter]
    )
    
    export_resume_btn.click(
        fn=export_resume,
        inputs=[resume_edit, company_input],
        outputs=export_resume_result
    )
    
    run_career_resume.click(
        fn=run_career_change_resume,
        inputs=[resume_input, job_input, email_input, current_field_input, target_field_input],
        outputs=[career_md, career_edit, career_suggestions, career_score, resume_counter]
    )
    
    export_career_btn.click(
        fn=export_resume,
        inputs=[career_edit, company_input],
        outputs=export_career_result
    )
    
    run_cover.click(
        fn=lambda resume, job, email: (
            get_or_create_user(email),
            generate_cover_letter(resume, job)
        )[1],
        inputs=[resume_input, job_input, email_input],
        outputs=cover_output
    )
    
    export_cover_btn.click(
        fn=save_cover_letter,
        inputs=[cover_output, company_input],
        outputs=export_cover_result
    )

if __name__ == "__main__":
    init_database()

    app_with_gradio = gr.mount_gradio_app(fastapi_app, app, path="/")

    uvicorn.run(
        app_with_gradio, 
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000))
    )