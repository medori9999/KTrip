# ✈️ KTrip: AI 기반 K-Culture 여행 큐레이션 플랫폼

> **"화면 속 동경이 현실의 여정이 되는 곳, 개인화 AI 여행 비서 KTrip"**
> 
> KTrip은 사용자의 취향을 분석하여 최적의 K-콘텐츠 촬영지 경로를 설계하고, 여행 중 마주치는 복잡한 메뉴판을 AI로 정밀 분석하여 현지인처럼 즐길 수 있도록 돕는 서비스입니다.

---

##  주요 기능 (Core Features)

### 1. 지능형 메뉴 분석 (Smart Menu Analysis)
단순한 텍스트 추출을 넘어 메뉴의 맥락을 읽어내는 분석 엔진입니다. 
- **OCR + LLM 하이브리드 정제:** Azure OCR의 공간 좌표 데이터와 GPT-4o의 문맥 추론을 결합하여 조각난 텍스트를 의미 단위로 재조합합니다.
- **정보 확장:** 메뉴 명칭 번역을 넘어 재료 설명, 맵기 단계 등을 AI가 스스로 판단하여 부가 정보를 제공합니다.

> **[메뉴판 과정]**
> ![Image](https://github.com/user-attachments/assets/71352a59-7432-4e3d-b013-f173ca737111)

### 2. RAG 기반 맞춤형 경로 추천 (Personalized Route)
<img width="1339" height="618" alt="Image" src="https://github.com/user-attachments/assets/dd923063-2154-4508-938b-a390b1eb8bfd" />
방대한 촬영지 DB에서 나만을 위한 '소울 루트'를 도출합니다.

- **4단계 RAG 아키텍처:** 키워드 추출 → DB 검색 → 관련도 랭킹 → 일정 생성의 4단계를 거쳐 할루시네이션(환각)을 최소화한 정보를 제공합니다.
- **병렬 처리 파이프라인:** 경로 생성과 메뉴 분석을 비동기 병렬로 처리하여 사용자 대기 시간을 이론적으로 50% 단축했습니다.

> <img width="713" height="524" alt="Image" src="https://github.com/user-attachments/assets/91e2565e-22d6-481b-8cf9-a1e4746bc6f5" />
 <img width="873" height="649" alt="Image" src="https://github.com/user-attachments/assets/750f95a0-e727-42d9-b33b-a00c40d39437" />

### 3. 여행 로그 및 소셜 템플릿 (Travel Log)
나의 발자취를 기록하고 감각적인 포스터로 변환합니다.
- [cite_start]**데이터 선순환:** 사용자의 방문 로그를 '취향의 좌표'로 축적하여 향후 고도화된 추천 시스템의 기반으로 활용합니다.
<img width="370" height="824" alt="Image" src="https://github.com/user-attachments/assets/8d90b81a-efa7-4ffb-bc36-97e52e5c73ff" />
---

##  기술적 챌린지 및 해결 (Technical Deep Dive)

### ** 자간 이슈: 공간 좌표 기반 텍스트 복원**
- **문제:** 메뉴판의 넓은 자간으로 인해 OCR이 단어를 개별 글자로 오인하여 번역 품질 저하 발생.
- **해결:** 텍스트의 **Y좌표 근접도**를 계산하고 LLM 프롬프트에 공간 레이아웃 정보를 주입하여, 파편화된 로우 데이터를 의미 있는 메뉴 정보로 완벽하게 재구성했습니다.
<img width="1239" height="509" alt="Image" src="https://github.com/user-attachments/assets/9af19dc8-dab7-4c16-b2b4-ba2eaf344a5d" />

### ** 4-Tier 아키텍처를 통한 효율적인 데이터 처리**
<img width="1139" height="308" alt="Image" src="https://github.com/user-attachments/assets/be1f66c4-ddd7-45c3-8bf5-ad49a90ab8c6" />
- **설계:** Client - Server - AI - Storage의 4계층 분리 설계를 통해 확장성을 확보했습니다.
- **효율:** 대용량 비정형 이미지(Blob)와 정형 텍스트(SQLite) 저장소를 분리하여 I/O 부하를 분산하고 처리 속도를 극대화했습니다.

---

## 기술 스택 (Tech Stack)

| 구분 | 기술 스택 |
| :--- | :--- |
| **Frontend** | Vanilla JS, MediaDevices API (경량 SPA 구조)  |
| **Backend** | FastAPI, Uvicorn, SQLAlchemy (비동기 컨트롤 타워)  |
| **AI Service** | Azure OpenAI (GPT-4o), Azure Document Intelligence |
| **Cloud/Infra** | Azure App Service, Azure Blob Storage, GitHub  |

---

##  프로젝트 구조 (Directory Structure)

```bash
KTrip/
├── backend/             # FastAPI 기반 비동기 API 서버
│   └── app/
│       ├── main.py      # 컨트롤 타워 및 API 엔드포인트 [cite: 609]
│       ├── ocr.py       # Azure Document Intelligence 연동 스크립트 [cite: 592]
│       └── llm.py       # GPT-4o 기반 데이터 정제 및 추천 로직 [cite: 592]
├── frontend/            # Vanilla JS 기반 경량 프론트엔드
└── data/                # K-Media 촬영지 및 마스터 DB [cite: 651]