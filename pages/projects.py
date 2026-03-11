import os
import streamlit as st
from src.core.session import get_user_id

user_id = get_user_id()
base_path = f"data/user_{user_id}"
os.makedirs(base_path, exist_ok=True)

st.header("📁 Projects")

project_name = st.text_input("Project name", key="project_name")
created = st.button("Create")

if created and project_name:
    os.makedirs(f"{base_path}/{project_name}", exist_ok=True)

projects = os.listdir(base_path)
selected = st.selectbox("Select project", projects)

st.session_state["current_project"] = selected
