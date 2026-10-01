def index_uploaded_chunks(chunks, embedding_manager, vectorstore, progress_callback=None):
    """Embed and replace only the supplied document chunks."""
    if not chunks:
        return []

    texts = [chunk.page_content for chunk in chunks]
    embeddings = embedding_manager.genetate_embedding(
        texts,
        progress_callback=progress_callback,
    )
    return vectorstore.replace_documents(chunks, embeddings)