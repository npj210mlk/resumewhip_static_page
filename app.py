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
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

# button styling
custom_css = """
<style>
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
</style>
"""
# custom_css = """
# <style>
# .tab-nav {
#     display: flex;
#     justify-content: center;
#     margin-bottom: 20px;
#     border-bottom: none !important;
# }

# .tab-nav button {
#     background: linear-gradient(135deg, #667eea, #764ba2);
#     color: white !important;
#     font-weight: bold;
#     font-size: 1.2em;
#     border-radius: 12px;
#     margin: 0 8px;
#     padding: 14px 28px;
#     border: none !important;
#     cursor: pointer;
#     transition: transform 0.2s ease, box-shadow 0.2s ease;
# }

# .tab-nav button:hover {
#     transform: translateY(-2px);
#     box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
# }

# .tab-nav button.selected {
#     background: linear-gradient(135deg, #ff7f50, #ff6b35);
#     box-shadow: 0 6px 20px rgba(255, 127, 80, 0.5);
# }
# </style>
# """

# get new SQLite connection for each request
def get_db_connection():
    """ Function to let FastAPI handle multiple requests to prevent db lockup"""
    conn = sqlite3.connect("resumewhip.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

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
    conn = sqlite3.connect('resumewhip.db')
    cursor = conn.cursor()
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                email TEXT,
                subscription_status TEXT DEFAULT 'free',
                credits_remaining INTEGER DEFAULT 3,
                stripe_customer_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_payment_date TIMESTAMP
            )
        ''')
        
    conn.commit()
    conn.close()

def get_user_id():
    """Generate a persistent session-based user ID"""
    # Use Gradio's session state if available, otherwise create persistent ID
    if hasattr(gr, 'current_user_id') and gr.current_user_id:
        return gr.current_user_id
    
    # Create new user ID and store in session
    user_id = str(uuid.uuid4())
    gr.current_user_id = user_id
    return user_id

def get_user_status():
    user_id = get_user_id()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT subscription_status, credits_remaining FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return "Free User – You've Got 3 Free Resumes Remaining"
    
    status, credits = row["subscription_status"], row["credits_remaining"]
    if status in ["paid", "premium"] or credits == -1:
        return "🌟 Premium User – Unlimited Resumes Granted!"
    else:
        return f"Free User – {credits if credits is not None else 3} Free Resumes Remaining"


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

def create_checkout_session():
    try:
        user_id = get_user_id()
        user_email = get_user_email_from_db(user_id)
        customer_id = get_stripe_customer_id_from_db(user_id)
        session = stripe.checkout.Session.create(
            client_reference_id=user_id,
            customer = customer_id if customer_id else None,
            customer_email = user_email if not customer_id else None,
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
        return f"Error creating checkout session: {e}"

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

def open_billing_portal():
    user_id = get_user_id()
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
            (user_id, 3, 'free')
        )
    else:
        cursor.execute(
        "UPDATE users SET subscription_status = 'free' WHERE user_id = ?",
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
            email = session.get("customer_details", {}).get("email")
            
            if user_id and customer_id:
                store_stripe_customer_id(user_id, customer_id, email)
                grant_unlimited_access(user_id)
                print(f"✅ Granted unlimited access to user: {user_id}")

        # ❌ Handle subscription cancellations
        elif event["type"] == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            customer_id = subscription["customer"]
            user_id = get_user_id_by_customer_id(customer_id)

            if user_id:
                revoke_unlimited_access(user_id)
                print(f"❌ Revoked access for user: {user_id}")

        else:
            print(f"ℹ️ Unhandled event type: {event['type']}")

        # Return success so Stripe stops retrying
        return JSONResponse(content={"status": "success"}, status_code=200)

    except stripe.error.SignatureVerificationError as e:
        print(f"🚨 Invalid signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    except Exception as e:
        print(f"🚨 Webhook error: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=400)

def run_resume_with_credits(resume_file, job_input):
    """Handle resume processing with credit system - abuse prevent"""
    if not resume_file or not job_input.strip():
        return ("⚠️ Please upload your resume and paste the job description they've provided.", "", "", "Free resumes left: -")
    
    user_id = get_user_id()

    ip_address = request.remote_addr if request else "unknown"
    if not check_rate_limit(ip_address):
        return "Daily free limit reached. Upgrade to Premium for unlimited access!"
     
    # Check subscription status from database
    credits, subscription_status = get_user_credits(user_id)
    
    # Double-check with Stripe for premium users
    if subscription_status in ['paid', 'premium'] or check_payment_status(user_id):
        credits = float("inf")
        if subscription_status != 'premium':
            update_user_credits(user_id, float("inf"), 'premium')
            user_status.update(get_user_status())
    
    # Generate unique resume ID for tracking
    resume_name = getattr(resume_file, "name", "unknown")
    new_resume_id = f"{resume_name}_{hash(job_input)}"
    
    # Check if this is a new resume (consumes credit) or edit of existing one
    current_resume = user_sessions.get(f"{user_id}_current_resume")
    
    if current_resume != new_resume_id:
        if credits != float("inf"):
            if credits <= 0:
                checkout_url = create_checkout_session()
                return (
                    f"⏰ You've used your 3 free resumes! Ready for unlimited access? [Subscribe here]({checkout_url}) for just $5.99/month!",
                    "", "", "Free resumes left: 0"
                )
            credits -= 1
            update_user_credits(user_id, credits)
            user_status.update(get_user_status())
        
        user_sessions[f"{user_id}_current_resume"] = new_resume_id
    
    # Process resume
    try:
        result = process_resume(resume_file, job_input)
        # log successful request so free runs are counted
        log_request(user_id, ip_address)
        credits_display = '∞' if credits == float('inf') else str(credits)
        return (*result, f"Free resumes left: {credits_display}")
    except Exception as e:
        print(f"Resume processing error: {e}")
        return (f"Error processing resume: {e}", "", "", f"Free resumes left: {credits}")

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
        return f"🚩 Unexpected error in generating cover letter: {e}"
    
def quick_job_summary(score):
    if score >= 80:
        return "✅ Job post looks legit! It scored 80% or higher on our validation run."
    elif score >= 50:
        return "⚠️ Only scored between a 50 and 79% on the validation run. Proceed with caution."
    else:
        return "❌ Waste of time. Couldn't even score a 49% on our validation run. Just an attempt to harvest your data."

def validate_job_posting(job_input_text, posting_date, company, job_title):
    """Validate job posting legitimacy"""
    # Fixed logic - check if fields are empty (not inverted)
    if not company.strip():
        return "⚠️ Please enter a company name to validate the job posting."
    
    if not job_input_text.strip():
        return "⚠️ Please paste the job description to validate."
    
    if not posting_date.strip():
        return "⚠️ Please provide a job posting date (YYYY-MM-DD format)."
    
    try:
        # Validate job posting
        recent = is_posting_recent(posting_date)
        template_flag = template_detector(job_input_text)
        urgency_flag = detect_urgency_language(job_input_text)
        social_links = mentioned_on_socials(company, job_title or "")
        
        report = "### 🕐 Posting Date Check:\n"
        report += "✅ Yup, the job looks recent (posted within 60 days).\nIn this market, jobs don't stay open for more than that." if recent else "⚠️ Warning: Job may be outdated (older than 60 days).\nCould be they're just harvesting candidates."
        
        report += "\n### 🤖 Template Language Check:\n"
        report += "⚠️ Generic/template language detected - proceed with caution.\nCould be just a cattle call for info to keep on file." if template_flag else "✅ Posting appears specific and legitimate - as if an actual person wrote it and they have an actual need.\n"
        
        report += "\n### ⚡ Urgency Language Check:\n"
        report += "⚠️ Urgency language detected - be cautious of scams.\nCheck the post for poor grammar, unrealistic salary / work expectations, and that 'too good to be true' feel." if urgency_flag else "✅ No suspicious urgency language found.\nSeems like a real job posting."
        
        report += "\n### 🔍 Verify the Job / Company on Social Media:\n"
        report += f"- [Search on X/Twitter]({social_links['x']})\n"
        report += f"- [Search on LinkedIn]({social_links['linkedin']})\n"
        
        summary = quick_job_summary(job_score)
        return f"### {summary}\n\nFull Report:\n{report}"

        
    except Exception as e:
        return f"🚩 Error validating job posting: {e}"

# Admin for granting access
def admin_grant_access(user_email_or_id):
    """ Function to grant unlimited access """
    user_id = get_user_id()
    grant_unlimited_access(user_id)
    return f"Granted unlimited access to user: {user_id}"

# # Sticky buy button + banner (add before "with gr.Blocks()")
# sticky_buy_button = """
# <div style="position:fixed; top:10px; right:20px; z-index:9999; text-align:center;">
#     <a href="https://buy.stripe.com/cNi9ASgWl6C614l3Ja1Jm00" target="_blank" 
#        style="background-color:#ff7f50; color:white; padding:12px 20px; 
#               text-decoration:none; border-radius:8px; font-size:1em; 
#               font-weight:bold; box-shadow:0px 2px 6px rgba(0,0,0,0.2);">
#         ♾️ Unlimited Resume Optimization — $5.99/mo
#     </a>
#     <div style="font-size:0.8em; color:#333; margin-top:4px;">
#         Trusted by 200+ job seekers
#     </div>
# </div>
# """

# Create Gradio interface
with gr.Blocks(title="ResumeWhip - AI Resume Optimizer | ATS-Friendly Resume Builder", theme=gr.themes.Soft(), css=custom_css) as app:
    
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

            user_status = gr.Markdown(get_user_status(), elem_id="user-status")

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
                
            # Subscribe button
            gr.HTML("""
            <div style="text-align:center; margin:20px 0;">
                <a href="https://buy.stripe.com/cNi9ASgWl6C614l3Ja1Jm00" 
                   target="_blank" 
                   style="background-color:#635BFF; color:white; padding:15px 25px; 
                          text-decoration:none; border-radius:8px; font-size:1.1em; 
                          font-weight:bold; display:inline-block;">
                    ♾️ Get Unlimited AI-Powered Resume Optimization for Just $5.99/Month!
                </a>
            </div>
            """)

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
            
            # Credit counter
            resume_counter = gr.Markdown("### Free Resumes Left: 3")

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

            # Tools tabs
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
                    validation_output = gr.Markdown()


                with gr.TabItem("🎯 RESUME OPTIMIZER"):
                    run_resume = gr.Button("🪄 Whip Up the Resume Optimizer!", variant="primary")
                    resume_md = gr.Markdown(label="Preview")
                    resume_edit = gr.Textbox(label="✏️ Edit Your Resume Here (optional)", lines=15)
                    suggestions = gr.Markdown(label="Suggestions & Tips")
                    with gr.Row():
                        export_resume_btn = gr.Button("Download Your Resume As PDF ➡️")
                        export_resume_result = gr.File()

                with gr.TabItem("📝 COVER LETTER WRITER"):
                    run_cover = gr.Button("📝 Whip Up the Cover Letter Writer!", variant="primary")
                    cover_output = gr.Textbox(
                            label="Here's Your Cover Letter. Edit Where Needed To Give It Your Voice.", 
                            lines=15
                        )
                    with gr.Row():
                            export_cover_btn = gr.Button("Download Your Cover Letter As PDF ➡️")
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
                            <span class="bold-text">About Us:</span> We were job seekers proficient in our fields and great with people,
                            but also job seekers who had an extremely hard time getting past ATS Systems. 
                            So, we created a resume optimizer that consistently outperforms 
                            Premium Job Platform Services by over 40%. 
                            <span class="bold-text">We're in the business of getting people past machines.</span>
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
   
    validate_btn.click(
        fn=validate_job_posting,
        inputs=[job_input, jd_date, company_input, jd_title],
        outputs=validation_output
    )
    
    run_resume.click(
        fn=run_resume_with_credits,
        inputs=[resume_input, job_input],
        outputs=[resume_md, resume_edit, suggestions, resume_counter]
    )

    manage_billing_btn.click(
        fn=open_billing_portal,
        inputs=[],
        outputs=billing_url_output
    )
    
    export_resume_btn.click(
        fn=export_resume,
        inputs=[resume_edit, company_input],
        outputs=export_resume_result
    )
    
    run_cover.click(
        fn=generate_cover_letter,
        inputs=[resume_input, job_input],
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
    #     inputs=[admin_input],
    #     outputs=access_status
    # )
# =========================================================================

# Stripe webhook endpoint (if needed)
# def handle_stripe_webhook(request_data):
#     """Handle Stripe webhook for subscription confirmation and storage"""
#     try:
#         endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
#         event = stripe.Webhook.construct_event(
#             request_data['payload'],
#             request_data['signature'],
#             endpoint_secret
#         )
        
#         if event["type"] == "checkout.session.completed":
#             session = event["data"]["object"]
#             user_id = session.get("client_reference_id")
#             customer_id = session.get("customer")

#             # store Stripe customer / user id
#             if user_id and customer_id:
#                 store_stripe_customer_id(user_id, customer_id)
#                 grant_unlimited_access(user_id)
        
#         # handle subscription cancellation
#         elif event["type"] == "customer.subscription.deleted":
#             subscription = event["data"]["object"]
#             customer_id = subscription["customer"]

#             # revoke acess
#             user_id = get_user_id_by_customer_id(customer_id)
#             if user_id:
#                 revoke_unlimited_access(user_id)
                
#         return {"status": "success"}
#     except Exception as e:
#         return {"status": "error", "message": str(e)}

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
    # Initialize the database
    init_database()
    uvicorn.run(
        fastapi_app, 
        host = "0.0.0.0",
        port = int(os.environ.get("PORT", 8000))
        )
    # # Verify environment variables
    # required_env_vars = ["STRIPE_SECRET_KEY", "PRICE_ID", "STRIPE_WEBHOOK_SECRET"]
    # missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    # if missing_vars:
    #     print(f"⚠️ Missing required environment variables: {missing_vars}")
    
    # # Start the webhook server in background
    # webhook_thread = threading.Thread(target=run_fastapi, daemon=True)
    # webhook_thread.start()

    # print("🚀 Whipping Up ResumeWhip...")
    # webhook_port = os.environ.get("WEBHOOK_PORT", 5000)
    # print(f"🔗 Webhook endpoint: http://your-domain.com:{webhook_port}/webhook")

    # # Launch Gradio
    # port = int(os.environ.get("PORT", 7860))
    # app.launch(
    #     server_name="0.0.0.0",
    #     server_port=port,
    #     show_error=True,
    #     share=False
    # )
# ================================ #
# ------ Final Code Above -------
# ================================ #
# import sqlite3
# import gradio as gr
# import os
# import stripe
# import pdfplumber
# import uuid
# import json
# from datetime import datetime
# from new_functions import (
#     extract_resume_text,
#     sanitize_input,
#     prompt_creator,
#     get_resume_response,
#     process_resume,
#     export_resume,
#     cover_letter_prompt_creator,
#     get_cover_response,
#     save_cover_letter,
#     is_posting_recent,
#     template_detector,
#     mentioned_on_socials,
#     detect_urgency_language
# )

# # Stripe setup
# stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
# PRICE_ID = os.getenv("PRICE_ID")

# # Simple in-memory storage
# user_credits = {}
# active_resumes = {}
# # track users who've paid
# paid_users = set()

# FREE_CREDITS = 3

# def get_user_id():
#     """Generate a session-based user ID"""
#     # For Gradio, we'll use a simple session state approach
#     if not hasattr(gr, '_current_user_id'):
#         gr._current_user_id = str(uuid.uuid4())
#     return gr._current_user_id

# def create_checkout_session():
#     try:
#         user_id = get_user_id()
#         session = stripe.checkout.Session.create(
#             client_reference_id=user_id,
#             payment_method_types=['card'],
#             line_items=[{
#                 'price': PRICE_ID,
#                 'quantity': 1,
#             }],
#             mode='subscription',
#             success_url="https://www.resumewhip.com/success",
#             cancel_url="https://resumewhip.com/cancel"
#         )
#         return session.url
#     except Exception as e:
#         return f"Error creating checkout session: {e}"
    
# def check_payment_status(user_id):
#     """ Function to check if the user has paid for the service using Stripe's API """
#     try:
#         # check db for stored id
#         customer_id = get_stripe_customer_id_from_db(user_id)
#         if not customer_id:
#             return False
        
#         # verify subscription with Stripe
#         subscriptions = stripe.Subscription.lis(
#             customer=customer_id,
#             status='active', 
#             limit=1
#         )

#         # see if they already have a subscription
#         if subscriptions.data:
#             subscription = subscriptions.data[0]

#             # make sure that subscription is for my product
#             if subscription.items.data[0].price.id == PRICE_ID:
#                 return True
        
#         return False
    
#     except stripe.error.StripeError as e:
#         print(f"Stripe error in checking subscription: {e}")
#         return False
    
#     except Exception as e:
#         print(f"Error in checking your payment status: {e}")
#         return False
    
#     # return user_id in paid_users

# def get_stripe_customer_id_from_db(user_id):
#     """
#     Get the Stripe customer ID from SQLite db
#     """
#     conn = sqlite3.connect('resumewhip.db')
#     cursor = conn.cursor()
    
#     cursor.execute('SELECT stripe_customer_id FROM users WHERE user_id = ?', (user_id,))
#     result = cursor.fetchone()
#     conn.close()
    
#     return result[0] if result and result[0] else None

# def store_stripe_customer_id(user_id, customer_id):
#     """
#     Store Stripe customer ID in SQLite when they first subscribe
#     """
#     conn = sqlite3.connect('resumewhip.db')
#     cursor = conn.cursor()
    
#     cursor.execute('''
#         UPDATE users SET stripe_customer_id = ? WHERE user_id = ?
#     ''', (customer_id, user_id))
    
