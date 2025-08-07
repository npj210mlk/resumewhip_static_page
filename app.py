# import "gradio" for UI
import gradio as gr
import io
import pdfplumber

#import "requests" to simplify HTTP requests
import requests

# import functions, a file created in the job folder that houses the functions Gradio needs to do its job
from new_functions import (
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
    source_link_meta_date,
    detect_urgency_language,
    detect_job_board_source,
    career_page_search_url
)

# import BeautifulSoup to check for published jobdate is in posting's metadata - checking for link's age here.
from bs4 import BeautifulSoup 

with gr.Blocks(css="""
    .section-header {
        text-align: center;
        color: #1e90ff;
        font-size: 2.5em;
        font-family: 'Segoe UI', sans-serif;
        font-weight: bold;
        margin-top: 20px;
        margin-bottom: 10px;
    }
    .subtext {
        text-align: center;
        font-size: 1.1em;
        color: #555;
        margin-bottom: 30px;
    }
    .gr-button {
        font-weight: bold;
        font-size: 1.1em;
        padding: 0.75em 1.5em;
        border-radius: 12px;
    }
""") as app:

    # Header
    gr.Markdown("<div class='section-header'>🥇 Welcome To atsbeater.com - Where We Help Your Resume Crush the ATS Overlords!</div>")
    gr.Markdown("""
        <div class='subtext'>
            Simply click or drag / drop your main resume, enter company name, paste in the provided job description, and BOOM: a keyword-optimized resume and cover letter is ready for your review and export.  
            Or, afraid that might be a ghost job there just to collect your data? Check out the Job Validator tab - we'll help you see if the job posting is real or sus.
        </div>
    """)

    # Inputs

    with gr.Row():
        resume_input = gr.File(label="📄 Upload Main Resume (either .pdf or .md)", file_types = [".pdf", ".md"])
        company_input = gr.Textbox(label="🏢 Company To Whom You're Sending This Thing", placeholder="e.g., Target, Amazon, etc.")
        job_input = gr.Textbox(label="📝 Job Description", lines=8, placeholder="Paste full job description here")

    gr.Markdown("<div class='section-header'>🧰 Tools!</div>")

    with gr.Tab("✨ Resume Optimizer"):
        gr.Markdown("<div class='section-header'>🤓 Resume Optimizer</div>")
        run_resume = gr.Button("✨ Optimize Resume")
        resume_md = gr.Markdown(label="Optimized Resume (Markdown)")
        resume_edit = gr.Textbox(label="✏️ Edit Your Resume Below", lines=10, interactive=True)
        suggestions = gr.Markdown(label="🔍 Suggestions")
        export_resume_btn = gr.Button("⬇ Export Resume as PDF")
        # for personal testing
        # export_resume_result = gr.Markdown()
        export_resume_result = gr.File(label = "📄 Download Your Optimized Resume PDF")

    with gr.Tab("📬 Cover Letter Generator"):
        gr.Markdown("<div class='section-header'>👋 Cover Letter Generator</div>")
        run_cover = gr.Button("📝 Click Here To Write Your Cover Letter")
        cover_output = gr.Textbox(label="Generated Cover Letter - Please Proofread and Check for <<cough cough>> Accuracy. 'I cured Polio!' No, you didn't.", lines=15, interactive=True)
        export_cover_btn = gr.Button("⬇ Export Cover Letter as PDF")
        # to export cover letter to user
        export_cover_result = gr.File(label = "📄 Download Your Cover Letter PDF")
        # for personal testing
        # export_cover_result = gr.Markdown()
        
    with gr.Tab("🔍 Job Validator"):
        gr.Markdown("<div class='section-header'>🕵️‍♂️ Job Validation Tool</div>")
        gr.Markdown("<div class='subtext'>Is this a real job, or just an attempt to mine your data? Check how recent, relevant, and visible a job post is on socials.</div>")

        with gr.Row():
            job_url = gr.Textbox(label="🔗 Optional: Job Posting URL", placeholder="https://jobs.greenhouse.io/...")
            jd_date = gr.Textbox(label="📅 Job Posting Date (Format: YYYY-MM-DD)", placeholder="e.g., 2025-06-01, or your best guess.")
            job_title = gr.Textbox(label="🔖 Job Title", placeholder="e.g., Technical Support Analyst")

        jd_validate_btn = gr.Button("✅ Run Job Validation")
        jd_validation_result = gr.Markdown()

        def source_link_meta_date(url):
            try:
                resp = requests.get(url, timeout=5)
                soup = BeautifulSoup(resp.text, "html.parser")

                # Look for known meta tags
                for tag in ["datePublished", "article:published_time", "og:published_time"]:
                    meta = soup.find("meta", {"property": tag}) or soup.find("meta", {"name": tag})
                    if meta and meta.get("content"):
                        return meta["content"]
            except Exception as e:
                return None
            return None

        def validate_job(posting_date, company, job_title, job_description, job_url):
            # handle user error / lack of info
            if not company or not job_description:
                return "Please enter at least the company name and job description."
                
            # Existing checks
            recent = is_posting_recent(posting_date)
            template_flag = template_detector(job_description)
            urgency_flag = detect_urgency_language(job_description)

            # New ones
            meta_date = source_link_meta_date(job_url)
            board_check = detect_job_board_source(job_url)
            career_search = career_page_search_url(company, job_title)

            report = f"### 🕒 Posting Date:\n"
            report += "✅ User-entered date is recent enough so that candidates are still being considered.\n" if recent else "⚠️ Possibly outdated - plenty of time to have filled this position.\n"
            report += f"📅 Meta date from page: `{meta_date}`\n" if meta_date else "Sadly, though, we couldn't find any exact publishing metadata from the page.\n"

            report += f"\n### 🤖 Template Detection:\n"
            report += "⚠️ Generic language detected - looks like a template was used.\n" if template_flag else "✅ Description looks specific enough to look like it was written by an actual person.\n"

            report += f"\n### 🚨 Urgency Signal:\n"
            report += "✅ Urgency signals found in description - genuine need for this position is expressed.\n" if urgency_flag else "⚠️ No urgency keywords found, so they're either taking their time or just harvesting candidates.\n"

            report += f"\n### 🌐 Job Source:\n{board_check}\n"

            report += f"\n### 🧭 Career Site Check:\nTry searching: [Google Career Match]({career_search})"

            return report
    
    jd_validate_btn.click(
        fn=validate_job,
        inputs=[jd_date, company_input, job_title, job_input, job_url],
        outputs=jd_validation_result
    )

    # Resume events
    run_resume.click(fn=process_resume, inputs=[resume_input, job_input], outputs=[resume_md, resume_edit, suggestions])
    export_resume_btn.click(fn=export_resume, inputs=[resume_edit, company_input], outputs=[export_resume_result])

    # Cover letter events
    def generate_cover_letter(resume_file, job_desc):
        # exception handling
        if resume_file is None or job_desc.strip() == "":
            return "⚠️ Sorry, but we need a resume and job description before we can generate a cover letter worth anything."
        try: 
            # look for the file extension
            if resume_file.name.lower().endswith(".pdf"):
                resume_txt = " "
                with pdfplumber.open(resume_file) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            resume_txt += text + "/n"
            elif resume_file.name.lower().endswith(".md"):
                with open(resume_file.name, "r", encoding = "utf-8") as f: 
                    resume_txt = f.read()
                    
            # if resume_file.name.lower().endswith(".pdf"):
            #     resume_txt = " "
            #     with pdfplumber.open(resume_file.name) as pdf:
            #         for page in pdf.pages:
            #             text = page.extract_text()
            #             if text:
            #                 resume_txt += text + "/n"
            # elif resume_file.name.lower().endswith(".md"):
            #     resume_txt = resume_file.read().decode("utf-8")

            else:
                return "💀 Unsupported file type. Please upload a resume with either a '.pdf' or '.md' extension."

            # print chunk of resume for user to see resume was loaded
            print("✅ Resume text that was loaded (first 300 chars): \n", resume_txt[:300])
            
            prompt = cover_letter_prompt_creator(resume_txt, job_desc)
            
            return get_cover_response(prompt)

        except Exception as e:
            return f"😐 Ruh-roh. There was an error reading your resume: {e}"

    def export_cover_handler(cover_text, company):
        pdf, md = save_cover_letter(cover_text, company)
        # for webapp
        return pdf
        # for personal
        # return f"✅ PDF saved at: `{pdf}`" if pdf else "❌ Failed to export."

    run_cover.click(fn=generate_cover_letter, inputs=[resume_input, job_input], outputs=[cover_output])
    export_cover_btn.click(fn=export_cover_handler, inputs=[cover_output, company_input], outputs=[export_cover_result])

# Launch
app.launch(server_name="0.0.0.0", server_port=8080, share = True)