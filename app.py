import streamlit as st
from docxtpl import DocxTemplate
from docx import Document
import io, re, json, requests, base64
import mammoth

# --- CẤU HÌNH GITHUB ---
GITHUB_USER = "mrspytro"  # Thay bằng username của fen
GITHUB_REPO = "Form_Auto" # Thay bằng tên Repo
GITHUB_FOLDER = "templates"
# Token này nên được lưu trong Streamlit Secrets để bảo mật
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "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")

# --- HÀM XỬ LÝ GITHUB API ---
def get_online_templates():
    """Lấy danh sách file từ thư mục templates trên GitHub"""
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{GITHUB_FOLDER}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            return {f['name']: f['download_url'] for f in res.json() if f['name'].endswith('.docx')}
    except: return {}
    return {}

def upload_to_github(file_name, file_bytes):
    """Đẩy file lên GitHub thông qua API"""
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{GITHUB_FOLDER}/{file_name}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Content-Type": "application/json"}
    
    # Mã hóa file sang Base64
    encoded_content = base64.b64encode(file_bytes).decode("utf-8")
    
    data = {
        "message": f"Bà xã cập nhật mẫu: {file_name}",
        "content": encoded_content,
        "branch": "main"
    }
    
    # Kiểm tra xem file đã tồn tại chưa để lấy SHA (nếu cần cập nhật)
    check_res = requests.get(url, headers=headers)
    if check_res.status_code == 200:
        data["sha"] = check_res.json()["sha"]

    res = requests.put(url, headers=headers, json=data)
    return res.status_code in [200, 201]

# --- LOGIC XỬ LÝ BIẾN WORD ---
def get_variables_final(file_stream):
    try:
        doc = Document(file_stream)
        ordered_vars = []
        seen = set()
        pattern = r"\{\{\s*(\w+)\s*\}\}"
        
        def process_match(match_text):
            m = re.match(r"([a-zA-Z]+)(\d+)_((?:(?!__).)+)(?:__(.*))?", match_text)
            if m:
                prefix, num, raw_name, note = m.groups()
                p_lower = prefix.lower()
                v_type = 'title' if p_lower == 't' else ('checkbox' if p_lower == 'cb' else 'field')
                display_name = raw_name.replace("_", " ").strip()
                return {
                    'original': match_text, 'type': v_type,
                    'label': display_name.upper() if v_type == 'title' else f"Mục {num}: {display_name.title()}",
                    'note': (note.replace("_", " ") if note else "")
                }
            return None

        for element in doc.element.body:
            if element.tag.endswith('p'):
                para = [p for p in doc.paragraphs if p._element == element]
                if para: 
                    matches = re.findall(pattern, para[0].text)
                    for var in matches:
                        if var not in seen:
                            res = process_match(var)
                            if res: ordered_vars.append(res); seen.add(var)
            elif element.tag.endswith('tbl'):
                table = [t for t in doc.tables if t._element == element]
                if table:
                    for row in table[0].rows:
                        for cell in row.cells:
                            matches = re.findall(pattern, cell.text)
                            for var in matches:
                                if var not in seen:
                                    res = process_match(var)
                                    if res: ordered_vars.append(res); seen.add(var)
        return ordered_vars
    except: return []

# --- GIAO DIỆN APP ---
st.set_page_config(page_title="Hệ thống Hồ sơ Tự động", layout="wide")

# CSS Paper View
st.markdown("<style>.cat-box { background: #f0f2f6; padding: 12px; border-left: 6px solid #1976d2; margin: 20px 0; } .paper-container { background: #525659; padding: 30px 0; display: flex; justify-content: center; } .a4-page { background: white; width: 210mm; padding: 20mm; box-shadow: 0 0 15px rgba(0,0,0,0.5); color: black; font-family: 'Times New Roman', serif; }</style>", unsafe_allow_html=True)

st.title("🏦 Quản lý Hồ sơ Sacombank Online")

if 'form_data' not in st.session_state:
    st.session_state.form_data = {}

# --- SIDEBAR: KHO MẪU & UPLOAD ---
with st.sidebar:
    st.header("📂 Kho mẫu hồ sơ")
    # Tự động lấy danh sách từ GitHub
    online_templates = get_online_templates()
    
    if online_templates:
        selected_name = st.selectbox("Chọn mẫu có sẵn:", ["--- Chọn mẫu ---"] + list(online_templates.keys()))
        current_template_url = online_templates.get(selected_name)
    else:
        st.warning("Thư mục /templates đang trống.")
        current_template_url = None

    st.divider()
    st.header("📤 Lưu trữ mẫu mới")
    new_template = st.file_uploader("Tải mẫu .docx lên kho lưu trữ GitHub", type=["docx"])
    if new_template:
        if st.button("Lưu lên GitHub"):
            with st.spinner("Đang tải lên..."):
                success = upload_to_github(new_template.name, new_template.getvalue())
                if success:
                    st.success(f"Đã lưu mẫu {new_template.name} thành công!")
                    st.rerun()
                else:
                    st.error("Lỗi khi tải lên GitHub.")

# --- XỬ LÝ FILE WORD ---
file_bytes = None
if current_template_url:
    res = requests.get(current_template_url)
    file_bytes = io.BytesIO(res.content)

if file_bytes:
    vars_list = get_variables_final(io.BytesIO(file_bytes.getvalue()))
    
    tab_in, tab_pre = st.tabs(["📝 NHẬP LIỆU", "🔍 PREVIEW & XUẤT FILE"])

    with tab_in:
        for item in vars_list:
            key = item['original']
            if item['type'] == 'title':
                st.markdown(f'<div class="cat-box">### 📂 {item["label"]}</div>', unsafe_allow_html=True)
                st.session_state.form_data[key] = ""
            else:
                c1, c2 = st.columns([0.6, 0.4])
                with c1:
                    val = st.session_state.form_data.get(key, False if item['type'] == 'checkbox' else "")
                    if item['type'] == 'checkbox':
                        st.session_state.form_data[key] = st.checkbox(item['label'], value=val, key=f"cb_{key}")
                    else:
                        st.session_state.form_data[key] = st.text_input(item['label'], value=val, key=f"tx_{key}")
                with c2:
                    if item['note']: st.write(""); st.caption(f"💡 *{item['note']}*")

    with tab_pre:
        render_ctx = {k: ("☑" if v is True else "☐" if v is False else v) for k, v in st.session_state.form_data.items()}
        try:
            doc = DocxTemplate(io.BytesIO(file_bytes.getvalue()))
            doc.render(render_ctx)
            out_bio = io.BytesIO(); doc.save(out_bio); out_bio.seek(0)
            
            # Preview A4
            html_res = mammoth.convert_to_html(out_bio)
            st.markdown(f'<div class="paper-container"><div class="a4-page">{html_res.value}</div></div>', unsafe_allow_html=True)
            
            st.divider()
            st.download_button("🚀 XUẤT FILE WORD HOÀN TẤT", data=out_bio.getvalue(), file_name=f"Filled_{selected_name}")
        except Exception as e: st.error(f"Lỗi hiển thị: {e}")
else:
    st.info("👈 Hãy chọn một mẫu từ kho lưu trữ hoặc tải lên mẫu mới ở thanh bên trái.")