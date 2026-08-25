"""
AI Homework Grader

Analyzes a student's submitted homework and provides a suggested grade.

IMPORTANT:
- AI grade is only a recommendation.
- Teacher's final grade remains the official grade.
- This module does NOT modify the homework database.
"""

import base64
import os

from openai import OpenAI


# ============================================================
# OPENAI CLIENT
# ============================================================

def get_openai_client():
    """
    Create the OpenAI client using the OPENAI_API_KEY
    stored in Streamlit secrets or environment variables.
    """

    try:
        import streamlit as st

        api_key = st.secrets.get(
            "OPENAI_API_KEY",
            None
        )

    except Exception:
        api_key = None

    if not api_key:
        api_key = os.getenv(
            "OPENAI_API_KEY"
        )

    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY is not configured."
        )

    return OpenAI(
        api_key=api_key
    )


# ============================================================
# FILE → BASE64
# ============================================================

def file_to_base64(uploaded_file):
    """
    Convert a Streamlit UploadedFile into base64.
    """

    if uploaded_file is None:
        return None

    file_bytes = uploaded_file.getvalue()

    return base64.b64encode(
        file_bytes
    ).decode("utf-8")


# ============================================================
# MIME TYPE
# ============================================================

def get_mime_type(uploaded_file):
    """
    Return the MIME type for an uploaded homework file.
    """

    if uploaded_file is None:
        return None

    mime_type = getattr(
        uploaded_file,
        "type",
        None
    )

    if mime_type:
        return mime_type

    filename = (
        uploaded_file.name
        .lower()
    )

    if filename.endswith(".pdf"):
        return "application/pdf"

    if filename.endswith(".jpg"):
        return "image/jpeg"

    if filename.endswith(".jpeg"):
        return "image/jpeg"

    if filename.endswith(".png"):
        return "image/png"

    return None


# ============================================================
# AI HOMEWORK GRADING
# ============================================================

def grade_homework_with_ai(
    uploaded_file,
    homework_title="Homework Assignment",
    curriculum_topic="",
    instructions="",
):
    """
    Analyze a student's homework submission.

    Returns a dictionary containing:

        suggested_grade
        suggested_percentage
        confidence
        strengths
        mistakes
        feedback
        reasoning

    The result is a recommendation only.
    """

    if uploaded_file is None:
        return {
            "success": False,
            "error": "No homework file was provided."
        }

    mime_type = get_mime_type(
        uploaded_file
    )

    if mime_type not in [
        "application/pdf",
        "image/jpeg",
        "image/png"
    ]:
        return {
            "success": False,
            "error": (
                "Unsupported file type. "
                "Please upload a PDF, JPG, JPEG, or PNG."
            )
        }

    try:

        client = get_openai_client()

        file_base64 = file_to_base64(
            uploaded_file
        )

        # ----------------------------------------------------
        # AI GRADING INSTRUCTIONS
        # ----------------------------------------------------

        system_prompt = """
You are an expert mathematics teacher helping another
mathematics teacher review student homework.

Your job is to analyze the student's submitted work and
provide a PRELIMINARY grading recommendation.

IMPORTANT RULES:

1. Do NOT assume an answer key exists.

2. If there is no answer key, independently solve the
   mathematical problems when possible.

3. Evaluate the student's actual mathematical reasoning,
   not just the final answer.

4. Identify:
   - correct answers
   - incorrect answers
   - partially correct work
   - computational errors
   - conceptual errors
   - missing work
   - unclear work

5. Give a suggested letter grade using:

   A+ = 98
   A  = 95
   A- = 92
   B+ = 88
   B  = 85
   B- = 82
   C+ = 78
   C  = 75
   C- = 72
   D  = 65
   F  = 50

6. The suggested grade must be based on the quality and
   correctness of the student's work.

7. Do NOT invent answers or claim certainty when the image
   is unclear.

8. If part of the submission cannot be read, explicitly say so.

9. The teacher will make the final grading decision.
   Your grade is ONLY a recommendation.

10. Provide useful teacher-facing feedback that allows the
    teacher to quickly verify your recommendation.

Return your response as JSON with exactly these fields:

{
    "suggested_grade": "A-",
    "suggested_percentage": 92,
    "confidence": "High",
    "strengths": [
        "..."
    ],
    "mistakes": [
        "..."
    ],
    "feedback": "...",
    "reasoning": "..."
}
"""

        # ----------------------------------------------------
        # HOMEWORK CONTEXT
        # ----------------------------------------------------

        context = f"""
Homework Title:
{homework_title}

Curriculum Topic:
{curriculum_topic}

Assignment Instructions:
{instructions}

Analyze the attached student submission.
"""

        # ----------------------------------------------------
        # IMAGE / PDF CONTENT
        # ----------------------------------------------------

        if mime_type == "application/pdf":

            data_url = (
                "data:application/pdf;base64,"
                + file_base64
            )

        else:

            data_url = (
                f"data:{mime_type};base64,"
                f"{file_base64}"
            )

        # ----------------------------------------------------
        # AI REQUEST
        # ----------------------------------------------------

        response = client.responses.create(
            model="gpt-5.6",
            instructions=system_prompt,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                context
                            )
                        },
                        {
                            "type": "input_file",
                            "filename": uploaded_file.name,
                            "file_data": data_url
                        }
                    ]
                }
            ]
        )

        # ----------------------------------------------------
        # RESPONSE TEXT
        # ----------------------------------------------------

        result_text = (
            response.output_text
            .strip()
        )

        # ----------------------------------------------------
        # PARSE JSON
        # ----------------------------------------------------

        import json

        try:

            result = json.loads(
                result_text
            )

        except json.JSONDecodeError:

            # Try to recover JSON if the model returned
            # markdown code fences.

            cleaned = (
                result_text
                .replace(
                    "```json",
                    ""
                )
                .replace(
                    "```",
                    ""
                )
                .strip()
            )

            try:

                result = json.loads(
                    cleaned
                )

            except json.JSONDecodeError:

                return {
                    "success": False,
                    "error": (
                        "AI returned an unexpected "
                        "response format."
                    ),
                    "raw_response": result_text
                }

        # ----------------------------------------------------
        # NORMALIZE RESULT
        # ----------------------------------------------------

        result.setdefault(
            "suggested_grade",
            ""
        )

        result.setdefault(
            "suggested_percentage",
            0
        )

        result.setdefault(
            "confidence",
            "Unknown"
        )

        result.setdefault(
            "strengths",
            []
        )

        result.setdefault(
            "mistakes",
            []
        )

        result.setdefault(
            "feedback",
            ""
        )

        result.setdefault(
            "reasoning",
            ""
        )

        result["success"] = True

        return result

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }
