import streamlit as st
import requests
import base64

# Cấu hình GitHub của fen
GITHUB_USER = "mrspytro"
GITHUB_REPO = "Form_Auto"
GITHUB_FOLDER = "templates"

# Lấy token (đảm bảo fen đã dán mã mới nhất vào Secrets hoặc trực tiếp ở đây)
GITHUB_TOKEN = "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"

# HEADER CHUẨN CHO FINE-GRAINED TOKEN
# Fen lưu ý dùng 'Bearer' và thêm version API để GitHub xác thực đúng
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN.strip()}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

def upload_to_github(file_name, file_bytes):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{GITHUB_FOLDER}/{file_name}"
    
    # Mã hóa Base64 chuẩn cho nội dung file
    encoded_content = base64.b64encode(file_bytes).decode("utf-8")
    
    data = {
        "message": f"Cập nhật mẫu hồ sơ: {file_name}",
        "content": encoded_content,
        "branch": "main" 
    }
    
    # Kiểm tra file tồn tại để lấy SHA (tránh lỗi 422 khi ghi đè)
    check_res = requests.get(url, headers=HEADERS)
    if check_res.status_code == 200:
        data["sha"] = check_res.json()["sha"]

    res = requests.put(url, headers=HEADERS, json=data)
    
    if res.status_code in [200, 201]:
        return True, "Thành công"
    else:
        # Trả về chi tiết lỗi để fen dễ debug
        error_info = res.json().get('message', 'Unknown Error')
        return False, f"GitHub Error {res.status_code}: {error_info}"