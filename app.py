import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px

# --- ตั้งค่าหน้าเว็บให้รองรับมือถือ ---
st.set_page_config(page_title="Anime Hub", page_icon="🎬", layout="centered")

# --- ฟังก์ชันเชื่อมต่อ Google Sheets ---
@st.cache_resource
def get_gspread_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds).open_by_key(st.secrets["sheet_id"])

@st.cache_data(ttl=30)
def load_data(sheet_name):
    sheet = get_gspread_client().worksheet(sheet_name)
    return pd.DataFrame(sheet.get_all_records())

def append_data(sheet_name, row_data):
    sheet = get_gspread_client().worksheet(sheet_name)
    sheet.append_row(row_data)
    st.cache_data.clear() # ล้างแคชเพื่อให้ข้อมูลใหม่แสดงทันที

# --- จัดการ Session ---
if "username" not in st.session_state:
    st.session_state.username = None

# --- หน้า Login ---
if not st.session_state.username:
    st.markdown("<h2 style='text-align: center;'>🔐 เข้าสู่ระบบ</h2>", unsafe_allow_html=True)
    users_df = load_data("user")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login", use_container_width=True) # ปุ่มเต็มจอสำหรับมือถือ
        
        if submit:
            # ตรวจสอบรหัสผ่านแบบง่าย (โปรเจ็คเล็ก)
            users_df["password"] = users_df["password"].astype(str)
            valid = users_df[(users_df["username"] == username) & (users_df["password"] == str(password))]
            if not valid.empty:
                st.session_state.username = username
                st.rerun()
            else:
                st.error("ชื่อผู้ใช้ หรือ รหัสผ่านไม่ถูกต้อง")
    st.stop() # หยุดการทำงานไม่ให้แสดงหน้าอื่นจนกว่าจะ Login

# --- UI หลัก (หลัง Login) ---
st.markdown(f"**👤 ยินดีต้อนรับ:** {st.session_state.username}")

# ใช้ Tabs เพื่อประหยัดพื้นที่บนมือถือ
tab1, tab2 = st.tabs(["⭐ ให้คะแนน", "📊 แดชบอร์ด"])

# โหลดข้อมูล
anime_df = load_data("anime_list")
recieve_df = load_data("recieve")

with tab1:
    st.subheader("รีวิวอนิเมะเรื่องโปรด")
    with st.form("rating_form"):
        # ดึงชื่ออนิเมะมาทำ Dropdown
        anime_names = anime_df["name"].tolist() if not anime_df.empty else []
        selected_anime = st.selectbox("เลือกอนิเมะ", anime_names)
        
        ratings = st.slider("คะแนน (1-10)", 1, 10, 5)
        submitted = st.form_submit_button("💾 บันทึกคะแนน", use_container_width=True)

        if submitted:
            if selected_anime:
                # หา id ถัดไป
                new_id = int(recieve_df["id"].max()) + 1 if not recieve_df.empty else 1
                # ดึงปีจากตาราง anime_list
                year = int(anime_df[anime_df["name"] == selected_anime]["year"].values[0])
                
                # บันทึกลงตาราง recieve
                append_data("recieve", [new_id, st.session_state.username, selected_anime, ratings, year])
                st.toast("บันทึกข้อมูลสำเร็จ! 🎉") # ใช้ toast แทนเด้ง error ใหญ่ๆ
                st.rerun()
            else:
                st.error("ไม่พบข้อมูลอนิเมะ")

with tab2:
    st.subheader("📈 สรุปผลเรตติ้งทั้งหมด")
    
    if recieve_df.empty:
        st.info("ยังไม่มีข้อมูลรีวิว")
    else:
        # สรุปตัวเลข
        col1, col2 = st.columns(2)
        col1.metric("จำนวนรีวิวทั้งหมด", f"{len(recieve_df)} รายการ")
        col2.metric("คะแนนเฉลี่ยรวม", f"{recieve_df['ratings'].mean():.1f} ดาว")
        
        # กราฟแท่งจัดอันดับอนิเมะ (ปรับให้สวยและดูบนมือถือได้)
        st.markdown("**🏆 คะแนนเฉลี่ยรายเรื่อง**")
        avg_rating = recieve_df.groupby("anime_name")["ratings"].mean().reset_index()
        avg_rating = avg_rating.sort_values("ratings", ascending=True)
        
        fig = px.bar(avg_rating, x="ratings", y="anime_name", orientation='h', 
                     color="ratings", color_continuous_scale="Viridis", height=300)
        fig.update_layout(xaxis_title="คะแนน", yaxis_title="", margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)
        
        # แสดงข้อมูลล่าสุด
        st.markdown("**🕒 รีวิวล่าสุด**")
        # ซ่อน index และแสดง 5 รายการล่าสุด
        st.dataframe(recieve_df.tail(5).sort_values("id", ascending=False), use_container_width=True, hide_index=True)