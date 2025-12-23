from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from sqlalchemy.sql import func
from .database import Base

# 정제 중인 CSV 데이터
class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)       # 장소명
    address = Column(String)                # 주소
    lat = Column(Float)                     # 위도
    lng = Column(Float)                     # 경도
    media_title = Column(String)            # 드라마 제목
    media_type = Column(String)             # 구분
    description = Column(Text, nullable=True) 
    ai_summary = Column(Text, nullable=True) 

# 사용자가 올린 사진과 변환된 결과물 기록.
class PhotoLog(Base):
    __tablename__ = "photo_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # 사용자가 올린 원본사진 저장경로 (예: /images/raw/user123.jpg)
    original_image_path = Column(String, nullable=False)
    
    # AI가 변환해준 인스타용 사진 경로 (예: /images/converted/filter_user123.jpg)
    converted_image_path = Column(String, nullable=True)
    
    # 어떤 스타일로 바꿨는지 (예: "cartoon", "sketch", "blog_vibe")
    style_type = Column(String, default="default")
    
    # 언제 요청했는지 로그 남기기용
    created_at = Column(DateTime(timezone=True), server_default=func.now())