#     conn.commit()
#     conn.close()

# def grant_unlimited_access(user_id):
#     """ If they've paid, they get full access """
#     paid_users.add(user_id)
#     user_credits[user_id] = float("inf")

# def get_user_credits(user_id):
#     conn = sqlite3.connect('resumewhip.db')
#     cursor = conn.cursor()
    
#     cursor.execute('SELECT credits_remaining, subscription_status FROM users WHERE user_id = ?', (user_id,))
#     result = cursor.fetchone()
    
#     if not result:
#         # New user - create entry
#         cursor.execute('INSERT INTO users (user_id, credits_remaining) VALUES (?, 3)', (user_id,))
#         conn.commit()
#         conn.close()
#         return 3, 'free'
    
#     conn.close()
#     return result[0], result[1]

# def update_user_credits(user_id, credits, subscription_status='free'):
#     conn = sqlite3.connect('resumewhip.db')
#     cursor = conn.cursor()
    
#     cursor.execute('''
#         INSERT OR REPLACE INTO users (user_id, credits_remaining, subscription_status) 
#         VALUES (?, ?, ?)
#     ''', (user_id, credits, subscription_status))
    
#     conn.commit()
#     conn.close()

# def run_resume_with_credits(resume_file, job_input):
#     """Handle resume processing with credit system"""
#     if not resume_file or not job_input.strip():
#         return ("⚠️ Please upload your resume and paste the job description they've provided.", "", "", "Free resumes left: -")
    
#     user_id = get_user_id()

#     # check on subscription
#     if check_payment_status(user_id):
#         credits = float("inf")
#         user_credits[user_id] = credits
#     else:
#         credits = user_credits.get(user_id, FREE_CREDITS)
    
#     # Generate unique resume ID
#     resume_name = getattr(resume_file, "name", "unknown")
#     new_resume_id = f"{resume_name}_{hash(job_input)}"
    
#     # Check if this is a new resume (consumes credit) or edit of existing one
#     if active_resumes.get(user_id) != new_resume_id:
#         if credits != float("inf"):
#             if credits <= 0:
#                 checkout_url = create_checkout_session()
#                 return (
#                     f"⏰ You've used your 3 free resumes! Ready for unlimited access? [Subscribe here]({checkout_url}) for just $5.99/month!",
#                     "", "", "Free resumes left: 0"
#                 )
#             credits -= 1
#             user_credits[user_id] = credits
#         active_resumes[user_id] = new_resume_id
    
#     # Process resume
#     try:
#         result = process_resume(resume_file, job_input)
#         credits_display = '∞' if credits == float('inf') else str(credits)
#         return (*result, f"Free resumes left: {credits_display}")
#     except Exception as e:
#         return (f"Error processing resume: {e}", "", "", f"Free resumes left: {credits}")

# def generate_cover_letter(resume_file, job_input):
#     """Generate cover letter from resume and job description"""
#     if not resume_file or not job_input.strip():
#         return "⚠️ Please check that you've uploaded a resume and pasted in the job description."
    
#     try:
#         # Extract text from resume file
#         resume_txt = extract_resume_text(resume_file)
#         if not resume_txt:
#             return "⚠️ For some reason, we could not extract text from the resume file. Please try again."
        
#         prompt = cover_letter_prompt_creator(resume_txt, job_input)
#         return get_cover_response(prompt)
#     except Exception as e:
#         return f"🚩 Unexpected error in generating cover letter: {e}"

# def validate_job_posting(job_input_text, posting_date, company, job_title):
#     """Validate job posting legitimacy"""
#     # Fixed logic - check if fields are empty (not inverted)
#     if not company.strip():
#         return "⚠️ Please enter a company name to validate the job posting."
    
#     if not job_input_text.strip():
#         return "⚠️ Please paste the job description to validate."
    
#     if not posting_date.strip():
#         return "⚠️ Please provide a job posting date (YYYY-MM-DD format)."
    
#     try:
#         # Validate job posting
#         recent = is_posting_recent(posting_date)
#         template_flag = template_detector(job_input_text)
#         urgency_flag = detect_urgency_language(job_input_text)
#         social_links = mentioned_on_socials(company, job_title or "")
        
#         report = "### 🕐 Posting Date Check:\n"
#         report += "✅ Yup, the job looks recent (posted within 60 days).\nIn this market, jobs don't stay open for more than that." if recent else "⚠️ Warning: Job may be outdated (older than 60 days).\nCould be they're just harvesting candidates."
        
#         report += "\n### 🤖 Template Language Check:\n"
#         report += "⚠️ Generic/template language detected - proceed with caution.\nCould be just a cattle call for info to keep on file." if template_flag else "✅ Posting appears specific and legitimate - as if an actual person wrote it and they have an actual need.\n"
        
#         report += "\n### ⚡ Urgency Language Check:\n"
#         report += "⚠️ Urgency language detected - be cautious of scams.\nCheck the post for poor grammar, unrealistic salary / work expectations, and that 'too good to be true' feel." if urgency_flag else "✅ No suspicious urgency language found.\nSeems like a real job posting."
        
#         report += "\n### 🔍 Verify the Job / Company on Social Media:\n"
#         report += f"- [Search on X/Twitter]({social_links['x']})\n"
#         report += f"- [Search on LinkedIn]({social_links['linkedin']})\n"
        
#         return report
        
#     except Exception as e:
#         return f"🚩 Error validating job posting: {e}"

# # Admin for granting access
# def admin_grant_access(user_email_or_id):
#     """ Function to grant unlimited access """
#     user_id = get_user_id()
#     grant_unlimited_access(user_id)
#     return f"Granted unlimited access to user: {user_id}"

# # Sticky buy button + banner (add before "with gr.Blocks()")
# sticky_buy_button = """
# <div style="position:fixed; top:10px; right:20px; z-index:9999; text-align:center;">
#     <a href="https://buy.stripe.com/cNi9ASgWl6C614l3Ja1Jm00" target="_blank" 
#        style="background-color:#ff7f50; color:white; padding:12px 20px; 
#               text-decoration:none; border-radius:8px; font-size:1em; 
#               font-weight:bold; box-shadow:0px 2px 6px rgba(0,0,0,0.2);">
#         ♾️ Unlimited Resume Optimization – $5.99/mo
#     </a>
#     <div style="font-size:0.8em; color:#333; margin-top:4px;">
#         Trusted by 200+ job seekers
#     </div>
# </div>
# """
# # Custom CSS for colored tabs and better styling
# custom_css = """
# <style>
# /* Style the tab buttons */
# .gradio-container .tab-nav button {
#     background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
#     color: white !important;
#     font-weight: bold !important;
#     border: none !important;
#     border-radius: 8px !important;
#     margin: 2px !important;
#     padding: 12px 20px !important;
#     transition: all 0.3s ease !important;
# }

# .gradio-container .tab-nav button:hover {
#     transform: translateY(-2px) !important;
#     box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4) !important;
# }

# .gradio-container .tab-nav button.selected {
#     background: linear-gradient(135deg, #ff7f50 0%, #ff6b35 100%) !important;
#     box-shadow: 0 4px 16px rgba(255, 127, 80, 0.5) !important;
# }

# /* Style primary buttons */
# .gradio-container .btn-primary {
#     background: linear-gradient(135deg, #ff7f50 0%, #ff6b35 100%) !important;
#     border: none !important;
#     font-weight: bold !important;
#     border-radius: 8px !important;
#     padding: 12px 24px !important;
#     transition: all 0.3s ease !important;
# }

# .gradio-container .btn-primary:hover {
#     transform: translateY(-2px) !important;
#     box-shadow: 0 6px 20px rgba(255, 127, 80, 0.4) !important;
# }

# /* Style download buttons */
# .gradio-container button:contains("Download PDF") {
#     background: linear-gradient(135deg, #28a745 0%, #20c997 100%) !important;
#     color: white !important;
#     border: none !important;
#     font-weight: bold !important;
#     border-radius: 8px !important;
# }
# </style>
# """

# # Create Gradio interface
# with gr.Blocks(title="ResumeWhip - AI Resume Optimizer | ATS-Friendly Resume Builder", theme=gr.themes.Soft(), css=custom_css) as app:
    
#     gr.HTML("<head><link rel='icon' href='favicon.png' type='image/png'></head>")
    
#     # Header
#     gr.Markdown("""
#     <h1 style='text-align:center; color:#1e90ff;'>🏎️💨 Welcome To ResumeWhip!</h1>
#     <h2 style='text-align:center; color:#dd1eff;'>The AI-Powered Resume Optimizer Meant to Whip ATS Systems</h2>
#     <h2 style='text-align:center; color:#dd1eff;'>Get Your First 3 Resumes Free!</h2> 
#     <h3 style='text-align:center;'>Powerful. Simple. Just Validate → Upload → Optimize → Apply!</h3>          
#     """)

#     with gr.Row():
#         # Sidebar
#         with gr.Column(scale=1):
#             with gr.Accordion("🦮 How To Use", open=False):
#                 gr.Markdown("""
#                          1.) Crank Your Existing Resume Up To 11 - list every single skill and experience you have
#                              (this is how our AI writes your resume and scores your chances);  
#                          2.) Follow the Prompts To Load the Requested Info;  
#                          3.) Choose Your Tool (you don't have to use all 3);  
#                          4.) Proofread / Edit the Results Using the 'Copy/Pastes' below;  
#                          5.) Download Your File as PDF; and  
#                          6.) Apply!
#                             """)
                
#             with gr.Accordion("📚 Formatting Tips", open=False):
#                 gr.Code("""
# If you're not happy with the default resume 
# format, you can make adjustments using the 
# simple copy and pastes below:
                        
# Want To Change Fonts:
# # = Biggest  
# ## = Smaller  
# ### = Smallest
# <b>text</b> = Bold  
# <i>text</i> = Italic  
# <u>text</u> = Underline
# (⬆️ Can Be Combined As Needed)
                        
# Making A List?
# - = Bullet Point  
# 1. = Numbered List

# Want To Link A Website?
# [Your Website](https://www.yourwebsite.com)

# Too "clumpy?" Break things up into separate lines
# with two spaces where you want the line break
# (after a period, for example). 
                        
# Or, if you want to create a section break with
# a line, just enter three dashes (---) where you 
# want that break to happen (eg: between 'Summary' 
# and 'Experience').

# "But my resume cuts off where I don't want it to!"
# Simple - just force a new page by copy/pasting this entire 
# line (below), and put it where you want one page to end
# and the next to begin:
# <div style="page-break-after: always; break-after: page;"></div>
#                 """, language="markdown")
                
#             with gr.Accordion("❓ Frequently Asked Questions", open=False):
#                 gr.Markdown("""
#         ### Common Questions About Resume Optimization
        
#         **Q: What is an ATS?**
#         A: "Applicant Tracking System." It's an automated filter Recruiters use to sift through the deluge of resumes they receive for open job positions.
                            
#         **Q: How does your Resume Optimizer and Cover Letter Writer work?**  
#         A: Our AI pits your resume up against job descriptions and tailors its content, keywords, and formatting to match what ATS systems and recruiters look for.
        
#         **Q: What makes ResumeWhip any different than the other resume optimizers?**
#         A: Its code is written by job seekers with fellow jobseekers in mind. In double-blind studies, it consistently outperforms the competition (eg: LinkedIn's AI Resume Optimizer).
                                       
#         **Q: Do optimized resumes really get more interviews?**  
#         A1: Yes - ATS-optimized, job-specific resumes typically see 3-5x higher response rates than generic versions. AI ensures you never miss the keywords ATS systems use to qualify your resume.
        
#         **Q: What file formats work best with the resume optimizer?**  
#         A: We support PDF(.pdf), Word (.docx), Markdown (.md), and text (.txt) files.
        
#         **Q: How many resumes can I optimize for free?**  
#         A: You get 3 free resume optimizations to try our service, then unlimited access for $5.99/month.

#         **Q: Why is the format of the resume I download look so plain?**
#         A: That's by design - ATS systems don't like a lot of formatting. (Tables and multiple columns? Nightmares for them.)
#         """)
            
