import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from sklearn.metrics.pairwise import cosine_similarity

st.set_page_config(page_title="Anime Recommender", page_icon="🎌", layout="centered")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

@st.cache_resource
def get_sheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    client = gspread.authorize(creds)
    return client.open_by_key(st.secrets["sheet_id"]).worksheet("ratings")

@st.cache_data(ttl=60)
def load_data():
    df = pd.DataFrame(get_sheet().get_all_records())
    if not df.empty:
        df["score"] = pd.to_numeric(df["score"], errors="coerce")
    return df

# ---------- UI ----------
st.title("🎌 Anime Rating Collector")

tab1, tab2, tab3 = st.tabs(["📝 ให้คะแนน", "📊 ข้อมูล", "✨ แนะนำ"])

with tab1:
    with st.form("rating_form", clear_on_submit=True):
        user  = st.text_input("ชื่อผู้ใช้", placeholder="somchai")
        anime = st.text_input("ชื่ออนิเมะ", placeholder="Steins;Gate")
        col1, col2 = st.columns(2)
        score = col1.slider("คะแนน", 1, 10, 8)
        year  = col2.number_input("ปีที่ฉาย", 1960, 2030, 2011, step=1)
        submitted = st.form_submit_button("ส่งข้อมูล", use_container_width=True)

    if submitted:
        if not user.strip() or not anime.strip():
            st.warning("กรุณากรอกชื่อผู้ใช้และชื่ออนิเมะ")
        else:
            get_sheet().append_row([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                user.strip().lower(), anime.strip(), int(score), int(year)
            ])
            load_data.clear()
            st.success(f"บันทึกแล้ว: {anime} — {score}/10")
            st.balloons()

with tab2:
    df = load_data()
    if df.empty:
        st.info("ยังไม่มีข้อมูล")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Ratings", len(df))
        c2.metric("Users", df["user"].nunique())
        c3.metric("Anime", df["anime"].nunique())
        st.dataframe(df, use_container_width=True)
        st.bar_chart(df.groupby("anime")["score"].mean().sort_values(ascending=False).head(10))

with tab3:
    df = load_data()
    if df.empty or df["user"].nunique() < 2:
        st.info("ต้องมีอย่างน้อย 2 ผู้ใช้ถึงจะแนะนำได้")
    else:
        target = st.selectbox("เลือกผู้ใช้", sorted(df["user"].unique()))
        matrix = df.pivot_table(index="user", columns="anime",
                                values="score", aggfunc="mean").fillna(0)

        sim = pd.DataFrame(cosine_similarity(matrix),
                           index=matrix.index, columns=matrix.index)
        neighbors = sim[target].drop(target).sort_values(ascending=False)

        watched = set(df[df["user"] == target]["anime"])
        scores = {}
        for other, w in neighbors.items():
            if w <= 0:
                continue
            for a, s in matrix.loc[other].items():
                if s > 0 and a not in watched:
                    scores[a] = scores.get(a, 0) + w * s

        if scores:
            rec = pd.Series(scores).sort_values(ascending=False).head(5)
            st.subheader("อาจจะชอบเรื่องนี้")
            for i, (a, s) in enumerate(rec.items(), 1):
                st.write(f"**{i}. {a}** — คะแนนความเข้ากัน `{s:.2f}`")
        else:
            st.info("ยังหาคำแนะนำไม่ได้ — เก็บข้อมูลเพิ่มอีกหน่อย")