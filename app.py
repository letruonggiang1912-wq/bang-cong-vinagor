#

import os
import io
from datetime import datetime
import streamlit as st
import pandas as pd
from PIL import Image

# PDF (ReportLab)
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.units import mm

APP_TITLE = "Tra cứu Bảng Công — Vinagor"
SHEET_NAME = "BẢNG CÔNG"
DEFAULT_IMPORT_COLUMNS = [
    "MNV", "TÊN", "BP", "Ngày công", "GIỜ THƯỜNG", "giờ lễ", "Chuyên cần",
    "KPIs Chất Lượng", "KPIs Khối Lượng", "Thưởng KPIs", "TĂNG CA", "ĂN CA",
]

# 🔐 PIN quản trị (lấy từ Secrets trên Streamlit Cloud)
ADMIN_PIN = os.getenv("ADMIN_PIN", "1234")

# 🔖 Logo: đặt file tại ./assets/logo.png trong repo (hoặc upload tạm ở trang Quản lý)
LOGO_PATH = os.getenv("LOGO_PATH", "assets/logo.png")

st.set_page_config(page_title=APP_TITLE, page_icon="📊", layout="wide")

# --- Helper functions ---

def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def read_sheet(file_bytes: bytes, sheet_name: str = SHEET_NAME) -> pd.DataFrame:
    try:
        df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name)
    except ValueError:
        with pd.ExcelFile(io.BytesIO(file_bytes)) as xls:
            candidates = {s.lower(): s for s in xls.sheet_names}
            if sheet_name.lower() in candidates:
                df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=candidates[sheet_name.lower()])
            else:
                raise
    return normalize_cols(df)


def store_df(df: pd.DataFrame):
    st.session_state["df_bang_cong"] = df


def get_df() -> pd.DataFrame | None:
    return st.session_state.get("df_bang_cong")


def get_daily_cols(df: pd.DataFrame):
    day_cols = []
    for c in df.columns:
        s = str(c).strip()
        if s.isdigit() and 1 <= int(s) <= 31:
            day_cols.append(c)
    return day_cols


def load_logo_bytes() -> bytes | None:
    # Ưu tiên file cố định trong repo
    try:
        if os.path.exists(LOGO_PATH):
            with open(LOGO_PATH, "rb") as f:
                return f.read()
    except Exception:
        pass
    # Nếu quản lý đã upload tạm trong phiên
    return st.session_state.get("logo_bytes")


def infer_month_year(df: pd.DataFrame) -> tuple[int, int]:
    """Tự nhận diện tháng/năm: nếu không có cột tháng, trả về tháng/năm hiện tại."""
    now = datetime.now()
    return now.month, now.year


def to_safe(val):
    return "" if pd.isna(val) else str(val)


def build_pdf(row: pd.Series, day_cols: list[str], month: int, year: int) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=16*mm, bottomMargin=16*mm)
    story = []
    styles = getSampleStyleSheet()

    # Header với logo + tiêu đề
    logo_bytes = load_logo_bytes()
    if logo_bytes:
        rl_img = RLImage(io.BytesIO(logo_bytes), width=45*mm, height=16*mm)
        story.append(rl_img)
        story.append(Spacer(1, 6))

    title = f"PHIẾU CÔNG THÁNG {month:02d}/{year}"
    story.append(Paragraph(f"<b>{title}</b>", styles['Title']))
    story.append(Spacer(1, 8))

    # Thông tin chung
    fields = [
        ("MNV", to_safe(row.get("MNV"))),
        ("Họ và tên", to_safe(row.get("TÊN"))),
        ("Bộ phận", to_safe(row.get("BP"))),
        ("Số ngày công", to_safe(row.get("Ngày công"))),
        ("Giờ thường", to_safe(row.get("GIỜ THƯỜNG"))),
        ("Giờ lễ", to_safe(row.get("giờ lễ"))),
        ("Tăng ca", to_safe(row.get("TĂNG CA"))),
        ("KPI Chất lượng", to_safe(row.get("KPIs Chất Lượng"))),
        ("KPI Khối lượng", to_safe(row.get("KPIs Khối Lượng"))),
        ("Thưởng KPI", to_safe(row.get("Thưởng KPIs"))),
        ("Ăn ca", to_safe(row.get("ĂN CA"))),
        ("Ghi chú", to_safe(row.get("Ghi chú")) if "Ghi chú" in row else ""),
    ]
    # Tổng lương nếu có cột phù hợp
    for salary_key in ["Lương", "Luong", "Tổng lương", "Tong luong", "TỔNG LƯƠNG"]:
        if salary_key in row.index:
            fields.append(("Tổng lương", to_safe(row.get(salary_key))))
            break

    info_table = Table([[f"{k}", f": {v}"] for k, v in fields], hAlign='LEFT', colWidths=[38*mm, 120*mm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 8))

    # Bảng 1..31 ngày (nếu có)
    if day_cols:
        days = [str(d) for d in sorted([int(str(c)) for c in day_cols])]
        values = [to_safe(row.get(int(d) if int(d) in row.index else d)) for d in days]
        # chia làm 2 hàng để gọn
        mid = len(days)//2
        data = [ ["Ngày"] + days[:mid], ["Công"] + values[:mid] ]
        if mid < len(days):
            data += [ ["Ngày"] + days[mid:], ["Công"] + values[mid:] ]
        table = Table(data, hAlign='LEFT')
        table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
            ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ]))
        story.append(Spacer(1, 6))
        story.append(table)
        story.append(Spacer(1, 8))

    # Ký xác nhận
    sig_table = Table([
        ["Xác nhận của nhân viên", "Phòng nhân sự ký xác nhận"],
        ["


........................................", "


........................................"],
    ], colWidths=[80*mm, 80*mm], hAlign='LEFT')
    sig_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
    ]))
    story.append(Spacer(1, 8))
    story.append(sig_table)

    # Footer
    story.append(Spacer(1, 12))
    story.append(Paragraph("© Vinagor — Hệ thống tra cứu bảng công nội bộ", styles['Normal']))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()

