
import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("API_KEY")

st.set_page_config(page_title="API Key Debug", layout="wide")
st.title("🔍 Debug: Render Deployment Check")

if api_key:
    st.success("API key loaded successfully!")
    st.code(api_key)
else:
    st.error("❌ API key not found. Check environment variable setup.")
