# Fi;e backend server: chứa 2 thằng hỏi đáp với tóm tắt, giao tiếp với web(front-end)
from flask import Flask, render_template, request, jsonify, session, redirect, url_for #server
from werkzeug.utils import secure_filename # định dạng lại tên file đẻ có thể lưu trữ
import os
import shutil
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from summarize import run_summarize_pdf #từ file summarize.py load hàm run_summarize_pdf
from rag import process_pdf_and_store, load_vector_store_and_qa #từ file rag.py load hàm process_pdf_and_store, load_vector_store_and_qa

load_dotenv() #lay bien moi truong (API KEYS)
openai_api_key = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0) #ChatGPT dùng model gpt-4o, temperature = 0.3
# temperature = 0 (trong khoang 0-1) để tăng độ đa dạng của câu trả lời, 0 là có gì nói đó 

UPLOAD_FOLDER = './uploads'
SUMMARY_FOLDER = './summaries'
ALLOWED_EXTENSIONS = {'pdf'}

# --------------------------------------FLASK SERVER--------------------------------------
app = Flask(__name__) #khởi chạy server

app.secret_key = '123' #key để mã hóa session   

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SUMMARY_FOLDER'] = SUMMARY_FOLDER

# tao folder tom tat
os.makedirs(SUMMARY_FOLDER, exist_ok=True)

# Cac bien de luu tru thong tin tom tat, session (id, ten session)
summaries = {} #biến để luư đoạn tóm tắt
sessions = {} # biến để lưu thông tin session (tên session, id session)

# Chạy session có sẵn (Example )
sessions['1'] = "Đại Dương"
# sessions['2'] = "Session 2"

#--------------------------------------FUNCTIONS vãng lai--------------------------------------
def allowed_file(filename): # check file có phải là pdf không
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_summary(session_id, filename, summary): # lưu lại tóm tắt vài 1 file text (.txt)
    # save_summary('1', 'aaa.pdf', 'noi dung tom tat')
    if session_id not in summaries:
        summaries[session_id] = {}
    summaries[session_id][filename] = summary #summaries[1]['aaa.pdf'] = 'noi dung tom tat'
    summary_path = os.path.join(app.config['SUMMARY_FOLDER'], f"{session_id}_{filename}.txt")
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(summary)
    # luu vao file text 1_aaa.pdf.txt
def load_summaries(): #load tất cả các file text (.txt) trong thư mục summaries
    for filename in os.listdir(app.config['SUMMARY_FOLDER']):
        if filename.endswith('.txt'): # 1_aaa.pdf.txt  1_link.txt.txt
            try:
                # lấy tên file: aa.pdf, link.txt
                parts = filename[:-4].split('_', 1)
                if len(parts) == 2:
                    session_id, pdf_filename = parts # 1, aaa.pdf
                else:
                    session_id = 'default'
                    pdf_filename = filename[:-4]  # xóa .txt
                
                summary_path = os.path.join(app.config['SUMMARY_FOLDER'], filename)
                with open(summary_path, 'r', encoding='utf-8') as f:
                    if session_id not in summaries:
                        summaries[session_id] = {}
                    summaries[session_id][pdf_filename] = f.read() #summaries[1]['aaa.pdf']
            except Exception as e:
                print(f"Lỗi chạy tóm tắt cho {filename}: {str(e)}")
