import streamlit as st
import os
import tempfile
from ingest import Ingestor
from search import SearchEngine
from streamlit_agraph import agraph, Node, Edge, Config

st.set_page_config(page_title="Local Hybrid GraphRAG", layout="wide")

st.title("🌐 CompuMax Local Hybrid GraphRAG System 2025")
st.markdown("Build relationships from your documents and query them with Hybrid (Vector + Graph) Retrieval.")

@st.cache_resource
def get_ingestor():
    return Ingestor()

@st.cache_resource
def get_search_engine():
    return SearchEngine()

# Initialize components
ingestor = get_ingestor()
search_engine = get_search_engine()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Sidebar for information and file upload
with st.sidebar:
    st.title("⚙️ System Status")
    st.info(f"**LLM Model:** `{search_engine.llm_model}`\n\n**Embed Model:** `{search_engine.embed_model}`")
    
    # Database Stats
    try:
        nodes_count, rels_count = 0, 0
        driver = search_engine.db.connect_neo4j()
        with driver.session() as session:
            nodes_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
            rels_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
        st.success(f"📊 **Database Stats:**\n- Nodes: `{nodes_count}`\n- Relationships: `{rels_count}`")
    except:
        st.error("Could not connect to Knowledge Graph for stats")
    st.divider()
    
    st.header("📁 Document Ingestion")
    uploaded_files = st.file_uploader("Upload Documents (PDF, DOCX, XLSX, CSV)", accept_multiple_files=True)
    
    if st.button("🚀 Process Documents") and uploaded_files:
        with st.status("Processing documents...", expanded=True) as status:
            for uploaded_file in uploaded_files:
                st.write(f"Processing `{uploaded_file.name}`...")
                # Save to temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                
                try:
                    ingestor.process_file(tmp_path)
                    st.success(f"Finished `{uploaded_file.name}`")
                except Exception as e:
                    st.error(f"Error processing `{uploaded_file.name}`: {e}")
                finally:
                    os.unlink(tmp_path)
            status.update(label="Ingestion Complete!", state="complete", expanded=False)

    if st.button("🗑️ Reset Databases", type="secondary"):
        if st.checkbox("Confirm deletion of ALL data?"):
            try:
                # Reset PG
                conn = search_engine.db.connect_pg()
                with conn.cursor() as cur:
                    cur.execute("TRUNCATE TABLE chunks RESTART IDENTITY")
                search_engine.db.release_pg(conn)
                
                # Reset Neo4j
                driver = search_engine.db.connect_neo4j()
                with driver.session() as session:
                    session.run("MATCH (n) DETACH DELETE n")
                
                st.success("All data cleared successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error resetting: {e}")

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
                    result = search_engine.hybrid_search(prompt)
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

with tab2:
    st.header("Knowledge Graph Visualization")
    if st.button("🔄 Refresh Graph"):
        st.rerun()

    with st.spinner("Loading graph data..."):
        nodes_data, edges_data = search_engine.get_all_graph_data()
        
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

# Cleanup on app close (if possible) or session end
# Note: Database handles are managed in session state, 
# but permanent close would happen when the process dies.
