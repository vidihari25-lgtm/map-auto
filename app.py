import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from datetime import datetime
import os
from io import BytesIO
import googlemaps
from streamlit_folium import st_folium
import folium

# --- Inisialisasi Google Maps ---
try:
    gmaps = googlemaps.Client(key=st.secrets["GMAPS_KEY"])
except:
    gmaps = None

def get_address_from_coords(lat, lng):
    if not gmaps: return "API Key belum diatur."
    try:
        res = gmaps.reverse_geocode((lat, lng))
        return res[0]['formatted_address'] if res else "Alamat tidak ditemukan."
    except: return "Gagal ambil alamat."

def add_stamp_to_image(image, text_content):
    target_width = 1280
    w_percent = (target_width / float(image.size[0]))
    h_size = int((float(image.size[1]) * float(w_percent)))
    image = image.resize((target_width, h_size), Image.Resampling.LANCZOS)
    img = image.convert("RGBA")
    width, height = img.size
    
    font_size = int(width * 0.04) 
    font_file = "arial.ttf"
    try:
        font = ImageFont.truetype(font_file, font_size) if os.path.exists(font_file) else ImageFont.load_default()
    except: font = ImageFont.load_default()

    draw = ImageDraw.Draw(img)
    bbox = draw.multiline_textbbox((0, 0), text_content, font=font, align="right")
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    mx, my = int(width * 0.03), int(height * 0.03)
    x, y = width - tw - mx, height - th - my

    # Shadow
    shadow = Image.new('RGBA', img.size, (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    off = max(2, int(font_size / 15))
    s_draw.multiline_text((x + off, y + off), text_content, font=font, fill=(0, 0, 0, 160), align="right")
    
    final = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(radius=max(1, int(font_size / 30)))))
    ImageDraw.Draw(final).multiline_text((x, y), text_content, font=font, fill="white", align="right")
    return final

# --- UI ---
st.set_page_config(page_title="GPS Stamp Pro", layout="wide")
st.title("📸 Stamp Foto & Map Picker (Fake GPS Style)")

uploaded_files = st.file_uploader("📂 Upload Foto", type=["jpg", "png"], accept_multiple_files=True)

if uploaded_files:
    if 'data_per_foto' not in st.session_state:
        st.session_state.data_per_foto = {}

    for i, file in enumerate(uploaded_files[:3]): # Limit 3 foto agar ringan
        st.markdown(f"---")
        st.subheader(f"Edit Foto #{i+1}")
        
        col_img, col_map = st.columns([1, 1])
        
        # Inisialisasi posisi awal (Default Lampung)
        lat_init, lng_init = -5.0382, 105.2763
        
        with col_map:
            st.info("📍 Klik pada peta untuk mengubah/menggeser lokasi (Fake GPS)")
            m = folium.Map(location=[lat_init, lng_init], zoom_start=15)
            m.add_child(folium.LatLngPopup()) # Biar bisa klik dapat koordinat
            map_data = st_folium(m, height=300, key=f"map_{i}")
            
            # Jika peta diklik, update koordinat
            if map_data.get("last_clicked"):
                lat_init = map_data["last_clicked"]["lat"]
                lng_init = map_data["last_clicked"]["lng"]

        with col_img:
            # Format tampilan koordinat ala GPS asli
            lat_disp = f"{abs(lat_init):.4f}{'S' if lat_init < 0 else 'N'}"
            lng_disp = f"{abs(lng_init):.4f}{'E' if lng_init > 0 else 'W'}"
            
            c1, c2 = st.columns(2)
            final_lat = c1.text_input("Lat", value=lat_disp, key=f"it_lat_{i}")
            final_lng = c2.text_input("Lng", value=lng_disp, key=f"it_lng_{i}")
            
            # Tombol Ambil Alamat Otomatis
            auto_addr = ""
            if st.button(f"🔍 Ambil Alamat dari Peta #{i+1}"):
                auto_addr = get_address_from_coords(lat_init, lng_init)
            
            in_lokasi = st.text_area("Detail Lokasi", value=auto_addr if auto_addr else "Tanggul Angin, Lampung", key=f"loc_{i}")
            in_waktu = st.text_input("Waktu", value=datetime.now().strftime("%d %b %Y %H.%M.%S"), key=f"tim_{i}")

            # Tombol Proses Foto Ini
            if st.button(f"🚀 Proses Stamp Foto #{i+1}"):
                full_text = f"{in_waktu}\n{final_lat} {final_lng}\n{in_lokasi}"
                img_res = add_stamp_to_image(Image.open(file), full_text)
                st.session_state.data_per_foto[i] = {"img": img_res.convert("RGB"), "nama": in_waktu}
                st.success(f"Foto #{i+1} Berhasil Di-stamp!")

# --- HASIL ---
if 'data_per_foto' in st.session_state and st.session_state.data_per_foto:
    st.markdown("### 📥 Download Hasil")
    for idx, data in st.session_state.data_per_foto.items():
        st.image(data["img"], width=400)
        buf = BytesIO()
        data["img"].save(buf, format="JPEG")
        st.download_button(f"Download Foto #{idx+1}", buf.getvalue(), f"stamp_{idx}.jpg")
