import os
import time
import hmac
import hashlib
import base64
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="원츄부부 황금 키워드 분석기", page_icon="🔍", layout="centered")

def get_secret(key: str) -> str:
    """Streamlit Cloud Secrets 우선 조회 후 로컬 .env 폴백"""
    try:
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.getenv(key, "")

API_KEY = get_secret("NAVER_AD_API_KEY")
SECRET_KEY = get_secret("NAVER_AD_SECRET_KEY")
CUSTOMER_ID = get_secret("NAVER_AD_CUSTOMER_ID")

BASE_URL = "https://api.searchad.naver.com"
URI = "/keywordstool"
METHOD = "GET"

def generate_signature(timestamp: str, method: str, uri: str, secret_key: str) -> str:
    message = f"{timestamp}.{method}.{uri}"
    hash_obj = hmac.new(
        bytes(secret_key, "utf-8"),
        bytes(message, "utf-8"),
        hashlib.sha256
    )
    return base64.b64encode(hash_obj.digest()).decode("utf-8")

def parse_count(value) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and "<" in value:
        return 5
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0

st.title("🔍 블로그 황금 키워드 분석기")
st.caption("네이버 검색광고 API 기반 실시간 월간 검색량 및 경쟁 강도 조회")

with st.form("search_form"):
    hint_input = st.text_input(
        "기준 키워드 (쉼표로 최대 5개)",
        value="분당맛집,판교카페,분당아기랑",
        help="공백 없이 쉼표로 구분해 입력하세요."
    )
    include_input = st.text_input(
        "필수 포함 단어 (선택, 쉼표 구분)",
        value="분당,판교,성남,수내,정자,서현,백현,고기리,아기,유아,키즈",
        help="비워두면 필터링 없이 전체 연관 키워드를 표시합니다."
    )
    col1, col2 = st.columns(2)
    with col1:
        min_search = st.number_input("최소 월간 검색수", min_value=0, value=300, step=100)
    with col2:
        comp_options = st.multiselect("경쟁 강도", ["낮음", "중간", "높음"], default=["낮음", "중간"])

    submitted = st.form_submit_button("황금 키워드 조회하기", use_container_width=True)

if submitted:
    if not all([API_KEY, SECRET_KEY, CUSTOMER_ID]):
        st.error("API 키가 설정되지 않았습니다. Secrets 또는 .env 파일을 확인하세요.")
        st.stop()

    with st.spinner("네이버 검색량 데이터 조회 중..."):
        timestamp = str(int(time.time() * 1000))
        signature = generate_signature(timestamp, METHOD, URI, SECRET_KEY)

        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "X-Timestamp": timestamp,
            "X-API-KEY": API_KEY,
            "X-Customer": str(CUSTOMER_ID),
            "X-Signature": signature,
        }
        params = {
            "hintKeywords": hint_input.replace(" ", ""),
            "showDetail": 1
        }

        res = requests.get(BASE_URL + URI, params=params, headers=headers)
        if res.status_code != 200:
            st.error(f"API 호출 오류 ({res.status_code}): {res.text}")
            st.stop()

        raw_list = res.json().get("keywordList", [])
        include_words = tuple(w.strip() for w in include_input.split(",") if w.strip())
        results = []

        for item in raw_list:
            kw = item["relKeyword"]
            pc_cnt = parse_count(item["monthlyPcQcCnt"])
            mo_cnt = parse_count(item["monthlyMobileQcCnt"])
            total_search = pc_cnt + mo_cnt
            comp = item["compIdx"]
            mo_ctr = item.get("monthlyAveMobileCtr", 0)

            if include_words and not any(word in kw for word in include_words):
                continue

            if total_search >= min_search and comp in comp_options:
                results.append({
                    "키워드": kw,
                    "총검색수": total_search,
                    "모바일": mo_cnt,
                    "PC": pc_cnt,
                    "클릭률(%)": mo_ctr,
                    "경쟁도": comp
                })

        if not results:
            st.warning("조건에 맞는 키워드가 없습니다. 포함 단어나 최소 검색수를 완화해 보세요.")
        else:
            df = pd.DataFrame(results).sort_values(by="총검색수", ascending=False)
            st.success(f"총 {len(df)}개의 황금 키워드를 찾았습니다!")
            st.dataframe(df, use_container_width=True, hide_index=True)

            # 모바일에서 복사하기 쉽도록 상위 30개 태그 형태 출력
            top_tags = " ".join([f"#{k}" for k in df["키워드"].head(30)])
            st.subheader("📋 상위 30개 태그 복사")
            st.code(top_tags, language="text")
            