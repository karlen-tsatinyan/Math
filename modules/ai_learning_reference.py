# ============================================================
# modules/ai_learning_reference.py
# ============================================================

import json
import re

import streamlit as st
import plotly.graph_objects as go

from google import genai
from google.genai import types


# ============================================================
# SETTINGS
# ============================================================

DEFAULT_MODEL = "gemini-3.7-flash"


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

    text = text.strip()

    # Remove markdown fences if Gemini adds them
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

    try:
        return json.loads(text)

    except Exception:
        pass

    # Try to locate the JSON object
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
# GENERATE LEARNING REFERENCE
# ============================================================

def generate_learning_reference(
    curriculum_topic,
    homework_title="",
    instructions="",
    student_grade=""
):

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

    client = get_gemini_client()

    if client is None:

        return {
            "success": False,
            "error": (
                "Gemini API key was not found. "
                "Please check Streamlit Secrets."
            )
        }

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

5. The important formula/rule if one exists.

6. ONE simple worked example that is DIFFERENT from
   the student's actual homework.

7. 2–4 common mistakes.

8. One short "Remember" statement.

VISUALIZATION
-------------
Decide whether an interactive mathematical visualization
would materially help the student understand this topic.

If yes:
- recommend a visualization type.

If no:
- set recommended to false.

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

