/* ==========================================
   K-Trip 공통 로직 (디자인 및 기능 100% 보존)
   ========================================== */

const STORAGE_KEY = 'ktrip_saved_routes';
let map, directionsService, routeRenderers = [], markers = [];

/**
 * 1. 지도 초기화 (Google Maps API)
 */
async function initMap() {
    try {
        const { Map } = await google.maps.importLibrary("maps");
        const { DirectionsService } = await google.maps.importLibrary("routes");
        const mapContainer = document.getElementById('map-container');
        
        if (!mapContainer) return;

        map = new Map(mapContainer, {
            center: { lat: 37.5665, lng: 126.9780 },
            zoom: 11,
            disableDefaultUI: true, 
            styles: [{ "featureType": "poi", "stylers": [{ "visibility": "off" }] }]
        });
        directionsService = new DirectionsService();
        console.log("Map initialized successfully.");
    } catch (e) {
        console.error("Map Load Error:", e);
    }
}

/**
 * 2. 지도 위 기존 마커 및 경로 제거
 */
function clearMap() {
    for (let i = 0; i < markers.length; i++) markers[i].setMap(null);
    markers = [];
    for (let i = 0; i < routeRenderers.length; i++) routeRenderers[i].setMap(null);
    routeRenderers = [];
}

/**
 * 3. 지도에 경로 그리기 (Transit 모드 및 폴리라인)
 */
async function drawRouteOnMap(spots) {
    if (!map || !spots || spots.length === 0) return;
    
    clearMap();
    const bounds = new google.maps.LatLngBounds();
    const positions = [];

    // 마커 생성 및 영역 확장
    spots.forEach((spot, index) => {
        const position = { lat: Number(spot.lat), lng: Number(spot.lng) };
        positions.push(position);
        
        const marker = new google.maps.Marker({
            position: position, 
            map: map, 
            title: spot.name,
            label: { text: (index + 1).toString(), color: "white", fontWeight: "bold" },
            zIndex: 100 + index
        });
        markers.push(marker);
        bounds.extend(position);
    });

    map.fitBounds(bounds);
    const { DirectionsRenderer } = await google.maps.importLibrary("routes");

    // 각 지점 사이의 경로 계산
    for (let i = 0; i < positions.length - 1; i++) {
        const start = positions[i];
        const end = positions[i+1];
        
        const renderer = new DirectionsRenderer({
            map: map, 
            suppressMarkers: true, 
            preserveViewport: true,
            polylineOptions: { strokeColor: "#6366f1", strokeWeight: 5, strokeOpacity: 0.8 }
        });
        routeRenderers.push(renderer);

        directionsService.route({
            origin: start, 
            destination: end, 
            travelMode: google.maps.TravelMode.TRANSIT,
        }, (response, status) => {
            if (status === "OK") {
                renderer.setDirections(response);
            } else {
                // 대중교통 경로 실패 시 직선 점선 표시 (원본 로직)
                new google.maps.Polyline({
                    path: [start, end], 
                    map: map, 
                    strokeColor: "#6366f1", 
                    strokeOpacity: 0.5, 
                    strokeWeight: 2,
                    icons: [{ icon: { path: 'M 0,-1 0,1', strokeOpacity: 1, scale: 2 }, offset: '0', repeat: '10px' }]
                });
            }
        });
    }
}

/**
 * 4. 결과 리스트 렌더링 (디자인 보존)
 */
function renderResult(spots) {
    const container = document.getElementById('result-container');
    if (!container) return;
    
    container.innerHTML = "";
    if (!spots || spots.length === 0) {
        container.innerHTML = "<p class='text-center text-gray-500 py-10'>No spots found.</p>";
        return;
    }

    spots.forEach((spot, index) => {
        // 원본 index.html의 리스트 HTML 구조 그대로 유지
        container.innerHTML += `
            <div class="flex gap-4">
                <div class="flex flex-col items-center">
                    <div class="w-8 h-8 bg-indigo-600 rounded-xl flex items-center justify-center text-white font-bold text-xs">${index + 1}</div>
                    ${index !== spots.length - 1 ? '<div class="line-draw h-full"></div>' : ''}
                </div>
                <div class="bg-white p-4 rounded-2xl flex-1 mb-4 border border-gray-100 shadow-sm">
                    <h4 class="font-bold text-sm text-indigo-900">${spot.name}</h4>
                    <p class="text-[10px] text-gray-500 mt-1">${spot.description}</p>
                    <div class="mt-2 text-[10px] font-bold text-indigo-400 bg-indigo-50 inline-block px-2 py-1 rounded-md">${spot.media_title || 'K-Place'}</div>
                </div>
            </div>`;
    });
}

/**
 * 5. 현재 경로 저장 (localStorage)
 */
function saveRoute() {
    const currentSpots = JSON.parse(localStorage.getItem('currentSpots'));
    if (!currentSpots || currentSpots.length === 0) { 
        alert("No route to save!"); 
        return; 
    }

    const savedData = JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
    const dateStr = new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    
    savedData.unshift({ 
        id: Date.now(), 
        date: dateStr, 
        spots: currentSpots 
    });
    
    localStorage.setItem(STORAGE_KEY, JSON.stringify(savedData));
    alert("Trip Saved Successfully! 💖");
}