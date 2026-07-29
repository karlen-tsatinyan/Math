```python
import streamlit as st
from supabase import create_client


st.title("Supabase Storage Connection Test")


try:

    # =========================================================
    # GET SUPABASE CREDENTIALS
    # =========================================================

    supabase_url = st.secrets["supabase"]["url"]
    supabase_key = st.secrets["supabase"]["key"]

    # =========================================================
    # CREATE SUPABASE CLIENT
    # =========================================================

    supabase = create_client(
        supabase_url,
        supabase_key
    )

    st.success("✅ Supabase client connected successfully.")

    # =========================================================
    # CONNECT DIRECTLY TO HOMEWORK BUCKET
    # =========================================================

    bucket = supabase.storage.from_("homework-files")

    st.success("✅ homework-files bucket connection works.")

    # =========================================================
    # TEST PUBLIC URL GENERATION
    # =========================================================

    test_path = "test/connection-test.txt"

    public_url = bucket.get_public_url(
        test_path
    )

    st.success("✅ Supabase Storage public URL generation works.")

    st.write("Test URL:")
    st.code(public_url)

    st.info(
        "The bucket connection is working. "
        "We have not uploaded a real homework file yet."
    )


except Exception as e:

    st.error(
        "❌ Supabase Storage connection test failed."
    )

    st.exception(e)
```
