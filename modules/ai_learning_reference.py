# ============================================================
# modules/ai_learning_reference.py
# ============================================================

import json
import math
import re
import time

import streamlit as st
import plotly.graph_objects as go

from google import genai
from google.genai import types


# ============================================================
# SETTINGS
# ============================================================

DEFAULT_MODEL = "gemini-3.5-flash-lite"

FALLBACK_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.6-flash",
]


# ============================================================
# GEMINI CLIENT
# ============================================================

def get_gemini_client():

    try:

        api_key = st.secrets["gemini"]["api_key"]

    except Exception:

        return None

    if not api_key:

        return None

    try:

        return genai.Client(
            api_key=api_key
        )

    except Exception:

        return None


# ============================================================
# RESPONSE SCHEMA
# ============================================================

LEARNING_SCHEMA = {

    "type": "object",

    "properties": {

        "topic": {
            "type": "string"
        },

        "title": {
            "type": "string"
        },

        "summary": {
            "type": "string"
        },

        "key_ideas": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },

        "steps": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },

        "formula": {
            "type": "string"
        },

        "worked_example": {
            "type": "string"
        },

        "common_mistakes": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },

        "remember": {
            "type": "string"
        },

        "visualization": {

            "type": "object",

            "properties": {

                "recommended": {
                    "type": "boolean"
                },

                "type": {
                    "type": "string"
                },

                "title": {
                    "type": "string"
                },

                "description": {
                    "type": "string"
                }

            },

            "required": [
                "recommended",
                "type",
                "title",
                "description"
            ]
        }
    },

    "required": [
        "topic",
        "title",
        "summary",
        "key_ideas",
        "steps",
        "formula",
        "worked_example",
        "common_mistakes",
        "remember",
        "visualization"
    ]
}


# ============================================================
# CLEAN JSON RESPONSE
# ============================================================

def _extract_json(text):

    if not text:

        return None

    text = str(text).strip()

    # --------------------------------------------------------
    # Remove markdown fences
    # --------------------------------------------------------

    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"^```\s*",
        "",
        text
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    # --------------------------------------------------------
    # Direct JSON parse
    # --------------------------------------------------------

    try:

        return json.loads(text)

    except Exception:

        pass

    # --------------------------------------------------------
    # Locate JSON object
    # --------------------------------------------------------

    start = text.find("{")

    end = text.rfind("}")

    if start >= 0 and end > start:

        try:

            return json.loads(
                text[start:end + 1]
            )

        except Exception:

            pass

    return None


# ============================================================
# FRIENDLY GEMINI ERROR
# ============================================================

def _friendly_gemini_error(error):

    error_text = str(
        error or ""
    )

    lower_text = error_text.lower()

    # --------------------------------------------------------
    # 503 / unavailable
    # --------------------------------------------------------

    if (
        "503" in lower_text
        or "unavailable" in lower_text
        or "service unavailable" in lower_text
        or "high demand" in lower_text
    ):

        return (
            "Gemini is temporarily unavailable because "
            "the model is experiencing high demand. "
            "Please wait a moment and try again."
        )

    # --------------------------------------------------------
    # 429 / rate limit
    # --------------------------------------------------------

    if (
        "429" in lower_text
        or "resource_exhausted" in lower_text
        or "rate limit" in lower_text
    ):

        return (
            "Gemini rate limit was reached. "
            "Please wait a moment and try again."
        )

    # --------------------------------------------------------
    # Authentication
    # --------------------------------------------------------

    if (
        "401" in lower_text
        or "403" in lower_text
        or "api key" in lower_text
        or "permission" in lower_text
    ):

        return (
            "The Gemini API could not be accessed. "
            "Please check the Gemini API key and permissions "
            "in Streamlit Secrets."
        )

    # --------------------------------------------------------
    # Generic
    # --------------------------------------------------------

    return error_text or (
        "Gemini did not return a response."
    )


# ============================================================
# GENERATE LEARNING REFERENCE
# ============================================================

