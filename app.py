# Libraries
import streamlit as st
import os

from backend.agent import processing, retrieval_node, mcq_or_theory_ques_gen_node, evaluation_node



# PAGE CONFIG
st.set_page_config(

    page_title="AI Quiz Generator",

    page_icon="🧠",

    layout="centered"
)

# CUSTOM CS
st.markdown(
    """
    <style>

    .main {

        padding-top: 2rem;
    }

    .title {

        text-align: center;

        font-size: 42px;

        font-weight: bold;

        color: #4CAF50;

        margin-bottom: 10px;
    }

    .subtitle {

        text-align: center;

        font-size: 18px;

        color: #BBBBBB;

        margin-bottom: 40px;
    }

    .section-box {

        background-color: #111827;

        padding: 20px;

        border-radius: 15px;

        margin-bottom: 20px;

        border: 1px solid #2d3748;
    }

    .question-box {

        background-color: #1E293B;

        padding: 25px;

        border-radius: 15px;

        margin-top: 20px;

        border-left: 5px solid #4CAF50;
    }

    .evaluation-box {

        background-color: #0F172A;

        padding: 20px;

        border-radius: 15px;

        border-left: 5px solid #38BDF8;

        margin-top: 20px;
    }

    </style>
    """,
    unsafe_allow_html=True
)



# TITLE
st.markdown(

    """
    <div class="title">
        🧠 AI Quiz Generator
    </div>

    <div class="subtitle">
        Generate MCQ and Theory Questions from PDFs using AI
    </div>
    """,

    unsafe_allow_html=True
)

st.divider()



# SESSION STATE
if "updated_state" not in st.session_state:

    st.session_state.updated_state = None

if "document_processed" not in st.session_state:

    st.session_state.document_processed = False

if "retrieval_done" not in st.session_state:

    st.session_state.retrieval_done = False

if "question_generated" not in st.session_state:

    st.session_state.question_generated = False

if "show_evaluation" not in st.session_state:

    st.session_state.show_evaluation = False



# FILE UPLOADER
uploaded_file = st.file_uploader(

    "📄 Upload File",

    type=["pdf", "txt", "docx"], 
    
    max_upload_size=1
)


# DOCUMENT PROCESSING
if uploaded_file is not None:

    if not st.session_state.document_processed:

        os.makedirs("uploads", exist_ok=True)

        file_path = os.path.join("uploads", uploaded_file.name)

        with open(file_path, "wb") as f:

            f.write(uploaded_file.getbuffer())

        state = {

            "file_path": file_path,

            "file_type": os.path.splitext(uploaded_file.name)[1]
        }

        updated_state = processing(state)

        st.session_state.updated_state = updated_state

        st.session_state.document_processed = True


# MAIN FLOW
if st.session_state.document_processed:

    updated_state = st.session_state.updated_state

    # Validation
    if updated_state["validation_status"] == "failed":

        st.error(updated_state["validation_reason"])

    else:

        st.success("✅ Document Processed Successfully")

        # TOPIC SECTION
        st.markdown(
            """
            <div class="section-box">
            <h3>📚 Suggested Topics</h3>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.write(updated_state["suggested_topics"])

        selected_topic = st.text_input(
            "Enter your topic or subtopic:"
        )


        # RETRIEVAL

        if st.button("🔍 Retrieve Relevant Chunks"):

            if selected_topic.strip():

                updated_state["selected_topic_or_subtopic"] = selected_topic

                updated_state = retrieval_node(updated_state)

                st.session_state.updated_state = updated_state

                st.session_state.retrieval_done = True

            else:

                st.warning("Please enter a topic first.")


        # QUESTION SETTINGS
        if st.session_state.retrieval_done:

            st.success("✅ Relevant Chunks Retrieved")

            question_type = st.selectbox("Select Question Type", ["MCQ", "Theory"])

            if question_type == "MCQ":

                updated_state["selected_questions_type"] = "mcq"

            else:

                updated_state["selected_questions_type"] = "theory"

            difficulty = st.selectbox("Select Difficulty", ["easy", "medium", "hard"])

            updated_state["selected_questions_difficulty"] = difficulty

   
            # GENERATE QUESTIONS
            if st.button("🚀 Generate Question"):

                updated_state = mcq_or_theory_ques_gen_node(updated_state)

                st.session_state.updated_state = updated_state

                st.session_state.question_generated = True


        # SHOW QUESTIONS
        if st.session_state.question_generated:

            updated_state = st.session_state.updated_state

            questions = updated_state["generated_questions"]

            current_index = updated_state["current_question_index"]


            # QUIZ COMPLETED
            if current_index >= len(questions):

                st.balloons()

                st.success("🎉 Quiz Completed Successfully!")

                st.metric(

                    "MCQ Score",

                    updated_state.get(
                        "total_mcq_score",
                        0
                    )
                )

                st.metric(

                    "Theory Score",

                    updated_state.get(
                        "total_theory_score",
                        0
                    )
                )

            else:

                current_question = questions[current_index]

      
                # EVALUATION SCREEN
                if st.session_state.show_evaluation:

                    latest_result = updated_state[ "evaluation_results"][-1]

                    st.markdown(

                        """
                        <div class="evaluation-box">

                        <h2>
                        📊 Evaluation Result
                        </h2>

                        </div>
                        """,

                        unsafe_allow_html=True
                    )

                    st.write(
                        "### Score:",
                        latest_result["score"]
                    )

                    st.write(
                        "### Your Answer:",
                        latest_result["user_answer"]
                    )

                    st.write(
                        "### Correct Answer:",
                        latest_result["correct_answer"]
                    )

                    if st.button("➡️ Next Question"):

                        updated_state["current_question_index"] += 1

                        st.session_state.updated_state = updated_state

                        st.session_state.show_evaluation = False

                        st.rerun()

     
                # QUESTION SCREEN
                else:

                    st.markdown(

                        f"""
                        <div class="question-box">

                        <h1>
                        Question {current_index + 1}/{len(questions)}
                        </h1>

                        </div>
                        """,

                        unsafe_allow_html=True
                    )

                    st.write(
                        current_question["question"]
                    )

                    user_answer = st.text_input(

                        "Enter your answer",

                        key=f"user_answer_{current_index}"
                    )

                    if st.button(

                        "✅ Submit Answer",

                        key=f"submit_{current_index}"
                    ):

                        if "ques_history" not in updated_state:

                            updated_state["ques_history"] = []

                        question_data = {

                            "question": current_question["question"],

                            "question_type": current_question["question_type"],

                            "difficulty": current_question["difficulty"],

                            "user_answer": user_answer
                        }

                        # MCQ
                        if current_question["question_type"] == "mcq":

                            question_data["mcq_answer"] = current_question.get(
                                "correct_answer",
                                "Not Found"
                            )

                        # THEORY
                        else:

                            question_data["theory_answer"] = current_question.get(
                                "correct_answer",
                                "Not Found"
                            )

                        updated_state["ques_history"].append(question_data)

                        updated_state = evaluation_node(updated_state)

                        st.session_state.updated_state = updated_state

                        st.session_state.show_evaluation = True

                        st.rerun()