Keep the entire response concise.
"""

    try:

        model = st.secrets["gemini"].get(
            "learning_model",
            DEFAULT_MODEL
        )

    except Exception:

        model = DEFAULT_MODEL

    try:

        response = client.models.generate_content(

            model=model,

            contents=prompt,

            config=types.GenerateContentConfig(

                temperature=0.25,

                response_mime_type="application/json",

                response_schema=LEARNING_SCHEMA
            )
        )

        result = _extract_json(
            response.text
        )

        if not result:

            return {
                "success": False,
                "error": (
                    "Gemini returned an invalid "
                    "learning reference."
                )
            }

        result["success"] = True

        return result

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
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

        render_slope_visualization()

    # ========================================================
    # LINEAR FUNCTION
    # ========================================================

    elif visualization_type == "linear_function":

        render_linear_visualization()

    # ========================================================
    # QUADRATIC
    # ========================================================

    elif visualization_type == "quadratic":

        render_quadratic_visualization()

    # ========================================================
    # PYTHAGOREAN
    # ========================================================

    elif visualization_type == "pythagorean":

        render_pythagorean_visualization()

    # ========================================================
    # TRIANGLE
    # ========================================================

    elif visualization_type == "triangle":

        render_triangle_visualization()

    # ========================================================
    # CIRCLE
    # ========================================================

    elif visualization_type == "circle":

        render_circle_visualization()

    # ========================================================
    # TRANSFORMATIONS
    # ========================================================

    elif visualization_type == "transformations":

        render_transformation_visualization()

    # ========================================================
    # TRIGONOMETRY
    # ========================================================

    elif visualization_type == "trigonometry":

        render_trigonometry_visualization()

    # ========================================================
    # PROBABILITY
    # ========================================================

    elif visualization_type == "probability":

        render_probability_visualization()


# ============================================================
# SLOPE VISUALIZATION
# ============================================================

def render_slope_visualization():

    slope = st.slider(
        "Slope",
        -5.0,
        5.0,
        1.0,
        0.5,
        key="learning_slope"
    )

    intercept = st.slider(
        "Y-intercept",
        -5.0,
        5.0,
        0.0,
        0.5,
        key="learning_intercept"
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
        title=f"y = {slope}x + {intercept}",
        showlegend=False
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ============================================================
# LINEAR FUNCTION
# ============================================================

def render_linear_visualization():

    m = st.slider(
        "Slope (m)",
        -5.0,
        5.0,
        1.0,
        0.5,
        key="learning_linear_m"
    )

    b = st.slider(
        "Y-intercept (b)",
        -5.0,
        5.0,
        0.0,
        0.5,
        key="learning_linear_b"
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

    fig.update_layout(
        height=450,
        xaxis_title="x",
        yaxis_title="f(x)",
        title="Explore a Linear Function"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ============================================================
# QUADRATIC
# ============================================================

def render_quadratic_visualization():

    a = st.slider(
        "a",
        -3.0,
        3.0,
        1.0,
        0.5,
        key="learning_quad_a"
    )

    b = st.slider(
        "b",
        -5.0,
        5.0,
        0.0,
        0.5,
        key="learning_quad_b"
    )

    c = st.slider(
        "c",
        -5.0,
        5.0,
        0.0,
        0.5,
        key="learning_quad_c"
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
        yaxis_title="y"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ============================================================
# PYTHAGOREAN THEOREM
# ============================================================

def render_pythagorean_visualization():

    a = st.slider(
        "Leg a",
        1.0,
        10.0,
        3.0,
        0.5,
        key="learning_pyth_a"
    )

    b = st.slider(
        "Leg b",
        1.0,
        10.0,
        4.0,
        0.5,
        key="learning_pyth_b"
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
        title=f"a² + b² = c²    |    c ≈ {c:.2f}",
        xaxis_title="",
        yaxis_title="",
        showlegend=False,
        xaxis=dict(
            scaleanchor="y"
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ============================================================
# TRIANGLE
# ============================================================

def render_triangle_visualization():

    base = st.slider(
        "Base",
        1.0,
        10.0,
        6.0,
        0.5,
        key="learning_triangle_base"
    )

    height = st.slider(
        "Height",
        1.0,
        10.0,
        4.0,
        0.5,
        key="learning_triangle_height"
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
        title=f"Triangle Area = {area:.2f}",
        showlegend=False,
        xaxis=dict(
            scaleanchor="y"
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ============================================================
# CIRCLE
# ============================================================

def render_circle_visualization():

    radius = st.slider(
        "Radius",
        1.0,
        10.0,
        5.0,
        0.5,
        key="learning_circle_radius"
    )

    theta = [
        i * 2 * 3.14159265 / 200
        for i in range(201)
    ]

    x = [
        radius * __import__("math").cos(t)
        for t in theta
    ]

    y = [
        radius * __import__("math").sin(t)
        for t in theta
    ]

    area = (
        3.14159265
        * radius ** 2
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
        title=f"Circle Area ≈ {area:.2f}",
        showlegend=False,
        xaxis=dict(
            scaleanchor="y"
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ============================================================
# TRANSFORMATIONS
# ============================================================

def render_transformation_visualization():

    shift_x = st.slider(
        "Horizontal translation",
        -5,
        5,
        2,
        key="learning_transform_x"
    )

    shift_y = st.slider(
        "Vertical translation",
        -5,
        5,
        1,
        key="learning_transform_y"
    )

    original_x = [1, 4, 2, 1]
    original_y = [1, 1, 4, 1]

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
        use_container_width=True
    )


# ============================================================
# TRIGONOMETRY
# ============================================================

def render_trigonometry_visualization():

    angle = st.slider(
        "Angle",
        0,
        89,
        30,
        1,
        key="learning_trig_angle"
    )

    import math

    radians = math.radians(
        angle
    )

    opposite = math.sin(
        radians
    )

    adjacent = math.cos(
        radians
    )

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=[0, adjacent, 0, 0],
            y=[0, 0, opposite, 0],
            mode="lines+markers",
            fill="toself",
            name="Triangle"
        )
    )

    fig.update_layout(
        height=450,
        title=(
            f"sin({angle}°) ≈ {opposite:.3f}   |   "
            f"cos({angle}°) ≈ {adjacent:.3f}"
        ),
        showlegend=False,
        xaxis=dict(
            scaleanchor="y"
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ============================================================
# PROBABILITY
# ============================================================

def render_probability_visualization():

    favorable = st.slider(
        "Favorable outcomes",
        0,
        20,
        3,
        key="learning_probability_favorable"
    )

    total = st.slider(
        "Total outcomes",
        1,
        20,
        10,
        key="learning_probability_total"
    )

    if favorable > total:
        favorable = total

    probability = (
        favorable / total
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
                total - favorable
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
        use_container_width=True
    )


# ============================================================
# DISPLAY LEARNING REFERENCE
# ============================================================

def display_learning_reference(
    result
):

    if not result:

        return

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

    st.markdown(
        f"## 📖 {result.get('title', 'Topic Reference')}"
    )

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
