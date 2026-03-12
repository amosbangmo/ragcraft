def get_retriever(vector_store, project_id):

    if vector_store is None:
        return None

    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": 4,
            "project_id": project_id
        }
    )

    return retriever