#             # Subscribe button
#             gr.HTML("""
#             <div style="text-align:center; margin:20px 0;">
#                 <a href="https://buy.stripe.com/cNi9ASgWl6C614l3Ja1Jm00" 
#                    target="_blank" 
#                    style="background-color:#635BFF; color:white; padding:15px 25px; 
#                           text-decoration:none; border-radius:8px; font-size:1.1em; 
#                           font-weight:bold; display:inline-block;">
#                     ♾️ Get Unlimited AI-Powered Resume Optimizaton for Just  $5.99/Month!
#                 </a>
#             </div>
#             """)
            
#             gr.Markdown("### 🛡️ We will never sell your data. Ever.")

#             gr.Markdown("### 🔥 Share the love - help friends skip the job search struggle!")

#             gr.HTML("""
#                 <div style="display:flex; flex-direction:column; gap:20px; margin-top:20px;">
                    
#                     <!-- Clean logo-based sharing -->
#                     <div style="display:flex; flex-direction:row; gap:20px; justify-content:center; align-items:center;">
                        
#                         <!-- LinkedIn -->
#                         <a href="https://www.linkedin.com/sharing/share-offsite/?url=https://resumewhip.com&summary=Finally%20found%20a%20resume%20tool%20that%20actually%20understands%20ATS%20systems%20🎯%20ResumeWhip%20uses%20AI%20to%20optimize%20resumes%20for%20each%20job%20posting.%20Getting%20way%20more%20interviews%20than%20generic%20resumes!" 
#                            target="_blank" 
#                            style="text-decoration: none; position: relative; display: inline-block;"
#                            onmouseover="showTooltip(this, 'Help your network with the AI resume optimizer that outperforms LinkedIn\'s own tools!')"
#                            onmouseout="hideTooltip(this)">
#                             <img src="https://upload.wikimedia.org/wikipedia/commons/8/81/LinkedIn_icon.svg" 
#                                  style="width:40px; height:40px; transition: transform 0.3s ease, filter 0.3s ease;"
#                                  onmouseover="this.style.transform='scale(1.2)'; this.style.filter='brightness(1.2)';"
#                                  onmouseout="this.style.transform='scale(1)'; this.style.filter='brightness(1)';">
#                         </a>
                        
#                         <!-- X/Twitter -->
#                         <a href="https://x.com/intent/post?url=https://resumewhip.com&text=Just%20boosted%20my%20resume%27s%20ATS%20score%20by%2040%25%20with%20AI!%20🎯%20Finally%20getting%20callbacks%20instead%20of%20radio%20silence.%20ResumeWhip%20tailors%20resumes%20to%20each%20job%20-%203%20free%20tries!" 
#                            target="_blank"
#                            style="text-decoration: none; position: relative; display: inline-block;"
#                            onmouseover="showTooltip(this, 'Tweet about AI resume success - your followers will thank you!')"
#                            onmouseout="hideTooltip(this)">
#                             <img src="https://upload.wikimedia.org/wikipedia/commons/c/ce/X_logo_2023.svg" 
#                                  style="width:40px; height:40px; transition: transform 0.3s ease, filter 0.3s ease;"
#                                  onmouseover="this.style.transform='scale(1.2)'; this.style.filter='brightness(1.2)';"
#                                  onmouseout="this.style.transform='scale(1)'; this.style.filter='brightness(1)';">
#                         </a>
                        
#                         <!-- Facebook -->
#                         <a href="https://www.facebook.com/sharer/sharer.php?u=https://resumewhip.com&quote=Stop%20sending%20resumes%20into%20the%20void!%20🎯%20This%20AI%20tool%20actually%20gets%20you%20past%20the%20bots%20and%20tailors%20resumes%20in%2030%20seconds.%20Game%20changer%20for%20job%20hunting!" 
#                            target="_blank" 
#                            style="text-decoration: none; position: relative; display: inline-block;"
#                            onmouseover="showTooltip(this, 'Share the secret to beating ATS systems with friends and family!')"
#                            onmouseout="hideTooltip(this)">
#                             <img src="https://upload.wikimedia.org/wikipedia/commons/0/05/Facebook_Logo_%282019%29.png" 
#                                  style="width:40px; height:40px; transition: transform 0.3s ease, filter 0.3s ease;"
#                                  onmouseover="this.style.transform='scale(1.2)'; this.style.filter='brightness(1.2)';"
#                                  onmouseout="this.style.transform='scale(1)'; this.style.filter='brightness(1)';">
#                         </a>
                        
#                         <!-- Reddit -->
#                         <a href="https://www.reddit.com/submit?url=https://resumewhip.com&title=Found%20an%20AI%20tool%20that%20actually%20gets%20resumes%20past%20ATS%20bots%20🤖➡️👤&text=Tired%20of%20sending%20resumes%20into%20the%20void?%20ResumeWhip%20uses%20AI%20to%20tailor%20resumes%20to%20job%20postings%20and%20beat%20ATS%20systems.%20Finally%20getting%20responses!" 
#                            target="_blank"
#                            style="text-decoration: none; position: relative; display: inline-block;"
#                            onmouseover="showTooltip(this, 'Help Your Reddit friends beat ATS systems and land their dream jobs!')"
#                            onmouseout="hideTooltip(this)">
#                             <img src="https://cdn.simpleicons.org/reddit/FF4500" 
#                                  style="width:40px; height:40px; transition: transform 0.3s ease, filter 0.3s ease;"
#                                  onmouseover="this.style.transform='scale(1.2)'; this.style.filter='brightness(1.2)';"
#                                  onmouseout="this.style.transform='scale(1)'; this.style.filter='brightness(1)';">
#                         </a>
                        
#                     </div>
                
#                 <!-- JavaScript for clean hover tooltips -->
#                 <script>
#                 function showTooltip(element, message) {
#                     // Remove any existing tooltip
#                     hideTooltip(element);
                    
#                     // Create tooltip
#                     const tooltip = document.createElement('div');
#                     tooltip.className = 'custom-tooltip';
#                     tooltip.innerHTML = message;
#                     tooltip.style.cssText = `
#                         position: absolute;
#                         bottom: 50px;
#                         left: 50%;
#                         transform: translateX(-50%);
#                         background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
#                         color: white;
#                         padding: 8px 12px;
#                         border-radius: 6px;
#                         font-size: 0.8em;
#                         font-weight: bold;
#                         white-space: nowrap;
#                         z-index: 1000;
#                         box-shadow: 0 4px 8px rgba(0,0,0,0.2);
#                         animation: fadeIn 0.3s ease;
#                     `;
                    
#                     element.appendChild(tooltip);
#                 }
                
#                 function hideTooltip(element) {
#                     const existing = element.querySelector('.custom-tooltip');
#                     if (existing) {
#                         existing.remove();
#                     }
#                 }
                
#                 // Add CSS for fade-in animation
#                 const style = document.createElement('style');
#                 style.textContent = `
#                     @keyframes fadeIn {
#                         from { opacity: 0; transform: translateX(-50%) translateY(5px); }
#                         to { opacity: 1; transform: translateX(-50%) translateY(0); }
#                     }
#                 `;
#                 document.head.appendChild(style);
#                 </script>
#                 """)

#         # Main content
#         with gr.Column(scale=5):
#             # Input section
#             with gr.Row():
#                 resume_input = gr.File(
#                     label="📄 Upload Resume Here", 
#                     file_types=[".pdf", ".docx", ".md", ".txt"]
#                 )
#                 company_input = gr.Textbox(
#                     label="🏢 Enter the Company's Name", 
#                     placeholder="e.g., Google, Microsoft"
#                 )
            
#             job_input = gr.Textbox(
#                 label="📝 Job Description (Please Paste Full Text)", 
#                 lines=6,
#                 placeholder="Paste the complete job posting here..."
#             )
            
#             # Credit counter
#             resume_counter = gr.Markdown("### Free Resumes Left: 3")

#             # Access granter
#             with gr.Accordion("My Admin Access", open=False, visible=False):
#                 grant_access_btn = gr.Button("🟢 Grant Unlimited Access", variant="secondary")
#                 access_status = gr.Markdown()

#             # Tools Available
#             gr.Markdown("<h2 style='text-align:center; color:#ff7f50;'>🧰 Tools In the Toolkit</h2>")

#             # Tools tabs
#             with gr.Tabs():
#                 with gr.TabItem("✅ Job Validator", id="validator_tab"):
#                     with gr.Row():
#                         jd_date = gr.Textbox(
#                             label="📅 Posting Date (Best Guess, Anyway.)", 
#                             placeholder="YYYY-MM-DD (e.g., 2024-12-01)"
#                         )
#                         jd_title = gr.Textbox(
#                             label="💼 Job Title", 
#                             placeholder="e.g., Data Scientist"
#                         )
                    
#                     validate_btn = gr.Button("🤖 Whip Up the Job Validator", variant="primary")
#                     validation_output = gr.Markdown()

#                 with gr.TabItem("🎯 Resume Optimizer", id="optimizer_tab"):
#                     run_resume = gr.Button("🪄 Whip Up Some Resume Magic!", variant="primary")
#                     resume_md = gr.Markdown(label="Preview")
#                     resume_edit = gr.Textbox(
#                         label="✏️ Edit Your Resume Here (optional)", 
#                         lines=15
#                     )
#                     suggestions = gr.Markdown(label="Suggestions & Tips")
                    
#                     with gr.Row():
#                         export_resume_btn = gr.Button("⬇️ Download PDF")
#                         export_resume_result = gr.File()

#                 with gr.TabItem("📝 Cover Letter Writer", id="cover_tab"):
#                     run_cover = gr.Button("📝 Whip Up My Cover Letter", variant="primary")
#                     cover_output = gr.Textbox(
#                         label="Here's Your Cover Letter. Edit To Give It Your Voice.", 
#                         lines=15
#                     )
                    
#                     with gr.Row():
#                         export_cover_btn = gr.Button("⬇️ Download PDF")
#                         export_cover_result = gr.File()

#     # Event handlers
#     validate_btn.click(
#         fn=validate_job_posting,
#         inputs=[job_input, jd_date, company_input, jd_title],
#         outputs=validation_output
#     )
    
#     run_resume.click(
#         fn=run_resume_with_credits,
#         inputs=[resume_input, job_input],
#         outputs=[resume_md, resume_edit, suggestions, resume_counter]
#     )
    
#     export_resume_btn.click(
#         fn=export_resume,
#         inputs=[resume_edit, company_input],
#         outputs=export_resume_result
#     )
    
#     run_cover.click(
#         fn=generate_cover_letter,
#         inputs=[resume_input, job_input],
#         outputs=cover_output
#     )
    
#     export_cover_btn.click(
#         fn=save_cover_letter,
#         inputs=[cover_output, company_input],
#         outputs=export_cover_result
#     )

#     # Admin event handler (for testing)

#     admin_input = gr.Textbox(label="User Email or ID")

#     grant_access_btn.click(
#         fn=admin_grant_access,
#         inputs=[admin_input],
#         outputs=access_status
#     )

# # Footer for SEO
# gr.HTML("""
#         <footer style = "margin-top: 50px; padding: 30px 20px; border-top: 2px solid #eee;
#                         background: linear-gradient(135deg, #f8f9a 0%, #e9ecef 100%);")
        
#             <!-- Main footer content -->
#             <div style="max-width: 1200px; margin: 0 auto; text-align: center;">
        
#                 <!-- Key links -->
#                 <div style="margin-bottom: 25px;">
#                     <a href="mailto:support@resumewhip.com"
#                         style="margin: 0 20px; color: #1e90ff; text-decoration: none; font-weight: 500;">
#                         📧 Contact Support
#                     </a>
#                     <a href="https://buy.stripe.com/cNi9ASgWl6C614l3Ja1Jm00"
#                         style="margin: 0 20px; color: #635BFF; text-decoration: none; font-weight: 500;">
#                         💳 Upgrade to Premium
#                     </a>
#                     <a href="https://resumewhip.com/blog"
#                         style="margin: 0 20px; color: #1e90ff; text-decoration: none; font-weight: 500;">
#                         📖 Resume Tips Blog
#                     </a>
#                 </div>
        
#                 <!-- Value proposition -->
#                 <div style="margin-bottom: 20px; color: #495057;">
#                     <h3 style="color: #343a40; margin-bottom: 10px;">
#                         🏎️💨 ResumeWhip - The AI Resume Optimizer That Actually Works
#                     </h3>
#                     <p style="font-size: 1.1em; line-height: 1.4; max-width: 600px; margin: 0 auto;">
#                         Help job seekers beat ATS systems, get more interviews and land dream jobs with
#                         the personalized AI resume optimizer that crushes the competition in head-to-head comparisons.
#                     </p>
#                 </div>
        
#                 <!-- Trust signals -->
#                 <div style="display: flex; justify-content: center; gap: 30px; margin-bottom: 25px;
#                             flex-wrap: wrap; color: #6c757d; font-size: 0.9em;">
#                                     <div>🛡️ Your data never stored or shared</div>
#                                     <div>⚡ 30-second resume optimization</div>
#                                     <div>🎯 40% higher ATS compatibility</div>
#                                     <div>💼 Works with all job boards</div>
#                 </div>

#                 <!-- Copyright and keywords -->
#                 <div style="border-top: 1px solid #dee2e6; padding-top: 20px;">
#                     <p style="color: #6c757d; font-size: 0.95em; margin-bottom: 10px;">
#                         © 2025 ResumeWhip - AI-Powered Resume Optimization Tool
#                     </p>
#                     <p style="color: #adb5bd; font-size: 0.8em; line-height: 1.3;">
#                         Keywords: AI resume optimizer, ATS resume checker, resume builder, cover letter generator, 
#                         job application tool, interview preparation, career advancement, resume writing service
#                     </p>
#                 </div>
            
#             </div>
#         </footer>
#         """)

# # Stripe webhook endpoint (if needed)
# def handle_stripe_webhook(request_data):
#     """Handle Stripe webhook for subscription confirmation and storage"""
#     try:
#         endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
#         event = stripe.Webhook.construct_event(
#             request_data['payload'],
#             request_data['signature'],
#             endpoint_secret
#         )
        
#         if event["type"] == "checkout.session.completed":
#             session = event["data"]["object"]
#             user_id = session.get("client_reference_id")
#             customer_id = session.get("customer")

#             # store Stripe customer / user id
#             if user_id and customer_id:
#                 store_stripe_customer_id(user_id, customer_id)
#                 grant_unlimited_access(user_id)
        
#         # handle subscription cancellation
#         elif event["type"] == "customer.subscription.deleted":
#             subscription = event["data"]["object"]
#             customer_id = subscription["customer"]

#             # revoke acess
#             user_id = get_user_id_by_customer_id(customer_id)
#             if user_id:
#                 revoke_unlimited_access(user_id)
                
#         return {"status": "success"}
#     except Exception as e:
#         return {"status": "error", "message": str(e)}

# def revoke_unlimited_access(user_id):
#     """
#     Revoke access when subscription is cancelled
#     """
#     paid_users.discard(user_id)
#     user_credits[user_id] = 0

