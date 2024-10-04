from dotenv import load_dotenv
import os
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader, WebBaseLoader
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
pdf_data_path = "./uploads"

def process_pdf_and_store(session_id, link=None):
    loader = DirectoryLoader(pdf_data_path, glob=f"{session_id}_*.pdf", loader_cls=PyPDFLoader)
    pdf_docs = loader.load()
    if link:
        web_loader = WebBaseLoader(link)
        web_docs = web_loader.load()
    docs = pdf_docs + web_docs
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)

    # Create vector store
    vectorstore = Chroma.from_documents(documents=splits, 
                                        embedding=OpenAIEmbeddings(),
                                        persist_directory=f"./vectorstore_{session_id}")
    
    # vectorstore.persist()

if __name__ == "__main__":
    session_id = str(input("Enter the session id: "))
    link = str(input("Enter the link of the PDF file: ", default=None))
    # path = input("Enter the path of the PDF file: ")
    # This is just for testing purposes
    process_pdf_and_store(session_id, link)