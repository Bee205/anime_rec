import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px

# --- ตั้งค่าหน้าเว็บให้รองรับมือถือ ---
st.set_page_config(page_title="Anime Hub", page_icon="🎬", layout="centered", initial_sidebar_state="expanded")

# --- CSS แต่ง UI ให้ดู Modern ---
st.markdown("""
    <style>
    /* แต่งปุ่มให้โค้งมนและเด่นขึ้น */
    div.stButton > button {
        border-radius: 10px;
        font-weight: bold;
        border: 2px solid #FF4B4B;
    }
    /* แต่งตัวเลขสถิติให้สวยขึ้น */
    div[data-testid="stMetricValue"] {
        font-size: 2.2rem;
        color: #FF4B4B;
    }
    </style>
""", unsafe_allow_html=True)

# --- ฟังก์ชันเชื่อมต่อ Google Sheets ---
@st.cache_resource
def get_gspread_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds).open_by_key(st.secrets["sheet_id"])

@st.cache_data(ttl=15) # ดึงข้อมูลใหม่ทุกๆ 15 วินาที
def load_data(sheet_name):
    try:
        sheet = get_gspread_client().worksheet(sheet_name)
        return pd.DataFrame(sheet.get_all_records())
    except Exception as e:
        st.error(f"ไม่พบชีตชื่อ {sheet_name} กรุณาตรวจสอบใน Google Sheets")
        return pd.DataFrame()

def append_data(sheet_name, row_data):
    sheet = get_gspread_client().worksheet(sheet_name)
    sheet.append_row(row_data)
    st.cache_data.clear() # ล้างแคชเพื่อให้ข้อมูลใหม่โชว์ทันที

# --- โหลดข้อมูล ---
anime_df = load_data("anime_list")
recieve_df = load_data("recieve")

# ==========================================
# 🧭 ระบบ Navigation (Navbar ด้านข้าง)
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🎬 Anime Hub</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    # เมนูเลือกหน้า
    page = st.radio(
        "เลือกเมนูการใช้งาน:",
        ["📝 โหวตอนิเมะ (Rate)", "📊 แดชบอร์ดสรุปผล (Dashboard)"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.caption("© 2026 Anime Hub Project")

# ==========================================
# 📄 หน้าที่ 1: หน้าโหวต (ไม่ต้องล็อกอิน)
# ==========================================
if page == "📝 โหวตอนิเมะ (Rate)":
    st.title("✨ รีวิว & ให้คะแนนอนิเมะ")
    st.markdown("เลือกอนิเมะที่คุณชื่นชอบแล้วให้คะแนนความสนุกได้เลย!")
    
    with st.form("rating_form", border=True):
        # เปลี่ยนจากการดึง Session Login เป็นให้พิมพ์ชื่อแทน
        user_name = st.text_input("👤 ชื่อของคุณ (หรือนามแฝง)")
        
        anime_names = anime_df["name"].tolist() if not anime_df.empty else []
        selected_anime = st.selectbox("📺 เลือกอนิเมะ", anime_names)
        
        ratings = st.slider("⭐ ให้คะแนน (1-10)", 1, 10, 5)
        
        submit_btn = st.form_submit_button("🚀 บันทึกคะแนน", use_container_width=True)

        if submit_btn:
            if not user_name:
                st.warning("⚠️ กรุณากรอกชื่อของคุณด้วยครับ")
            elif not selected_anime:
                st.warning("⚠️ กรุณาเลือกอนิเมะ")
            else:
                # หา ID ใหม่
                new_id = int(recieve_df["id"].max()) + 1 if not recieve_df.empty else 1
                # ดึงปีที่ฉาย
                year = int(anime_df[anime_df["name"] == selected_anime]["year"].values[0])
                
                # บันทึกลงชีต recieve
                append_data("recieve", [new_id, user_name, selected_anime, ratings, year])
                st.success("บันทึกข้อมูลสำเร็จ! ขอบคุณสำหรับรีวิวครับ 🎉")
                st.balloons() # ปล่อยลูกโป่งฉลอง

# ==========================================
# 📄 หน้าที่ 2: หน้าแดชบอร์ดสรุปผล
# ==========================================
elif page == "📊 แดชบอร์ดสรุปผล (Dashboard)":
    st.title("📈 แดชบอร์ดสรุปเรตติ้ง")
    
    if recieve_df.empty:
        st.info("ยังไม่มีข้อมูลรีวิวในขณะนี้")
    else:
        # 1. การ์ดสรุปผล (ตัวเลขใหญ่ๆ ดึงดูดสายตา)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("ผู้ร่วมโหวต", f"{recieve_df['user'].nunique()} คน")
        with col2:
            st.metric("รีวิวทั้งหมด", f"{len(recieve_df)} ครั้ง")
        with col3:
            st.metric("คะแนนเฉลี่ยรวม", f"{recieve_df['ratings'].mean():.2f} ⭐")
        
        st.markdown("---")

        # 2. กราฟจัดอันดับอนิเมะ (Top 10)
        st.subheader("🏆 10 อันดับอนิเมะคะแนนสูงสุด")
        
        # คำนวณคะแนนเฉลี่ยและดึงมา 10 อันดับแรก
        avg_rating = recieve_df.groupby("anime_name")["ratings"].mean().reset_index()
        avg_rating = avg_rating.sort_values("ratings", ascending=False).head(10)
        avg_rating = avg_rating.sort_values("ratings", ascending=True) # กลับด้านให้แสดงจากมากไปน้อย (Plotly แถวบนสุดคือข้อมูลท้ายสุด)
        
        # วาดกราฟ
        fig = px.bar(
            avg_rating, x="ratings", y="anime_name", orientation='h', 
            color="ratings", color_continuous_scale="Magma", height=400,
            text_auto='.1f' # แสดงตัวเลขบนกราฟ
        )
        fig.update_layout(
            xaxis_title="คะแนนเฉลี่ย", 
            yaxis_title="", 
            margin=dict(l=0, r=0, t=20, b=0),
            plot_bgcolor="rgba(0,0,0,0)" # ทำให้พื้นหลังกราฟใส
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")

        # 3. ตารางแสดงข้อมูลฟีดล่าสุด
        st.subheader("🕒 ฟีดรีวิวล่าสุด")
        
        # จัดการ Dataframe ใหม่ให้สวยขึ้นก่อนโชว์
        display_df = recieve_df.sort_values("id", ascending=False)[["user", "anime_name", "ratings", "year"]]
        display_df.columns = ["ชื่อผู้โหวต", "อนิเมะ", "คะแนนโหวต", "ปีที่ฉาย"]
        
        # โชว์แค่ 10 รายการล่าสุด และซ่อนเลข Index
        st.dataframe(display_df.head(10), use_container_width=True, hide_index=True)