from flask import Flask, render_template, request, jsonify, session, redirect, url_for #server
from werkzeug.utils import secure_filename 
import os
import re
import json
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import PyPDF2
from dotenv import load_dotenv
# from langchain_community.vectorstores.chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.prompts import PromptTemplate
from langchain_chroma import Chroma
load_dotenv() #load environment variableS (API KEYS)
openai_api_key = os.getenv("OPENAI_API_KEY")
pdf_data_path = "./uploads" #uploaded pdf data path
llm = ChatOpenAI(model="gpt-4o-mini")

UPLOAD_FOLDER = './uploads'
SUMMARY_FOLDER = './summaries'
ALLOWED_EXTENSIONS = {'pdf'}
# --------------------------------------SUMMARIZE .PDF FILE--------------------------------------
WHITESPACE_HANDLER = lambda k: re.sub('\s+', ' ', re.sub('\n+', ' ', k.strip()))

def extract_text_from_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    return text

def chunk_text(text, chunk_size=2000):
    words = text.split()
    return [' '.join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

def summarize_chunk(chunk, tokenizer, model, device):
    input_ids = tokenizer(
        [WHITESPACE_HANDLER(chunk)],
        return_tensors="pt",
        padding="max_length",
        truncation=True,
        max_length=512
    )["input_ids"].to(device)

    output_ids = model.generate(
        input_ids=input_ids,
        max_length=256,
        min_length=50,
        no_repeat_ngram_size=2,
        num_beams=4
    )[0]

    return tokenizer.decode(
        output_ids,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False
    )

def summarize_pdf(pdf_path):
    # Check if CUDA is available
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    model_name = "csebuetnlp/mT5_multilingual_XLSum"
    tokenizer = AutoTokenizer.from_pretrained(model_name, legacy=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to(device)

    text = extract_text_from_pdf(pdf_path)
    chunks = chunk_text(text)
    
    summaries = []
    for chunk in chunks:
        summary = summarize_chunk(chunk, tokenizer, model, device)
        summaries.append(summary)
    
    return " ".join(summaries)


# --------------------------------------PREPARE VECTOR STORE--------------------------------------
def process_pdf_and_store(session_id):
    loader = DirectoryLoader(pdf_data_path, glob=f"{session_id}_*.pdf", loader_cls=PyPDFLoader)
    docs = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)

    # Create vector store
    vectorstore = Chroma.from_documents(documents=splits, 
                                        embedding=OpenAIEmbeddings(),
                                        persist_directory=f"./vectorstore_{session_id}")
    
    # vectorstore.persist()

# --------------------------------------Q&A RETRIEVER--------------------------------------
# Load the vector store and do Q&A
def load_vector_store_and_qa(session_id, question):
    persist_directory = f"./vectorstore_{session_id}"
    
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

# --------------------------------------FLASK SERVER--------------------------------------
app = Flask(__name__)
app.secret_key = '123'  # Set a secret key for sessions

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SUMMARY_FOLDER'] = SUMMARY_FOLDER

# Ensure the summary folder exists
os.makedirs(SUMMARY_FOLDER, exist_ok=True)

# In-memory storage for summaries and sessions
summaries = {}
sessions = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_summary(session_id, filename, summary):
    if session_id not in summaries:
        summaries[session_id] = {}
    summaries[session_id][filename] = summary
    summary_path = os.path.join(app.config['SUMMARY_FOLDER'], f"{session_id}_{filename}.txt")
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(summary)

def load_summaries():
    for filename in os.listdir(app.config['SUMMARY_FOLDER']):
        if filename.endswith('.txt'):
            try:
                # Try to split the filename into session_id and pdf_filename
                parts = filename[:-4].split('_', 1)
                if len(parts) == 2:
                    session_id, pdf_filename = parts
                else:
                    # If splitting fails, use a default session_id and the whole filename as pdf_filename
                    session_id = 'default'
                    pdf_filename = filename[:-4]  # Remove .txt extension
                
                summary_path = os.path.join(app.config['SUMMARY_FOLDER'], filename)
                with open(summary_path, 'r', encoding='utf-8') as f:
                    if session_id not in summaries:
                        summaries[session_id] = {}
                    summaries[session_id][pdf_filename] = f.read()
            except Exception as e:
                print(f"Error loading summary for file {filename}: {str(e)}")

# Load existing summaries when the app starts
load_summaries()

# Add pre-loaded sessions manually here
sessions['1'] = "COVID-19 Research On Education"
# sessions['2'] = "Preloaded Session 2"
@app.route('/')
def index():
    return render_template('session_management.html', sessions=sessions)

@app.route('/create_session', methods=['POST'])
def create_session():
    session_name = request.form['session_name']
    session_id = str(len(sessions) + 1)
    sessions[session_id] = session_name
    return redirect(url_for('index'))

@app.route('/session/<session_id>')
def session_page(session_id):
    if session_id not in sessions:
        return redirect(url_for('index'))
    session['current_session'] = session_id
    # Load the files for this session
    file_list = [f.split('_', 1)[1] for f in os.listdir(UPLOAD_FOLDER) if f.startswith(f"{session_id}_")]
    print(file_list)
    return render_template('index_allin.html', session_id=session_id, file_list=file_list)

@app.route('/upload', methods=['POST'])
def upload_file():
    session_id = session.get('current_session')
    if not session_id:
        return jsonify({'error': 'No active session'})
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        existing_filename = request.form.get('existing_filename')
        if existing_filename:
            # Remove the old file and its summary if it exists
            old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_{existing_filename}")
            old_summary_path = os.path.join(app.config['SUMMARY_FOLDER'], f"{session_id}_{existing_filename}.txt")
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
            if os.path.exists(old_summary_path):
                os.remove(old_summary_path)
            if session_id in summaries and existing_filename in summaries[session_id]:
                del summaries[session_id][existing_filename]

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_{filename}")
        file.save(file_path)
        
        # Generate and store summary
        summary = summarize_pdf(file_path)
        save_summary(session_id, filename, summary)

        process_pdf_and_store(session_id)  # Process and store the uploaded PDF
        return jsonify({'success': 'File uploaded and summarized successfully', 'filename': filename})
    return jsonify({'error': 'Invalid file type'})

@app.route('/summarize', methods=['POST'])
def summarize():
    session_id = session.get('current_session')
    if not session_id:
        return jsonify({'error': 'No active session'})
    
    filename = request.json['filename']
    if session_id in summaries and filename in summaries[session_id]:
        return jsonify({'summary': summaries[session_id][filename]})
    else:
        return jsonify({'error': 'Summary not found'})

@app.route('/chat', methods=['POST'])
def chat():
    session_id = session.get('current_session')
    if not session_id:
        return jsonify({'error': 'No active session'})
    
    question = request.json['question']
    answer = load_vector_store_and_qa(session_id, question)
    return jsonify({'answer': answer})

@app.route('/delete', methods=['POST'])
def delete_file():
    session_id = session.get('current_session')
    if not session_id:
        return jsonify({'error': 'No active session'})
    
    filename = request.json['filename']
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_{filename}")
    summary_path = os.path.join(app.config['SUMMARY_FOLDER'], f"{session_id}_{filename}.txt")
    if os.path.exists(file_path):
        os.remove(file_path)
        if os.path.exists(summary_path):
            os.remove(summary_path)
        if session_id in summaries and filename in summaries[session_id]:
            del summaries[session_id][filename]
        # You might want to update your vector store here to remove the deleted file's data
        return jsonify({'success': 'File and summary deleted successfully'})
    else:
        return jsonify({'error': 'File not found'})

if __name__ == '__main__':
    app.run(debug=True)