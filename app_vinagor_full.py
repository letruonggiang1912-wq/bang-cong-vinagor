# app.py — Tra cứu Bảng Công Vinagor (Streamlit)
# (Logo lớn đầu trang, Upload Excel, Xuất PDF, Tự nhận tháng/năm)

import os
import io
from datetime import datetime
import streamlit as st
import pandas as pd
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.units import mm

APP_TITLE = 'Tra cứu Bảng Công — Vinagor'
SHEET_NAME = 'BẢNG CÔNG'
ADMIN_PIN = os.getenv('ADMIN_PIN', '1234')
LOGO_PATH = 'assets/logo.png'

st.set_page_config(page_title=APP_TITLE, page_icon='📊', layout='wide')

def normalize_cols(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df

def read_sheet(file_bytes):
    try:
        df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=SHEET_NAME)
    except ValueError:
        with pd.ExcelFile(io.BytesIO(file_bytes)) as xls:
            lower = {s.lower(): s for s in xls.sheet_names}
            if SHEET_NAME.lower() in lower:
                df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=lower[SHEET_NAME.lower()])
            else:
                raise
    return normalize_cols(df)

def load_logo_bytes():
    try:
        if os.path.exists(LOGO_PATH):
            with open(LOGO_PATH, 'rb') as f:
                return f.read()
    except Exception:
        pass
    return st.session_state.get('logo_bytes')

def infer_month_year():
    now = datetime.now()
    return now.month, now.year

def build_pdf(row, day_cols, month, year):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=16*mm, bottomMargin=16*mm)
    story, styles = [], getSampleStyleSheet()

    logo = load_logo_bytes()
    if logo:
        story.append(RLImage(io.BytesIO(logo), width=70*mm, height=25*mm))
        story.append(Spacer(1, 8))

    story.append(Paragraph(f'<b>PHIẾU CÔNG THÁNG {month:02d}/{year}</b>', styles['Title']))
    story.append(Spacer(1, 8))

    def safe(v): return '' if pd.isna(v) else str(v)

    fields = [(c, safe(row.get(c))) for c in row.index if c not in day_cols]
    table = Table([[k, ':', v] for k, v in fields], colWidths=[40*mm, 5*mm, 120*mm])
    table.setStyle(TableStyle([('FONTNAME', (0,0), (-1,-1), 'Helvetica'), ('FONTSIZE', (0,0), (-1,-1), 9)]))
    story.append(table)
    story.append(Spacer(1, 10))

    if day_cols:
        day_cols = sorted(day_cols, key=lambda x: int(str(x)))
        data = [['Ngày'] + [str(d) for d in day_cols], ['Công'] + [safe(row.get(d)) for d in day_cols]]
        t = Table(data)
        t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.25, colors.grey)]))
        story.append(t)

    story.append(Spacer(1, 12))
    story.append(Paragraph('© Vinagor — Hệ thống tra cứu bảng công nội bộ', styles['Normal']))
    doc.build(story)
    buf.seek(0)
    return buf.read()

def render_header():
    col1, col2 = st.columns([1, 3])
    with col1:
        logo = load_logo_bytes()
        if logo: st.image(Image.open(io.BytesIO(logo)), use_column_width=False)
    with col2:
        st.title(APP_TITLE)
        st.caption('Hệ thống tra cứu bảng công trực tuyến — Công ty Cổ phần Vinagor')

render_header()
menu = st.sidebar.radio('Chọn trang', ['Công nhân', 'Quản lý', 'Hướng dẫn'])

if menu == 'Hướng dẫn':
    st.markdown('1️⃣ Trang Quản lý để upload Excel.\n2️⃣ Trang Công nhân để nhập MNV xem phiếu công.')

elif menu == 'Quản lý':
    st.subheader('Trang Quản lý')
    pin = st.text_input('Nhập PIN', type='password')
    if pin != ADMIN_PIN:
        st.stop()
    file = st.file_uploader('Tải file Excel (xlsx)', type='xlsx')
    if file:
        df = read_sheet(file.read())
        st.session_state['data'] = df
        st.success(f'Đã nạp {len(df)} dòng từ sheet {SHEET_NAME}.')
        st.dataframe(df.head(10))
    logo = st.file_uploader('Tải logo (tùy chọn)', type=['png','jpg'])
    if logo: st.session_state['logo_bytes'] = logo.read()

elif menu == 'Công nhân':
    st.subheader('Tra cứu thông tin cá nhân')
    df = st.session_state.get('data')
    if df is None:
        st.warning('Chưa có dữ liệu, vui lòng upload Excel trước.')
        st.stop()
    mnv = st.text_input('Nhập MNV')
    if not mnv: st.stop()
    res = df[df['MNV'].astype(str).str.lower() == mnv.strip().lower()]
    if res.empty:
        st.warning('Không tìm thấy MNV này.')
    else:
        st.dataframe(res, use_container_width=True)
        month, year = infer_month_year()
        pdf = build_pdf(res.iloc[0], [c for c in df.columns if str(c).isdigit()], month, year)
        st.download_button('🧾 Tải phiếu công (PDF)', pdf, f'phieu_cong_{mnv}_{year}{month:02d}.pdf', 'application/pdf')
