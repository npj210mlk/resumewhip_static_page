# Final
import os
import sqlite3
import gradio as gr
import stripe
import pdfplumber
import uuid
import json
import threading
# ...and because fastapi is asynchronous, we need a server:
import uvicorn

from datetime import datetime
from new_functions import (
    extract_resume_text,
    sanitize_input,
    prompt_creator,
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

# for handling the api stuff
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse

# button styling - <style></style> not needed b/c gradio injects the style string for us
custom_css = """
#email-box input {
    border: 3px solid #ff5722 !important;
    background-color: #fff8f6;
    font-size: 1.2em !important;
    padding: 10px !important;
    font-weight: bold !important;
    color: #333 !important;

#email-box label {
    color: #ff5722 !important;   /* Orange CTA color */
    font-size: 1.1em !important; /* Slightly larger */
    font-weight: bold !important;
}

/* === IMPROVED COLOR VARIABLES === */
:root {
    --primary-blue: #4f46e5;      /* Modern indigo - more professional than purple */
    --primary-blue-hover: #3730a3; 
    --accent-orange: #f59e0b;      /* Warmer orange - better contrast */
    --accent-orange-hover: #d97706;
    --success-green: #10b981;      /* Modern green */
    --success-green-hover: #059669;
    --neutral-gray: #6b7280;       /* Better readability */
    --light-gray: #f9fafb;
    --border-gray: #e5e7eb;
}

.tab-nav {
    display: flex;
    justify-content: center;
    margin-bottom: 20px;
    border-bottom: none !important;
    background: var(--light-gray);
    border-radius: 12px;
    padding: 8px;
}

.tab-nav button {
    background: linear-gradient(135deg, var(--primary-blue), var(--primary-blue-hover));
    color: white !important;
    font-weight: 700;
    font-size: 1.3em;
    border-radius: 8px;
    margin: 0 4px;
    padding: 16px 32px;
    border: none !important;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 2px 8px rgba(79, 70, 229, 0.2);
}

.tab-nav button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(79, 70, 229, 0.3);
    background: linear-gradient(135deg, var(--primary-blue-hover), var(--primary-blue));
}

.tab-nav button.selected {
    background: linear-gradient(135deg, var(--accent-orange), var(--accent-orange-hover));
    box-shadow: 0 4px 16px rgba(245, 158, 11, 0.4);
    transform: translateY(-1px);
}

/* === IMPROVED BUTTON STYLING === */
button[variant="primary"], .whip-button {
    background: linear-gradient(135deg, var(--success-green), var(--success-green-hover)) !important;
    color: white !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 14px 28px !important;
    font-size: 1.1em !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2) !important;
}

button[variant="primary"]:hover, .whip-button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(16, 185, 129, 0.3) !important;
}

/* === SUBSCRIPTION BUTTONS - HIGH VISIBILITY === */
.btn-upgrade, a[href*="stripe.com"] {
    background: linear-gradient(135deg, #ff6e5b, #ff815b) !important;
    color: white !important;
    border: 2px solid transparent !important;
    border-radius: 12px !important;
    padding: 16px 24px !important;
    font-weight: 700 !important;
    font-size: 1.1em !important;
    text-decoration: none !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 16px rgba(245, 158, 11, 0.3) !important;
    display: inline-block !important;
}

.btn-upgrade:hover, a[href*="stripe.com"]:hover {
    transform: translateY(-3px) scale(1.02) !important;
    box-shadow: 0 8px 24px rgba(245, 158, 11, 0.4) !important;
    border-color: white !important;
}

/* === CLEANER TIP SECTION === */
div[style*="linear-gradient(135deg, #66ea92"] {
    background: linear-gradient(135deg, #5b63ff, #845bff) !important;
    border: 2px solid rgba(255, 255, 255, 0.2) !important;
}

/* Hide upgrade elements for premium users */
body[data-user-status="premium"] .upgrade-prompt,
body[data-user-status="premium"] .subscription-cta,
body[data-user-status="premium"] a[href*="stripe.com"] {
    display: none !important;
}

/* Premium user badge styling */
.premium-badge {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: white;
    padding: 12px 20px;
    border-radius: 25px;
    font-weight: 700;
    font-size: 0.9em;
    box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2);
    border: 2px solid rgba(255, 255, 255, 0.2);
    text-align: center;
    margin: 10px 0;
}

/* Premium status indicators */
.premium-status {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: white;
    border-radius: 10px;
    padding: 15px;
    font-weight: 600;
    font-size: 1.2em;
    text-align: center;
    box-shadow: 0 4px 16px rgba(16, 185, 129, 0.3);
}

/* Premium welcome message */
.premium-welcome {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: white;
    padding: 25px;
    border-radius: 15px;
    text-align: center;
    margin: 20px 0;
    box-shadow: 0 8px 24px rgba(16, 185, 129, 0.3);
    border: 2px solid rgba(255, 255, 255, 0.1);
}

.premium-welcome h3 {
    margin: 0 0 10px 0;
    font-size: 1.8em;
}

.premium-welcome p {
    margin: 0;
    font-size: 1.2em;
    opacity: 0.9;
}

/* Subtle premium indicators throughout the interface */
body[data-user-status="premium"] .tool-section::before {
    content: "✨ Premium";
    position: absolute;
    top: -10px;
    right: 15px;
    background: #10b981;
    color: white;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 0.8em;
    font-weight: 700;
}

/* Enhanced tab styling for premium users */
body[data-user-status="premium"] .tab-nav button.selected {
    background: linear-gradient(135deg, #10b981, #059669);
    box-shadow: 0 4px 16px rgba(16, 185, 129, 0.4);
}

.download-btn-green {
    background: linear-gradient(135deg, #10b981, #059669) !important;
    color: white !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 14px 28px !important;
    font-size: 1.1em !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2) !important;
}

.download-btn-green:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(16, 185, 129, 0.3) !important;
    background: linear-gradient(135deg, #059669, #047857) !important;
}

"""
# environment variables
DATABASE_PATH = os.getenv("DATABASE_PATH", "resumewhip.db")
ADMIN_INCOGNITO = os.getenv("ADMIN_INCOGNITO", "change_this_secret_key")

# get new SQLite connection for each request

# def get_db_connection():
#     """ Function to let FastAPI handle multiple requests to prevent db lockup"""
#     db_path
#     conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
#     conn.row_factory = sqlite3.Row
#     return conn

# isolate the variables / store data specific to each thread in its own database connection
thread_local = threading.local()

def get_db_connection():
    """ Get a thread-safe database connection using thread_local """
    if not hasattr(thread_local, "connection"):
    # Check if persistent Render disk exists
        render_path = "/var/data/resumewhip.db"
        local_path = "resumewhip.db"
        db_path = render_path if os.path.exists("/var/data") else local_path

        print(f"🔍 New DB connection for thread: {os.path.abspath(db_path)}")

        thread_local.connection = sqlite3.connect(db_path, timeout = 10)
        thread_local.connection.row_factory = sqlite3.Row

    # original connection was just "conn"
    # conn = sqlite3.connect(db_path, check_same_thread=False)
    # conn.row_factory = sqlite3.Row
    # return conn

    # threading connection
    return thread_local.connection


# Stripe setup
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
PRICE_ID = os.getenv("PRICE_ID")

# initialize Fastapi for the webhooks
fastapi_app = FastAPI()

# Simple in-memory storage - but sync with database
user_sessions = {}  # Maps session IDs to user data
FREE_CREDITS = 3

def init_database():
    """Initialize SQLite database with required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    # email TEXT UNIQUE to tie users to email
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
    
    # IP usage table (for rate limiting on free users)
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

def check_rate_limit(ip_address):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    today = datetime.date.today()
    cursor.execute("""
        SELECT count FROM ip_usage
        WHERE ip=? AND date=?
    """, (ip_address, today))
    row = cursor.fetchone()

    if row and row["count"] >= 3:
        # limit reached
        return False
    else:
        cursor.execute("""
            INSERT INTO ip_usage (ip, date, count)
            VALUES (?, ?, 1)
            ON CONFLICT(ip, date) DO UPDATE SET count = count + 1
        """, (ip_address, today))
        conn.commit()
        return True

def get_user_ip():
    """ Get the user's IP address, accounting for proxies. """
    if request.headers.get("X-Forwarded-For"):
        ip = request.headers["X-Forwarded-For"].split(",")[0]
    else:
        ip = request.remote_addr or "unknown"
    return ip

def track_ip_usage(ip):
    """ Log / update daily ip usage. """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # today's date for unique daily count
        today = datetime.now().strftime("%Y-%m-%d")

        cursor.execute(
            """
            INSERT INTO ip_usage (ip, date, count)
            VALUES (?, ?, 1)
            ON CONFLICT(ip, date)
            DO UPDATE SET count = count + 1;
            """,
            (ip, today)
        )

        conn.commit()
    
    except sqlite3.Error as db_error:
        print(f"🚨 Database error in track_ip_usage: {db_error}")
        if conn:
            conn.rollback()

    finally:
        if conn:
            conn.close()

def get_or_create_user(email: str):
    """Fetch user by email or create a record if they don't have one"""
    print(f"🔍 DEBUG: get_or_create_user called with email: {email}")
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT user_id, credits_remaining, subscription_status FROM users WHERE email = ?",
            (email,)
            )
        row = cursor.fetchone()

        if row:
            user_id, credits, status = row
            print(f"✅ Found existing user: {user_id}")

        else:
            user_id = str(uuid.uuid4())
            credits = 3
            status = "free"
            cursor.execute(
                "INSERT INTO users (user_id, email, credits_remaining, subscription_status) VALUES (?, ?, ?, ?)",
                (user_id, email, credits, status)
            )
            conn.commit()
            print(f"✅ Created new user: {email}, id={user_id}")
        
        return user_id, credits, status
    
    except sqlite3.Error as e:
        print(f"🚨 Database error: {e}")
        conn.rollback()
        raise
    
    finally:
        conn.close()

