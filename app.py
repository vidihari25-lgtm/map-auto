import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from datetime import datetime
import os
from io import BytesIO
import googlemaps
from streamlit_folium import st_folium
import folium
import textwrap
import requests

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="GPS Stamp Pro", layout="wide")

# --- INITIALIZE SESSION STATE ---
if 'lat' not in st.session_state: st.session_state.lat = -5.0382
if 'lng' not in st.session_state: st.session_state.lng = 105.2763
if 'manual_addr' not in st.session_state: st.session_state.manual_addr = "Tanggul Angin, Lampung"
if 'processed_images' not in st.session_state: st.session_state.processed_images = {}

# --- FUNGSI RESET / GANTI FOTO ---
with st.sidebar:
    st.header("Pengaturan")
    if st.button("🗑️ Hapus Data & Ganti Foto", type="primary"):
        st.session_state.clear()
        st.rerun()
    st.info("Tombol ini akan menghapus semua foto dan mereset lokasi.")

# --- FUNGSI GOOGLE MAPS (GEOCODING & STATIC MAP) ---
def get_address_from_coords(lat, lng):
    try:
        gmaps = googlemaps.Client(key=st.secrets["GMAPS_KEY"])
        res = gmaps.reverse_geocode((lat, lng))
        return res[0]['formatted_address'] if res else "Alamat tidak ditemukan"
    except:
        return "API Key Error / Limit Habis"

def get_static_map_image(lat, lng, zoom=15, size=(300, 300)):
    api_key = st.secrets.get("GMAPS_KEY")
    if not api_key: return None
    
    base_url = "https://maps.googleapis.com/maps/api/staticmap?"
    coords = f"{lat},{lng}"
    params = {
        'center': coords,
        'zoom': zoom,
        'size': f"{size[0]}x{size[1]}",
        'maptype': 'roadmap',
        'markers': f"color:red|{coords}",
        'key': api_key
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGBA")
    except Exception as e:
        print(f"Gagal mengambil static map: {e}")
        return None

# --- FUNGSI STAMP FOTO UTAMA (Update: Ukuran Peta Dikecilkan) ---
def add_stamp_to_image(image, waktu, koord_str, lokasi, lat_float, lng_float):
    # 1. Resize proporsional foto utama
    target_width = 1280
    w_percent = (target_width / float(image.size[0]))
    h_size = int((float(image.size[1]) * float(w_percent)))
    image = image.resize((target_width, h_size), Image.Resampling.LANCZOS)
    img = image.convert("RGBA")
    width, height = img.size
    
    # --- BAGIAN TEXT STAMP (Kanan Bawah) ---
    font_size = int(width * 0.03) 
    font_file = "arial.ttf"
    try:
        font = ImageFont.truetype(font_file, font_size) if os.path.exists(font_file) else ImageFont.load_default()
    except:
        font = ImageFont.load_default()

    # Text Wrapping
    lokasi_wrapped = "\n".join(textwrap.wrap(lokasi, width=30))
    final_text = f"{waktu}\n{koord_str}\n{lokasi_wrapped}"

    # Hitung Ukuran Text
    draw = ImageDraw.Draw(img)
    bbox = draw.multiline_textbbox((0, 0), final_text, font=font, align="right")
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Margin dasar
    margin_x = int(width * 0.03)
    margin_y = int(height * 0.03)

    # Posisi Text (Kanan Bawah)
    text_x = width - text_width - margin_x
    text_y = height - text_height - margin_y

    # Buat Shadow TEXT
    shadow = Image.new('RGBA', img.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.multiline_text((text_x + 2, text_y + 2), final_text, font=font, fill=(0, 0, 0, 220), align="right")
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=2))
    img = Image.alpha_composite(img, shadow)
    
    # Tulis Teks Utama Putih
    final_draw = ImageDraw.Draw(img)
    final_draw.multiline_text((text_x, text_y), final_text, font=font, fill="white", align="right")

    # --- BAGIAN STATIC MAP STAMP (Kiri Bawah) ---
    # UPDATE: Mengubah persentase lebar peta dari 0.25 menjadi 0.18 (18%)
    map_target_width = int(width * 0.18)
    
    # Request ukuran ke Google tetap agak besar biar tajam
    api_map_size = (map_target_width + 150, map_target_width + 150)
    
    # Ambil gambar dari Google
    map_img = get_static_map_image(lat_float, lng_float, size=api_map_size)
    
    if map_img:
        # Resize peta ke ukuran target yang sudah dikecilkan (18%)
        map_img = map_img.resize((map_target_width, map_target_width), Image.Resampling.LANCZOS)
        
        # Tentukan posisi peta (Kiri Bawah)
        map_x = margin_x
        map_y = height - map_img.height - margin_y
        
        # Tempelkan peta
        img.paste(map_img, (map_x, map_y), map_img)

    return img.convert("RGB")

