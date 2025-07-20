# imports for both Resume and Cover Letter Optimizers
import os
import uuid
import re
import requests
from dotenv import load_dotenv
from openai import OpenAI
from markdown import markdown
from weasyprint import HTML
from bs4 import BeautifulSoup
from urllib.parse import quote

# import for Job Validator
from datetime import datetime, timedelta

# load dotenv
load_dotenv()

# assign "MY_SK" as global variable
open_apikey = os.getenv("MY_SK")

# ===== Resume Functions =====

# create the gpt_resumes folder
os.makedirs("gpt_resumes", exist_ok = True)

# Sanitizer function to protect the prompts (thank you, Jacob, for pointing this out!)
def sanitize_input(text: str) -> str:
    """
    This function is meant to prevent bad actors from corrupting prompts with potentially
    malicious patterns. The problem is called 'prompt injecting,' and can be as problematic from prompts
    as sql-injecting is for passwords.

    Args:
        text (str): the resume or job description, whatever the user input is
    Returns:
        str: a slugged / cleaned version of that input
    """
    # Strip Markdown/code block markers, quotes, and classic injection phrases
    disallowed_patterns = ["```", "'''", '"""', "<script>", "</script>", "Ignore previous instructions", "Forget all prior directions"]
    
    for pattern in disallowed_patterns:
        text = text.replace(pattern, "") #<- replace those disallowed patterns with ""

    # remove double newlines / strip extra whitespace
    text = text.strip()
    
    return text

# prompt creator function - the lambda function from scratchpad
# basically, Steps 1, 2, and 3 from scratchpad
def prompt_creator(resume_string: str, job_desc_string: str) -> str:
    """
    Using the prompt engineered in the scratchpad 'lambda' function, this function uses the power of ChatGPT's 4o-mini-mini engine to
    act as a professional resume optimizer to take my existing resume and:
        1.) Use action-verbs and job posting keywords to optimize it for Applicant Tracking Systems;
        2.) Provide us with feedback on any changes that can be made to strengthen the resume; and 
        3.) Format the adjusted, AI-assisted resume in a clean Markdown format

    Args:
        resume_string (str): our existing resume text input
        job_desc_string (str): The target job description text

    Returns:
        str: A formatted prompt string containing instructions for resume optimization
    """
    # Protect the prompt engineering / LLM instructions
    resume_string = sanitize_input(resume_string)
    job_desc_string = sanitize_input(job_desc_string)

    return f"""
    ### Role: 
    You are a professional resume optimization expert. Your task is to tailor my resume to align with a specific job description.

    My career goals emphasize collaboration, problem-solving, and helping businesses extract value from their data. Your output should be a **targeted, one-page resume** optimized for recruiters and Applicant Tracking Systems (ATS).

    ---

    ### Guidelines

    **1. Relevance**
    - Prioritize **my most relevant skills and experiences** based on the job description.
    - De-emphasize or omit unrelated content to keep the resume **concise and focused**.
    - Limit to **2–3 most relevant roles** with **2–3 key bullet points** per role.
    - Highlight only the **core competencies** matching the job requirements.

    **2. Career Pivot Strategy (Data Engineer → PM/TPM)**  
    - Reframe my experience to emphasize transferable **Project/Product Management** skills.  
    - Highlight past responsibilities where I:  
    - Translated technical requirements into business solutions  
    - Led cross-functional initiatives or teams  
    - Owned timelines, roadmaps, or deliverables  
    - Facilitated communication between technical and non-technical stakeholders  
    - Position me as someone ready to step into a **Technical Product Manager** or 
        **Technical Project Manager** role.  
    - Use language common to PM/TPM resumes (e.g., "drove delivery", "owned outcomes", "prioritized 
        feature development", "collaborated with stakeholders").  

    **3. Impactful Results**
    - Use **strong action verbs** and **quantifiable outcomes** (%, $, time saved, etc).
    - Emphasize how my experience **adds measurable value**.
    - Customize the Experience section to directly reflect the responsibilities and outcomes in the job posting.

    **4. Summary Section**
    - Tailor the Summary to the job description and recruiter expectations.
    - Clearly articulate how my experience enables me to succeed quickly in this role.

    **5. Keyword Optimization**
    - Naturally integrate **keywords and phrases** from the job posting to improve ATS compatibility.

    **6. Recommendations (if gaps exist)**
    If the resume doesn't fully match the job:
    - Suggest **additional skills** to highlight.
    - Recommend **certifications or courses** (completed or worth pursuing).
    - Propose **project ideas** that better align with the role.
    - Recommend edits to improve the Summary based on the job's intent.
    - Provide a **predicted resume–job fit score** (0–100%).

    **7. Formatting**
    - Output the resume in **clean Markdown** format.
    - Include an **“Additional Suggestions”** section with actionable improvements.

    ---

    ### Input:
    - **Resume**: `{resume_string}`
    - **Job Description**: `{job_desc_string}`

    ---

    ### Output:

    1. **Tailored Resume**:
    - A one-page resume in Markdown.
    - Focuses on relevant experience, uses confident language, and includes job-specific keywords.

    2. **Additional Suggestions** *(if applicable)*:
    - Highlight missing skills, certifications, or project ideas.
    - Recommend edits to align tone and content with job description.
    - Include fit score.
    """

