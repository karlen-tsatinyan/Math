# ============================================================
# modules/ai_learning_reference.py
# ============================================================
#
# AI Learning Reference
#
# Purpose:
#   Give students a short, useful theory/reference section
#   related to the curriculum topic of their homework or lesson.
#
# Design goals:
#   - One Gemini request per click
#   - Retry the SAME model on temporary 503 errors
#   - Fall back only after same-model retries fail
#   - No database storage
#   - Results stored only in Streamlit session_state
#   - Topic-specific visualizations generated locally
#   - Plotly visualizations when appropriate
#
# ============================================================

import json
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
    "gemini-3.6-flash-lite",
    "gemini-3.7-flash-lite",
]

# Number of retries for the SAME model after a temporary 503.
#
# Example:
#   attempt 1 -> 503
#   wait
#   attempt 2 -> 503
#   wait
#   attempt 3 -> 503
#   then try fallback model
#
SAME_MODEL_RETRIES = 2

RETRY_DELAYS = [
    2,
    5,
]

# Keep generation relatively concise.
# This helps response speed and reduces token usage.
TEMPERATURE = 0.2

MAX_OUTPUT_TOKENS = 1800


# ============================================================
# GEMINI SECRET
# ============================================================

def get_gemini_api_key():
    """
    Get Gemini API key from Streamlit Secrets.

    Expected format:

    [gemini]
    api_key = "YOUR_KEY"
    """

    try:

        gemini_section = st.secrets.get(
            "gemini",
            {}
        )

        if not gemini_section:
            return None

        api_key = gemini_section.get(
            "api_key"
        )

        if api_key:

            api_key = str(
                api_key
            ).strip()

            if api_key:
                return api_key

    except Exception:
        pass

    return None


# ============================================================
# GEMINI DEFAULT MODEL
# ============================================================

def get_default_model():
    """
    Read the preferred Gemini model from Streamlit Secrets.

    Supported:

    [gemini]
    api_key = "..."
    default_model = "gemini-3.5-flash-lite"

    If default_model is not present, use DEFAULT_MODEL.
    """

    try:

        gemini_section = st.secrets.get(
            "gemini",
            {}
        )

        configured_model = (
            gemini_section.get(
                "default_model"
            )
        )

        if configured_model:

            configured_model = str(
                configured_model
            ).strip()

            if configured_model:
                return configured_model

    except Exception:
        pass

    return DEFAULT_MODEL


# ============================================================
# GEMINI CLIENT
# ============================================================

@st.cache_resource
def get_gemini_client(api_key):
    """
    Create and cache the Gemini client.

    Caching the client avoids recreating it on every Streamlit
    rerun.
    """

    return genai.Client(
        api_key=api_key
    )


# ============================================================
# ERROR HELPERS
# ============================================================

def is_temporary_gemini_error(error):
    """
    Determine whether an error looks like a temporary
    availability/rate-limit/server problem.

    We retry 503 / UNAVAILABLE / RESOURCE EXHAUSTED style
    errors instead of immediately failing.
    """

    message = str(
        error
    ).upper()

    temporary_patterns = [
        "503",
        "UNAVAILABLE",
        "SERVICE UNAVAILABLE",
        "HIGH DEMAND",
        "RESOURCE EXHAUSTED",
        "429",
        "TOO MANY REQUESTS",
        "OVERLOADED",
    ]

    return any(
        pattern in message
        for pattern in temporary_patterns
    )


def clean_json_response(text):
    """
    Clean common Gemini JSON formatting issues.
    """

    if not text:
        return ""

    text = str(
        text
    ).strip()

    # Remove markdown JSON fences.
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

    return text.strip()


# ============================================================
# TOPIC NORMALIZATION
# ============================================================

def normalize_topic(topic):
    """
    Normalize a curriculum topic for local topic detection.
    """

    if topic is None:
        return ""

    topic = str(
        topic
    ).strip().lower()

    topic = re.sub(
        r"\s+",
        " ",
        topic
    )

    return topic


# ============================================================
# TOPIC CATEGORY DETECTION
# ============================================================

