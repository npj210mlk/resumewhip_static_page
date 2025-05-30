import os # use personal openai key
import uuid # for unique file usernames
import re # for future 'generate' button
from dotenv import load_dotenv # loads environmental variables

# for working with OpenAI:
from openai import OpenAI

# HTML to Markdown for editing
from markdown import markdown
from IPython.display import display, Markdown # <-- make it look nice in the notebook

# for design
from weasyprint import HTML # see previous notebook for weasyprint notes

# env file load check
load_dotenv()

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
    return f"""
    ### Role: 
    You are a professional cover letter writer, and your goal is to create a unique cover letter that showcases 
    how the job experience in my resume can exceed the needs listed in a specific job description.
    Your goal is to dazzle recruiters with a conversational yet professional tone that sets my candidacy apart from others
    applying for that same role.

    ### Guidelines:
    1. **Relevance**:
    - Prioritize the particular skills and experiences I have with what is **most relevant to the job position**.
    - De-emphasize or even completely remove irrelevant details to ensure a **concise** but **descriptive** cover letter.
    - Limit integrating actual work experience and job needs paragraphs to my 2-3 most relevant roles
    - Select only the core competencies and listed projects most relevant to the job description

    2. **Action-Driven Results**:
    - Choose **strong action verbs** and **quantifiable results** (eg: percentages, revenues, efficiency improvement, etc.)

    3. **Keyword Optimization**:
    - Integrate **keywords** and phrases from the job description naturally to optimize for Applicant Tracking Systems (ATS)

    4. **Tone**:
    - Please keep the **tone** of the cover letter **professional** **without sounding like a robot**. 
    - The **objective** is to **exhibit competance** in the duties listed, but also to sound like I'm talking to a cohort.

    5. **Formatting**:
    - Ouptut the tailored cover letter in a **clean Markdown format** for ease of editing.

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

def get_cover_response(prompt: str, api_key: str, model: str = "gpt-4o-mini", temperature: float = 0.7) -> str:
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
    open_apikey = os.environ.get("openapi_apikey")
    
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