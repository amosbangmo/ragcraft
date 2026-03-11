from dotenv import load_dotenv
import os
from langchain_openai import OpenAIEmbeddings

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is missing")

EMBEDDINGS = OpenAIEmbeddings(api_key=OPENAI_API_KEY)