# Step 4 from scratchpad
def get_resume_response(prompt: str, model: str = "gpt-4o-mini", temperature: float = 0.7) -> str:
    """
    Now that we've got the resume optimized, we send it to OpenAI's API, where it sends us back the
    optimized resume response. 

    Args:
        prompt (str): The formatted prompt containing the resume and job description
        model ("gpt-4o-mini"): The OpenAI engine to use.
        temperature (float, optional): Controls randomness in the response. Hard-set to 0.7, 
        a popular temperature setting.

    Returns:
        str: The AI-generated optimized resume

    Raises:
        OpenAIError: If there's an issue with the API call
    """
    # set up api client
    client = OpenAI(api_key = open_apikey)

    # make the call and set response variable to hold the all info we get back
    response = client.chat.completions.create(
    model = model,
    
    # set our roles up - think of casting a play: "Today, the role of the Expert Resume Writer will be played by the system."
    messages = [
        {"role" : "system", "content" : "Expert Resume Writer"},
        {"role" : "user", "content" : prompt}
    ],
    
    # give it some creative license with our default 0.7 rating
    temperature = temperature
)

    # extract and return our response
    return response.choices[0].message.content

# Step 5 (more or less) from scratchpad
def process_resume(resume_file, job_desc_string):
    """
    Compares the resume file against the job description to create an optimized version.

    Args:
        resume (file): A file object containing the resume in markdown format
        job_desc_string (str): The job description text to optimize the resume against

    Returns:
        tuple: A tuple containing three elements:
            - str: The optimized resume in markdown format (for display)
            - str: The same optimized resume (for editing)
            - str: Suggestions for improving the resume
    """
    try:
        # Read resume file
        with open(resume_file.name, "r", encoding="utf-8") as f:
            resume_md = f.read()

        # Create prompt from inputs
        prompt = prompt_creator(resume_md, job_desc_string)

        # Get AI response from LLM
        response = get_resume_response(prompt)

        # ----------- Extract Sections -----------
        # Default values in case parsing fails
        optimized_resume = "⚠️ Resume not properly generated."
        suggestions = "No additional suggestions returned."

        # Use regex to extract both sections
        match = re.search(
            r"(?:#+\s*Tailored Resume.*?)(?P<resume>.*?)"
            r"(?:#+\s*Additional Suggestions.*?)(?P<suggestions>.*)",
            response,
            re.DOTALL | re.IGNORECASE,
        )

        if match:
            optimized_resume = match.group("resume").strip()
            suggestions = match.group("suggestions").strip()
        else:
            # Fallback split method, if regex fails
            parts = response.split("## Additional Suggestions")
            optimized_resume = parts[0].strip()
            if len(parts) > 1:
                suggestions = parts[1].strip()

        # Prepend headers
        optimized_resume = "## Tailored Resume\n\n" + optimized_resume
        suggestions = "## Additional Suggestions\n\n" + suggestions

        return [optimized_resume, optimized_resume, suggestions]

    except Exception as e:
        return [
            "⚠️ An error occurred while processing your resume.",
            "",
            f"## Additional Suggestions\n\nError details:\n```\n{e}\n```"
        ]

