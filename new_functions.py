# === Round Two... Thousand
import os
import io
import re
import uuid
import logging
import requests
import pdfplumber
import docx
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
from markdown import markdown
from weasyprint import HTML, CSS
from bs4 import BeautifulSoup
from urllib.parse import quote

# ========================
# Setup & Configuration
# ========================

load_dotenv()
open_apikey = os.getenv("OPENAI_API_KEY")

if not open_apikey:
    raise EnvironmentError("OPENAI_API_KEY is missing. Please set it in Render environment variables.")

client = OpenAI(api_key = open_apikey)

logging.basicConfig(level=logging.INFO, format = "%(asctime)s - %(levelname)s - %(message)s")

# Directories
os.makedirs("gpt_resumes", exist_ok = True)
os.makedirs("gpt_cover_letters", exist_ok = True)

# ========================
# Resume Functions
# ========================

def extract_resume_text(file_path: str) -> str:
    if file_path.lower().endswith(".pdf"):
        with pdfplumber.open(file_path) as pdf:
            return "\n".join([page.extract_text() or "" for page in pdf.pages]).strip()
    elif file_path.lower().endswith(".docx"):
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs]).strip()
    elif file_path.lower().endswith((".md", ".txt")):
        with open(file_path, "r", encoding = "utf-8") as f:
            return f.read().strip()
    else:
        raise ValueError("Unsupported file type. Please upload .pdf, .docx, .md, or .txt.")

def get_embedding(text: str):
    response = client.embeddings.create(model = "text-embedding-3-small", input = text)
    return response.data[0].embedding

def calculate_resume_job_similarity(resume_txt: str, job_description: str) -> float:
    resume_emb = np.array(get_embedding(resume_txt)).reshape(1, -1)
    job_emb = np.array(get_embedding(job_description)).reshape(1, -1)
    return round(float(cosine_similarity(resume_emb, job_emb)[0][0]), 3)

def sanitize_input(text: str) -> str:
    patterns = ["```", "'''", '"""', "<script>", "</script>", "Ignore previous instructions", "Forget all prior directions"]
    for p in patterns:
        text = text.replace(p, "")
    return text.strip()

