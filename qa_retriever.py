# qa_retriever.py
import os
from dotenv import load_dotenv
from langchain import hub
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(model="gpt-4o-mini")
persist_directory = "./vectorstore"

# Load the vector store and do Q&A
def load_vector_store_and_qa(question):
    # Load the persisted vector store
    vectorstore = Chroma(persist_directory=persist_directory,
                        embedding_function=OpenAIEmbeddings()
    )
    retriever = vectorstore.as_retriever()
    # Define new custom template
    new_template = """You are an expert assistant specializing in providing detailed, clear, and accurate answers.
    Please consider all of the provided context carefully, and be sure to answer in full sentences.
    If you don't know the answer, it's okay to acknowledge that.
    Question: {question}
    Context: {context}
    Answer:"""
    # Update the prompt
    prompt = PromptTemplate(input_variables=["context", "question"], 
                            template=new_template
    )
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return rag_chain.invoke(question)
