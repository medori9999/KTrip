import sqlite3
import pandas as pd
import os

# 1. 파일 경로 설정 (backend 폴더 기준)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # backend 폴더
CSV_PATH = os.path.join(BASE_DIR, "locations.csv")
DB_PATH = os.path.join(BASE_DIR, "ktrip.db")

def init_database():
    print(f"📂 CSV 파일 읽는 중: {CSV_PATH}")
    
    # 2. CSV 파일 불러오기 (한글 컬럼명이므로 utf-8-sig 사용)
    try:
        df = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
        # 혹시 모를 빈 값(NaN)은 빈 문자열로 채워줍니다. (에러 방지)
        df = df.fillna('')
        print(f"✅ 데이터 {len(df)}개 로드 성공!")
        print(f"   - 컬럼 목록: {list(df.columns)}")
    except FileNotFoundError:
        print("❌ 오류: locations.csv 파일을 찾을 수 없습니다. backend 폴더에 파일이 있는지 확인해주세요.")
        return
    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}")
        return

    # 3. 데이터베이스 연결 (없으면 자동 생성됨)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 4. 기존 테이블이 있다면 삭제하고 새로 생성 (초기화)
    cursor.execute("DROP TABLE IF EXISTS locations")
    
    # 5. 테이블 스키마 정의 (우리가 쓸 영어 변수명으로 매핑할 준비)
    # [수정 1] description 뒤에 쉼표(,) 추가!
    cursor.execute("""
    CREATE TABLE locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,         -- 장소명
        address TEXT,               -- 주소
        lat REAL,                   -- 위도
        lng REAL,                   -- 경도
        media_title TEXT,           -- 제목 (영화/드라마 이름)
        media_type TEXT,            -- 미디어타입 (movie, drama 등)
        description TEXT,           -- 장소설명 (여기 쉼표 필수!)
        place_type TEXT             -- 장소타입(restaurant, cafe, place)
    )
    """)

    # 6. 데이터 집어넣기 (한글 컬럼 -> 영어 DB 컬럼 매핑)
    success_count = 0
    
    for index, row in df.iterrows():
        try:
            # CSV의 한글 컬럼명에서 데이터를 꺼냅니다.
            name = row['장소명']
            address = row['주소']
            lat = row['위도']
            lng = row['경도']
            media_title = row['제목']
            media_type = row['미디어타입']
            description = row['장소설명']
            place_type = row['장소타입']

            # [수정 2] VALUES에 물음표 8개, 변수에도 place_type 추가!
            cursor.execute("""
            INSERT INTO locations (name, address, lat, lng, media_title, media_type, description, place_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, address, lat, lng, media_title, media_type, description, place_type))
            
            success_count += 1
            
        except KeyError as e:
            print(f"⚠️ 컬럼 이름이 다릅니다! CSV 파일의 헤더를 확인해주세요. (없는 컬럼: {e})")
            break
        except Exception as e:
            print(f"⚠️ {index}번째 행 저장 실패: {e}")

    # 7. 저장 및 종료
    conn.commit()
    conn.close()
    print(f"🎉 총 {success_count}개 장소 데이터 저장 완료! (DB 파일: {DB_PATH})")

def init_visited_table():
    """추가 기능: 방문자 카운트를 위한 visited_spots 테이블 생성"""
    print(f"🛠️ 방문자 카운트 테이블 생성 중...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # visited_spots 테이블 생성 (이미 있으면 생성 안 함)
    # place_name: 장소 이름 (PRIMARY KEY로 중복 방지)
    # count: 방문한 팬의 수
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS visited_spots (
        place_name TEXT PRIMARY KEY,
        count INTEGER DEFAULT 0
    )
    """)

    # [테스트용] 초기 데이터가 없을 때만 몇 가지 장소 추가 (필요 없으면 삭제 가능)
    test_data = [('Gyeongbokgung', 10), ('N Seoul Tower', 5)]
    for name, cnt in test_data:
        cursor.execute("INSERT OR IGNORE INTO visited_spots (place_name, count) VALUES (?, ?)", (name, cnt))

    conn.commit()
    conn.close()
    print("✅ 'visited_spots' 테이블 준비 완료!")

if __name__ == "__main__":
    # 1. 기존 장소 데이터 초기화 실행
    init_database()
    
    # 2. 새로운 방문자 카운트 테이블 생성 실행
    init_visited_table()
    
    print(f"\n🚀 모든 데이터베이스 설정이 완료되었습니다! (경로: {DB_PATH})")

if __name__ == "__main__":
    init_database()