from flask import Flask, render_template, request, flash, redirect, url_for, send_file
import os
from dotenv import load_dotenv
import google.generativeai as genai
from markdown import markdown
import tempfile
import logging  # Import the logging module
from gemini_flask_functions import *

# import the functions from 'gemini_flask_functions' python file:
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


# start Flask
app = Flask(__name__)
app.secret_key = "super secret key"  #  Important for flash messages!

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Load environment variables
load_dotenv()

# call the api
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY was not loaded from your environment.")
    #  Don't raise an exception here.  Handle it more gracefully in the routes.
    # raise ValueError("GEMINI_API_KEY was not loaded from your environment.")
else:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("Gemini API Key loaded.")


# Global variable for the Gemini model
gemini_model = None

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


@app.route('/', methods=['GET'])
def index():
    """Home page with form to upload resume and job description"""
    return render_template('index.html')



@app.route('/tailor-resume', methods=['POST'])
def tailor_resume():
    """Process the resume and job description to generate a tailored resume"""
    global gemini_model  #  Declare that you're using the global variable

    if not gemini_model:
        flash("API configuration error. Please check your environment variables and restart the application.", "error")
        logger.error("Gemini model is not initialized.")
        return redirect(url_for('index'))

    # Get resume and job description from form
    resume_text = request.form.get('resume_text')
    jd_text = request.form.get('job_description')

    if not resume_text or not jd_text:
        flash("Please provide both resume and job description.", "error")
        return redirect(url_for('index'))

    try:
        # Generate tailored resume
        prompt = generate_tailoring_prompt(resume_text, jd_text)
        logger.debug(f"Generated prompt: {prompt}")  # Log the prompt

        response = get_gemini_response_with_function_calling(
            gemini_model,
            prompt,
            tailored_resume_function_schema() # Pass the schema here
        )
        logger.debug(f"Gemini API response: {response}")  # Log the full response

        tailored_resume, additional_suggestions = parse_gemini_response(response)

        if not tailored_resume:
            flash("Failed to generate tailored resume. Please try again.", "error")
            logger.warning("Gemini failed to generate resume.")
            return redirect(url_for('index'))

        # Convert Markdown to HTML for display
        tailored_resume_html = markdown(tailored_resume)
        logger.info("Successfully generated tailored resume.")

        return render_template(
            'result.html',
            tailored_resume_html=tailored_resume_html,
            tailored_resume_md=tailored_resume,
            additional_suggestions=additional_suggestions,
        )

    except Exception as e:
        flash(f"An error occurred: {str(e)}", "error")
        logger.exception(f"An error occurred: {e}")  # Log the full traceback
        return redirect(url_for('index'))



@app.route('/download-resume', methods=['POST'])
def download_resume():
    """Download the tailored resume as a markdown file"""
    tailored_resume = request.form.get('tailored_resume_md')

    if not tailored_resume:
        flash("No resume data to download.", "warning")
        return redirect(url_for('index'))

    # Create a temporary file
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.md') as temp:
            temp_path = temp.name
            temp.write(tailored_resume.encode('utf-8'))
        logger.info(f"Created temporary file: {temp_path}")

        # Send the file to the user
        return send_file(
            temp_path,
            as_attachment=True,
            download_name="tailored_resume.md",
            mimetype="text/markdown",
        )
    except Exception as e:
        flash(f"Error downloading resume: {e}", "error")
        logger.exception(f"Error downloading resume: {e}")
        return redirect(url_for('index'))
    finally:
        # Clean up the temporary file after sending
        if 'temp_path' in locals():  # Check if temp_path was defined
            os.unlink(temp_path)
            logger.info(f"Deleted temporary file: {temp_path}")



if __name__ == '__main__':
    # Check if running in IPython/Jupyter
    try:
        get_ipython
        # If we're in IPython/Jupyter, don't use the auto-reloader
        print("Flask app is ready. Access it at http://127.0.0.1:5000/")
        #  No app.run() here
    except NameError:
        # Normal Python environment
        app.run(debug=True)  #  <----  ONLY ONE app.run()
    #  No app.run() here