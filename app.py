# --- LOGIKA SINKRONISASI LOKASI ---
# Inisialisasi posisi awal di session state jika belum ada
if 'lat' not in st.session_state:
    st.session_state.lat = -5.0382
if 'lng' not in st.session_state:
    st.session_state.lng = 105.2763
if 'manual_addr' not in st.session_state:
    st.session_state.manual_addr = "Tanggul Angin, Lampung"

# --- UI TAMPILAN ---
col_img, col_map = st.columns([1, 1])

with col_map:
    st.info("📍 Klik pada peta untuk 'Fake GPS'. Koordinat akan berubah otomatis.")
    # Membuat peta Folium
    m = folium.Map(location=[st.session_state.lat, st.session_state.lng], zoom_start=15)
    m.add_child(folium.LatLngPopup()) 
    
    # Menangkap data dari peta
    map_data = st_folium(m, height=300, key="map_picker")
    
    # JIKA PETA DIKLIK: Update session state
    if map_data.get("last_clicked"):
        st.session_state.lat = map_data["last_clicked"]["lat"]
        st.session_state.lng = map_data["last_clicked"]["lng"]
        # Trigger rerun agar angka di textbox langsung berubah
        st.rerun()

with col_img:
    # Format koordinat untuk tampilan stamp
    lat_disp = f"{abs(st.session_state.lat):.4f}{'S' if st.session_state.lat < 0 else 'N'}"
    lng_disp = f"{abs(st.session_state.lng):.4f}{'E' if st.session_state.lng > 0 else 'W'}"
    
    c1, c2 = st.columns(2)
    in_lat = c1.text_input("Latitude", value=lat_disp, key="input_lat")
    in_lng = c2.text_input("Longitude", value=lng_disp, key="input_lng")
    
    # Tombol Ambil Alamat Otomatis dari Google Maps
    if st.button("🔍 Ambil Alamat dari Titik Peta"):
        st.session_state.manual_addr = get_address_from_coords(st.session_state.lat, st.session_state.lng)
    
    in_lokasi = st.text_area("Lokasi (Edit Manual)", value=st.session_state.manual_addr, key="input_loc")
