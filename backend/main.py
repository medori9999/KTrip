# backend/main.py
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import sys
import os

# 1. llm.py를 불러오기 위한 경로 설정
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.llm import get_ai_recommendation

app = FastAPI()

# 2. CORS 설정 (보안 규칙 완화: 로컬 테스트용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터 받을 형식 정의 (HTML에서 보내는 이름과 같아야 함)
class SurveyRequest(BaseModel):
    target_area: str
    duration: str
    pace: str
    companion: str
    interests: list
    k_content_ratio: str
    food_preference: str
    need_cafe: str
    photo_priority: str
    record_method: str

# HTML에서 "추천해줘!" 하고 요청을 보내는 곳
@app.post("/api/recommend")
async def recommend_trip(request: SurveyRequest):
    print(f" [HTML 요청 도착] {request.dict()}")
    
    # 파이썬 딕셔너리를 JSON 문자열로 변환 (llm.py가 좋아하는 형식)
    user_query_json = json.dumps(request.dict(), ensure_ascii=False)
    
    # 작성자님이 만든 AI 함수 실행!
    ai_response_str = get_ai_recommendation(user_query_json)
    
    # 결과를 JSON으로 풀어서 HTML에게 돌려줌
    try:
        return json.loads(ai_response_str)
    except:
        return {"spots": []} # 에러 나면 빈 리스트 반환

# 5. 프론트엔드(HTML) 파일을 서버에서 직접 보여주기 설정
# (frontend 폴더 안에 있는 파일들을 주소창에 / 만 치면 보여줌)
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")