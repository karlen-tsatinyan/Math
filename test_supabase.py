import streamlit as st
from supabase import create_client


st.title("Supabase Storage Connection Test")


try:

    # -----------------------------------------
    # Get Supabase credentials
    # -----------------------------------------

    supabase_url = st.secrets["supabase"]["url"]
    supabase_key = st.secrets["supabase"]["key"]

    # -----------------------------------------
    # Create Supabase client
    # -----------------------------------------

    supabase = create_client(
        supabase_url,
        supabase_key
    )

    st.success("✅ Supabase client connected successfully.")

    # -----------------------------------------
    # Test Storage
    # -----------------------------------------

    buckets = supabase.storage.list_buckets()

    st.success("✅ Supabase Storage connection works.")

    st.subheader("Available Storage Buckets")

    if buckets:

        for bucket in buckets:

            st.write(
                f"📦 {bucket.name}"
            )

    else:

        st.warning(
            "No Storage buckets were found."
        )

    # -----------------------------------------
    # Check homework-files bucket
    # -----------------------------------------

    homework_bucket = None

    for bucket in buckets:

        if bucket.name == "homework-files":

            homework_bucket = bucket
            break

    if homework_bucket:

        st.success(
            "✅ homework-files bucket was found!"
        )

    else:

        st.error(
            "❌ homework-files bucket was NOT found."
        )


except Exception as e:

    st.error(
        "❌ Supabase connection test failed."
    )

    st.exception(e)
