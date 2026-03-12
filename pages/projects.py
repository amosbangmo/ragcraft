import streamlit as st
from src.core.session import get_user_id
from src.app.ragcraft_app import RAGCraftApp

app = RAGCraftApp()

user_id = get_user_id()
st.header("📁 Projects")

project_name = st.text_input("Project name", key="project_name")

if st.button("Create") and project_name:
    app.create_project(user_id, project_name)

projects = app.list_projects(user_id)

if projects:
    selected = st.selectbox("Select project", projects)
    st.session_state["project_id"] = selected
else:
    st.info("No project yet.")
