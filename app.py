# Libraries

import streamlit as st
import os

from backend.agent import processing, retrieval_node, mcq_or_theory_ques_gen_node


# Session State Initiaization
if "updated_state" not in st.session_state:

    st.session_state.updated_state = None

if "document_processed" not in st.session_state:

    st.session_state.document_processed = False

if "retrieval_done" not in st.session_state:

    st.session_state.retrieval_done = False

if "question_generated" not in st.session_state:

    st.session_state.question_generated = False



# File uploader
uploaded_file = st.file_uploader("Upload File", type=["pdf", "txt", "docx"])


# Document Processing
if uploaded_file is not None:

    # Process Only Once
    if not st.session_state.document_processed:

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

        # Run Backend Processing
        updated_state = processing(state)

        # Store in Session State
        st.session_state.updated_state = updated_state
        st.session_state.document_processed = True



# MAIN APP FLOW
if st.session_state.document_processed:

    updated_state = st.session_state.updated_state

    # Validation check
    if updated_state["validation_status"] == "failed":

        st.error(updated_state["validation_reason"])

    else:

        st.success("Document Processed Successfully")

        # Suggested Topics
        st.subheader("Suggested Topics")

        st.write(updated_state["suggested_topics"])

        # Topic input
        selected_topic = st.text_input("Enter your topic or subtopic:")

        # RETRIEVAL
        if st.button("Retrieve Relevant Chunks"):

            if selected_topic.strip():

                updated_state["selected_topic_or_subtopic"] = selected_topic

                updated_state = retrieval_node(updated_state)

                # Save updated state
                st.session_state.updated_state = (updated_state)

                st.session_state.retrieval_done = True

            else:

                st.warning("Please enter a topic first.")


        # QUESTION SETTINGS
        if st.session_state.retrieval_done:

            st.success("Relevant Chunks Retrieved")

            # Question type
            question_type = st.selectbox("Select Question Type", ["MCQ", "Theory"])

            if question_type == "MCQ":

                updated_state["selected_questions_type"] = "mcq"

            else:

                updated_state["selected_questions_type"] = "theory"

            # Difficulty
            difficulty = st.selectbox("Select Difficulty", ["easy", "medium", "hard"])

            updated_state["selected_questions_difficulty"] = difficulty

            # QUESTION GENERATION
            if st.button("Generate Question"):

                updated_state = mcq_or_theory_ques_gen_node(updated_state)
             

                # Save generated state
                st.session_state.updated_state = updated_state
              

                st.session_state.question_generated = True

        # DISPLAY QUESTION
        if st.session_state.question_generated:

            updated_state = st.session_state.updated_state

            # Check if question exists
            if "generated_question" in updated_state:

                st.subheader("Generated Question")

                st.write(
                    updated_state["generated_question"]
                )

                # User answer
                user_answer = st.text_input(
                    "Enter your answer"
                )

                # Store answer
                updated_state["user_answer"] = (
                    user_answer
                )

            else:

                st.error(
                    "Question generation failed."
                )