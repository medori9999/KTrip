import streamlit as st
from streamlit_folium import st_folium
import folium
import sys
import os

# [경로 설정]
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 페이지 기본 설정
st.set_page_config(page_title="KTrip - 나만의 여행 플래너", page_icon="✈️", layout="centered")


# [필수] Azure Maps 키 입력

AZURE_MAPS_KEY = #키를 입력하셔야합니다


st.title("✈️ KTrip")
st.header("Tell us your travel style")
st.markdown("Get a personalized itinerary designed just for you")
st.markdown("---")


# 세션 상태 초기화 
if 'form_submitted' not in st.session_state:
    st.session_state['form_submitted'] = False
if 'ai_result' not in st.session_state:
    st.session_state['ai_result'] = None



#  설문조사 폼 (5단계 완벽 복구)

with st.form("travel_preference_form"):

    # --- Section 1. Basic Travel Info ---
    st.subheader("1. Basic Travel Info 🗓️")
    location_option = st.radio("Which area?", ["Auto-detect", "Choose manually"], horizontal=True)
    if location_option == "Choose manually":
        st.text_input("City name")
    duration = st.radio("Duration?", ["Half day", "1 day", "2 days", "3+ days"], horizontal=True)
    st.markdown("---")

    # --- Section 2. Travel Style ---
    st.subheader("2. Travel Style 🏃‍♂️")
    pace = st.radio("Pace?", ["Slow", "Balanced", "Fast"], horizontal=True)
    companion = st.radio("Companion?", ["Solo", "With others"], horizontal=True)
    st.markdown("---")

    # --- Section 3. Interests ---
    st.subheader("3. Interests 🎭")
    interests = st.multiselect("Interests?", ["K-pop", "K-drama", "K-food", "Landmarks"], default=["K-drama"])

    k_content_ratio = st.radio("How much K-content?", ["Mostly", "Half", "Little"])
    st.markdown("---")

    # --- Section 4. Food & Café  ---
    st.subheader("4. Food & Café Preferences ☕")
    food_style = st.radio("Food Style?", ["Safe/Familiar", "Spicy OK", "Local/Exotic"])
    cafe_option = st.radio("Include Cafés?", ["Must", "Good to have", "No"])
    st.markdown("---")

    # --- Section 5. Photos & Memories ---
    st.subheader("5. Photos & Memories 📸")
    photo_importance = st.radio("Photos?", ["Very Important", "Sometimes", "Not really"], horizontal=True)
    record_style = st.radio("Record Style?", ["Insta-story", "Diary", "None"], horizontal=True)
    st.markdown("---")

    submitted = st.form_submit_button("Generate My Itinerary 🚀", use_container_width=True)

    # 버튼이 눌리면 -> 세션 상태를 True로 변경하고 데이터 저장
    if submitted:
        st.session_state['form_submitted'] = True
        
        #  나중에 실제 AI 응답으로 교체할 부분
        st.session_state['ai_result'] = [
            {"name": "Gyeongbokgung Palace", "lat": 37.5796, "lng": 126.9770},
            {"name": "Bukchon Hanok Village", "lat": 37.5826, "lng": 126.9850},
            {"name": "Insadong", "lat": 37.5743, "lng": 126.9895}
        ]



# 지도 생성 함수

def create_azure_map(key, locations):
    if not locations: return None
    
    start_lat, start_lng = locations[0]['lat'], locations[0]['lng']
    m = folium.Map(location=[start_lat, start_lng], zoom_start=14, tiles=None)

    azure_tiles = f"https://atlas.microsoft.com/map/tile?api-version=2.1&tilesetId=microsoft.base.road&zoom={{z}}&x={{x}}&y={{y}}&subscription-key={key}&language=en-US"
    
    folium.TileLayer(
        tiles=azure_tiles, attr="Microsoft Azure Maps", name="Azure Maps", overlay=False, control=True
    ).add_to(m)

    route_points = []
    for i, loc in enumerate(locations):
        folium.Marker(
            location=[loc['lat'], loc['lng']],
            popup=f"{i+1}. {loc['name']}",
            tooltip=f"{i+1}. {loc['name']}",
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(m)
        route_points.append([loc['lat'], loc['lng']])

    # 단순 직선 연결 (PolyLine)
    if len(route_points) > 1:
        folium.PolyLine(route_points, color="blue", weight=5, opacity=0.7).add_to(m)

    return m



# 결과 화면 표시 (세션 상태 확인)

if st.session_state['form_submitted']:
    
    st.subheader("🗺️ Recommended Itinerary")

    if "여기에" in AZURE_MAPS_KEY or not AZURE_MAPS_KEY:
        st.error("🚨 Azure Maps Key를 입력해주세요!")
    else:
        # 세션에 저장된 데이터로 지도 그리기
        map_obj = create_azure_map(AZURE_MAPS_KEY, st.session_state['ai_result'])
        st_folium(map_obj, width=700, height=500)

        st.write("### 📍 Route Details")
        for idx, loc in enumerate(st.session_state['ai_result']):
            st.info(f"**Step {idx+1}:** {loc['name']}")