def detect_topic_category(topic):
    """
    Determine the EXACT topic-specific visualization category.

    IMPORTANT:
    A broad subject such as "geometry" or "statistics" is NOT
    enough to trigger a visualization.

    Only topics with a specifically supported visualization
    category will return a visualization category.

    If the topic is not specifically supported, return "general".
    """

    t = normalize_topic(topic)

    # --------------------------------------------------------
    # PYTHAGOREAN THEOREM
    # Check BEFORE general geometry.
    # --------------------------------------------------------

    if any(
        phrase in t
        for phrase in [
            "pythagorean theorem",
            "pythagorean",
            "right triangle theorem",
        ]
    ):
        return "pythagorean"

    # --------------------------------------------------------
    # SLOPE
    # --------------------------------------------------------

    if any(
        phrase in t
        for phrase in [
            "slope of a line",
            "slope of line",
            "finding slope",
            "find the slope",
            "calculate slope",
            "slope",
            "rate of change",
        ]
    ):
        return "slope"

    # --------------------------------------------------------
    # SLOPE-INTERCEPT FORM
    # --------------------------------------------------------

    if any(
        phrase in t
        for phrase in [
            "slope intercept form",
            "slope-intercept form",
            "y = mx + b",
            "y=mx+b",
        ]
    ):
        return "slope_intercept"

    # --------------------------------------------------------
    # LINEAR EQUATIONS / LINEAR FUNCTIONS
    # --------------------------------------------------------

    if any(
        phrase in t
        for phrase in [
            "linear equation",
            "linear equations",
            "linear function",
            "linear functions",
            "graphing linear equations",
            "graphing linear functions",
        ]
    ):
        return "linear"

    # --------------------------------------------------------
    # QUADRATIC / PARABOLA
    # --------------------------------------------------------

    if any(
        phrase in t
        for phrase in [
            "quadratic function",
            "quadratic functions",
            "graphing quadratic",
            "graphing quadratics",
            "parabola",
            "parabolas",
        ]
    ):
        return "quadratic"

    # --------------------------------------------------------
    # QUADRATIC VERTEX
    # --------------------------------------------------------

    if any(
        phrase in t
        for phrase in [
            "vertex of a quadratic",
            "vertex of a parabola",
            "vertex form",
            "finding the vertex",
            "find the vertex",
        ]
    ):
        return "quadratic_vertex"

    # --------------------------------------------------------
    # QUADRATIC ROOTS / X-INTERCEPTS
    # --------------------------------------------------------

    if any(
        phrase in t
        for phrase in [
            "roots of a quadratic",
            "root of a quadratic",
            "zeros of a quadratic",
            "zero of a quadratic",
            "x-intercepts of a quadratic",
            "x intercepts of a quadratic",
        ]
    ):
        return "quadratic_roots"

    # --------------------------------------------------------
    # FACTORING QUADRATICS
    # --------------------------------------------------------

    if any(
        phrase in t
        for phrase in [
            "factoring quadratic",
            "factor quadratic",
            "factoring quadratics",
            "factor quadratics",
            "quadratic factoring",
        ]
    ):
        return "quadratic_factoring"

    # --------------------------------------------------------
    # EXPONENTIAL GROWTH
    # --------------------------------------------------------

    if any(
        phrase in t
        for phrase in [
            "exponential growth",
            "exponential increase",
            "compound growth",
            "compound interest",
        ]
    ):
        return "exponential_growth"

    # --------------------------------------------------------
    # EXPONENTIAL DECAY
    # --------------------------------------------------------

    if any(
        phrase in t
        for phrase in [
            "exponential decay",
            "exponential decrease",
            "half life",
            "half-life",
        ]
    ):
        return "exponential_decay"

    # --------------------------------------------------------
    # GENERAL EXPONENTIAL FUNCTIONS
    # --------------------------------------------------------

    if any(
        phrase in t
        for phrase in [
            "exponential function",
            "exponential functions",
            "exponential equation",
            "exponential equations",
        ]
    ):
        return "exponential"

    # --------------------------------------------------------
    # LOGARITHMS
    # --------------------------------------------------------

    if any(
        phrase in t
        for phrase in [
            "logarithm",
            "logarithms",
            "log function",
            "logarithmic function",
            "logarithmic functions",
            "natural logarithm",
            "natural logarithms",
        ]
    ):
        return "logarithm"

    # --------------------------------------------------------
    # SINE FUNCTION
    # --------------------------------------------------------

    if any(
        phrase in t
        for phrase in [
            "sine function",
            "sine functions",
            "graphing sine",
            "graph sine",
            "sin function",
            "sinusoidal sine",
        ]
    ):
        return "sine"

    # --------------------------------------------------------
    # COSINE FUNCTION
    # --------------------------------------------------------

    if any(
        phrase in t
        for phrase in [
            "cosine function",
            "cosine functions",
            "graphing cosine",
            "graph cosine",
            "cos function",
        ]
    ):
        return "cosine"

    # --------------------------------------------------------
    # UNIT CIRCLE
    # --------------------------------------------------------

    if any(
        phrase in t
        for phrase in [
            "unit circle",
            "unit circle values",
            "unit circle angles",
        ]
    ):
        return "unit_circle"

    # --------------------------------------------------------
    # GENERAL TRIGONOMETRY
    #
    # We intentionally DO NOT visualize generic "trigonometry".
    # --------------------------------------------------------

    # --------------------------------------------------------
    # CONDITIONAL PROBABILITY
    # --------------------------------------------------------

    if any(
        phrase in t
        for phrase in [
            "conditional probability",
            "conditional probabilities",
        ]
    ):
        return "conditional_probability"

    # --------------------------------------------------------
    # PROBABILITY
    # Only visualize if the topic explicitly involves
    # probability distributions / outcomes.
    # --------------------------------------------------------

    if any(
        phrase in t
        for phrase in [
            "probability distribution",
            "probability distributions",
            "theoretical probability",
            "experimental probability",
        ]
    ):
        return "probability"

    # --------------------------------------------------------
    # MEAN / MEDIAN / MODE
    # --------------------------------------------------------

    if any(
        phrase in t
        for phrase in [
            "mean median mode",
            "mean, median, and mode",
            "mean median and mode",
        ]
    ):
        return "central_tendency"

    # --------------------------------------------------------
    # STANDARD DEVIATION
    # --------------------------------------------------------

    if any(
        phrase in t
        for phrase in [
            "standard deviation",
            "standard deviations",
        ]
    ):
        return "standard_deviation"

    # --------------------------------------------------------
    # NORMAL DISTRIBUTION
    # --------------------------------------------------------

    if any(
        phrase in t
        for phrase in [
            "normal distribution",
            "normal distributions",
            "bell curve",
            "bell-shaped distribution",
        ]
    ):
        return "normal_distribution"

    # --------------------------------------------------------
    # ARITHMETIC SEQUENCE
    # --------------------------------------------------------

    if any(
        phrase in t
        for phrase in [
            "arithmetic sequence",
            "arithmetic sequences",
            "arithmetic progression",
        ]
    ):
        return "arithmetic_sequence"

    # --------------------------------------------------------
    # GEOMETRIC SEQUENCE
    # --------------------------------------------------------

    if any(
        phrase in t
        for phrase in [
            "geometric sequence",
            "geometric sequences",
            "geometric progression",
        ]
    ):
        return "geometric_sequence"

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Do NOT return a broad visualization category for:
    #
    # geometry
    # triangle
    # circles
    # angles
    # statistics
    # probability
    # trigonometry
    #
    # unless specifically handled above.
    # --------------------------------------------------------

    return "general"

# ============================================================
# VISUALIZATION DECISION
# ============================================================

