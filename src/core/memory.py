from langchain_classic.memory import ConversationBufferMemory

def create_memory():

    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )

    return memory