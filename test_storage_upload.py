import streamlit as st
from supabase_client import get_supabase

st.title("🧪 Supabase Storage Upload Test")

try:
    supabase = get_supabase()

    bucket_name = "homework-files"

    st.success("✅ Supabase client connected.")

    test_file = st.file_uploader(
        "Choose a test PDF or image",
        type=["pdf", "jpg", "jpeg", "png"]
    )

    if test_file is not None:

        storage_path = f"test/test_{test_file.name}"

        st.write("Uploading to:")
        st.code(storage_path)

        file_bytes = test_file.getvalue()

        response = (
            supabase.storage
            .from_(bucket_name)
            .upload(
                storage_path,
                file_bytes,
                {
                    "content-type": (
                        test_file.type
                        or "application/octet-stream"
                    },
                    "upsert": "true"
                }
            )
        )

        st.success("✅ Upload completed!")

        st.write("Supabase response:")
        st.write(response)

        st.write("Bucket:")
        st.code(bucket_name)

        st.write("Path:")
        st.code(storage_path)

except Exception as e:

    st.error("❌ Upload failed.")

    st.exception(e)
