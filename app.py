# Fi;e backend server: chứa 2 thằng hỏi đáp với tóm tắt, giao tiếp với web(front-end)
from flask import Flask, render_template, request, jsonify, session, redirect, url_for #server
from werkzeug.utils import secure_filename 
import os
import shutil
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from summarize import run_summarize_pdf #từ file summarize.py load thằng hàm run_summarize_pdf
from rag import process_pdf_and_store, load_vector_store_and_qa

load_dotenv() #load environment variableS (API KEYS)
openai_api_key = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0) #ChatGPT dùng model gpt-4o, temperature = 0.3
# temperature = 0 (trong khoang 0-1) để tăng độ đa dạng của câu trả lời 0 là có gì nói đó 

UPLOAD_FOLDER = './uploads'
SUMMARY_FOLDER = './summaries'
ALLOWED_EXTENSIONS = {'pdf'}

# --------------------------------------FLASK SERVER--------------------------------------
app = Flask(__name__) #khởi chạy server

app.secret_key = '123' #key để mã hóa session   

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SUMMARY_FOLDER'] = SUMMARY_FOLDER

# Ensure the summary folder exists
os.makedirs(SUMMARY_FOLDER, exist_ok=True)

# In-memory storage for summaries and sessions
summaries = {} #biến để luư đoạn tóm tắt
sessions = {} # biến để lưu thông tin session (tên session, id session)

# Add pre-loaded sessions manually here
sessions['1'] = "COVID-19 Research On Education"
# sessions['2'] = "Preloaded Session 2"

#--------------------------------------FUNCTIONS vãng lai--------------------------------------
def allowed_file(filename): # check file có phải là pdf không
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_summary(session_id, filename, summary): # lưu lại tóm tắt vài 1 file text (.txt)
    if session_id not in summaries:
        summaries[session_id] = {}
    summaries[session_id][filename] = summary
    summary_path = os.path.join(app.config['SUMMARY_FOLDER'], f"{session_id}_{filename}.txt")
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(summary)

def load_summaries(): #load tất cả các file text (.txt) trong thư mục summaries
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

@app.route('/') #route mặc định http://127.0.0.1:5000/
def index():
    return render_template('session_management.html', sessions=sessions) 
#ROUTE NÀO CÓ render_template() thì sẽ trả về 1 file html (GIAO DIỆN)

@app.route('/create_session', methods=['POST']) #http://127.0.0.1:5000/create_session
#DÙNG ĐỂ TẠO RA 1 SESSION MỚI
def create_session():
    session_name = request.form['session_name']
    session_id = str(len(sessions) + 1)
    sessions[session_id] = session_name
    return redirect(url_for('index'))
@app.route('/delete_session', methods=['POST'])
# DÙNG ĐỂ XÓA 1 SESSION 
def delete_session():
    data = request.json
    session_id = data.get('session_id')
    print(session_id)
    if session_id in sessions:
        # del sessions[session_id]
        # Remove vectorstore directory
        shutil.rmtree(f"./vectorstore_{session_id}", ignore_errors=True)
        # Delete all files and summaries for this session
        for f in os.listdir(UPLOAD_FOLDER):
            if f.startswith(f"{session_id}_"):
                os.remove(os.path.join(UPLOAD_FOLDER, f))
        for f in os.listdir(SUMMARY_FOLDER):
            if f.startswith(f"{session_id}_"):
                os.remove(os.path.join(SUMMARY_FOLDER, f))
    return jsonify({'success': True})

@app.route('/session/<session_id>')
# ROUTE ĐỂ HIỂN THỊ GIAO DIỆN CHAT
def session_page(session_id):
    if session_id not in sessions:
        return redirect(url_for('index'))
    session['current_session'] = session_id
    # Load the files for this session
    file_list = [f.split('_', 1)[1] for f in os.listdir(UPLOAD_FOLDER) if f.startswith(f"{session_id}_")]
    print(file_list)
    return render_template('chat.html', session_id=session_id, file_list=file_list)

@app.route('/upload', methods=['POST'])
# route để xử lí file pdf mà user đã gửi lên
def upload_file():
    session_id = session.get('current_session')
    if not session_id:
        return jsonify({'error': 'No active session'})
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    file = request.files['file'] # lấy cái mà web gửi xuống 
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
        summary = run_summarize_pdf(file_path, llm) #tóm tắt file pdf
        save_summary(session_id, filename, summary) #lwu lại tóm tắt

        process_pdf_and_store(session_id, UPLOAD_FOLDER)  # Chuyển chữ thành số để hỏi đáp 
        return jsonify({'success': 'File uploaded and summarized successfully', 'filename': filename}) #gửi kq về web
    return jsonify({'error': 'Invalid file type'})

# Route for processing URLs and saving as .txt
@app.route('/process-url', methods=['POST'])
# route để xử lí url mà user đã gửi lên

def process_url():
    session_id = session.get('current_session')
    if not session_id:
        return jsonify({'error': 'No active session'})

    data = request.get_json()
    url = data.get('url') # lấy cái link đc gửi 
    if not url:
        return jsonify({'error': 'No URL provided'})
    summary = run_summarize_pdf(url, llm) # Tóm tắt nội dung trên url
    # Save the webpage name
    text_filename = f"{session_id}_{secure_filename(url)}.txt"
    text_filepath = os.path.join(app.config['UPLOAD_FOLDER'], text_filename)
    with open(text_filepath, 'w', encoding='utf-8') as f:
        f.write(url) # lưu địa chỉ vào file text cùng tên 

    filename = f"{secure_filename(url)}.txt"
    save_summary(session_id, filename, summary) # lưu lại cái tóm tắt 
    process_pdf_and_store(session_id, UPLOAD_FOLDER)  # chuyển chữ thành vector (embedding) để hỏi đáp
    return jsonify({'success': 'URL processed successfully', 'filename': filename, 'url': url})
    
@app.route('/summarize', methods=['POST'])
# route để hiển thị tóm tắt của file pdf
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
# route để hiển thị câu trả lời của câu hỏi
def chat():
    session_id = session.get('current_session')
    if not session_id:
        return jsonify({'error': 'No active session'})
    question = request.json['question']
    answer = load_vector_store_and_qa(session_id, llm, question)
    return jsonify({'answer': answer})

@app.route('/delete', methods=['POST'])
# route để xóa file pdf và file tóm tắt
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