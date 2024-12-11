# Khai bao cac thu vien can thiet
import os
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader, WebBaseLoader
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.prompts import PromptTemplate
from langchain_chroma import Chroma

upload_folder = "./uploads"
def process_pdf_and_store(session_id, upload_folder): # Bước 1: Hàm này dùng để xử lý file pdf, embedding thành vector và lưu trữ vào vectorstore

    # Lấy tất cả các file trong thư mục chủ đề hiện tại để xử lí
    pdf_loader = DirectoryLoader(upload_folder, glob=f"{session_id}_*.pdf", loader_cls=PyPDFLoader)
    pdf_docs = pdf_loader.load() # load nội dung từ file pdf

    web_address = []
    # Đọc địa chỉ url từ file text và lưu vào web_address
    for file in os.listdir(upload_folder):
        if file.endswith(".txt") and file.startswith(f"{session_id}_"):
            with open(os.path.join(upload_folder, file), 'r') as f:
                url = f.read().splitlines()[0] # Lấy địa chỉ lưu trong file .txt
                web_address.append(url)
    web_loader = WebBaseLoader(web_address)
    web_docs = web_loader.load()
    
    #Gộp các tài liệu 
    docs = pdf_docs + web_docs

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=100) # chia nội dung của file pdf thành các chunk 1024 kí tự
    splits = text_splitter.split_documents(docs)

    # Create vector store
    vectorstore = Chroma.from_documents(documents=splits, 
                                        embedding=OpenAIEmbeddings(),
                                        persist_directory=f"./vectorstore_{session_id}") # embedding: chuyển chữ thành số (vector) --> lưu thành vectorstore
    
if __name__ == "__main__":
    process_pdf_and_store(1, upload_folder) # gọi hàm ở trên