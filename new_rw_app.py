# === Hybrid ResumeWhip - New Frontend + Gradio Backup ===
import os
import sqlite3
import gradio as gr
import stripe
import uuid
import json
import threading
import uvicorn
from dotenv import load_dotenv
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, Header, File, UploadFile, Form
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Import your existing functions
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
    detect_urgency_language,
    calculate_resume_score
)

# Load environment
load_dotenv()

# Database setup
DATABASE_PATH = os.getenv("DATABASE_PATH", "resumewhip.db")
ADMIN_INCOGNITO = os.getenv("ADMIN_INCOGNITO", "change_this_secret_key")

# Stripe setup
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
PRICE_ID = os.getenv("PRICE_ID")

# Initialize FastAPI
fastapi_app = FastAPI(title="ResumeWhip API")

# Add CORS middleware
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
os.makedirs("static", exist_ok=True)
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
fastapi_app.mount("/static", StaticFiles(directory="static"), name="static")

# Database helper
def get_db_connection():
    """Get database connection"""
    render_path = "/var/data/resumewhip.db"
    local_path = "resumewhip.db"
    db_path = render_path if os.path.exists("/var/data") else local_path
    
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

# User management functions (reuse from your existing code)
def get_or_create_user(email: str):
    """Get or create user by email"""
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
    finally:
        conn.close()

def update_user_credits(user_id, credits):
    """Update user credits"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET credits_remaining = ? WHERE user_id = ?", 
            (credits, user_id)
        )
        conn.commit()
    finally:
        conn.close()

# ==========================================
# NEW FRONTEND API ROUTES
# ==========================================

@fastapi_app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the new professional frontend"""
    try:
        with open("static/index.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Frontend not found. Please add index.html to static/</h1>", status_code=404)

@fastapi_app.post("/api/user/login")
async def user_login(request: Request):
    """Handle user email login"""
    data = await request.json()
    email = data.get("email")
    
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    
    user_id, credits, status = get_or_create_user(email)
    is_premium = status in ["paid", "premium"]
    
    return JSONResponse({
        "user_id": user_id,
        "credits": credits if not is_premium else "unlimited",
        "is_premium": is_premium,
        "status": status
    })

@fastapi_app.post("/api/validate-job")
async def validate_job_api(request: Request):
    """Validate job posting"""
    data = await request.json()
    
    job_description = data.get("job_description", "")
    company_name = data.get("company_name", "")
    job_title = data.get("job_title", "")
    
    # Simple scoring logic (use your existing function)
    score = 100
    warnings = []

    if "wire money" in job_description.lower() or "gift cards" in job_description.lower():
        score -= 50
        warnings.append("🚩 Mentions money transfer or gift cards.")
    if "no experience required" in job_description.lower():
        score -= 15
        warnings.append("⚠️ Very low barrier to entry.")
    if detect_urgency_language(job_description):
        score -= 10
        warnings.append("⚠️ Excessive urgency language.")
    if template_detector(job_description):
        score -= 10
        warnings.append("⚠️ Contains many generic phrases.")

    score = max(score, 0)
    
    summary = "✅ Job looks legitimate!" if score >= 80 else \
              "⚠️ Proceed with caution." if score >= 50 else \
              "❌ High risk posting."
    
    return JSONResponse({
        "score": score,
        "summary": summary,
        "report": "\n".join(warnings) if warnings else "No red flags detected."
    })

@fastapi_app.post("/api/optimize-resume")
async def optimize_resume_api(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    company_name: str = Form(...),
    email: str = Form(...)
):
    """Optimize resume"""
    # Get user
    user_id, credits, status = get_or_create_user(email)
    is_premium = status in ["paid", "premium"]
    
    # Check credits
    if not is_premium and credits <= 0:
        return JSONResponse({
            "error": "No credits remaining",
            "upgrade_url": f"/api/create-checkout?email={email}"
        }, status_code=402)
    
    # Save uploaded file temporarily
    temp_path = f"temp_{uuid.uuid4()}.{resume.filename.split('.')[-1]}"
    with open(temp_path, "wb") as f:
        f.write(await resume.read())
    
    try:
        # Extract resume text
        resume_text = extract_resume_text(temp_path)
        
        # Calculate original score
        original_score, original_feedback = calculate_resume_score(resume_text, job_description)
        
        # Optimize
        optimized_preview, suggestions, match_info, optimized_text = process_resume(
            temp_path, job_description
        )
        
        # Calculate optimized score
        optimized_score, optimized_feedback = calculate_resume_score(optimized_text, job_description)
        
        # Deduct credits if not premium
        if not is_premium:
            update_user_credits(user_id, credits - 1)
        
        return JSONResponse({
            "original_score": original_score,
            "optimized_score": optimized_score,
            "optimized_resume": optimized_text,
            "resume_preview": optimized_preview,
            "suggestions": suggestions,
            "credits_remaining": credits - 1 if not is_premium else "unlimited"
        })
    
    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)

