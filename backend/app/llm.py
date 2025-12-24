import os
import json
import sqlite3
import re
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 0. 유틸리티: JSON 문자열 클리닝
# ==========================================
def clean_json_string(raw_string):
    """AI 응답에서 ```json 등의 마크다운 태그를 제거"""
    try:
        cleaned = re.sub(r"```json\s*", "", raw_string)
        cleaned = re.sub(r"```\s*", "", cleaned)
        return cleaned.strip()
    except:
        return raw_string

# ==========================================
# 1. AI를 활용한 지능형 키워드 추출 (확장 검색 기능 탑재)
# ==========================================
def extract_smart_keywords(user_query_json):
    """
    1. 사용자가 선택한 '관심사(Interests)'를 DB 검색에 맞는 단어로 변환 (매핑)
    2. 그 외 텍스트에서 AI가 추가적인 고유 명사를 찾음
    """
    api_key = os.getenv("AZURE_OPENAI_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    client = AzureOpenAI(api_key=api_key, api_version="2023-05-15", azure_endpoint=endpoint)

    # 0. [필수] 용어 매핑 사전 (Frontend 영어 -> DB 한글/영어 변환)
    # 왼쪽이 설문조사 값, 오른쪽이 실제 DB 검색에 쓸 단어들
    KEYWORD_MAP = {
        "K-drama": ["드라마", "Drama", "촬영지"],
        "K-pop": ["K-POP", "아이돌", "Idol", "소속사", "뮤비"],
        "K-movie": ["영화", "Movie", "촬영장소"],
        "K-Show": ["예능", "TV", "방송"],
        "Balanced pace": [], # 이런 건 장소 검색어가 아니니 무시
        "Spicy food is okay": ["매운", "떡볶이"],
        "Relaxed and slow": ["공원", "산책"],
        "Mostly K-content": []
    }

    base_keywords = []
    
    try:
        data = json.loads(user_query_json)
        
        # 1. 관심사(Interests) 매핑 적용
        if "interests" in data and isinstance(data["interests"], list):
            for interest in data["interests"]:
                # 매핑된 단어가 있으면 그걸 넣고, 없으면 원래 단어 그대로 넣기
                mapped_words = KEYWORD_MAP.get(interest, [interest])
                base_keywords.extend(mapped_words)
        
        # 2. 지역(target_area) 처리
        if "target_area" in data and data["target_area"] not in ["Auto-detect my location", "Choose manually"]:
            base_keywords.append(data["target_area"])
            
    except:
        pass 

    # 3. AI 확장 키워드 추출 (지수 -> 블랙핑크 등)
    system_prompt = """
    You're an expert travel planner, and you are always helpful and well-mannered with everyone.
    **You must provide your response in JSON format.**
    You are designing a course for foreign tourists who love K-Contents (K-POP, K-Drama, K-Movie).
    **IMPORTANT: All values in the JSON, including place names, must be in English.**

    [Data Handling & Translation Rules]
    1. **Translate Place Names**: Convert the Korean place names from the provided [Place Data] into natural English.
    - (e.g., 'Seoul City Hall', 'Yoojung Restaurant')
    2. **Language**: Ensure all text in `message`, `name`, `description`, and `tip` is written in English.

    [Itinerary Logic]
    1. **Category Matching**: Use items from [MEAL] for lunch/dinner, [CAFE] for dessert, and [TOUR] for sightseeing.
    2. **Logical Flow**: Plan the route: Meal(Lunch) -> Tour -> Cafe(Dessert) -> Tour(Optional) -> Meal(Dinner).
    3. **Efficiency**: Use the provided coordinates (lat, lng) to arrange the spots in a geographically efficient order while maintaining the meal sequence.

    [JSON Output Format]
    {{
        "message": "English title and summary of the theme.",
        "spots": [
            {{
                "name": "English Place Name (Role)",
                "lat": 37.xxx,
                "lng": 127.xxx,
                "description": "Why this spot is recommended based on K-Content interests.",
                "tip": "Practical advice like menu recommendations or photo spots."
            }}
        ]
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"데이터: {user_query_json}"}
            ],
            temperature=0
        )
        cleaned_text = clean_json_string(response.choices[0].message.content)
        ai_keywords = json.loads(cleaned_text)
        
        # 4. 최종 합치기 (파이썬 매핑 + AI 추출)
        final_keywords = list(set(base_keywords + ai_keywords))
        
        # 불용어 필터링
        stop_words = ["추천", "여행", "코스", "맛집", "식당", "카페", "장소", "어디", "내위치", "자동", "Auto-detect", "Choose", "Manually"]
        # len(k) > 1 조건 삭제 (한 글자 이름 허용)
        filtered_keywords = [k for k in final_keywords if k not in stop_words]
        
        return filtered_keywords

    except Exception as e:
        print(f"⚠️ 키워드 추출 실패: {e}")
        # 실패 시 기본값이라도 반환해야 빈 화면이 안 뜸
        return base_keywords if base_keywords else ["서울", "관광"]

# ==========================================
# 2. 유연한 DB 검색 (SQL 에러 수정됨)
# ==========================================
def get_db_info(user_query_json):
    keywords = extract_smart_keywords(user_query_json)
    print(f"🤖 [AI 최종 검색 키워드] {keywords}") 

    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(os.path.dirname(current_dir), "ktrip.db")
    if not os.path.exists(db_path): db_path = os.path.join(current_dir, "ktrip.db")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    all_rows = []
    
    for kw in keywords:
        kw = kw.strip()
        if len(kw) < 1: continue

        # [SQL문 복구 완료] 여기에 "너는..." 같은 글자가 들어가면 안 됩니다.
        sql = """
            SELECT name, description, lat, lng, media_title, place_type, media_type
            FROM locations 
            WHERE (name LIKE ? OR media_title LIKE ? OR description LIKE ? OR media_type LIKE ?)
            ORDER BY 
                CASE 
                    WHEN media_title LIKE ? THEN 1 
                    WHEN name LIKE ? THEN 2 
                    ELSE 3 
                END
            LIMIT 5
        """
        # 파라미터 6개 (WHERE절 4개 + ORDER BY절 2개)
        param = f'%{kw}%'
        cursor.execute(sql, (param, param, param, param, param, param))
        all_rows.extend(cursor.fetchall())
    
    conn.close()
    
    # 중복 제거 및 분류 로직
    unique_rows = {row[0]: row for row in all_rows}.values()
    categorized = {"MEAL": [], "CAFE": [], "TOUR": []}

    for name, desc, lat, lng, m_title, p_type, m_type in unique_rows:
        p_type_str = str(p_type).lower() if p_type else ""
        place_info = f"- {name} (관련: {m_title}), 타입: {p_type_str}, 좌표: {lat}, {lng}, 설명: {desc[:60]}..."

        if "restaurant" in p_type_str or "식당" in p_type_str or "food" in p_type_str:
            categorized["MEAL"].append(place_info)
        elif "cafe" in p_type_str or "카페" in p_type_str:
            categorized["CAFE"].append(place_info)
        else:
            categorized["TOUR"].append(place_info)
            
    print(f"📊 검색 결과 - 식당: {len(categorized['MEAL'])}, 카페: {len(categorized['CAFE'])}, 명소: {len(categorized['TOUR'])}")

    info_text = "### [식당 후보]\n" + ("\n".join(categorized["MEAL"]) if categorized["MEAL"] else "없음")
    info_text += "\n\n### [카페 후보]\n" + ("\n".join(categorized["CAFE"]) if categorized["CAFE"] else "없음")
    info_text += "\n\n### [관광지 후보]\n" + ("\n".join(categorized["TOUR"]) if categorized["TOUR"] else "없음")
    
    return info_text

# ==========================================
# 3. 최종 결과값 추출
# ==========================================
def get_ai_recommendation(user_query):
    api_key = os.getenv("AZURE_OPENAI_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    client = AzureOpenAI(api_key=api_key, api_version="2023-05-15", azure_endpoint=endpoint)

    context_data = get_db_info(user_query)

    system_prompt = f"""
    너는 K-Contents 여행 코스 플래너야. 
    제공된 [장소 데이터]를 바탕으로 사용자에게 최적의 코스를 JSON으로 추천해줘.

    [필수 규칙]
    1. 사용자가 식당/카페를 원하면 해당 카테고리에서 우선적으로 선택해.
    2. 동선 효율성(좌표)을 고려해.
    3. Output은 오직 JSON 포맷이어야 해.

    [출력 포맷]
    {{
        "spots": [
            {{
                "name": "장소명",
                "lat": 37.xxx,
                "lng": 127.xxx,
                "description": "이 장소 추천 이유",
                "media_title": "관련 작품명"
            }}
        ]
    }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"요청: {user_query}\n\n[장소 데이터]\n{context_data}"}
            ],
            temperature=0.7,
            response_format={"type": "json_object"} 
        )
        return clean_json_string(response.choices[0].message.content)

    except Exception as e:
        return json.dumps({"error": str(e), "spots": []}, ensure_ascii=False)