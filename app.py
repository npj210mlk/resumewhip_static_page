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

def get_sidebar_content():
    """Return sidebar content based on user subscription status"""
    user_id = get_user_id()
    is_premium = is_premium_user(user_id)
    
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
                ♾️ Get Unlimited Access - $5.99/Month!
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
        return (
            "⚠️ Please upload your resume and paste the job description they've provided.", "", 
            "", "Free resumes left: -")
    
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
