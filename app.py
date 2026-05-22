# Libraries

import streamlit as st
import os

from backend.agent import processing, retrieval_node


# File uploader
uploaded_file = st.file_uploader("Upload File", type=["pdf", "txt", "docx"])

# Run only after upload
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

        "file_path": file_path,

        "file_type": os.path.splitext(uploaded_file.name)[1]
    }

    # Process document
    updated_state = processing(state)

    # Validation failure
    if updated_state["validation_status"] == "failed":

        st.error(updated_state["validation_reason"])

    else:

        st.success("Document Processed Successfully")

        # Suggested Topics
        st.subheader("Suggested Topics")

        st.write(updated_state["suggested_topics"])

        # User topic selection
        selected_topic = st.text_input("Enter your topic or subtopic: ")

        # Retrieval button
        if st.button("Retrieve Relevant Chunks"):

            # Store selected topic
            updated_state[
                "selected_topic_or_subtopic"
            ] = selected_topic

            # Run retrieval
            updated_state = retrieval_node(updated_state)

            st.success("Relevant Chunks Retrieved")

            # Question type selection
            question_type = st.selectbox("Select Question Type", ["MCQ", "Theory"])

            # Store question type
            if question_type == "MCQ":

                updated_state["selected_questions_type"] = "mcq"

            else:

                updated_state["selected_questions_type"] = "theory"

            # Display selected type
            st.write("Selected Question Type:", updated_state["selected_questions_type"])
