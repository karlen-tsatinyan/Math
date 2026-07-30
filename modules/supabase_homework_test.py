import streamlit as st
from supabase_client import get_supabase

st.title("Supabase Homework File Test")

try:
    supabase = get_supabase()

    st.success("✅ Supabase connected")

    # Check bucket
    buckets = supabase.storage.list_buckets()

    bucket_names = [bucket.name for bucket in buckets]

    if "homework-files" in bucket_names:
        st.success("✅ homework-files bucket found")
    else:
        st.error("❌ homework-files bucket NOT found")
        st.stop()

    # Test file
    test_path = "assignments/student_1/2026-07-30_333.pdf"

    st.write("Testing file:")
    st.code(test_path)

    # Direct download through Supabase client
    file_data = (
        supabase
        .storage
        .from_("homework-files")
        .download(test_path)
    )

    st.success(
        f"✅ Supabase downloaded the file successfully: "
        f"{len(file_data):,} bytes"
    )

    st.download_button(
        "📥 Download Test File",
        data=file_data,
        file_name="333.pdf",
        mime="application/pdf",
        key="supabase_direct_download_test"
    )

except Exception as e:
    st.error("❌ Direct Supabase download failed")
    st.exception(e)