# if __name__ == "__main__":
#     port = int(os.environ.get("PORT", 7860))
#     app.launch(
#         server_name="0.0.0.0",
#         server_port=port,
#         show_error=True,
#         share=False
#     )

# ================================ #
# ------ Final Code Above -------
# ================================ #

# # Round 5
# import gradio as gr
# import os
# import stripe
# import pdfplumber
# import uuid
# import json
# from datetime import datetime
# from new_functions import (
#     extract_resume_text,
#     sanitize_input,
#     prompt_creator,
#     get_resume_response,
#     process_resume,
#     export_resume,
#     cover_letter_prompt_creator,
#     get_cover_response,
#     save_cover_letter,
#     is_posting_recent,
#     template_detector,
#     mentioned_on_socials,
#     detect_urgency_language
# )

# # Stripe setup
# stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
# PRICE_ID = os.getenv("PRICE_ID")

# # Simple in-memory storage (consider Redis for production)
# user_credits = {}
# active_resumes = {}
# FREE_CREDITS = 3

# def get_user_id():
#     """Generate a session-based user ID"""
#     # For Gradio, we'll use a simple session state approach
#     if not hasattr(gr, '_current_user_id'):
#         gr._current_user_id = str(uuid.uuid4())
#     return gr._current_user_id

# def create_checkout_session():
#     try:
#         user_id = get_user_id()
#         session = stripe.checkout.Session.create(
#             client_reference_id=user_id,
#             payment_method_types=['card'],
#             line_items=[{
#                 'price': PRICE_ID,
#                 'quantity': 1,
#             }],
#             mode='subscription',
#             success_url="https://www.resumewhip.com/success",
#             cancel_url="https://resumewhip.com/cancel"
#         )
#         return session.url
#     except Exception as e:
#         return f"Error creating checkout session: {e}"

# def run_resume_with_credits(resume_file, job_input):
#     """Handle resume processing with credit system"""
#     if not resume_file or not job_input.strip():
#         return ("⚠️ Please upload your resume and paste the job description they've provided.", "", "", "Free resumes left: -")
    
#     user_id = get_user_id()
#     credits = user_credits.get(user_id, FREE_CREDITS)
    
#     # Generate unique resume ID
#     resume_name = getattr(resume_file, "name", "unknown")
#     new_resume_id = f"{resume_name}_{hash(job_input)}"
    
#     # Check if this is a new resume (consumes credit) or edit of existing one
#     if active_resumes.get(user_id) != new_resume_id:
#         if credits != float("inf"):
#             if credits <= 0:
#                 checkout_url = create_checkout_session()
#                 return (
#                     f"⏰ You've used your 3 free resumes! Ready for unlimited access? [Subscribe here]({checkout_url}) for just $5.99/month!",
#                     "", "", "Free resumes left: 0"
#                 )
#             credits -= 1
#             user_credits[user_id] = credits
#         active_resumes[user_id] = new_resume_id
    
#     # Process resume
#     try:
#         result = process_resume(resume_file, job_input)
#         credits_display = '∞' if credits == float('inf') else str(credits)
#         return (*result, f"Free resumes left: {credits_display}")
#     except Exception as e:
#         return (f"Error processing resume: {e}", "", "", f"Free resumes left: {credits}")

# def generate_cover_letter(resume_file, job_input):
#     """Generate cover letter from resume and job description"""
#     if not resume_file or not job_input.strip():
#         return "⚠️ Please check that you've uploaded a resume and pasted in the job description."
    
#     try:
#         # Extract text from resume file
#         resume_txt = extract_resume_text(resume_file)
#         if not resume_txt:
#             return "⚠️ For some reason, we could not extract text from the resume file. Please try again."
        
#         prompt = cover_letter_prompt_creator(resume_txt, job_input)
#         return get_cover_response(prompt)
#     except Exception as e:
#         return f"🚩 Unexpected error in generating cover letter: {e}"

# def validate_job_posting(job_input_text, posting_date, company, job_title):
#     """Validate job posting legitimacy"""
#     # Fixed logic - check if fields are empty (not inverted)
#     if not company.strip():
#         return "⚠️ Please enter a company name to validate the job posting."
    
#     if not job_input_text.strip():
#         return "⚠️ Please paste the job description to validate."
    
#     if not posting_date.strip():
#         return "⚠️ Please provide a job posting date (YYYY-MM-DD format)."
    
#     try:
#         # Validate job posting
#         recent = is_posting_recent(posting_date)
#         template_flag = template_detector(job_input_text)
#         urgency_flag = detect_urgency_language(job_input_text)
#         social_links = mentioned_on_socials(company, job_title or "")
        
#         report = "### 🕐 Posting Date Check:\n"
#         report += "✅ Yup, the job looks recent (posted within 60 days).\nIn this market, jobs don't stay open for more than that." if recent else "⚠️ Warning: Job may be outdated (older than 60 days).\nCould be they're just harvesting candidates."
        
#         report += "\n### 🤖 Template Language Check:\n"
#         report += "⚠️ Generic/template language detected - proceed with caution.\nCould be just a cattle call for info to keep on file." if template_flag else "✅ Posting appears specific and legitimate - as if an actual person wrote it and they have an actual need.\n"
        
#         report += "\n### ⚡ Urgency Language Check:\n"
#         report += "⚠️ Urgency language detected - be cautious of scams.\nCheck the post for poor grammar, unrealistic salary / work expectations, and that 'too good to be true' feel." if urgency_flag else "✅ No suspicious urgency language found.\nSeems like a real job posting."
        
#         report += "\n### 🔍 Verify the Job / Company on Social Media:\n"
#         report += f"- [Search on X/Twitter]({social_links['x']})\n"
#         report += f"- [Search on LinkedIn]({social_links['linkedin']})\n"
        
#         return report
        
#     except Exception as e:
#         return f"🚩 Error validating job posting: {e}"

# # Sticky buy button + banner (add before "with gr.Blocks()")
# sticky_buy_button = """
# <div style="position:fixed; top:10px; right:20px; z-index:9999; text-align:center;">
#     <a href="https://buy.stripe.com/cNi9ASgWl6C614l3cc" target="_blank" 
#        style="background-color:#ff7f50; color:white; padding:12px 20px; 
#               text-decoration:none; border-radius:8px; font-size:1em; 
#               font-weight:bold; box-shadow:0px 2px 6px rgba(0,0,0,0.2);">
#         ♾️ Unlimited Resume Optimization – $5.99/mo
#     </a>
#     <div style="font-size:0.8em; color:#333; margin-top:4px;">
#         Trusted by 200+ job seekers
#     </div>
# </div>
# """
# # Create Gradio interface
# with gr.Blocks(title="ResumeWhip - AI Resume Optimizer | ATS-Friendly Resume Builder", theme=gr.themes.Soft()) as app:
    
#     gr.HTML("<head><link rel='icon' href='favicon.png' type='image/png'></head>")
    
#     # Header
#     gr.Markdown("""
#     <h1 style='text-align:center; color:#1e90ff;'>🏎️💨 Welcome To ResumeWhip!</h1>
#     <h2 style='text-align:center; color:#dd1eff;'>The AI-Powered Resume Optimizer Meant to Whip ATS Systems</h2>
#     <h2 style='text-align:center; color:#dd1eff;'>Get Your First 3 Resumes Free!</h2> 
#     <h3 style='text-align:center;'>Powerful. Simple. Just Validate → Upload → Optimize → Apply!</h3>          
#     """)

#     with gr.Row():
#         # Sidebar
#         with gr.Column(scale=1):
#             with gr.Accordion("🦮 How To Use", open=False):
#                 gr.Markdown("""
#                          1.) Crank Your Existing Resume Up To 11 - list every single skill and experience you have
#                              (this is how our AI writes your resume and scores your chances);  
#                          2.) Follow the Prompts To Load the Requested Info;  
#                          3.) Choose Your Tool (you don't have to use all 3);  
#                          4.) Proofread / Edit the Results Using the 'Copy/Pastes' below;  
#                          5.) Download Your File as PDF; and  
#                          6.) Apply!
#                             """)
                
#             with gr.Accordion("📚 Formatting Tips", open=False):
#                 gr.Code("""
# If you're not happy with the default resume 
# format, you can make adjustments using the 
# simple copy and pastes below:
                        
# Want To Change Fonts:
# # = Biggest  
# ## = Smaller  
# ### = Smallest
# <b>text</b> = Bold  
# <i>text</i> = Italic  
# <u>text</u> = Underline
# (⬆️ Can Be Combined As Needed)
                        
# Making A List?
# - = Bullet Point  
# 1. = Numbered List

# Want To Link A Website?
# [Your Website](https://www.yourwebsite.com)

# Too "clumpy?" Break things up into separate lines
# with two spaces where you want the line break
# (after a period, for example). 
                        
# Or, if you want to create a section break with
# a line, just enter three dashes (---) where you 
# want that break to happen (eg: between 'Summary' 
# and 'Experience').

# "But the page cuts off where I don't want it to!"
# Simple - just force a new page by copy/pasting this entire 
# line (below), and put it where you want one page to end
# and the next to begin:
# <div style="page-break-after: always; break-after: page;"></div>
#                 """, language="markdown")
                
#             with gr.Accordion("❓ Frequently Asked Questions", open=False):
#                 gr.Markdown("""
#         ### Common Questions About Resume Optimization
        
#         **Q: How does AI resume optimization work?**  
#         A: Our AI pits your resume up against job descriptions and tailors its content, keywords, and formatting to match what ATS systems and recruiters look for.
        
#         **Q: Is this better than manual resume writing?**  
#         A1: AI optimization ensures you never miss important keywords and helps facilitate multiple job applications efficiently, removing as many headaches as possible.
        
#         **Q: What file formats work with the resume optimizer?**  
#         A: We support PDF, Word (.docx), Markdown (.md), and text (.txt) files for maximum compatibility.
        
#         **Q: How many resumes can I optimize for free?**  
#         A: You get 3 free resume optimizations to try our service, then unlimited access for $5.99/month.
        
#         **Q: Do optimized resumes really get more interviews?**  
#         A: Yes - ATS-optimized, job-specific resumes typically see 3-5x higher response rates than generic versions.

#         **Q: What if I don't like the format of the resume your Resume Optimizer tool generates?**
#         A1: No problem! We have included a menu with some tips to help you adjust the format to your liking!
#         Tip: Keep your resume clean and simple - ATS systems don't really like a lot of formatting. (Tables? Yikes.)
#         """)
            
#             # Subscribe button
#             gr.HTML("""
#             <div style="text-align:center; margin:20px 0;">
#                 <a href="https://buy.stripe.com/cNi9ASgWl6C614l3cc" 
#                    target="_blank" 
#                    style="background-color:#635BFF; color:white; padding:15px 25px; 
#                           text-decoration:none; border-radius:8px; font-size:1.1em; 
#                           font-weight:bold; display:inline-block;">
#                     ♾️ Get Unlimited AI-Powered Resume Optimizaton for Just  $5.99/Month!
#                 </a>
#             </div>
#             """)
            
#             gr.Markdown("### 🛡️ We will never sell your data. Ever.")

#             gr.Markdown("### 🔥 Share the love - help friends skip the job search struggle!")

#             gr.HTML("""
#                 <div style="display:flex; flex-direction:column; gap:20px; margin-top:20px;">
                    
#                     <!-- Clean logo-based sharing -->
#                     <div style="display:flex; flex-direction:row; gap:20px; justify-content:center; align-items:center;">
                        
#                         <!-- LinkedIn -->
#                         <a href="https://www.linkedin.com/sharing/share-offsite/?url=https://resumewhip.com&summary=Finally%20found%20a%20resume%20tool%20that%20actually%20understands%20ATS%20systems%20🎯%20ResumeWhip%20uses%20AI%20to%20optimize%20resumes%20for%20each%20job%20posting.%20Getting%20way%20more%20interviews%20than%20generic%20resumes!" 
#                            target="_blank" 
#                            style="text-decoration: none; position: relative; display: inline-block;"
#                            onmouseover="showTooltip(this, 'Help your network with the AI resume optimizer that outperforms LinkedIn\'s own tools!')"
#                            onmouseout="hideTooltip(this)">
#                             <img src="https://upload.wikimedia.org/wikipedia/commons/8/81/LinkedIn_icon.svg" 
#                                  style="width:40px; height:40px; transition: transform 0.3s ease, filter 0.3s ease;"
#                                  onmouseover="this.style.transform='scale(1.2)'; this.style.filter='brightness(1.2)';"
#                                  onmouseout="this.style.transform='scale(1)'; this.style.filter='brightness(1)';">
#                         </a>
                        
#                         <!-- X/Twitter -->
#                         <a href="https://x.com/intent/post?url=https://resumewhip.com&text=Just%20boosted%20my%20resume%27s%20ATS%20score%20by%2040%25%20with%20AI!%20🎯%20Finally%20getting%20callbacks%20instead%20of%20radio%20silence.%20ResumeWhip%20tailors%20resumes%20to%20each%20job%20-%203%20free%20tries!" 
#                            target="_blank"
#                            style="text-decoration: none; position: relative; display: inline-block;"
#                            onmouseover="showTooltip(this, 'Tweet about AI resume success - your followers will thank you!')"
#                            onmouseout="hideTooltip(this)">
#                             <img src="https://upload.wikimedia.org/wikipedia/commons/c/ce/X_logo_2023.svg" 
#                                  style="width:40px; height:40px; transition: transform 0.3s ease, filter 0.3s ease;"
#                                  onmouseover="this.style.transform='scale(1.2)'; this.style.filter='brightness(1.2)';"
#                                  onmouseout="this.style.transform='scale(1)'; this.style.filter='brightness(1)';">
#                         </a>
                        
#                         <!-- Facebook -->
#                         <a href="https://www.facebook.com/sharer/sharer.php?u=https://resumewhip.com&quote=Stop%20sending%20resumes%20into%20the%20void!%20🎯%20This%20AI%20tool%20actually%20gets%20you%20past%20the%20bots%20and%20tailors%20resumes%20in%2030%20seconds.%20Game%20changer%20for%20job%20hunting!" 
#                            target="_blank" 
#                            style="text-decoration: none; position: relative; display: inline-block;"
#                            onmouseover="showTooltip(this, 'Share the secret to beating ATS systems with friends and family!')"
#                            onmouseout="hideTooltip(this)">
#                             <img src="https://upload.wikimedia.org/wikipedia/commons/0/05/Facebook_Logo_%282019%29.png" 
#                                  style="width:40px; height:40px; transition: transform 0.3s ease, filter 0.3s ease;"
#                                  onmouseover="this.style.transform='scale(1.2)'; this.style.filter='brightness(1.2)';"
#                                  onmouseout="this.style.transform='scale(1)'; this.style.filter='brightness(1)';">
#                         </a>
                        
