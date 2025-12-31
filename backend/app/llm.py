import os
import json
import sqlite3
import re
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 0. Utility Functions
# ==========================================
def clean_json_string(raw_string):
    try:
        cleaned = re.sub(r"```json\s*", "", raw_string)
        cleaned = re.sub(r"```\s*", "", cleaned)
        return cleaned.strip()
    except:
        return raw_string

# ==========================================
# [NEW] Semantic Search Helper
# ==========================================
def calculate_relevance_score(spot_data, keywords, user_preferences):
    """Calculate relevance score for better retrieval"""
    score = 0
    name, desc, media, place_type = spot_data
    
    # Keyword matching
    for kw in keywords:
        kw_lower = str(kw).lower()
        if kw_lower in str(name).lower():
            score += 3
        if kw_lower in str(media).lower():
            score += 5  # Media match is highly relevant
        if kw_lower in str(desc).lower():
            score += 2
    
    # User preference matching
    interests = user_preferences.get("interests", [])
    for interest in interests:
        interest_lower = str(interest).lower()
        if interest_lower in str(media).lower():
            score += 4
        if interest_lower in str(desc).lower():
            score += 2
    
    return score

# ==========================================
# 1. Enhanced Keyword Extraction
# ==========================================
def extract_smart_keywords(user_query_json):
    api_key = os.getenv("AZURE_OPENAI_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    client = AzureOpenAI(api_key=api_key, api_version="2023-05-15", azure_endpoint=endpoint)

    base_keywords = []
    is_chat_mode = False
    
    try:
        if isinstance(user_query_json, dict):
            data = user_query_json
        else:
            data = json.loads(user_query_json)
            
        if "interests" in data:
            KEYWORD_MAP = {
                "K-drama": ["드라마", "Drama", "촬영지", "filming location"],
                "K-pop": ["K-POP", "아이돌", "Idol", "소속사", "뮤비", "MV"],
                "K-movie": ["영화", "Movie", "촬영장소", "cinema"],
                "K-Show": ["예능", "TV", "방송", "variety show"],
                "Spicy food is okay": ["매운", "떡볶이", "spicy"],
                "Relaxed and slow": ["공원", "산책", "park", "peaceful"]
            }
            if isinstance(data["interests"], list):
                for interest in data["interests"]:
                    base_keywords.extend(KEYWORD_MAP.get(interest, [interest]))
            if "target_area" in data and data["target_area"] not in ["Auto-detect my location", "Choose manually"]:
                base_keywords.append(data["target_area"])
        if "bias" in data and data["bias"]:
            base_keywords.append(data["bias"])
    except:
        is_chat_mode = True

    system_prompt = """
    You are a keyword extractor for K-culture travel recommendations.
    Extract 1-5 most important keywords including:
    - Proper nouns (BTS, Gangnam, Itaewon)
    - K-content titles (드라마명, 영화명)
    - Location types (cafe, restaurant, tower)
    
    Output: Python List JSON string. (e.g. ["BTS", "Gangnam", "cafe"])
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Extract keywords from: {user_query_json}"}
            ],
            temperature=0
        )
        cleaned_text = clean_json_string(response.choices[0].message.content)
        ai_keywords = json.loads(cleaned_text)
        
        final_keywords = list(set(base_keywords + ai_keywords))
        stop_words = ["추천", "여행", "코스", "맛집", "식당", "카페", "장소", "어디", "내위치", "자동"]
        
        if not final_keywords and is_chat_mode:
            return [str(user_query_json)[:10]]
            
        return [k for k in final_keywords if k not in stop_words]
    except:
        return [str(user_query_json)] if is_chat_mode else ["서울", "관광"]

# ==========================================
# 2. [ENHANCED] Multi-stage RAG Retrieval
# ==========================================
def get_db_info(user_query_json, limit_count=50):
    """Enhanced retrieval with scoring and ranking"""
    keywords = extract_smart_keywords(user_query_json)
    
    # Parse user preferences
    try:
        user_prefs = user_query_json if isinstance(user_query_json, dict) else json.loads(user_query_json)
    except:
        user_prefs = {}
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(os.path.dirname(current_dir), "ktrip.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Stage 1: Keyword-based retrieval
    all_rows = []
    for kw in keywords:
        param = f'%{str(kw).strip()}%'
        cursor.execute("""
            SELECT name, description, lat, lng, media_title, place_type 
            FROM locations 
            WHERE (name LIKE ? OR media_title LIKE ? OR description LIKE ?)
            LIMIT ?
        """, (param, param, param, limit_count))
        all_rows.extend(cursor.fetchall())

    # Stage 2: Fallback retrieval if insufficient results
    if len(all_rows) < 30:
        cursor.execute("""
            SELECT name, description, lat, lng, media_title, place_type 
            FROM locations 
            ORDER BY RANDOM() 
            LIMIT 50
        """)
        all_rows.extend(cursor.fetchall())
    
    conn.close()
    
    # Stage 3: Score and rank results (semantic matching)
    unique_rows = {row[0]: row for row in all_rows}.values()
    scored_rows = []
    for row in unique_rows:
        score = calculate_relevance_score(
            (row[0], row[1], row[4], row[5]), 
            keywords, 
            user_prefs
        )
        scored_rows.append((score, row))
    
    # Sort by relevance score (highest first)
    scored_rows.sort(reverse=True, key=lambda x: x[0])
    
    # Stage 4: Categorize with rich context
    categorized = {"MEAL": [], "CAFE": [], "TOUR": []}
    
    for score, (name, desc, lat, lng, m_title, p_type) in scored_rows:
        p_type_str = str(p_type).lower() if p_type else ""
        
        # [ENHANCED] Add relevance score to context
        info = {
            "korean_id": name,
            "media": m_title or "General K-culture spot",
            "type": p_type_str,
            "lat": lat,
            "lng": lng,
            "description": desc[:150] if desc else "",
            "relevance": score  # RAG scoring
        }
        
        # Enhanced categorization
        if any(w in p_type_str for w in ["restaurant", "food", "meal", "식당", "맛집", "bakery", "dining"]):
            categorized["MEAL"].append(info)
        elif any(w in p_type_str for w in ["cafe", "카페", "coffee", "dessert", "tea"]):
            categorized["CAFE"].append(info)
        else:
            categorized["TOUR"].append(info)
    
    # Return top results per category
    return {
        "MEAL": categorized["MEAL"][:25],
        "CAFE": categorized["CAFE"][:15],
        "TOUR": categorized["TOUR"][:25]
    }

# ==========================================
# [NEW] Context Builder for RAG
# ==========================================
def build_rag_context(db_data, category, limit=10):
    """Build structured context for LLM from retrieved data"""
    items = db_data.get(category, [])[:limit]
    
    if not items:
        return f"No {category} data available."
    
    context_lines = [f"\n=== {category} OPTIONS (ranked by relevance) ==="]
    for idx, item in enumerate(items, 1):
        context_lines.append(
            f"{idx}. Korean_Name: {item['korean_id']} | "
            f"Related_Content: {item['media']} | "
            f"Location: ({item['lat']}, {item['lng']}) | "
            f"Description: {item['description']}"
        )
    
    return "\n".join(context_lines)

# ==========================================
# 3. [ENHANCED] Main Recommendation with Rich RAG
# ==========================================
def get_ai_recommendation(user_query):
    api_key = os.getenv("AZURE_OPENAI_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    client = AzureOpenAI(api_key=api_key, api_version="2023-05-15", azure_endpoint=endpoint)

    # RAG Stage 1: Retrieve relevant data
    db_data = get_db_info(user_query)
    user_data = user_query if isinstance(user_query, dict) else json.loads(user_query)
    duration = str(user_data.get("duration", "1 day")).lower()

    # Calculate exact count
    required_count = 5
    if "half" in duration: 
        required_count = 3
    elif "2 day" in duration: 
        required_count = 10
    elif "3 day" in duration or "+" in duration: 
        required_count = 15

    # Build strict sequence instruction
    if required_count == 3:
        sequence_instruction = "EXACT ORDER: spot[0]=Meal, spot[1]=Tour, spot[2]=Cafe"
    elif required_count == 5:
        sequence_instruction = "EXACT ORDER: spot[0]=Lunch, spot[1]=Tour, spot[2]=Cafe, spot[3]=Tour, spot[4]=Dinner"
    elif required_count == 10:
        sequence_instruction = "EXACT ORDER: Day1[spot[0]=Lunch, spot[1]=Tour, spot[2]=Cafe, spot[3]=Tour, spot[4]=Dinner] + Day2[spot[5]=Lunch, spot[6]=Tour, spot[7]=Cafe, spot[8]=Tour, spot[9]=Dinner]"
    else:  # 15
        sequence_instruction = "EXACT ORDER: Day1[0=Lunch,1=Tour,2=Cafe,3=Tour,4=Dinner] + Day2[5=Lunch,6=Tour,7=Cafe,8=Tour,9=Dinner] + Day3[10=Lunch,11=Tour,12=Cafe,13=Tour,14=Dinner]"

    # RAG Stage 2: Build rich context from retrieved data
    meal_context = build_rag_context(db_data, "MEAL", limit=15)
    cafe_context = build_rag_context(db_data, "CAFE", limit=10)
    tour_context = build_rag_context(db_data, "TOUR", limit=15)

    # Enhanced system prompt with RAG context
    system_prompt = f"""
You are a professional Seoul K-culture travel planner using a RETRIEVAL-AUGMENTED GENERATION system.

**CRITICAL REQUIREMENTS - THESE ARE MANDATORY:**

1. **LANGUAGE**: ALL text MUST be in ENGLISH ONLY. No Korean characters allowed anywhere.

2. **TRANSLATION RULE**: 
- The retrieved database provides Korean names (Korean_Name field)
- You MUST translate these to natural English names
- Format: "English Name(Role)"
- Example: "Jinmi Restaurant(Lunch)", "N Seoul Tower(Tour)"

3. **EXACT COUNT**: Return EXACTLY {required_count} spots. No more, no less.

4. **ROLE LABELS**: Every name must end with one of these roles:
- (Meal) or (Lunch) or (Dinner) for restaurants
- (Tour) for attractions/activities
- (Cafe) for coffee shops

5. **STRICT SEQUENCE - FOLLOW THIS EXACTLY, NO EXCEPTIONS**:
- Half day (3 spots): Position 1=MEAL, Position 2=TOUR, Position 3=CAFE
- 1 day (5 spots): Position 1=Lunch, Position 2=TOUR, Position 3=CAFE, Position 4=TOUR, Position 5=Dinner
- 2 days (10 spots): Positions 1-5 (Day 1) + Positions 6-10 (Day 2), each following 1-day pattern
- 3+ days (15 spots): Positions 1-5 (Day 1) + Positions 6-10 (Day 2) + Positions 11-15 (Day 3)

   **NEVER PUT TWO MEALS IN A ROW. NEVER PUT TWO CAFES IN A ROW.**

6. **NO DUPLICATES**: Never use the same location twice in the entire itinerary.

7. **TIPS - MANDATORY FORMAT**:
- For Restaurants (Lunch/Dinner): Recommend 1-2 signature menu items. Example: "Try the Kimchi Jjigae and Bulgogi. Arrive before 12pm to avoid lines."
- For Cafes: Recommend 1-2 popular drinks/desserts. Example: "Order the Strawberry Latte and Croffle. Second floor has the best Instagram spot."
- For Tours: Give practical visiting tips. Example: "Best visited at sunset. Take the cable car to avoid the stairs."

8. **OUTPUT FORMAT** (JSON):
{{
"spots": [
    {{
    "name": "Myeongdong Kyoja(Lunch)",
    "description": "Famous handmade noodle restaurant featured in multiple K-dramas",
    "lat": "37.5665",
    "lng": "126.9780",
    "media_title": "Running Man, Itaewon Class",
    "tips": "Must-try: Kalguksu (handmade noodles) and Mandu (dumplings). Arrive before 11:30am to skip the queue."
    }},
    {{
    "name": "Cafe Onion(Cafe)",
    "description": "Industrial-chic cafe in a renovated factory building",
    "lat": "37.5547",
    "lng": "126.9236", 
    "media_title": "Instagram favorite among K-pop idols",
    "tips": "Order the Einspanner (cream coffee) and Croissant. The rooftop terrace offers great photo opportunities."
    }}
]
}}

**RETRIEVED DATA FROM DATABASE (Use ONLY these options):**

{meal_context}

{cafe_context}

{tour_context}

**SEQUENCE VALIDATION CHECKLIST - YOU MUST VERIFY THIS:**
For 1 day: spots[0]=(Lunch), spots[1]=(Tour), spots[2]=(Cafe), spots[3]=(Tour), spots[4]=(Dinner)
For 2 days: Same pattern twice (positions 0-4, then 5-9)
For 3 days: Same pattern three times (positions 0-4, 5-9, 10-14)

**IF YOUR OUTPUT DOESN'T MATCH THE CHECKLIST, IT'S WRONG. FIX IT BEFORE RESPONDING.**

**RAG INSTRUCTION**: You MUST select locations from the retrieved data above. Do NOT invent new locations. If retrieved data is insufficient, explain the limitation but try your best with available data.
"""

    user_interests = user_data.get("interests", [])
    k_content = user_data.get("k_content_ratio", "")
    
    user_message = f"""
Create a {duration} K-culture itinerary with EXACTLY {required_count} spots.

{sequence_instruction}

**CHECK YOUR OUTPUT BEFORE RESPONDING:**
- Count the spots array length = {required_count}?
- No two meals in a row?
- No two cafes in a row?
- Every 5-spot cycle follows: Lunch→Tour→Cafe→Tour→Dinner?
- All locations selected from the RETRIEVED DATA above?

User preferences:
- Interests: {', '.join(user_interests) if user_interests else 'General K-culture'}
- K-content ratio: {k_content}
- Food preference: {user_data.get('food_preference', '')}
- Pace: {user_data.get('pace', '')}

CRITICAL RULES:
1. Translate ALL Korean names to English
2. Follow the EXACT sequence shown above (check each position!)
3. Return EXACTLY {required_count} spots in correct order
4. NO duplicates anywhere
5. Add (Role) to every name: (Lunch), (Dinner), (Tour), or (Cafe)
6. Write everything in ENGLISH
7. **TIPS MUST INCLUDE:**
- Restaurants → Recommend specific menu items (e.g., "Try the Bulgogi and Bibimbap")
- Cafes → Recommend drinks/desserts (e.g., "Order the Einspanner and Tiramisu")
- Tours → Give visiting tips (e.g., "Best time: sunset. Entrance fee: 10,000 won")
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0,
            response_format={"type": "json_object"} 
        )
        
        result = clean_json_string(response.choices[0].message.content)
        
        # Validation: Check if response meets requirements
        try:
            parsed = json.loads(result)
            if "spots" in parsed and len(parsed["spots"]) != required_count:
                print(f"⚠️ Warning: Expected {required_count} spots, got {len(parsed['spots'])}")
        except:
            pass
            
        return result
        
    except Exception as e:
        print(f"❌ Error in get_ai_recommendation: {str(e)}")
        return json.dumps({
            "message": f"Planning error: {str(e)}", 
            "spots": []
        })

