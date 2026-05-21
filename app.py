# Libraries
import streamlit as st
import os 

from backend.agent import document_validation_node

uploaded_file = st.file_uploader("Uploaded File", type=["pdf", "txt", "docx"], max_upload_size=10)

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
    updated_state = document_validation_node(state)

    # Show result 
    if updated_state["validation_status"] == "success":

        st.success("Document validation successful.")

        st.write(updated_state)

    else:

        st.error(updated_state["validation_reason"])