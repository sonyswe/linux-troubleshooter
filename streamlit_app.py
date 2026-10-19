from pathlib import Path
import streamlit as st

st.set_page_config(
    page_title="Linux Troubleshooting AI Assistant",
    page_icon="🐧",
    layout="wide",
)

st.title("🐧 Linux Troubleshooting AI Assistant")
st.write("Ask questions about Linux, services, networking, and DevOps.")

st.info(
    "Recruiter Demo Mode: This version works without Ollama "
    "or a database. Answers are predefined troubleshooting guidance."
)

answers = {
    "nginx": """
### Troubleshooting Nginx