# email logging / email validation wrapper
def ensure_user_logged(email):
    """Make sure the user is logged before the app runs"""
    if not email or not email.strip():
        raise ValueError("Email required.")
    return get_or_create_user(email)

# # ================= TEST DATABASE WRITING - TEMP FUNCTION ==================
# def test_db_write():
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     cursor.execute("INSERT INTO users (user_id, email) VALUES (?, ?)", 
#                       ("test-123", "test@test.com"))
#     conn.commit()
#     conn.close()
#     return "Test write complete"
# # ================= TEST DATABASE WRITING - TEMP FUNCTION ==================

def get_user_status(email):
    user_id, credits, status = get_or_create_user(email)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT subscription_status, credits_remaining FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return "As A Free User, You've Got 3 Free Resumes Remaining"
    
    status, credits = row["subscription_status"], row["credits_remaining"]
    if status in ["paid", "premium"] or credits == -1:
        return "🌟 Unlimited Resumes Granted! You're A Premium User - Thanks So Much for Choosing Us!"
    else:
        return f"You currently have {credits if credits is not None else 3} Free Resumes Remaining"

def is_premium_user(user_id):
    """Check if user has active premium subscription"""
    credits, subscription_status = get_user_credits(user_id)
    return (subscription_status in ['paid', 'premium'] or 
            credits == float('inf') or 
            check_payment_status(user_id))

def get_user_credits(user_id):
    """ Retrieve user credits from database"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
                   INSERT INTO users (user_id, credits_remaining, subscription_status)
                   VALUES (?, 3, 'free')
                   ON CONFLICT(user_id) DO NOTHING
                   """, (user_id,))

    # get current values
    cursor.execute("SELECT credits_remaining, subscription_status FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.commit()

    # since they alreay exist, return their current credits  
    conn.close()
    return row["credits_remaining"], row["subscription_status"]

def update_user_credits(user_id, credits, subscription_status='free'):
    """ update user credits """
    conn = get_db_connection()               
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET credits_remaining = ?, subscription_status = ? WHERE user_id = ?", 
        (credits, subscription_status, user_id)
        )
    conn.commit()
    conn.close()

# def get_credits_display(email):
#     """Return credits display based on user status"""
#     user_id, credits, status = get_or_create_user(email)
#     credits_display = "∞" if status in ["paid", "premium"] else str(credits)
#     return f"### 🫘 Free Resumes Left: {credits_display}"
    
#     if is_premium:
#         return gr.Markdown("""
#         <div style="text-align: center; padding: 15px; 
#                     background: linear-gradient(135deg, #10b981 0%, #059669 100%);
#                     color: white; border-radius: 10px; font-weight: 600; font-size: 1.2em;">
#             <strong>✨ Premium: Unlimited Resumes</strong>
#         </div>
#         """)
#     else:
#         # credits, _ = get_user_credits(user_id)
#         return gr.Markdown(f"""
#         <div style="text-align: center; padding: 15px; 
#                     background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
#                     color: white; border-radius: 10px; font-weight: 600; font-size: 1.2em;">
#             <strong>Free Resumes Left: {credits}</strong>
#         </div>
#         """)

def get_credits_display(email):
    """Return credits display based on user status"""
    user_id, credits, status = get_or_create_user(email)
    
    if status in ["paid", "premium"]:
        return """
        <div style="text-align: center; padding: 15px; 
                    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                    color: white; border-radius: 10px; font-weight: 600; font-size: 1.2em;">
            <strong>✨ Premium: Unlimited Resumes</strong>
        </div>
        """
    else:
        return f"""
        <div style="text-align: center; padding: 15px; 
                    background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
                    color: white; border-radius: 10px; font-weight: 600; font-size: 1.2em;">
            <strong>🫘 Free Resumes Left: {credits}</strong>
        </div>
        """

def get_user_id_by_customer_id(customer_id):
    """Get user_id from database using customer_id"""
    conn = get_db_connection() 
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE stripe_customer_id = ?", (customer_id,))
    row = cursor.fetchone()
    conn.close()
    return row["user_id"] if row else None

def get_stripe_customer_id_from_db(user_id):
    """Get the Stripe customer ID from SQLite db"""
    conn = get_db_connection() 
    cursor = conn.cursor()
    cursor.execute(
        "SELECT stripe_customer_id FROM users WHERE user_id = ?",
        (user_id,)
        )
    row = cursor.fetchone()
    conn.close()
    return row["stripe_customer_id"] if row else None

def get_user_email_from_db(user_id):
    conn = get_db_connection() 
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row["email"] if row else None

