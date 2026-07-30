import streamlit as st
from supabase import create_client


@st.cache_resource
def get_supabase():
    """
    Create and cache one Supabase client
    for the entire Streamlit application.
    """

    supabase_url = st.secrets["supabase"]["url"]
    supabase_key = st.secrets["supabase"]["key"]

    return create_client(
        supabase_url,
        supabase_key
    )
