# 🥊 Resume Optimizing: An AI Cage Match
> (🔒 Safety Note: This notebook does not access your personal files or send data anywhere. All processing is done locally or in a secure temporary cloud environment (Colab/Binder). All code is listed in this repo.


Welcome to a head-to-head showdown between two powerful language models: OpenAI's `gpt-4o-mini` and Google's `gemini-2.0-flash`. This project explores how each engine handles the exact same resume-optimization prompt — and what that says about their training, output quality, and user-friendliness.

---

## 🚀 Why I Built This

I wanted to answer a simple question:

> *If I give both engines the same detailed prompt, will they return the same quality response?*

Turns out — **not even close**.

This project started as a curiosity about large language models (LLMs), but it quickly turned into a deeper reflection on usability, structure, and real-world value for **job seekers trying to optimize their resumes**.

---

## 🧠 What I Learned

- **OpenAI's `gpt-4o-mini`** is incredibly strong right out of the box. With a well-written prompt, it delivers polished, keyword-rich resumes without much coaching.
- **Google's `gemini-2.0-flash`** is also powerful — but more "literal." It benefits from more structured instructions and formatting hints to guide the output.
- **For the average person**, ChatGPT is the easier tool to use. Most folks don't know they *need* to structure prompts to get useful AI results — and that's where ChatGPT shines.

---

## 📷 Preview

Here’s a sample screenshot from the Gemini notebook:

![Notebook Screenshot](jupyter_notebook_screenshot.png)

---

## 🧰 Project Structure

- `notebooks/openai_optimizer.ipynb` → Built with Gradio UI for OpenAI-based optimization
- `notebooks/gemini_optimizer.ipynb` → Built with Flask UI for Gemini-based optimization
- `assets/` → Includes example prompts and screenshots
- `.env` → You’ll store your API keys here (not included for security)

---

## 📦 Dependencies

You'll need:

- Python 3.x  
- Jupyter Notebook or VS Code
- `openai`  
- `google.generativeai`  
- `dotenv`  
- `markdown`  
- `weasyprint`  
- `gradio` (for OpenAI UI)  
- `flask` (for Gemini UI)

```bash
pip install openai google-generativeai python-dotenv markdown weasyprint gradio flask
