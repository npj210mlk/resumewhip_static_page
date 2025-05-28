# working with our os and .env file
import os
from dotenv import load_dotenv

# since we're using Gemini
import google.generativeai as genai

# make printouts look nicer in Jupyter Notebooks - not needed here, but preserved for sake of clarity.
# from IPython.display import display, Markdown

from markdown import markdown

load_dotenv()

def configure_gemini_api():
    """
    This function does two things:
    1.) It configures the Gemini API using the 'GEMINI_API_KEY' environment variable; and
    2.) Let's you know if that environment variable was not loaded.
    """

    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY was not loaded from your environment.")
    genai.configure(api_key=GEMINI_API_KEY)

    # No 'return' statement is needed - all this does is perform an action, not any calculation

def tailored_resume_function_schema():
    """
    Dictates to Gemini how you want your resume tailored based on a job description.
    What returns is a dictionary that allows us to pass everything to the Gemini API in its expected format.
    """
    function_schema = {
        "name": "tailor_resume",
        "description": "Optimize my resume based on a job description.",
    
        # 'Here is how we want the info back'
        "parameters": {
            "type": "object",
            "properties": {
                "tailored_resume": {
                    "type": "string",
                    "description": "The Markdown-formatted resume.",
                },
                "additional_suggestions": {
                    "type": "string",
                    "description": "Ideas to make your resume stronger for this position.",
                },
            },
    
            # Make sure we get back SOMETHING
            "required": ["tailored_resume"],
        },
    }
    return function_schema

def gemini_initialization_with_function_calling(function_schema: dict):
    """
    By passing in the (expected) dictionary returned from 'function_schema,' you make the gemini-2.0-flash engine
    a single variable ("initialized") that can be used with all its parameters - all its rules. 
    
    Returns the initialized GenerativeModel with its function-calling "tools"
    """
    model = genai.GenerativeModel(
        model_name = "gemini-2.0-flash",

        # Pass the function_schema for the model to call
        tools = [{"function_declarations" : [function_schema]}]
    )
    return model

def generate_tailoring_prompt(resume_text: str, jd_string: str) -> str:
    """
    Generates the prompt telling Gemini to tailor a resume based on a given job description.

    Arguments are the 'resume_text' and 'jd_string' variables.

    What gets returned is the prompt from the 'res_optimizer_new_and_improved_gemini' notebook.
    """
    return f"""
    You are a professional resume optimization expert.
    Optimize the resume I have provided you to align with the given job description following the guidelines below:

    1. Make the resume one page, relevant, keyword optimized, action-driven  and in reverse chronological order.
    2. Format it cleanly in **Markdown**.
    3. Include any relevant project information that would help position me above / distinguish me from others.
    4. The primary goal of this optimization is to best position the resume against Application Tracking Systems.
    5. At the end, provide an "**Additional Suggestions**" section with suggestions improvements my resume where gaps exist.
    6. You MUST call the tailor_resume function below with your final answer. Do NOT return plain text. Use the schema provided.

    Resume:
    {resume_text}

    Job Description:
    {jd_string}
    """

# Rewriting 'get_gemini_response_with_function_calling' with same notes:
def get_gemini_response_with_function_calling(
    model: genai.GenerativeModel,
    prompt: str,
    function_schema: dict,
    temperature: float = 0.7
    # modified hint:
) -> genai.types.GenerateContentResponse:
    """
    This function sends our prompt to Gemini along with the function schema.
    It returns the response object from the gemini-2.0-flash engine - the 'genai.GenerateContentResponse' line
    """
    response = model.generate_content(
        contents=[{"role": "user", "parts": [{"text": prompt}]}],
        tools=[{"function_declarations": [function_schema]}],
        generation_config=genai.types.GenerationConfig(temperature=temperature),
    )
    return response

def handle_gemini_response(response: genai.types.GenerateContentResponse, output_file_path: str = "nj_gemini_pm_res.md"):
    """
    This function is designed to handle the Gemini API response. It checks for either blob text orfunction calls, 
    and writes the file 'nj_gemini_pm_res.md.'

    Explanation of arguments:
        response (genai.types.GenerateContentResponse) == the specified response object from the Gemini model.
        output_file_path (str, optional) == where the tailored resume is written (defaults to "nj_gemini_pm_res.md").
    """
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

                    if tailored_resume:
                        print("Tailored Resume:")
                        print(tailored_resume)

                        try:
                            with open(output_file_path, "w", encoding="utf-8") as output_file:
                                output_file.write(tailored_resume)
                            print(f"Saved Gemini-tailored resume to {output_file_path}")
                        except Exception as e:
                            print(f"There's been a problem: we couldn't save the Markdown file: {e}")

                    else:
                        print("Error: tailored_resume not found in function arguments.")

                    if additional_suggestions:
                        print("\nAdditional Suggestions:")
                        print(additional_suggestions)
                else:
                    print("Function call was made, but not for 'tailor_resume'.")
                    print("Function name:", function_call.name)

            elif first_part.text:
                print("Gemini's direct response:")
                print(first_part.text)
            else:
                print("No function call or text in the response.")
                print(response)
        else:
            print("Response contained no content or parts")
            print(response)
    else:
        print("No candidates in response")
        print(response)