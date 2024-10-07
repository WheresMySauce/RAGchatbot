# Khai bao cac thu vien can thiet
import os
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader, WebBaseLoader
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.prompts import PromptTemplate
from langchain_chroma import Chroma

def process_pdf_and_store(session_id, upload_folder): # Bước 1: Hàm này dùng để xử lý file pdf, embedding thành vector và lưu trữ vào vectorstore
    pdf_loader = DirectoryLoader(upload_folder, glob=f"{session_id}_*.pdf", loader_cls=PyPDFLoader) # lây tất cả các file pdf trong thư mục upload, sau đó load nó
    pdf_docs = pdf_loader.load() # load nội dung từ file pdf

    web_address = []
    # Đọc địa chỉ url từ file text  và lưu vào web_address
    for file in os.listdir(upload_folder):
        if file.endswith(".txt") and file.startswith(f"{session_id}_"):
            with open(os.path.join(upload_folder, file), 'r') as f:
                url = f.read().splitlines()[0] #doc link trong dong dau tien cua file txt
                web_address.append(url)
                # url = f.read()
                # web_address.append(url)

    web_loader = WebBaseLoader(web_address)
    web_docs = web_loader.load()

    docs = pdf_docs + web_docs

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=100) # chia nội dung của file pdf thành các chunk 1024 kí tự
    splits = text_splitter.split_documents(docs)

    # Create vector store
    vectorstore = Chroma.from_documents(documents=splits, 
                                        embedding=OpenAIEmbeddings(),
                                        persist_directory=f"./vectorstore_{session_id}") # embedding: chuyển chữ thành số (vector) --> lưu thành vectorstore
    

def load_vector_store_and_qa(session_id, llm, question): # Bước 2: Hàm này dùng để load vectorstore đã lưu và trả lời câu hỏi
    persist_directory = f"./vectorstore_{session_id}"
    # Load the persisted vector store
    vectorstore = Chroma(persist_directory=persist_directory,
                        embedding_function=OpenAIEmbeddings()
    )
    retriever = vectorstore.as_retriever() # load lại vectorstore

    # Define new custom template
    template = """Use the following pieces of context to answer the question at the end.
    If you don't know the answer, just say that you don't know, don't try to make up an answer.
    Use three sentences maximum and keep the answer as concise as possible.
    Note that the question language could be differ from language of the context.
    Your answer language should match with the question language.

    {context}

    Question: {question}

    Helpful Answer:"""
    # Update the prompt
    custom_rag_prompt = PromptTemplate.from_template(template)
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs) # khai báo prompt (câu hỏi)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | custom_rag_prompt
        | llm
        | StrOutputParser()
    )
    return rag_chain.invoke(question)