def log_request(user_id, ip_address):
    """ prevent endless account creation """
    conn = get_db_connection() 
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS requests_log (
            user_id TEXT,
            ip_address TEXT,
            request_date DATE
        )
    """)
    cursor.execute("INSERT INTO requests_log (user_id, ip_address, request_date) VALUES (?, ?, date('now'))",
                   (user_id, ip_address))
    conn.commit()
    conn.close()

def check_rate_limit(ip_address):
    conn = get_db_connection() 
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) as count FROM requests_log
        WHERE ip_address = ? AND request_date = date('now')
    """, (ip_address,))
    row = cursor.fetchone()
    conn.close()
    return row["count"] < 3  # e.g., 3 free resumes per day

def store_stripe_customer_id(user_id, customer_id):
    """Store Stripe customer ID in SQLite when they first subscribe"""
    conn = get_db_connection() 
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET stripe_customer_id = ? WHERE user_id = ?",
        (customer_id, user_id))
    conn.commit()
    conn.close()

def create_checkout_session(email):
    try:
        # 🔑 Always log the user first
        user_id, credits, status = get_or_create_user(email)

        # then check if payment system is ready
        if not PRICE_ID or not PRICE_ID.strip():
            return "⚠️ Payment system not fully configured. Please contact support."

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
            success_url="https://www.resumewhip.com/success",
            cancel_url="https://resumewhip.com/cancel"
        )
        return session.url
    
    except Exception as e:
        print(f"Error creating checkout session: {e}")
        return f"⚠️ Unable to start checkout. Please try again later or contact support."

def check_payment_status(user_id):
    """Function to check if the user has paid for the service using Stripe's API"""
    try:
        # check db for stored id
        customer_id = get_stripe_customer_id_from_db(user_id)
        if not customer_id:
            return False
        
        # verify subscription with Stripe
        subscriptions = stripe.Subscription.list(
            customer=customer_id,
            status='active', 
            limit=1
        )

        # see if they already have a subscription
        if subscriptions.data:
            subscription = subscriptions.data[0]
            # make sure that subscription is for my product
            if subscription.items.data[0].price.id == PRICE_ID:
                return True
        
        return False
    
    except stripe.error.StripeError as e:
        print(f"Stripe error in checking subscription: {e}")
        return False
    
    except Exception as e:
        print(f"Error in checking your payment status: {e}")
        return False

def get_sidebar_content(email):
    """Return sidebar content based on user subscription status"""
    user_id, credits, status = get_or_create_user(email)
    is_premium = (status in ['paid', 'premium'])
    
    if is_premium:
        # Premium user sidebar - no upgrade prompts
        return gr.HTML("""
        <div style="text-align:center; margin:20px 0;">
            <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                        color: white; padding: 20px; border-radius: 12px;
                        box-shadow: 0 4px 16px rgba(16, 185, 129, 0.3);">
                <h3 style="margin: 0 0 10px 0; font-size: 1.3em;">✨ Premium Member</h3>
                <p style="margin: 0; font-size: 1.1em; opacity: 0.9;">
                    Unlimited resume optimization active
                </p>
            </div>
        </div>
        """)
    else:
        # Free user sidebar - show upgrade option
        return gr.HTML("""
        <div style="text-align:center; margin:20px 0;">
            <a href="https://buy.stripe.com/cNi9ASgWl6C614l3Ja1Jm00" 
               target="_blank" 
               style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
                      color: white; padding: 16px 24px; text-decoration: none;
                      border-radius: 12px; font-size: 1.1em; font-weight: 700;
                      display: inline-block; transition: all 0.3s ease;
                      box-shadow: 0 4px 16px rgba(245, 158, 11, 0.3);">
                ♾️ Get Unlimited AI-Powered Resume Optimization for Just $5.99/Month!
            </a>
        </div>
        """)
    
def create_billing_portal_session(user_id):
    try:
        customer_id = get_stripe_customer_id_from_db(user_id)
        if not customer_id:
            return None  # No customer yet, so nothing to manage

        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url="https://www.resumewhip.com"  # Where to send users after they're done
        )
        return session.url
    except Exception as e:
        print(f"Error creating billing portal session: {e}")
        return None

def open_billing_portal(email):
    user_id, credits, status = get_or_create_user(email)
    portal_url = create_billing_portal_session(user_id)
    return portal_url if portal_url else "No billing account found."

def grant_unlimited_access(user_id):
    """If they've paid, they get full access"""
    conn = get_db_connection() 
    cursor = conn.cursor()

    # make sure they exist
    cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone() is None:
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
    conn.close()

def revoke_unlimited_access(user_id):
    """Revoke unlimited access and set user to free; create if missing"""
    conn = get_db_connection() 
    cursor = conn.cursor()

    # see if they exist
    cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO users (user_id, credits_remaining, subscription_status) VALUES (?, ?, ?)",
            (user_id, 1, 'free') # 1 more courtesy resume
        )
    else:
        cursor.execute(
        "UPDATE users SET credits_remaining = 1, subscription_status = 'free' WHERE user_id = ?",
        (user_id,) 
    )
    conn.commit()
    conn.close()