def should_visualize(topic):
    """
    Return True only when detect_topic_category()
    identifies a specifically supported visualization.

    Broad or unsupported topics return False.

    This keeps visualization decisions synchronized with
    detect_topic_category().
    """

    if not topic:
        return False

    category = detect_topic_category(topic)

    supported_categories = [
        "slope",
        "slope_intercept",

        "linear",

        "quadratic",
        "quadratic_vertex",
        "quadratic_roots",
        "quadratic_factoring",

        "exponential",
        "exponential_growth",
        "exponential_decay",

        "logarithm",

        "sine",
        "cosine",
        "unit_circle",

        "pythagorean",

        "conditional_probability",
        "probability",

        "central_tendency",
        "standard_deviation",
        "normal_distribution",

        "arithmetic_sequence",
        "geometric_sequence",
    ]

    return category in supported_categories


# ============================================================
# AI PROMPT
# ============================================================

def build_learning_prompt(
    curriculum_topic,
    homework_title="",
    instructions="",
    student_grade=""
):
    """
    Build a concise prompt for Gemini.

    Important:
    Gemini is asked to produce theory/reference content.

    Visualization selection is handled locally.
    """

    topic = (
        str(
            curriculum_topic or ""
        ).strip()
    )

    title = (
        str(
            homework_title or ""
        ).strip()
    )

    instruction_text = (
        str(
            instructions or ""
        ).strip()
    )

    grade = (
        str(
            student_grade or ""
        ).strip()
    )

    return f"""
You are an expert mathematics teacher creating a short learning
reference for a student.

Create a concise, student-friendly reference for the topic:

CURRICULUM TOPIC:
{topic}

HOMEWORK:
{title}

STUDENT GRADE:
{grade}

HOMEWORK INSTRUCTIONS:
{instruction_text}

The student is asking for help understanding the topic while
working independently.

Do NOT solve the student's specific homework assignment.

Instead, teach the underlying mathematical concept.

The response must be useful for a student who wants a quick
reference without searching the internet.

Return ONLY valid JSON with exactly these fields:

{{
  "topic": "short topic name",
  "summary": "2-4 sentence explanation",
  "key_ideas": [
    "important idea 1",
    "important idea 2",
    "important idea 3"
  ],
  "steps": [
    "step 1",
    "step 2",
    "step 3",
    "step 4"
  ],
  "worked_example": {{
    "problem": "a representative example",
    "solution": [
      "step-by-step solution"
    ],
    "answer": "final answer"
  }},
  "common_mistakes": [
    "common mistake 1",
    "common mistake 2",
    "common mistake 3"
  ],
  "tip": "one short teacher-style tip"
}}

Keep the explanation appropriate for the student's grade.

Use correct mathematical terminology.

Use concise language.

Do not include markdown code fences.

Do not include HTML.

Do not include an interactive visualization in the JSON.
"""


# ============================================================
# GEMINI REQUEST
# ============================================================

def call_gemini(
    client,
    model,
    prompt
):
    """
    Call Gemini.

    The response is requested as JSON.

    This function does not retry.
    Retry logic is handled by generate_learning_reference()
    so that the same model can be retried cleanly.
    """

    response = client.models.generate_content(

        model=model,

        contents=prompt,

        config=types.GenerateContentConfig(

            temperature=TEMPERATURE,

            max_output_tokens=MAX_OUTPUT_TOKENS,

            response_mime_type="application/json"
        )
    )

    return response


# ============================================================
# PARSE GEMINI RESULT
# ============================================================

def parse_gemini_result(response):
    """
    Convert Gemini response into a Python dictionary.
    """

    if response is None:

        raise ValueError(
            "Gemini returned an empty response."
        )

    text = getattr(
        response,
        "text",
        None
    )

    if not text:

        raise ValueError(
            "Gemini returned no text."
        )

    text = clean_json_response(
        text
    )

    try:

        result = json.loads(
            text
        )

    except json.JSONDecodeError as e:

        raise ValueError(
            f"Gemini returned invalid JSON: {e}"
        )

    if not isinstance(
        result,
        dict
    ):

        raise ValueError(
            "Gemini response was not a JSON object."
        )

    return result


# ============================================================
# NORMALIZE RESULT
# ============================================================

def normalize_learning_result(result):
    """
    Ensure all expected fields exist.

    This prevents UI errors if Gemini returns a slightly
    incomplete response.
    """

    if not isinstance(
        result,
        dict
    ):

        result = {}

    result.setdefault(
        "topic",
        ""
    )

    result.setdefault(
        "summary",
        ""
    )

    result.setdefault(
        "key_ideas",
        []
    )

    result.setdefault(
        "steps",
        []
    )

    result.setdefault(
        "worked_example",
        {}
    )

    result.setdefault(
        "common_mistakes",
        []
    )

    result.setdefault(
        "tip",
        ""
    )

    if not isinstance(
        result["key_ideas"],
        list
    ):

        result["key_ideas"] = [
            str(
                result["key_ideas"]
            )
        ]

    if not isinstance(
        result["steps"],
        list
    ):

        result["steps"] = [
            str(
                result["steps"]
            )
        ]

    if not isinstance(
        result["common_mistakes"],
        list
    ):

        result["common_mistakes"] = [
            str(
                result["common_mistakes"]
            )
        ]

    if not isinstance(
        result["worked_example"],
        dict
    ):

        result["worked_example"] = {}

    result["worked_example"].setdefault(
        "problem",
        ""
    )

    result["worked_example"].setdefault(
        "solution",
        []
    )

    result["worked_example"].setdefault(
        "answer",
        ""
    )

    if not isinstance(
        result["worked_example"]["solution"],
        list
    ):

        result["worked_example"]["solution"] = [
            str(
                result["worked_example"]["solution"]
            )
        ]

    return result


# ============================================================
# GENERATE LEARNING REFERENCE
# ============================================================

