from flask import Flask, render_template, request, flash, redirect, url_for, session
import os
from dotenv import load_dotenv
import google.generativeai as genai
from markdown import markdown
import tempfile
import logging  # Import the logging module
from gemini_flask_functions import *

# import the functions from "gemini_flask_functions" python file:
# Assuming this file is in the same directory.  If not, adjust the import.
# try:
#     from gemini_flask_functions import (
#         configure_gemini_api,
#         tailored_resume_function_schema,
#         gemini_initialization_with_function_calling,
#         generate_tailoring_prompt,
#         get_gemini_response_with_function_calling,
#     )
# except ImportError as e:
#     print(f"Error importing gemini_flask_functions: {e}")
#     #  Consider exiting here if this is critical:
#     #  import sys
#     #  sys.exit(1)

# Load environment variables
load_dotenv()

# start Flask
app = Flask(__name__)
# required for sessions
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev")

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# set up the folder to store uploaded files (eg: your resume)
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# call the api
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.error("We (well: NICK) messed up. Bozo didn't correctly load the GEMINI_API_KEY from the environment.")
    #  Don't raise an exception here.  Handle it more gracefully in the routes.
    # raise ValueError("GEMINI_API_KEY was not loaded from your environment.")
else:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("Holy cow: it's working!!")


# Global variable for the Gemini model
# gemini_model = None

# Set up the function schema:
function_schema = {
    "name": "tailor_resume",
    "description": "Make my resume fit the job description so I can get a damn recruiter on the phone.",
    "parameters": {
        "type": "object",
        "properties": {
            "tailored_resume": {
                "type": "string",
                "description": "Your Markdown-formatted resume - for easy editing.",
            },
            "additional_suggestions": {
                "type": "string",
                "description": "Not bad! But here are some ideas to make your resume stronger for this position.",
            },
        },
        "required": ["tailored_resume"]
    }
}

# Inialize the Gemini 2.0 Flash Engine
gemini_model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    tools=[{"function_declarations": [function_schema]}]
)

# Throw in the Prompt aimed at the resume and job description
def generate_tailoring_prompt(resume_text, jd_text):
    return f"""
You are a professional resume optimization expert.
Optimize the resume I have provided you to align with the given job description following the guidelines below:

1. Make the resume one page, relevant, keyword optimized, action-driven.
2. Format it cleanly in **Markdown**.
3. Optimize for Applicant Tracking Systems (ATS).
4. End with an "**Some Suggestions To Make Your Resume Stronger**" section if relevant.

Resume:
{resume_text}

Job Description:
{jd_text}
"""

# Configure Gemini API on app startup
try:
    configure_gemini_api()
    function_schema = tailored_resume_function_schema()
    gemini_model = gemini_initialization_with_function_calling(function_schema)
    logger.info("Gemini model initialized.")
except ValueError as e:
    logger.error(f"Error during initialization: {e}")
    #  Set gemini_model to None so the app can still run (with reduced functionality)
    gemini_model = None
    #  No need to sys.exit here, handle in route


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

    return tailored_resume, additional_suggestions

# Since we're dealing with URLs - Routes - we need a route handler
@app.route("/")
def index():
    """Home page with form to upload resume and job description"""
    return render_template("index.html")

@app.route("/tailor-resume", methods=["GET", "POST"])
def tailor_resume():
    """Process the resume and job description to generate a tailored resume"""
    # handle the resume upload:
    if request.method == "POST":
        jd_text = request.form.get("job_description")
        resume_text = ""

        # keep the uploaded resume going
        if "resume_on_file" not in session:
            file = request.files.get("resume_file")
            if file and file.filename:
                resume_text = file.read().decode("utf-8")
                session["resume_text"] = resume_text
                session["resume_on_file"] = True
            else:
                flash("Hey, dipshit: we still need your resume.")
                return redirect(url_for("index"))
        else:
            resume_text = session.get("resume_text")

# Build out the prompts and make the Gemini call
    prompt = generate_tailoring_prompt(resume_text, jd_text)

    try:
        response = gemini_model.generate_content(
            contents = [{"role" : "user", "parts" : [{"text" : prompt}]}], 
            tools = [{"function_declarations" : [function_schema]}],
         generation_config = genai.types.GenerationConfig(temperature = 0.7)
    )

    except Exception as exception:
        flash(f"We found a Gemini API error: {exception}")
        return redirect(url_for("index"))

    # Get the response from the function call
    tailored_resume = ""
    additional_suggestions = ""

    if response.candidates:
        first_part = response.candidates[0].content.parts[0]
        if first_part.function_call and first_part.function_call.name == "tailor_resume":
            args = first_part.function_call.args
            tailored_resume = args.get("tailored_resume", "")
            additional_suggestion = args.get("additional_suggestions", "")
        elif first_part.text:
            tailored_resume = first_part.text
    
    return render_template("result.html", tailored_resume_html = tailored_resume,
                           tailored_resume_md = tailored_resume, additional_suggetions = additional_suggestions
                           )

