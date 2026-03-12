def get_retriever(vector_store):
    if vector_store is None:
        return None

    return vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 4}
    )