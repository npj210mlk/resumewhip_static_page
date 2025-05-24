from flask import Flask, render_template, request, flash, redirect, url_for, send_file # jsonify(?)
import os
from dotenv import load_dotenv
import google.generativeai as genai
from markdown import markdown
import tempfile
import re # <-- regex library for slugging company name later

# import the functions from 'gemini_flash_functions' python file:
# from gemini_flask_functions import (
#     configure_gemini_api,
#     tailored_resume_function_schema,
#     gemini_initialization_with_function_calling,
#     generate_tailoring_prompt,
#     get_gemini_response_with_function_calling
# )

# start Flask
app = Flask(__name__)
# add a secret key to make the flask app secure - this one is 24-bytes.
app.secret_key = os.urandom(24) 

# Load environment variables
load_dotenv()

# call the api
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY was not loaded from your environment.")
genai.configure(api_key=GEMINI_API_KEY)

def parse_gemini_response(response):
    """
    Parse the Gemini API response to extract the tailored resume and suggestions.
    This is an adaptation of the handle_gemini_response function that returns values
    instead of writing to a file.
    """
    tailored_resume = None
    additional_suggestions = None
    
    if response.candidates:
        first_candidate = response.candidates[0]

        if first_candidate.content and first_candidate.content.parts:
            first_part = first_candidate.content.parts[0]

            if first_part.function_call:
                function_call = first_part.function_call

                if function_call.name == "tailor_resume":
                    arguments = function_call.args
                    tailored_resume = arguments.get("tailored_resume")
                    additional_suggestions = arguments.get("additional_suggestions")
            elif first_part.text:
                # Fallback if function calling didn't work
                tailored_resume = first_part.text
    
    # output had markdown fences (e.g., "```markdown")
    # if block below cleans up the output

    if tailored_resume and tailored_resume.strip().startswith("```markdown") and tailored_resume.strip().endswith("```"):
        # remove the "```markdown" at the beginning
        tailored_resume = tailored_resume.strip()[len("```markdown"):].strip()
        # remove ```fence from the end
        tailored_resume = tailored_resume.rsplit("```", 1)[0].strip()

    
    return tailored_resume, additional_suggestions

# Configure Gemini API on app startup
try:
    configure_gemini_api()
    function_schema = tailored_resume_function_schema()
    gemini_model = gemini_initialization_with_function_calling(function_schema)
except ValueError as e:
    print(f"Error during initialization: {e}")
    gemini_model = None

@app.route("/", methods=["GET"])
def index():
    """Home page with form to upload resume and job description"""
    return render_template("index.html")

@app.route("/tailor-resume", methods=["GET", "POST"])
def tailor_resume():
    """Process the resume and job description to generate a tailored resume"""
    if not gemini_model:
        flash("API configuration error. Please check your environment variables.")
        return redirect(url_for("index"))
    
    # Get resume, company name, and job description from form
    resume_text = request.form.get("resume_text")
    copmany_name = request.form.get("company_name")
    jd_text = request.form.get("job_description")

    if not resume_text or not jd_text:
        flash("Please provide both resume and job description.")
        return redirect(url_for("index"))
    
    try:
        # Generate tailored resume
        prompt = generate_tailoring_prompt(resume_text, jd_text)
        response = get_gemini_response_with_function_calling(
            gemini_model, 
            prompt, 
            function_schema
        )
        
        tailored_resume, additional_suggestions = parse_gemini_response(response)
        
        if not tailored_resume:
            flash("Failed to generate tailored resume. Please try again.")
            return redirect(url_for("index"))
            
        # Convert Markdown to HTML for display
        tailored_resume_html = markdown(tailored_resume)
        
        return render_template(
            "result.html", 
            # pass tailored_resume
            tailored_resume_html=tailored_resume_html,
            tailored_resume_md=tailored_resume,
            # pass company name
            company_name=company_name, 
            # pass any additional suggestions
            additional_suggestions=additional_suggestions
            
        )
        
    except Exception as e:
        flash(f"An error occurred: {str(e)}")
        return redirect(url_for("index"))

@app.route("/download-resume", methods=["POST"])
def download_resume():
    """Download the tailored resume as a markdown file"""
    tailored_resume = request.form.get("tailored_resume_md")
    
    if not tailored_resume:
        flash("No resume data to download.")
        return redirect(url_for("index"))
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".md") as temp:
        temp_path = temp.name
        temp.write(tailored_resume.encode("utf-8"))
    
    # Send the file to the user
    try:
        return send_file(
            temp_path,
            as_attachment=True,
            download_name="tailored_resume.md",
            mimetype="text/markdown"
        )
    finally:
        # Clean up the temporary file after sending
        os.unlink(temp_path)

# save the edited / optimized resume
@app.route("/save-edited-resume", methods=["POST"])
def save_edited_resume():
    """
    Takes the edits you made based on the additional suggestions,
    and allows you to save them to your machine.
    """
    final_resume_content = request.form.get("final_resume_content")
    company_name = request.form.get("company_name_for_resume_tracking")

    # return to home page if no resume content is found
    if not final_resume_content:
        flash("Sorry - no resume content to save.")
        return redirect(url_for("index"))
    
    # generate a filename for the optimized resume
    if company_name:
        # slug it to clean it from spaces / characters
        company_slugged = re.sub(r"[^a-zA-Z0-9_-]", "", company_name.lower().replace(" ", "_"))
        download_filename = f"{company_slugged}_tailored_resume.md"
    else:
        download_filename = "tailored_resume.md"
    
    # we need to create a temporary file here to make the Python available as a standard file
    # that can be sent to the server
    with tempfile.NamedTemporaryFile(delete=False, suffix=".md") as temp:
        temp_path = temp.name
        temp.write(final_resume_content.encode("utf-8"))
    
    try:
        return send_file(
            temp_path,
            as_attachment=True,
            download_name=download_filename,
            # specify markdown as the text 
            mimetype="text/markdown"
        )
    
    finally:
        # delete when done
        os.unlink(temp_path)

if __name__ == "__main__":
    # Check if running in IPython/Jupyter
    try:
        get_ipython
        # If we're in IPython/Jupyter, don't use the auto-reloader
        print("Flask app is ready. Access it at http://127.0.0.1:5000/")
        print("To run the app, use: app.run()")
    except NameError:
        # Normal Python environment
        app.run(debug=True)

# for local testing - erase for production
app.run()