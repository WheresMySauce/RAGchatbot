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
//confirm xóa session
function confirmDelete() {
    if (sessionToDelete) {
        fetch("{{ url_for('delete_session') }}", {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ session_id: sessionToDelete }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Failed to delete session');
            }
        })
        .catch((error) => {
            console.error('Error:', error);
            alert('An error occurred while deleting the session');
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