# --- TAMPILAN UTAMA ---
st.title("📸 GPS Stamp Pro & Fake Location")

uploaded_files = st.file_uploader("📂 Upload Foto", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

if uploaded_files:
    st.write("---")
    col_map, col_ctrl = st.columns([1.5, 1])

    with col_map:
        st.success("📍 **Langkah 1: Tentukan Titik Lokasi**")
        m = folium.Map(location=[st.session_state.lat, st.session_state.lng], zoom_start=15)
        m.add_child(folium.LatLngPopup())
        map_data = st_folium(m, height=400, width=None, key="map_picker")
        
        if map_data.get("last_clicked"):
            new_lat = map_data["last_clicked"]["lat"]
            new_lng = map_data["last_clicked"]["lng"]
            if new_lat != st.session_state.lat or new_lng != st.session_state.lng:
                st.session_state.lat = new_lat
                st.session_state.lng = new_lng
                st.rerun()

    with col_ctrl:
        st.success("📝 **Langkah 2: Edit Data Stamp**")
        
        lat_txt = f"{abs(st.session_state.lat):.5f}{'S' if st.session_state.lat < 0 else 'N'}"
        lng_txt = f"{abs(st.session_state.lng):.5f}{'E' if st.session_state.lng > 0 else 'W'}"
        koord_display = f"{lat_txt} {lng_txt}"
        
        st.code(f"Koordinat: {koord_display}")
        
        if st.button("🔍 Ambil Alamat Google Maps"):
            with st.spinner("Mengambil alamat..."):
                st.session_state.manual_addr = get_address_from_coords(st.session_state.lat, st.session_state.lng)
            st.rerun()

        in_lokasi = st.text_area("Alamat (Bisa Diedit)", value=st.session_state.manual_addr, height=100)
        in_waktu = st.text_input("Waktu Stamp", value=datetime.now().strftime("%d %b %Y %H.%M"))
        
        st.warning(f"Siap memproses {len(uploaded_files)} foto.")
        
        if st.button("🚀 PROSES SEMUA FOTO", type="primary"):
            st.session_state.processed_images = {} 
            progress_bar = st.progress(0)
            
            for i, file in enumerate(uploaded_files):
                img_result = add_stamp_to_image(
                    Image.open(file), 
                    in_waktu, 
                    koord_display, 
                    in_lokasi,
                    st.session_state.lat,
                    st.session_state.lng
                )
                
                safe_filename = in_waktu.replace(" ", "-").replace(":", "-").replace("/", "-")
                filename_final = f"Stamp_{safe_filename}_{i+1}.jpg"
                
                st.session_state.processed_images[i] = {
                    "img": img_result,
                    "nama_file": filename_final
                }
                progress_bar.progress((i + 1) / len(uploaded_files))
            st.success("Selesai! Silakan download di bawah.")

# --- AREA DOWNLOAD ---
if st.session_state.processed_images:
    st.write("---")
    st.header("📥 Download Hasil")
    
    cols = st.columns(3)
    for i, (idx, data) in enumerate(st.session_state.processed_images.items()):
        with cols[i % 3]:
            st.image(data["img"], use_container_width=True)
            buf = BytesIO()
            data["img"].save(buf, format="JPEG", quality=95)
            st.download_button(
                label=f"⬇️ Download #{idx+1}",
                data=buf.getvalue(),
                file_name=data["nama_file"],
                mime="image/jpeg",
                key=f"btn_dl_{idx}"
            )