def generate_learning_reference(
    curriculum_topic,
    homework_title="",
    instructions="",
    student_grade=""
):

    # ========================================================
    # VALIDATE TOPIC
    # ========================================================

    topic = str(
        curriculum_topic or ""
    ).strip()

    if not topic:

        return {
            "success": False,
            "error": (
                "No curriculum topic is assigned "
                "to this homework."
            )
        }

    # ========================================================
    # GEMINI CLIENT
    # ========================================================

    client = get_gemini_client()

    if client is None:

        return {
            "success": False,
            "error": (
                "Gemini API key was not found. "
                "Please check Streamlit Secrets."
            )
        }

    # ========================================================
    # PROMPT
    # ========================================================

    prompt = f"""
You are the learning-reference assistant inside a
professional mathematics tutoring portal.

Create a SHORT, meaningful learning reference for a student.

STUDENT INFORMATION
-------------------
Grade: {student_grade or "Not specified"}

CURRICULUM TOPIC
----------------
{topic}

HOMEWORK TITLE
--------------
{homework_title or "Not specified"}

TEACHER INSTRUCTIONS
--------------------
{instructions or "None"}

IMPORTANT PURPOSE
------------------
The student is using this while studying or doing homework.

The reference should TEACH THE CONCEPT.

Do NOT solve the student's assigned homework.

Do NOT give answers to specific homework problems.

Do NOT invent a textbook chapter number.

Do NOT tell the student to search Google.

Keep the explanation appropriate for the student's grade.

CONTENT REQUIREMENTS
--------------------

Create:

1. A short title.

2. A concise explanation of the main idea.

3. 2–5 key ideas.

4. A short step-by-step method when appropriate.

5. The important formula or rule if one exists.

6. ONE simple worked example that is DIFFERENT from
   the student's actual homework.

7. 2–4 common mistakes.

8. One short "Remember" statement.

VISUALIZATION
-------------

Decide whether an interactive mathematical visualization
would materially help the student understand this topic.

If yes:

- recommend a visualization type
- explain why it helps

If no:

- set recommended to false
- use type "none"

Only recommend a visualization if it is mathematically
meaningful and useful for understanding the concept.

Use one of these visualization types when appropriate:

- slope
- linear_function
- quadratic
- pythagorean
- triangle
- circle
- transformations
- trigonometry
- probability
- none

IMPORTANT VISUALIZATION RULE
----------------------------

The visualization recommendation should match the
curriculum topic.

For example:

- slope → slope
- linear equations/functions → linear_function
- quadratics → quadratic
- right triangles → pythagorean
- triangle geometry → triangle
- circle geometry → circle
- transformations → transformations
- trigonometry → trigonometry
- probability → probability

Keep the entire response concise.
"""

    # ========================================================
    # MODEL SELECTION
    # ========================================================

    try:

        primary_model = st.secrets["gemini"].get(
            "learning_model",
            DEFAULT_MODEL
        )

    except Exception:

        primary_model = DEFAULT_MODEL

    primary_model = str(
        primary_model or DEFAULT_MODEL
    ).strip()

    # --------------------------------------------------------
    # Build unique model list
    # --------------------------------------------------------

    models_to_try = [
        primary_model
    ]

    for fallback_model in FALLBACK_MODELS:

        if fallback_model not in models_to_try:

            models_to_try.append(
                fallback_model
            )

    # ========================================================
    # GEMINI REQUEST
    # ========================================================

    last_error = None

    for model_name in models_to_try:

        # ----------------------------------------------------
        # Two attempts per model
        # ----------------------------------------------------

        for attempt in range(2):

            try:

                response = client.models.generate_content(

                    model=model_name,

                    contents=prompt,

                    config=types.GenerateContentConfig(

                        temperature=0.25,

                        response_mime_type=(
                            "application/json"
                        ),

                        response_schema=(
                            LEARNING_SCHEMA
                        )
                    )
                )

                # ------------------------------------------------
                # Get response text
                # ------------------------------------------------

                response_text = getattr(
                    response,
                    "text",
                    None
                )

                if not response_text:

                    last_error = (
                        f"{model_name} returned "
                        "an empty response."
                    )

                    break

                # ------------------------------------------------
                # Parse JSON
                # ------------------------------------------------

                result = _extract_json(
                    response_text
                )

                if not result:

                    last_error = (
                        f"{model_name} returned "
                        "an invalid learning reference."
                    )

                    break

                # ------------------------------------------------
                # Ensure visualization object exists
                # ------------------------------------------------

                if not isinstance(
                    result.get("visualization"),
                    dict
                ):

                    result["visualization"] = {

                        "recommended": False,

                        "type": "none",

                        "title": "",

                        "description": ""
                    }

                # ------------------------------------------------
                # Success
                # ------------------------------------------------

                result["success"] = True

                return result

            except Exception as e:

                last_error = e

                error_text = str(
                    e
                ).lower()

                # ------------------------------------------------
                # Temporary service errors
                # ------------------------------------------------

                temporary_error = (

                    "503" in error_text

                    or "unavailable" in error_text

                    or "service unavailable"
                    in error_text

                    or "high demand"
                    in error_text
                )

                # ------------------------------------------------
                # Rate limit
                # ------------------------------------------------

                rate_limit_error = (

                    "429" in error_text

                    or "resource_exhausted"
                    in error_text

                    or "rate limit"
                    in error_text
                )

                # ------------------------------------------------
                # Retry temporary errors
                # ------------------------------------------------

                if (
                    temporary_error
                    or rate_limit_error
                ):

                    if attempt == 0:

                        time.sleep(
                            2
                        )

                        continue

                # ------------------------------------------------
                # Don't retry permanent errors
                # ------------------------------------------------

                break

        # --------------------------------------------------------
        # Try next fallback model
        # --------------------------------------------------------

        continue

    # ========================================================
    # ALL MODELS FAILED
    # ========================================================

    friendly_error = _friendly_gemini_error(
        last_error
    )

    return {

        "success": False,

        "error": friendly_error
    }