def generate_learning_reference(
    curriculum_topic,
    homework_title="",
    instructions="",
    student_grade=""
):
    """
    Main public function used by the Student Portal.

    One user click normally results in:
        1 Gemini request

    Temporary 503:
        retry SAME model

    Only if those retries fail:
        try fallback model(s)

    Visualization:
        generated locally
        no second Gemini request
    """

    api_key = get_gemini_api_key()

    if not api_key:

        return {
            "success": False,
            "error": (
                "Gemini API key was not found in Streamlit Secrets. "
                "Please check the [gemini] api_key setting."
            )
        }

    topic = (
        str(
            curriculum_topic or ""
        ).strip()
    )

    if not topic:

        return {
            "success": False,
            "error": (
                "No curriculum topic was provided."
            )
        }

    try:

        client = get_gemini_client(
            api_key
        )

    except Exception as e:

        return {
            "success": False,
            "error": (
                f"Unable to initialize Gemini: {e}"
            )
        }

    prompt = build_learning_prompt(

        curriculum_topic=topic,

        homework_title=homework_title,

        instructions=instructions,

        student_grade=student_grade
    )

    default_model = get_default_model()

    # --------------------------------------------------------
    # MODEL ORDER
    # --------------------------------------------------------

    models_to_try = []

    if default_model:

        models_to_try.append(
            default_model
        )

    for fallback in FALLBACK_MODELS:

        if fallback not in models_to_try:

            models_to_try.append(
                fallback
            )

    last_error = None

    # ========================================================
    # TRY MODELS
    # ========================================================

    for model_index, model in enumerate(
        models_to_try
    ):

        # ----------------------------------------------------
        # Same-model retry loop
        # ----------------------------------------------------

        attempts = SAME_MODEL_RETRIES + 1

        for attempt in range(
            attempts
        ):

            try:

                response = call_gemini(

                    client=client,

                    model=model,

                    prompt=prompt
                )

                result = parse_gemini_result(
                    response
                )

                result = normalize_learning_result(
                    result
                )

                # ------------------------------------------------
                # LOCAL VISUALIZATION DECISION
                # ------------------------------------------------

                category = detect_topic_category(
                    topic
                )

                result["visualization"] = {

                    "enabled": should_visualize(
                        topic
                    ),

                    "category": category,

                    "topic": topic
                }

                result["model"] = model

                result["success"] = True

                return result

            except Exception as e:

                last_error = e

                # ------------------------------------------------
                # Temporary error
                # ------------------------------------------------

                if is_temporary_gemini_error(
                    e
                ):

                    # If retries remain, retry SAME model.
                    if attempt < attempts - 1:

                        delay_index = min(
                            attempt,
                            len(RETRY_DELAYS) - 1
                        )

                        delay = RETRY_DELAYS[
                            delay_index
                        ]

                        time.sleep(
                            delay
                        )

                        continue

                    # Same model exhausted.
                    break

                # ------------------------------------------------
                # Non-temporary error
                # ------------------------------------------------

                break

        # --------------------------------------------------------
        # Move to fallback model.
        #
        # We only arrive here after the current model's retry
        # attempts are exhausted.
        # --------------------------------------------------------

        continue

    # ========================================================
    # ALL MODELS FAILED
    # ========================================================

    error_text = str(
        last_error
        or "Unknown Gemini error."
    )

    return {
        "success": False,
        "error": (
            "Gemini could not create the learning reference. "
            f"Last error: {error_text}"
        )
    }


# ============================================================
# LOCAL VISUALIZATION HELPERS
# ============================================================

def _add_axis_titles(
    fig,
    x_title="x",
    y_title="y"
):
    """
    Apply consistent Plotly axis labels.
    """

    fig.update_layout(

        xaxis_title=x_title,

        yaxis_title=y_title,

        height=420,

        margin=dict(
            l=40,
            r=20,
            t=50,
            b=40
        ),

        hovermode="x unified"
    )

    return fig


# ============================================================
# LINEAR VISUALIZATION
# ============================================================

def create_linear_visualization(topic):
    """
    Visualize y = 2x + 1.

    This gives students an intuitive connection between
    slope and intercept.
    """

    x = list(
        range(-10, 11)
    )

    y = [
        2 * value + 1
        for value in x
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="lines+markers",
            name="y = 2x + 1"
        )
    )

    fig.update_layout(
        title="Linear Relationship",
        xaxis_title="x",
        yaxis_title="y",
        height=420,
        margin=dict(
            l=40,
            r=20,
            t=50,
            b=40
        )
    )

    return fig


# ============================================================
# QUADRATIC VISUALIZATION
# ============================================================

def create_quadratic_visualization(topic):
    """
    Visualize a basic parabola.
    """

    x = [
        -5 + i * 0.1
        for i in range(101)
    ]

    y = [
        value ** 2
        for value in x
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="lines",
            name="y = x²"
        )
    )

    fig.update_layout(
        title="Quadratic Function",
        xaxis_title="x",
        yaxis_title="y",
        height=420,
        margin=dict(
            l=40,
            r=20,
            t=50,
            b=40
        )
    )

    return fig


# ============================================================
# EXPONENTIAL GROWTH
# ============================================================

def create_exponential_growth_visualization(topic):

    x = [
        i / 5
        for i in range(0, 31)
    ]

    y = [
        2 ** value
        for value in x
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="lines",
            name="y = 2ˣ"
        )
    )

    fig.update_layout(
        title="Exponential Growth",
        xaxis_title="x",
        yaxis_title="y",
        height=420,
        margin=dict(
            l=40,
            r=20,
            t=50,
            b=40
        )
    )

    return fig


# ============================================================
# EXPONENTIAL DECAY
# ============================================================

def create_exponential_decay_visualization(topic):

    x = [
        i / 5
        for i in range(0, 31)
    ]

    y = [
        100 * (0.5 ** value)
        for value in x
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="lines",
            name="Decay"
        )
    )

    fig.update_layout(
        title="Exponential Decay",
        xaxis_title="Time",
        yaxis_title="Amount",
        height=420,
        margin=dict(
            l=40,
            r=20,
            t=50,
            b=40
        )
    )

    return fig


