"""
generator.py — Generates a cover letter and email body using DeepSeek,
               then saves the cover letter as a PDF.
"""

import os
from openai import OpenAI
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL    = "deepseek-chat"


def _get_client():
    """Return a DeepSeek client (OpenAI-compatible), reading the key at call time."""
    return OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url=DEEPSEEK_BASE_URL,
    )


# ─── AI generation ────────────────────────────────────────────────────────────

def generate_cover_letter(cv_text: str, company: str, role: str, extras: str = "") -> str:
    """Return a professional cover letter as plain text."""
    prompt = f"""
You are an expert career coach. Write a professional, personalised cover letter for the job application below.

---
CV / Resume:
{cv_text}

---
Target Company: {company}
Target Role   : {role}
Additional Info: {extras if extras else "None"}

---
Instructions:
- Use EXACTLY this structure (no deviations):

  [Full Name]
  [Phone] | [Email] | [LinkedIn / Location from CV]
  [Today's date]

  Hiring Manager
  [Company Name]

  Dear Hiring Manager,

  [Opening paragraph — enthusiasm for the role and company]

  [Second paragraph — 2–3 key achievements from the CV that match the role]

  [Third paragraph — what you will bring to the team]

  [Closing paragraph — request an interview, thank the reader]

  Best regards,
  [Full Name]
  [Phone] | [Email]

- Use information from the CV — do NOT use placeholder brackets.
- Formal, professional tone.
- Output the letter only, no extra commentary.
"""
    response = _get_client().chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def generate_email(cv_text: str, company: str, role: str, cover_letter: str) -> dict:
    """Return a dict with 'subject' and 'body' keys for the application email."""
    prompt = f"""
Write a short, professional job application email to accompany a cover letter PDF attachment.

CV Summary (for context):
{cv_text[:1500]}

Company : {company}
Role    : {role}

The cover letter is attached as a PDF. The email body should:
- Be 3–5 sentences.
- Mention the attached cover letter.
- Express genuine interest.
- End with a professional sign-off using the applicant's name from the CV.

Return ONLY in this exact format (no extra text):
SUBJECT: <subject line>
BODY:
<email body>
"""
    response = _get_client().chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    raw = response.choices[0].message.content.strip()

    # Parse subject and body
    subject = ""
    body = ""
    if "SUBJECT:" in raw and "BODY:" in raw:
        parts = raw.split("BODY:", 1)
        subject = parts[0].replace("SUBJECT:", "").strip()
        body = parts[1].strip()
    else:
        subject = f"Application for {role} at {company}"
        body = raw

    return {"subject": subject, "body": body + "\n"}


def regenerate_cover_letter(cv_text: str, company: str, role: str, extras: str = "", feedback: str = "") -> str:
    """Regenerate cover letter with optional user feedback/suggestions."""
    feedback_section = ""
    if feedback and feedback.strip():
        feedback_section = f"\nUser feedback to incorporate:\n{feedback}\n"

    prompt = f"""
You are an expert career coach. Regenerate a professional, personalised cover letter for the job application below.
{feedback_section}
---
CV / Resume:
{cv_text}

---
Target Company: {company}
Target Role   : {role}
Additional Info: {extras if extras else "None"}

---
Instructions:
- Use EXACTLY this structure (no deviations):

  [Full Name]
  [Phone] | [Email] | [LinkedIn / Location from CV]
  [Today's date]

  Hiring Manager
  [Company Name]

  Dear Hiring Manager,

  [Opening paragraph — enthusiasm for the role and company]

  [Second paragraph — 2–3 key achievements from the CV that match the role]

  [Third paragraph — what you will bring to the team]

  [Closing paragraph — request an interview, thank the reader]

  Best regards,
  [Full Name]
  [Phone] | [Email]

- Use information from the CV — do NOT use placeholder brackets.
- Formal, professional tone.
- Output the letter only, no extra commentary.
"""
    response = _get_client().chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def regenerate_email(cv_text: str, company: str, role: str, cover_letter: str, feedback: str = "") -> dict:
    """Regenerate email with optional user feedback/suggestions."""
    feedback_section = ""
    if feedback and feedback.strip():
        feedback_section = f"\nUser feedback to incorporate:\n{feedback}\n"

    prompt = f"""
Regenerating a job application email based on user feedback.
{feedback_section}
Write a short, professional job application email to accompany a cover letter PDF attachment.

CV Summary (for context):
{cv_text[:1500]}

Company : {company}
Role    : {role}

The cover letter is attached as a PDF. The email body should:
- Be 3–5 sentences.
- Mention the attached cover letter.
- Express genuine interest.
- End with a professional sign-off using the applicant's name from the CV.

Return ONLY in this exact format (no extra text):
SUBJECT: <subject line>
BODY:
<email body>
"""
    response = _get_client().chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    raw = response.choices[0].message.content.strip()

    subject = ""
    body = ""
    if "SUBJECT:" in raw and "BODY:" in raw:
        parts = raw.split("BODY:", 1)
        subject = parts[0].replace("SUBJECT:", "").strip()
        body = parts[1].strip()
    else:
        subject = f"Application for {role} at {company}"
        body = raw

    return {"subject": subject, "body": body + "\n"}


# ─── PDF export ───────────────────────────────────────────────────────────────

def save_cover_letter_pdf(cover_letter_text: str, output_path: str) -> str:
    """Save the cover letter text as a formatted PDF. Returns the output path."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
    )

    styles = getSampleStyleSheet()
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=11,
        leading=16,
        spaceAfter=12,
    )

    story = []
    for paragraph in cover_letter_text.split("\n\n"):
        paragraph = paragraph.strip()
        if paragraph:
            story.append(Paragraph(paragraph.replace("\n", "<br/>"), body_style))
            story.append(Spacer(1, 0.3 * cm))

    doc.build(story)
    return output_path