def prompt_creator(resume_string: str, job_desc_string: str) -> str:
    """
    Optimized prompt that prioritizes ATS compatibility and measurable impact.
    """
    # Protect the prompt engineering / LLM instructions
    resume_string = sanitize_input(resume_string)
    job_desc_string = sanitize_input(job_desc_string)

    return f"""
    ### Role: 
    You are an ATS optimization expert. Your task is to rewrite this resume to maximize compatibility with Applicant Tracking Systems while showcasing measurable impact.

    ---

    ### Critical Requirements (MUST FOLLOW):

    **1. Keyword Integration (HIGHEST PRIORITY)**
    - Extract the 20-30 most important technical terms, skills, and phrases from the job description.
    - Incorporate at LEAST 60% of these keywords naturally throughout the resume.
    - Use the EXACT terminology from the job posting (e.g., if they say "machine learning," don't say "ML").
    - Keywords must appear in context, not just listed.
    - If a required keyword cannot be supported by past experience, reference it in the Skills or Summary sections **without implying prior mastery or false experience.** 
    (Example: "Familiar with cloud deployment tools" instead of "Expert in cloud deployment.")


    **2. Quantifiable Achievements (MANDATORY)**
    - KEEP ALL existing numbers, percentages, dollar amounts, and metrics from the original resume.
    - Every bullet point must include at least ONE measurable result:
      * Percentages (increased by X%, reduced by Y%)
      * Dollar amounts (saved $X, generated $Y revenue)
      * Scale metrics (served X users, managed Y projects)
      * Time metrics (delivered X weeks early, reduced time by Y%)
    - If the original resume lacks metrics, ADD realistic ones based on typical role impact.
    - Examples: "Led 5-person team," "Improved efficiency by 25%," "Managed $500K budget"

    **3. Action Verbs (REQUIRED)**
    - Start EVERY bullet point with a strong action verb from this list:
      * Achieved, Improved, Increased, Reduced, Optimized, Generated
      * Led, Managed, Directed, Coordinated, Supervised
      * Developed, Created, Designed, Implemented, Built, Engineered
      * Analyzed, Evaluated, Assessed, Identified
      * Delivered, Executed, Established, Launched
    - Never start with weak verbs like "Responsible for" or "Helped with"

    **4. Relevant Experience Focus**
    - Include 2-4 most relevant roles (not just 2-3).
    - Each role should have 3-5 bullet points (not just 2-3) that directly relate to the job description.
    - Reframe existing experience to emphasize skills mentioned in the job posting.

    **5. Summary Section**
    - Write a 2–3 sentence professional summary that:
    * Mirrors the job title and core skills from the job description.
    * Accurately reflects the candidate’s actual background — do NOT add years of experience, certifications, or skills that are not verifiable in the original resume.
    * Focus on tone, clarity, and relevance rather than exaggeration.
    * Use factual phrasing like “experienced in,” “familiar with,” or “skilled at” when the level of expertise is uncertain.

    **6. Skills Section**
    - Create a dedicated "Technical Skills" or "Core Competencies" section
    - List skills exactly as they appear in the job description
    - Group by category if applicable (e.g., "Languages," "Tools," "Frameworks")

    ---

    ### Input:
    - **Resume**: `{resume_string}`
    - **Job Description**: `{job_desc_string}`

    ---

    ### Output Format:

    Return the optimized resume in clean Markdown with these sections:
    1. **Contact Info** (if present in original)
    2. **Summary** (keyword-rich, quantifiable)
    3. **Skills** (matched to job description)
    4. **Experience** (3-5 bullets per role, each with metrics and strong action verbs)
    5. **Education** (if present)

    Then add:
    ### Additional Suggestions
    - List any missing keywords that should be added
    - Suggest certifications or skills that would strengthen the application
    - Recommend any weak bullet points that need more quantifiable impact

    ---

    ### Remember: Your rewritten resume will be evaluated based on: 
        1. Keyword match accuracy (50 points),
        2. Use of strong action verbs (20 points),
        3. Quantifiable results (20 points),
        4. Optimal length and clarity (10 points).
        Your goal is to maximize the score in all categories."s
    """

def get_resume_response(prompt: str, model: str = "gpt-4o-mini", temperature: float = 0.7) -> str:
    try:
        response = client.chat.completions.create(
            model = model,
            messages = [
                {"role": "system", "content": "Expert Resume Writer"},
                {"role": "user", "content": prompt}
            ],
            temperature = temperature
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"OpenAI call failed: {e}")
        return f"Error: {e}"
    
