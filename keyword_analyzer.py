import os
import time
import hmac
import hashlib
import base64
from datetime import datetime
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("NAVER_AD_API_KEY")
SECRET_KEY = os.getenv("NAVER_AD_SECRET_KEY")
CUSTOMER_ID = os.getenv("NAVER_AD_CUSTOMER_ID")

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


def analyze_golden_keywords(
    hint_keywords: str,
    include_words: tuple = (),
    min_search: int = 300,
    allowed_comp: tuple = ("낮음", "중간")
):
    """특정 단어가 포함된 황금 키워드만 필터링하여 엑셀로 저장"""
    if not all([API_KEY, SECRET_KEY, CUSTOMER_ID]):
        print("오류: .env 파일 설정을 확인하세요.")
        return

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
        "hintKeywords": hint_keywords.replace(" ", ""),
        "showDetail": 1
    }

    response = requests.get(BASE_URL + URI, params=params, headers=headers)
    if response.status_code != 200:
        print(f"API 호출 오류 ({response.status_code}): {response.text}")
        return

    raw_list = response.json().get("keywordList", [])
    results = []

    for item in raw_list:
        kw = item["relKeyword"]
        pc_cnt = parse_count(item["monthlyPcQcCnt"])
        mo_cnt = parse_count(item["monthlyMobileQcCnt"])
        total_search = pc_cnt + mo_cnt
        comp = item["compIdx"]
        mo_ctr = item.get("monthlyAveMobileCtr", 0)

        # include_words가 지정된 경우 해당 단어가 하나라도 포함된 키워드만 통과
        if include_words and not any(word in kw for word in include_words):
            continue

        if total_search >= min_search and comp in allowed_comp:
            results.append({
                "키워드": kw,
                "PC검색수": pc_cnt,
                "모바일검색수": mo_cnt,
                "총검색수": total_search,
                "모바일클릭률(%)": mo_ctr,
                "경쟁정도": comp
            })

    if not results:
        print("조건에 맞는 키워드가 없습니다. include_words나 min_search 조건을 완화해 보세요.")
        return

    df = pd.DataFrame(results).sort_values(by="총검색수", ascending=False)

    print(f"\n[기준: {hint_keywords}] 필터링된 황금 키워드 (총 {len(df)}개)\n")
    print(df.head(30).to_string(index=False))

    today_str = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"golden_keywords_{today_str}.xlsx"
    df.to_excel(filename, index=False)
    print(f"\n저장 완료: '{filename}' (전체 {len(df)}개 키워드 포함)")


if __name__ == "__main__":
    analyze_golden_keywords(
        hint_keywords="분당맛집,판교카페,분당아기랑",
        # 결과에 반드시 포함될 단어 목록 (비워두면 전체 조회)
        include_words=("분당", "판교", "성남", "수내", "정자", "서현", "백현", "운중", "고기리", "아기", "유아", "키즈"),
        min_search=300,
        allowed_comp=("낮음", "중간")
    )