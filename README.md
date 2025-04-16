# Resume Optimizer: LLM-Powered Resume Tailoring with Python + ChatGPT

This project takes your resume and a job description, uses few-shot prompting with ChatGPT-4o-mini to tailor your resume to the job, and saves the result as a clean, professional PDF — along with suggestions to make it more Applicant Tracking System (ATS) friendly.

Built in Jupyter Notebook for transparency and ease of use.

---

## What It Does

- Converts a resume from Markdown to HTML
- Compares resume content to a job description
- Uses the OpenAI API to:
  - Suggest optimizations
  - Rewrite your resume for stronger alignment
  - Highlight improvements for ATS readability
- Saves the optimized resume as a styled PDF

---

## Tech Stack

| Tool          | Purpose                          |
|---------------|----------------------------------|
| Python        | Core logic and processing        |
| Jupyter       | Notebook-based development       |
| `markdown`    | Converts Markdown to HTML        |
| `WeasyPrint`  | Converts HTML to PDF             |
| `dotenv`      | Secure API key management        |
| OpenAI API    | Powers ChatGPT-4o-mini prompts   |

---

## Example Workflow

1. Start with a resume in Markdown format (`resume.md`)
2. Paste in a job description
3. Run the prompt-based comparison and rewrite
4. Save the result as a PDF
5. Review suggestions for ATS improvement

---

## Getting Started

Step 1: Clone the repo and install dependencies (using bash):

git clone https://github.com/npj210mlk/resume-optimizer.git
cd resume-optimizer

pip install -r requirements.txt

Step 2: Create a .env file with your OpenAI API Key:

OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxx

Step 3: Launch the Notebook

jupyter notebook

---

## Project Structure

resume-optimizer/
├── data/                  # Input resumes and job descriptions
├── output/                # Final optimized PDFs
├── styles/                # CSS for PDF styling
├── resume_optimizer.ipynb # The main notebook
├── requirements.txt
└── README.md

---

## Acknowledgements!!!

This project was inspired by [Shaw Talebi's Resume Optimizer](https://github.com/ShawhinT/AI-Builders-Bootcamp-2). His content, approach, and fluid teaching style were beyond instrumental in this project's success.

---

## About the Author

I'm Nick Joseph, a freelance Data & Prompt Engineer focused on building tools that connect human communication with AI's LLMs in meaningful ways.

This project is both a technical exercise and a personal career tool - and it's open for collaboration!