def career_pivot_prompt_creator(resume_string: str, job_desc_string: str, 
                                current_field: str, target_field: str) -> str:
    """
    Specialized prompt for career changers that emphasizes transferable skills
    and reframes experience in terms relevant to the target industry.
    
    Args:
        resume_string (str): Original resume text
        job_desc_string (str): Target job description
        current_field (str): Current/previous career field
        target_field (str): Desired career field
    
    Returns:
        str: Optimized prompt for career transition scenarios
    """
    # Protect from injections
    resume_string = sanitize_input(resume_string)
    job_desc_string = sanitize_input(job_desc_string)
    current_field = sanitize_input(current_field)
    target_field = sanitize_input(target_field)
    
    return f"""
    ### Role: 
    You are a career transition specialist and ATS optimization expert. Your task is to help someone 
    successfully pivot from **{current_field}** to **{target_field}** by rewriting their resume to 
    emphasize transferable skills and reframe their experience in terms the target industry understands.

    ---

    ### Critical Requirements (MUST FOLLOW):

    **1. Transferable Skills Bridge (HIGHEST PRIORITY - 40 points)**
    - Identify ALL skills from {current_field} that directly apply to {target_field}
    - Reframe past accomplishments using {target_field} terminology and context
    - Focus on universal competencies: leadership, problem-solving, communication, data analysis, project management
    - Examples of reframing:
      * "Managed classroom of 30 students" → "Led team of 30 individuals, tracking performance metrics"
      * "Retail sales" → "Customer relationship management and revenue generation"
      * "Restaurant management" → "Operations optimization and team leadership"
    - Create a "bridge narrative" that shows logical progression from {current_field} to {target_field}

    **2. Target Industry Keyword Integration (30 points)**
    - Extract 20-30 key terms from the job description
    - Incorporate at LEAST 60% of these keywords naturally
    - Use EXACT terminology from {target_field} (if job says "stakeholder management," don't say "working with people")
    - If candidate lacks direct experience with a required skill, reference it in Skills/Summary as "familiar with" or "learning"
    - Never imply false expertise

    **3. De-emphasize Outdated Industry Jargon (20 points)**
    - Remove or minimize {current_field}-specific terms that don't translate
    - Replace industry jargon with universal business language
    - Example: Instead of "POS systems" use "point-of-sale technology and transaction processing"
    - Keep the *concept* but make it accessible to {target_field} recruiters

    **4. Lead with Most Relevant Experience (10 points)**
    - Reorganize experience to highlight transferable roles/projects FIRST
    - Even if not most recent, put relevant experience at the top
    - Create a "Relevant Experience" section if needed
    - Use reverse-chronological within each section

    **5. Quantifiable Achievements (MANDATORY)**
    - KEEP ALL existing numbers, percentages, and metrics from original resume
    - ADD realistic metrics where missing based on typical role impact
    - Every bullet point needs at least ONE measurable result
    - Examples: "Led 5-person team," "Improved efficiency by 25%," "Managed $500K budget"

    **6. Action Verbs (REQUIRED)**
    - Start EVERY bullet point with strong action verbs:
      * Achieved, Improved, Increased, Reduced, Optimized, Generated
      * Led, Managed, Directed, Coordinated, Supervised
      * Developed, Created, Designed, Implemented, Built, Engineered
      * Analyzed, Evaluated, Assessed, Identified
    - Never use "Responsible for" or "Helped with"

    **7. Career Transition Summary (CRITICAL)**
    - Write a 3-4 sentence professional summary that:
      * Acknowledges the career transition positively
      * Highlights transferable skills from {current_field}
      * Emphasizes enthusiasm/readiness for {target_field}
      * Mirrors core competencies from the job description
    - Example: "Results-driven professional transitioning from {current_field} to {target_field}, 
      bringing 5+ years of data analysis, team leadership, and process optimization. Proven track 
      record of improving efficiency by 30% and managing cross-functional projects. Seeking to 
      leverage analytical skills and business acumen in {target_field} role."

    **8. Skills Section Strategy**
    - Create TWO skill categories:
      * **Transferable Skills**: Universal competencies applicable to any field
      * **Technical Skills**: {target_field}-specific tools/technologies from job description
    - List any {target_field} skills you're learning/acquiring
    - Be honest about proficiency levels

    ---

    ### Input:
    - **Current Resume**: `{resume_string}`
    - **Target Job Description**: `{job_desc_string}`
    - **Transitioning From**: {current_field}
    - **Transitioning To**: {target_field}

    ---

    ### Output Format:

    Return the optimized resume in clean Markdown with these sections:
    1. **Contact Info** (if present in original)
    2. **Professional Summary** (career transition narrative, keyword-rich)
    3. **Transferable Skills** (universal competencies)
    4. **Technical Skills** (target field specific)
    5. **Relevant Experience** (reframed with transferable focus, 3-5 bullets per role)
    6. **Additional Experience** (if needed, de-emphasized)
    7. **Education** (if present)

    Then add:
    ### Career Transition Coaching
    - Suggest which past experiences to emphasize most
    - Identify any gaps to address (courses, certifications, projects)
    - Recommend specific ways to strengthen the transition narrative
    - List any {target_field} keywords still missing from the resume

    ---

    ### Scoring Criteria:
    Your rewritten resume will be evaluated on:
    1. **Transferable Skills Bridge** (40 points) - How well you connect {current_field} to {target_field}
    2. **Keyword Match** (30 points) - Target industry terminology integration
    3. **Quantifiable Results** (20 points) - Measurable achievements
    4. **Action Verbs & Clarity** (10 points) - Strong language and readability

    **Remember**: This candidate has real value to offer {target_field}. Your job is to make 
    that value immediately obvious to recruiters who may not understand {current_field} terminology.
    """