# ============================================================
# INTERACTIVE VISUALIZATIONS
# ============================================================

def render_learning_visualization(
    visualization,
    topic=""
):

    if not visualization:

        return

    if not visualization.get(
        "recommended",
        False
    ):

        return

    visualization_type = str(
        visualization.get(
            "type",
            "none"
        )
    ).lower().strip()

    title = visualization.get(
        "title",
        "Interactive Visualization"
    )

    description = visualization.get(
        "description",
        ""
    )

    st.markdown(
        f"### 🎯 {title}"
    )

    if description:

        st.caption(
            description
        )

    # ========================================================
    # SLOPE
    # ========================================================

    if visualization_type == "slope":

        render_slope_visualization(
            topic
        )

    # ========================================================
    # LINEAR FUNCTION
    # ========================================================

    elif visualization_type == "linear_function":

        render_linear_visualization(
            topic
        )

    # ========================================================
    # QUADRATIC
    # ========================================================

    elif visualization_type == "quadratic":

        render_quadratic_visualization(
            topic
        )

    # ========================================================
    # PYTHAGOREAN
    # ========================================================

    elif visualization_type == "pythagorean":

        render_pythagorean_visualization(
            topic
        )

    # ========================================================
    # TRIANGLE
    # ========================================================

    elif visualization_type == "triangle":

        render_triangle_visualization(
            topic
        )

    # ========================================================
    # CIRCLE
    # ========================================================

    elif visualization_type == "circle":

        render_circle_visualization(
            topic
        )

    # ========================================================
    # TRANSFORMATIONS
    # ========================================================

    elif visualization_type == "transformations":

        render_transformation_visualization(
            topic
        )

    # ========================================================
    # TRIGONOMETRY
    # ========================================================

    elif visualization_type == "trigonometry":

        render_trigonometry_visualization(
            topic
        )

    # ========================================================
    # PROBABILITY
    # ========================================================

    elif visualization_type == "probability":

        render_probability_visualization(
            topic
        )


# ============================================================
# SLOPE VISUALIZATION
# ============================================================

def render_slope_visualization(
    topic=""
):

    key_suffix = (
        str(topic)
        .lower()
        .replace(" ", "_")
        [:40]
    )

    slope = st.slider(

        "Slope",

        -5.0,

        5.0,

        1.0,

        0.5,

        key=f"learning_slope_{key_suffix}"
    )

    intercept = st.slider(

        "Y-intercept",

        -5.0,

        5.0,

        0.0,

        0.5,

        key=f"learning_intercept_{key_suffix}"
    )

    x = [
        -10 + i * 0.2
        for i in range(101)
    ]

    y = [
        slope * value + intercept
        for value in x
    ]

    fig = go.Figure()

    fig.add_trace(

        go.Scatter(

            x=x,

            y=y,

            mode="lines",

            name="Line"
        )
    )

    fig.add_hline(
        y=0
    )

    fig.add_vline(
        x=0
    )

    fig.update_layout(

        height=450,

        xaxis_title="x",

        yaxis_title="y",

        title=(
            f"y = {slope}x + {intercept}"
        ),

        showlegend=False
    )

    st.plotly_chart(

        fig,

        use_container_width=True,

        key=f"chart_slope_{key_suffix}"
    )


