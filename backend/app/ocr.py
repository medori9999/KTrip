# backend/app/ocr.py

import os
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI
from dotenv import load_dotenv
import json
import re

load_dotenv()

def clean_json_string(raw_string):
    try:
        cleaned = re.sub(r"```json\s*", "", raw_string)
        cleaned = re.sub(r"```\s*", "", cleaned)
        return cleaned.strip()
    except:
        return raw_string

def analyze_menu_image(image_stream):
    print("🚀 [1단계] 메뉴판 분석 시작...")

    # 1. 키 확인
    doc_endpoint = os.getenv("AZURE_DOC_ENDPOINT")
    doc_key = os.getenv("AZURE_DOC_KEY")

    if not doc_endpoint or not doc_key:
        print("❌ 에러: .env 파일에 AZURE_DOC 관련 설정이 없습니다.")
        return {"error": "Azure credentials missing in .env"}

    # 2. Azure Document Intelligence 호출
    extracted_text = ""
    try:
        print("📡 Azure Document Intelligence에 연결 중...")
        document_analysis_client = DocumentIntelligenceClient(
            endpoint=doc_endpoint, 
            credential=AzureKeyCredential(doc_key)
        )

        # ★★★ [수정된 부분] analyze_request -> body 로 변경 ★★★
        poller = document_analysis_client.begin_analyze_document(
            "prebuilt-read", 
            body=image_stream, 
            content_type="application/octet-stream"
        )
        
        print("⏳ 이미지 분석 중 (시간이 좀 걸립니다)...")
        result = poller.result()

        extracted_text = " ".join([line.content for page in result.pages for line in page.lines])
        print(f"✅ OCR 성공! 추출된 텍스트(일부): {extracted_text[:50]}...")
        
    except Exception as e:
        print(f"❌ [OCR 실패] Azure 연결 에러: {str(e)}")
        return {"error": f"OCR Failed: {str(e)}"}

    # 3. GPT 호출
    try:
        print("🤖 GPT-4o에게 메뉴 분석 요청 중...")
        api_key = os.getenv("AZURE_OPENAI_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        client = AzureOpenAI(api_key=api_key, api_version="2023-05-15", azure_endpoint=endpoint)

        system_prompt = """
    You are an expert Korean Food Translator AI.
    The user will provide raw text extracted from a Korean menu board.
    
    YOUR MISSION (Execute in Order):

    1. **Fix Wide Letter Spacing (CRITICAL)**:
    - Korean menus often use wide spacing for alignment (Justified Text).
    - If you see single characters separated by spaces or newlines, COMBINE them.
    - Example: "우        동" → "우동" (Udon)
    - Example: "라        면" → "라면" (Ramen)
    - Example: "물        만        두" → "물만두"
       - **Rule**: If a single character (like "동", "면", "두") has a price next to it, search for its prefix immediately before it.

    2. **Merge Composite Names**: 
    - Combine modifiers with the main dish.
    - Example: "김치" + "우동" → "김치 우동" (ONE item).
    - Example: "해물" + "파전" → "해물 파전".
    - If multiple words share ONE price, they are ONE item.

    3. **Translate**: Translate the corrected name to natural English.
    
    4. **Description**: Explain ingredients and taste in detail (e.g., "Thick wheat noodle soup with fish cake and savory broth.").
    
    5. **Spicy Level**: Estimate spicy level (0~3).
    
    6. **Extract Price**: Find the associated price number.

    OUTPUT FORMAT (JSON):
    {
        "foods": [
            {
                "korean": "Fixed Korean Name (e.g. 우동)",
                "english": "English Name",
                "description": "Detailed description...",
                "spicy_level": 0,
                "price": "3500"
            }
        ]
    }
    """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": extracted_text}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        final_json = clean_json_string(response.choices[0].message.content)
        print("✅ GPT 분석 완료!")
        return json.loads(final_json)

    except Exception as e:
        print(f"❌ [AI 실패] GPT 에러: {str(e)}")
        return {"error": f"AI Failed: {str(e)}"}