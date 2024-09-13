# app.py
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import os
from summarizepdf import summarize_pdf
from prepare_vectorstore import process_pdf_and_store
from qa_retriever import load_vector_store_and_qa

app = Flask(__name__)

UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

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
            # Remove the old file if it exists
            old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], existing_filename)
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        process_pdf_and_store()  # Process and store the uploaded PDF
        return jsonify({'success': 'File uploaded successfully', 'filename': filename})
    return jsonify({'error': 'Invalid file type'})

@app.route('/summarize', methods=['POST'])
def summarize():
    filename = request.json['filename']
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    summary = summarize_pdf(file_path)
    return jsonify({'summary': summary})

@app.route('/chat', methods=['POST'])
def chat():
    question = request.json['question']
    answer = load_vector_store_and_qa(question)
    return jsonify({'answer': answer})

@app.route('/delete', methods=['POST'])
def delete_file():
    filename = request.json['filename']
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        # You might want to update your vector store here to remove the deleted file's data
        return jsonify({'success': 'File deleted successfully'})
    else:
        return jsonify({'error': 'File not found'})

if __name__ == '__main__':
    app.run(debug=True)