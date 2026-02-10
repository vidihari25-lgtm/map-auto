import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from datetime import datetime
import os
from io import BytesIO
import googlemaps
from streamlit_folium import st_folium
import folium
import textwrap  # Tambahan untuk memotong teks agar tidak melebar

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

# --- FUNGSI GOOGLE MAPS ---
def get_address_from_coords(lat, lng):
    try:
        gmaps = googlemaps.Client(key=st.secrets["GMAPS_KEY"])
        res = gmaps.reverse_geocode((lat, lng))
        return res[0]['formatted_address'] if res else "Alamat tidak ditemukan"
    except:
        return "API Key Error / Limit Habis"

# --- FUNGSI STAMP FOTO (DIPERBAIKI AGAR TIDAK MELEBAR) ---
def add_stamp_to_image(image, waktu, koord, lokasi):
    # 1. Resize proporsional (Mencegah gambar gepeng)
    target_width = 1280
    w_percent = (target_width / float(image.size[0]))
    h_size = int((float(image.size[1]) * float(w_percent)))
    image = image.resize((target_width, h_size), Image.Resampling.LANCZOS)
    img = image.convert("RGBA")
    
    # 2. Siapkan Font (Arial)
    font_size = int(img.width * 0.035) # Ukuran font 3.5% dari lebar
    font_file = "arial.ttf"
    try:
        font = ImageFont.truetype(font_file, font_size) if os.path.exists(font_file) else ImageFont.load_default()
    except:
        font = ImageFont.load_default()

    # 3. Text Wrapping (Agar stamp tidak memanjang ke samping)
    # Memotong lokasi setiap 40 karakter agar turun ke baris baru
    lokasi_wrapped = "\n".join(textwrap.wrap(lokasi, width=40))
    final_text = f"{waktu}\n{koord}\n{lokasi_wrapped}"

    # 4. Hitung Ukuran Kotak Text
    draw = ImageDraw.Draw(img)
    bbox = draw.multiline_textbbox((0, 0), final_text, font=font, align="right")
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # 5. Tentukan Posisi (Pojok Kanan Bawah)
    margin_x = int(img.width * 0.03)
    margin_y = int(img.height * 0.03)
    x = img.width - text_width - margin_x
    y = img.height - text_height - margin_y

    # 6. Buat Shadow (Bayangan) Background agar Tulisan Terbaca
    shadow = Image.new('RGBA', img.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    
    # Padding background sedikit lebih besar dari teks
    pad = 10
    # Menggambar kotak hitam transparan di belakang teks
    shadow_draw.rectangle(
        [x - pad, y - pad, x + text_width + pad, y + text_height + pad], 
        fill=(0, 0, 0, 140) # Hitam transparan (Alpha 140)
    )
    
    # Gabungkan Shadow dengan Gambar Asli
    final = Image.alpha_composite(img, shadow)
    
    # 7. Tulis Teks Putih di Atasnya
    final_draw = ImageDraw.Draw(final)
    final_draw.multiline_text((x, y), final_text, font=font, fill="white", align="right")
    
    return final.convert("RGB")

# --- TAMPILAN UTAMA ---
st.title("📸 GPS Stamp Pro & Fake Location")

uploaded_files = st.file_uploader("📂 Upload Foto (Bisa Banyak Sekaligus)", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

if uploaded_files:
    st.write("---")
    # Layout: Kiri Peta, Kanan Kontrol
    col_map, col_ctrl = st.columns([1.5, 1])

    with col_map:
        st.success("📍 **Langkah 1: Tentukan Titik Lokasi**")
        # Peta
        m = folium.Map(location=[st.session_state.lat, st.session_state.lng], zoom_start=15)
        m.add_child(folium.LatLngPopup())
        map_data = st_folium(m, height=400, width=None, key="map_picker")
        
        # Logika Update Koordinat saat Peta Diklik
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
        
        # Tombol Ambil Alamat
        if st.button("🔍 Ambil Alamat Google Maps"):
            with st.spinner("Mengambil alamat..."):
                st.session_state.manual_addr = get_address_from_coords(st.session_state.lat, st.session_state.lng)
            st.rerun()

        # Input Manual
        in_lokasi = st.text_area("Alamat (Bisa Diedit)", value=st.session_state.manual_addr, height=100)
        in_waktu = st.text_input("Waktu Stamp", value=datetime.now().strftime("%d %b %Y %H.%M"))
        
        st.warning(f"Akan memproses {len(uploaded_files)} foto.")
        
        # Tombol Proses Utama
        if st.button("🚀 PROSES SEMUA FOTO", type="primary"):
            st.session_state.processed_images = {} # Reset hasil lama
            progress_bar = st.progress(0)
            
            for i, file in enumerate(uploaded_files):
                img_result = add_stamp_to_image(Image.open(file), in_waktu, koord_display, in_lokasi)
                
                # Membuat Nama File sesuai Tanggal Input
                # Mengubah "12 Okt 2025 14.30" menjadi "Stamp_12-Okt-2025_14-30.jpg"
                safe_filename = in_waktu.replace(" ", "-").replace(":", "-").replace("/", "-")
                filename_final = f"Stamp_{safe_filename}_{i+1}.jpg"
                
                st.session_state.processed_images[i] = {
                    "img": img_result,
                    "nama_file": filename_final
                }
                progress_bar.progress((i + 1) / len(uploaded_files))
            st.success("Selesai! Silakan download di bawah.")

# --- AREA DOWNLOAD HASIL ---
if st.session_state.processed_images:
    st.write("---")
    st.header("📥 Download Hasil")
    
    # Grid Layout untuk hasil
    cols = st.columns(3)
    for i, (idx, data) in enumerate(st.session_state.processed_images.items()):
        with cols[i % 3]:
            st.image(data["img"], use_container_width=True)
            
            # Convert ke Buffer untuk Download
            buf = BytesIO()
            data["img"].save(buf, format="JPEG", quality=95)
            
            st.download_button(
                label=f"⬇️ Download #{idx+1}",
                data=buf.getvalue(),
                file_name=data["nama_file"],
                mime="image/jpeg",
                key=f"btn_dl_{idx}"
            )
