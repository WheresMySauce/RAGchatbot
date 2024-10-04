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

// Get the modal
var modal = document.getElementById("uploadModal");
// Get the button that opens the modal
var btn = document.getElementById("uploadBtn");
// Get the <span> element that closes the modal
var span = document.getElementsByClassName("close")[0];
// Open the modal when clicking the upload button
btn.onclick = function() {
    modal.style.display = "block";
}
// Close the modal
span.onclick = function() {
    modal.style.display = "none";
}
window.onclick = function(event) {
    if (event.target == modal) {
        modal.style.display = "none";
    }
}
// Handle file upload
document.getElementById("file-upload-modal").onchange = function() {
    var file = this.files[0];
    if (file) {
        var formData = new FormData();
        formData.append('file', file);

        $.ajax({
            url: '/upload',  // Backend route for uploading files
            type: 'POST',
            data: formData,
            contentType: false,
            processData: false,
            success: function(response) {
                if (response.success) {
                    addFileToList(response.filename, response.filename);
                } else {
                    alert('Error: ' + response.error);
                }
            }
        });
        modal.style.display = "none";  // Close modal after upload
    }
}

// Handle URL submission
function submitUrl() {
    url = document.getElementById("web-url-modal").value;
    if (url.trim() === '') return;

    $.ajax({
        url: '/process-url',  // Backend route for processing URLs
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ url: url }),
        success: function(response) {
            if (response.success) {
                addFileToList(response.filename, response.url);
            } else {
                alert('Error: ' + response.error);
            }
        }
    });
    modal.style.display = "none";  // Close modal after submission
}

// Add the uploaded or URL-submitted file to the list dynamically
function addFileToList(filename, rawName) {
    console.log(filename);
    console.log(rawName);
    const fileId = `file-${filename.replace(/\./g, '-')}`;
    $('#file-list').append(`
        <div id="${fileId}" class="file-item">
            <div class="file-name">${rawName}</div>
            <div class="file-actions">
                <button class="file-action" onclick="summarize('${filename}')">Summarize</button>
                <button class="file-action" onclick="deleteFile('${filename}')")">Delete</button>
            </div>
        </div>
    `);
}

function summarize(filename) {
    $.ajax({
        url: '/summarize',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({filename: filename}),
        success: function(response) {
            if (response.summary) {
                alert('Summary: ' + response.summary);
            } else {
                alert('Error: ' + response.error);
            }
        }
    });
}

function deleteFile(filename) {
    if (confirm(`Are you sure you want to delete ${filename}?`)) {
        $.ajax({
            url: '/delete',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({filename: filename}),
            success: function(response) {
                if (response.success) {
                    $(`#file-${filename.replace(/\./g, '-')}`).remove();
                } else {
                    alert('Error: ' + response.error);
                }
            }
        });
    }
}

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