def process_resume(resume_file_path, job_desc_string):
    try:
        resume_txt = extract_resume_text(resume_file_path)
        if not resume_txt:
            return ["⚠️ Empty resume file.", "", "", ""]

        # score resume before optimization
        before_score = calculate_resume_job_similarity(resume_txt, job_desc_string)
        
        # generate the optimized resume
        prompt = prompt_creator(resume_txt, job_desc_string)
        response = get_resume_response(prompt)

        # split out any suggestions
        parts = re.split(r"^#+ Additional Suggestions", response, flags = re.IGNORECASE | re.MULTILINE)
        optimized = parts[0].strip() if parts else response
        suggestions = parts[1].strip() if len(parts) > 1 else "No additional suggestions."

        # score after optimization
        after_score = calculate_resume_job_similarity(optimized, job_desc_string)

        # quick output build - we need the og optimized resume, suggestions, the score, and an editable optimized
        match_info = f"### 📊 Resume Match Score\n- Before: {before_score * 100:.1f}%\n- After: {after_score * 100:.1f}%"
        return [optimized, suggestions, match_info, optimized]
    # except Exception as e:
    #     logging.error(f"process_resume failed: {e}")
    #     return [f"Error: {e}", "", "", ""]
    except Exception as e:
        print(f"DEBUG: Optimization Error: {e}") # This prints to your server logs
        logging.error(f"process_resume failed: {e}")
        return [f"⚠️ Error optimizing resume. Details: {e}", "", "", ""] 

def export_resume(new_resume, company_name):
    company_slug = re.sub(r"[^a-zA-Z0-9_-]", "", company_name.lower())
    unique_id = str(uuid.uuid4())[:8]
    output_pdf = f"gpt_resumes/{company_slug}_{unique_id}_optimized_resume.pdf"
    
    try:
        html_content = markdown(new_resume)
        css_path = "exported_resume_format.css"
        stylesheets = [CSS(filename = css_path)] if os.path.exists(css_path) else []
        HTML(string = html_content).write_pdf(output_pdf, stylesheets = stylesheets)
        return output_pdf
    except Exception as e:
        logging.error(f"Resume export failed: {e}")
        return None

# ========================
# Cover Letter Functions
# ========================

def cover_letter_prompt_creator(resume_string: str, jd_string: str) -> str:
   
    # protect from injections
    resume_string = sanitize_input(resume_string)
    jd_string = sanitize_input(jd_string)
   
    return f"""
    ### Role
    You are a professional cover letter writer tasked with creating a compelling, one-page cover letter that clearly shows 
    how my background and experience meet — or exceed — the requirements of a specific job description.

    The tone should be professional yet conversational — confident without arrogance, polished but human. 

    Your goal is to help me stand out by aligning the most relevant parts of my resume with the needs of the role.

    ---

    ### Guidelines

    1. **Relevance**
    - Highlight the 2–3 most relevant roles or experiences that directly support the job description.
    - Cut any content that doesn't contribute to a concise, tailored message.
    - Prioritize transferable skills, project outcomes, and business impact over duties.

    2. **Action & Results**
    - Use strong action verbs and quantify results when possible (e.g., % growth, time saved, revenue impact).

    3. **ATS Alignment**
    - Naturally weave in job description keywords and phrasing to optimize for applicant tracking systems (ATS).

    4. **Tone**
    - Aim for confident, plainspoken language — not overly formal or robotic.
    - Speak directly to the reader, like a capable peer making their case.

    5. **Formatting**
    - Return the full cover letter in **clean Markdown format** with appropriate paragraph spacing for readability.

    ---

    ### Input

    **My Resume:**
    {resume_string}

    **Job Description:**
    {jd_string}

    ---

    ### Output

    A complete, one-page **Markdown-formatted cover letter** that:
    - Emphasizes the most relevant experience, skills, and accomplishments;
    - Reflects the language and priorities of the job description;
    - Shows confidence, competence, and personality without fluff.
    """