# Steps 6 and 7 from scratchpad
def export_resume(new_resume, company_name):
    """
    Takes the markdown resume, converts it to PDF format, and saves it.

    Args:
        new_resume (str): The new, optimized resume content in markdown format

    Returns:
        str: A message indicating success or failure of the PDF export
    """

    # slug company name
    company_slugged = re.sub(r"[^a-zA-Z0-9_-]", "", company_name.lower())
    unique_id = str(uuid.uuid4())[:8] 

    # build out the filename w/ slugged name and unique_id
    output_pdf_file = f"gpt_resumes/{company_slugged}{unique_id}_optimized_resume.pdf"
    
    try:
        # Convert Markdown to HTML
        html_content = markdown(new_resume)
        # Convert HTML to PDF and save
        HTML(string=html_content).write_pdf(output_pdf_file)
        
        return f"✅ Successfully exported and saved your resume to {output_pdf_file}"
    except Exception as e:
        return f"❌ Failed to export resume: {str(e)}"
    
# ===== Cover Letter Functions ====

# import os # use personal openai key
# import uuid # for unique file usernames
# import re # for future 'generate' button
# from dotenv import load_dotenv # loads environmental variables

# # for working with OpenAI:
# from openai import OpenAI

# # HTML to Markdown for editing
# from markdown import markdown
# from IPython.display import display, Markdown # <-- make it look nice in the notebook

# # for design
# from weasyprint import HTML # see previous notebook for weasyprint notes

# # env file load check
# load_dotenv()

# create a directory
os.makedirs("gpt_cover_letters", exist_ok=True)

# create the prompt for the cover letter
def cover_letter_prompt_creator(resume_string: str, jd_string: str) ->str:
    """
    Using the prompt engineered in the scratchpad 'lambda' function, this function uses the power of 
    ChatGPT's 4o-mini engine to act as a professional cover letter writer, take my 
    existing resume, and:
        1.) Use action-verbs and job posting keywords to optimize it for Applicant Tracking Systems;
        2.) Apply any relevant experience / projects to showcasing how I can exceed the 
            job description; and 
        3.) Format the adjusted, AI-assisted cover letter in a clean Markdown format

    Args:
        resume_string (str): our existing resume text input
        jd_string (str): The target job description text

    Returns:
        str: A formatted prompt string containing instructions for resume optimization
    """
    # Again: protect from injections
    resume_string = sanitize_input(resume_string)
    jd_string = sanitize_input(jd_string)

    return f"""
    ### Role: 
    -  You are a professional cover letter writer, and your goal is to create a unique cover 
    letter that showcases how the job experience in my resume can exceed the needs listed 
    in a specific job description.
    
    - Your need to dazzle recruiters with a conversational yet professional tone that sets my 
    candidacy apart from others applying for that same role.

    ### Guidelines:
    1. **Relevance**:
    - Prioritize the particular skills and experiences I have with what is **most relevant to the 
    job position**.
    - De-emphasize or even completely remove irrelevant details to ensure a **concise** but 
    **descriptive** cover letter.
    - Limit integrating actual work experience and job needs paragraphs to my 2-3 most relevant roles
    - Select only the core competencies and listed projects most relevant to the job description

    2. **Action-Driven Results**:
    - Choose **strong action verbs** and **quantifiable results** (eg: percentages, revenues, 
    efficiency improvement, etc.)

    3. **Keyword Optimization**:
    - Integrate **keywords** and phrases from the job description naturally to optimize for 
    Applicant Tracking Systems (ATS)

    4. **Tone**:
    - Please keep the **tone** of the cover letter **professional** **without sounding like a robot**. 
    - The **objective** is to **exhibit competence** in the duties listed, but also to sound 
    like I'm talking to a cohort.

    5. **Formatting**:
    - Output the tailored cover letter in a **clean Markdown format** for ease of editing.

    ---

    ## Input:
    - **My resume**:
    {resume_string}

    - **The Job Description**:
    {jd_string}

    ---

    ### Output:
    **Tailored Cover Letter**:
    - A cover letter in **Markdown format** that emphasizes relevant experience, skills, and achievements.
    - Incorporates job description **keywords** to optimize for ATS.
    - Uses confident language and is no longer than **one page**.
    """

