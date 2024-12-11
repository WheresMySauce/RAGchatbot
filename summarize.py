# Thêm thư viện cần thiết (file python nào cũng có)
import asyncio
import backoff
from openai import APIConnectionError
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
from langchain_text_splitters import CharacterTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.output_parsers import StrOutputParser
from langchain.prompts import ChatPromptTemplate
from werkzeug.utils import secure_filename

# Khai báo hàm (function) dùng từ khóa def 
def map_reduce_parameters(llm): # Hàm này dùng để tạo ra 2 chuỗi quy trình (chain) để tóm tắt văn bản
    # map dùng để tóm tắt các văn bản nhỏ sau khi đã chia ra
    map_prompt = ChatPromptTemplate.from_messages(
        [("system", "Write a concise summary of the following:\\n\\n{context}. Your answer language match with the document language.")],
    )
    map_chain = map_prompt | llm | StrOutputParser() # quy trình từ prompt --> đưa vô model (gpt) --> model trả lời 
    # reduce dùng để tóm tắt các văn bản đã được tóm tắt từ map để có output cuối cùng 
    reduce_template = """
    The following is a set of summaries:
    {docs}
    Take these and distill it into a final, consolidated summary
    of the main themes. Your answer language match with the document language.
    """
    reduce_prompt = ChatPromptTemplate([("human", reduce_template)])
    reduce_chain = reduce_prompt | llm | StrOutputParser()
    return map_chain, reduce_chain

async def summarize_content(path, llm): # Hàm này dùng để tóm tắt nội dung từ file pdf hoặc link web
    map_chain, reduce_chain = map_reduce_parameters(llm) #gọi cái hàm map_reduce_parameters ở trên 
    print(f"Loading content from {path}...")
    print(path)
    if path.endswith('.pdf'):
        loader = PyPDFLoader(path)  # Nếu file là pdf thì dùng PyPDFLoader
        docs = loader.load() #load nội dung
        title = secure_filename(docs[0].metadata.get('source'))
    elif path.startswith('http'):
        loader = WebBaseLoader(path) # Nếu file là link web thì dùng WebBaseLoader
        docs = loader.load() #load nội dung 
        title = docs[0].metadata.get('title')
    else:
        raise ValueError("Unsupported document type. Please provide a PDF file path or a URL.")
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=1024, chunk_overlap=0
    )
    # có thể tăng chunk size để giảm thời gian xử lí nhưng có thể thất thoát nội dung
    split_docs = text_splitter.split_documents(docs) # chia tài liệu thành các phần nhỏ/chunk
    print(f"Generated {len(split_docs)} documents.")

    doc_summaries = []
    # Tóm tắt các phần nhỏ song song với nhau
    tasks = [map_chain.ainvoke(doc.page_content) for doc in split_docs]
    doc_summaries = await asyncio.gather(*tasks) # tóm tắt các phần nhỏ song song với nhau 
    # Tổng hợp các tóm tắt thành một tóm tắt cuối cùng
    combined_summary = await reduce_chain.ainvoke("\n".join(doc_summaries))
    return title, combined_summary # trả về kết quả cuối cùng sau khi gộp lại các tóm tắt
@backoff.on_exception(backoff.expo, APIConnectionError, max_tries=5)
async def summarize_with_backoff(file_path, llm):
    return await summarize_content(file_path, llm)
def run_summarize_pdf(file_path, llm):
    async def run():
        try:
            return await summarize_with_backoff(file_path, llm)
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # If there's no event loop in the current thread, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(run())