# ==========================================
# 4. [ENHANCED] Chatbot Modification with RAG
# ==========================================
# [llm.py 의 modify_ai_recommendation 함수 전체 교체]

def modify_ai_recommendation(current_json, user_request):
    api_key = os.getenv("AZURE_OPENAI_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    client = AzureOpenAI(api_key=api_key, api_version="2023-05-15", azure_endpoint=endpoint)

    # 1. 요청사항에 맞는 장소 검색 (RAG)
    new_context_data = get_db_info(user_request, limit_count=30)
    
    meal_ctx = build_rag_context(new_context_data, "MEAL", limit=10)
    cafe_ctx = build_rag_context(new_context_data, "CAFE", limit=8)
    tour_ctx = build_rag_context(new_context_data, "TOUR", limit=10)

    # 2. 시스템 프롬프트 (강력한 규칙 추가)
    system_prompt = f"""
    You are an expert travel modification assistant.
    
    [CRITICAL RULE]
    You must return the **FULL COMPLETE ITINERARY**. 
    Do NOT return only the new spots. 
    You must output ALL original spots + NEW spots combined in a single list.

    **MANDATORY RULES:**
    1. Translate Korean location names to natural English.
    2. Add role labels: Name(Role) - (Meal), (Lunch), (Dinner), (Tour), or (Cafe).
    3. NO DUPLICATES - Check against [Current Itinerary].
    4. **INSERTION**: Insert the new spot at a logical position (e.g., Cafe after Lunch).
    5. **TIPS**: Provide specific English tips for the NEW spot.

    **OUTPUT FORMAT (JSON ONLY):**
    {{
    "message": "Added [Place Name] to your trip!",
    "spots": [
        {{
        "name": "Existing Spot(Tour)",
        "description": "...",
        "lat": "...", "lng": "...", "media_title": "...", "tips": "..."
        }},
        {{
        "name": "NEW SPOT(Cafe)", 
        "description": "...", 
        "lat": "...", "lng": "...", "media_title": "...", "tips": "..."
        }},
        ... (Return ALL spots)
    ]
    }}

    **RETRIEVED CANDIDATES (Use these for the new spot):**
    {meal_ctx}
    {cafe_ctx}
    {tour_ctx}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"""
                [Current Itinerary]
                {json.dumps(current_json, ensure_ascii=False)}

                [User Request]
                "{user_request}"

                COMMAND: 
                1. Identify what the user wants to add/change.
                2. Select a suitable spot from RETRIEVED CANDIDATES.
                3. Add it to the Current Itinerary (keep existing spots unless asked to remove).
                4. Return the FULL JSON.
                """}
            ],
            temperature=0,
            response_format={"type": "json_object"} 
        )
        
        result = clean_json_string(response.choices[0].message.content)
        
        # [디버깅] AI가 뭘 줬는지 서버 로그로 확인 (나중에 주석 처리 가능)
        print(f"🤖 AI Modify Response: {result[:200]}...") 

        return result
        
    except Exception as e:
        print(f"❌ Error in modify_ai_recommendation: {str(e)}")
        # 에러가 나도 기존 데이터라도 보여주기 위해 반환
        return json.dumps(current_json, ensure_ascii=False)