def get_cover_response(prompt: str, model: str = "gpt-4o-mini", temperature: float = 0.7) -> str:
    """
    Now that we've got the cover letter set up for optimization, we send it to OpenAI's API, 
    which sends back the optimized cover letter response. 

    With this function, we:
    1.) set up our OpenAI client;
    2.) make an API call to OpenAI using the provided prompt; and 
    3.) returns to us the generated cover letter response.

    Args:
        prompt (str): The formatted prompt containing the resume and job description
        api_key (str): our OpenAI API key for call authentication
        model ("gpt-4o-mini): The OpenAI engine to use. Here, we're hard-coding it to "gpt-4o-mini"
        temperature (float, optional): Controls randomness in the response.

    Returns:
        str: The AI-generated optimized cover letter, tailored to best fit the position.

    Raises:
        OpenAIError: If there's an issue with the API call
    """
    # set up api client
    client = OpenAI(api_key = open_apikey)

    # make the call and set response variable to hold the all info we get back
    response = client.chat.completions.create(
    model = model,
    
    # set our roles up - think of casting a play: 
    # "Today, the role of the Professional Cover Letter Writer  will be played by the system."
    messages = [
        {"role" : "system", "content" : "Professional Cover Letter Writer"},
        {"role" : "user", "content" : prompt}
    ],
    
    # give it some creative license with our default 0.7 rating (above this, text was unpredictable)
    temperature = temperature
    )

    # extract and return our response
    return response.choices[0].message.content

def save_cover_letter(response_string: str, company_name: str, output_dir: str = "gpt_cover_letters"):
    """
    Saves the resume ChatGPT wrote / optimized and saves it as a PDF AND a Markdown.
    Args:
        response_string (str): the AI-optimized cover letter in Markdown format.
        company_name (str): The name of the company for - again, for file naming.
        output_dir (str): The directory where the files will be saved; defaults to "gpt_cover_letters"
    Returns:
        tuple: A tuple containing the paths to the saved PDF and Markdown files.
               Returns (None, None) if an error occurs during PDF conversion.
    """
    # Make sure the  directory exists so you can send the file
    os.makedirs(output_dir, exist_ok=True)

    # Slug / Clean company name and generate unique ID and file path
    company_slugged = company_name.lower().replace(" ", "_").replace(".", "") #<- "taco deli" becomes "taco_deli"
    unique_id = str(uuid.uuid4())[:8] #<- gets unique 8-character code 
    output_pdf_file = os.path.join(output_dir, f"{company_slugged}_{unique_id}_optimized.pdf") #<- preps as PDF
    output_markdown_file = os.path.join(output_dir, f"{company_slugged}_{unique_id}_optimized.md")# <- preps as MD

    # Save as Markdown (from Block 3)
    try:
        with open(output_markdown_file, "w", encoding="utf-8") as file:
            file.write(response_string)
        print(f"Cover letter saved as Markdown: {output_markdown_file}")
    except IOError as e:
        print(f"Apolgies, but we couldn't save the Markdown file : {e}")
        # We might still proceed with PDF if Markdown fails, depending on requirements

    # Put WeasyPrint to work
    try:
        html_content = markdown(response_string)
        HTML(string=html_content).write_pdf(output_pdf_file)
        print(f"Cover letter saved as PDF: {output_pdf_file}")
        return output_pdf_file, output_markdown_file
    except Exception as e: # Catch a broader exception for Weasyprint issues
        print(f"Error converting to PDF with Weasyprint: {e}")
        print("Please ensure Weasyprint is correctly installed and its dependencies (like Cairo) are met.")
        return None, output_markdown_file # Return None for PDF if it failed

