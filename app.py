from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.utils import secure_filename
import os
import json
from summarizepdf import summarize_pdf
from prepare_vectorstore import process_pdf_and_store
from qa_retriever import load_vector_store_and_qa

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Set a secret key for sessions

UPLOAD_FOLDER = './uploads'
SUMMARY_FOLDER = './summaries'
ALLOWED_EXTENSIONS = {'pdf'}

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
    return render_template('index_allin.html', session_id=session_id, session_name=sessions[session_id])

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