#                         <!-- Reddit -->
#                         <a href="https://www.reddit.com/submit?url=https://resumewhip.com&title=Found%20an%20AI%20tool%20that%20actually%20gets%20resumes%20past%20ATS%20bots%20🤖➡️👤&text=Tired%20of%20sending%20resumes%20into%20the%20void?%20ResumeWhip%20uses%20AI%20to%20tailor%20resumes%20to%20job%20postings%20and%20beat%20ATS%20systems.%20Finally%20getting%20responses!" 
#                            target="_blank"
#                            style="text-decoration: none; position: relative; display: inline-block;"
#                            onmouseover="showTooltip(this, 'Help Your Reddit friends beat ATS systems and land their dream jobs!')"
#                            onmouseout="hideTooltip(this)">
#                             <img src="https://cdn.simpleicons.org/reddit/FF4500" 
#                                  style="width:40px; height:40px; transition: transform 0.3s ease, filter 0.3s ease;"
#                                  onmouseover="this.style.transform='scale(1.2)'; this.style.filter='brightness(1.2)';"
#                                  onmouseout="this.style.transform='scale(1)'; this.style.filter='brightness(1)';">
#                         </a>
                        
#                     </div>
                
#                 <!-- JavaScript for clean hover tooltips -->
#                 <script>
#                 function showTooltip(element, message) {
#                     // Remove any existing tooltip
#                     hideTooltip(element);
                    
#                     // Create tooltip
#                     const tooltip = document.createElement('div');
#                     tooltip.className = 'custom-tooltip';
#                     tooltip.innerHTML = message;
#                     tooltip.style.cssText = `
#                         position: absolute;
#                         bottom: 50px;
#                         left: 50%;
#                         transform: translateX(-50%);
#                         background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
#                         color: white;
#                         padding: 8px 12px;
#                         border-radius: 6px;
#                         font-size: 0.8em;
#                         font-weight: bold;
#                         white-space: nowrap;
#                         z-index: 1000;
#                         box-shadow: 0 4px 8px rgba(0,0,0,0.2);
#                         animation: fadeIn 0.3s ease;
#                     `;
                    
#                     element.appendChild(tooltip);
#                 }
                
#                 function hideTooltip(element) {
#                     const existing = element.querySelector('.custom-tooltip');
#                     if (existing) {
#                         existing.remove();
#                     }
#                 }
                
#                 // Add CSS for fade-in animation
#                 const style = document.createElement('style');
#                 style.textContent = `
#                     @keyframes fadeIn {
#                         from { opacity: 0; transform: translateX(-50%) translateY(5px); }
#                         to { opacity: 1; transform: translateX(-50%) translateY(0); }
#                     }
#                 `;
#                 document.head.appendChild(style);
#                 </script>
#                 """)

#         # Main content
#         with gr.Column(scale=3):
#             # Input section
#             with gr.Row():
#                 resume_input = gr.File(
#                     label="📄 Upload Resume Here", 
#                     file_types=[".pdf", ".docx", ".md", ".txt"]
#                 )
#                 company_input = gr.Textbox(
#                     label="🏢 Enter the Company's Name", 
#                     placeholder="e.g., Google, Microsoft"
#                 )
            
#             job_input = gr.Textbox(
#                 label="📝 Job Description (Please Paste Full Text)", 
#                 lines=6,
#                 placeholder="Paste the complete job posting here..."
#             )
            
#             # Credit counter
#             resume_counter = gr.Markdown("### Free Resumes Left: 3")

#             # Tools Available
#             gr.Markdown("<h2 style='text-align:center; color:#ff7f50;'>🧰 Tools In the Toolkit</h2>")

#             # Tools tabs
#             with gr.Tabs():
#                 with gr.TabItem("✅ Job Validator"):
#                     with gr.Row():
#                         jd_date = gr.Textbox(
#                             label="📅 Posting Date (Best Guess, Anyway.)", 
#                             placeholder="YYYY-MM-DD (e.g., 2024-12-01)"
#                         )
#                         jd_title = gr.Textbox(
#                             label="💼 Job Title", 
#                             placeholder="e.g., Data Scientist"
#                         )
                    
#                     validate_btn = gr.Button("🔍 Validate This Job Posting", variant="secondary")
#                     validation_output = gr.Markdown()

#                 with gr.TabItem("🎯 Resume Optimizer"):
#                     run_resume = gr.Button("🪄 Whip Up Some Resume Magic!", variant="primary")
#                     resume_md = gr.Markdown(label="Preview")
#                     resume_edit = gr.Textbox(
#                         label="✏️ Edit Your Resume (optional)", 
#                         lines=15
#                     )
#                     suggestions = gr.Markdown(label="Suggestions & Tips")
                    
#                     with gr.Row():
#                         export_resume_btn = gr.Button("⬇️ Download PDF")
#                         export_resume_result = gr.File()

#                 with gr.TabItem("📝 Cover Letter"):
#                     run_cover = gr.Button("📝 Whip Up A Cover Letter", variant="secondary")
#                     cover_output = gr.Textbox(
#                         label="Your Cover Letter", 
#                         lines=15
#                     )
                    
#                     with gr.Row():
#                         export_cover_btn = gr.Button("⬇️ Download PDF")
#                         export_cover_result = gr.File()

#     # Event handlers
#     validate_btn.click(
#         fn=validate_job_posting,
#         inputs=[job_input, jd_date, company_input, jd_title],
#         outputs=validation_output
#     )
    
#     run_resume.click(
#         fn=run_resume_with_credits,
#         inputs=[resume_input, job_input],
#         outputs=[resume_md, resume_edit, suggestions, resume_counter]
#     )
    
#     export_resume_btn.click(
#         fn=export_resume,
#         inputs=[resume_edit, company_input],
#         outputs=export_resume_result
#     )
    
#     run_cover.click(
#         fn=generate_cover_letter,
#         inputs=[resume_input, job_input],
#         outputs=cover_output
#     )
    
#     export_cover_btn.click(
#         fn=save_cover_letter,
#         inputs=[cover_output, company_input],
#         outputs=export_cover_result
#     )

# # Footer for SEO
# gr.HTML("""
#         <footer style = "margin-top: 50px; padding: 30px 20px; border-top: 2px solid #eee;
#                         background: linear-gradient(135deg, #f8f9a 0%, #e9ecef 100%);")
        
#             <!-- Main footer content -->
#             <div style="max-width: 1200px; margin: 0 auto; text-align: center;">
        
#                 <!-- Key links -->
#                 <div style="margin-bottom: 25px;">
#                     <a href="mailto:support@resumewhip.com"
#                         style="margin: 0 20px; color: #1e90ff; text-decoration: none; font-weight: 500;">
#                         📧 Contact Support
#                     </a>
#                     <a href="https://buy.stripe.com/cNi9ASgWl6C614l3cc"
#                         style="margin: 0 20px; color: #635BFF; text-decoration: none; font-weight: 500;">
#                         💳 Upgrade to Premium
#                     </a>
#                     <a href="https://resumewhip.com/blog"
#                         style="margin: 0 20px; color: #1e90ff; text-decoration: none; font-weight: 500;">
#                         📖 Resume Tips Blog
#                     </a>
#                 </div>
        
#                 <!-- Value proposition -->
#                 <div style="margin-bottom: 20px; color: #495057;">
#                     <h3 style="color: #343a40; margin-bottom: 10px;">
#                         🏎️💨 ResumeWhip - The AI Resume Optimizer That Actually Works
#                     </h3>
#                     <p style="font-size: 1.1em; line-height: 1.4; max-width: 600px; margin: 0 auto;">
#                         Help job seekers beat ATS systems, get more interviews and land dream jobs with
#                         the personalized AI resume optimizer that crushes the competition in head-to-head comparisons.
#                     </p>
#                 </div>
        
#                 <!-- Trust signals -->
#                 <div style="display: flex; justify-content: center; gap: 30px; margin-bottom: 25px;
#                             flex-wrap: wrap; color: #6c757d; font-size: 0.9em;">
#                                     <div>🛡️ Your data never stored or shared</div>
#                                     <div>⚡ 30-second resume optimization</div>
#                                     <div>🎯 40% higher ATS compatibility</div>
#                                     <div>💼 Works with all job boards</div>
#                 </div>

#                 <!-- Copyright and keywords -->
#                 <div style="border-top: 1px solid #dee2e6; padding-top: 20px;">
#                     <p style="color: #6c757d; font-size: 0.95em; margin-bottom: 10px;">
#                         © 2025 ResumeWhip - AI-Powered Resume Optimization Tool
#                     </p>
#                     <p style="color: #adb5bd; font-size: 0.8em; line-height: 1.3;">
#                         Keywords: AI resume optimizer, ATS resume checker, resume builder, cover letter generator, 
#                         job application tool, interview preparation, career advancement, resume writing service
#                     </p>
#                 </div>
            
#             </div>
#         </footer>
#         """)

# # Stripe webhook endpoint (if needed)
# def handle_stripe_webhook(request_data):
#     """Handle Stripe webhook for subscription confirmation"""
#     try:
#         endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
#         event = stripe.Webhook.construct_event(
#             request_data['payload'],
#             request_data['signature'],
#             endpoint_secret
#         )
        
#         if event["type"] == "checkout.session.completed":
#             session = event["data"]["object"]
#             user_id = session.get("client_reference_id")
#             if user_id:
#                 user_credits[user_id] = float("inf")
                
#         return {"status": "success"}
#     except Exception as e:
#         return {"status": "error", "message": str(e)}

# if __name__ == "__main__":
#     port = int(os.environ.get("PORT", 7860))
#     app.launch(
#         server_name="0.0.0.0",
#         server_port=port,
#         show_error=True,
#         share=False
#     )

# # Round 4
# import gradio as gr
# import os
# import stripe
# import pdfplumber
# import uuid
# from flask import Flask, request, make_response
# from new_functions import (
#     extract_resume_text,
#     sanitize_input,
#     prompt_creator,
#     get_resume_response,
#     process_resume,
#     export_resume,
#     cover_letter_prompt_creator,
#     get_cover_response,
#     save_cover_letter,
#     is_posting_recent,
#     template_detector,
#     mentioned_on_socials,
#     detect_urgency_language
# ) 

# stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
# PRICE_ID = "price_1S4MQICB2P1PAV6iRNFAcF36"

# # set up Flask for cookies to track free use
# flask_app = Flask(__name__)

# # tracking credits / resumes
# user_credits = {}
# active_resumes = {}
# FREE_CREDITS = 3

# def get_user_id():
#     """
#     Gets user's id; if no login info provided, uses session-based ID.
#     If needed, replaces with real authentication later.
#     """
#     user_id = request.cookies.get("user_id")
#     if not user_id:
#         user_id = str(uuid.uuid4())
#     return user_id

# @flask_app.after_request
# def set_cookie(response):
#     if not request.cookies.get("user_id"):
#         response.set_cookie("user_id", str(uuid.uuid4()), max_age = 60*60*24*30)
#     return response

# # Flask to set the cookies once the page loads
# @flask_app.route("/")
# def home():
#     resp = make_response("Welcome to ResumeWhip!")
#     if not request.cookies.get("user_id"):
#         resp.set_cookie("user_id", str(uuid.uuid4()), max_age = 60*60*24*30)
#     return resp

# def run_resume_with_credits(resume_file, job_input):
#     user_id = get_user_id()
#     credits = user_credits.get(user_id, FREE_CREDITS)

#     # generate the resume's unique ID from uploaded file and job description
#     resume_name = getattr(resume_file, "name", "unknown")
#     new_resume_id = f"{resume_name}_{hash(job_input)}"

#     # run a check to see if it's a new resume (using a credit) or just an edit to the same one (not using any credits)
#     if active_resumes.get(user_id) != new_resume_id:
#         # check to see if it's an unlimited plan
#         if credits != float("inf"):
#             if credits <= 0:
#                 return ("⏰ Looks like your 3 free resumes have been completed, but we'd love to keep helping - our prompts are constantly being worked on to improve your likelihood of landing your dream job. Please consider subscribing - at only $5.99 / month, you get all the AI-powered resume optimization you want!", "", "", f"Free resumes left: 0")
#             credits -= 1
#             user_credits[user_id] = credits
#         active_resumes[user_id] = new_resume_id

#     # normal resume generation
#     result = process_resume(resume_file, job_input)
#     return (*result, f"Free resumes left: {'∞' if credits == float('inf') else credits}")

# def create_checkout_session():
#     try:
#         session = stripe.checkout.Session.create(
#             client_reference_id = get_user_id(),
#             payment_method_types = ['card'],
#             line_items = [{
#                 'price' : PRICE_ID,
#                 'quantity' : 1,
#             }],
#             mode = 'subscription', 
#             success_url = "https://www.resumewhip.com/success",
#             cancel_url = "https://www.resumewhip.com/cancel"
#         )

#         return session.url
#     except Exception as e:
#         return f"There was an error creating your checkout session: {e}"

# with gr.Blocks(title = "ResumeWhip") as app:
   
#     gr.HTML("<head><link rel='icon' href='favicon.png' type='image/png'></head>")
#     # --- Header ---
#     gr.Markdown("""
#     <h1 style='text-align:center; color:#1e90ff;'>🏎️💨 Welcome To ResumeWhip!!</h1>
#     <h2 style='text-align:center; color:#dd1eff;'>Your One-Stop AI-Powered Resume Optimizer Shop</h2> 
#     <h3 style='text-align:center;'>Powerful Simplicity: Just Verify → Upload → Optimize → Apply!</h3>          
#     """)

#     with gr.Row():
#         # --- Sidebar (simplified into Accordions) ---
#         with gr.Column(scale=1):
#             with gr.Accordion("🦮 How To Use This Website", open = False):
#                 gr.Markdown("""
#                         1.) Crank Your Existing Resume Up To 11 - list every single skill and experience you have
#                             (this is how our AI writes your resume and scores your chances);  
#                         2.) Follow the Prompts To Load the Requested Info;  
#                         3.) Choose Your Tool (you don't have to use all 3);  
#                         4.) Proofread / Edit the Results Using the 'Copy/Pastes' below;  
#                         5.) Download Your File as PDF; and  
#                         6.) Apply!
#                             """)
                
#             with gr.Accordion("📚 Copy/Pastes for Resume Formatting", open=False):
#                 gr.Code("""
# If you're not happy with the default resume 
# format, you can make adjustments using the 
# simple copy and pastes below:
                        
# Want To Change Fonts:
# # = Biggest  
# ## = Smaller  
# ### = Smallest
# <b>text</b> = Bold  
# <i>text</i> = Italic  
# <u>text</u> = Underline
# (⬆️ Can Be Combined)
                        
# How About A List?
# - = Bullet Point  
# 1. = Numbered List

# Link Your Website:
# [Your Website](https://www.yourwebsite.com)

# Too "clumpy?" Break things up into separate lines
# with two spaces where you want the line break
# (e.g. after a period). 
                        
# Or, if you want to break things up by drawing a
# a line, just enter three dashes (---) where you 
# want the section break (eg: between 'Summary' 
# and 'Experience).