# ============================================================
# TRIGONOMETRY VISUALIZATION
# ============================================================

def create_trigonometry_visualization(topic):

    import math

    angles = [
        i
        for i in range(
            0,
            361,
            5
        )
    ]

    radians = [
        math.radians(
            angle
        )
        for angle in angles
    ]

    sine_values = [
        math.sin(
            angle
        )
        for angle in radians
    ]

    cosine_values = [
        math.cos(
            angle
        )
        for angle in radians
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=angles,
            y=sine_values,
            mode="lines",
            name="sin θ"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=angles,
            y=cosine_values,
            mode="lines",
            name="cos θ"
        )
    )

    fig.update_layout(
        title="Sine and Cosine",
        xaxis_title="Angle (degrees)",
        yaxis_title="Value",
        height=420,
        margin=dict(
            l=40,
            r=20,
            t=50,
            b=40
        )
    )

    return fig


# ============================================================
# GEOMETRY VISUALIZATION
# ============================================================

def create_geometry_visualization(topic):

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=[
                0,
                4,
                2,
                0
            ],
            y=[
                0,
                0,
                3,
                0
            ],
            mode="lines+markers",
            fill="toself",
            name="Triangle"
        )
    )

    fig.update_layout(
        title="Triangle Geometry",
        xaxis_title="x",
        yaxis_title="y",
        height=420,
        yaxis=dict(
            scaleanchor="x",
            scaleratio=1
        ),
        margin=dict(
            l=40,
            r=20,
            t=50,
            b=40
        )
    )

    return fig


# ============================================================
# PYTHAGOREAN VISUALIZATION
# ============================================================

def create_pythagorean_visualization(topic):

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=[
                0,
                3,
                0,
                0
            ],
            y=[
                0,
                0,
                4,
                0
            ],
            mode="lines+markers",
            fill="toself",
            name="3-4-5 triangle"
        )
    )

    fig.update_layout(
        title="Pythagorean Theorem",
        xaxis_title="x",
        yaxis_title="y",
        height=420,
        yaxis=dict(
            scaleanchor="x",
            scaleratio=1
        ),
        margin=dict(
            l=40,
            r=20,
            t=50,
            b=40
        )
    )

    return fig


# ============================================================
# STATISTICS VISUALIZATION
# ============================================================

def create_statistics_visualization(topic):

    values = [
        62,
        68,
        70,
        71,
        72,
        73,
        75,
        76,
        77,
        79,
        82,
        88
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Box(
            x=values,
            name="Distribution",
            boxpoints="all",
            jitter=0.35,
            pointpos=0
        )
    )

    fig.update_layout(
        title="Understanding Data Spread",
        xaxis_title="Value",
        height=420,
        margin=dict(
            l=40,
            r=20,
            t=50,
            b=40
        )
    )

    return fig


# ============================================================
# PROBABILITY VISUALIZATION
# ============================================================

def create_probability_visualization(topic):

    outcomes = [
        "A",
        "B",
        "C",
        "D",
        "E",
        "F"
    ]

    probabilities = [
        1 / 6
        for _ in outcomes
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=outcomes,
            y=probabilities,
            name="Probability"
        )
    )

    fig.update_layout(
        title="Equal Probability Outcomes",
        xaxis_title="Outcome",
        yaxis_title="Probability",
        height=420,
        margin=dict(
            l=40,
            r=20,
            t=50,
            b=40
        )
    )

    return fig


# ============================================================
# SEQUENCE VISUALIZATION
# ============================================================

def create_sequence_visualization(topic):

    n = list(
        range(
            1,
            11
        )
    )

    values = [
        3 * value + 1
        for value in n
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=n,
            y=values,
            mode="lines+markers",
            name="Arithmetic sequence"
        )
    )

    fig.update_layout(
        title="Arithmetic Sequence",
        xaxis_title="Term number",
        yaxis_title="Term value",
        height=420,
        margin=dict(
            l=40,
            r=20,
            t=50,
            b=40
        )
    )

    return fig


# ============================================================
# LOGARITHM VISUALIZATION
# ============================================================

def create_logarithm_visualization(topic):

    import math

    x = [
        0.1 + i * 0.1
        for i in range(100)
    ]

    y = [
        math.log(
            value,
            10
        )
        for value in x
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="lines",
            name="log₁₀(x)"
        )
    )

    fig.update_layout(
        title="Logarithmic Function",
        xaxis_title="x",
        yaxis_title="log₁₀(x)",
        height=420,
        margin=dict(
            l=40,
            r=20,
            t=50,
            b=40
        )
    )

    return fig

# ============================================================
# SLOPE VISUALIZATION
# ============================================================

def create_slope_visualization(topic):
    """
    Show a line with a clear rise/run relationship.

    y = 2x + 1
    slope = 2 = rise/run = 2/1
    """

    x = list(range(-5, 6))

    y = [
        2 * value + 1
        for value in x
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="lines+markers",
            name="y = 2x + 1"
        )
    )

    # Rise/run triangle
    fig.add_trace(
        go.Scatter(
            x=[0, 1, 1],
            y=[1, 1, 3],
            mode="lines+markers",
            name="Rise / Run"
        )
    )

    fig.update_layout(
        title="Slope: Rise Over Run",
        xaxis_title="x",
        yaxis_title="y",
        height=420,
        margin=dict(
            l=40,
            r=20,
            t=50,
            b=40
        )
    )

    return fig


# ============================================================
# SLOPE-INTERCEPT VISUALIZATION
# ============================================================

def create_slope_intercept_visualization(topic):
    """
    Illustrate y = mx + b.
    """

    x = list(range(-5, 6))

    y = [
        2 * value + 3
        for value in x
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="lines+markers",
            name="y = 2x + 3"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[0],
            y=[3],
            mode="markers+text",
            text=["b = 3"],
            textposition="top right",
            name="y-intercept"
        )
    )

    fig.update_layout(
        title="Slope-Intercept Form: y = mx + b",
        xaxis_title="x",
        yaxis_title="y",
        height=420,
        margin=dict(
            l=40,
            r=20,
            t=50,
            b=40
        )
    )

    return fig


