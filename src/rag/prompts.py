from langchain_classic.prompts import PromptTemplate

def get_rag_prompt():

    template = """
You are an AI assistant answering questions using the provided context.

Context:
{context}

Question:
{input}

Instructions:
- Use only the provided context
- If the answer is not in the context, say you don't know
- Provide a clear and concise answer
"""

    prompt = PromptTemplate(
        template=template,
        input_variables=["context", "input"]
    )

    return prompt