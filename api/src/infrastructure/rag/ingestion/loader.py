from pathlib import Path


def save_uploaded_file(uploaded_file, project_path: str) -> str:
    file_path = Path(project_path) / uploaded_file.name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return str(file_path)
