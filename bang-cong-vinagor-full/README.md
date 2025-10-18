# 📘 Bảng Công Vinagor (Streamlit)

Ứng dụng tra cứu bảng công trực tuyến cho Công ty Cổ phần Vinagor.

## 🚀 Cách chạy cục bộ
```bash
pip install -r requirements.txt
streamlit run app.py
```

## ☁️ Deploy lên Streamlit Cloud
1. Tạo repo trên GitHub (vd: bang-cong-vinagor)
2. Upload toàn bộ file:
   - app.py
   - requirements.txt
   - thư mục assets/logo.png
3. Vào https://share.streamlit.io → New App → chọn repo + file app.py
4. Thêm mã PIN quản lý:
```
ADMIN_PIN = 5678
```

Sau khi deploy, truy cập web tại:  
`https://bang-cong-vinagor.streamlit.app`