# ============================================================
# LINEAR FUNCTION
# ============================================================

def render_linear_visualization(
    topic=""
):

    key_suffix = (
        str(topic)
        .lower()
        .replace(" ", "_")
        [:40]
    )

    m = st.slider(

        "Slope (m)",

        -5.0,

        5.0,

        1.0,

        0.5,

        key=f"learning_linear_m_{key_suffix}"
    )

    b = st.slider(

        "Y-intercept (b)",

        -5.0,

        5.0,

        0.0,

        0.5,

        key=f"learning_linear_b_{key_suffix}"
    )

    x = [
        -10 + i * 0.2
        for i in range(101)
    ]

    y = [
        m * value + b
        for value in x
    ]

    fig = go.Figure()

    fig.add_trace(

        go.Scatter(

            x=x,

            y=y,

            mode="lines",

            name="f(x)"
        )
    )

    fig.add_hline(
        y=0
    )

    fig.add_vline(
        x=0
    )

    fig.update_layout(

        height=450,

        xaxis_title="x",

        yaxis_title="f(x)",

        title="Explore a Linear Function",

        showlegend=False
    )

    st.plotly_chart(

        fig,

        use_container_width=True,

        key=f"chart_linear_{key_suffix}"
    )


# ============================================================
# QUADRATIC
# ============================================================

def render_quadratic_visualization(
    topic=""
):

    key_suffix = (
        str(topic)
        .lower()
        .replace(" ", "_")
        [:40]
    )

    a = st.slider(

        "a",

        -3.0,

        3.0,

        1.0,

        0.5,

        key=f"learning_quad_a_{key_suffix}"
    )

    b = st.slider(

        "b",

        -5.0,

        5.0,

        0.0,

        0.5,

        key=f"learning_quad_b_{key_suffix}"
    )

    c = st.slider(

        "c",

        -5.0,

        5.0,

        0.0,

        0.5,

        key=f"learning_quad_c_{key_suffix}"
    )

    x = [
        -10 + i * 0.1
        for i in range(201)
    ]

    y = [

        a * value ** 2
        + b * value
        + c

        for value in x
    ]

    fig = go.Figure()

    fig.add_trace(

        go.Scatter(

            x=x,

            y=y,

            mode="lines",

            name="Quadratic"
        )
    )

    fig.add_hline(
        y=0
    )

    fig.add_vline(
        x=0
    )

    fig.update_layout(

        height=450,

        title="Explore a Quadratic Function",

        xaxis_title="x",

        yaxis_title="y",

        showlegend=False
    )

    st.plotly_chart(

        fig,

        use_container_width=True,

        key=f"chart_quadratic_{key_suffix}"
    )


# ============================================================
# PYTHAGOREAN THEOREM
# ============================================================

def render_pythagorean_visualization(
    topic=""
):

    key_suffix = (
        str(topic)
        .lower()
        .replace(" ", "_")
        [:40]
    )

    a = st.slider(

        "Leg a",

        1.0,

        10.0,

        3.0,

        0.5,

        key=f"learning_pyth_a_{key_suffix}"
    )

    b = st.slider(

        "Leg b",

        1.0,

        10.0,

        4.0,

        0.5,

        key=f"learning_pyth_b_{key_suffix}"
    )

    c = (
        a ** 2
        + b ** 2
    ) ** 0.5

    fig = go.Figure()

    fig.add_trace(

        go.Scatter(

            x=[0, a, 0, 0],

            y=[0, 0, b, 0],

            mode="lines+markers",

            fill="toself",

            name="Right Triangle"
        )
    )

    fig.update_layout(

        height=450,

        title=(
            f"a² + b² = c²   |   "
            f"c ≈ {c:.2f}"
        ),

        xaxis_title="",

        yaxis_title="",

        showlegend=False,

        xaxis=dict(
            scaleanchor="y"
        )
    )

    st.plotly_chart(

        fig,

        use_container_width=True,

        key=f"chart_pythagorean_{key_suffix}"
    )


# ============================================================
# TRIANGLE
# ============================================================

