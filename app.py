"""
Streamlit web interface for CompuMax Local Hybrid GraphRAG System.
"""
import streamlit as st
import os
import tempfile
import logging
import asyncio
from typing import List, Callable, Optional

from ingest import Ingestor
from search import SearchEngine
from streamlit_agraph import agraph, Node, Edge, Config
from config import settings


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# Custom Styling for "Premium" feel
st.set_page_config(
    page_title="CompuMax GraphRAG", 
    page_icon="🌐",
    layout="wide"
)

st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .sidebar .sidebar-content {
        background-image: linear-gradient(#2e3440, #4c566a);
        color: white;
    }
    h1 {
        color: #1e3a8a;
        font-family: 'Inter', sans-serif;
    }
    .st-emotion-cache-v0 {
        border-radius: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🌐 CompuMax Local Hybrid GraphRAG System 2025")
st.markdown("""
    ---
    Transform static documents into dynamic, interconnected knowledge. 
    Combining **Vector Semantic Search** with **Graph Relational Context**.
    """)


# Helper for running async functions
def run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        # If loop is already running (e.g. inside another async context), 
        # we might need to use existing loop.
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)


@st.cache_resource
def get_ingestor():
    """Get cached ingestor instance."""
    return Ingestor()


@st.cache_resource
def get_search_engine():
    """Get cached search engine instance."""
    return SearchEngine()


# Initialize components
ingestor = get_ingestor()
search_engine = get_search_engine()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# Sidebar for information and file upload
with st.sidebar:
    st.title("⚙️ System Status")
    chat_model = getattr(settings, "DEEPSEEK_MODEL_CHAT", "deepseek-chat (default)")
    st.info(f"**API Provider:** DeepSeek\n\n**Chat Model:** `{chat_model}`")
    
    # Database Stats
    if st.button("Refresh Stats"):
        try:
            async def get_stats():
                driver = await search_engine.db.get_neo4j_driver()
                async with driver.session() as session:
                    nodes_res = await session.run("MATCH (n) RETURN count(n) as count")
                    n_rec = await nodes_res.single()
                    nodes_count = n_rec["count"] if n_rec else 0
                    
                    rels_res = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
                    r_rec = await rels_res.single()
                    rels_count = r_rec["count"] if r_rec else 0
                return nodes_count, rels_count

            nodes_count, rels_count = run_async(get_stats())
            st.success(f"📊 **Database Stats:**\n- Nodes: `{nodes_count}`\n- Relationships: `{rels_count}`")
        except Exception as e:
            st.error("Could not connect to Knowledge Graph for stats")
            logger.error("Could not connect to Knowledge Graph for stats", exc_info=e)
    
    st.divider()
    
    st.header("📁 Document Ingestion")
    uploaded_files = st.file_uploader(
        "Upload Documents (PDF, DOCX, XLSX, CSV, TXT)", 
        accept_multiple_files=True,
        type=[ext.lstrip('.') for ext in settings.ALLOWED_FILE_EXTENSIONS]
    )
    
    if st.button("🚀 Process Documents") and uploaded_files:
        # Validate files
        valid_files = []
        for uploaded_file in uploaded_files:
            # Check extension
            ext = os.path.splitext(uploaded_file.name)[1].lower()
            if ext not in settings.ALLOWED_FILE_EXTENSIONS:
                st.warning(f"Skipping {uploaded_file.name}: unsupported extension {ext}")
                continue
            # Check size (max 100 MB)
            max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
            if uploaded_file.size > max_size:
                st.warning(f"Skipping {uploaded_file.name}: file size exceeds {settings.MAX_UPLOAD_SIZE_MB} MB")
                continue
            valid_files.append(uploaded_file)
        
        if not valid_files:
            st.error("No valid files to process")
        else:
            with st.status("Processing documents...", expanded=True) as status:
                for file_idx, uploaded_file in enumerate(valid_files):
                    st.write(f"File {file_idx+1}/{len(valid_files)}: Processing `{uploaded_file.name}`...")
                    # Save to temp file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    
                    # Create progress elements for this file
                    chunk_progress_bar = st.progress(0)
                    batch_info = st.empty()
                    
                    def create_progress_callback(progress_bar, info_placeholder, filename):
                        def callback(progress_data):
                            if "total_chunks" in progress_data and "chunks_processed" in progress_data:
                                # Update progress bar
                                total = progress_data["total_chunks"]
                                processed = progress_data["chunks_processed"]
                                if total > 0:
                                    progress_bar.progress(processed / total)
                                # Update batch info
                                batch_num = progress_data.get("current_batch", 0)
                                total_batches = progress_data.get("total_batches", 1)
                                batch_size = progress_data.get("batch_size", 0)
                                info_text = f"Batch {batch_num}/{total_batches} ({batch_size} chunks)"
                                if "duration" in progress_data:
                                    info_text += f" | {progress_data['duration']:.2f}s ({progress_data.get('chunks_per_second', 0):.1f} chunks/s)"
                                info_placeholder.markdown(info_text)
                            elif "error" in progress_data:
                                info_placeholder.error(f"Error in batch {progress_data.get('batch_index', '?')}: {progress_data['error']}")
                        return callback
                    
                    progress_callback = create_progress_callback(chunk_progress_bar, batch_info, uploaded_file.name)
                    
                    try:
                        # Async process with progress callback
                        run_async(ingestor.process_file(tmp_path, progress_callback))
                        st.success(f"Finished `{uploaded_file.name}`")
                    except Exception as e:
                        st.error(f"Error processing `{uploaded_file.name}`: {e}")
                        logger.error(f"Error processing file {uploaded_file.name}", exc_info=e)
                    finally:
                        # Clean up progress elements
                        chunk_progress_bar.empty()
                        batch_info.empty()
                        try:
                            os.unlink(tmp_path)
                        except:
                            pass
                status.update(label="Ingestion Complete!", state="complete", expanded=False)

    if st.button("🗑️ Reset Databases", type="secondary"):
        if st.checkbox("Confirm deletion of ALL data?"):
            try:
                async def reset_db():
                    # Reset PG
                    pool = await search_engine.db.get_pg_pool()
                    async with pool.acquire() as conn:
                        await conn.execute("TRUNCATE TABLE chunks RESTART IDENTITY")
                    
                    # Reset Neo4j
                    driver = await search_engine.db.get_neo4j_driver()
                    async with driver.session() as session:
                        await session.run("MATCH (n) DETACH DELETE n")

                run_async(reset_db())
                st.success("All data cleared successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error resetting: {e}")
                logger.error("Error resetting database", exc_info=e)


# Main area with Tabs
tab1, tab2 = st.tabs(["💬 Chat", "🕸️ Knowledge Graph"])

with tab1:
    st.header("Chat with your Knowledge Base")
    
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask a question about your documents..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Searching and generating answer..."):
                try:
                    # Async search
                    result = run_async(search_engine.hybrid_search(prompt))
                    answer = result["answer"]
                    sources = result["sources"]
                    
                    # Show search metadata
                    with st.expander("🔍 Search Details (Hybrid)"):
                        st.write(f"**Search Type:** `Hybrid (Vector + Graph)`")
                        st.write(f"**Vector Chunks Found:** `{sources['vector_count']}`")
                        st.write(f"**Graph Relationships Found:** `{sources['graph_count']}`")
                        st.write(f"**Entities Extracted:** `{', '.join(sources['entities_found'])}`")
                    
                    st.markdown(answer)
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})
                except Exception as e:
                    st.error(f"Error during search: {e}")
                    logger.error("Error during search", exc_info=e)

with tab2:
    st.header("Knowledge Graph Visualization")
    if st.button("🔄 Refresh Graph"):
        st.rerun()

    with st.spinner("Loading graph data..."):
        try:
            nodes_data, edges_data = run_async(search_engine.get_all_graph_data())
            
            if not nodes_data:
                st.info("No data in the Knowledge Graph yet. Upload documents to see the graph!")
            else:
                nodes = [Node(id=n["id"], label=n["label"], size=25, color="#007bff") for n in nodes_data]
                edges = [Edge(source=e["source"], label=e["label"], target=e["target"]) for e in edges_data]
                
                config = Config(
                    width=1000, 
                    height=600, 
                    directed=True, 
                    nodeHighlightBehavior=True, 
                    highlightColor="#F7A7A6",
                    collapsible=True,
                    node={'labelProperty': 'label'},
                    link={'labelProperty': 'label', 'renderLabel': True}
                )
                
                agraph(nodes=nodes, edges=edges, config=config)
        except Exception as e:
             st.error(f"Error loading graph: {e}")

# Cleanup (not strictly necessary as session state manages objects, but good practice if convenient)