# ============================================================
# QUADRATIC VERTEX VISUALIZATION
# ============================================================

def create_quadratic_vertex_visualization(topic):
    """
    Show a parabola with its vertex highlighted.
    """

    x = [
        -5 + i * 0.1
        for i in range(101)
    ]

    y = [
        (value - 1) ** 2 - 4
        for value in x
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="lines",
            name="y = (x - 1)² - 4"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[1],
            y=[-4],
            mode="markers+text",
            text=["Vertex (1, -4)"],
            textposition="top center",
            name="Vertex"
        )
    )

    fig.update_layout(
        title="Quadratic Vertex",
        xaxis_title="x",
        yaxis_title="y",
        height=420,
        margin=dict(
            l=40,
            r=20,
            t=50,
            b=40
        )
    )

    return fig


# ============================================================
# QUADRATIC ROOTS VISUALIZATION
# ============================================================

def create_quadratic_roots_visualization(topic):
    """
    Show a parabola and its x-intercepts.
    """

    x = [
        -4 + i * 0.1
        for i in range(81)
    ]

    y = [
        (value - 1) ** 2 - 4
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

    fig.add_trace(
        go.Scatter(
            x=[-1, 3],
            y=[0, 0],
            mode="markers+text",
            text=["x = -1", "x = 3"],
            textposition="top center",
            name="Roots"
        )
    )

    fig.update_layout(
        title="Quadratic Roots / X-Intercepts",
        xaxis_title="x",
        yaxis_title="y",
        height=420,
        margin=dict(
            l=40,
            r=20,
            t=50,
            b=40
        )
    )

    return fig


# ============================================================
# QUADRATIC FACTORING VISUALIZATION
# ============================================================

def create_quadratic_factoring_visualization(topic):
    """
    Connect factoring to the zeros of a quadratic.

    y = (x - 2)(x + 3)
    roots: x = 2 and x = -3
    """

    x = [
        -5 + i * 0.1
        for i in range(101)
    ]

    y = [
        (value - 2) * (value + 3)
        for value in x
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="lines",
            name="(x - 2)(x + 3)"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[-3, 2],
            y=[0, 0],
            mode="markers+text",
            text=["x = -3", "x = 2"],
            textposition="top center",
            name="Zeros"
        )
    )

    fig.update_layout(
        title="Factoring a Quadratic and Its Zeros",
        xaxis_title="x",
        yaxis_title="y",
        height=420,
        margin=dict(
            l=40,
            r=20,
            t=50,
            b=40
        )
    )

    return fig


# ============================================================
# SINE VISUALIZATION
# ============================================================

def create_sine_visualization(topic):

    import math

    angles = list(
        range(
            0,
            361,
            5
        )
    )

    values = [
        math.sin(
            math.radians(angle)
        )
        for angle in angles
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=angles,
            y=values,
            mode="lines",
            name="sin θ"
        )
    )

    fig.update_layout(
        title="Sine Function",
        xaxis_title="Angle (degrees)",
        yaxis_title="sin θ",
        height=420,
        margin=dict(
            l=40,
            r=20,
            t=50,
            b=40
        )
    )

    return fig


# ============================================================
# COSINE VISUALIZATION
# ============================================================

def create_cosine_visualization(topic):

    import math

    angles = list(
        range(
            0,
            361,
            5
        )
    )

    values = [
        math.cos(
            math.radians(angle)
        )
        for angle in angles
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=angles,
            y=values,
            mode="lines",
            name="cos θ"
        )
    )

    fig.update_layout(
        title="Cosine Function",
        xaxis_title="Angle (degrees)",
        yaxis_title="cos θ",
        height=420,
        margin=dict(
            l=40,
            r=20,
            t=50,
            b=40
        )
    )

    return fig


# ============================================================
# UNIT CIRCLE VISUALIZATION
# ============================================================

def create_unit_circle_visualization(topic):

    import math

    angles = [
        i
        for i in range(
            0,
            361,
            2
        )
    ]

    radians = [
        math.radians(
            angle
        )
        for angle in angles
    ]

    x = [
        math.cos(angle)
        for angle in radians
    ]

    y = [
        math.sin(angle)
        for angle in radians
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="lines",
            name="Unit Circle"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[0, 1],
            y=[0, 0],
            mode="lines+markers",
            name="Radius"
        )
    )

    fig.update_layout(
        title="Unit Circle",
        xaxis_title="cos θ",
        yaxis_title="sin θ",
        height=420,
        yaxis=dict(
            scaleanchor="x",
            scaleratio=1
        ),
        margin=dict(
            l=40,
            r=20,
            t=50,
            b=40
        )
    )

    return fig


# ============================================================
# TOPIC-SPECIFIC VISUALIZATION DISPATCHER
# ============================================================

