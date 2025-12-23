from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 지금은 로컬 나중엔 여기만 Azure.
SQLALCHEMY_DATABASE_URL = "sqlite:///./ktrip.db"

# 엔진 생성
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

#세션 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 모델들이 상속받을 기본 클래스.
Base = declarative_base()

# DB 연결 함수 (나중에 API에서 갖다 씀)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()