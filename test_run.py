# test_run.py
import os
import sys
import json

# 현재 폴더를 파이썬 경로에 추가 
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from backend.app.llm import get_ai_recommendation
except ImportError:
    print(" 에러: backend/app/llm.py 파일을 찾을 수 없습니다. 폴더 구조를 확인하세요.")
    sys.exit()

def run_test():
    print(" [테스트 시작] KTrip AI 추천 시스템 테스트")
    print("-" * 50)

    #  테스트 질문 설정
    user_query = "방탄소년단이 방문한 맛집 하루코스 만들어줘"    
    print(f" 사용자 질문: {user_query}")
    print(" AI와 DB가 통신 중입니다... 잠시만 기다려주세요.")

    #  LLM 함수 호출
    response_json = get_ai_recommendation(user_query)

    #  결과 출력 및 분석
    print("\n" + "="*50)
    print(" AI 응답 결과 (JSON 포맷)")
    print("="*50)
    
    try:

        parsed_response = json.loads(response_json)
        print(json.dumps(parsed_response, indent=4, ensure_ascii=False))
        
        if "error" in parsed_response:
            print("\n 작동 실패: 키 설정이나 엔드포인트를 다시 확인하세요.")
        elif not parsed_response.get("spots"):
            print("\n 경고: DB에서 장소를 찾지 못해 AI가 일반적인 답변을 했을 수 있습니다.")
        else:
            print("\n 성공: DB에서 장소를 찾아 좌표와 함께 응답했습니다!")
            
    except json.JSONDecodeError:
    
        print(response_json)
        print("\n 경고: 응답이 JSON 형식이 아닙니다.")

    print("="*50)

if __name__ == "__main__":
    run_test()