# Job Validator

# Is posting within the last 60 days?
def is_posting_recent(posting_date_str, days = 60):
    """
    This function checks the job posting date using datetime. 
    It takes the job's posting date and subtracts the number of days from today's date.
    A time limit of 60 days was set because in today's job market, there's no way a job
    legitimately stays open for longer than that.
    """
    try:
        date_posted = datetime.strptime(posting_date_str, "%Y-%m-%d")
        return (datetime.now() - date_posted) <= timedelta(days = days)
    
    # let user know if it's a missing date or a date not in the '%Y-%m-%d'format
    except Exception as e: 
        print(f"Date parsing field has failed: {e}")
        return False
    
# Does it look like someone just threw the job up using AI or a template?
generic_phrases = [
    "fast-paced environment", "team player", "self-starter",
    "excellent communication skills", "wears many hats", "wear many hats",
    "competitive salary", "generous benefits package", "dynamic team", 
    "strong work ethic", "attention to detail"
]

def template_detector(job_description):
    """
    This function checks the job description for any of the generic phrases above and counts them.
    If there's more than 4, a flag will mark suspicion of some kind of template or AI use.
    """
    job_lower = job_description.lower()
    score = sum(phrase in job_lower for phrase in generic_phrases)
    return score >= 4

# Is the job being mentioned on any of the company's social media posts?
def mentioned_on_socials(company, job_title):
    """
    Function to search common phrases on X and LinkedIn indicating a fresh job post.
    Nobody hashtags anything older than the 60-day limit we set on the posting earlier.
    """
    query = f"{company} {job_title} #NowHiring OR #WeAreHiring OR #JobAlert OR #ApplyNow"
    return {
        "x": f"https://x.com/search?q={query.replace(' ', '%20')}&src=typed_query",
        "linkedin": f"https://linkedin.com/search/results/content/?keywords={query.replace(' ', '%20')}"
    }

def source_link_meta_date(url):
    try:
        resp = requests.get(url, timeout=5)
        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in ["datePublished", "article:published_time", "og:published_time"]:
            meta = soup.find("meta", {"property": tag}) or soup.find("meta", {"name": tag})
            if meta and meta.get("content"):
                return meta["content"]
    except Exception as e:
        return None
    return None

def detect_urgency_language(text):
    urgency_keywords = [
        "hiring now", "immediate opening", "urgent need", "start immediately",
        "apply today", "fast hire", "join our team", "#nowhiring", "we’re hiring"
    ]
    return any(keyword in text.lower() for keyword in urgency_keywords)

def detect_job_board_source(url):
    if not url:
        return "❓ No URL provided"
    boards = ["greenhouse.io", "lever.co", "workable.com", "smartrecruiters.com", "breezy.hr", "jobs.jobvite.com"]
    for board in boards:
        if board in url:
            return f"✅ Reputable board: {board}"
    return "⚠️ Unknown or direct post"

def career_page_search_url(company, job_title):
    query = quote(f"{company} {job_title} site:{company}.com")
    return f"https://www.google.com/search?q={query}"

def detect_urgency_language(text):
    urgency_keywords = [
        "hiring now", "immediate opening", "urgent need", "start immediately",
        "apply today", "fast hire", "join our team", "#nowhiring", "we’re hiring"
    ]
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in urgency_keywords)



