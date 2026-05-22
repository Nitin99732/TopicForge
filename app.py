# Libraries
import streamlit as st
import os 

from backend.agent import processing, retrieval_node

uploaded_file = st.file_uploader("Uploaded File", type=["pdf", "txt", "docx"], max_upload_size=1)

if uploaded_file is not None:

    # Create uploads folder
    os.makedirs("uploads", exist_ok=True)

    # Create file path
    file_path = os.path.join("uploads", uploaded_file.name)

    # Save uploaded file
    with open(file_path, "wb") as f:

        f.write(uploaded_file.getbuffer())

    # Initial workflow state
    state = {
        "file_path" : file_path, 
        "file_type" : os.path.splitext(uploaded_file.name)[1]
    }

    # Run backend validation 
    updated_state = processing(state)

    

    # Suggested Topics
    st.subheader("Suggested Topics")

    st.write(updated_state["suggested_topics"])

    # User Selected Topic/SubTopic
    selected_topic = st.text_input("Enter your topic or subtopic: ")

    # Run Retrieval Only After Selection
    if selected_topic:

        updated_state["selected_topic_or_subtopic"] = selected_topic

        updated_state = retrieval_node(updated_state)

        st.success("Relevant Chunks Retrieved.")