# Page cuts off where you don't want it to?
# Force Create A New Page by copy/pasting this entire 
# line, andnput it wherever you want:
# <div style="page-break-after: always; break-after: page;"></div>                      
#                 """, language="markdown")
#     # Stripe Subscribe Button
#             gr.HTML("""
#         <div style="text-align:center; margin-top:20px;">
#             <a href="https://buy.stripe.com/cNi9ASgWl6C614l3Ja1Jm00" 
#                target="_blank" 
#                style="background-color:#635BFF; color:white; padding:15px 25px; 
#                       text-decoration:none; border-radius:8px; font-size:1.2em; 
#                       font-weight:bold; display:inline-block;">
#                 🚀 Subscribe and Get Unlimited Resume Optimizatons
#                     for Only $5.99/month!
#             </a>
#         </div>
#     """)
            
#             gr.Markdown("### 🛡️ We never store, share, or sell your data.")
            
#             gr.Markdown("### 🔐 All payments are handled through Stripe.")

#             gr.Markdown("[📬 Need Help / Have Suggestions? Send Us An Email!](mailto:support@resumewhip.com)")

#             gr.Markdown("### #️⃣ Know someone who could use this in their job search? Share away!")
#             gr.HTML("""
#                     <!-- Share Icons -->
#     <div style="display:flex; flex-direction:row; gap:15px; justify-content:center; margin-top:10px;">
#         <a href="https://www.facebook.com/sharer/sharer.php?u=https://resumewhip.com" target="_blank">
#             <img src="https://upload.wikimedia.org/wikipedia/commons/0/05/Facebook_Logo_%282019%29.png" style="width:32px; height:32px;">
#         </a>
#         <a href="https://x.com/intent/post?url=https://resumewhip.com&text=Check%20out%20this%20awesome%20Resume%20Optimizer!" target="_blank">
#             <img src="https://upload.wikimedia.org/wikipedia/commons/c/ce/X_logo_2023.svg" alt="X" style="width:36px; height:36px;">
#         </a>
#         <a href="https://www.linkedin.com/sharing/share-offsite/?url=https://resumewhip.com" target="_blank">
#             <img src="https://upload.wikimedia.org/wikipedia/commons/8/81/LinkedIn_icon.svg" style="width:32px; height:32px;">
#         </a>
#         <a href="https://www.reddit.com/submit?url=https://resumewhip.com&title=Check%20this%20out!" target="_blank">
#              <img src="https://cdn.simpleicons.org/reddit/FF4500" alt="Reddit" style="width:32px; height:32px;">
#         </a>
#     </div>
# """)
# #             gr.Markdown("### 💸 Donations appreciated... only if we've helped:")
# #             gr.HTML("""
# #                     <div style="text-align:left; display:flex; flex-direction:column; gap:10px; margin-top:15px;">
# #         <!-- Support Buttons -->
# #         <form action="https://www.paypal.com/donate" method="post" target="_blank">
# #             <input type="hidden" name="business" value="YOUR_PAYPAL_EMAIL_OR_ID" />
# #             <input type="hidden" name="currency_code" value="USD" />
# #             <input type="image" src="https://www.paypalobjects.com/en_US/i/btn/btn_donate_LG.gif" 
# #                border="0" name="submit" alt="Donate with PayPal" />
# #         </form>
# #         <a href="https://www.buymeacoffee.com/yourname" target="_blank">
# #         <img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" style="height:40px;width:180px;">
# #         </a>
# #     </div>
# # </div>
# # """)

#         # --- Main App ---      
#         # Add CSS styling for the counter
#         gr.HTML("""
#                 <style>
#                 #resume-counter {
#                 text-align: center;
#                 font-size: 1.2em;
#                 color: #1e90ff;
#                 margin-bottom: 10px;
#                 font-weight: bold;
#                 }
#                 </style>
#                 """)
        
#         with gr.Column(scale=5):
#             with gr.Row():
#                 resume_input = gr.File(label="📝 Upload Your Resume Here", file_types = [".pdf", ".md", ".docx", ".txt"])
#                 company_input = gr.Textbox(label="🏢 Type In the Company Name", placeholder="e.g., ING Partners")
#                 job_input = gr.Textbox(label="🔬 Paste Entire Job Description", lines=8)
                
#             with gr.Row():
#                 resume_counter = gr.Markdown("### Free Resumes Left: 3", elem_id = "counter")

#             gr.Markdown("<h2 style='text-align:center; color:#ff7f50;'>🧰 Tools In the Toolkit</h2>")

#             with gr.Tab("📋 Job Validator"):
#                 with gr.Row():
#                     # with gr.Column():
#                     #     resume_input = gr.File(label="Upload Your Resume")
#                     #     job_desc_input = gr.Textbox(label="Paste Job Description", lines=10)
#                         # resume_input = gr.File(label="Upload Your Resume")
#                         # job_desc_input = gr.Textbox(label="Paste Job Description", lines=10)
#                     # with gr.Column():
#                         jd_date = gr.Textbox(label="Posting Date (YYYY-MM-DD)")
#                         jd_title = gr.Textbox(label="Job Title")
#                         validate_btn = gr.Button("✅ Validate Job - A Quick Check To See If the Job Post Is Legitimate")
#                         validation_output = gr.Markdown(label="Job Validation Results")

#                 def full_job_validator(job_input_text, posting_date, company, job_title):
#                     # --- Warning for empty / missing company name ---
#                     if not company.strip() == "":
#                         return "⚠️ Please enter a company name so we can validate the job posting."
                    
#                     # --- Warning if job_input_text is missing ---
#                     if not job_input_text.strip() == "":
#                         return "⚠️ Sorry, but we need a job description to help validate the job!"
                    
#                     # --- Warning if posting_date is missing ---
#                     if not posting_date.strip() == "":
#                         return "⚠️ Can you please give us a job posting date (or your best guess)? That would help alot."
                    
#                     # --- Existing job validation logic ---
#                     recent = is_posting_recent(posting_date)
#                     template_flag = template_detector(job_input_text)
#                     urgency_flag = detect_urgency_language(job_input_text)
#                     social_links = mentioned_on_socials(company, job_title)

#                     report = "### 🕒 Posting Date Check:\n"
#                     report += "✅ Job appears to be recent enough.\nNot a lot of jobs are still looking after 45 days." if recent else "⚠️ Warning! Job may be outdated.\n"

#                     report += "\n### 🤖 Template Language:\n"
#                     report += "⚠️ Generic/template language detected - could be just harvesting data and / or candidates.\n" if template_flag else "✅ Posting looks specific enough to be an actual need.\n"

#                     report += "\n### ⚡ Urgency Language:\n"
#                     report += "⚠️ Urgency words detected.\nProceed with caution, especially if the post is older than 30 days." if urgency_flag else "✅ No urgency language detected.\n"

#                     report += "\n### 🔍 Social Media Mentions:\n"
#                     report += f"- [Search on X](<{social_links['x']}>)\n"
#                     report += f"- [Search on LinkedIn](<{social_links['linkedin']}>)\n"

#                     # # --- Optional: Resume processing ---
#                     # if resume_file is not None:
#                     #     resume_report = process_resume(resume_file, job_input)
#                     #     report += f"\n### 📄 Resume Fit Analysis:\n{resume_report}\n"

#                     return report

#                 validate_btn.click(
#                     full_job_validator, [job_input, jd_date, company_input, jd_title], validation_output
#                 )

#             # with gr.Tab("Job Validator"):
#             #     jd_date = gr.Textbox(label="Posting Date (YYYY-MM-DD)")
#             #     jd_title = gr.Textbox(label="Job Title")
#             #     jd_validate_btn = gr.Button("✅ Validate Job")
#             #     jd_validation_result = gr.Markdown()

#             #     def validate_job(posting_date, company, job_title, job_description):
#             #         recent = is_posting_recent(posting_date)
#             #         template_flag = template_detector(job_description)
#             #         urgency_flag = detect_urgency_language(job_description)
#             #         social_links = mentioned_on_socials(company, job_title)

#             #         report = f"### 🕒 Posting Date Check:\n"
#             #         report += "✅ Job appears to be recent.\n" if recent else "⚠️ Job may be outdated.\n"

#             #         report += f"\n### 🤖 Template Language:\n"
#             #         report += "⚠️ Generic/template language detected - could be just harvesting candidates.\n" if template_flag else "✅ Posting looks specific enough to be an actual need.\n"

#             #         report += f"\n### 🔍 Social Media Mentions:\n"
#             #         report += f"- [Search on X](<{social_links['x']}>)\n"
#             #         report += f"- [Search on LinkedIn](<{social_links['linkedin']}>)\n"

#             #         return report

#             #     jd_validate_btn.click(
#             #         fn=validate_job,
#             #         inputs=[jd_date, company_input, jd_title, job_input],
#             #         outputs=jd_validation_result
#             #     )
            
#             with gr.Tab("Resume Optimizer"):
#                 run_resume = gr.Button("🧙 Click Here To Whip Up Some Resume Magic!")
#                 resume_md = gr.Markdown()
#                 resume_edit = gr.Textbox(label="Above Is the Preview of Your Optimized Resume - If You Want, You Can Edit In This Box Below.", lines=10)
#                 suggestions = gr.Markdown(label="Suggestions")
#                 export_resume_btn = gr.Button("⬇ Download as PDF")
#                 export_resume_result = gr.File()

#             with gr.Tab("Cover Letter Generator"):
#                 run_cover = gr.Button("📝 Click Here To Whip Up A Cover Letter")
#                 cover_output = gr.Textbox(label="Cover Letter", lines=12)
#                 export_cover_btn = gr.Button("⬇ Download as PDF")
#                 export_cover_result = gr.File()
            
#             # buy_button = gr.Button("🛍️ Subscribe and Get All the Resumes You Want for Less Than $6/Month!")
#             # buy_link = gr.Markdown()

#             # buy_button.click(
#             #     fn = lambda: f"[Click here for Limitless AI-Powered Resume Optimization!]({create_checkout_session()})",
#             #     outputs = buy_link
#             # )

#             # with gr.Tab("Job Validator"):
#             #     jd_date = gr.Textbox(label="Posting Date (YYYY-MM-DD)")
#             #     jd_title = gr.Textbox(label="Job Title")
#             #     jd_validate_btn = gr.Button("✅ Validate Job")
#             #     jd_validation_result = gr.Markdown()

#             #     def validate_job(posting_date, company, job_title, job_description):
#             #         recent = is_posting_recent(posting_date)
#             #         template_flag = template_detector(job_description)
#             #         social_links = mentioned_on_socials(company, job_title)

#             #         report = f"### 🕒 Posting Date Check:\n"
#             #         report += "✅ Job appears to be recent.\n" if recent else "⚠️ Job may be outdated.\n"

#             #         report += f"\n### 🤖 Template Language:\n"
#             #         report += "⚠️ Generic/template language detected.\n" if template_flag else "✅ Looks specific.\n"

#             #         report += f"\n### 🔍 Social Media Mentions:\n"
#             #         report += f"- [Search on X](<{social_links['x']}>)\n"
#             #         report += f"- [Search on LinkedIn](<{social_links['linkedin']}>)\n"

#             #         return report

#             #     jd_validate_btn.click(
#             #         fn=validate_job,
#             #         inputs=[jd_date, company_input, jd_title, job_input],
#             #         outputs=jd_validation_result
#             #     )

#             # Resume events
#             run_resume.click(run_resume_with_credits, [resume_input, job_input], [resume_md, resume_edit, suggestions, resume_counter])
#             export_resume_btn.click(export_resume, [resume_edit, company_input], [export_resume_result])

#             # Cover letter events
#             def generate_cover_letter(resume_file, job_input):
#                 if resume_file is None or not job_input.strip():
#                     return "⚠️ Sorry, but the tools need both a resume and pasted job description before they can do you any good."

#                 # Normalize extension safely
#                 fname = getattr(resume_file, "name", "")
#                 ext = fname.lower().split(".")[-1] if "." in fname else ""

#             # Read resume text from PDF or text-like files
#                 resume_txt = ""
#                 try:
#                     if ext == "pdf":
#                         with pdfplumber.open(fname or resume_file) as pdf:
#                             for page in pdf.pages:
#                                 resume_txt += (page.extract_text() or "")
#                     else:
#                     # Fallback: treat as text/markdown
#                         with open(fname, "r", encoding="utf-8") as f:
#                             resume_txt = f.read()
#                 except Exception as e:
#                     return f"😐 Ruh-roh! Problem with the resume: {e}"

#                 prompt = cover_letter_prompt_creator(resume_txt, job_input)
#                 return get_cover_response(prompt)


#             run_cover.click(generate_cover_letter, [resume_input, job_input], [cover_output])
#             export_cover_btn.click(save_cover_letter, [cover_output, company_input], [export_cover_result])

#     # --- Footer ---
#     # gr.Markdown("""
#     # <hr>
#     # <p style='text-align:center; font-size:1.5em; color:gray;'>
#     # 🛡️ Your data is never stored, shared, or sold. Ever.
#     # </p>
#     # """)

# # Flask webhook setup so that once users pay, they have full access

# @flask_app.route("/webhook", methods = ["POST"])

# def stripe_webhook():
#     payload = request.data
#     signature_header = request.headers.get("Stripe-Signature")
#     endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

#     try:
#         event = stripe.Webhook.construct_event(payload, signature_header, endpoint_secret)
#     except Exception as e:
#         return str(e), 400
    
#     if event["type"] == "checkout.session.completed":
#         session = event["data"]["object"]
#         user_id = session.get("client_reference_id", "guest")

#         # give user infinite ("inf") access
#         user_credits[user_id] = float("inf")

#     return "", 200

# # Launch
# if __name__ == "__main__":
#     app.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", "8080")))
#     flask_app.run(host = "0.0.0.0", port = 8081)

# # Round 3
# import gradio as gr
# import io
# import pdfplumber
# import requests
# from new_functions import (
#     sanitize_input,
#     prompt_creator,
#     get_resume_response,
#     process_resume,
#     export_resume,
#     cover_letter_prompt_creator,
#     get_cover_response,
#     save_cover_letter,
#     is_posting_recent,
#     template_detector,
#     mentioned_on_socials,
#     source_link_meta_date,
#     detect_urgency_language,
#     detect_job_board_source,
#     career_page_search_url
# )
# from bs4 import BeautifulSoup 

# # ----- New and Improved app.py -----
# with gr.Blocks(css="""
# #     .section-header {
# #         text-align: center;
# #         color: #1e90ff;
# #         font-size: 2.5em;
# #         font-family: 'Segoe UI', sans-serif;
# #         font-weight: bold;
# #         margin-top: 20px;
# #         margin-bottom: 10px;
# #     }
# #     .subtext {
# #         text-align: center;
# #         font-size: 1.1em;
# #         color: #555;
# #         margin-bottom: 30px;
# #     }
# #     .gr-button {
# #         font-weight: bold;
# #         font-size: 1.1em;
# #         padding: 0.75em 1.5em;
# #         border-radius: 12px;
# #     }
# # """) as app:
#     with gr.Row():
#         # --- Sidebar ---
#         with gr.Column(scale=1):

