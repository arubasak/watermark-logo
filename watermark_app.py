# -*- coding: utf-8 -*-
import streamlit as st
import os
import shutil
import zipfile
from PIL import Image, ImageDraw, ImageFont, ImageColor
from io import BytesIO
import hashlib
import traceback

# --- Constants ---
PRODUCTS_DIR = "products"
OUTPUT_DIR = "branded_products"
FONT_FILENAME = "arial.ttf"
DEFAULT_FONT_SIZE = 50
DEFAULT_WATERMARK_COLOR = "#ffffff"
DEFAULT_OPACITY = 0.5
DEFAULT_LOGO_SCALE = 0.15
DEFAULT_PADDING = 30
DEFAULT_BRAND_NAME = "JhumJhum "
DEFAULT_ADD_LOGO_BACKDROP = True
DEFAULT_BACKDROP_COLOR = (255, 255, 255, 180)
DEFAULT_BACKDROP_OFFSET = (2, 2)
ALLOWED_IMAGE_TYPES = ["png", "jpg", "jpeg"]
ALLOWED_UPLOAD_TYPES = ["zip"] + ALLOWED_IMAGE_TYPES
KNOWN_ZIP_MIMES = ["application/zip", "application/x-zip", "application/x-zip-compressed"]

# --- Password Protection ---
def check_password():
    if "APP_PASSWORD_HASH" not in st.secrets:
        st.error("Password configuration missing.")
        st.stop()
    APP_PASSWORD_HASH = st.secrets["APP_PASSWORD_HASH"]

    def password_entered():
        entered_hash = hashlib.sha256(st.session_state["password"].encode()).hexdigest()
        st.session_state["authenticated"] = (entered_hash == APP_PASSWORD_HASH)
        if not st.session_state["authenticated"]: st.error("❌ Incorrect password")

    if not st.session_state.get("authenticated", False):
        st.text_input("Enter password:", type="password", on_change=password_entered, key="password")
        st.warning("Please enter the correct password to proceed.")
        st.stop()
    return True

# --- Function to Prepare Input Images (with file extension fallback) ---
def prepare_input_images(uploaded_files, target_dir):
    if not uploaded_files:
        st.warning("No files uploaded.")
        return False
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir)

    with st.spinner("Preparing uploaded images..."):
        for uploaded_file in uploaded_files:
            try:
                is_zip = False
                if uploaded_file.type in KNOWN_ZIP_MIMES or (uploaded_file.name and uploaded_file.name.lower().endswith(".zip")):
                    is_zip = True
                
                if is_zip:
                    with zipfile.ZipFile(BytesIO(uploaded_file.getvalue()), "r") as zip_ref:
                        zip_ref.extractall(target_dir)
                else:
                    file_ext = os.path.splitext(uploaded_file.name)[1].lower().lstrip('.')
                    if (uploaded_file.type and uploaded_file.type.split('/')[-1] in ALLOWED_IMAGE_TYPES) or (file_ext in ALLOWED_IMAGE_TYPES):
                        with open(os.path.join(target_dir, uploaded_file.name), "wb") as f:
                            f.write(uploaded_file.getvalue())
                    else:
                        st.warning(f"⚠️ Skipping unsupported file type: `{uploaded_file.name}`")
            except Exception as e:
                st.error(f"❌ Error processing `{uploaded_file.name}`: {e}")

    image_files_found = any(f.lower().endswith(tuple(f".{ext}" for ext in ALLOWED_IMAGE_TYPES)) for r, _, files in os.walk(target_dir) for f in files)
    if not image_files_found:
        st.error("❌ No valid image files were found after processing uploads.")
        return False
    return True

# --- Helper function for resizing with padding ---
def resize_with_padding(img, target_width, target_height, bg_color=(255, 255, 255)):
    original_ratio = img.width / img.height
    target_ratio = target_width / target_height
    if original_ratio > target_ratio:
        new_width = target_width
        new_height = int(new_width / original_ratio)
    else:
        new_height = target_height
        new_width = int(new_height * original_ratio)
    
    try: from PIL.Image import Resampling; resized_img = img.resize((new_width, new_height), Resampling.LANCZOS)
    except ImportError: resized_img = img.resize((new_width, new_height), Image.LANCZOS)

    new_img = Image.new("RGBA", (target_width, target_height), bg_color + (255,))
    paste_x = (target_width - new_width) // 2
    paste_y = (target_height - new_height) // 2
    new_img.paste(resized_img, (paste_x, paste_y), resized_img if resized_img.mode == 'RGBA' else None)
    return new_img

