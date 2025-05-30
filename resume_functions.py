
# imports for both Resume and Cover Letter Optimizers
import os
import uuid
import re
from dotenv import load_dotenv
from openai import OpenAI
from markdown import markdown
from weasyprint import HTML

# load dotenv
load_dotenv()

# assign "my_sk" as global variable
my_sk = os.getenv("MY_SK")

# ===== Resume Functions =====

# create the gpt_resumes folder
os.makedirs("gpt_resumes", exist_ok = True)

# prompt creator function - the lambda function from scratchpad

# basically, Steps 1, 2, and 3 from scratchpad
def prompt_creator(resume_string: str, job_desc_string: str) -> str:
    """
    Using the prompt engineered in the scratchpad 'lambda' function, this function uses the power of ChatGPT's 4o-mini engine to
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
    return f"""
    ### Role: 
    You are a professional resume optimization expert, tailoring my resume to fit specific job descriptions. 
    You know my job preferences include collaborating with people, and helping businesses get the most out of their data.
    Your goal is to optimize my resume and provide actionable suggestions for improvement to align with the target role.

    ### Guidelines:
    1. **Relevance**:
    - Prioritize the particular skills and experiences I have with what is **most relevant to the job position**.
    - De-emphasize or even completely remove irrelevant details to ensure a **concise** and **targeted** resume.
    - Limit work experience section to 2-3 most relevant roles
    - Limit bullet points under each role to 2-3 most relevant impacts

    2. **Action-Driven Results**:
    - Choose **strong action verbs** and **quantifiable results** (eg: percentages, revenues, efficiency improvement, etc.)

    3. **Keyword Optimization**:
    - Integrate **keywords** and phrases from the job description naturally to optimize for Applicant Tracking Systems (ATS)

    4. **Project Inclusion**:
    - Incorporate any of the relevant projects listed on the resume that would enhance its position within Applican Tracking Systems (ATS)
    
    5. **Additional Suggestions*** *(if gaps exist)*:
    - If the resume does not fully align with the job description, suggest:
        a.) **Additional technical or soft skills** that I could add to make my profile stronger.
        b.) **Certifications or courses** I have (or could pursue) that would bridge the gap(s).
        c.) **Project ideas or experiences** that would better align with the role.

    6.) **Formatting**:
    - Ouptut the tailored resume in **clean Markdown format**.
    - Include an **"Additional Suggestions"** section at the end with actionable improvement recommendations.

    ---

    ## Input:
    - **My resume**:
    {resume_string}

    - **The Job Description**:
    {job_desc_string}

    ---

    ### Output:
    1. **Tailored Resume**:
    - A resume in **Markdown format** that emphasizes relevant experience, skills, and achievements.
    - Incorporates job description **keywords** to optimize for ATS.
    - Uses confident language and is no longer than **one page**.

    2. **Additional Suggestions** *(if applicable)*:
    - List **skills** that could strengthen alignment with the role.
    - Recommend **certifications or courses** to pursue.
    - Suggest **specific projects or experiences** to develop.
    """

# Step 4 from scratchpad
def get_resume_response(prompt: str, api_key: str, model: str = "gpt-4o-mini", temperature: float = 0.7) -> str:
    """
    Now that we've got the resume optimized, we send it to OpenAI's API, where it sends us back the optimized
    resume response. 

    With this function, we:
    1.) set up our OpenAI client;
    2.) make an API call to OpenAI using the provided prompt; and 
    3.) returns to us the generated resume response.

    Args:
        prompt (str): The formatted prompt containing the resume and job description
        api_key (str): our OpenAI API key for call authentication
        model ("gpt-4o-mini): The OpenAI engine to use. Here, we're hard-coding it to "gpt-4o-mini"
        temperature (float, optional): Controls randomness in the response. Hard-set to 0.7, a popular temperature setting.

    Returns:
        str: The AI-generated optimized resume, along with the suggestions we need to make it stronger

    Raises:
        OpenAIError: If there's an issue with the API call
    """
    # set up api client
    open_apikey = os.environ.get("openapi_apikey")
    
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
def process_resume(resume, job_desc_string):
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
    # read resume
    with open(resume, "r", encoding="utf-8") as file:
        resume_string = file.read()

    # create prompt
    prompt = prompt_creator(resume_string, job_desc_string)

    # generate response with the my_sk we globally set with load_dotenv() earlier
    response_string = get_resume_response(prompt, my_sk)
    response_list = response_string.split("## Additional Suggestions")
    
    # extract new resume and suggestions for improvement
    new_resume = response_list[0]
    suggestions = "## Additional Suggestions \n\n" +response_list[1]

    # the three resumes: the optimized resume, a version of that we can edit, and suggestions for improving it
    return new_resume, new_resume, suggestions

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