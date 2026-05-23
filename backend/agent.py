# Libraries
from typing import TypedDict, Optional, List, Dict

import os

import random

import chromadb

from docx import Document

from uuid import uuid4

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.messages import SystemMessage, HumanMessage

from langgraph.graph import StateGraph, START, END

from IPython.display import Image, display

from dotenv import load_dotenv

from pypdf import PdfReader

load_dotenv()


#LLM 
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Agent State
class AgentState(TypedDict):

    # File
    file_path: Optional[str]
    file_name: Optional[str]
    file_type: Optional[str]

    # Validation
    validation_status: Optional[str]
    validation_reason: Optional[str]

    # Sections
    sections: List[Dict]

    # Chunks
    chunks : List[Dict]

    # Indexing stauts
    indexing_status : str

    # Suggested/Selected Topics or SubTopics
    selected_topic_or_subtopic : Optional[str]
    suggested_topics : Optional[str]

    # Reirieval Chunks
    retrieved_chunks: List[Dict]

    # Selected Questions type
    selected_questions_type : Optional[str]

    # Generated Question
    generated_question: Optional[str]

    # Hidden Correct/Ideal Answer
    correct_answer: Optional[str]

    # User Answer
    user_answer: Optional[str]

    # Selected Question Difficulty
    selected_questions_difficulty: Optional[str]

    # Question History
    ques_history: List[Dict]

    # Evaluation Results
    evaluation_results: List[Dict]

    # Total Score
    total_mcq_score: int
    total_theory_score: int

    
# Document Validation Node
def document_validation_node(state : AgentState) -> AgentState:
    """
    Validates whether uploaded document
    is safe and usable for the RAG pipeline.

    Checks:
    - corrupted PDF
    - encrypted PDF
    - extractable text
    - empty document
    - scanned/image-only PDF
    """

    # Reterive file info from state
    file_path = state["file_path"]
    file_type = state["file_type"]

    # Validates .txt and .docx files
    if file_type in [".txt", ".docx"]:

        state["validation_status"] = "success"
        
        return state
    
    # Validates PDF's
    # Corrupted pdf check
    try:
        # Open pdf
        doc = PdfReader(file_path)

    except Exception:
        state["validation_status"] = "failed"
        state["validation_reason"] = "corrupted_pdf"

        return state
    
    # Encrypted pdf check
    if doc.is_encrypted:
        state["validation_status"] = "failed"
        state["validation_reason"] = "encrypted_pdf"

        return state
    
    # Extract text
    extracted_text = ""

    for page in doc.pages:
        extracted_text += page.extract_text()

    # Empty pdf check
    if len(extracted_text.strip()) == 0:
        state["validation_status"] = "failed"
        state["validation_reason"] = "empty_pdf"

        return state  

    # Scanned/Image only pdf check
    if len(extracted_text.strip()) < 100:
        state["validation_status"] = "failed"
        state["validation_reason"] = "scanned_or_image_only_pdf"

        return state  
    
    # Success
    state["validation_status"] = "success"
    state["validation_reason"] = ""


    return state    
    

 
    
# Document Ingestion Node
def document_ingestion_node(state : AgentState) -> AgentState:
    """
    Extract structured readable content 
    from validate document 

    strategy :-
    - for txt : full text extraction
    - for docx : pagragph based extraction
    - for pdf : page based extraction
    """

    # Retriving document info
    file_path = state["file_path"]
    file_type = state["file_type"]

    sections = []

    # txt text extraction
    if file_type == ".txt":

        with open(file_path, "r", encoding="utf-8") as file:
            
            text = file.read()

        sections.append({
            "page" : 1,
            "text" : text.strip()
        })

    # docx text extraction
    elif file_type == ".docx":

        doc = Document(file_path)

        full_text = ""

        for paragraph in doc.paragraphs:
            
            if paragraph.text.strip():

                full_text += paragraph.text + "\n"

        sections.append({
            "page" : 1,
            "text" : full_text.strip()
        })

    # pdf text extraction
    elif file_type == ".pdf":
        doc = fitz.open(file_path)
 
        for page_number, page in enumerate(doc):
            text = page.get_text()

            if len(text.strip()) == 0:
                continue
        
            sections.append({
                "page" : page_number + 1,
                "text" : text.strip()
            })
            
        doc.close()

    # Store Sections in state
    state["sections"] = sections
    
    return state

        


# Semantic Chunking Node
def semantic_chunking_node(state : AgentState) -> AgentState:
    """
    Converts extracted documetn setions 
    into semantically meaningful chunks.

    Strategy:
    - Recursive semantic splitting
    - Overlap preservation
    - Page tracking
    """

    # Reterive sections info from state
    sections = state["sections"]

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size = 800,
        chunk_overlap = 150,
        length_function = len
    )

    chunks = []

    for section in sections:

        page = section["page"]
        text = section["text"]

        # Skip empty text 
        if len(text.strip()) == 0:
            continue

        # Generate semantic chunks
        split_chunks = text_splitter.split_text(text)

        # Store chunks meta data
        for chunk_order, chunk_text in enumerate(split_chunks):
            chunks.append({
                "chunk_id" : str(uuid4()),
                "page" : page,
                "chunk_order" : chunk_order + 1,
                "text" : chunk_text
            })

    state["chunks"] = chunks

    return state



# Indexing Node
embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")

chroma_client = chromadb.PersistentClient(path = "./chroma_db")

collection = chroma_client.get_or_create_collection(name="educational_chunks")

def indexing_node(state : AgentState) -> AgentState:
    """
    Converts chunks into embeddings 
    and store them in chromadb.
    """

    chunks = state["chunks"]
    
    # Process each chunk
    for chunk in chunks:

        # Reterive info from chunks
        chunk_id = chunk["chunk_id"]
        page = chunk["page"]
        text = chunk["text"]
        chunk_order = chunk["chunk_order"]

        # Generate embeddings
        embedding = embedding_model.embed_query(text)

        # Store in ChromaDB
        collection.add(
            ids = [chunk_id],
            documents = [text],
            embeddings = [embedding],
            metadatas = [{
                "page" : page,
                "chunk_order" : chunk_order
            }]

        )

    # Store Indexing status
    state["indexing_status"] = "success"

    return state


# Topic/SubTopic Suggestions and Selection Node
def topic_suggestion_selection_node(state: AgentState) -> AgentState:
    """
    Generates topic/subtopic names
    from educational material and
    lets user select topic/subtopic.

    Strategies:
    - Random chunk sampling
    - LLM-based topic extraction
    """

    chunks = state["chunks"]

    combined_text = ""

    # Random chunk sampling
    sample_chunks = random.sample(chunks, min(15, len(chunks)))

    for chunk in sample_chunks:

        combined_text += chunk["text"] + "\n\n"

    response = llm.invoke([
        SystemMessage(
            content="""
            You are an educational topic extractor.

            Extract major topics and subtopics
            from provided educational content.
            """
        ),

        HumanMessage(
            content=combined_text
        )
    ])

    # Extract generated topics
    suggested_topics = response.content

    # Store in state
    state["suggested_topics"] = suggested_topics

    return state



# Retrieval Node
def retrieval_node(state : AgentState) -> AgentState:
    """
    Retrieves semantically relevant chunks
    based on selected topic/subtopic.
    """

    # Retrieve selected topic/subtopic
    retrieval_query = state["selected_topic_or_subtopic"] 

    # Generate query embedding
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")

    query_embedding = embedding_model.embed_query(retrieval_query)
    
    # Search ChromaDB
    results = collection.query(query_embeddings = [query_embedding],  n_results=5)

    # Extract retrieved chunks
    retrieved_chunks = []

    documents = results["documents"][0]

    metadatas = results["metadatas"][0]

    ids = results["ids"][0]

    # Build retrieved chunk objects
    for chunk_id, text, metadata in zip(ids, documents, metadatas):

        retrieved_chunks.append({

            "chunk_id": chunk_id,

            "text": text,

            "page": metadata["page"],

            "chunk_order":
            metadata["chunk_order"]
        })

    # Store in state
    state["retrieved_chunks"] = retrieved_chunks

    return state



# MCQ's or Theory Questions Generation Node
def mcq_or_theory_ques_gen_node(state: AgentState) -> AgentState:
    """
    Generates a Single MCQ or Theory question.

    Stores:
    - generated question
    - hidden correct answers
    - user answer
    - question history
    """

    # Retrieve workflow state
    topic = state["selected_topic_or_subtopic"]

    topic_chunks = state["retrieved_chunks"]

    ques_type = state["selected_questions_type"]

    ques_difficulty = state["selected_questions_difficulty"]

    # Build context
    context = ""

    for chunk in topic_chunks:

        context += (chunk["text"] + "\n\n")

    # Session memory
    ques_history = state.get("ques_history", [])

    previous_ques = ""

    for item in ques_history:

        previous_ques += (item["question"] + "\n")


    # MCQ GENERATION
    if ques_type == "mcq":

        system_mess = SystemMessage(

            content=f"""
            You are an educational MCQ generator.

            Generate one MCQ question.

            Educational context:
            {context}

            Topic:
            {topic}

            Difficulty:
            {ques_difficulty}

            Previously generated questions:
            {previous_ques}

            Rules:
            - Generate only one MCQ
            - Generate exactly four options
            - Do not repeat previous questions
            - Include correct answer

            Output Format:

            Question: ...

            A) ...
            B) ...
            C) ...
            D) ...

            Correct Answer: A
            """
        )

        response = llm.invoke([system_mess])

        generated_output = response.content

        # Safe extraction
        if "Correct Answer:" in generated_output:

            mcq_ans = generated_output.split("Correct Answer:")[-1].strip()

            display_ques = generated_output.split("Correct Answer:")[0].strip()

        else:

            mcq_ans = "Not Found"

            display_ques = generated_output

        # Store
        state["generated_question"] = display_ques

        state["correct_ans"] = mcq_ans

    # THEORY GENERATION
    else:

        system_message = SystemMessage(

            content=f"""
            You are an educational theory
            question generator.

            Generate one theory question.

            Educational Context:
            {context}

            Topic:
            {topic}

            Difficulty:
            {ques_difficulty}

            Previously Generated Questions:
            {previous_ques}

            Rules:
            - Generate only one theory question
            - Do not repeat previous questions
            - Generate ideal answer

            Output Format:

            Question: ...

            Ideal Answer: ...
            """
        )

        response = llm.invoke([system_message])

        generated_output = response.content

        # Safe extraction
        if "Ideal Answer:" in generated_output:

            theory_ans = generated_output.split("Ideal Answer:")[-1].strip()

            display_ques = generated_output.split("Ideal Answer:")[0].strip()

        else:

            theory_ans = "Not Found"

            display_ques = generated_output

        # Store
        state["generated_question"] = display_ques
        

        state["correct_ans"] = theory_ans

    return state



# Evaluation Node
def evaluation_node(
    state: AgentState
) -> AgentState:

    """
    Evaluates user answers.
    """

    # Retrieve workflow state
    ques_history = state["ques_history"]

    # Total scores
    total_mcq_score = 0

    total_theory_score = 0

    # Evaluation results
    evaluation_results = []

    for question in ques_history:

        # ----------------------------
        # MCQ Evaluation
        # ----------------------------

        if question["question_type"] == "mcq":

            if (
                question["mcq_answer"]
                .lower()
                .strip()

                ==

                question["user_answer"]
                .lower()
                .strip()
            ):

                mcq_score = 1

            else:

                mcq_score = 0

            total_mcq_score += mcq_score

            evaluation_results.append({

                "question":
                question["question"],

                "score":
                mcq_score,

                "user_answer":
                question["user_answer"],

                "correct_answer":
                question["mcq_answer"]
            })

        # ----------------------------
        # THEORY EVALUATION
        # ----------------------------

        else:

            system_mess = SystemMessage(

                content=f"""
                You are a theory question evaluator.

                Give score from 0 to 10.

                Question:
                {question["question"]}

                Difficulty:
                {question["difficulty"]}

                User Answer:
                {question["user_answer"]}

                Ideal Answer:
                {question["theory_answer"]}

                Output Format:

                Score: ...
                """
            )

            response = llm.invoke([
                system_mess
            ])

            gen_output = response.content

            # Safe extraction
            if "Score:" in gen_output:

                theory_score = gen_output.split(
                    "Score:"
                )[-1].strip()

            else:

                theory_score = "0"

            try:

                total_theory_score += int(
                    theory_score
                )

            except:

                pass

            evaluation_results.append({

                "question":
                question["question"],

                "score":
                theory_score,

                "user_answer":
                question["user_answer"],

                "correct_answer":
                question["theory_answer"]
            })

    # Store totals
    state["total_mcq_score"] = (
        total_mcq_score
    )

    state["total_theory_score"] = (
        total_theory_score
    )

    # Store evaluations
    state["evaluation_results"] = (
        evaluation_results
    )

    return state

# Nodes Processing pipeline
def processing(state : AgentState) -> AgentState:

    try: 

        # Validation
        state = document_validation_node(state)

        if state["validation_status"] == "failed":
            return state
        
        # Extract text
        state = document_ingestion_node(state)

        # Chunking 
        state = semantic_chunking_node(state)

        # Indexing
        state = indexing_node(state)

        # Topic Suggestion 
        state = topic_suggestion_selection_node(state)

        return state


    finally: 

        # Delete uploaded file after processing
        if os.path.exists(state["file_path"]):

            os.remove(state["file_path"])


graph = StateGraph(AgentState)

graph.add_node("document_validation_node", document_validation_node)
graph.add_node("document_ingestion_node", document_ingestion_node)
graph.add_node("semantic_chunking_node", semantic_chunking_node)
graph.add_node("indexing_node", indexing_node)
graph.add_node("topic_suggestion_selection_node", topic_suggestion_selection_node)
graph.add_node("retrieval_node", retrieval_node)
graph.add_node("mcq_or_theory_ques_gen", mcq_or_theory_ques_gen_node)
graph.add_node("evaluation_node", evaluation_node)


graph.add_edge(START, "document_validation_node")
graph.add_edge("document_validation_node", "document_ingestion_node")
graph.add_edge("document_ingestion_node", "semantic_chunking_node")
graph.add_edge("semantic_chunking_node", "indexing_node")
graph.add_edge("indexing_node", "topic_suggestion_selection_node")
graph.add_edge("topic_suggestion_selection_node", "retrieval_node")
graph.add_edge("retrieval_node", "mcq_or_theory_ques_gen")
graph.add_edge("mcq_or_theory_ques_gen", "evaluation_node")
graph.add_edge("evaluation_node", END)


agent = graph.compile()

png_data = agent.get_graph().draw_mermaid_png()

with open("workflow_graph.png", "wb") as f:

    f.write(png_data)

print("Graph saved successfully.")