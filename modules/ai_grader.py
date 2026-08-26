# ============================================================
# AI HOMEWORK GRADER
# ============================================================

"""
Uses Google Gemini to analyze a student's submitted homework PDF.

IMPORTANT:
- AI provides a recommendation only.
- The teacher remains responsible for the final grade.
- This module does NOT modify the homework database.
"""

import os
import json
import tempfile
import time

from google import genai
from google.genai import types


# ============================================================
# GEMINI CLIENT
# ============================================================

def get_gemini_api_key():

    api_key = None

    # --------------------------------------------------------
    # 1. STREAMLIT SECRETS
    # --------------------------------------------------------

    try:
        import streamlit as st

        # Your current secrets structure:
        #
        # [gemini]
        # api_key = "..."

        gemini_section = st.secrets.get(
            "gemini"
        )

        if gemini_section:

            api_key = gemini_section.get(
                "api_key"
            )

    except Exception:
        api_key = None

    # --------------------------------------------------------
    # 2. ENVIRONMENT VARIABLE FALLBACK
    # --------------------------------------------------------

    if not api_key:

        api_key = os.getenv(
            "GEMINI_API_KEY"
        )

    # --------------------------------------------------------
    # 3. GOOGLE API KEY FALLBACK
    # --------------------------------------------------------

    if not api_key:

        api_key = os.getenv(
            "GOOGLE_API_KEY"
        )

    # --------------------------------------------------------
    # VALIDATE
    # --------------------------------------------------------

    if not api_key:

        raise ValueError(
            "Gemini API key was not found. "
            "Please configure [gemini] api_key "
            "in Streamlit Secrets."
        )

    return str(api_key).strip()

# ============================================================
# GEMINI CLIENT
# ============================================================

def get_gemini_client():

    api_key = get_gemini_api_key()

    return genai.Client(
        api_key=api_key
    )

# ============================================================
# AI HOMEWORK GRADING
# ============================================================