@fastapi_app.post("/api/download-resume")
async def download_resume_api(request: Request):
    """Generate and download resume PDF"""
    data = await request.json()
    resume_content = data.get("resume_content")
    company_name = data.get("company_name", "company")
    
    # Use your existing export function
    pdf_path = export_resume(resume_content, company_name)
    
    if pdf_path and os.path.exists(pdf_path):
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"optimized_resume_{company_name}.pdf"
        )
    else:
        raise HTTPException(status_code=500, detail="Failed to generate PDF")

@fastapi_app.post("/api/generate-cover-letter")
async def generate_cover_letter_api(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    company_name: str = Form(...),
    email: str = Form(...)
):
    """Generate cover letter"""
    # Save uploaded file temporarily
    temp_path = f"temp_{uuid.uuid4()}.{resume.filename.split('.')[-1]}"
    with open(temp_path, "wb") as f:
        f.write(await resume.read())
    
    try:
        # Extract resume text
        resume_text = extract_resume_text(temp_path)
        
        # Generate cover letter
        prompt = cover_letter_prompt_creator(resume_text, job_description)
        cover_letter = get_cover_response(prompt)
        
        return JSONResponse({
            "cover_letter": cover_letter
        })
    
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@fastapi_app.post("/api/download-cover-letter")
async def download_cover_letter_api(request: Request):
    """Generate and download cover letter PDF"""
    data = await request.json()
    cover_letter = data.get("cover_letter")
    company_name = data.get("company_name", "company")
    
    # Use your existing save function
    pdf_path = save_cover_letter(cover_letter, company_name)
    
    if pdf_path and os.path.exists(pdf_path):
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"cover_letter_{company_name}.pdf"
        )
    else:
        raise HTTPException(status_code=500, detail="Failed to generate PDF")

@fastapi_app.get("/api/create-checkout")
async def create_checkout_api(email: str):
    """Create Stripe checkout session"""
    user_id, _, _ = get_or_create_user(email)
    
    try:
        session = stripe.checkout.Session.create(
            client_reference_id=user_id,
            customer_email=email,
            payment_method_types=['card'],
            line_items=[{
                'price': PRICE_ID,
                'quantity': 1,
            }],
            mode='subscription',
            success_url="https://www.resumewhip.com?payment=success",
            cancel_url="https://www.resumewhip.com?canceled=true"
        )
        
        return JSONResponse({"url": session.url})
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# STRIPE WEBHOOK (Keep your existing one)
# ==========================================

@fastapi_app.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
        
        # Handle events (use your existing logic)
        if event["type"] == "checkout.session.completed":
            # Grant premium access
            pass
        
        return JSONResponse(content={"status": "success"}, status_code=200)
    
    except Exception as e:
        print(f"Webhook error: {e}")
        return JSONResponse(content={"status": "error"}, status_code=400)

# ==========================================
# GRADIO BACKUP INTERFACE
# ==========================================

# Import your existing Gradio app
# (Keep ALL your existing Gradio code here - just wrap it in a variable)
# For brevity, I'm not repeating it all, but you'll paste your entire Gradio block here

# Example placeholder:
def create_gradio_app():
    """Create your existing Gradio interface"""
    # ... paste your entire gr.Blocks() code here ...
    # This is your backup interface
    pass

# gradio_app = create_gradio_app()

# ==========================================
# MAIN ENTRY POINT
# ==========================================

if __name__ == "__main__":
    # Mount Gradio at /gradio
    # app_with_gradio = gr.mount_gradio_app(fastapi_app, gradio_app, path="/gradio")
    
    # For now, just run FastAPI (add Gradio mounting after testing)
    uvicorn.run(
        fastapi_app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000))
    )