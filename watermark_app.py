# -*- coding: utf-8 -*- # Add this line for better encoding support
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
FONT_FILENAME = "arial.ttf" # Place this font file in the same directory
DEFAULT_FONT_SIZE = 50
DEFAULT_WATERMARK_COLOR = "#ffffff"
DEFAULT_OPACITY = 0.5
DEFAULT_LOGO_SCALE = 0.15
DEFAULT_PADDING = 30
DEFAULT_BRAND_NAME = "JhumJhum "
DEFAULT_ADD_LOGO_BACKDROP = True
DEFAULT_BACKDROP_COLOR = (255, 255, 255, 180) # White with alpha
DEFAULT_BACKDROP_OFFSET = (2, 2)
ALLOWED_IMAGE_TYPES = ["png", "jpg", "jpeg"]
ALLOWED_UPLOAD_TYPES = ["zip"] + ALLOWED_IMAGE_TYPES
KNOWN_ZIP_MIMES = ["application/zip", "application/x-zip", "application/x-zip-compressed"]

# --- Password Protection ---
def check_password():
    """Checks if the user is authenticated using secrets."""
    if "APP_PASSWORD_HASH" not in st.secrets:
        st.error("Password configuration missing in st.secrets.")
        st.warning("Please add `APP_PASSWORD_HASH = 'your_sha256_hash'` to your Streamlit secrets.")
        st.stop(); return False
    APP_PASSWORD_HASH = st.secrets["APP_PASSWORD_HASH"]

    def password_entered():
        entered_hash = hashlib.sha256(st.session_state["password"].encode()).hexdigest()
        st.session_state["authenticated"] = (entered_hash == APP_PASSWORD_HASH)
        if not st.session_state["authenticated"]: st.error("❌ Incorrect password")

    if "authenticated" not in st.session_state: st.session_state["authenticated"] = False
    if st.session_state.get("authenticated", False): return True

    st.text_input("Enter password:", type="password", on_change=password_entered, key="password")
    if not st.session_state.get("authenticated", False):
         st.warning("Please enter the correct password to proceed.")
         st.stop()
    return st.session_state.get("authenticated", False)

# --- Function to Prepare Input Images (with file extension fallback) ---
def prepare_input_images(uploaded_files, target_dir):
    """
    Clears the target directory and populates it with images from uploaded files.
    Handles both ZIP archives and individual image files.
    Returns True if processing finished, False on critical errors or if no images are found.
    """
    if not uploaded_files:
        st.warning("No files uploaded.")
        return False

    if os.path.exists(target_dir):
        try: shutil.rmtree(target_dir)
        except OSError as e:
            st.error(f"Error clearing previous input directory {target_dir}: {e}"); return False
    try: os.makedirs(target_dir)
    except OSError as e:
        st.error(f"Error creating input directory {target_dir}: {e}"); return False

    any_processing_error = False
    with st.spinner("Preparing uploaded images..."):
        for uploaded_file in uploaded_files:
            try:
                is_zip = False
                if uploaded_file.type in KNOWN_ZIP_MIMES or (uploaded_file.name and uploaded_file.name.lower().endswith(".zip")):
                    is_zip = True
                
                if is_zip:
                    st.write(f"Extracting ZIP file: `{uploaded_file.name}`")
                    try:
                        zip_file_bytes = BytesIO(uploaded_file.getvalue())
                        with zipfile.ZipFile(zip_file_bytes, "r") as zip_ref:
                            zip_ref.extractall(target_dir)
                        st.success(f"✅ Extracted `{uploaded_file.name}`")
                    except Exception as e:
                        st.error(f"❌ Error extracting ZIP `{uploaded_file.name}`: {e}"); any_processing_error = True
                
                else:
                    is_allowed_image = False
                    file_ext = os.path.splitext(uploaded_file.name)[1].lower().lstrip('.')
                    if uploaded_file.type and uploaded_file.type.split('/')[-1] in ALLOWED_IMAGE_TYPES:
                        is_allowed_image = True
                    elif file_ext in ALLOWED_IMAGE_TYPES:
                        is_allowed_image = True
                        st.write(f"Info: Accepting file '{uploaded_file.name}' based on its extension.")
                    
                    if is_allowed_image:
                        img_path = os.path.join(target_dir, uploaded_file.name)
                        with open(img_path, "wb") as f:
                            f.write(uploaded_file.getvalue())
                    else:
                        st.warning(f"⚠️ Skipping unsupported file type: `{uploaded_file.name}`")
            
            except Exception as e:
                st.error(f"❌ Unexpected error processing file `{uploaded_file.name}`: {e}"); any_processing_error = True

    if any_processing_error:
         st.warning("Some files could not be processed correctly.")

    image_files_found = any(f.lower().endswith(tuple(f".{ext}" for ext in ALLOWED_IMAGE_TYPES)) for _, _, files in os.walk(target_dir) for f in files)
    if not image_files_found:
        st.error("❌ No valid image files were found after processing uploads.")
        return False
    return True