def create_topic_visualization(topic):
    """
    Create a visualization ONLY when the curriculum topic
    has an explicitly supported visualization category.

    IMPORTANT:
    This function does NOT guess.

    The topic is first classified by detect_topic_category().
    Only an exact supported category is allowed to produce
    a visualization.

    Unsupported or broad topics return None.
    """

    category = detect_topic_category(
        topic
    )

    # --------------------------------------------------------
    # No specific visualization
    # --------------------------------------------------------

    if category == "general":

        return None

    # --------------------------------------------------------
    # LINEAR
    # --------------------------------------------------------

    if category == "linear":

        return create_linear_visualization(
            topic
        )

    # --------------------------------------------------------
    # SLOPE
    # --------------------------------------------------------

    if category == "slope":

        return create_slope_visualization(
            topic
        )

    # --------------------------------------------------------
    # SLOPE-INTERCEPT FORM
    # --------------------------------------------------------

    if category == "slope_intercept":

        return create_slope_intercept_visualization(
            topic
        )

    # --------------------------------------------------------
    # QUADRATIC
    # --------------------------------------------------------

    if category == "quadratic":

        return create_quadratic_visualization(
            topic
        )

    # --------------------------------------------------------
    # QUADRATIC VERTEX
    # --------------------------------------------------------

    if category == "quadratic_vertex":

        return create_quadratic_vertex_visualization(
            topic
        )

    # --------------------------------------------------------
    # QUADRATIC ROOTS
    # --------------------------------------------------------

    if category == "quadratic_roots":

        return create_quadratic_roots_visualization(
            topic
        )

    # --------------------------------------------------------
    # QUADRATIC FACTORING
    # --------------------------------------------------------

    if category == "quadratic_factoring":

        return create_quadratic_factoring_visualization(
            topic
        )

    # --------------------------------------------------------
    # EXPONENTIAL
    # --------------------------------------------------------

    if category == "exponential":

        return create_exponential_growth_visualization(
            topic
        )

    # --------------------------------------------------------
    # EXPONENTIAL GROWTH
    # --------------------------------------------------------

    if category == "exponential_growth":

        return create_exponential_growth_visualization(
            topic
        )

    # --------------------------------------------------------
    # EXPONENTIAL DECAY
    # --------------------------------------------------------

    if category == "exponential_decay":

        return create_exponential_decay_visualization(
            topic
        )

    # --------------------------------------------------------
    # LOGARITHM
    # --------------------------------------------------------

    if category == "logarithm":

        return create_logarithm_visualization(
            topic
        )

    # --------------------------------------------------------
    # SINE
    # --------------------------------------------------------

    if category == "sine":

        return create_sine_visualization(
            topic
        )

    # --------------------------------------------------------
    # COSINE
    # --------------------------------------------------------

    if category == "cosine":

        return create_cosine_visualization(
            topic
        )

    # --------------------------------------------------------
    # UNIT CIRCLE
    # --------------------------------------------------------

    if category == "unit_circle":

        return create_unit_circle_visualization(
            topic
        )

    # --------------------------------------------------------
    # PYTHAGOREAN THEOREM
    # --------------------------------------------------------

    if category == "pythagorean":

        return create_pythagorean_visualization(
            topic
        )

    # --------------------------------------------------------
    # CONDITIONAL PROBABILITY
    # --------------------------------------------------------

    if category == "conditional_probability":

        return create_probability_visualization(
            topic
        )

    # --------------------------------------------------------
    # PROBABILITY
    # --------------------------------------------------------

    if category == "probability":

        return create_probability_visualization(
            topic
        )

    # --------------------------------------------------------
    # CENTRAL TENDENCY
    # --------------------------------------------------------

    if category == "central_tendency":

        return create_statistics_visualization(
            topic
        )

    # --------------------------------------------------------
    # STANDARD DEVIATION
    # --------------------------------------------------------

    if category == "standard_deviation":

        return create_statistics_visualization(
            topic
        )

    # --------------------------------------------------------
    # NORMAL DISTRIBUTION
    # --------------------------------------------------------

    if category == "normal_distribution":

        return create_statistics_visualization(
            topic
        )

    # --------------------------------------------------------
    # ARITHMETIC SEQUENCE
    # --------------------------------------------------------

    if category == "arithmetic_sequence":

        return create_sequence_visualization(
            topic
        )

    # --------------------------------------------------------
    # GEOMETRIC SEQUENCE
    # --------------------------------------------------------

    if category == "geometric_sequence":

        return create_sequence_visualization(
            topic
        )

    # --------------------------------------------------------
    # SAFETY FALLBACK
    #
    # If a category is added to detect_topic_category()
    # later but a visualization has not yet been created,
    # return None rather than showing an unrelated graph.
    # --------------------------------------------------------

    return None

# ============================================================
# TOPIC VISUALIZATION DISPATCHER
# ============================================================

