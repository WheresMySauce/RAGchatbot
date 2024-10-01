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

function uploadFile(file) {
    var formData = new FormData();
    formData.append('file', file);

    $.ajax({
        url: '/upload',
        type: 'POST',
        data: formData,
        contentType: false,
        processData: false,
        success: function(response) {
            if(response.success) {
                addFileToList(response.filename);
            } else {
                alert('Error: ' + response.error);
            }
        }
    });
}

function addFileToList(filename) {
    const fileId = `file-${filename.replace(/\./g, '-')}`;
    $('#file-list').append(`
        <div id="${fileId}" class="file-item">
            ${filename}
            <button onclick="summarize('${filename}')">Summarize</button>
            <button onclick="deleteFile('${filename}')">Delete</button>
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