def render_triangle_visualization(
    topic=""
):

    key_suffix = (
        str(topic)
        .lower()
        .replace(" ", "_")
        [:40]
    )

    base = st.slider(

        "Base",

        1.0,

        10.0,

        6.0,

        0.5,

        key=f"learning_triangle_base_{key_suffix}"
    )

    height = st.slider(

        "Height",

        1.0,

        10.0,

        4.0,

        0.5,

        key=f"learning_triangle_height_{key_suffix}"
    )

    area = (
        base * height / 2
    )

    fig = go.Figure()

    fig.add_trace(

        go.Scatter(

            x=[0, base, 0, 0],

            y=[0, 0, height, 0],

            mode="lines+markers",

            fill="toself",

            name="Triangle"
        )
    )

    fig.update_layout(

        height=450,

        title=(
            f"Triangle Area = {area:.2f}"
        ),

        showlegend=False,

        xaxis=dict(
            scaleanchor="y"
        )
    )

    st.plotly_chart(

        fig,

        use_container_width=True,

        key=f"chart_triangle_{key_suffix}"
    )


# ============================================================
# CIRCLE
# ============================================================

def render_circle_visualization(
    topic=""
):

    key_suffix = (
        str(topic)
        .lower()
        .replace(" ", "_")
        [:40]
    )

    radius = st.slider(

        "Radius",

        1.0,

        10.0,

        5.0,

        0.5,

        key=f"learning_circle_radius_{key_suffix}"
    )

    theta = [

        i * 2 * math.pi / 200

        for i in range(201)
    ]

    x = [

        radius * math.cos(t)

        for t in theta
    ]

    y = [

        radius * math.sin(t)

        for t in theta
    ]

    area = (
        math.pi
        * radius ** 2
    )

    circumference = (
        2
        * math.pi
        * radius
    )

    fig = go.Figure()

    fig.add_trace(

        go.Scatter(

            x=x,

            y=y,

            mode="lines",

            fill="toself",

            name="Circle"
        )
    )

    fig.update_layout(

        height=450,

        title=(
            f"Area ≈ {area:.2f}   |   "
            f"Circumference ≈ {circumference:.2f}"
        ),

        showlegend=False,

        xaxis=dict(
            scaleanchor="y"
        )
    )

    st.plotly_chart(

        fig,

        use_container_width=True,

        key=f"chart_circle_{key_suffix}"
    )


# ============================================================
# TRANSFORMATIONS
# ============================================================

def render_transformation_visualization(
    topic=""
):

    key_suffix = (
        str(topic)
        .lower()
        .replace(" ", "_")
        [:40]
    )

    shift_x = st.slider(

        "Horizontal translation",

        -5,

        5,

        2,

        key=f"learning_transform_x_{key_suffix}"
    )

    shift_y = st.slider(

        "Vertical translation",

        -5,

        5,

        1,

        key=f"learning_transform_y_{key_suffix}"
    )

    original_x = [
        1,
        4,
        2,
        1
    ]

    original_y = [
        1,
        1,
        4,
        1
    ]

    transformed_x = [

        x + shift_x

        for x in original_x
    ]

    transformed_y = [

        y + shift_y

        for y in original_y
    ]

    fig = go.Figure()

    fig.add_trace(

        go.Scatter(

            x=original_x,

            y=original_y,

            mode="lines+markers",

            name="Original"
        )
    )

    fig.add_trace(

        go.Scatter(

            x=transformed_x,

            y=transformed_y,

            mode="lines+markers",

            name="Translated"
        )
    )

    fig.update_layout(

        height=450,

        title="Explore a Translation",

        xaxis=dict(
            range=[-6, 10]
        ),

        yaxis=dict(

            range=[-6, 10],

            scaleanchor="x"
        )
    )

    st.plotly_chart(

        fig,

        use_container_width=True,

        key=f"chart_transform_{key_suffix}"
    )


# ============================================================
# TRIGONOMETRY
# ============================================================

