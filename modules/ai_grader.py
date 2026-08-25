"""
AI Homework Grader

Uses Google Gemini to analyze student homework.

IMPORTANT:
- AI grade is only a recommendation.
- Teacher's final grade remains the official grade.
- This module does NOT modify the homework database.
"""

import json
import os

from google import genai
from google.genai import types


# ============================================================
# GEMINI CLIENT
# ============================================================

def get_gemini_client():
    """
    Create a Gemini client using GEMINI_API_KEY.

    Streamlit Cloud:
        Add GEMINI_API_KEY to Streamlit Secrets.

    Local development:
        Set GEMINI_API_KEY as an environment variable.
    """

    api_key = None

    # --------------------------------------------------------
    # Try Streamlit Secrets first
    # --------------------------------------------------------

    try:

        import streamlit as st

        api_key = st.secrets.get(
            "GEMINI_API_KEY",
            None
        )

    except Exception:
        pass

    # --------------------------------------------------------
    # Fall back to environment variable
    # --------------------------------------------------------

    if not api_key:

        api_key = os.getenv(
            "GEMINI_API_KEY"
        )

    # --------------------------------------------------------
    # No API key
    # --------------------------------------------------------

    if not api_key:

        raise ValueError(
            "GEMINI_API_KEY is not configured. "
            "Please add it to Streamlit Secrets."
        )

    return genai.Client(
        api_key=api_key
    )


# ============================================================
# AI HOMEWORK GRADER
# ============================================================

def grade_homework_with_ai(
    submission_bytes,
    submission_filename,
    homework_title="Homework Assignment",
    curriculum_topic="",
    instructions="",
):
    """
    Analyze a student's submitted homework PDF.

    Parameters
    ----------
    submission_bytes:
        The actual bytes of the student's PDF.

    submission_filename:
        Original filename / display name.

    homework_title:
        Homework title from the homework table.

    curriculum_topic:
        Curriculum topic from the homework table.

    instructions:
        Teacher's assignment instructions/comments.

    Returns
    -------
    dict

        {
            "success": True,
            "suggested_grade": "B+",
            "suggested_percentage": 88,
            "confidence": "High",
            "strengths": [...],
            "mistakes": [...],
            "feedback": "...",
            "reasoning": "..."
        }

    IMPORTANT:
    This function NEVER saves anything to the database.
    """

    # ========================================================
    # VALIDATE FILE
    # ========================================================

    if not submission_bytes:

        return {
            "success": False,
            "error": (
                "No student submission was provided."
            )
        }

    # ========================================================
    # VALIDATE FILE TYPE
    # ========================================================

    filename = (
        str(submission_filename or "")
        .lower()
        .strip()
    )

    if not filename.endswith(".pdf"):

        return {
            "success": False,
            "error": (
                "The AI grader currently expects "
                "the student's merged PDF submission."
            )
        }

    # ========================================================
    # GET GEMINI CLIENT
    # ========================================================

    try:

        client = get_gemini_client()

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }

    # ========================================================
    # GRADING INSTRUCTIONS
    # ========================================================

    grading_prompt = f"""
You are an expert mathematics teacher assisting another
professional mathematics teacher.

You are reviewing a student's submitted homework.

Your job is to provide a PRELIMINARY grading recommendation.

The teacher will review your recommendation before entering
the official grade.

============================================================
HOMEWORK INFORMATION
============================================================

Homework Title:
{homework_title}

Curriculum Topic:
{curriculum_topic}

Teacher Instructions / Comments:
{instructions}

============================================================
GRADING RULES
============================================================

Evaluate the student's actual mathematical work.

Do NOT simply look at final answers.

Evaluate:

1. Mathematical correctness
2. Mathematical reasoning
3. Intermediate calculations
4. Algebraic manipulation
5. Appropriate formulas and methods
6. Accuracy of arithmetic
7. Final answers
8. Completeness of the work
9. Whether partial credit appears appropriate
10. Whether the student's work demonstrates understanding

If an answer appears incorrect:

- Determine the correct mathematical solution yourself.
- Identify where the student's reasoning went wrong.
- Explain the error clearly.

If work is partially correct:

- Recognize the correct reasoning.
- Identify the point where the solution becomes incorrect.
- Consider appropriate partial credit.

If handwriting or part of the submission is unclear:

- Do NOT invent what the student wrote.
- Explicitly identify the unclear portion.
- Reduce confidence accordingly.

There may NOT be an answer key.

When an answer key is not available, independently solve the
mathematical problems when necessary.

============================================================
GRADE SCALE
============================================================

Use this grading scale:

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

The suggested percentage should correspond reasonably to the
suggested letter grade.

============================================================
IMPORTANT
============================================================

The AI grade is ONLY a recommendation.

Do NOT state that the grade is final.

The teacher will make the final grading decision.

============================================================
OUTPUT
============================================================

Return ONLY valid JSON.

Do not use Markdown.

Use exactly this structure:

{{
    "suggested_grade": "B+",
    "suggested_percentage": 88,
    "confidence": "High",
    "strengths": [
        "The student correctly ..."
    ],
    "mistakes": [
        "Problem 4 contains ..."
    ],
    "feedback": "Good understanding of ...",
    "reasoning": "The student demonstrates ..."
}}

============================================================
"""

    # ========================================================
    # SEND PDF TO GEMINI
    # ========================================================

    try:

        response = client.models.generate_content(

            model="gemini-3.7-flash",

            contents=[
                types.Part.from_bytes(
                    data=submission_bytes,
                    mime_type="application/pdf"
                ),

                grading_prompt
            ],

            config=types.GenerateContentConfig(

                temperature=0.1,

                response_mime_type="application/json"
            )
        )

    except Exception as e:

        return {
            "success": False,
            "error": (
                "Gemini was unable to analyze the "
                f"student submission: {e}"
            )
        }

    # ========================================================
    # GET RESPONSE TEXT
    # ========================================================

    try:

        result_text = (
            response.text
            .strip()
        )

    except Exception:

        return {
            "success": False,
            "error": (
                "Gemini returned an empty response."
            )
        }

    if not result_text:

        return {
            "success": False,
            "error": (
                "Gemini returned an empty response."
            )
        }

    # ========================================================
    # PARSE JSON
    # ========================================================

    try:

        result = json.loads(
            result_text
        )

    except json.JSONDecodeError:

        return {
            "success": False,
            "error": (
                "Gemini returned an unexpected "
                "response format."
            ),
            "raw_response": result_text
        }

    # ========================================================
    # NORMALIZE RESULT
    # ========================================================

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

    # ========================================================
    # ENSURE LIST VALUES
    # ========================================================

    if not isinstance(
        result["strengths"],
        list
    ):

        result["strengths"] = [
            str(result["strengths"])
        ]

    if not isinstance(
        result["mistakes"],
        list
    ):

        result["mistakes"] = [
            str(result["mistakes"])
        ]

    # ========================================================
    # FINAL RESULT
    # ========================================================

    result["success"] = True

    return result
