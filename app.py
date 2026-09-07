import streamlit as st


# ============================================================
# IMPORTS
# ============================================================

from src.load_and_chunk import (
    process_all_pdfs,
    chunk_documnents
)

from src.embedding import EmbeddingManager
from src.vectorstore import VectorStore


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="RAG Chatbot",
    page_icon="🤖",
    layout="wide"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 40px;
        font-weight: 700;
        text-align: center;
        margin-bottom: 5px;
    }

    .subtitle {
        text-align: center;
        color: #888888;
        margin-bottom: 30px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SESSION STATE
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "rag_trained" not in st.session_state:
    st.session_state.rag_trained = False


# ============================================================
# CACHE EMBEDDING MANAGER
# ============================================================

@st.cache_resource
def get_embedding_manager():

    print("====================================")
    print("Loading Embedding Manager...")
    print("====================================")

    embedding_manager = EmbeddingManager()

    print("Embedding Manager Loaded!")

    return embedding_manager


# ============================================================
# CACHE VECTOR STORE
# ============================================================

@st.cache_resource
def get_vectorstore():

    print("====================================")
    print("Loading Vector Store...")
    print("====================================")

    vectorstore = VectorStore()

    print("Vector Store Loaded!")

    return vectorstore


# ============================================================
# CACHE RAG BOT
# ============================================================

@st.cache_resource
def get_rag_bot():

    print("====================================")
    print("Loading RAG Bot...")
    print("====================================")

    # Import only when required
    from src.search import RagBot

    print("RAG Bot Loaded!")

    return RagBot


# ============================================================
# TRAIN RAG
# ============================================================

def train_rag():

    with st.status(
        "Training RAG...",
        expanded=True
    ) as status:

        # ----------------------------------------------------
        # STEP 1: LOAD PDF DOCUMENTS
        # ----------------------------------------------------

        st.write("📄 Loading PDF documents...")

        try:

            all_documents = process_all_pdfs(
                "./data"
            )

        except Exception as e:

            status.update(
                label="Failed to load PDFs",
                state="error"
            )

            st.error(
                f"PDF loading error: {e}"
            )

            return False


        st.write(
            f"✅ Documents loaded: {len(all_documents)}"
        )


        # ----------------------------------------------------
        # STEP 2: CHUNK DOCUMENTS
        # ----------------------------------------------------

        st.write(
            "✂️ Splitting documents into chunks..."
        )

        try:

            all_chunks = chunk_documnents(
                all_documents
            )

        except Exception as e:

            status.update(
                label="Failed during chunking",
                state="error"
            )

            st.error(
                f"Chunking error: {e}"
            )

            return False


        st.write(
            f"✅ Chunks created: {len(all_chunks)}"
        )


        # ----------------------------------------------------
        # STEP 3: EXTRACT TEXT
        # ----------------------------------------------------

        texts = [
            doc.page_content
            for doc in all_chunks
        ]


        if not texts:

            status.update(
                label="No text found",
                state="error"
            )

            st.error(
                "No text was extracted from the PDFs."
            )

            return False


        # ----------------------------------------------------
        # STEP 4: GET EMBEDDING MANAGER
        # ----------------------------------------------------

        st.write(
            "🧠 Loading embedding model..."
        )

        try:

            embedding_manager = (
                get_embedding_manager()
            )

        except Exception as e:

            status.update(
                label="Embedding model failed",
                state="error"
            )

            st.error(
                f"Embedding model error: {e}"
            )

            return False


        # ----------------------------------------------------
        # STEP 5: GENERATE EMBEDDINGS
        # ----------------------------------------------------

        st.write(
            "🧠 Generating embeddings..."
        )

        try:

            all_embeddings = (
                embedding_manager.genetate_embedding(
                    texts
                )
            )

        except Exception as e:

            status.update(
                label="Embedding generation failed",
                state="error"
            )

            st.error(
                f"Embedding generation error: {e}"
            )

            return False


        st.write(
            "✅ Embeddings generated"
        )


        # ----------------------------------------------------
        # STEP 6: GET VECTOR STORE
        # ----------------------------------------------------

        st.write(
            "💾 Loading vector store..."
        )

        try:

            vectorstore = get_vectorstore()

        except Exception as e:

            status.update(
                label="Vector store failed",
                state="error"
            )

            st.error(
                f"Vector store error: {e}"
            )

            return False


        # ----------------------------------------------------
        # STEP 7: STORE DOCUMENTS
        # ----------------------------------------------------

        st.write(
            "💾 Adding documents to vector store..."
        )

        try:

            vectorstore.add_documents(
                all_chunks,
                all_embeddings
            )

        except Exception as e:

            status.update(
                label="Failed to store documents",
                state="error"
            )

            st.error(
                f"Vector store error: {e}"
            )

            return False


        # ----------------------------------------------------
        # COMPLETE
        # ----------------------------------------------------

        status.update(
            label="RAG training completed!",
            state="complete"
        )


        return True


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ RAG Settings")

    st.divider()


    # --------------------------------------------------------
    # RAG STATUS
    # --------------------------------------------------------

    st.subheader("RAG Status")

    if st.session_state.rag_trained:

        st.success(
            "🟢 RAG is ready"
        )

    else:

        st.info(
            "🔵 RAG is not trained"
        )


    st.divider()


    # --------------------------------------------------------
    # TRAIN RAG
    # --------------------------------------------------------

    if st.button(
        "🧠 Train / Rebuild RAG",
        use_container_width=True
    ):

        success = train_rag()

        if success:

            st.session_state.rag_trained = True

            st.success(
                "RAG training completed!"
            )


    st.divider()


    # --------------------------------------------------------
    # CLEAR CHAT
    # --------------------------------------------------------

    if st.button(
        "🗑️ Clear Chat",
        use_container_width=True
    ):

        st.session_state.messages = []

        st.rerun()


    # --------------------------------------------------------
    # CLEAR CACHE
    # --------------------------------------------------------

    if st.button(
        "🔄 Clear Model Cache",
        use_container_width=True
    ):

        st.cache_resource.clear()

        st.session_state.rag_trained = False

        st.success(
            "Cache cleared!"
        )

        st.rerun()


# ============================================================
# MAIN HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🤖 RAG Chatbot</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Ask questions about your PDF documents'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# DISPLAY CHAT HISTORY
# ============================================================

for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


# ============================================================
# CHAT INPUT
# ============================================================

query = st.chat_input(
    "Ask something about your documents..."
)


# ============================================================
# HANDLE USER QUERY
# ============================================================

if query:

    # --------------------------------------------------------
    # DISPLAY USER MESSAGE
    # --------------------------------------------------------

    st.session_state.messages.append(
        {
            "role": "user",
            "content": query
        }
    )


    with st.chat_message("user"):

        st.markdown(query)


    # --------------------------------------------------------
    # RAG RESPONSE
    # --------------------------------------------------------

    with st.chat_message("assistant"):

        with st.spinner(
            "🔍 Searching your knowledge base..."
        ):

            try:

                # Get cached RAG bot
                rag_bot = get_rag_bot()

                # Run RAG
                answer = rag_bot(query)

                # Display answer
                st.markdown(answer)

                # Save response
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer
                    }
                )


            except Exception as e:

                error_message = (
                    f"❌ Something went wrong:\n\n{str(e)}"
                )

                st.error(
                    error_message
                )

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": error_message
                    }
                )