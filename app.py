import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from datetime import datetime
import os
from io import BytesIO
import googlemaps

# --- Inisialisasi Google Maps ---
# Mengambil API Key dari Secrets Streamlit (Lebih Aman)
try:
    gmaps = googlemaps.Client(key=st.secrets["GMAPS_KEY"])
except:
    gmaps = None

def get_address_from_coords(lat_str, lng_str):
    """Fungsi untuk mengambil alamat dari Google Maps"""
    if not gmaps:
        return "API Key belum diatur di Secrets."
    try:
        # Membersihkan input koordinat (menghilangkan S, E, dan spasi)
        lat = float(lat_str.upper().replace('S', '').replace(',', '.').strip()) * -1
        lng = float(lng_str.upper().replace('E', '').replace(',', '.').strip())
        
        reverse_geocode_result = gmaps.reverse_geocode((lat, lng))
        if reverse_geocode_result:
            return reverse_geocode_result[0]['formatted_address']
        return "Alamat tidak ditemukan."
    except Exception as e:
        return f"Error: Pastikan format koordinat benar (contoh: 5,0382S)"

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
    except:
        font = ImageFont.load_default()

    temp_draw = ImageDraw.Draw(img)
    bbox = temp_draw.multiline_textbbox((0, 0), text_content, font=font, align="right")
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]

    margin_x, margin_y = int(width * 0.03), int(height * 0.03)
    x, y = width - text_width - margin_x, height - text_height - margin_y

    shadow_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    offset = max(2, int(font_size / 15))
    shadow_draw.multiline_text((x + offset, y + offset), text_content, font=font, fill=(0, 0, 0, 160), align="right")
    
    final_img = Image.alpha_composite(img, shadow_layer.filter(ImageFilter.GaussianBlur(radius=max(1, int(font_size / 30)))))
    ImageDraw.Draw(final_img).multiline_text((x, y), text_content, font=font, fill="white", align="right")

    return final_img

# --- UI STREAMLIT ---
st.set_page_config(page_title="Stamp Foto GPS", layout="wide")
st.title("📸 Stamp Foto Google Maps Otomatis")

if 'processed_images' not in st.session_state:
    st.session_state.processed_images = {}

uploaded_files = st.file_uploader("📂 Pilih Foto", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if uploaded_files:
    with st.form("form_proses"):
        input_data = []
        for i, file in enumerate(uploaded_files[:5]):
            st.markdown(f"### Foto #{i+1}")
            col_img, col_ctrl = st.columns([1, 2])
            
            with col_img:
                st.image(Image.open(file), use_container_width=True)
            
            with col_ctrl:
                c1, c2 = st.columns(2)
                in_lat = c1.text_input("Latitude", value="5,0382S", key=f"lat_{i}")
                in_lng = c2.text_input("Longitude", value="105,2763E", key=f"lng_{i}")
                
                # Tombol Aksi Otomatis
                current_addr = "Tanggul Angin, Lampung" # Default awal
                if st.form_submit_button(f"🔍 Cek Alamat Otomatis #{i+1}"):
                    current_addr = get_address_from_coords(in_lat, in_lng)
                
                in_waktu = st.text_input("Waktu", value=datetime.now().strftime("%d %b %Y %H.%M.%S"), key=f"w_{i}")
                in_lokasi = st.text_area("Lokasi (Bisa Edit Manual)", value=current_addr, key=f"l_{i}")
                
                teks_full = f"{in_waktu}\n{in_lat} {in_lng}\n{in_lokasi}"
                input_data.append({"file": file, "teks": teks_full, "index": i, "nama": in_waktu})

        submit_all = st.form_submit_button("🚀 PROSES SEMUA FOTO")

    if submit_all:
        for item in input_data:
            img = Image.open(item["file"])
            res = add_stamp_to_image(img, item["teks"])
            st.session_state.processed_images[item["index"]] = {"image": res.convert("RGB"), "nama": item["nama"]}
        st.success("✅ Selesai!")

# --- DOWNLOAD AREA ---
if st.session_state.processed_images:
    st.markdown("---")
    cols = st.columns(len(st.session_state.processed_images))
    for i, (idx, data) in enumerate(st.session_state.processed_images.items()):
        with cols[i]:
            st.image(data["image"], use_container_width=True)
            buf = BytesIO()
            data["image"].save(buf, format="JPEG", quality=95)
            st.download_button("Download", buf.getvalue(), file_name=f"{data['nama']}.jpg", key=f"dl_{idx}")
