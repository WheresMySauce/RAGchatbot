let sessionToDelete = null;
// MODAL = CỬA SỔ
// Hiển thị cái cửa sổ tạo session và xóa sesion
function openModal() {
    document.getElementById('createSessionModal').style.display = 'block';
}
// Đóng cái cửa sổ tạo session và xóa sesion
function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}
// mở cái session đó ra nhảy vào khung chat
function openSession(sessionId) {
    window.location.href = '/session/' + sessionId;
}
// xóa sesion
function deleteSession(event, sessionId) {
    event.stopPropagation();
    sessionToDelete = sessionId;
    document.getElementById('deleteSessionModal').style.display = 'block';
}
function createSession(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);

    fetch('/create_session', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.reload();
        } else {
            // Show an alert with the error message
            alert(data.message);
        }
    })
    // .catch(error => {
    //     console.error('Error:', error);
    //     alert('An error occurred while creating the session');
    // });
}
//confirm xóa session
function confirmDelete() {
    if (sessionToDelete) {
        fetch("/delete_session", {  // xai route delete_session,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ session_id: sessionToDelete }),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Failed to delete session: ' + (data.error || 'Unknown error'));
            }
        })
        .catch((error) => {
            console.error('Error:', error);
            alert('An error occurred while deleting the session: ' + error.message);
        });
    }
    closeModal('deleteSessionModal');
}
// Bấm ra ngoài để tắt cửa sổ 
window.onclick = function(event) {
    if (event.target == document.getElementById('createSessionModal')) {
        closeModal('createSessionModal');
    }
    if (event.target == document.getElementById('deleteSessionModal')) {
        closeModal('deleteSessionModal');
    }
}