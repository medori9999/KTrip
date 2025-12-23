# backend/app/llm.py
import os
import json
from openai import AzureOpenAI
from dotenv import load_dotenv
import sqlite3

load_dotenv()

def get_db_info(query):
    """
    DB에서 장소 정보를 검색 (위도, 경도 포함!)
    """
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ktrip.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 키워드 추출 
    keyword = query.replace("추천해줘", "").replace("여행", "").strip()
    
    
    cursor.execute("SELECT name, description, lat, lng FROM locations WHERE address LIKE ? OR name LIKE ? LIMIT 3", (f'%{keyword}%', f'%{keyword}%'))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return ""
    
    # AI에게 줄 정보 포맷팅
    info_text = ""
    for name, desc, lat, lng in rows:
        info_text += f"- 이름: {name}, 설명: {desc}, 위도: {lat}, 경도: {lng}\n"
    return info_text

def get_ai_recommendation(user_query):
    """
    Azure OpenAI에게 JSON 포맷으로 답변받기
    """
    api_key = os.getenv("AZURE_OPENAI_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

    if not api_key or not endpoint:
        # 에러 상황도 JSON으로 리턴
        return json.dumps({"error": "Azure 설정이 없습니다."})

    client = AzureOpenAI(
        api_key=api_key,
        api_version="2023-05-15",
        azure_endpoint=endpoint
    )

    context_info = get_db_info(user_query)

    #  시스템 프롬프트에서 JSON 출력을 강제함 33333
    system_prompt = """
    너는 여행 가이드야. 사용자 질문과 제공된 [장소 데이터]를 보고 추천 코스를 짜줘.
    
    [중요 규칙]
    반드시 아래와 같은 'JSON 포맷'으로만 대답해. 다른 말(인사말 등)은 절대 하지 마.
    
    {
        "message": "사용자에게 보여줄 친절한 설명 텍스트",
        "spots": [
            {"name": "장소명1", "lat": 37.xxxx, "lng": 127.xxxx},
            {"name": "장소명2", "lat": 37.xxxx, "lng": 127.xxxx}
        ]
    }
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"질문: {user_query}\n\n[장소 데이터]\n{context_info}"}
    ]

    try:
        response = client.chat.completions.create(
            model=deployment_name,
            messages=messages,
            temperature=0.7,
            response_format={"type": "json_object"} 
        )
        return response.choices[0].message.content
    except Exception as e:
        return json.dumps({"error": f"AI 에러: {str(e)}"}) ##
    
