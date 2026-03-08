import streamlit as st
from docxtpl import DocxTemplate
from docx import Document
import io, re, json, smtplib
import mammoth
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

# --- HÀM XỬ LÝ BIẾN ---
def get_variables_v8(file_stream):
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
            text = ""
            if element.tag.endswith('p'):
                para = [p for p in doc.paragraphs if p._element == element]
                if para: text = para[0].text
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
            matches = re.findall(pattern, text)
            for var in matches:
                if var not in seen:
                    res = process_match(var)
                    if res: ordered_vars.append(res); seen.add(var)
        return ordered_vars
    except: return []

# --- GIAO DIỆN XÁC THỰC (LOGIN) ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
    
    if st.session_state.password_correct:
        return True

    st.title("🔐 Truy cập nội bộ")
    pwd = st.text_input("Nhập mật khẩu để tiếp tục", type="password")
    if st.button("Đăng nhập"):
        if pwd == "123": # Fen có thể đổi mật khẩu tại đây
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("Sai mật khẩu!")
    return False

# --- GIAO DIỆN CHÍNH ---
if check_password():
    st.set_page_config(page_title="Hồ sơ Bank Pro", layout="wide")
    
    # CSS A4 Preview
    st.markdown("<style>.cat-box { background: #f0f2f6; padding: 12px; border-left: 6px solid #1976d2; margin: 20px 0; } .paper-container { background: #525659; padding: 30px 0; display: flex; justify-content: center; } .a4-page { background: white; width: 210mm; padding: 20mm; box-shadow: 0 0 15px rgba(0,0,0,0.5); color: black; font-family: 'Times New Roman', serif; }</style>", unsafe_allow_html=True)

    st.title("🏦 Hệ thống Biểu mẫu Sacombank")
    
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {}

    with st.sidebar:
        st.header("💾 Quản lý dữ liệu")
        uploaded_json = st.file_uploader("Nạp bản nháp (.json)", type=["json"])
        if uploaded_json:
            st.session_state.form_data.update(json.load(uploaded_json))
            st.success("Đã nạp dữ liệu!")
        
        if st.button("🗑️ Xóa sạch form"):
            st.session_state.form_data = {}
            st.rerun()

    uploaded_docx = st.file_uploader("Nạp mẫu Word (.docx)", type=["docx"])

    if uploaded_docx:
        file_bytes = io.BytesIO(uploaded_docx.read())
        vars_list = get_variables_v8(io.BytesIO(file_bytes.getvalue()))
        
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
                
                # Mammoth Preview
                html_res = mammoth.convert_to_html(out_bio)
                st.markdown(f'<div class="paper-container"><div class="a4-page">{html_res.value}</div></div>', unsafe_allow_html=True)
                
                st.divider()
                c1, c2 = st.columns(2)
                with c1:
                    st.download_button("💾 LƯU BẢN NHÁP (.json)", data=json.dumps(st.session_state.form_data, ensure_ascii=False), file_name="Draft.json")
                with c2:
                    st.download_button("🚀 XUẤT FILE WORD", data=out_bio.getvalue(), file_name=f"Filled_{uploaded_docx.name}")
            except Exception as e: st.error(f"Lỗi: {e}")