"""
AI Homework Grader

Analyzes a student's submitted homework directly from
Supabase Storage and returns a teacher-facing grading
recommendation.

IMPORTANT:
- AI grade is ONLY a recommendation.
- Teacher's final grade remains the official grade.
- This module does NOT modify the homework database.
"""

import base64
import json
import os

import streamlit as st
from openai import OpenAI

from supabase_client import get_supabase


# ============================================================
# CONFIGURATION
# ============================================================

BUCKET_NAME = "homework-files"

# Cost-sensitive GPT-5.6 model
AI_MODEL = "gpt-5.6-luna"


# ============================================================
# OPENAI CLIENT
# ============================================================

def get_openai_client():
    """
    Create the OpenAI client using OPENAI_API_KEY
    from Streamlit secrets or environment variables.
    """

    api_key = None

    # --------------------------------------------------------
    # Streamlit Cloud Secrets
    # --------------------------------------------------------

    try:

        api_key = st.secrets.get(
            "OPENAI_API_KEY",
            None
        )

    except Exception:
        pass

    # --------------------------------------------------------
    # Environment Variable
    # --------------------------------------------------------

    if not api_key:

        api_key = os.getenv(
            "OPENAI_API_KEY"
        )

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    if not api_key:

        raise ValueError(
            "OPENAI_API_KEY is not configured. "
            "Please add OPENAI_API_KEY to Streamlit Secrets."
        )

    return OpenAI(
        api_key=api_key
    )


# ============================================================
# SUPABASE: DOWNLOAD FILE
# ============================================================

def download_student_submission(storage_path):
    """
    Download the student's submitted homework directly
    from Supabase Storage.

    Parameters
    ----------
    storage_path : str
        Example:
        submissions/student_12/homework_45_abc123.pdf

    Returns
    -------
    bytes
        PDF file bytes
    """

    if not storage_path:

        raise ValueError(
            "No student submission path was provided."
        )

    path = str(
        storage_path
    ).strip()

    if not path:

        raise ValueError(
            "Student submission path is empty."
        )

    try:

        supabase = get_supabase()

        response = (
            supabase
            .storage
            .from_(BUCKET_NAME)
            .download(path)
        )

        # Supabase normally returns raw bytes.
        if isinstance(response, bytes):

            return response

        # Some client versions may return an object
        # containing the data.
        if hasattr(response, "data"):

            data = response.data

            if isinstance(data, bytes):

                return data

        raise ValueError(
            "Supabase returned an unexpected "
            "file format."
        )

    except Exception as e:

        raise RuntimeError(
            "Unable to download the student's "
            f"submission from Supabase Storage: {e}"
        )


# ============================================================
# BASE64 ENCODING
# ============================================================

def bytes_to_base64(file_bytes):
    """
    Convert file bytes to base64.
    """

    return base64.b64encode(
        file_bytes
    ).decode("utf-8")


# ============================================================
# AI GRADING
# ============================================================

def grade_homework_with_ai(
    student_file,
    homework_title="Homework Assignment",
    curriculum_topic="",
    instructions="",
):
    """
    Analyze a student's submitted homework.

    Parameters
    ----------
    student_file : str
        Supabase Storage path to the student's PDF.

    homework_title : str
        Homework title.

    curriculum_topic : str
        Curriculum topic.

    instructions : str
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
    """

    # ========================================================
    # VALIDATE FILE
    # ========================================================

    if not student_file:

        return {
            "success": False,
            "error": (
                "No student submission is available."
            )
        }

    try:

        # ====================================================
        # DOWNLOAD STUDENT PDF
        # ====================================================

        file_bytes = (
            download_student_submission(
                student_file
            )
        )

        if not file_bytes:

            return {
                "success": False,
                "error": (
                    "The student submission is empty."
                )
            }

        # ====================================================
        # CONVERT TO BASE64
        # ====================================================

        file_base64 = (
            bytes_to_base64(
                file_bytes
            )
        )

        # ====================================================
        # OPENAI CLIENT
        # ====================================================

        client = get_openai_client()

        # ====================================================
        # SYSTEM INSTRUCTIONS
        # ====================================================

        system_prompt = """
You are an expert mathematics teacher assisting
another professional mathematics teacher.

Your task is to REVIEW a student's submitted
mathematics homework and provide a preliminary
grading recommendation.

The teacher will make the final grading decision.

IMPORTANT RULES:

1. Carefully examine the student's actual work.

2. Do not judge only by the final answers.

3. Evaluate:
   - mathematical reasoning
   - calculations
   - algebraic manipulation
   - formulas
   - intermediate steps
   - notation
   - final answers

4. If an answer key is not provided, independently
   solve the mathematical problems when necessary.

5. Identify partial credit opportunities.

6. Distinguish between:
   - conceptual mistakes
   - arithmetic mistakes
   - notation mistakes
   - incomplete work
   - missing answers

7. Do not invent information that cannot be seen.

8. If part of the student's work is unreadable,
   explicitly state that.

9. Consider the curriculum topic when evaluating
   the student's understanding.

10. The suggested grade is NOT automatically final.

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

Return ONLY valid JSON.

Use exactly this structure:

{
    "suggested_grade": "B+",
    "suggested_percentage": 88,
    "confidence": "High",
    "strengths": [
        "Strength 1",
        "Strength 2"
    ],
    "mistakes": [
        "Mistake 1",
        "Mistake 2"
    ],
    "feedback": "Suggested teacher feedback.",
    "reasoning": "Explanation of why the suggested grade was given."
}

The suggested percentage must be a number.

The confidence must be one of:

"High"
"Medium"
"Low"
"""

        # ====================================================
        # HOMEWORK CONTEXT
        # ====================================================

        context = f"""
HOMEWORK INFORMATION

Homework Title:
{homework_title}

Curriculum Topic:
{curriculum_topic}

Teacher Instructions / Comments:
{instructions}

TASK

Analyze the student's submitted homework PDF.

Determine:

1. What the student did correctly.
2. What the student did incorrectly.
3. Whether the student demonstrated understanding
   of the curriculum topic.
4. Whether partial credit appears appropriate.
5. A suggested letter grade.
6. A suggested percentage.
7. Confidence in the recommendation.
8. Suggested teacher feedback.

Remember:

This is a teacher-assistance tool.

Do not automatically assign the grade.
"""

        # ====================================================
        # PDF DATA URL
        # ====================================================

        pdf_data_url = (
            "data:application/pdf;base64,"
            + file_base64
        )

        # ====================================================
        # SEND TO OPENAI
        # ====================================================

        response = client.responses.create(

            model=AI_MODEL,

            instructions=system_prompt,

            input=[

                {
                    "role": "user",

                    "content": [

                        {
                            "type": "input_text",

                            "text": context
                        },

                        {
                            "type": "input_file",

                            "filename": "student_homework.pdf",

                            "file_data": pdf_data_url
                        }

                    ]
                }
            ]
        )

        # ====================================================
        # GET RESPONSE TEXT
        # ====================================================

        result_text = (
            response.output_text
            .strip()
        )

        # ====================================================
        # PARSE JSON
        # ====================================================

        try:

            result = json.loads(
                result_text
            )

        except json.JSONDecodeError:

            # ------------------------------------------------
            # Try removing markdown fences
            # ------------------------------------------------

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
                        "The AI returned an unexpected "
                        "response format."
                    ),
                    "raw_response": result_text
                }

        # ====================================================
        # NORMALIZE RESPONSE
        # ====================================================

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

    # ========================================================
    # ERROR HANDLING
    # ========================================================

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }
