# Libraries
from typing import TypedDict, Optional, List, Dict

import os

import fitz

import random

import chromadb

from docx import Document

from uuid import uuid4

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.messages import SystemMessage, HumanMessage

from langgraph.graph import StateGraph, START, END

from IPython.display import Image, display


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

    # Question History
    ques_history: List[Dict]

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
        doc = fitz.open(file_path)

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

    for page in doc:
        extracted_text += page.get_text()

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

    doc.close()

    return state    
    