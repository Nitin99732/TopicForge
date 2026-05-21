# Libraries
import streamlit as st

# Upload file
upload_file = st.file_uploader(label="Upload PDF, TXT or DOCX.", type=["pdf", "txt", "docx"], max_upload_size=10)


#File Uploaded Successfully
if upload_file is not None:

    st.success("File uploaded successfully.")

    st.write("File name: ", upload_file.name)