def render_trigonometry_visualization(
    topic=""
):

    key_suffix = (
        str(topic)
        .lower()
        .replace(" ", "_")
        [:40]
    )

    angle = st.slider(

        "Angle",

        0,

        89,

        30,

        1,

        key=f"learning_trig_angle_{key_suffix}"
    )

    radians = math.radians(
        angle
    )

    opposite = math.sin(
        radians
    )

    adjacent = math.cos(
        radians
    )

    tangent = math.tan(
        radians
    )

    fig = go.Figure()

    fig.add_trace(

        go.Scatter(

            x=[
                0,
                adjacent,
                0,
                0
            ],

            y=[
                0,
                0,
                opposite,
                0
            ],

            mode="lines+markers",

            fill="toself",

            name="Triangle"
        )
    )

    fig.update_layout(

        height=450,

        title=(

            f"sin({angle}°) ≈ {opposite:.3f}   |   "

            f"cos({angle}°) ≈ {adjacent:.3f}   |   "

            f"tan({angle}°) ≈ {tangent:.3f}"
        ),

        showlegend=False,

        xaxis=dict(
            scaleanchor="y"
        )
    )

    st.plotly_chart(

        fig,

        use_container_width=True,

        key=f"chart_trig_{key_suffix}"
    )


# ============================================================
# PROBABILITY
# ============================================================

def render_probability_visualization(
    topic=""
):

    key_suffix = (
        str(topic)
        .lower()
        .replace(" ", "_")
        [:40]
    )

    favorable = st.slider(

        "Favorable outcomes",

        0,

        20,

        3,

        key=f"learning_probability_favorable_{key_suffix}"
    )

    total = st.slider(

        "Total outcomes",

        1,

        20,

        10,

        key=f"learning_probability_total_{key_suffix}"
    )

    if favorable > total:

        favorable = total

    probability = (
        favorable / total
    )

    unfavorable = (
        total - favorable
    )

    fig = go.Figure()

    fig.add_trace(

        go.Bar(

            x=[
                "Favorable",
                "Unfavorable"
            ],

            y=[
                favorable,
                unfavorable
            ]
        )
    )

    fig.update_layout(

        height=400,

        title=(

            f"Probability = "
            f"{probability:.1%}"
        ),

        showlegend=False
    )

    st.plotly_chart(

        fig,

        use_container_width=True,

        key=f"chart_probability_{key_suffix}"
    )


# ============================================================
# DISPLAY LEARNING REFERENCE
# ============================================================

def display_learning_reference(
    result
):

    if not result:

        return

    # ========================================================
    # ERROR
    # ========================================================

    if not result.get(
        "success",
        False
    ):

        st.error(

            result.get(

                "error",

                "Unable to create learning reference."
            )
        )

        return

    # ========================================================
    # TITLE
    # ========================================================

    st.markdown(

        f"## 📖 "
        f"{result.get('title', 'Topic Reference')}"
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    summary = result.get(
        "summary",
        ""
    )

    if summary:

        st.info(
            summary
        )

    # ========================================================
    # KEY IDEAS
    # ========================================================

    key_ideas = result.get(
        "key_ideas",
        []
    )

    if key_ideas:

        st.markdown(
            "### 💡 Key Ideas"
        )

        for item in key_ideas:

            st.markdown(
                f"- {item}"
            )

    # ========================================================
    # FORMULA
    # ========================================================

    formula = str(

        result.get(
            "formula",
            ""
        )
    ).strip()

    if formula:

        st.markdown(

            "### 📐 Important Rule / Formula"
        )

        st.code(

            formula,

            language="text"
        )

    # ========================================================
    # STEPS
    # ========================================================

    steps = result.get(
        "steps",
        []
    )

    if steps:

        st.markdown(

            "### 🪜 How to Approach It"
        )

        for index, step in enumerate(

            steps,

            start=1
        ):

            st.markdown(

                f"**{index}.** {step}"
            )

    # ========================================================
    # WORKED EXAMPLE
    # ========================================================

    example = str(

        result.get(
            "worked_example",
            ""
        )
    ).strip()

    if example:

        st.markdown(

            "### ✏️ Worked Example"
        )

        st.info(
            example
        )

    # ========================================================
    # COMMON MISTAKES
    # ========================================================

    mistakes = result.get(

        "common_mistakes",

        []
    )

    if mistakes:

        st.markdown(

            "### ⚠️ Common Mistakes"
        )

        for mistake in mistakes:

            st.markdown(

                f"- {mistake}"
            )

    # ========================================================
    # REMEMBER
    # ========================================================

    remember = str(

        result.get(
            "remember",
            ""
        )
    ).strip()

    if remember:

        st.success(

            f"🧠 **Remember:** {remember}"
        )

    # ========================================================
    # VISUALIZATION
    # ========================================================

    visualization = result.get(

        "visualization"
    )

    if visualization:

        render_learning_visualization(

            visualization,

            result.get(
                "topic",
                ""
            )
        )
