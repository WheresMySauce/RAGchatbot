$(document).ready(function() {
    $('#file-upload').change(function() {
        uploadFile(this.files[0]);
    });

    $('#user-input').keypress(function(e) {
        if(e.which == 13) {
            sendMessage();
            return false;
        }
    });
});
// lấy giá trị model/ cửa sổ 
var modal = document.getElementById("uploadModal");
// lấy giá trị button
var btn = document.getElementById("uploadBtn");
// lấy giá trị span (x) đóng model)
var span = document.getElementsByClassName("close")[0];
// Open the modal when clicking the upload button

btn.onclick = function() {
    modal.style.display = "block";
}
// đóng modal khi click vào nút (x)
span.onclick = function() {
    modal.style.display = "none";
}
window.onclick = function(event) {
    if (event.target == modal) {
        modal.style.display = "none";
    }
}
// Tải file lên server
document.getElementById("file-upload-modal").onchange = function() {
    var file = this.files[0];
    if (file) {
        var formData = new FormData();
        formData.append('file', file);
        modal.style.display = "none";  // Xóa modal sau khi tải lên
        $('#uploadBtn').prop('disabled', true);
        $('#uploadBtn').css('background-color', 'gray');
        $('#uploadBtn').text('Đang Xử lí...');
        $.ajax({
            url: '/upload',  // route để xử lí file pdf
            type: 'POST',
            data: formData,
            contentType: false,
            processData: false,
            success: function(response) {
                if (response.success) {
                    $('#uploadBtn').prop('disabled', false);
                    $('#uploadBtn').css('background-color', '');
                    $('#uploadBtn').text('Thêm nguồn')
                    addFileToList(response.filename, response.raw_filename, response.raw_filename);
                } else {
                    alert('Lỗi: ' + response.error);
                    $('#uploadBtn').prop('disabled', false);
                    $('#uploadBtn').css('background-color', '');
                    $('#uploadBtn').text('Thêm nguồn')
                }
            }
        });

    }
}

// Xử  lí link 
function submitUrl() {
    url = document.getElementById("web-url-modal").value;
    if (url.trim() === '') return;
    console.log(url);
    modal.style.display = "none";
    $('#uploadBtn').prop('disabled', true);
    $('#uploadBtn').css('background-color', 'gray');
    $('#uploadBtn').text('Đang Xử lí...');
    $.ajax({
        url: '/process-url',  // route xử lí link
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ url: url }), //https://www.wikipedia.org/....
        success: function(response) {
            if (response.success) {
                // console.log(response.title);
                // console.log(response.filename);
                // console.log(response.url);
                document.getElementById('web-url-modal').value = "";
                $('#uploadBtn').prop('disabled', false);
                $('#uploadBtn').css('background-color', '');
                $('#uploadBtn').text('Thêm nguồn')
                addFileToList(response.filename, response.title, response.url);
            } else {
                alert('Lỗi: ' + response.error);
                $('#uploadBtn').prop('disabled', false);
                $('#uploadBtn').css('background-color', '');
                $('#uploadBtn').text('Thêm nguồn')
            }
        }
    });
}

// Thêm tên file vào danh sách (cột bên trái)
function addFileToList(filename, rawName, url) {
    // Add the file to the list dynamically
    let fileItem = `
        <div id="${filename}" class="file-item">
            <div class="file-name">`;

    // Check if URL is a link
    if (url.startsWith('http')) {
        fileItem += `<a href="${url}" target="_blank">${rawName}</a>`;
    } else {
        fileItem += `${rawName}`;
    }

    fileItem += `
            </div>
            <div class="file-actions">
                <button class="file-action" onclick="summarize('${filename}')">Tóm tắt</button>
                <button class="file-action" onclick="deleteFile('${filename}')">Xóa</button>
            </div>
        </div>
    `;

    // Append the new file item to the list
    $('#file-list').append(fileItem);
}

// Hien thi noi dung tom tat
var summaryModal = document.getElementById("summaryModal");

// Get the button that closes the summary modal
var closeSummaryButton = document.getElementById("closeSummaryModal");

// When the user clicks on the close button, close the summary modal
closeSummaryButton.onclick = function() {
    summaryModal.style.display = "none";
}

// Close the summary modal when clicking outside of it
window.onclick = function(event) {
    if (event.target == modal) {
        modal.style.display = "none";
    }
    if (event.target == summaryModal) {
        summaryModal.style.display = "none";
    }
}

// Update the summarize function
function summarize(filename) {
    $.ajax({
        url: '/summarize',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({filename: filename}),
        success: function(response) {
            if (response.summary) {
                // Replace newline characters with <br> tags
                var formattedSummary = response.summary.replace(/\n/g, '<br>');
                // Display the summary in the modal
                document.getElementById("summaryContent").innerHTML = formattedSummary;
                summaryModal.style.display = "block";
            } else {
                alert('Lỗi: ' + response.error);
            }
        }
    });
}

// Nút xóa file trong danh sách 
function deleteFile(filename) {
    //xóa .txt trong filename
    // var rawFilename = filename.replace('.txt', '');
    // if (confirm(`Bạn có chắc muốn xóa tài liệu ${rawFilename} ?`)) {
    if (confirm(`Bạn có chắc muốn xóa tài liệu này?`)) {
        $.ajax({
            url: '/delete',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({filename: filename}),
            success: function(response) {
                console.log(response.filename);
                if (response.success) {
                    $(`[id='${response.filename}']`).remove();
                } else {
                    alert('Error: ' + response.error);
                }
            }
        });
    }
}

// Gửi tin nhắn
function sendMessage() {
    var message = $('#user-input').val();
    if (message.trim() === '') return;

    $('#chat-messages').append(`<div class="message user-message">${message}</div>`);
    $('#user-input').val('');

    $.ajax({
        url: '/chat',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({question: message}),
        success: function(response) {
            $('#chat-messages').append(`<div class="message bot-message">${response.answer}</div>`);
            $('#chat-messages').scrollTop($('#chat-messages')[0].scrollHeight);
        }
    });
}