@fastapi_app.post("/webhook")
async def stripe_webhook(request: Request):
    """Stripe webhook endpoint for subscription and payment events."""
    try:
        # Get raw body and Stripe signature
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")

        if not sig_header or not WEBHOOK_SECRET:
            print("🚨 Missing Stripe signature or webhook secret.")
            raise HTTPException(status_code=400, detail="Missing signature or webhook secret")

        # Verify Stripe signature
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)

        # ✅ Handle successful payment
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            user_id = session.get("client_reference_id")
            customer_id = session.get("customer")
            # email = session.get("customer_details", {}).get("email")
            
            if user_id and customer_id:
                # if using email 
                # store_stripe_customer_id(user_id, customer_id, email)
                # without email (what Claude's recommending)
                store_stripe_customer_id(user_id, customer_id)
                # grant unlimisted access
                grant_unlimited_access(user_id)
                print(f"✅ Granted unlimited access to user: {user_id}")
        
        # 🔄 Handle successful subscription RENEWALS
        elif event["type"] == "invoice.payment_succeeded":
            invoice = event["data"]["object"]
            customer_id = invoice["customer"]
            
            # Find user and ensure they have premium access
            user_id = get_user_id_by_customer_id(customer_id)
            if user_id:
                grant_unlimited_access(user_id)
                print(f"✅ Renewed premium access for user: {user_id}")

        # ⚠️ Handle PAYMENT FAILURES
        elif event["type"] == "invoice.payment_failed":
            invoice = event["data"]["object"]
            customer_id = invoice["customer"]
            user_id = get_user_id_by_customer_id(customer_id)
            
            if user_id:
                # Don't immediately revoke - give grace period
                print(f"⚠️ Payment failed for user: {user_id} - grace period active")

        # ❌ Handle subscription CANCELLATIONS
        elif event["type"] == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            customer_id = subscription["customer"]
            user_id = get_user_id_by_customer_id(customer_id)

            if user_id:
                revoke_unlimited_access(user_id)
                print(f"❌ Revoked access for user: {user_id}")

        # commented out per claude
        # else:
        #     print(f"ℹ️ Unhandled event type: {event['type']}")

        # Return success so Stripe stops retrying
        return JSONResponse(content={"status": "success"}, status_code=200)

    # comment out per claude
    # except stripe.error.SignatureVerificationError as e:
    #     print(f"🚨 Invalid signature: {e}")
    #     raise HTTPException(status_code=400, detail="Invalid signature")

    except Exception as e:
        print(f"🚨 Webhook error: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=400)

@fastapi_app.middleware("http")
async def track_user_requests(request: Request, call_next):
    # get the ip addys from headers
    ip = request.headers.get("x-forwarded-for", request.client.host).split(",")[0]
    # store for gradio to access
    response = await call_next(request)
    return response

@fastapi_app.get("/admin/users")
async def admin_view_users(auth: str = Header(None)):
    """View all users in production database - protected by secret key"""
    if auth != ADMIN_INCOGNITO:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
    users = cursor.fetchall()
    conn.close()
    
    # Convert to list of dicts for JSON response
    user_list = [dict(user) for user in users]
    
    return {
        "total_users": len(user_list),
        "users": user_list  
    }

def run_resume_with_credits_with_scoring(resume_file, job_input, email):
    """Handle resume processing with premium and free user experience"""

    # Validate the user's email input
    if not email or not email.strip():
        return ("🚨 Please enter your email address to continue.", "", "", "", gr.Markdown(""))
    
    # Validate the user's job_input
    if not resume_file or not job_input.strip():
        return ("⚠️ Please upload your resume and paste the job description.", "", "", "",
                get_credits_display(email))
    
    # if not email or not email.strip():
    #     return ("🚨 Please enter your email address to continue.", "", "", "", gr.Markdown(""))
    
    # Get or create the user - db insertion
    user_id, credits, status = get_or_create_user(email)
    is_premium = (status in ["paid", "premium"])

    # Log IP used
    try:
        # default fallback
        ip = "unknown"
        # pass this from FASTAPI context
        track_ip_usage(ip)
    except Exception as ip_error: 
        print(f"⚠️ Could not log user's IP: {ip_error}")
    
    if is_premium:
        # Premium user - unlimited access
        try:
            # extract the original resume's text
            original_text = extract_resume_text(resume_file)

            # calculate original score
            original_score, original_feedback = calculate_resume_score(original_text, job_input)

            # process the existing resume
            optimized_preview, suggestions, match_info, optimized_text = process_resume(resume_file, job_input)
            # editable text output:
            # optimized_text = result[1]

            # calculate the optimized score
            optimized_score, optimized_feedback = calculate_resume_score(optimized_text, job_input)

            # now for the comparison visualization
            score_comparison = create_score_comparison(
                original_score, optimized_score,
                original_feedback, optimized_feedback
            )

            # premium_display = gr.Markdown("""
            # <div style="text-align: center; padding: 15px; 
            #             background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            #             color: white; border-radius: 10px; font-weight: 600; font-size: 1.2em;">
            #     <strong>✨ You're Premium! Thanks for Choosing Us!</strong>
            # </div>
            # """)

            premium_display = get_credits_display(email) 

            return (optimized_preview, optimized_text, suggestions, score_comparison, premium_display)
        
        except Exception as premium_error:
            print(f"🚨 Premium processing error: {premium_error}")
            return (f"Error processing resume: {premium_error}", "", "", "", get_credits_display(email))
    else:
        # Free user - existing credit logic
        # credits, status = get_user_credits(user_id)

        if credits <= 0:
            checkout_url = create_checkout_session(email)
            return(
                f"⏰ Unlock Unlimited Power! [Upgrade here]({checkout_url}) for unlimited optimization.",
                "", "", "", get_credits_display(email)
            )
        
        try:
            # get the  original resume text
            original_text = extract_resume_text(resume_file)

            # score that o.g.
            original_score, original_feedback = calculate_resume_score(original_text, job_input)

            # process the resume
            optimized_preview, suggestions, match_info, optimized_text = process_resume(resume_file, job_input)
            # optimized_text = result[1]

            # calculate optimized resume score
            optimized_score, optimized_feedback = calculate_resume_score(optimized_text, job_input)

            # create the comparison
            score_comparison = create_score_comparison(
                original_score, optimized_score,
                original_feedback, optimized_feedback
            )
            # deduct credits AFTER successfull processing
            update_user_credits(user_id, credits - 1)

            # return (*result, get_credits_display(email))
            return (optimized_preview, optimized_text, suggestions, score_comparison, get_credits_display(email))
        
        except Exception as free_error:
            print(f"🚨 Free user processing error: {free_error}")
            return (f"😩 Apologies, but there was an error in  processing your resume: {free_error}", "", "", "", get_credits_display(email))

def show_premium_welcome():
    """Show welcome message for new premium users"""
    return gr.HTML("""
    <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                color: white; padding: 25px; border-radius: 15px; text-align: center;
                margin: 20px 0; box-shadow: 0 8px 24px rgba(16, 185, 129, 0.3);">
        <h3 style="margin: 0 0 10px 0; font-size: 1.8em;">🎉 Welcome to Premium - We're Honored To Have You Here!</h3>
        <p style="margin: 0; font-size: 1.2em; opacity: 0.9;">
            Thank you for your subscription! You now have unlimited access to all ResumeWhip tools.
        </p>
    </div>
    """)

def refresh_user_interface(email):
    """ After payment, refresh interface based on current user status"""
    user_id, credits, status = get_or_create_user(email)
    is_premium = is_premium_user(user_id)
    
    if is_premium:
        return (
            get_credits_display(email),
            show_premium_welcome(),
            gr.update(visible=False)  # Hide upgrade prompts
        )
    else:
        return (
            get_credits_display(email), 
            gr.update(visible=False),  # Hide welcome message
            gr.update(visible=True)   # Show upgrade prompts
        )

def generate_cover_letter(resume_file, job_input):
    """Generate cover letter from resume and job description"""
    if not resume_file or not job_input.strip():
        return "⚠️ Please check that you've uploaded a resume and pasted in the job description."
    
    try:
        # Extract text from resume file
        resume_txt = extract_resume_text(resume_file)
        if not resume_txt:
            return "⚠️ For some reason, we could not extract text from the resume file. Please try again."
        
        prompt = cover_letter_prompt_creator(resume_txt, job_input)
        return get_cover_response(prompt)
    except Exception as e:
        return (f"🚩 Unexpected error in generating cover letter: {e}")
    
# def quick_job_summary(score):
#     if score >= 80:
#         return "✅ Job post looks legit! It scored 80% or higher on our validation run."
#     elif score >= 50:
#         return "⚠️ Only scored between a 50 and 79% on the validation run. Proceed with caution."
#     else:
#         return "❌ Waste of time. Couldn't even score a 49% on our validation run. Just an attempt to harvest your data."

# Score box

def quick_job_summary(score):
    if score >= 80:
        color = "#10b981"  # Green
        text = "✅ Go for it! Job post looks legit, scoring 80% or higher on our validation run.."
    elif score >= 50:
        color = "#f59e0b"  # Orange
        text = "⚠️ Only scored between a 50 and 79% on the validation run  - templated lingo, ghost-post maybe?"
    else:
        color = "#ef4444"  # Red
        text = "❌ High risk! We don't like it. Couldn't even score a 49% on our validation run. Likely data harvesting - Don't waste your time."
    
    return f"""
    <div style="background:{color}; color:white; padding:10px; 
                border-radius:8px; text-align:center; 
                font-weight:bold; font-size:1.1em; margin-bottom:10px;">
        {text}
    </div>
    """

# New Validate Job Posting

def validate_job_posting(job_description, company_name=None, job_title=None):
    if not job_description.strip():
        return "⚠️ Please paste a job description before validating.", ""

    # --- Scoring Logic ---
    score = 100
    warnings = []

    if "wire money" in job_description.lower() or "gift cards" in job_description.lower():
        score -= 50
        warnings.append("🚩 Mentions money transfer or gift cards.")
    if "no experience required" in job_description.lower():
        score -= 15
        warnings.append("⚠️ Very low barrier to entry may be suspicious.")
    if "urgent hire" in job_description.lower() or "act fast" in job_description.lower():
        score -= 10
        warnings.append("⚠️ Excessive urgency language detected.")
    if "training fee" in job_description.lower():
        score -= 30
        warnings.append("🚩 Mentions paying fees for training.")
    if job_description.lower().count("team player") > 2:
        score -= 5
        warnings.append("⚠️ Too many generic phrases like 'team player'.")

    score = max(score, 0)

    # --- Outputs ---
    summary_html = quick_job_summary(score)

    report_lines = []
    if company_name:
        report_lines.append(f"**Company:** {company_name}")
    if job_title:
        report_lines.append(f"**Job Title:** {job_title}")

    report_lines.append(f"**Score:** {score}/100")
    if warnings:
        report_lines.append("\n".join(warnings))
    else:
        report_lines.append("✅ No major red flags found.")

    full_report = "\n".join(report_lines)

    return summary_html, full_report

# Job Scoring

def calculate_resume_score(resume_text, job_description):
    """Calculate a resume score based on ATS-relevant factors"""
    score = 0
    max_score = 100
    feedback = []
    
    # Extract job keywords (filter out common words)
    stop_words = {'the', 'and', 'for', 'with', 'this', 'that', 'from', 'have', 'will', 'your', 'our', 'their'}
    job_keywords = set(word.lower() for word in job_description.split() 
                      if len(word) > 4 and word.isalpha() and word.lower() not in stop_words)
    resume_words = set(word.lower() for word in resume_text.split() 
                       if len(word) > 4 and word.isalpha())
    
    # 1. Critical Keyword Match (50 points) - MOST IMPORTANT
    keyword_matches = job_keywords.intersection(resume_words)
    match_rate = len(keyword_matches) / len(job_keywords) if job_keywords else 0
    keyword_score = min(50, int(match_rate * 50))
    score += keyword_score
    feedback.append(f"**Critical Keywords:** {keyword_score}/50 - Matched {len(keyword_matches)} of {len(job_keywords)} key terms ({int(match_rate*100)}%)")
    
    # 2. Impact Language (20 points)
    action_verbs = ['achieved', 'improved', 'increased', 'reduced', 'led', 'managed', 
                   'developed', 'created', 'designed', 'implemented', 'delivered', 
                   'optimized', 'generated', 'established', 'coordinated', 'executed']
    action_verb_count = sum(1 for verb in action_verbs if verb in resume_text.lower())
    action_score = min(20, action_verb_count * 3)
    score += action_score
    feedback.append(f"**Impact Language:** {action_score}/20 - {action_verb_count} strong action verbs")
    
    # 3. Quantifiable Results (20 points)
    import re
    # Look for percentages, dollar amounts, or numbers with context
    metrics = re.findall(r'\d+[%$,]|\$\d+|\d+\+|\d+x', resume_text)
    quant_score = min(20, len(metrics) * 4)
    score += quant_score
    feedback.append(f"**Quantifiable Results:** {quant_score}/20 - {len(metrics)} measurable achievements")
    
    # 4. Optimal Length (10 points) - Reward conciseness
    word_count = len(resume_text.split())
    if 250 <= word_count <= 600:
        length_score = 10
        feedback.append(f"**Length:** 10/10 - Optimal ({word_count} words)")
    elif 200 <= word_count < 250 or 600 < word_count <= 750:
        length_score = 7
        feedback.append(f"**Length:** 7/10 - Good ({word_count} words)")
    elif 150 <= word_count < 200 or 750 < word_count <= 900:
        length_score = 5
        feedback.append(f"**Length:** 5/10 - Could be better ({word_count} words)")
    else:
        length_score = 3
        feedback.append(f"**Length:** 3/10 - Too {'short' if word_count < 150 else 'long'} ({word_count} words)")
    score += length_score
    
    return score, feedback

def create_score_comparison(original_score, optimized_score, original_feedback, optimized_feedback):
    """Create a visual score comparison"""
    
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
    <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); 
                padding: 25px; border-radius: 15px; margin: 20px 0;">
        <h3 style="text-align: center; color: #495057; margin-bottom: 20px;">
            📊 Resume Analysis Report
        </h3>
        
        <div style="display: flex; justify-content: space-around; gap: 20px; margin-bottom: 25px;">
            <!-- Original Score -->
            <div style="flex: 1; background: white; padding: 20px; border-radius: 12px; 
                        text-align: center; border: 2px solid {orig_color};">
                <h4 style="color: #6b7280; margin: 0 0 10px 0;">Original Resume</h4>
                <div style="font-size: 3em; font-weight: 800; color: {orig_color}; margin: 10px 0;">
                    {original_score}
                </div>
                <div style="font-size: 1.2em; color: {orig_color}; font-weight: 700;">
                    Grade: {orig_grade}
                </div>
            </div>
            
            <!-- Arrow & Improvement -->
            <div style="display: flex; align-items: center; justify-content: center; flex-direction: column;">
                <div style="font-size: 2em; color: #10b981;">➡️</div>
                <div style="background: #10b981; color: white; padding: 8px 16px; 
                            border-radius: 20px; margin-top: 10px; font-weight: 700;">
                    +{improvement} points
                </div>
            </div>
            
            <!-- Optimized Score -->
            <div style="flex: 1; background: white; padding: 20px; border-radius: 12px; 
                        text-align: center; border: 2px solid {opt_color};">
                <h4 style="color: #6b7280; margin: 0 0 10px 0;">Optimized Resume</h4>
                <div style="font-size: 3em; font-weight: 800; color: {opt_color}; margin: 10px 0;">
                    {optimized_score}
                </div>
                <div style="font-size: 1.2em; color: {opt_color}; font-weight: 700;">
                    Grade: {opt_grade}
                </div>
            </div>
        </div>
        
        <!-- Detailed Breakdown -->
        <div style="background: white; padding: 20px; border-radius: 12px; margin-top: 20px;">
            <h4 style="color: #495057; margin-bottom: 15px;">📈 What Improved:</h4>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                <div>
                    <h5 style="color: #6b7280; margin-bottom: 10px;">Original Analysis:</h5>
                    {'<br>'.join(original_feedback)}
                </div>
                <div>
                    <h5 style="color: #10b981; margin-bottom: 10px;">Optimized Analysis:</h5>
                    {'<br>'.join(optimized_feedback)}
                </div>
            </div>
        </div>
    </div>
    """
    return comparison_html

# Admin for granting access
def admin_grant_access(email):
    """ Function to grant unlimited access for testing, marketing, etc. """
    user_id, credits, status = get_or_create_user(email)
    grant_unlimited_access(user_id)
    return f"Granted unlimited access to user: {user_id}"

# def handle_resume_optimize(email, resume_text, job_desc):
#     """Main handler for the Resume Optimizer button."""
#     try:
#         # ✅ log the user and IP
#         get_or_create_user(email)
#         track_ip_usage(get_user_ip())

#         # ✅ run existing optimizer
#         optimized_md, editable_text, tips, score_html = process_resume(
#             resume_text, job_desc
#         )

#         return optimized_md, editable_text, tips, score_html

    # except Exception as e:
    #     print(f"Error in handle_resume_optimize: {e}")
    #     return "⚠️ Error optimizing resume.", "", "", ""

    # except Exception as e:
    #     print(f"DEBUG: Optimization Error: {e}") # This prints to your server logs
    #     return f"⚠️ Error optimizing resume. Details: {e}" # This shows the error to the user
# for paid unlimited access

# Create Gradio interface
with gr.Blocks(title="ResumeWhip - AI Resume Optimizer | ATS-Friendly Resume Builder", 
               theme=gr.themes.Soft(), css=custom_css) as app:
    
    gr.HTML("<head><link rel='icon' href='favicon.png' type='image/png'></head>")
    
    # Header
    gr.Markdown("""
    <h1 style='text-align:center; color:#1e90ff;'>🏎️💨 Welcome To ResumeWhip!</h1>
    <h2 style='text-align:center; color:#dd1eff;'>The AI-Powered Resume Optimizer Meant to Whip ATS Systems</h2>
    <h2 style='text-align:center; color:#dd1eff;'>Get Your First 3 Resumes Free!</h2> 
    <h3 style='text-align:center;'>Powerful. Simple. Just Validate → Upload → Optimize → Apply!</h3>          
    """)

    with gr.Row():
        # Sidebar
        with gr.Column(scale=1):

            #placeholder text
            user_status = gr.Markdown("""<h5 style='text-align:center; color:#ff621e;'>Please enter your email to get started</h5>""", elem_id="user-status")

            with gr.Accordion("🦮 How To Use", open=False):
                gr.Markdown("""
                         1.) Crank Your Existing Resume Up To 11 - list every single skill and experience you have
                             (this is how our AI writes your resume and scores your chances);  
                         2.) Follow the Prompts To Load the Requested Info;  
                         3.) Choose Your Tool (you don't have to use all 3);  
                         4.) Proofread / Edit the Results Using the 'Copy/Pastes' below;  
                         5.) Download Your File as PDF; and  
                         6.) Apply!
                            """)
                
            with gr.Accordion("📚 Formatting Tips", open=False):
                gr.Code("""
