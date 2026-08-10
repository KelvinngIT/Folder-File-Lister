import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import os
from io import BytesIO

st.set_page_config(
    page_title="Folder File Lister → Excel",
    page_icon="📁",
    layout="wide"
)

st.title("📁 Folder File Lister → Excel")
st.markdown("Enter a target folder path → list all files → download as Excel")

# ---------- Important notice ----------
st.info(
    """
    **Important:** This app can only access folders on the computer where it is running.
    
    - To scan folders on **your own computer**, you must run it locally:
      ```bash
      streamlit run app.py
