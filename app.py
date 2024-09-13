# app.py
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import os
import json
from summarizepdf import summarize_pdf
from prepare_vectorstore import process_pdf_and_store
from qa_retriever import load_vector_store_and_qa

app = Flask(__name__)

UPLOAD_FOLDER = './uploads'
SUMMARY_FOLDER = './summaries'
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SUMMARY_FOLDER'] = SUMMARY_FOLDER

# Ensure the summary folder exists
os.makedirs(SUMMARY_FOLDER, exist_ok=True)

# In-memory storage for summaries
summaries = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_summary(filename, summary):
    summaries[filename] = summary
    summary_path = os.path.join(app.config['SUMMARY_FOLDER'], f"{filename}.txt")
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(summary)

def load_summaries():
    for filename in os.listdir(app.config['SUMMARY_FOLDER']):
        if filename.endswith('.txt'):
            pdf_filename = filename[:-4]  # Remove .txt extension
            summary_path = os.path.join(app.config['SUMMARY_FOLDER'], filename)
            with open(summary_path, 'r', encoding='utf-8') as f:
                summaries[pdf_filename] = f.read()

# Load existing summaries when the app starts
load_summaries()

@app.route('/')
def index():
    return render_template('index_allin.html')

@app.route('/upload', methods=['POST'])
def upload_file():
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
            old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], existing_filename)
            old_summary_path = os.path.join(app.config['SUMMARY_FOLDER'], f"{existing_filename}.txt")
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
            if os.path.exists(old_summary_path):
                os.remove(old_summary_path)
            if existing_filename in summaries:
                del summaries[existing_filename]

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Generate and store summary
        summary = summarize_pdf(file_path)
        save_summary(filename, summary)

        process_pdf_and_store()  # Process and store the uploaded PDF
        return jsonify({'success': 'File uploaded and summarized successfully', 'filename': filename})
    return jsonify({'error': 'Invalid file type'})

@app.route('/summarize', methods=['POST'])
def summarize():
    filename = request.json['filename']
    if filename in summaries:
        return jsonify({'summary': summaries[filename]})
    else:
        return jsonify({'error': 'Summary not found'})

@app.route('/chat', methods=['POST'])
def chat():
    question = request.json['question']
    answer = load_vector_store_and_qa(question)
    return jsonify({'answer': answer})

@app.route('/delete', methods=['POST'])
def delete_file():
    filename = request.json['filename']
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    summary_path = os.path.join(app.config['SUMMARY_FOLDER'], f"{filename}.txt")
    if os.path.exists(file_path):
        os.remove(file_path)
        if os.path.exists(summary_path):
            os.remove(summary_path)
        if filename in summaries:
            del summaries[filename]
        # You might want to update your vector store here to remove the deleted file's data
        return jsonify({'success': 'File and summary deleted successfully'})
    else:
        return jsonify({'error': 'File not found'})

if __name__ == '__main__':
    app.run(debug=True)