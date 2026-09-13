import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- ตั้งค่าการเชื่อมต่อ Google Sheets ---
def get_sheet():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    # ดึงค่าจาก Secrets
    creds_dict = {
        "type": st.secrets["gcp_service_account"]["type"],
        "project_id": st.secrets["gcp_service_account"]["project_id"],
        "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
        "private_key": st.secrets["gcp_service_account"]["private_key"].replace("\\n", "\n"),
        "client_email": st.secrets["gcp_service_account"]["client_email"],
        "client_id": st.secrets["gcp_service_account"]["client_id"],
        "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
        "token_uri": st.secrets["gcp_service_account"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"],
    }
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client.open_by_key(st.secrets["sheet_id"]).worksheet("ratings")

@st.cache_data(ttl=60)
def load_data():
    data = get_sheet().get_all_records()
    return pd.DataFrame(data)

# --- หน้า UI ---
st.title("Anime Rating System")

df = load_data()

# Form รับค่า
with st.form("rating_form"):
    user = st.text_input("ชื่อผู้ใช้")
    anime_name = st.text_input("ชื่ออนิเมะ")
    score = st.slider("คะแนน", 1, 10, 5)
    year = st.number_input("ปีที่ฉาย", 1990, 2026, 2024)
    submitted = st.form_submit_button("บันทึกข้อมูล")

    if submitted:
        if user and anime_name:
            # สร้าง ID อัตโนมัติ (ถ้ามีข้อมูลแล้ว เอาเลข Max + 1)
            new_id = int(df["id"].max()) + 1 if not df.empty else 1
            
            get_sheet().append_row([new_id, user, anime_name, score, year])
            st.success("บันทึกสำเร็จ!")
            st.rerun() # Refresh หน้าจอ
        else:
            st.error("กรุณากรอกข้อมูลให้ครบ")

# แสดงผลข้อมูล
st.subheader("รายการอนิเมะทั้งหมด")
st.dataframe(df)