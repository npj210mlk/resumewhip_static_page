# Round 4
import gradio as gr
import io
import pdfplumber
import requests
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
    source_link_meta_date,
    detect_urgency_language,
    detect_job_board_source,
    career_page_search_url
)
from bs4 import BeautifulSoup 

with gr.Blocks() as app:
    # --- Header ---
    gr.Markdown("""
    <h1 style='text-align:center; color:#1e90ff;'>🥇 Welcome To ResumeWhip!!</h1>
    <h2 style='text-align:center; color:#dd1eff;'>Your One-Stop Resume Optimizer Shop!</h2> 
    <h3 style='text-align:center;'>Powerful Simplicity: Just Verify → Upload → Optimize → Apply!</h3>
    """)

    with gr.Row():
        # --- Sidebar (simplified into Accordions) ---
        with gr.Column(scale=1):
            with gr.Accordion("🦮 How To Use This Website", open = False):
                gr.Markdown("""
                        1.) Crank Your Existing Resume To 11 - list every single skill and experience you have
                            (this is how our AI writes your resume and scores your chances);  
                        2.) Follow the Prompts To Load the Requested Info;  
                        3.) Choose Your Tool (you don't have to use all 3);  
                        4.) Proofread / Edit the Results Using the 'Copy/Pastes' below;  
                        5.) Download Your File as PDF; and 
                        6.) Apply!
                            """)
                
            with gr.Accordion("📚 Copy/Pastes for Resume Formatting", open=False):
                gr.Code("""
If you're not happy with the default resume 
format, you can make adjustments using the 
simple copy and pastes below:
                        
Want To Change Fonts:
# = Biggest  
## = Smaller  
### = Smallest
<b>text</b> = Bold  
<i>text</i> = Italic  
<u>text</u> = Underline
(⬆️ Can Be Combined)
                        
How About A List?
- = Bullet Point  
1. = Numbered List

Link Your Website:
[Your Website](https://www.yourwebsite.com)

Too "clumpy?" Break things up into separate lines, 
by leaving two spaces where you want the line 
to break (e.g. after a period).

Page cuts off where you don't want it to?
Start A New Page (copy/paste entire line below):
<div style="page-break-after: always; break-after: page;"></div>                      
                """, language="markdown")

            gr.Markdown("[📬 Need Help? Have Suggestions?](mailto:support@resumewhip.com)")

            gr.Markdown("### 🛡️ We never store, share, or sell your data. Ever.")

            gr.Markdown("### #️⃣ Know someone who could use this in their job search? Share away!")
            gr.HTML("""
                    <!-- Share Icons -->
    <div style="display:flex; flex-direction:row; gap:15px; justify-content:center; margin-top:10px;">
        <a href="https://www.facebook.com/sharer/sharer.php?u=https://resumewhip.com" target="_blank">
            <img src="https://upload.wikimedia.org/wikipedia/commons/0/05/Facebook_Logo_%282019%29.png" style="width:32px; height:32px;">
        </a>
        <a href="https://x.com/intent/post?url=https://resumewhip.com&text=Check%20out%20this%20awesome%20Resume%20Optimizer!" target="_blank">
            <img src="https://upload.wikimedia.org/wikipedia/commons/c/ce/X_logo_2023.svg" alt="X" style="width:36px; height:36px;">
        </a>
        <a href="https://www.linkedin.com/sharing/share-offsite/?url=https://resumewhip.com" target="_blank">
            <img src="https://upload.wikimedia.org/wikipedia/commons/8/81/LinkedIn_icon.svg" style="width:32px; height:32px;">
        </a>
        <a href="https://www.reddit.com/submit?url=https://resumewhip.com&title=Check%20this%20out!" target="_blank">
             <img src="https://cdn.simpleicons.org/reddit/FF4500" alt="Reddit" style="width:32px; height:32px;">
        </a>
    </div>
""")
#             gr.Markdown("### 💸 Donations appreciated... only if we've helped:")
#             gr.HTML("""
#                     <div style="text-align:left; display:flex; flex-direction:column; gap:10px; margin-top:15px;">
#         <!-- Support Buttons -->
#         <form action="https://www.paypal.com/donate" method="post" target="_blank">
#             <input type="hidden" name="business" value="YOUR_PAYPAL_EMAIL_OR_ID" />
#             <input type="hidden" name="currency_code" value="USD" />
#             <input type="image" src="https://www.paypalobjects.com/en_US/i/btn/btn_donate_LG.gif" 
#                border="0" name="submit" alt="Donate with PayPal" />
#         </form>
#         <a href="https://www.buymeacoffee.com/yourname" target="_blank">
#         <img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" style="height:40px;width:180px;">
#         </a>
#     </div>
# </div>
# """)

        # --- Main App ---
        with gr.Column(scale=5):
            with gr.Row():
                resume_input = gr.File(label="📝 Upload Your Resume Here", file_types = [".pdf", ".md", ".docx", ".txt"])
                company_input = gr.Textbox(label="🏢 Type In the Company Name", placeholder="e.g., ING Partners")
                job_input = gr.Textbox(label="🔬 Paste Entire Job Description", lines=8)

            gr.Markdown("<h2 style='text-align:center; color:#ff7f50;'>🧰 Tools In the Toolkit</h2>")

            with gr.Tab("📋 Job Validator"):
                with gr.Row():
                    # with gr.Column():
                    #     resume_input = gr.File(label="Upload Your Resume")
                    #     job_desc_input = gr.Textbox(label="Paste Job Description", lines=10)
                        # resume_input = gr.File(label="Upload Your Resume")
                        # job_desc_input = gr.Textbox(label="Paste Job Description", lines=10)
                    # with gr.Column():
                        jd_date = gr.Textbox(label="Posting Date (YYYY-MM-DD)")
                        jd_title = gr.Textbox(label="Job Title")
                        jd_company = gr.Textbox(label="Company Name")  # added for social check

                validate_btn = gr.Button("✅ Validate Job - A Quick Check To See If It's Legitimate")
                validation_output = gr.Markdown(label="Job Validation Results")

                def full_job_validator(resume_file, job_input_text, posting_date, company, job_title):
                    # --- Existing job validation logic ---
                    recent = is_posting_recent(posting_date)
                    template_flag = template_detector(job_input)
                    urgency_flag = detect_urgency_language(job_input)
                    social_links = mentioned_on_socials(company, job_title)

                    report = f"### 🕒 Posting Date Check:\n"
                    report += "✅ Job appears to be recent enough.\nNot a lot of jobs are still looking after 30 days." if recent else "⚠️ Warning! Job may be outdated.\n"

                    report += f"\n### 🤖 Template Language:\n"
                    report += "⚠️ Generic/template language detected - could be just harvesting data and / or candidates.\n" if template_flag else "✅ Posting looks specific enough to be an actual need.\n"

                    report += f"\n### ⚡ Urgency Language:\n"
                    report += "⚠️ Urgency words detected.\nProceed with caution, especially if the post is older than 30 days." if urgency_flag else "✅ No urgency language detected.\n"

                    report += f"\n### 🔍 Social Media Mentions:\n"
                    report += f"- [Search on X](<{social_links['x']}>)\n"
                    report += f"- [Search on LinkedIn](<{social_links['linkedin']}>)\n"

                    # # --- Optional: Resume processing ---
                    # if resume_file is not None:
                    #     resume_report = process_resume(resume_file, job_input)
                    #     report += f"\n### 📄 Resume Fit Analysis:\n{resume_report}\n"

                    return report

                validate_btn.click(
                    full_job_validator,
                    inputs=[resume_input, job_input, jd_date, jd_company, jd_title],
                    outputs=validation_output
                )

            # with gr.Tab("Job Validator"):
            #     jd_date = gr.Textbox(label="Posting Date (YYYY-MM-DD)")
            #     jd_title = gr.Textbox(label="Job Title")
            #     jd_validate_btn = gr.Button("✅ Validate Job")
            #     jd_validation_result = gr.Markdown()

            #     def validate_job(posting_date, company, job_title, job_description):
            #         recent = is_posting_recent(posting_date)
            #         template_flag = template_detector(job_description)
            #         urgency_flag = detect_urgency_language(job_description)
            #         social_links = mentioned_on_socials(company, job_title)

            #         report = f"### 🕒 Posting Date Check:\n"
            #         report += "✅ Job appears to be recent.\n" if recent else "⚠️ Job may be outdated.\n"

            #         report += f"\n### 🤖 Template Language:\n"
            #         report += "⚠️ Generic/template language detected - could be just harvesting candidates.\n" if template_flag else "✅ Posting looks specific enough to be an actual need.\n"

            #         report += f"\n### 🔍 Social Media Mentions:\n"
            #         report += f"- [Search on X](<{social_links['x']}>)\n"
            #         report += f"- [Search on LinkedIn](<{social_links['linkedin']}>)\n"

            #         return report

            #     jd_validate_btn.click(
            #         fn=validate_job,
            #         inputs=[jd_date, company_input, jd_title, job_input],
            #         outputs=jd_validation_result
            #     )
            
            with gr.Tab("Resume Optimizer"):
                run_resume = gr.Button("🧙 Whip Up Some Resume Magic!")
                resume_md = gr.Markdown()
                resume_edit = gr.Textbox(label="Optimized Resume Above. Make Any Edits In This Box. Or Don't - Up To You.", lines=10)
                suggestions = gr.Markdown(label="Suggestions")
                export_resume_btn = gr.Button("⬇ Download as PDF")
                export_resume_result = gr.File()

            with gr.Tab("Cover Letter Generator"):
                run_cover = gr.Button("📝 Write My Cover Letter")
                cover_output = gr.Textbox(label="Cover Letter", lines=12)
                export_cover_btn = gr.Button("⬇ Download as PDF")
                export_cover_result = gr.File()

            # with gr.Tab("Job Validator"):
            #     jd_date = gr.Textbox(label="Posting Date (YYYY-MM-DD)")
            #     jd_title = gr.Textbox(label="Job Title")
            #     jd_validate_btn = gr.Button("✅ Validate Job")
            #     jd_validation_result = gr.Markdown()

            #     def validate_job(posting_date, company, job_title, job_description):
            #         recent = is_posting_recent(posting_date)
            #         template_flag = template_detector(job_description)
            #         social_links = mentioned_on_socials(company, job_title)

            #         report = f"### 🕒 Posting Date Check:\n"
            #         report += "✅ Job appears to be recent.\n" if recent else "⚠️ Job may be outdated.\n"

            #         report += f"\n### 🤖 Template Language:\n"
            #         report += "⚠️ Generic/template language detected.\n" if template_flag else "✅ Looks specific.\n"

            #         report += f"\n### 🔍 Social Media Mentions:\n"
            #         report += f"- [Search on X](<{social_links['x']}>)\n"
            #         report += f"- [Search on LinkedIn](<{social_links['linkedin']}>)\n"

            #         return report

            #     jd_validate_btn.click(
            #         fn=validate_job,
            #         inputs=[jd_date, company_input, jd_title, job_input],
            #         outputs=jd_validation_result
            #     )

            # Resume events
            run_resume.click(fn=process_resume, inputs=[resume_input, job_input], outputs=[resume_md, resume_edit, suggestions])
            export_resume_btn.click(fn=export_resume, inputs=[resume_edit, company_input], outputs=[export_resume_result])

            # Cover letter events
            def generate_cover_letter(resume_file, job_input):
                if resume_file is None or not job_input or job_input.strip() == "":
                    return "⚠️ Sorry, but the tools need both a resume and pasted job description before they can do you any good."

                # Normalize extension safely
                fname = getattr(resume_file, "name", "")
                ext = fname.lower().split(".")[-1] if "." in fname else ""

            # Read resume text from PDF or text-like files
                resume_txt = ""
                try:
                    if ext == "pdf":
                        with pdfplumber.open(fname or resume_file) as pdf:
                            for page in pdf.pages:
                                resume_txt += (page.extract_text() or "")
                    else:
                    # Fallback: treat as text/markdown
                        with open(fname, "r", encoding="utf-8") as f:
                            resume_txt = f.read()
                except Exception as e:
                    return f"😐 Ruh-roh! Problem with the resume: {e}"

                prompt = cover_letter_prompt_creator(resume_txt, job_input)
                return get_cover_response(prompt)


            run_cover.click(fn=generate_cover_letter, inputs=[resume_input, job_input], outputs=[cover_output])
            export_cover_btn.click(fn=save_cover_letter, inputs=[cover_output, company_input], outputs=[export_cover_result])

    # --- Footer ---
    # gr.Markdown("""
    # <hr>
    # <p style='text-align:center; font-size:1.5em; color:gray;'>
    # 🛡️ Your data is never stored, shared, or sold. Ever.
    # </p>
    # """)

# Launch
app.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", "8080")))

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