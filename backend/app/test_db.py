import sys
import os

# (경로 설정 현재 위치가 어디든 backend 모듈을 잘 찾게 해주는 코드
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.database import engine, SessionLocal, Base
from backend.app.models import Location

def init_db():
    # 테이블 생성 
    # models.py에 적은 대로 ktrip.db 파일 안에 테이블을 만듭니다
    Base.metadata.create_all(bind=engine)
    print("✅ 테이블 생성 완료! (ktrip.db 파일 생성됨)")

def test_insert_and_read():
    db = SessionLocal()
    
    try:
        # 테스트 데이터 넣기
        if db.query(Location).first():
            print("ℹ️ 이미 데이터가 있어서 추가는 건너뜁니다.") #이미 있는데이터는갈아버리기
        else:
            sample = Location(
                name="해운대 포장마차",
                address="부산광역시 해운대구",
                lat=35.15,
                lng=129.16,
                media_title="내 남편과 결혼해줘",
                media_type="드라마",
                description="주인공이 회귀 전 기억을 떠올리던 곳",
                ai_summary="로맨틱하면서도 쓸쓸한 겨울 바다 느낌을 원하신다면 강추!"
            )
            db.add(sample)
            db.commit()
            print("✅ 테스트 데이터 저장(Insert) 완료!")

        # 3. 데이터 조회하기
        locations = db.query(Location).all()
        print("\n[ 현재 DB에 저장된 장소들 ]")
        for loc in locations:
            print(f"🎬 [{loc.media_type}] {loc.media_title} 촬영지 -> {loc.name}")
            print(f"   (AI 추천멘트: {loc.ai_summary})")

    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    test_insert_and_read()