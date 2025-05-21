# imports
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

    4. **Additional Suggestions*** *(if gaps exist)*:
    - If the resume does not fully align with the job description, suggest:
        a.) **Additional technical or soft skills** that I could add to make my profile stronger.
        b.) **Certifications or courses** I have (or could pursue) that would bridge the gap(s).
        c.) **Project ideas or experiences** that would better align with the role.

    5.) **Formatting**:
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
    3.) rerurns to us the generated resume response.

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
def export_resume(new_resume):
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
    output_pdf_file = f"gpt_resumes/{company_slugged}{unique_id}_tailored_resume.pdf"
    
    try:
        # Convert Markdown to HTML
        html_content = markdown(new_resume)
        # Convert HTML to PDF and save
        HTML(string=html_content).write_pdf(output_pdf_file)
        
        return f"✅ Successfully exported and saved your resume to {output_pdf_file}"
    except Exception as e:
        return f"❌ Failed to export resume: {str(e)}"