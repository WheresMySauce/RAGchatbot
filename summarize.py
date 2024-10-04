import asyncio
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.output_parsers import StrOutputParser
from langchain.prompts import ChatPromptTemplate

def map_reduce_parameters(llm):
    map_prompt = ChatPromptTemplate.from_messages(
        [("system", "Write a concise summary of the following:\\n\\n{context}. Your answer language match with the input language.")],
    )
    map_chain = map_prompt | llm | StrOutputParser()
    reduce_template = """
    The following is a set of summaries:
    {docs}
    Take these and distill it into a final, consolidated summary
    of the main themes. Your answer language match with the input language.
    """
    reduce_prompt = ChatPromptTemplate([("human", reduce_template)])
    reduce_chain = reduce_prompt | llm | StrOutputParser()
    return map_chain, reduce_chain

async def summarize_content(path, llm):
    map_chain, reduce_chain = map_reduce_parameters(llm)
    print(f"Loading content from {path}...")
    if path.endswith('.pdf'):
        loader = PyPDFLoader(path)
    elif path.startswith('http'):
        loader = WebBaseLoader(path)
    else:
        raise ValueError("Unsupported document type. Please provide a PDF file path or a URL.")
    docs = loader.load()
    text_splitter = CharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=1024, chunk_overlap=0
    )
    split_docs = text_splitter.split_documents(docs)
    print(f"Generated {len(split_docs)} documents.")

    doc_summaries = []
    # Create a list of tasks
    tasks = [map_chain.ainvoke(doc.page_content) for doc in split_docs]
    doc_summaries = await asyncio.gather(*tasks)
    # Step 3: Combine summaries into a final summary (reduce step)
    combined_summary = await reduce_chain.ainvoke("\n".join(doc_summaries))
    return combined_summary
def run_summarize_pdf(file_path, llm):
    summary = asyncio.run(summarize_content(file_path, llm))
    return summary