#             # gr.Markdown("### 💖💸 We Accept Donations (but Only If We Helped)! 💸💖")

#             # # PayPal donate button
#             # gr.HTML(
#             #     """<form action="https://www.paypal.com/donate" method="post" target="_blank">
#             #        <input type="hidden" name="business" value="YOUR_PAYPAL_EMAIL_OR_ID" />
#             #        <input type="hidden" name="currency_code" value="USD" />
#             #        <input type="image" src="https://www.paypalobjects.com/en_US/i/btn/btn_donate_LG.gif" 
#             #               border="0" name="submit" title="PayPal - The safer, easier way to pay online!" 
#             #               alt="Donate with PayPal button" />
#             #        <img alt="" border="0" src="https://www.paypal.com/en_US/i/scr/pixel.gif" width="1" height="1" />
#             #        </form>"""
#             # )
#             #  # Buy Me a Coffee button
#             # gr.HTML(
#             #     """<a href="https://www.buymeacoffee.com/yourname" target="_blank">
#             #        <img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" 
#             #             alt="Send Us A Coffee" style="height:40px;width:180px;">
#             #        </a>"""
#             # )

#             gr.Markdown("### 📝 Markdown CheatSheet If You Don't Like Your Exported Resume Format")
#             gr.Code("""
                
# For Text Size:
# # = Biggest  
# ## = Little Smaller
# ### = Smaller Still

# For Text Formatting:
# <b>text</b> = Bolds Text
# <i>text</i> = Italicizes Text
# <u>text</u> = Underlines Text
# <b><u><i>text</i></u></b> =
# Bolds, Underlines, and Italicizes Text

# For Lists:
# - = Bullet Point
# 1. = Numbered List

# For Linking Your Website:
# [Website](actual_website_link)

# To Force A Page Break (Copy This Entire Line)
# <div style="page-break-after: always; break-after: page;"></div>
#                 """,
#                 language="markdown"
#             )

#             gr.Markdown("### 📬 Questions? / Comments? / Feedback?")
#             gr.HTML(
#                 """
#                   <p>📧 <a href="mailto:support@resumewhip.com">support@resumewhip.com</a></p>
#                 """
#             )
#             gr.Markdown("### 🛡️ Your Data Is Neither Stored, Shared, Nor Sold. Ever. At Any Time.")
#             gr.Markdown("### 💖💸 We Love Donations (and Coffee), but Only If We've Helped! 💸💖")
#             # PayPal donate button
#             gr.HTML(
#                 """<form action="https://www.paypal.com/donate" method="post" target="_blank">
#                    <input type="hidden" name="business" value="YOUR_PAYPAL_EMAIL_OR_ID" />
#                    <input type="hidden" name="currency_code" value="USD" />
#                    <input type="image" src="https://www.paypalobjects.com/en_US/i/btn/btn_donate_LG.gif" 
#                           border="0" name="submit" title="PayPal - The safer, easier way to pay online!" 
#                           alt="Donate with PayPal button" />
#                    <img alt="" border="0" src="https://www.paypal.com/en_US/i/scr/pixel.gif" width="1" height="1" />
#                    </form>"""
#             )
#              # Buy Me a Coffee button
#             gr.HTML(
#                 """<a href="https://www.buymeacoffee.com/yourname" target="_blank">
#                    <img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" 
#                         alt="Send Us A Coffee" style="height:40px;width:180px;">
#                    </a>"""
#             )
            
#             gr.Markdown("### 🌍 If You Like Us, Share Us!")
#             gr.HTML(
#                 """
#                 <div style="display:flex; flex-direction:row; gap:15px; justify-content:center;">
#                     <a href="https://www.facebook.com/sharer/sharer.php?u=https://resumewhip.com" target="_blank">
#                         <img src="https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/facebook.svg" alt="Facebook" style="width:32px; height:32px;">
#                     </a>
#                     <a href="https://twitter.com/intent/tweet?url=https://resumewhip.com&text=Check%20out%20this%20awesome%20Resume%20Optimizer!" target="_blank">
#                         <img src="https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/x.svg" alt="X" style="width:32px; height:32px;">
#                     </a>
#                     <a href="https://www.linkedin.com/sharing/share-offsite/?url=https://resumewhip.com" target="_blank">
#                         <img src="https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/linkedin.svg" alt="LinkedIn" style="width:32px; height:32px;">
#                     </a>
#                 </div>
#                 """
#             )

#         # --- Main App ---
#         with gr.Column(scale=5):
#             # Header
#             gr.Markdown("<h1 style  = 'text-align:center; color:#1e90ff;'>🥇 Welcome To resumewhip.com!!</h1>")
#             gr.Markdown("""
#                         <center>Your <b><i>free resume-optimizing app</i></b> focused on beating those 
#                         stupid ATS filters to land you actual interviews!
#                         """)    
#             gr.Markdown("""### 🦮 <u>Quick Guide: How This Works</u>:
#                         1.) Create A Main Resume - list every single skill and experience you have;  
#                         2.) Follow the Prompts To Load the Info the Tools Need;  
#                         3.) Choose the Tool You Want;  
#                         4.) Proofread / Edit the Results Using the Markdown Cheat Sheet;  
#                         5.) When You're Satisfied, Download What You Want;  
#                         6.) Apply; and  
#                         7.) Land That Dream Job! 
#                         """)

#             # Inputs
#             with gr.Row():
#                 resume_input = gr.File(label="📝 Put Your Main Resume Here")
#                 company_input = gr.Textbox(label="🏢 The Company with Whom You're Applying", placeholder="e.g., Data Clymer")
#                 job_input = gr.Textbox(label="🔬 Paste FULL Job Description Here", lines=10, interactive=True)
            
#             gr.Markdown("<h3 style = 'text-align:center; color:#1e90ff;'>🧰 Click Below To Choose Your Free Resume Boosting Tool!</h3>")

#             with gr.Tab("Resume Optimizer"):
#                 gr.Markdown("<div class='section-header'>🤓 Resume Optimizer</div>" )
#                 run_resume = gr.Button("✨ Click Here To Optimize Your Resume")
#                 resume_md = gr.Markdown(label="Optimized Resume (Markdown View)")
#                 resume_edit = gr.Textbox(label="Edit Your Resume In the Box Below", lines=10, interactive=True)
#                 suggestions = gr.Markdown(label="Suggestions for Improvement")
#                 export_resume_btn = gr.Button("⬇ Download Your Optimized Resume As PDF And Click To View (In Blue, To Right)")
#                 export_resume_result = gr.Markdown()

#             with gr.Tab("Cover Letter Generator"):
#                 run_cover = gr.Button("📝 Click Here To Generate Your Cover Letter")
#                 cover_output = gr.Textbox(label="Generated Cover Letter (Proofread and Edit To Your Tastes))", lines=15, interactive=True)
#                 export_cover_btn = gr.Button("⬇ Download And View Your Optimized Cover Letter As PDF (In Blue, To Right)")
#                 export_cover_result = gr.Markdown()

#             with gr.Tab("Job Validator"):
#                 gr.Markdown("Validate whether a job post is recent, specific, and visible on social platforms.")

#                 with gr.Row():
#                     jd_date = gr.Textbox(label="Job Posting Date (YYYY-MM-DD)", placeholder="e.g., 2025-06-01")

#                     jd_title = gr.Textbox(label="Job Title", placeholder="e.g., Senior Data Engineer")

#                 jd_validate_btn = gr.Button("✅ Run Job Validation")
#                 jd_validation_result = gr.Markdown()

#                 # Validation click logic
#                 def validate_job(posting_date, company, job_title, job_description):
#                     recent = is_posting_recent(posting_date)
#                     template_flag = template_detector(job_description)
#                     social_links = mentioned_on_socials(company, job_title)

#                     report = f"### 🕒 Posting Date Check:\n"
#                     report += "✅ Job appears to be recent.\n" if recent else "⚠️ Job may be outdated (posted over 60 days ago).\n"

#                     report += f"\n### 🤖 Template Language Detection:\n"
#                     report += "⚠️ This job description uses generic/template language.\n" if template_flag else "✅ Description looks specific.\n"

#                     report += f"\n### 🔍 Social Media Mentions:\n"
#                     report += f"- [Search on X](<{social_links['x']}>)\n"
#                     report += f"- [Search on LinkedIn](<{social_links['linkedin']}>)\n"

#                     return report

#                 jd_validate_btn.click(
#                     fn=validate_job,
#                     inputs=[jd_date, company_input, jd_title, job_input],
#                     outputs=jd_validation_result
#                 )

#             # Resume events
#             run_resume.click(fn=process_resume, inputs=[resume_input, job_input], outputs=[resume_md, resume_edit, suggestions])
#             export_resume_btn.click(fn=export_resume, inputs=[resume_edit, company_input], outputs=[export_resume_result])

#             # Cover letter events
#             def generate_cover_letter(resume_file, job_desc):
#                 with open(resume_file.name, "r", encoding="utf-8") as f:
#                     resume_txt = f.read()
#                 prompt = cover_letter_prompt_creator(resume_txt, job_desc)
#                 return get_cover_response(prompt)

#             def export_cover_handler(cover_text, company):
#                 pdf, md = save_cover_letter(cover_text, company)
#                 return f"✅ PDF saved at: `{pdf}`" if pdf else "❌ Failed to export."

#             run_cover.click(fn=generate_cover_letter, inputs=[resume_input, job_input], outputs=[cover_output])
#             export_cover_btn.click(fn=export_cover_handler, inputs=[cover_output, company_input], outputs=[export_cover_result])

#         # # --- Social Share Column (Right Side) ---
#         # with gr.Column(scale=1):
#         #     gr.Markdown("### 🛡️ Your Data Is Neither Stored, Shared, Nor Sold. Ever. At Any Time.")
#         #     gr.Markdown("### 💖💸 We Love Donations (and Coffee), but Only If We've Helped! 💸💖")
#         #     # PayPal donate button
#         #     gr.HTML(
#         #         """<form action="https://www.paypal.com/donate" method="post" target="_blank">
#         #            <input type="hidden" name="business" value="YOUR_PAYPAL_EMAIL_OR_ID" />
#         #            <input type="hidden" name="currency_code" value="USD" />
#         #            <input type="image" src="https://www.paypalobjects.com/en_US/i/btn/btn_donate_LG.gif" 
#         #                   border="0" name="submit" title="PayPal - The safer, easier way to pay online!" 
#         #                   alt="Donate with PayPal button" />
#         #            <img alt="" border="0" src="https://www.paypal.com/en_US/i/scr/pixel.gif" width="1" height="1" />
#         #            </form>"""
#         #     )
#         #      # Buy Me a Coffee button
#         #     gr.HTML(
#         #         """<a href="https://www.buymeacoffee.com/yourname" target="_blank">
#         #            <img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" 
#         #                 alt="Send Us A Coffee" style="height:40px;width:180px;">
#         #            </a>"""
#         #     )
            
#         #     gr.Markdown("### 🌍 If You Like Us, Share Us!")
#         #     gr.HTML(
#         #         """
#         #         <div style="display:flex; flex-direction:column; gap:10px; align-items:center;">
#         #             <a href="https://www.facebook.com/sharer/sharer.php?u=https://resumewhip.com" target="_blank">
#         #                 <img src="https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/facebook.svg" alt="Facebook" style="width:32px; height:32px;">
#         #             </a>
#         #             <a href="https://twitter.com/intent/tweet?url=https://resumewhip.com&text=Check%20out%20this%20awesome%20Resume%20Optimizer!" target="_blank">
#         #                 <img src="https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/x.svg" alt="X" style="width:32px; height:32px;">
#         #             </a>
#         #             <a href="https://www.linkedin.com/sharing/share-offsite/?url=https://resumewhip.com" target="_blank">
#         #                 <img src="https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/linkedin.svg" alt="LinkedIn" style="width:32px; height:32px;">
#         #             </a>
#         #         </div>
#         #         """
#         #     )

# # Launch
# app.launch(server_name="0.0.0.0", server_port=8080)


# # # import "gradio" for UI
# # import gradio as gr
# # import io
# # import pdfplumber

# # #import "requests" to simplify HTTP requests
# # import requests

# # # import functions, a file created in the job folder that houses the functions Gradio needs to do its job
# # from new_functions import (
# #     sanitize_input,
# #     prompt_creator,
# #     get_resume_response,
# #     process_resume,
# #     export_resume,
# #     cover_letter_prompt_creator,
# #     get_cover_response,
# #     save_cover_letter,
# #     is_posting_recent,
# #     template_detector,
# #     mentioned_on_socials,
# #     source_link_meta_date,
# #     detect_urgency_language,
# #     detect_job_board_source,
# #     career_page_search_url
# # )

# # # import BeautifulSoup to check for published jobdate is in posting's metadata - checking for link's age here.
# # from bs4 import BeautifulSoup 

# # # ----- New and Improved app.py -----
# # with gr.Blocks(css="""
# # #     .section-header {
# # #         text-align: center;
# # #         color: #1e90ff;
# # #         font-size: 2.5em;
# # #         font-family: 'Segoe UI', sans-serif;
# # #         font-weight: bold;
# # #         margin-top: 20px;
# # #         margin-bottom: 10px;
# # #     }
# # #     .subtext {
# # #         text-align: center;
# # #         font-size: 1.1em;
# # #         color: #555;
# # #         margin-bottom: 30px;
# # #     }
# # #     .gr-button {
# # #         font-weight: bold;
# # #         font-size: 1.1em;
# # #         padding: 0.75em 1.5em;
# # #         border-radius: 12px;
# # #     }
# # # """) as app:
# #     with gr.Row():
# #         # --- Sidebar ---
# #         with gr.Column(scale=1):
# #             gr.Markdown("### 💖💸 We Accept Donations (but Only If We Helped)! 💸💖")

# #             # PayPal donate button
# #             gr.HTML(
# #                 """<form action="https://www.paypal.com/donate" method="post" target="_blank">
# #                    <input type="hidden" name="business" value="YOUR_PAYPAL_EMAIL_OR_ID" />
# #                    <input type="hidden" name="currency_code" value="USD" />
# #                    <input type="image" src="https://www.paypalobjects.com/en_US/i/btn/btn_donate_LG.gif" 
# #                           border="0" name="submit" title="PayPal - The safer, easier way to pay online!" 
# #                           alt="Donate with PayPal button" />
# #                    <img alt="" border="0" src="https://www.paypal.com/en_US/i/scr/pixel.gif" width="1" height="1" />
# #                    </form>"""
# #             )
# #              # Buy Me a Coffee button
# #             gr.HTML(
# #                 """<a href="https://www.buymeacoffee.com/yourname" target="_blank">
# #                    <img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" 
# #                         alt="Send Us A Coffee" style="height:40px;width:180px;">
# #                    </a>"""
# #             )