# Chạy lại đề lấy tóm tắt
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
        # xóa vector store của session
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
    # lấy tên session
    session_name = sessions[session_id]
    # gui ten file cho web
    title_list = []
    file_list = []
    secured_file_list = []
    for f in os.listdir(UPLOAD_FOLDER):
        if f.startswith(f"{session_id}_") and f.endswith('.txt'): #1_link.txt
            with open(os.path.join(UPLOAD_FOLDER, f), 'r', encoding='utf-8') as file:
                raw_link, title = file.read().splitlines()
                #lay link trong dong dau tien cua file text
                #lay title trong dong thu 2 cua file text
                file_list.append(raw_link) #lay ten file trong file text
                title_list.append(title) #lay title trong file text
                secured_file_list.append(secure_filename(raw_link)+'.txt') #lay ten file trong file text
        elif f.startswith(f"{session_id}_") and f.endswith('.pdf'): #1_aaa.pdf
            file_list.append(f.split('_', 1)[1]) #aaa.pdf
            title_list.append(f.split('_', 1)[1]) #aaa.pdf
            secured_file_list.append(secure_filename(f.split('_', 1)[1])) #secure_filename(aaa.pdf)
    print(file_list)
    print(secured_file_list)
    #file_list = ['aaa.pdf', 'link.txt']
    #secured_file_list = ['secure_filename(aaa.pdf)', 'secure_filename(aaa.pdf)']
    return render_template('chat.html', session_id=session_id,
                                        session_name=session_name,
                                        file_list=file_list,
                                        secured_file_list=secured_file_list, 
                                        title_list=title_list, 
                                        zip=zip)

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
        raw_filename = file.filename # aaa.pdf
        filename = secure_filename(raw_filename) # secure_filename(aaa.pdf)
        existing_filename = request.form.get('existing_filename')
        if existing_filename:
            # Xóa file cũ
            old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_{existing_filename}")
            old_summary_path = os.path.join(app.config['SUMMARY_FOLDER'], f"{session_id}_{existing_filename}.txt")
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
            if os.path.exists(old_summary_path):
                os.remove(old_summary_path)
            if session_id in summaries and existing_filename in summaries[session_id]:
                del summaries[session_id][existing_filename]

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_{filename}") #1_{secure_filename(aaa)}.pdf
        file.save(file_path) #1_aaa.pdf
        
        # Chạy tóm tắt và lưu lại
        try:
            title, summary = run_summarize_pdf(file_path, llm) #tóm tắt file pdf
        except Exception as e:
            summary = f"Đã xảy ra lỗi tóm tắt: {str(e)} \nCó thể do file quá lớn"
         
        save_summary(session_id, filename, summary) #lwu lại tóm tắt

        process_pdf_and_store(session_id, UPLOAD_FOLDER)  # Chuyển chữ thành số để hỏi đáp 
        # 'filename' : secure_filename(aaa.pdf), 'raw_filename' : aaa.pdf
        return jsonify({'success': 'File uploaded and summarized successfully', 'filename': filename, 'raw_filename' : raw_filename}) #gửi kq về web
    return jsonify({'error': 'Invalid file type'})

@app.route('/process-url', methods=['POST'])
# route để xử lí url mà user đã gửi lên

def process_url():
    session_id = session.get('current_session')
    if not session_id:
        return jsonify({'error': 'No active session'})

    data = request.get_json()
    url = data.get('url') # lấy cái link đc gửi 
    secured_url = secure_filename(url) # secure(link)
    if not url:
        return jsonify({'error': 'No URL provided'})
    title, summary = run_summarize_pdf(url, llm) # Tóm tắt nội dung trên url
    # Lưu tên web và tóm tắt vào file text
    text_filename = f"{session_id}_{secured_url}.txt" #1_secure(link).txt
    text_filepath = os.path.join(app.config['UPLOAD_FOLDER'], text_filename) #1_secure(link).txt
    with open(text_filepath, 'w', encoding='utf-8') as f:
        f.write(url + '\n' + title) #lưu lại link trong dòng đầu tiên của file text
    filename = f"{secured_url}.txt" # secure(link).txt
    save_summary(session_id, filename, summary) # lưu lại cái tóm tắt 
    process_pdf_and_store(session_id, UPLOAD_FOLDER)  # chuyển chữ thành vector (embedding) để hỏi đáp
    return jsonify({'success': 'URL processed successfully', 'filename': filename, 'url': url, 'title': title})
    
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
        # Dự phòng nếu muốn chạy lại vector_store
        return jsonify({'success': 'File and summary deleted successfully', 'filename': filename})  
    else:
        return jsonify({'error': 'File not found'})

if __name__ == '__main__':
    app.run(debug=True)