# --- Giao diện ---

# Header với logo nếu có
logo_bytes_for_header = load_logo_bytes()
col1, col2 = st.columns([1,3])
with col1:
    if logo_bytes_for_header:
        st.image(Image.open(io.BytesIO(logo_bytes_for_header)), caption=None)
with col2:
    st.title(APP_TITLE)
    st.caption("Hệ thống tra cứu bảng công trực tuyến — Công ty Cổ phần Vinagor")

menu = st.sidebar.radio("Chọn trang", ["Công nhân", "Quản lý", "Hướng dẫn"], index=0)

if menu == "Hướng dẫn":
    st.markdown(
        """
        ### 📘 Hướng dẫn sử dụng
        1. **Trang Quản lý** → nhập **PIN** → **Tải file Excel** (có sheet `BẢNG CÔNG`).
        2. Sau khi upload, dữ liệu lưu tạm (sẽ mất nếu khởi động lại app).
        3. **Trang Công nhân** → nhập **MNV** hoặc **Tên** để xem dữ liệu cá nhân.

        👉 Triển khai web miễn phí tại *Streamlit Cloud*.
        """
    )

elif menu == "Quản lý":
    st.subheader("Trang Quản lý")
    pin = st.text_input("Nhập PIN quản trị", type="password")
    if pin != ADMIN_PIN:
        st.info("Nhập đúng PIN để tải file Excel mới.")
        st.stop()

    # Upload Excel
    file = st.file_uploader("Tải file Excel (xlsx)", type=["xlsx"])
    if file is not None:
        try:
            df = read_sheet(file.read(), sheet_name=SHEET_NAME)
            st.session_state["df_bang_cong"] = df
            st.success(f"Đã nạp {len(df)} dòng từ sheet '{SHEET_NAME}'.")
            st.dataframe(df.head(20), use_container_width=True)
        except Exception as e:
            st.error(f"Không đọc được sheet '{SHEET_NAME}'. Lỗi: {e}")

    # Upload logo (tùy chọn) nếu chưa có file trong repo
    st.markdown("#### Logo Vinagor (tùy chọn nếu chưa đặt ở assets/logo.png)")
    logo_up = st.file_uploader("Tải logo PNG/JPG", type=["png","jpg","jpeg"], key="logo")
    if logo_up is not None:
        st.session_state["logo_bytes"] = logo_up.read()
        st.success("Đã nạp logo cho phiên hiện tại.")

    # Tải CSV hiện tại
    if get_df() is not None:
        st.download_button(
            "⬇️ Tải dữ liệu hiện tại (CSV)",
            data=get_df().to_csv(index=False).encode("utf-8-sig"),
            file_name="bang_cong.csv",
            mime="text/csv",
        )

elif menu == "Công nhân":
    st.subheader("Tra cứu thông tin cá nhân")
    df = get_df()
    if df is None:
        st.warning("Chưa có dữ liệu. Vui lòng nhờ quản lý tải file Excel trước.")
        st.stop()

    # Month-year auto
    month, year = infer_month_year(df)

    mnv = st.text_input("Nhập MNV của bạn")
    result = pd.DataFrame()

    if mnv and "MNV" in df.columns:
        mask = df["MNV"].astype(str).str.strip().str.lower() == mnv.strip().lower()
        result = df[mask]

    if not result.empty:
        base_cols = [c for c in DEFAULT_IMPORT_COLUMNS if c in result.columns]
        day_cols = get_daily_cols(result)

        st.markdown("### Thông tin tổng quan")
        st.dataframe(result[base_cols], use_container_width=True)

        if day_cols:
            st.markdown("### Chấm công theo ngày")
            st.dataframe(result[day_cols], use_container_width=True)

        # Nút tải PDF
        row = result.iloc[0]
        pdf_bytes = build_pdf(row, day_cols, month, year)
        st.download_button(
            label="🧾 Tải phiếu công (PDF)",
            data=pdf_bytes,
            file_name=f"phieu_cong_{row.get('MNV','nv')}_{year}{month:02d}.pdf",
            mime="application/pdf",
        )

    else:
        st.info("Không tìm thấy MNV hoặc chưa nhập MNV.")

    st.markdown("---")
    name = st.text_input("(Dự phòng) Nhập TÊN để tìm")
    if name and "TÊN" in df.columns:
        mask = df["TÊN"].astype(str).str.strip().str.lower() == name.strip().lower()
        rs = df[mask]
        if not rs.empty:
            st.dataframe(rs, use_container_width=True)
        else:
            st.warning("Không tìm thấy tên khớp hoàn toàn.")

