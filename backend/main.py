from fastapi import FastAPI, Request,UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse # [추가] HTML 파일을 직접 보내기 위해 필요
from pydantic import BaseModel
import json
import sys
import os
from dotenv import load_dotenv

load_dotenv()

# 1. 경로 설정
current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path) # backend 폴더
root_dir = os.path.dirname(current_dir) # 프로젝트 최상위 폴더
frontend_path = os.path.join(root_dir, "frontend") # frontend 폴더 경로 확정

sys.path.append(current_dir)

from app.llm import get_ai_recommendation, modify_ai_recommendation
from app.ocr import analyze_menu_image

app = FastAPI()

# 2. CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 데이터 모델 정의
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

class ModifyRequest(BaseModel):
    current_spots: list
    user_request: str

# 4. API 엔드포인트
@app.post("/api/recommend")
async def recommend_trip(request: SurveyRequest):
    print(f"📩 [초기 요청] {request.dict()}")
    user_query_json = json.dumps(request.dict(), ensure_ascii=False)
    ai_response_str = get_ai_recommendation(user_query_json)
    try:
        return json.loads(ai_response_str)
    except:
        return {"spots": []}

@app.post("/api/modify")
async def modify_trip(request: ModifyRequest):
    print(f"💬 [수정 요청] '{request.user_request}'")
    current_plan = {"spots": request.current_spots}
    updated_json_str = modify_ai_recommendation(current_plan, request.user_request)
    try:
        return json.loads(updated_json_str)
    except:
        print("❌ AI 응답 파싱 실패")
        return {"spots": request.current_spots}

# =========================================================
# [핵심 수정] 5. HTML 페이지 라우팅 (이정표 세우기)
# =========================================================

# (1) 메인 홈 (http://localhost:8000/) -> index.html
@app.get("/")
async def read_root():
    return FileResponse(os.path.join(frontend_path, "index.html"))

# (2) 설문조사 (http://localhost:8000/survey) -> survey.html
@app.get("/survey")
async def read_survey():
    return FileResponse(os.path.join(frontend_path, "survey.html"))

# (3) 결과 페이지
@app.get("/result.html")
async def read_result():
    return FileResponse(os.path.join(frontend_path, "result.html"))

# (4) 채팅 페이지
@app.get("/chat.html")
async def read_chat():
    return FileResponse(os.path.join(frontend_path, "chat.html"))

# (5) 저장됨 페이지
@app.get("/saved.html")
async def read_saved():
    return FileResponse(os.path.join(frontend_path, "saved.html"))

# (6) 포토 페이지
@app.get("/photo.html")
async def read_photo():
    return FileResponse(os.path.join(frontend_path, "photo.html"))

@app.get("/api/config")
def get_config():
    # 환경 변수에서 키를 읽어서 프론트엔드에 전달
    return {"googleMapsKey": os.getenv("GOOGLE_MAPS_API_KEY")}

@app.post("/api/analyze-menu")
async def analyze_menu(file: UploadFile = File(...)):
    print(f"📸 [이미지 수신] {file.filename}")
    
    # 1. 이미지 파일을 바이너리로 읽기
    image_data = await file.read()
    
    # 2. OCR 및 AI 분석 시작
    result = analyze_menu_image(image_data)
    
    return result

# 6. 정적 파일 (CSS, JS, 이미지 등) 연결 - 가장 마지막에 배치!
# 위에서 정의하지 않은 나머지 파일들을 frontend 폴더에서 찾음
app.mount("/", StaticFiles(directory=frontend_path), name="frontend")

