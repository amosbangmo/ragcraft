from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk_text(text: str, source: str):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150
    )
    docs = splitter.create_documents(
        [text],
        metadatas=[{"source": source}]
    )
    for doc in docs[0:5]:
        print("Chunk : " + doc.page_content)    
    return docs