def grade_homework_with_ai(
    pdf_bytes,
    homework_title="Homework Assignment",
    curriculum_topic="",
    instructions="",
):
    """
    Analyze a student's homework PDF with Gemini.

    Parameters
    ----------
    pdf_bytes : bytes
        Student's homework PDF.

    homework_title : str
        Homework title.

    curriculum_topic : str
        Curriculum topic.

    instructions : str
        Teacher instructions/comments.

    Returns
    -------
    dict
        AI grading recommendation.

    IMPORTANT:
        This function does NOT save anything to the database.
    """

    # ========================================================
    # VALIDATE INPUT
    # ========================================================

    if not pdf_bytes:

        return {
            "success": False,
            "error": (
                "No student homework PDF was provided."
            )
        }

    temp_path = None

    try:

        # ====================================================
        # GEMINI CLIENT
        # ====================================================

        client = get_gemini_client()

        # ====================================================
        # CREATE TEMPORARY PDF
        # ====================================================

        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            delete=False
        ) as temp_file:

            temp_file.write(pdf_bytes)

            temp_path = temp_file.name

        # ====================================================
        # UPLOAD PDF TO GEMINI
        # ====================================================

        uploaded_file = client.files.upload(
            file=temp_path
        )

        # ====================================================
        # GRADING PROMPT
        # ====================================================

        prompt = f"""
You are an expert mathematics teacher assisting another
professional mathematics teacher with homework review.

Analyze the student's submitted homework PDF.

This is a PRELIMINARY grading recommendation only.

The teacher will personally review your analysis and make
the final grading decision.

------------------------------------------------------------
HOMEWORK INFORMATION
------------------------------------------------------------

Homework Title:
{homework_title}

Curriculum Topic:
{curriculum_topic}

Teacher Instructions:
{instructions}

------------------------------------------------------------
GRADING RULES
------------------------------------------------------------

1. Carefully examine the student's actual mathematical work.

2. Do not assume that an answer is correct simply because
   the final answer looks reasonable.

3. Evaluate mathematical reasoning, calculations, formulas,
   notation, intermediate steps, and final answers.

4. Identify conceptual mistakes separately from simple
   arithmetic or transcription mistakes.

5. Give credit for partially correct reasoning when
   appropriate.

6. If the student's work is unclear or unreadable, say so.

7. If there is no answer key, independently solve the
   problems when necessary.

8. Do not invent missing student work.

9. Do not invent problems that are not present.

10. Consider the entire submission when recommending a grade.

------------------------------------------------------------
GRADE SCALE
------------------------------------------------------------

A+ = 98
A  = 95
A- = 92

B+ = 88
B  = 85
B- = 82

C+ = 78
C  = 75
C- = 72

D = 65
F = 50

------------------------------------------------------------
IMPORTANT
------------------------------------------------------------

The suggested grade is NOT the official grade.

The teacher must review the recommendation before saving
anything to the tutoring portal.

------------------------------------------------------------
OUTPUT
------------------------------------------------------------

Return ONLY valid JSON with this structure:

{{
    "suggested_grade": "B+",
    "suggested_percentage": 88,
    "confidence": "High",
    "summary": "Short overall assessment.",
    "strengths": [
        "Strength 1",
        "Strength 2"
    ],
    "mistakes": [
        "Mistake 1",
        "Mistake 2"
    ],
    "problem_analysis": [
        {{
            "problem": "1",
            "result": "Correct",
            "explanation": "Brief explanation."
        }}
    ],
    "feedback": "Suggested teacher feedback.",
    "reasoning": "Brief explanation of why the suggested grade was assigned."
}}

Do not include Markdown code fences.

Return JSON only.
"""

        # ====================================================
        # GEMINI REQUEST WITH RETRY + MODEL FALLBACK
        # ====================================================

        response = None
        last_error = None

        # Primary model first, then a fallback model.
        models_to_try = [
            "gemini-3.7-flash",
            "gemini-3.6-flash",
        ]

        generation_config = types.GenerateContentConfig(
            response_mime_type="application/json",

            response_schema={
                "type": "object",

                "properties": {

                    "suggested_grade": {
                        "type": "string"
                    },

                    "suggested_percentage": {
                        "type": "integer"
                    },

                    "confidence": {
                        "type": "string"
                    },

                    "summary": {
                        "type": "string"
                    },

                    "strengths": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },

                    "mistakes": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },

                    "problem_analysis": {
                        "type": "array",
                        "items": {
                            "type": "object",

                            "properties": {

                                "problem": {
                                    "type": "string"
                                },

                                "result": {
                                    "type": "string"
                                },

                                "explanation": {
                                    "type": "string"
                                }
                            },

                            "required": [
                                "problem",
                                "result",
                                "explanation"
                            ]
                        }
                    },

                    "feedback": {
                        "type": "string"
                    },

                    "reasoning": {
                        "type": "string"
                    }
                },

                "required": [
                    "suggested_grade",
                    "suggested_percentage",
                    "confidence",
                    "summary",
                    "strengths",
                    "mistakes",
                    "problem_analysis",
                    "feedback",
                    "reasoning"
                ]
            }
        )

        for model_name in models_to_try:

            for attempt in range(3):

                try:

                    response = client.models.generate_content(
                        model=model_name,
                        contents=[
                            prompt,
                            uploaded_file
                        ],
                        config=generation_config
                    )

                    if response is not None:
                        break

                except Exception as e:

                    last_error = e
                    error_text = str(e)

                    temporary_error = (
                        "503" in error_text
                        or "UNAVAILABLE" in error_text.upper()
                        or "429" in error_text
                        or "RESOURCE_EXHAUSTED"
                        in error_text.upper()
                    )

                    if not temporary_error:
                        raise

                    # Exponential backoff:
                    # 2 seconds, 5 seconds, 10 seconds.
                    if attempt < 2:
                        time.sleep(
                            [2, 5, 10][attempt]
                        )

            if response is not None:
                break

        if response is None:

            if last_error:

                return {
                    "success": False,
                    "error": (
                        "Gemini is temporarily unavailable "
                        "after multiple attempts. "
                        "Please try again in a few moments. "
                        f"Last error: {last_error}"
                    )
                }

            return {
                "success": False,
                "error": (
                    "Gemini did not return a response."
                )
            }

        # ====================================================
        # GET RESPONSE
        # ====================================================

        response_text = response.text

        if not response_text:

            return {
                "success": False,
                "error": (
                    "Gemini returned an empty response."
                )
            }

        # ====================================================
        # PARSE JSON
        # ====================================================

        try:

            result = json.loads(
                response_text
            )

        except json.JSONDecodeError:

            return {
                "success": False,
                "error": (
                    "Gemini returned an unexpected "
                    "response format."
                ),
                "raw_response": response_text
            }

        # ====================================================
        # NORMALIZE RESULT
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
            "summary",
            ""
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
            "problem_analysis",
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

        error_text = str(e)

        if (
            "503" in error_text
            or "UNAVAILABLE" in error_text.upper()
        ):

            friendly_error = (
                "Gemini is temporarily unavailable because "
                "the model is experiencing high demand. "
                "Please try again in a few moments."
            )

        elif (
            "429" in error_text
            or "RESOURCE_EXHAUSTED"
            in error_text.upper()
        ):

            friendly_error = (
                "Gemini rate limit was reached. "
                "Please wait a moment and try again."
            )

        else:

            friendly_error = error_text

        return {
            "success": False,
            "error": friendly_error
        }

    # ========================================================
    # CLEANUP
    # ========================================================

    finally:

        if temp_path:

            try:

                os.remove(
                    temp_path
                )

            except Exception:

                pass
