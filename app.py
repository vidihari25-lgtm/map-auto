import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from datetime import datetime
import os
from io import BytesIO
import googlemaps
from streamlit_folium import st_folium
import folium

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="GPS Stamp Pro", layout="wide")

# --- INITIALIZE SESSION STATE (Agar Tidak NameError) ---
if 'lat' not in st.session_state:
    st.session_state.lat = -5.0382
if 'lng' not in st.session_state:
    st.session_state.lng = 105.2763
if 'manual_addr' not in st.session_state:
    st.session_state.manual_addr = "Tanggul Angin, Lampung"
if 'processed_images' not in st.session_state:
    st.session_state.processed_images = {}

# --- FUNGSI GOOGLE MAPS ---
def get_address_from_coords(lat, lng):
    try:
        gmaps = googlemaps.Client(key=st.secrets["GMAPS_KEY"])
        res = gmaps.reverse_geocode((lat, lng))
        return res[0]['formatted_address'] if res else "Alamat tidak ditemukan"
    except:
        return "Atur API Key di Secrets dulu ya"

# --- FUNGSI STAMP FOTO ---
def add_stamp_to_image(image, text_content):
    target_width = 1280
    w_percent = (target_width / float(image.size[0]))
    h_size = int((float(image.size[1]) * float(w_percent)))
    image = image.resize((target_width, h_size), Image.Resampling.LANCZOS)
    img = image.convert("RGBA")
    
    font_size = int(img.width * 0.04)
    font_file = "arial.ttf"
    try:
        font = ImageFont.truetype(font_file, font_size) if os.path.exists(font_file) else ImageFont.load_default()
    except:
        font = ImageFont.load_default()

    draw = ImageDraw.Draw(img)
    bbox = draw.multiline_textbbox((0, 0), text_content, font=font, align="right")
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = img.width - tw - int(img.width * 0.03), img.height - th - int(img.height * 0.03)

    shadow = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).multiline_text((x + 2, y + 2), text_content, font=font, fill=(0, 0, 0, 160), align="right")
    final = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(radius=2)))
    ImageDraw.Draw(final).multiline_text((x, y), text_content, font=font, fill="white", align="right")
    return final.convert("RGB")

# --- UI UTAMA ---
st.title("📸 GPS Stamp & Fake Map Picker")

uploaded_files = st.file_uploader("📂 Upload Foto", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

if uploaded_files:
    st.markdown("---")
    col_map, col_ctrl = st.columns([1, 1])

    with col_map:
        st.info("📍 Klik Peta untuk Geser Lokasi")
        m = folium.Map(location=[st.session_state.lat, st.session_state.lng], zoom_start=15)
        m.add_child(folium.LatLngPopup())
        map_data = st_folium(m, height=400, width=None, key="map_picker")
        
        # SINKRONISASI OTOMATIS SAAT DIKLIK
        if map_data.get("last_clicked"):
            if st.session_state.lat != map_data["last_clicked"]["lat"]:
                st.session_state.lat = map_data["last_clicked"]["lat"]
                st.session_state.lng = map_data["last_clicked"]["lng"]
                st.rerun()

    with col_ctrl:
        lat_disp = f"{abs(st.session_state.lat):.5f}{'S' if st.session_state.lat < 0 else 'N'}"
        lng_disp = f"{abs(st.session_state.lng):.5f}{'E' if st.session_state.lng > 0 else 'W'}"
        
        st.write(f"**Koordinat Terpilih:** `{lat_disp}, {lng_disp}`")
        
        if st.button("🔍 Cari Alamat Otomatis di Titik Ini"):
            st.session_state.manual_addr = get_address_from_coords(st.session_state.lat, st.session_state.lng)
            st.rerun()

        in_lokasi = st.text_area("Lokasi (Bisa Edit Manual)", value=st.session_state.manual_addr)
        in_waktu = st.text_input("Waktu", value=datetime.now().strftime("%d %b %Y %H.%M.%S"))

        if st.button("🚀 PROSES SEMUA FOTO", type="primary"):
            full_text = f"{in_waktu}\n{lat_disp} {lng_disp}\n{in_lokasi}"
            for i, file in enumerate(uploaded_files):
                st.session_state.processed_images[i] = {
                    "img": add_stamp_to_image(Image.open(file), full_text),
                    "nama": f"HASIL_{i}_{in_waktu}.jpg"
                }
            st.success("Selesai! Scroll ke bawah untuk download.")

# --- AREA DOWNLOAD ---
if st.session_state.processed_images:
    st.markdown("### 📥 Hasil Stamp")
    res_cols = st.columns(3)
    for i, data in st.session_state.processed_images.items():
        with res_cols[i % 3]:
            st.image(data["img"], use_container_width=True)
            buf = BytesIO()
            data["img"].save(buf, format="JPEG")
            st.download_button(f"Download #{i+1}", buf.getvalue(), data["nama"], key=f"dl_{i}")
