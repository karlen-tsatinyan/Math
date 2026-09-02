import hashlib
import secrets
from datetime import datetime, timedelta

from database import query_dataframe, execute


# ==========================================================
# REMEMBER-ME SETTINGS
# ==========================================================

REMEMBER_ME_DAYS = 30


# ==========================================================
# INTERNAL TOKEN HASH
# ==========================================================

def _hash_token(token):
    """
    Hash the browser token before storing it in the database.

    The actual token is never stored in the database.
    """

    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


# ==========================================================
# BUILD USER
# ==========================================================

def _build_user(username, role, student_id):
    """
    Build the same user structure used by the existing portal.
    """

    user = {
        "username": username,
        "role": role,
        "student_id": student_id
    }

    # ------------------------------------------------------
    # ADMIN
    # ------------------------------------------------------

    if role == "admin":

        user["courses"] = []
        user["selected_course"] = None

        return user

    # ------------------------------------------------------
    # STUDENT COURSES
    # ------------------------------------------------------

    if student_id is None:

        user["courses"] = []
        user["selected_course"] = None

        return user

    course_query = """
        SELECT
            subject
        FROM students
        WHERE id = %s
        LIMIT 1
    """

    student_result = query_dataframe(
        course_query,
        (student_id,)
    )

    courses = []

    if not student_result.empty:

        subject = student_result.iloc[0]["subject"]

        if subject is not None:

            subject_text = str(subject).strip()

            if (
                subject_text
                and subject_text.lower()
                not in [
                    "nan",
                    "none",
                    "null"
                ]
            ):

                courses = [
                    course.strip()
                    for course in subject_text.split(",")
                    if course.strip()
                    and course.strip().lower()
                    not in [
                        "nan",
                        "none",
                        "null"
                    ]
                ]

    # ------------------------------------------------------
    # REMOVE DUPLICATES
    # ------------------------------------------------------

    courses = list(
        dict.fromkeys(courses)
    )

    user["courses"] = courses

    if len(courses) == 1:

        user["selected_course"] = courses[0]

    else:

        user["selected_course"] = None

    return user


# ==========================================================
# NORMAL LOGIN
# ==========================================================

def login(username, password):

    if username is None:
        return None

    username = str(username).strip()

    if not username or not password:
        return None

    # ======================================================
    # FIND USER
    # ======================================================

    query = """
        SELECT
            u.username,
            u.role,
            u.student_id
        FROM users u
        WHERE LOWER(TRIM(u.username)) = LOWER(TRIM(%s))
          AND u.password = %s
        LIMIT 1
    """

    result = query_dataframe(
        query,
        (
            username,
            password
        )
    )

    # ======================================================
    # INVALID LOGIN
    # ======================================================

    if result.empty:
        return None

    # ======================================================
    # BUILD USER
    # ======================================================

    return _build_user(
        username=result.iloc[0]["username"],
        role=result.iloc[0]["role"],
        student_id=result.iloc[0]["student_id"]
    )


# ==========================================================
# CREATE REMEMBER-ME TOKEN
# ==========================================================

def create_login_token(user):
    """
    Create a secure random browser login token.

    The raw token is returned to app.py so it can be placed
    in the browser cookie.

    Only the SHA-256 hash is stored in PostgreSQL.
    """

    if not user:
        return None

    username = user.get("username")

    if not username:
        return None

    # ------------------------------------------------------
    # Generate cryptographically secure random token
    # ------------------------------------------------------

    token = secrets.token_urlsafe(48)

    token_hash = _hash_token(token)

    expires_at = (
        datetime.utcnow()
        + timedelta(days=REMEMBER_ME_DAYS)
    )

    # ------------------------------------------------------
    # Remove old expired/revoked tokens for this username
    # ------------------------------------------------------

    try:

        execute(
            """
            DELETE FROM login_tokens
            WHERE username = %s
              AND (
                    expires_at < CURRENT_TIMESTAMP
                    OR revoked_at IS NOT NULL
                  )
            """,
            (username,)
        )

    except Exception:
        pass

    # ------------------------------------------------------
    # Store token hash
    # ------------------------------------------------------

    execute(
        """
        INSERT INTO login_tokens (
            username,
            token_hash,
            expires_at
        )
        VALUES (
            %s,
            %s,
            %s
        )
        """,
        (
            username,
            token_hash,
            expires_at
        )
    )

    return token


# ==========================================================
# RESTORE USER FROM REMEMBER-ME TOKEN
# ==========================================================

def login_from_token(token):
    """
    Validate a persistent browser token and rebuild the user.

    Returns:
        user dictionary
        or None if the token is invalid/expired/revoked
    """

    if not token:
        return None

    try:

        token = str(token).strip()

        if not token:
            return None

        token_hash = _hash_token(token)

        result = query_dataframe(
            """
            SELECT
                username,
                expires_at
            FROM login_tokens
            WHERE token_hash = %s
              AND revoked_at IS NULL
              AND expires_at > CURRENT_TIMESTAMP
            LIMIT 1
            """,
            (token_hash,)
        )

        if result.empty:
            return None

        username = result.iloc[0]["username"]

        # --------------------------------------------------
        # Re-read current user information.
        #
        # This is important because role/student/course
        # information may have changed since the cookie
        # was created.
        # --------------------------------------------------

        user_result = query_dataframe(
            """
            SELECT
                username,
                role,
                student_id
            FROM users
            WHERE LOWER(TRIM(username))
                = LOWER(TRIM(%s))
            LIMIT 1
            """,
            (username,)
        )

        if user_result.empty:
            return None

        user = _build_user(
            username=user_result.iloc[0]["username"],
            role=user_result.iloc[0]["role"],
            student_id=user_result.iloc[0]["student_id"]
        )

        return user

    except Exception:
        return None


# ==========================================================
# REVOKE ONE LOGIN TOKEN
# ==========================================================

def revoke_login_token(token):
    """
    Revoke only the current browser/device token.
    """

    if not token:
        return

    try:

        token_hash = _hash_token(
            str(token).strip()
        )

        execute(
            """
            UPDATE login_tokens
            SET revoked_at = CURRENT_TIMESTAMP
            WHERE token_hash = %s
            """,
            (token_hash,)
        )

    except Exception:
        pass


# ==========================================================
# REVOKE ALL TOKENS FOR USER
# ==========================================================

def revoke_all_login_tokens(username):
    """
    Optional helper.

    This can be used later if you want an administrator to
    force a user to log in again on every device.
    """

    if not username:
        return

    try:

        execute(
            """
            UPDATE login_tokens
            SET revoked_at = CURRENT_TIMESTAMP
            WHERE LOWER(TRIM(username))
                = LOWER(TRIM(%s))
              AND revoked_at IS NULL
            """,
            (username,)
        )

    except Exception:
        pass


# ==========================================================
# CLEAN EXPIRED TOKENS
# ==========================================================

def cleanup_expired_tokens():
    """
    Remove expired tokens periodically.
    """

    try:

        execute(
            """
            DELETE FROM login_tokens
            WHERE expires_at < CURRENT_TIMESTAMP
               OR revoked_at IS NOT NULL
            """
        )

    except Exception:
        pass
