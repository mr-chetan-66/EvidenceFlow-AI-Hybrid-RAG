from langchain_groq import ChatGroq
from src.embedding import EmbeddingManager
from src.vectorstore import VectorStore
import os
from dotenv import load_dotenv
load_dotenv()


llm = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name="openai/gpt-oss-20b",
    temperature=0.2,
    max_tokens=1024
)

embedding_manager=EmbeddingManager()
vectorstore=VectorStore()

def RagBot(query):
    query_embedding=embedding_manager.genetate_embedding([query])[0]
    retrive_info=vectorstore.similar_search(query_embedding=query_embedding,n_results=5)
    documents = retrive_info['documents'][0]
    
    prompt = f"""
    You are a helpful question-answering assistant.

    Answer the question using ONLY the context below.

    Rules:
    - Do not use outside knowledge.
    - Do not hallucinate.
    - If the context does not contain the answer, say:
    "I don't have enough information in the provided context."
    - Keep the answer concise and clear.

    Context:
    {documents}

    Question:
    {query}

    Answer:
    """

    response = llm.invoke(prompt)

    return response.content

        