import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px

# ==========================================
# ⚙️ 1. ตั้งค่าหน้าเว็บ (Page Configuration)
# ==========================================
st.set_page_config(
    page_title="Anime Hub",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🎨 2. ตั้งค่า CSS (ตกแต่ง UI ให้ดู Modern)
# ==========================================
st.markdown("""
    <style>
    /* แต่งปุ่มกดให้โค้งมน ดูทันสมัย */
    div.stButton > button {
        border-radius: 10px;
        font-weight: bold;
        border: 2px solid #FF4B4B;
        transition: all 0.3s ease;
        padding: 10px 20px;
    }
    /* เอฟเฟกต์ตอนเอาเมาส์ชี้ปุ่ม */
    div.stButton > button:hover {
        background-color: #FF4B4B;
        color: white;
        box-shadow: 0px 4px 10px rgba(255, 75, 75, 0.4);
    }
    /* แต่งตัวเลขสถิติ (Metric) ให้เด่นชัด */
    div[data-testid="stMetricValue"] {
        font-size: 2.5rem;
        color: #FF4B4B;
        font-weight: 800;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🔌 3. ระบบเชื่อมต่อ Google Sheets API
# ==========================================
@st.cache_resource
def get_gspread_client():
    # กำหนดสิทธิ์การเข้าถึง (Scope)
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    
    # ดึงข้อมูลจาก st.secrets
    creds_dict = dict(st.secrets["gcp_service_account"])
    
    # จัดการเรื่องขึ้นบรรทัดใหม่ของ private_key
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    
    # สร้าง Credentials และ Authorize
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    
    # เปิด Sheet ตาม ID
    return client.open_by_key(st.secrets["sheet_id"])

# ฟังก์ชันดึงข้อมูล (ทำ Cache ไว้ 15 วินาที)
@st.cache_data(ttl=15)
def load_data(sheet_name):
    try:
        client = get_gspread_client()
        sheet = client.worksheet(sheet_name)
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดชีต {sheet_name}: {e}")
        return pd.DataFrame()

# ฟังก์ชันบันทึกข้อมูลเพิ่ม
def append_data(sheet_name, row_data):
    client = get_gspread_client()
    sheet = client.worksheet(sheet_name)
    sheet.append_row(row_data)
    st.cache_data.clear() # ล้างแคชเพื่อให้เห็นข้อมูลใหม่ทันที

# ==========================================
# 💾 4. โหลดข้อมูลมาใช้งาน
# ==========================================
anime_df = load_data("anime_list")
recieve_df = load_data("recieve")

# ==========================================
# 🧭 5. ระบบ Navigation (Sidebar)
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🎬 Anime Hub</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    # เมนูสำหรับเลือกหน้า
    page = st.radio(
        "เลือกเมนูการใช้งาน:",
        [
            "📝 โหวตอนิเมะ (Rate)", 
            "📊 แดชบอร์ดสรุปผล", 
            "🎯 อนิเมะแนะนำ (Recommend)"
        ],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.caption("© 2026 Anime Hub Project")

# ==========================================
# 📄 หน้าที่ 1: ระบบโหวตอนิเมะ
# ==========================================
if page == "📝 โหวตอนิเมะ (Rate)":
    st.title("✨ รีวิว & ให้คะแนนอนิเมะ")
    st.markdown("มาร่วมแชร์คะแนนความสนุกของอนิเมะที่คุณชื่นชอบกันเถอะ!")
    
    # สร้างแบบฟอร์ม
    with st.form("rating_form", border=True):
        user_name = st.text_input("👤 ชื่อของคุณ (หรือนามแฝง)")
        
        # ดึงรายชื่ออนิเมะมาใส่ใน Dropdown
        anime_names = anime_df["name"].tolist() if not anime_df.empty else []
        selected_anime = st.selectbox("📺 เลือกอนิเมะ", anime_names)
        
        # แถบเลื่อนให้คะแนน
        ratings = st.slider("⭐ ให้คะแนน (1-10)", min_value=1, max_value=10, value=5)
        
        # ปุ่มกดยืนยัน
        submit_btn = st.form_submit_button("🚀 บันทึกคะแนน", use_container_width=True)

        if submit_btn:
            # ตรวจสอบว่ากรอกข้อมูลครบหรือไม่
            if not user_name.strip():
                st.warning("⚠️ กรุณากรอกชื่อของคุณด้วยครับ")
            elif not selected_anime:
                st.warning("⚠️ กรุณาเลือกอนิเมะจากรายการ")
            else:
                # สร้าง ID อัตโนมัติ
                if not recieve_df.empty:
                    new_id = int(recieve_df["id"].max()) + 1
                else:
                    new_id = 1
                    
                # ดึงปีที่ฉายจากตาราง anime_list
                anime_row = anime_df[anime_df["name"] == selected_anime]
                year = int(anime_row["year"].values[0])
                
                # เตรียมข้อมูลสำหรับบันทึก
                row_to_insert = [new_id, user_name, selected_anime, ratings, year]
                
                # บันทึกลง Google Sheets
                append_data("recieve", row_to_insert)
                
                st.success(f"บันทึกคะแนนให้เรื่อง {selected_anime} สำเร็จ! 🎉")
                st.balloons()

# ==========================================
# 📄 หน้าที่ 2: แดชบอร์ดสรุปผลสถิติ
# ==========================================
elif page == "📊 แดชบอร์ดสรุปผล":
    st.title("📈 แดชบอร์ดสรุปเรตติ้ง")
    
    if recieve_df.empty:
        st.info("ยังไม่มีข้อมูลรีวิวในขณะนี้ มาร่วมเป็นคนแรกที่โหวตกันเถอะ!")
    else:
        # 2.1 การ์ดแสดงสถิติรวม (Metrics)
        col1, col2, col3 = st.columns(3)
        with col1:
            total_users = recieve_df['user'].nunique()
            st.metric("ผู้ร่วมโหวต (คน)", f"{total_users:,}")
        with col2:
            total_reviews = len(recieve_df)
            st.metric("รีวิวทั้งหมด (ครั้ง)", f"{total_reviews:,}")
        with col3:
            avg_all = recieve_df['ratings'].mean()
            st.metric("คะแนนเฉลี่ยรวม", f"{avg_all:.2f} ⭐")
        
        st.markdown("---")

        # 2.2 กราฟจัดอันดับอนิเมะ Top 10
        st.subheader("🏆 10 อันดับอนิเมะคะแนนสูงสุด")
        
        # คำนวณคะแนนเฉลี่ยรายเรื่อง
        avg_rating_df = recieve_df.groupby("anime_name")["ratings"].mean().reset_index()
        # ดึง 10 อันดับแรก
        top_10_df = avg_rating_df.sort_values("ratings", ascending=False).head(10)
        # สลับลำดับเพื่อให้กราฟของ Plotly แสดงอันดับ 1 ไว้บนสุด
        top_10_df = top_10_df.sort_values("ratings", ascending=True) 
        
        # สร้างกราฟแท่งแนวนอน
        fig = px.bar(
            top_10_df, 
            x="ratings", 
            y="anime_name", 
            orientation='h', 
            color="ratings", 
            color_continuous_scale="Magma", 
            height=450,
            text_auto='.1f' # แสดงตัวเลขทศนิยม 1 ตำแหน่งบนกราฟ
        )
        
        fig.update_layout(
            xaxis_title="คะแนนเฉลี่ย (เต็ม 10)", 
            yaxis_title="", 
            margin=dict(l=0, r=0, t=30, b=0),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")

        # 2.3 ตารางแสดงฟีดรีวิวล่าสุด
        st.subheader("🕒 ฟีดรีวิวล่าสุดจากผู้ใช้")
        
        # คัดกรองและเรียงข้อมูลล่าสุด
        recent_reviews = recieve_df.sort_values("id", ascending=False)[["user", "anime_name", "ratings", "year"]]
        recent_reviews.columns = ["ชื่อผู้โหวต", "ชื่ออนิเมะ", "คะแนนที่ให้", "ปีที่ฉาย"]
        
        # แสดงตาราง 10 รายการล่าสุด
        st.dataframe(recent_reviews.head(10), use_container_width=True, hide_index=True)

# ==========================================
# 📄 หน้าที่ 3: ระบบแนะนำอนิเมะ (Recommendation)
# ==========================================
elif page == "🎯 อนิเมะแนะนำ (Recommend)":
    st.title("🎯 อนิเมะที่คุณอาจจะชอบ")
    st.markdown("ระบบจะวิเคราะห์และคัดเลือกอนิเมะระดับท็อปที่คุณ **ยังไม่เคยโหวต** มาแนะนำให้ครับ")
    
    if anime_df.empty:
        st.error("⚠️ ไม่พบข้อมูลในฐานข้อมูลอนิเมะ (anime_list)")
    else:
        # ช่องค้นหาชื่อผู้ใช้
        search_user = st.text_input("🔍 พิมพ์ชื่อของคุณ (ระบบจะตัดเรื่องที่คุณเคยดูแล้วออกให้)")
        
        # 3.1 เตรียมข้อมูลตั้งต้น (ชื่อ, แนว, ปี)
        # ตรวจสอบว่ามีคอลัมน์ genre หรือไม่ ถ้าไม่มีให้ใส่ "ไม่ระบุ" ดัก Error ไว้
        if "genre" not in anime_df.columns:
            anime_df["genre"] = "ไม่ระบุ"
            
        recommend_df = anime_df[["name", "genre", "year"]].copy()
        
        # 3.2 นำคะแนนเฉลี่ยมาประกอบร่าง
        if not recieve_df.empty:
            # คำนวณคะแนนเฉลี่ยจากข้อมูลที่มีคนโหวต
            avg_rates = recieve_df.groupby("anime_name")["ratings"].mean().reset_index()
            
            # เอาข้อมูลมารวมกัน (Join)
            recommend_df = pd.merge(recommend_df, avg_rates, left_on="name", right_on="anime_name", how="left")
            
            # ถ้าเรื่องไหนยังไม่มีใครโหวต ค่าจะเป็น NaN ให้เปลี่ยนเป็น 0
            recommend_df["ratings"] = recommend_df["ratings"].fillna(0)
        else:
            # กรณีที่ยังไม่มีใครโหวตเลยสักคน
            recommend_df["ratings"] = 0.0

        # 3.3 กรองข้อมูลเรื่องที่ผู้ใช้เคยดูแล้วออก
        if search_user and not recieve_df.empty:
            # หาลิสต์ชื่ออนิเมะที่ตรงกับชื่อผู้ใช้นี้
            watched_list = recieve_df[recieve_df["user"] == search_user]["anime_name"].tolist()
            
            # คัดเฉพาะเรื่องที่ไม่ได้อยู่ในลิสต์ที่เคยดู
            recommend_df = recommend_df[~recommend_df["name"].isin(watched_list)]
            
            if watched_list:
                st.info(f"👀 ตรวจพบว่าคุณ '{search_user}' เคยให้คะแนนไปแล้ว {len(watched_list)} เรื่อง")

        # 3.4 จัดเรียงอันดับตามคะแนนและดึง Top 5
        top_recs = recommend_df.sort_values(by="ratings", ascending=False).head(5)
        
        if top_recs.empty:
            st.success("🎉 สุดยอดมาก! คุณดูอนิเมะในระบบของเราครบทุกเรื่องแล้ว")
        else:
            st.subheader("🔥 5 อันดับอนิเมะห้ามพลาดสำหรับคุณ")
            
            # จัดรูปแบบคอลัมน์ให้สวยงามก่อนแสดงผล
            display_recs = top_recs[["name", "genre", "year", "ratings"]].copy()
            display_recs.columns = ["ชื่ออนิเมะ", "แนว (Genre)", "ปีที่ฉาย", "คะแนนจากผู้ใช้"]
            
            # ฟอร์แมตตัวเลขคะแนน ถ้าเป็น 0 ให้แสดงว่า "ยังไม่มีคะแนน"
            display_recs["คะแนนจากผู้ใช้"] = display_recs["คะแนนจากผู้ใช้"].apply(
                lambda x: f"{x:.1f} ⭐" if x > 0 else "ยังไม่มีคะแนน"
            )
            
            # แสดงตารางแบบเต็มจอ
            st.dataframe(display_recs, use_container_width=True, hide_index=True)