# --- NEW: Helper function for resizing with padding ---
def resize_with_padding(img, target_width, target_height, bg_color=(255, 255, 255)):
    """
    Resizes an image to fit within target dimensions while maintaining aspect ratio.
    Pads the remaining space with a specified background color. The returned image is RGBA.
    """
    original_ratio = img.width / img.height
    target_ratio = target_width / target_height

    if original_ratio > target_ratio:
        new_width = target_width
        new_height = int(new_width / original_ratio)
    else:
        new_height = target_height
        new_width = int(new_height * original_ratio)

    try:
        from PIL.Image import Resampling
        resized_img = img.resize((new_width, new_height), Resampling.LANCZOS)
    except ImportError:
        resized_img = img.resize((new_width, new_height), Image.LANCZOS)

    new_img = Image.new("RGBA", (target_width, target_height), bg_color + (255,))
    paste_x = (target_width - new_width) // 2
    paste_y = (target_height - new_height) // 2
    new_img.paste(resized_img, (paste_x, paste_y), resized_img if resized_img.mode == 'RGBA' else None)
    return new_img

# --- Main App Logic ---
if not check_password():
    st.stop()

st.set_page_config(layout="wide")
st.title("🖼️ Add Logo & Brand Watermark")

for folder in [PRODUCTS_DIR, OUTPUT_DIR]:
    os.makedirs(folder, exist_ok=True)

col1, col2 = st.columns(2)
with col1:
    logo_file = st.file_uploader("1. Upload Logo (PNG)", type=["png"], key="logo_uploader")
with col2:
    uploaded_files = st.file_uploader(
        "2. Upload Product Images (ZIP, PNG, JPG, JPEG)",
        type=ALLOWED_UPLOAD_TYPES,
        accept_multiple_files=True,
        key="product_images_uploader"
    )

if not logo_file or not uploaded_files:
    st.info("💡 Please upload both a logo and product images to continue.")
    st.stop()