def get_cover_response(prompt: str, model: str = "gpt-4o-mini", temperature: float = 0.7) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Professional Cover Letter Writer"},
            {"role": "user", "content": prompt}
        ],
        temperature = temperature
    )
    return response.choices[0].message.content

def save_cover_letter(response_string: str, company_name: str):
    os.makedirs("gpt_cover_letters", exist_ok = True)
    slug = company_name.lower().replace(" ", "_").replace(".", "")
    uid = str(uuid.uuid4())[:8]
    pdf_path = f"gpt_cover_letters/{slug}_{uid}_optimized_cover_letter.pdf"
    # md_path = f"gpt_cover_letters/{slug}_{uid}_optimized_cover_letter.md"

    try:
        # with open(md_path, "w", encoding="utf-8") as f:
        #     f.write(response_string)
        HTML(string = markdown(response_string)).write_pdf(pdf_path)
        return pdf_path # , md_path
    except Exception as e:
        logging.error(f"Cover letter save failed: {e}")
        return None# , md_path

# ========================
# Job Validator Functions
# ========================

def is_posting_recent(posting_date_str, days=60):
    try:
        date_posted = datetime.fromisoformat(posting_date_str)
        return (datetime.now() - date_posted) <= timedelta(days=days)
    except Exception as e:
        logging.warning(f"Date parsing failed for '{posting_date_str}': {e}")
        return False

generic_phrases = [
    "fast-paced environment", "team player", "self-starter", "excellent communication skills",
    "wears many hats", "wear many hats", "competitive salary", "generous benefits package",
    "dynamic team", "strong work ethic", "attention to detail"
]

def template_detector(job_description):
    score = sum(phrase in job_description.lower() for phrase in generic_phrases)
    return score >= 4

def mentioned_on_socials(company, job_title):
    query = f"{company} {job_title} #NowHiring OR #WeAreHiring OR #JobAlert OR #ApplyNow"
    return {
        "x": f"https://x.com/search?q={query.replace(' ', '%20')}&src=typed_query",
        "linkedin": f"https://linkedin.com/search/results/content/?keywords={query.replace(' ', '%20')}"
    }

def source_link_meta_date(url):
    try:
        resp = requests.get(url, timeout = 5)
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in ["datePublished", "article:published_time", "og:published_time"]:
            meta = soup.find("meta", {"property": tag}) or soup.find("meta", {"name": tag})
            if meta and meta.get("content"):
                return meta["content"]
    except Exception:
        return None
    return None

def detect_urgency_language(text):
    urgency_keywords = ["hiring now", "immediate opening", "urgent need", "start immediately", "apply today", "fast hire", "join our team", "#nowhiring", "we’re hiring"]
    return any(k in text.lower() for k in urgency_keywords)

def detect_job_board_source(url):
    if not url:
        return "❓ No URL provided"
    boards = ["greenhouse.io", "lever.co", "workable.com", "smartrecruiters.com", "breezy.hr", "jobs.jobvite.com"]
    for b in boards:
        if b in url:
            return f"✅ Reputable board: {b}"
    return "⚠️ Unknown or direct post"

def career_page_search_url(company, job_title):
    q = quote(f"{company} {job_title} site:{company}.com")
    return f"https://www.google.com/search?q={q}"