If you're not happy with the default resume 
format, you can make adjustments using the 
simple copy and pastes below:
                        
Want To Change Fonts?  
# = Biggest  
## = Smaller  
### = Smallest
<b>text</b> = Bold  
<i>text</i> = Italic  
<u>text</u> = Underline
(⬆️ Can Be Combined As Needed)
                        
Making A List?  
- = Bullet Point  
1. = Numbered List

Want To Link A Website? 
Write it into your resume like this: 
[Your Website](https://www.yourwebsite.com)

Resume too "clumpy?"  
Double-space where you want the 
line to break (after a period, 
for example). 
                        
"I want a visible line between my resume sections!"  
Hit 'Enter' twice at the end of the section, 
type three dashes (---), hit 'Enter' two 
more times, and BOOM! Line between sections.

"But my resume cuts off where I don't want it to!"
Bummer. Wait! Just  force a new page by copy/pasting this entire 
line (below), and put it where you want one page to end
and the next to begin:
<div style="page-break-after: always; break-after: page;"></div>
                """, language="markdown")
                
            with gr.Accordion("❓ Frequently Asked Questions", open=False):
                gr.Markdown("""
        ### Common Questions About Resume Optimization
        
        **Q: What is an ATS?**  
        A: "Applicant Tracking System." It's an automated filter Recruiters use to sift through the deluge of resumes they receive for open job positions.
                            
        **Q: How does your Resume Optimizer and Cover Letter Writer work?**  
        A: Our AI pits your resume up against job descriptions and tailors its content, keywords, and formatting to match what ATS systems and recruiters look for.
        
        **Q: What makes ResumeWhip any different than the other resume optimizers?**
        A: Its code is written by job seekers with fellow jobseekers in mind. In double-blind studies, it consistently outperforms the competition (eg: LinkedIn's AI Resume Optimizer).
                                       
        **Q: Do optimized resumes really get more interviews?**  
        A1: Yes - ATS-optimized, job-specific resumes typically see 3-5x higher response rates than generic versions. AI ensures you never miss the keywords ATS systems use to qualify your resume.
        
        **Q: What file formats work best with the resume optimizer?**  
        A: We support PDF(.pdf), Word (.docx), Markdown (.md), and text (.txt) files.
        
        **Q: How many resumes can I optimize for free?**  
        A: You get 3 free resume optimizations to try our service, then unlimited access for $5.99/month.

        **Q: Why is the format of the resume I download look so plain?**  
        A: That's by design - ATS systems don't like a lot of formatting. (Tables and multiple columns? Nightmares for them.)
        """)

            sidebar_content = gr.HTML("")
            
            gr.Markdown("### 🛡️ We will never sell your data. Ever.")

            gr.Markdown("### 🔥 Share the love - help friends skip the job search struggle!")

            gr.HTML("""
                <div style="display:flex; flex-direction:column; gap:20px; margin-top:20px;">
                    
                    <!-- Clean logo-based sharing -->
                    <div style="display:flex; flex-direction:row; gap:20px; justify-content:center; align-items:center;">
                        
                        <!-- LinkedIn -->
                        <a href="https://www.linkedin.com/sharing/share-offsite/?url=https://resumewhip.com&summary=Finally%20found%20a%20resume%20tool%20that%20actually%20understands%20ATS%20systems%20🎯%20ResumeWhip%20uses%20AI%20to%20optimize%20resumes%20for%20each%20job%20posting.%20Getting%20way%20more%20interviews%20than%20generic%20resumes!" 
                           target="_blank" 
                           style="text-decoration: none; position: relative; display: inline-block;"
                           onmouseover="showTooltip(this, 'Help your network with the AI resume optimizer that outperforms LinkedIn\'s own tools!')"
                           onmouseout="hideTooltip(this)">
                            <img src="https://upload.wikimedia.org/wikipedia/commons/8/81/LinkedIn_icon.svg" 
                                 style="width:40px; height:40px; transition: transform 0.3s ease, filter 0.3s ease;"
                                 onmouseover="this.style.transform='scale(1.2)'; this.style.filter='brightness(1.2)';"
                                 onmouseout="this.style.transform='scale(1)'; this.style.filter='brightness(1)';">
                        </a>
                        
                        <!-- X/Twitter -->
                        <a href="https://x.com/intent/post?url=https://resumewhip.com&text=Just%20boosted%20my%20resume%27s%20ATS%20score%20by%2040%25%20with%20AI!%20🎯%20Finally%20getting%20callbacks%20instead%20of%20radio%20silence.%20ResumeWhip%20tailors%20resumes%20to%20each%20job%20-%203%20free%20tries!" 
                           target="_blank"
                           style="text-decoration: none; position: relative; display: inline-block;"
                           onmouseover="showTooltip(this, 'Tweet about AI resume success - your followers will thank you!')"
                           onmouseout="hideTooltip(this)">
                            <img src="https://upload.wikimedia.org/wikipedia/commons/c/ce/X_logo_2023.svg" 
                                 style="width:40px; height:40px; transition: transform 0.3s ease, filter 0.3s ease;"
                                 onmouseover="this.style.transform='scale(1.2)'; this.style.filter='brightness(1.2)';"
                                 onmouseout="this.style.transform='scale(1)'; this.style.filter='brightness(1)';">
                        </a>
                        
                        <!-- Facebook -->
                        <a href="https://www.facebook.com/sharer/sharer.php?u=https://resumewhip.com&quote=Stop%20sending%20resumes%20into%20the%20void!%20🎯%20This%20AI%20tool%20actually%20gets%20you%20past%20the%20bots%20and%20tailors%20resumes%20in%2030%20seconds.%20Game%20changer%20for%20job%20hunting!" 
                           target="_blank" 
                           style="text-decoration: none; position: relative; display: inline-block;"
                           onmouseover="showTooltip(this, 'Share the secret to beating ATS systems with friends and family!')"
                           onmouseout="hideTooltip(this)">
                            <img src="https://upload.wikimedia.org/wikipedia/commons/0/05/Facebook_Logo_%282019%29.png" 
                                 style="width:40px; height:40px; transition: transform 0.3s ease, filter 0.3s ease;"
                                 onmouseover="this.style.transform='scale(1.2)'; this.style.filter='brightness(1.2)';"
                                 onmouseout="this.style.transform='scale(1)'; this.style.filter='brightness(1)';">
                        </a>
                        
                        <!-- Reddit -->
                        <a href="https://www.reddit.com/submit?url=https://resumewhip.com&title=Found%20an%20AI%20tool%20that%20actually%20gets%20resumes%20past%20ATS%20bots%20🤖➡️👤&text=Tired%20of%20sending%20resumes%20into%20the%20void?%20ResumeWhip%20uses%20AI%20to%20tailor%20resumes%20to%20job%20postings%20and%20beat%20ATS%20systems.%20Finally%20getting%20responses!" 
                           target="_blank"
                           style="text-decoration: none; position: relative; display: inline-block;"
                           onmouseover="showTooltip(this, 'Help Your Reddit friends beat ATS systems and land their dream jobs!')"
                           onmouseout="hideTooltip(this)">
                            <img src="https://cdn.simpleicons.org/reddit/FF4500" 
                                 style="width:40px; height:40px; transition: transform 0.3s ease, filter 0.3s ease;"
                                 onmouseover="this.style.transform='scale(1.2)'; this.style.filter='brightness(1.2)';"
                                 onmouseout="this.style.transform='scale(1)'; this.style.filter='brightness(1)';">
                        </a>
                        
                    </div>
                
                <!-- JavaScript for clean hover tooltips -->
                <script>
                function showTooltip(element, message) {
                    // Remove any existing tooltip
                    hideTooltip(element);
                    
                    // Create tooltip
                    const tooltip = document.createElement('div');
                    tooltip.className = 'custom-tooltip';
                    tooltip.innerHTML = message;
                    tooltip.style.cssText = `
                        position: absolute;
                        bottom: 50px;
                        left: 50%;
                        transform: translateX(-50%);
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 8px 12px;
                        border-radius: 6px;
                        font-size: 0.8em;
                        font-weight: bold;
                        white-space: nowrap;
                        z-index: 1000;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                        animation: fadeIn 0.3s ease;
                    `;
                    
                    element.appendChild(tooltip);
                }
                
                function hideTooltip(element) {
                    const existing = element.querySelector('.custom-tooltip');
                    if (existing) {
                        existing.remove();
                    }
                }
                
                // Add CSS for fade-in animation
                const style = document.createElement('style');
                style.textContent = `
                    @keyframes fadeIn {
                        from { opacity: 0; transform: translateX(-50%) translateY(5px); }
                        to { opacity: 1; transform: translateX(-50%) translateY(0); }
                    }
                `;
                document.head.appendChild(style);
                </script>
                """)

        # Main content
        with gr.Column(scale=5):
            # Input section
            with gr.Row():
                email_input = gr.Textbox(
                    label="📧 Please enter your email to get started. Don't worry: it never leaves our database.",
                    placeholder="you@example.com",
                    elem_id = "email-box"
                    )
                
                resume_input = gr.File(
                    label="📄 Upload Resume Here", 
                    file_types=[".pdf", ".docx", ".md", ".txt"]
                )
                company_input = gr.Textbox(
                    label="🏢 Enter the Company's Name", 
                    placeholder="e.g., Amazon, Barnes & Noble"
                )
            
            job_input = gr.Textbox(
                label="📋 Job Description (Please Paste Full Text)", 
                lines=6,
                placeholder="Paste the complete job posting here..."
            )

            # email_input = gr.Textbox(
            #     label="📧 Please enter your email to get started. Don't worry: it never leaves our database.",
            #     placeholder="you@example.com",
            #     elem_id = "email-box"
            #     )

            # Credit counter
            # resume_counter = gr.Markdown("### Free Resumes Left: --")
            # just a visual check here. if I don't like it, go back to the resume_counter above
            # resume_counter = get_credits_display(email)

            # Access granter
            with gr.Accordion("My Admin Access", open=False, visible=False):
                grant_access_btn = gr.Button("🟢 Grant Unlimited Access", variant="secondary")
                manage_billing_btn = gr.Button("Manage Billing", variant="secondary")
                access_status = gr.Markdown()
                billing_url_output = gr.Markdown()

            # Tools Available
            # gr.Markdown("<h2 style='text-align:center; color:#ff7f50;'>🧰 Tools In the Toolkit</h2>")
            # Replace your existing tool buttons HTML section with this updated version:

# Replace your existing tool buttons HTML section with this updated version:

            gr.HTML("""
            <div style="text-align: center; margin: 30px 0;">
                <h2 style="font-size: 2.2em; color: #495057; font-weight: 700; margin-bottom: 15px;">
                    🧰 Tools In the Toolkit
                </h2>
                <p style="font-size: 1.1em; color: #6c757d; margin-bottom: 30px;">
                    <b>Choose your tool using the tabs below - each one gives your resume an edge in today's job search.</b>
                </p>
            </div>
        """)
            
            # with gr.Row():
            #     email_input = gr.Textbox(
            #         label="📧 Please enter your email to get started. Don't worry: it never leaves our database.",
            #         placeholder="you@example.com",
            #         lines=1
            #     )

            # Tools tabs
            # with gr.Tabs():
            #     with gr.TabItem("✅ Job Validator"):
            #         job_description = gr.Textbox(label="Job Description", lines=6)
            #         company_name = gr.Textbox(label="Company Name")
            #         job_title = gr.Textbox(label="Job Title")
            #         validate_btn = gr.Button("Whip Up the Job Validator!")

            #         # Two separate outputs now
            #         summary_output = gr.HTML()
            #         report_output = gr.Markdown()

            #==================== Old Validator Code ============
            with gr.Tabs():
                with gr.TabItem("✅ JOB VALIDATOR"):
                    with gr.Row():
                        jd_date = gr.Textbox(
                            label="📅 Posting Date (Best Guess, Anyway.)", 
                            placeholder="YYYY-MM-DD (e.g., 2024-12-01)"
                        )
                        jd_title = gr.Textbox(
                            label="💼 Job Title", 
                            placeholder="e.g., Data Scientist, Welder"
                        )
                    validate_btn = gr.Button("🤖 Whip Up the Job Validator!", variant="primary")
                    summary_output = gr.HTML()
                    report_output = gr.Markdown()
                    # validation_output = gr.Markdown()
            #======================================================

                with gr.TabItem("🎯 RESUME OPTIMIZER"):
                    run_resume = gr.Button("🪄 Whip Up the Resume Optimizer! (Takes About 30 Seconds.)", variant="primary")
                    
                    # process_resume outputs
                    # resume_md = gr.Markdown(label="Here's A Preview of Your Optimized Resume")
                    # suggestions = gr.Markdown(label="Suggestions & Tips")
                    # score_comparison = gr.Markdown(label = "📊 Resume Match Score")
                    # resume_edit = gr.Textbox(label="✏️ Edit Your Resume Here (optional)", lines=15)
                    # resume_counter = gr.Markdown(label = "🫘 Resume Counter")
                    resume_md = gr.Markdown(label="Here's A Preview of Your Optimized Resume")
                    resume_edit = gr.Textbox(label="✏️ Edit Your Resume Here (optional)", lines=15)
                    suggestions = gr.Markdown(label="Suggestions & Tips")
                    score_comparison = gr.HTML(label = "📊 Resume Match Score")
                    resume_counter = gr.Markdown(label = "🫘 Resume Counter")
                    with gr.Row():
                        export_resume_btn = gr.Button(
                            "📍 Click Here To Download Your Resume As PDF",
                            elem_classes = "download-btn-green"
                            )
                        export_resume_result = gr.File()

                with gr.TabItem("📝 COVER LETTER WRITER"):
                    run_cover = gr.Button("📝 Whip Up the Cover Letter Writer!", variant="primary")
                    cover_output = gr.Textbox(
                            label="Here's Your Cover Letter. Edit Where Needed To Give It Your Voice.", 
                            lines=15
                        )
                    with gr.Row():
                            export_cover_btn = gr.Button(
                                "📍 Click Here To Download Your Cover Letter As PDF",
                                elem_classes = "download-btn-green"
                                )
                            export_cover_result = gr.File()

            gr.HTML("""
                    <div style="
                        text-align: center;
                        margin: 20px 0;
                        padding: 15px;
                        background: linear-gradient(135deg, #5b63ff 0%, #845bff 100%);
                        border-radius: 15px;
                        color: white;
                        font-size: 1.1em;
                        font-weight: 600;
                        border: 3px solid #fff;
                        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.3);
                    ">
                        ⚡ Tip: Job post sound fishy? Use our Job Validator to check if it's legit before worrying about applying! ⚡
                    </div>
                 """)  

    # Footer for SEO
    gr.HTML("""
            <footer style = "margin-top: 50px; padding: 30px 20px; border-top: 2px solid #eee;
                            background: linear-gradient(135deg, #f8f9a 0%, #e9ecef 100%);")
            
                <!-- Main footer content -->
                <div style="max-width: 1200px; margin: 0 auto; text-align: center;">
            
                    <!-- Key links -->
                    <div style="margin-bottom: 25px;">
                        <a href="mailto:support@resumewhip.com"
                            style="margin: 0 20px; color: #1e90ff; text-decoration: none; font-weight: 500;">
                            📧 Contact Support
                        </a>
                        <a href="https://buy.stripe.com/cNi9ASgWl6C614l3Ja1Jm00"
                            style="margin: 0 20px; color: #635BFF; text-decoration: none; font-weight: 500;">
                            💳 Upgrade to Premium
                        </a>
                        <a href="https://resumewhip.com/blog"
                            style="margin: 0 20px; color: #1e90ff; text-decoration: none; font-weight: 500;">
                            📖 Resume Tips Blog
                        </a>
                    </div>
            
                    <!-- Value proposition -->
                    <div style="margin-bottom: 20px; color: #495057;">
                        <h3 style="color: #343a40; margin-bottom: 10px;">
                            🏎️💨 ResumeWhip - The AI Resume Optimizer That Actually Works
                        </h3>
                        <p style="font-size: 1.1em; line-height: 1.4; max-width: 600px; margin: 0 auto;">
                            <b>About Us:</b> We were job seekers proficient in our fields and great with people,
                            but also job seekers who had an extremely hard time getting past ATS Systems. 
                            So, we created a resume optimizer that consistently outperforms 
                            Premium Job Platform Services by over 40%. 
                           <b>We're in the business of getting people past machines.</b>
                        </p>
                    </div>
            
                    <!-- Trust signals -->
                    <div style="display: flex; justify-content: center; gap: 30px; margin-bottom: 25px;
                                flex-wrap: wrap; color: #6c757d; font-size: 0.9em;">
                                        <div>🛡️ We never share or sell your data</div>
                                        <div>⚡ 30-second resume optimization</div>
                                        <div>🎯 40% higher ATS compatibility</div>
                                        <div>💼 Works with all job boards</div>
                    </div>

                    <!-- Copyright and keywords -->
                    <div style="border-top: 1px solid #dee2e6; padding-top: 20px;">
                        <p style="color: #6c757d; font-size: 0.95em; margin-bottom: 10px;">
                            © 2025 ResumeWhip - AI-Powered Resume Optimization Tool
                        </p>
                        <p style="color: #adb5bd; font-size: 0.8em; line-height: 1.3;">
                            Keywords: AI resume optimizer, ATS resume checker, resume builder, cover letter generator, 
                            job application tool, interview preparation, career advancement, resume writing service
                        </p>
                    </div>
                
                </div>
            </footer>
            """)
    
    # Event handlers

    email_input.submit(
        fn=lambda email: (
            get_or_create_user(email),
            get_user_status(email),
            get_credits_display(email),
            get_sidebar_content(email)
        ),
        inputs=[email_input],
        outputs=[user_status, resume_counter, sidebar_content]
    )
    
    validate_btn.click(
        fn=lambda job_desc, company, title, email: (
            ensure_user_logged(email) if email else None,
            validate_job_posting(job_desc, company, title)
        )[1] if email else ("🚨 Please enter your email first", ""),
        inputs=[job_input, company_input, jd_title, email_input],
        outputs=[summary_output, report_output]
    )

    # run_resume.click(
    #     fn = lambda resume, job, email: (
    #         get_or_create_user(email), 
    #         run_resume_with_credits_with_scoring(resume, job, email)
    #     )[1],
    #     inputs=[resume_input, job_input, email_input],
    #     outputs=[resume_md, resume_edit, suggestions, score_comparison, resume_counter]
    # )
    
    run_resume.click(
        fn=run_resume_with_credits_with_scoring,
        inputs=[resume_input, job_input, email_input],
        outputs=[resume_md, resume_edit, suggestions, score_comparison, resume_counter]
    )

    manage_billing_btn.click(
        fn=open_billing_portal,
        inputs=[email_input],
        outputs=billing_url_output
    )
    
    export_resume_btn.click(
        fn=export_resume,
        inputs=[resume_edit, company_input],
        outputs=export_resume_result
    )
    
    run_cover.click(
        fn=lambda resume, job, email: (
            get_or_create_user(email),  # 🔑 force email logging
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

    # # Admin event handler (for testing)
    # admin_input = gr.Textbox(label="User Email or ID")

# =========================================================================
# Add the code below for free access to users for testing (like Mia, etc.)
    # grant_access_btn.click(
    #     fn=admin_grant_access,
    #     inputs=[email_input],
    #     outputs=access_status
    # )
# =========================================================================

def run_fastapi():
    """ Function to run the FASTAPI server for webhooks. """
    uvicorn.run(
        fastapi_app, 
        host="0.0.0.0", 
        port=int(os.environ.get("WEBHOOK_PORT", 5000)),
        log_level="info"
    )

# Mounting Gradio Inside FastAPI
fastapi_app = gr.mount_gradio_app(fastapi_app, app, path="/")

if __name__ == "__main__":
    import os
    print(f"Current working directory: {os.getcwd()}")
    print(f"Database will be at: {os.path.abspath('resumewhip.db')}")
    # Initialize the database
    init_database()
    uvicorn.run(
        fastapi_app, 
        host = "0.0.0.0",
        port = int(os.environ.get("PORT", 8000))
        )