@app.route("/clear-resume")
def clear_resume():
    session.pop("resume_text", None)
    session.pop("resume_on_file", None)
    flash("Resume is gone. Please upload a new one. Not sure why this happened (we're only kinda smart).")
    return redirect(url_for("index"))

@app.route("/download-resume", methods = ["POST"])
def download_resume():
    resume_md = request.form.get("tailored_resume_md")
    if not resume_md:
        flash("There's no resume data to download.")
        return redirect(url_for("index"))
    
    with tempfile.NamedTemporaryFile(delete = False, suffix = ".md") as temp:
        temp.write(resume_md.encode("utf-8"))
        temp_path = temp.name
    
    try:
        return send_file(temp_path, as_attachment = True,
                         download_name = "your_editable_markdown_resume.md", mimetype = "text/markdown"
                         )
    
    finally:
        os.unlink(temp_path)

# Finally: launch this sucker.
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host = "0.0.0.0", port = port, debug = True)

#     global gemini_model  #  Declare that you're using the global variable

#     if not gemini_model:
#         flash("API configuration error. Please check your environment variables and restart the application.", "error")
#         logger.error("Gemini model is not initialized.")
#         return redirect(url_for("index"))

#     # Get resume and job description from form
#     resume_text = request.form.get("resume_text")
#     jd_text = request.form.get("job_description")

#     if not resume_text or not jd_text:
#         flash("Please provide both resume and job description.", "error")
#         return redirect(url_for("index"))

#     try:
#         # Generate tailored resume
#         prompt = generate_tailoring_prompt(resume_text, jd_text)
#         logger.debug(f"Generated prompt: {prompt}")  # Log the prompt

#         response = get_gemini_response_with_function_calling(
#             gemini_model,
#             prompt,
#             tailored_resume_function_schema() # Pass the schema here
#         )
#         logger.debug(f"Gemini API response: {response}")  # Log the full response

#         tailored_resume, additional_suggestions = parse_gemini_response(response)

#         if not tailored_resume:
#             flash("Failed to generate tailored resume. Please try again.", "error")
#             logger.warning("Gemini failed to generate resume.")
#             return redirect(url_for("index"))

#         # Convert Markdown to HTML for display
#         tailored_resume_html = markdown(tailored_resume)
#         logger.info("Successfully generated tailored resume.")

#         return render_template(
#             "result.html",
#             tailored_resume_html=tailored_resume_html,
#             tailored_resume_md=tailored_resume,
#             additional_suggestions=additional_suggestions,
#         )

#     except Exception as e:
#         flash(f"An error occurred: {str(e)}", "error")
#         logger.exception(f"An error occurred: {e}")  # Log the full traceback
#         return redirect(url_for("index"))



# @app.route("/download-resume", methods=["POST"])
# def download_resume():
#     """Download the tailored resume as a markdown file"""
#     tailored_resume = request.form.get("tailored_resume_md")

#     if not tailored_resume:
#         flash("No resume data to download.", "warning")
#         return redirect(url_for("index"))

#     # Create a temporary file
#     try:
#         with tempfile.NamedTemporaryFile(delete=False, suffix=".md") as temp:
#             temp_path = temp.name
#             temp.write(tailored_resume.encode("utf-8"))
#         logger.info(f"Created temporary file: {temp_path}")

#         # Send the file to the user
#         return send_file(
#             temp_path,
#             as_attachment=True,
#             download_name="tailored_resume.md",
#             mimetype="text/markdown",
#         )
#     except Exception as e:
#         flash(f"Error downloading resume: {e}", "error")
#         logger.exception(f"Error downloading resume: {e}")
#         return redirect(url_for("index"))
#     finally:
#         # Clean up the temporary file after sending
#         if "temp_path" in locals():  # Check if temp_path was defined
#             os.unlink(temp_path)
#             logger.info(f"Deleted temporary file: {temp_path}")

# # # The following codeblock was for development purposes only (to get the address),
# # # and has been commented out for deployment in Render (below)
# # if __name__ == "__main__":
# #     # Check if running in IPython/Jupyter
# #     try:
# #         get_ipython
# #         # If we're in IPython/Jupyter, don't use the auto-reloader
# #         print("Flask app is ready. Access it at http://127.0.0.1:5000/")
# #         #  No app.run() here
# #     except NameError:
# #         # Normal Python environment
# #         app.run(debug=True)  #  <----  ONLY ONE app.run()
# #     #  No app.run() here


# # The following code block concerns the deployment of the app - we've chosen Render.
# # Per Render docs, we have to bind 0.0.0.0 on PORT - an evnironment variable Render assigns at runtime.
# if __name__ == "__main__":
#     # default the port locally to 5000
#     port = int(os.environ.get("PORT", 5000))
#     # bind all the network interfaces 
#     app.run(host = "0.0.0.0", port = port, debug = True)