# --- Main Processing Block ---
try:
    logo_bytes = BytesIO(logo_file.getvalue())
    original_logo = Image.open(logo_bytes).convert("RGBA")

    # --- Configuration ---
    st.sidebar.header("⚙️ Customization")
    
    # --- NEW: Output Dimensions UI ---
    st.sidebar.subheader("📐 Output Dimensions")
    DIMENSIONS = {
        "Original Size": None,
        "Instagram Post (1:1)": (1080, 1080),
        "Instagram Story (9:16)": (1080, 1920),
        "Instagram Portrait (4:5)": (1080, 1350),
        "Facebook Post (1.91:1)": (1200, 630),
        "Pinterest Pin (2:3)": (1000, 1500)
    }
    selected_dimensions_names = st.sidebar.multiselect(
        "Select output sizes",
        options=list(DIMENSIONS.keys()),
        default=["Original Size", "Instagram Post (1:1)"],
        key="output_dimensions_select"
    )
    resize_bg_color_hex = st.sidebar.color_picker(
        "Background color for resizing", "#FFFFFF", key="resize_bg_color_picker",
        help="Color for padding if image ratio doesn't match target."
    )
    try: resize_bg_color = ImageColor.getrgb(resize_bg_color_hex)
    except ValueError: resize_bg_color = (255, 255, 255)
    
    # --- Watermark & Logo Settings ---
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

    try:
        font = ImageFont.truetype(FONT_FILENAME, font_size)
    except IOError:
        st.sidebar.warning(f"Font '{FONT_FILENAME}' not found. Using default font.")
        font = ImageFont.load_default()

    if not prepare_input_images(uploaded_files, PRODUCTS_DIR):
        st.stop()

    files_to_process_paths = [os.path.join(r, f) for r, _, files in os.walk(PRODUCTS_DIR) for f in files if f.lower().endswith(tuple(f".{ext}" for ext in ALLOWED_IMAGE_TYPES)) and not f.startswith('.')]
    if not files_to_process_paths:
        st.warning("⚠️ No valid image files found after filtering."); st.stop()

    st.write(f"Found {len(files_to_process_paths)} source images to process.")
    progress_bar = st.progress(0)
    status_text = st.empty()
    processed_files, processed_count, error_count = [], 0, 0

    base_text_color = ImageColor.getrgb(watermark_color_hex)
    text_color = base_text_color + (int(255 * opacity),)

    if os.path.exists(OUTPUT_DIR): shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    # --- Image Processing Loop ---
    for i, product_path in enumerate(files_to_process_paths):
        base_fname = os.path.basename(product_path)
        status_text.text(f"Processing: {base_fname} ({i + 1}/{len(files_to_process_paths)})")
        
        output_sub_dir = os.path.dirname(os.path.join(OUTPUT_DIR, os.path.relpath(product_path, PRODUCTS_DIR)))
        os.makedirs(output_sub_dir, exist_ok=True)

        try:
            product_img = Image.open(product_path).convert("RGBA")
            watermark_layer = Image.new("RGBA", product_img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(watermark_layer)

            # Logo
            logo_base = original_logo.copy()
            target_width = max(1, int(product_img.width * logo_scale))
            target_height = max(1, int(target_width * (logo_base.height / logo_base.width)))
            logo_resized = logo_base.resize((target_width, target_height), Image.LANCZOS)
            x_logo = product_img.width - logo_resized.width - padding
            y_logo = product_img.height - logo_resized.height - padding
            if add_logo_backdrop:
                shadow_img = Image.new("RGBA", logo_resized.size, DEFAULT_BACKDROP_COLOR)
                watermark_layer.paste(shadow_img, (x_logo + DEFAULT_BACKDROP_OFFSET[0], y_logo + DEFAULT_BACKDROP_OFFSET[1]), shadow_img)
            watermark_layer.paste(logo_resized, (x_logo, y_logo), logo_resized)

            # Text Watermark
            if brand_name.strip() and font:
                text_bbox = draw.textbbox((0, 0), brand_name.strip(), font=font, anchor="lt")
                text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
                if text_width > 0 and text_height > 0:
                    text_y = {"Top": padding, "Middle": (product_img.height - text_height) // 2}.get(position, product_img.height - text_height - padding)
                    step = text_width + horizontal_spacing
                    for x in range(-text_width, product_img.width + text_width, step):
                        draw.text((x, text_y), brand_name.strip(), font=font, fill=text_color, anchor="lt")

            # --- MODIFIED: Composite, Resize, and Save ---
            final_image = Image.alpha_composite(product_img, watermark_layer)
            out_fname_base = os.path.splitext(base_fname)[0]

            for dim_name in selected_dimensions_names:
                target_dims = DIMENSIONS.get(dim_name)
                if target_dims is None:
                    out_fname = f"{out_fname_base}_branded_original.png"
                    out_path = os.path.join(output_sub_dir, out_fname)
                    final_image.save(out_path, "PNG")
                    processed_files.append(out_path)
                else:
                    target_w, target_h = target_dims
                    resized_padded_image = resize_with_padding(final_image, target_w, target_h, resize_bg_color)
                    out_fname = f"{out_fname_base}_branded_{target_w}x{target_h}.png"
                    out_path = os.path.join(output_sub_dir, out_fname)
                    resized_padded_image.save(out_path, "PNG")
                    processed_files.append(out_path)
            
            processed_count += 1
        except Exception as e:
            st.error(f"❌ Failed to process `{base_fname}`: {e}"); error_count += 1
        
        progress_bar.progress((i + 1) / len(files_to_process_paths))

    status_text.text(f"Processing complete. {processed_count} images processed, {error_count} errors.")
    if not processed_files:
        st.error("🚫 No images were processed successfully."); st.stop()

    # --- Preview ---
    st.subheader("🖼️ Preview (First 5 Images)")
    cols = st.columns(min(len(processed_files), 5))
    for idx, path in enumerate(processed_files[:len(cols)]):
        with cols[idx]: st.image(path, caption=os.path.basename(path), use_container_width=True)

    # --- Zip and Download ---
    st.subheader("⬇️ Download Results")
    with st.spinner("Zipping processed images..."):
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in processed_files:
                zipf.write(file_path, arcname=os.path.relpath(file_path, OUTPUT_DIR))
        zip_buffer.seek(0)
    
    st.download_button(
        label=f"📦 Download All ({len(processed_files)}) Branded Images as ZIP",
        data=zip_buffer, file_name="branded_images.zip", mime="application/zip"
    )

except Exception as e:
    st.error("An unexpected error occurred during the main workflow:")
    st.error(traceback.format_exc())