# #             gr.Markdown("### 📝 Quick Markdown You Can Copy / Paste Into the Markdown Resume Section for Adjusting Your Exported Resume Format")
# #             gr.Code(
# #                 """
# # For Text Size:
# # # = Biggest  
# # ## = Little Smaller
# # ### = Smaller Still

# # For Text Formatting:
# # <b>text</b> = Bolds Text
# # <i>text</i> = Italicizes Text
# # <u>text</u> = Underlines Text

# # For Lists:
# # - = Bullet Point
# # 1. = Numbered List

# # For Linking Your Website:
# # [Website](actual_website_link)

# # To Force A Page Break (Copy This Entire Line)
# # <div style="page-break-after: always; break-after: page;"></div>
# #                 """,
# #                 language="markdown"
# #             )

# #             gr.Markdown("### 📬 Contact Us")
# #             gr.HTML(
# #                 """<p>Have feedback or suggestions? Reach out anytime:</p>
# #                    <p>📧 <a href="mailto:support@resumewhip.com">support@resumewhip.com</a></p>
# #                 """
# #             )

# #         # --- Main App ---
# #         with gr.Column(scale=3):
# #             # Header
# #             gr.Markdown("## Your One-Stop Resume and Cover Letter Optimizer")
# #             gr.Markdown("""
# #             1. Drop your Markdown resume below.  
# #             2. Enter the company name.  
# #             3. Paste the job description.  
# #             4. Generate both your tailored resume **and** a compelling cover letter in Markdown & PDF format.
# #             """)

# #             # Inputs
# #             with gr.Row():
# #                 resume_input = gr.File(label="Drop Your Markdown Resume Here")
# #                 company_input = gr.Textbox(label="The Company with Whom You're Applying", placeholder="e.g., Data Clymer")
# #                 job_input = gr.Textbox(label="Paste In the Job Description Here", lines=10, interactive=True)

# #             with gr.Tab("Resume Optimizer"):
# #                 run_resume = gr.Button("✨ Optimize Resume")
# #                 resume_md = gr.Markdown(label="Optimized Resume (Markdown View)")
# #                 resume_edit = gr.Textbox(label="Edit Your Resume Below", lines=10, interactive=True)
# #                 suggestions = gr.Markdown(label="Suggestions")
# #                 export_resume_btn = gr.Button("⬇ Download Your Optimized Resume As PDF (In Blue, To Right)")
# #                 export_resume_result = gr.Markdown()

# #             with gr.Tab("Cover Letter Generator"):
# #                 run_cover = gr.Button("📝 Generate Cover Letter")
# #                 cover_output = gr.Textbox(label="Generated Cover Letter (Markdown)", lines=15, interactive=True)
# #                 export_cover_btn = gr.Button("⬇ Download Your Optimized Cover Letter As PDF (In Blue, To Right)")
# #                 export_cover_result = gr.Markdown()

# #             with gr.Tab("Job Validator"):
# #                 gr.Markdown("Validate whether a job post is recent, specific, and visible on social platforms.")

# #                 with gr.Row():
# #                     jd_date = gr.Textbox(label="Job Posting Date (YYYY-MM-DD)", placeholder="e.g., 2025-06-01")
# #                     jd_company = gr.Textbox(label="Company Name", placeholder="e.g., IEM, LLC")

# #                 jd_title = gr.Textbox(label="Job Title", placeholder="e.g., Senior Data Engineer")
# #                 jd_desc = gr.Textbox(label="Paste Full Job Description", lines=10)

# #                 jd_validate_btn = gr.Button("✅ Run Job Validation")
# #                 jd_validation_result = gr.Markdown()

# #                 # Validation click logic
# #                 def validate_job(posting_date, company, job_title, job_description):
# #                     recent = is_posting_recent(posting_date)
# #                     template_flag = template_detector(job_description)
# #                     social_links = mentioned_on_socials(company, job_title)

# #                     report = f"### 🕒 Posting Date Check:\n"
# #                     report += "✅ Job appears to be recent.\n" if recent else "⚠️ Job may be outdated (posted over 60 days ago).\n"

# #                     report += f"\n### 🤖 Template Language Detection:\n"
# #                     report += "⚠️ This job description uses generic/template language.\n" if template_flag else "✅ Description looks specific.\n"

# #                     report += f"\n### 🔍 Social Media Mentions:\n"
# #                     report += f"- [Search on X](<{social_links['x']}>)\n"
# #                     report += f"- [Search on LinkedIn](<{social_links['linkedin']}>)\n"

# #                     return report

# #                 jd_validate_btn.click(
# #                     fn=validate_job,
# #                     inputs=[jd_date, jd_company, jd_title, jd_desc],
# #                     outputs=jd_validation_result
# #                 )

# #             # Resume events
# #             run_resume.click(fn=process_resume, inputs=[resume_input, job_input], outputs=[resume_md, resume_edit, suggestions])
# #             export_resume_btn.click(fn=export_resume, inputs=[resume_edit, company_input], outputs=[export_resume_result])

# #             # Cover letter events
# #             def generate_cover_letter(resume_file, job_desc):
# #                 with open(resume_file.name, "r", encoding="utf-8") as f:
# #                     resume_txt = f.read()
# #                 prompt = cover_letter_prompt_creator(resume_txt, job_desc)
# #                 return get_cover_response(prompt)

# #             def export_cover_handler(cover_text, company):
# #                 pdf, md = save_cover_letter(cover_text, company)
# #                 return f"✅ PDF saved at: `{pdf}`" if pdf else "❌ Failed to export."

# #             run_cover.click(fn=generate_cover_letter, inputs=[resume_input, job_input], outputs=[cover_output])
# #             export_cover_btn.click(fn=export_cover_handler, inputs=[cover_output, company_input], outputs=[export_cover_result])

# # # Launch
# # app.launch(server_name="0.0.0.0", server_port=8080)


# # ----- Old app.py ----
# # with gr.Blocks(css="""
# #     .section-header {
# #         text-align: center;
# #         color: #1e90ff;
# #         font-size: 2.5em;
# #         font-family: 'Segoe UI', sans-serif;
# #         font-weight: bold;
# #         margin-top: 20px;
# #         margin-bottom: 10px;
# #     }
# #     .subtext {
# #         text-align: center;
# #         font-size: 1.1em;
# #         color: #555;
# #         margin-bottom: 30px;
# #     }
# #     .gr-button {
# #         font-weight: bold;
# #         font-size: 1.1em;
# #         padding: 0.75em 1.5em;
# #         border-radius: 12px;
# #     }
# # """) as app:

# #     # Header
# #     gr.Markdown("<div class='section-header'>🥇 Welcome To atsbeater.com - Where We Help Your Resume Crush the ATS Overlords!</div>")
# #     gr.Markdown("""
# #         <div class='subtext'>
# #             Simply click or drag / drop your main resume, enter company name, paste in the provided job description, and BOOM: a keyword-optimized resume and cover letter is ready for your review and export.  
# #             Or, afraid that might be a ghost job there just to collect your data? Check out the Job Validator tab - we'll help you see if the job posting is real or sus.
# #         </div>
# #     """)

# #     # Inputs

# #     with gr.Row():
# #         resume_input = gr.File(label="📄 Upload Your Main Resume Here (In Either .pdf or .md Format)", file_types = [".pdf", ".md"])
# #         company_input = gr.Textbox(label="🏢 Company To Whom You're Sending This Thing", placeholder="e.g., Target, Amazon, etc.")
# #         job_input = gr.Textbox(label="📝 Job Description", lines=8, placeholder="Paste full job description here")

# #     gr.Markdown("<div class='section-header'>🧰 Tools!</div>")

# #     with gr.Tab("✨ Resume Optimizer"):
# #         gr.Markdown("<div class='section-header'>🤓 Resume Optimizer</div>")
# #         run_resume = gr.Button("✨ Click To Preview Optimized Resume (Editing Box Below Preview)")
# #         resume_md = gr.Markdown(label="Optimized Resume (Markdown)")
# #         resume_edit = gr.Textbox(label="✏️ Edit Your Resume Below", lines=10, interactive=True)
# #         suggestions = gr.Markdown(label="🔍 Suggestions")
# #         export_resume_btn = gr.Button("⬇ Download Your Optimized Resume As PDF (In Blue, To Right)")
# #         # for personal testing
# #         # export_resume_result = gr.Markdown()
# #         export_resume_result = gr.File(label = "📄 Download Your Optimized Resume PDF")

# #     with gr.Tab("📬 Cover Letter Generator"):
# #         gr.Markdown("<div class='section-header'>👋 Cover Letter Generator</div>")
# #         run_cover = gr.Button("📝 Click Here To Preview Your Cover Letter - And Edit In the Space Provided")
# #         cover_output = gr.Textbox(label="Generated Cover Letter - Please Proofread, and Check for <<cough cough>> Accuracy. 'I cured Polio!' No, you didn't.", lines=15, interactive=True)
# #         export_cover_btn = gr.Button("⬇ Download Your Optimized Cover Letter As PDF (In Blue, To Right)")
# #         # to export cover letter to user
# #         export_cover_result = gr.File(label = "📄 Download Your Cover Letter PDF")
# #         # for personal testing
# #         # export_cover_result = gr.Markdown()
        
# #     with gr.Tab("🔍 Job Validator"):
# #         gr.Markdown("<div class='section-header'>🕵️‍♂️ Job Validation Tool</div>")
# #         gr.Markdown("<div class='subtext'>Is this a real job, or just an attempt to mine your data? Check how recent, relevant, and visible a job post is on socials.</div>")

# #         with gr.Row():
# #             job_url = gr.Textbox(label="🔗 Optional: Job Posting URL", placeholder="https://jobs.greenhouse.io/...")
# #             jd_date = gr.Textbox(label="📅 Job Posting Date (Format: YYYY-MM-DD)", placeholder="e.g., 2025-06-01, or your best guess.")
# #             job_title = gr.Textbox(label="🔖 Job Title", placeholder="e.g., Technical Support Analyst")

# #         jd_validate_btn = gr.Button("✅ Run Job Validation")
# #         jd_validation_result = gr.Markdown()

# #         def source_link_meta_date(url):
# #             try:
# #                 resp = requests.get(url, timeout=5)
# #                 soup = BeautifulSoup(resp.text, "html.parser")

# #                 # Look for known meta tags
# #                 for tag in ["datePublished", "article:published_time", "og:published_time"]:
# #                     meta = soup.find("meta", {"property": tag}) or soup.find("meta", {"name": tag})
# #                     if meta and meta.get("content"):
# #                         return meta["content"]
# #             except Exception as e:
# #                 return None
# #             return None

# #         def validate_job(posting_date, company, job_title, job_description, job_url):
# #             # handle user error / lack of info
# #             if not company or not job_description:
# #                 return "Please enter at least the company name and job description."
                
# #             # Existing checks
# #             recent = is_posting_recent(posting_date)
# #             template_flag = template_detector(job_description)
# #             urgency_flag = detect_urgency_language(job_description)

# #             # New ones
# #             meta_date = source_link_meta_date(job_url)
# #             board_check = detect_job_board_source(job_url)
# #             career_search = career_page_search_url(company, job_title)

# #             report = f"### 🕒 Posting Date:\n"
# #             report += "✅ User-entered date is recent enough so that candidates are still being considered.\n" if recent else "⚠️ Possibly outdated - plenty of time to have filled this position.\n"
# #             report += f"📅 Meta date from page: `{meta_date}`\n" if meta_date else "Sadly, though, we couldn't find any exact publishing metadata from the page.\n"

# #             report += f"\n### 🤖 Template Detection:\n"
# #             report += "⚠️ Generic language detected - looks like a template was used.\n" if template_flag else "✅ Description looks specific enough to look like it was written by an actual person.\n"

# #             report += f"\n### 🚨 Urgency Signal:\n"
# #             report += "✅ Urgency signals found in description - genuine need for this position is expressed.\n" if urgency_flag else "⚠️ No urgency keywords found, so they're either taking their time or just harvesting candidates.\n"

# #             report += f"\n### 🌐 Job Source:\n{board_check}\n"

# #             report += f"\n### 🧭 Career Site Check:\nTry searching: [Google Career Match]({career_search})"

# #             return report
    
# #     jd_validate_btn.click(
# #         fn=validate_job,
# #         inputs=[jd_date, company_input, job_title, job_input, job_url],
# #         outputs=jd_validation_result
# #     )

# #     # Resume events
# #     run_resume.click(fn=process_resume, inputs=[resume_input, job_input], outputs=[resume_md, resume_edit, suggestions])
# #     export_resume_btn.click(fn=export_resume, inputs=[resume_edit, company_input], outputs=[export_resume_result])

# #     # Cover letter events
# #     def generate_cover_letter(resume_file, job_desc):
# #         # exception handling
# #         if resume_file is None or job_desc.strip() == "":
# #             return "⚠️ Sorry, but we need a resume and job description before we can generate a cover letter worth anything."
# #         try: 
# #             # look for the file extension
# #             if resume_file.name.lower().endswith(".pdf"):
# #                 resume_txt = " "
# #                 with pdfplumber.open(resume_file) as pdf:
# #                     for page in pdf.pages:
# #                         text = page.extract_text()
# #                         if text:
# #                             resume_txt += text + "/n"
# #             elif resume_file.name.lower().endswith(".md"):
# #                 with open(resume_file.name, "r", encoding = "utf-8") as f: 
# #                     resume_txt = f.read()
                    
# #             # if resume_file.name.lower().endswith(".pdf"):
# #             #     resume_txt = " "
# #             #     with pdfplumber.open(resume_file.name) as pdf:
# #             #         for page in pdf.pages:
# #             #             text = page.extract_text()
# #             #             if text:
# #             #                 resume_txt += text + "/n"
# #             # elif resume_file.name.lower().endswith(".md"):
# #             #     resume_txt = resume_file.read().decode("utf-8")

# #             else:
# #                 return "💀 Unsupported file type. Please upload a resume with either a '.pdf' or '.md' extension."

# #             # print chunk of resume for user to see resume was loaded
# #             print("✅ Resume text that was loaded (first 300 chars): \n", resume_txt[:300])
            
# #             prompt = cover_letter_prompt_creator(resume_txt, job_desc)
            
# #             return get_cover_response(prompt)

# #         except Exception as e:
# #             return f"😐 Ruh-roh. There was an error reading your resume: {e}"

# #     def export_cover_handler(cover_text, company):
# #         pdf, md = save_cover_letter(cover_text, company)
# #         # for webapp
# #         return pdf
# #         # for personal
# #         # return f"✅ PDF saved at: `{pdf}`" if pdf else "❌ Failed to export."

# #     run_cover.click(fn=generate_cover_letter, inputs=[resume_input, job_input], outputs=[cover_output])
# #     export_cover_btn.click(fn=export_cover_handler, inputs=[cover_output, company_input], outputs=[export_cover_result])

# # # Launch
# # app.launch(server_name="0.0.0.0", server_port=8080, share = True)