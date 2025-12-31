from fastapi import FastAPI, Request,UploadFile, File, Form, Body
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse # [추가] HTML 파일을 직접 보내기 위해 필요
from pydantic import BaseModel
import json
import sys
import os
import uuid
import sqlite3
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()

# 1. 경로 설정
current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path) # backend 폴더
root_dir = os.path.dirname(current_dir) # 프로젝트 최상위 폴더
frontend_path = os.path.join(root_dir, "frontend") # frontend 폴더 경로 확정
DB_PATH = os.path.join(current_dir, "ktrip.db")

sys.path.append(current_dir)

from app.llm import get_ai_recommendation, modify_ai_recommendation
from app.ocr import analyze_menu_image

app = FastAPI()

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = "photos"

if AZURE_STORAGE_CONNECTION_STRING:
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
else:
    print("⚠️ 경고: .env 파일에 AZURE_STORAGE_CONNECTION_STRING이 없습니다.")

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
    

@app.post("/api/upload-and-count")
async def upload_and_count(
    file: UploadFile = File(None), # None 허용으로 변경 (사진 없이 저장만 할 때 대비)
    place_name: str = Form(...)
):
    try:
        image_url = None
        # 사진이 있을 때만 Azure Blob Storage에 업로드
        if file:
            file_ext = file.filename.split(".")[-1]
            unique_filename = f"{uuid.uuid4()}.{file_ext}"
            blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=unique_filename)
            contents = await file.read()
            blob_client.upload_blob(contents)
            image_url = blob_client.url

        # SQLite DB 방문 카운트 증가 (이 부분은 항상 실행)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO visited_spots (place_name, count) 
            VALUES (?, 1)
            ON CONFLICT(place_name) DO UPDATE SET count = count + 1
        """, (place_name,))
        
        cursor.execute("SELECT count FROM visited_spots WHERE place_name = ?", (place_name,))
        updated_count = cursor.fetchone()[0]
        conn.commit()
        conn.close()

        return {"success": True, "newCount": updated_count, "imageUrl": image_url}
    except Exception as e:
        return {"success": False, "error": str(e)}    

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

@app.post("/api/save-plan")
async def save_plan(plan_data: dict = Body(...)):
    try:
        # 1. 데이터를 JSON 문자열로 변환
        json_content = json.dumps(plan_data, ensure_ascii=False, indent=2)
        
        # 2. 파일명 생성 (예: 20251231_uuid.json)
        filename = f"{uuid.uuid4()}.json"
        
        # 3. Azure Blob Storage 'plans' 컨테이너에 업로드
        # (주의: 컨테이너 이름이 'plans'인지 확인하세요!)
        blob_client = blob_service_client.get_blob_client(container="plans", blob=filename)
        blob_client.upload_blob(json_content)
        
        print(f"✅ 경로 데이터 저장 완료: {filename}")
        return {"success": True, "filename": filename}
    except Exception as e:
        print(f"❌ 경로 저장 실패: {e}")
        return {"success": False, "error": str(e)}
@app.get("/api/get-visit-count/{place_name}")
async def get_visit_count(place_name: str):
    try:
        # DB 연결
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 해당 장소의 카운트 조회
        cursor.execute("SELECT count FROM visited_spots WHERE place_name = ?", (place_name,))
        row = cursor.fetchone()
        
        conn.close()
        
        # 데이터가 있으면 그 숫자, 없으면 0 반환
        count = row[0] if row else 0
        print(f"🔍 조회 요청: {place_name} -> {count}명")
        
        return {"success": True, "count": count}
    except Exception as e:
        print(f"❌ 조회 실패: {e}")
        return {"success": False, "count": 0}

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