# --- Main App Logic ---
if not check_password():
    st.stop()

st.set_page_config(layout="wide")
st.title("🖼️ JhumJhum's Brand Watermark App")

for folder in [PRODUCTS_DIR, OUTPUT_DIR]:
    os.makedirs(folder, exist_ok=True)

col1, col2 = st.columns(2)
with col1:
    logo_file = st.file_uploader("1. Upload Logo (PNG recommended)", type=ALLOWED_IMAGE_TYPES) 
with col2:
    uploaded_files = st.file_uploader("2. Upload Product Images (ZIP, PNG, JPG, JPEG)", type=ALLOWED_UPLOAD_TYPES, accept_multiple_files=True)

if not logo_file or not uploaded_files:
    st.info("💡 Please upload both a logo and product images to continue.")
    st.stop()

try:
    # --- THE DEFINITIVE FIX ---
    # Open the uploaded file and convert to RGBA. This handles all formats gracefully.
    # All strict checks have been removed.
    original_logo = Image.open(BytesIO(logo_file.getvalue())).convert("RGBA")

    # --- Configuration ---
    st.sidebar.header("⚙️ Customization")
    st.sidebar.subheader("📐 Output Dimensions")
    DIMENSIONS = {
        "Original Size": None, "Instagram Post (1:1)": (1080, 1080), "Instagram Story (9:16)": (1080, 1920),
        "Instagram Portrait (4:5)": (1080, 1350), "Facebook Post (1.91:1)": (1200, 630), "Pinterest Pin (2:3)": (1000, 1500)
    }
    selected_dimensions_names = st.sidebar.multiselect("Select output sizes", options=list(DIMENSIONS.keys()), default=["Original Size", "Instagram Post (1:1)"])
    resize_bg_color = ImageColor.getrgb(st.sidebar.color_picker("Background color for padding", "#FFFFFF"))

    st.sidebar.subheader("💧 Watermark & Logo")
    logo_scale = st.sidebar.slider("Logo Size", 0.05, 0.5, DEFAULT_LOGO_SCALE, 0.01)
    add_logo_backdrop = st.sidebar.checkbox("Add logo backdrop", DEFAULT_ADD_LOGO_BACKDROP)
    brand_name = st.sidebar.text_input("Watermark Text", DEFAULT_BRAND_NAME)
    font_size = st.sidebar.slider("Font Size", 10, 150, DEFAULT_FONT_SIZE, 5)
    opacity = st.sidebar.slider("Text Opacity", 0.0, 1.0, DEFAULT_OPACITY, 0.05)
    watermark_color_hex = st.sidebar.color_picker("Text Color", DEFAULT_WATERMARK_COLOR)
    position = st.sidebar.selectbox("Text Position", ["Top", "Middle", "Bottom"], index=1)
    horizontal_spacing = st.sidebar.slider("Text Spacing", 10, 200, 50, 10)
    padding = st.sidebar.slider("Edge Padding", 5, 100, DEFAULT_PADDING, 5)

    try: font = ImageFont.truetype(FONT_FILENAME, font_size)
    except IOError:
        st.sidebar.warning(f"Font '{FONT_FILENAME}' not found. Using default."); font = ImageFont.load_default()

    if not prepare_input_images(uploaded_files, PRODUCTS_DIR):
        st.stop()

    files_to_process = [os.path.join(r, f) for r, _, fs in os.walk(PRODUCTS_DIR) for f in fs if not f.startswith('.') and f.lower().endswith(tuple(f".{ext}" for ext in ALLOWED_IMAGE_TYPES))]
    if not files_to_process:
        st.warning("⚠️ No valid image files found after filtering."); st.stop()

    st.write(f"Found {len(files_to_process)} source images to process.")
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    processed_images_map = {}
    processed_count, error_count = 0, 0
    text_color = ImageColor.getrgb(watermark_color_hex) + (int(255 * opacity),)

    if os.path.exists(OUTPUT_DIR): shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    for i, product_path in enumerate(files_to_process):
        base_fname = os.path.basename(product_path)
        status_text.text(f"Processing: {base_fname} ({i + 1}/{len(files_to_process)})")
        processed_images_map[base_fname] = []
        
        try:
            product_img = Image.open(product_path).convert("RGBA")
            watermark_layer = Image.new("RGBA", product_img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(watermark_layer)

            logo = original_logo.copy()
            target_w = max(1, int(product_img.width * logo_scale))
            target_h = max(1, int(target_w * (logo.height / logo.width)))
            logo_resized = logo.resize((target_w, target_h), Image.LANCZOS)
            x_logo, y_logo = product_img.width - target_w - padding, product_img.height - target_h - padding
            if add_logo_backdrop:
                backdrop = Image.new("RGBA", logo_resized.size, DEFAULT_BACKDROP_COLOR)
                watermark_layer.paste(backdrop, (x_logo + DEFAULT_BACKDROP_OFFSET[0], y_logo + DEFAULT_BACKDROP_OFFSET[1]), backdrop)
            watermark_layer.paste(logo_resized, (x_logo, y_logo), logo_resized)

            if brand_name.strip():
                bbox = draw.textbbox((0, 0), brand_name.strip(), font=font, anchor="lt")
                w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
                if w > 0:
                    y_text = {"Top": padding, "Middle": (product_img.height - h) // 2}.get(position, product_img.height - h - padding)
                    for x in range(-w, product_img.width + w, w + horizontal_spacing):
                        draw.text((x, y_text), brand_name.strip(), font=font, fill=text_color, anchor="lt")
            
            final_image = Image.alpha_composite(product_img, watermark_layer)
            out_fname_base = os.path.splitext(base_fname)[0]

            for dim_name in selected_dimensions_names:
                target_dims = DIMENSIONS.get(dim_name)
                output_sub_dir = os.path.dirname(os.path.join(OUTPUT_DIR, os.path.relpath(product_path, PRODUCTS_DIR)))
                os.makedirs(output_sub_dir, exist_ok=True)
                
                if target_dims:
                    resized_img = resize_with_padding(final_image, target_dims[0], target_dims[1], resize_bg_color)
                    out_fname = f"{out_fname_base}_branded_{target_dims[0]}x{target_dims[1]}.png"
                    out_path = os.path.join(output_sub_dir, out_fname)
                    resized_img.save(out_path, "PNG")
                else:
                    out_fname = f"{out_fname_base}_branded_original.png"
                    out_path = os.path.join(output_sub_dir, out_fname)
                    final_image.save(out_path, "PNG")
                
                processed_images_map[base_fname].append({"path": out_path, "dim_name": dim_name})
            
            processed_count += 1
        except Exception as e:
            st.error(f"❌ Failed to process `{base_fname}`: {e}"); error_count += 1
        
        progress_bar.progress((i + 1) / len(files_to_process))

    status_text.text(f"Processing complete. {processed_count} images processed, {error_count} errors.")
    all_processed_paths = [v['path'] for versions in processed_images_map.values() for v in versions]

    if not all_processed_paths:
        st.error("🚫 No images were processed successfully."); st.stop()

    st.subheader("🖼️ Preview (First 5 Results)")
    cols = st.columns(min(len(all_processed_paths), 5))
    for idx, path in enumerate(all_processed_paths[:len(cols)]):
        with cols[idx]: st.image(path, caption=os.path.basename(path), use_container_width=True)

    st.subheader("⬇️ Individual Downloads")
    for base_fname, versions in processed_images_map.items():
        if not versions: continue
        with st.expander(f"Downloads for: {base_fname}"):
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(versions[0]['path'], use_container_width=True)
            with col2:
                for version in versions:
                    with open(version['path'], "rb") as f:
                        st.download_button(
                            label=f"Download '{version['dim_name']}'",
                            data=f.read(),
                            file_name=os.path.basename(version['path']),
                            mime="image/png",
                            key=f"dl_{base_fname}_{version['dim_name']}"
                        )

    st.subheader("📦 Download All as ZIP")
    with st.spinner("Zipping processed images..."):
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in all_processed_paths:
                zipf.write(file_path, arcname=os.path.relpath(file_path, OUTPUT_DIR))
        zip_buffer.seek(0)
    
    st.download_button(
        label=f"📦 Download All ({len(all_processed_paths)}) Branded Images",
        data=zip_buffer, file_name="branded_images.zip", mime="application/zip"
    )

except Exception as e:
    st.error("An unexpected error occurred in the main workflow:")
    st.error(traceback.format_exc())