def create_topic_visualization(topic):
    """
    Create a visualization ONLY when the curriculum topic
    has an explicitly supported topic category.

    IMPORTANT:
    - No generic visualization is created.
    - Broad topics return None.
    - The visualization is selected from the locally
      detected topic category.
    """

    category = detect_topic_category(topic)

    # --------------------------------------------------------
    # Unsupported / broad topic
    # --------------------------------------------------------

    if category == "general":
        return None

    # --------------------------------------------------------
    # LINEAR
    # --------------------------------------------------------

    if category == "linear":
        return create_linear_visualization(topic)

    # --------------------------------------------------------
    # SLOPE
    # --------------------------------------------------------

    if category == "slope":
        return create_slope_visualization(topic)

    # --------------------------------------------------------
    # SLOPE-INTERCEPT FORM
    # --------------------------------------------------------

    if category == "slope_intercept":
        return create_slope_intercept_visualization(topic)

    # --------------------------------------------------------
    # QUADRATIC
    # --------------------------------------------------------

    if category == "quadratic":
        return create_quadratic_visualization(topic)

    # --------------------------------------------------------
    # QUADRATIC VERTEX
    # --------------------------------------------------------

    if category == "quadratic_vertex":
        return create_quadratic_vertex_visualization(topic)

    # --------------------------------------------------------
    # QUADRATIC ROOTS
    # --------------------------------------------------------

    if category == "quadratic_roots":
        return create_quadratic_roots_visualization(topic)

    # --------------------------------------------------------
    # QUADRATIC FACTORING
    # --------------------------------------------------------

    if category == "quadratic_factoring":
        return create_quadratic_factoring_visualization(topic)

    # --------------------------------------------------------
    # EXPONENTIAL
    # --------------------------------------------------------

    if category == "exponential":
        return create_exponential_growth_visualization(topic)

    # --------------------------------------------------------
    # EXPONENTIAL GROWTH
    # --------------------------------------------------------

    if category == "exponential_growth":
        return create_exponential_growth_visualization(topic)

    # --------------------------------------------------------
    # EXPONENTIAL DECAY
    # --------------------------------------------------------

    if category == "exponential_decay":
        return create_exponential_decay_visualization(topic)

    # --------------------------------------------------------
    # LOGARITHM
    # --------------------------------------------------------

    if category == "logarithm":
        return create_logarithm_visualization(topic)

    # --------------------------------------------------------
    # SINE
    # --------------------------------------------------------

    if category == "sine":
        return create_sine_visualization(topic)

    # --------------------------------------------------------
    # COSINE
    # --------------------------------------------------------

    if category == "cosine":
        return create_cosine_visualization(topic)

    # --------------------------------------------------------
    # UNIT CIRCLE
    # --------------------------------------------------------

    if category == "unit_circle":
        return create_unit_circle_visualization(topic)

    # --------------------------------------------------------
    # PYTHAGOREAN THEOREM
    # --------------------------------------------------------

    if category == "pythagorean":
        return create_pythagorean_visualization(topic)

    # --------------------------------------------------------
    # PROBABILITY
    # --------------------------------------------------------

    if category == "probability":
        return create_probability_visualization(topic)

    # --------------------------------------------------------
    # CONDITIONAL PROBABILITY
    #
    # No dedicated visualization function currently exists.
    # Therefore DO NOT create a generic probability graph.
    # --------------------------------------------------------

    if category == "conditional_probability":
        return None

    # --------------------------------------------------------
    # STATISTICS
    # --------------------------------------------------------
    # These topics currently do NOT have dedicated
    # topic-specific visualizations.
    #
    # Do NOT use the generic box plot because it does not
    # specifically teach mean/median/mode, standard deviation,
    # or normal distribution.
    # --------------------------------------------------------

    if category == "central_tendency":
        return None

    if category == "standard_deviation":
        return None

    if category == "normal_distribution":
        return None
        
    # --------------------------------------------------------
    # SEQUENCES
    # --------------------------------------------------------

    if category == "arithmetic_sequence":
        return create_sequence_visualization(topic)

    # --------------------------------------------------------
    # GEOMETRIC SEQUENCE
    #
    # No dedicated geometric-sequence visualization currently
    # exists, so do NOT substitute an arithmetic sequence graph.
    # --------------------------------------------------------

    if category == "geometric_sequence":
        return None

    # --------------------------------------------------------
    # SAFETY FALLBACK
    # --------------------------------------------------------

    return None


# ============================================================
# DISPLAY LEARNING REFERENCE
# ============================================================

def display_learning_reference(
    result
):
    """
    Display the AI Learning Reference.

    This function is compatible with the existing
    homework.py / student.py implementation.
    """

    if not result:

        return

    if not result.get(
        "success",
        True
    ):

        st.error(
            result.get(
                "error",
                "Unable to display learning reference."
            )
        )

        return

    # ========================================================
    # TOPIC
    # ========================================================

    topic = result.get(
        "topic",
        ""
    )

    if topic:

        st.markdown(
            f"### 📖 {topic}"
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    summary = result.get(
        "summary",
        ""
    )

    if summary:

        st.markdown(
            "#### 💡 Key Idea"
        )

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
            "#### 🔑 Key Ideas"
        )

        for idea in key_ideas:

            st.markdown(
                f"- {idea}"
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
            "#### 🧭 How to Approach It"
        )

        for number, step in enumerate(
            steps,
            start=1
        ):

            st.markdown(
                f"**{number}.** {step}"
            )

    # ========================================================
    # WORKED EXAMPLE
    # ========================================================

    worked_example = result.get(
        "worked_example",
        {}
    )

    if worked_example:

        problem = worked_example.get(
            "problem",
            ""
        )

        solution = worked_example.get(
            "solution",
            []
        )

        answer = worked_example.get(
            "answer",
            ""
        )

        if problem:

            st.markdown(
                "#### ✏️ Worked Example"
            )

            st.markdown(
                f"**Example:** {problem}"
            )

        if solution:

            for number, step in enumerate(
                solution,
                start=1
            ):

                st.markdown(
                    f"**Step {number}:** {step}"
                )

        if answer:

            st.success(
                f"**Answer:** {answer}"
            )

    # ========================================================
    # COMMON MISTAKES
    # ========================================================

    common_mistakes = result.get(
        "common_mistakes",
        []
    )

    if common_mistakes:

        st.markdown(
            "#### ⚠️ Common Mistakes"
        )

        for mistake in common_mistakes:

            st.markdown(
                f"- {mistake}"
            )

    # ========================================================
    # TEACHER TIP
    # ========================================================

    tip = result.get(
        "tip",
        ""
    )

    if tip:

        st.markdown(
            "#### 👨‍🏫 Quick Tip"
        )

        st.warning(
            tip
        )

    # ========================================================
    # VISUALIZATION
    # ========================================================

    visualization = result.get(
        "visualization",
        {}
    )

    visualization_enabled = (
        visualization.get(
            "enabled",
            False
        )
    )

    visualization_topic = (
        visualization.get(
            "topic",
            topic
        )
    )

    if visualization_enabled:

        st.markdown(
            "#### 📊 Interactive Visualization"
        )

        st.caption(
            "Use the graph to connect the concept "
            "to its visual meaning."
        )

        fig = create_topic_visualization(
            visualization_topic
        )

        if fig is not None:

            st.plotly_chart(
                fig,
                use_container_width=True,
                key=(
                    "learning_visualization_"
                    + re.sub(
                        r"[^a-zA-Z0-9]+",
                        "_",
                        visualization_topic
                    )[:60]
                )
            )

        else:

            st.caption(
                "A visualization is not available "
                "for this topic yet."
            )

    # ========================================================
    # MODEL INFORMATION
    # ========================================================

    model = result.get(
        "model"
    )

    if model:

        with st.expander(
            "ℹ️ Reference Information"
        ):

            st.caption(
                f"AI model: {model}"
            )
