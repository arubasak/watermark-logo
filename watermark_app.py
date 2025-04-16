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
DEFAULT_BACKDROP_COLOR = (255, 255, 255, 180) # White with alpha 180/255
DEFAULT_BACKDROP_OFFSET = (2, 2)
ALLOWED_IMAGE_TYPES = ["png", "jpg", "jpeg"]
ALLOWED_UPLOAD_TYPES = ["zip"] + ALLOWED_IMAGE_TYPES

# --- Password Protection ---
def check_password():
    # ... (password checking logic remains the same)
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

# --- Function to Prepare Input Images ---
def prepare_input_images(uploaded_files, target_dir):
    """
    Clears the target directory and populates it with images from uploaded files.
    Handles both ZIP archives and individual image files.
    Returns True if successful, False otherwise.
    """
    if not uploaded_files:
        st.warning("No files uploaded.")
        return False

    # Clear the target directory before processing new files
    if os.path.exists(target_dir):
        try:
            shutil.rmtree(target_dir)
        except OSError as e:
            st.error(f"Error clearing previous input directory {target_dir}: {e}")
            return False
    try:
        os.makedirs(target_dir)
    except OSError as e:
        st.error(f"Error creating input directory {target_dir}: {e}")
        return False

    success = True
    with st.spinner("Preparing uploaded images..."):
        for uploaded_file in uploaded_files:
            try:
                # Check if it's a ZIP file
                if uploaded_file.type == "application/zip":
                    st.write(f"Extracting ZIP file: `{uploaded_file.name}`")
                    try:
                        zip_file_bytes = BytesIO(uploaded_file.read())
                        with zipfile.ZipFile(zip_file_bytes, "r") as zip_ref:
                            zip_ref.extractall(target_dir)
                        st.success(f"✅ Extracted `{uploaded_file.name}`")
                    except zipfile.BadZipFile:
                        st.error(f"❌ Invalid ZIP file: `{uploaded_file.name}`. Skipping.")
                        success = False
                    except Exception as e:
                        st.error(f"❌ Error extracting ZIP `{uploaded_file.name}`: {e}")
                        success = False

                # Check if it's an allowed image type
                elif uploaded_file.type.split('/')[-1] in ALLOWED_IMAGE_TYPES:
                    st.write(f"Processing image file: `{uploaded_file.name}`")
                    # Save the individual image file directly
                    img_path = os.path.join(target_dir, uploaded_file.name)
                    try:
                        with open(img_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        # Optional: Verify if it's a valid image after saving
                        # try:
                        #     Image.open(img_path).verify()
                        # except Exception:
                        #     st.warning(f"⚠️ Could not verify image format for `{uploaded_file.name}`, but saved.")
                        #     # os.remove(img_path) # Optionally remove if verification fails
                    except Exception as e:
                         st.error(f"❌ Error saving image `{uploaded_file.name}`: {e}")
                         success = False
                else:
                    st.warning(f"⚠️ Skipping unsupported file type: `{uploaded_file.name}` ({uploaded_file.type})")

            except Exception as e:
                st.error(f"❌ Unexpected error processing file `{uploaded_file.name}`: {e}")
                success = False

    if not success:
        st.warning("Some files could not be processed.")
    # Check if any valid images ended up in the directory
    image_files_found = any(f.lower().endswith(tuple(f".{ext}" for ext in ALLOWED_IMAGE_TYPES))
                           for _, _, files in os.walk(target_dir) for f in files)
    if not image_files_found:
        st.error("❌ No valid image files were found after processing uploads.")
        return False

    return image_files_found # Return true only if valid images exist

# --- Main App Logic ---
if not check_password():
    st.stop()

st.set_page_config(layout="wide")
st.title("🖼️ Add Logo & Brand Watermark")

for folder in [PRODUCTS_DIR, OUTPUT_DIR]:
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError as e:
        st.error(f"Error ensuring folder exists {folder}: {e}")
        st.stop()

# --- File Uploads ---
col1, col2 = st.columns(2)
with col1:
    logo_file = st.file_uploader("1. Upload Logo (PNG)", type=["png"], key="logo_uploader")
with col2:
    # UPDATED FILE UPLOADER: Accepts multiple files, ZIP or images
    uploaded_files = st.file_uploader(
        "2. Upload Product Images (ZIP or individual PNG/JPG/JPEG files)",
        type=ALLOWED_UPLOAD_TYPES,
        accept_multiple_files=True, # Allow selecting multiple files
        key="product_images_uploader"
    )

# --- Guard Clauses ---
if not logo_file:
    st.info("💡 Please upload a logo file.")
    st.stop()

if not uploaded_files: # Check if the list of uploaded files is empty
    st.info("💡 Please upload product images (ZIP or individual files).")
    st.stop()

# --- Process Files ---
try:
    original_logo = Image.open(logo_file).convert("RGBA")

    # --- Configuration ---
    st.sidebar.header("⚙️ Customization")
    # Logo Settings
    logo_scale = st.sidebar.slider("Logo Size (relative to image width)", 0.05, 0.5, DEFAULT_LOGO_SCALE, 0.01, key="logo_scale_slider")
    add_logo_backdrop = st.sidebar.checkbox("Add white backdrop to logo", DEFAULT_ADD_LOGO_BACKDROP, key="add_shadow_check")
    # Watermark Text Settings
    brand_name = st.sidebar.text_input("Watermark Text", DEFAULT_BRAND_NAME, key="brand_text_input")
    font_size = st.sidebar.slider("Watermark Font Size (pt)", 10, 150, DEFAULT_FONT_SIZE, 5, key="fontsize_slider")
    opacity = st.sidebar.slider("Watermark Text Opacity", 0.0, 1.0, DEFAULT_OPACITY, 0.05, key="opacity_slider")
    watermark_color_hex = st.sidebar.color_picker("Watermark Text Color", DEFAULT_WATERMARK_COLOR, key="color_picker")
    position = st.sidebar.selectbox("Watermark Text Position", ["Top", "Middle", "Bottom"], index=1, key="position_select")
    horizontal_spacing = st.sidebar.slider("Horizontal Text Spacing (px)", 10, 200, 50, 10, key="hspacing_slider")
    # General Settings
    padding = st.sidebar.slider("Logo/Text Padding (px from edge)", 5, 100, DEFAULT_PADDING, 5, key="padding_slider")

    # --- Font Loading ---
    st.sidebar.subheader("Font Status")
    font_load_status = st.sidebar.empty()
    font = None
    try:
        if os.path.exists(FONT_FILENAME):
            font = ImageFont.truetype(FONT_FILENAME, font_size)
            font_load_status.info(f"✅ Loaded: '{FONT_FILENAME}' (Size: {font_size}pt)")
        else:
            font_load_status.error(f"❌ Font file '{FONT_FILENAME}' not found!")
            st.sidebar.warning(f"Place '{FONT_FILENAME}' in the script's directory.")
            font = ImageFont.load_default()
            font_load_status.warning("ℹ️ Using default bitmap font. Size slider ineffective.")
    except Exception as e:
        font_load_status.error(f"❌ Error loading font '{FONT_FILENAME}': {e}")
        font = ImageFont.load_default()
        font_load_status.warning("ℹ️ Using default font due to error. Size slider ineffective.")

    # --- Prepare Input Images ---
    # Call the new function to handle uploaded files (ZIP or individual)
    if not prepare_input_images(uploaded_files, PRODUCTS_DIR):
        # Error messages are handled within the function
        st.stop() # Stop if preparation failed

    # --- Image Processing Setup ---
    processed_files = []
    files_to_process_paths = []
    # Find all image files recursively within PRODUCTS_DIR (populated by prepare_input_images)
    for root, _, files in os.walk(PRODUCTS_DIR):
        for f in files:
             if f.lower().endswith(tuple(f".{ext}" for ext in ALLOWED_IMAGE_TYPES)) and not f.startswith('.') and '__MACOSX' not in root:
                 full_path = os.path.join(root, f)
                 files_to_process_paths.append(full_path)

    if not files_to_process_paths:
        st.warning("⚠️ No valid image files found in the prepared input directory.")
        st.stop()

    st.write(f"Found {len(files_to_process_paths)} images to process.")
    progress_bar = st.progress(0)
    status_text = st.empty()
    processed_count = 0
    error_count = 0

    # Prepare text color
    try:
        base_text_color = ImageColor.getrgb(watermark_color_hex)
        text_color = base_text_color + (int(255 * opacity),)
    except ValueError:
        st.error(f"Invalid color format: {watermark_color_hex}. Using default white.")
        base_text_color = ImageColor.getrgb("#ffffff")
        text_color = base_text_color + (int(255 * opacity),)

    # Clear output directory
    if os.path.exists(OUTPUT_DIR):
        try:
            shutil.rmtree(OUTPUT_DIR); os.makedirs(OUTPUT_DIR)
        except OSError as e:
            st.error(f"Error clearing output directory {OUTPUT_DIR}: {e}"); st.stop()

    # --- Image Processing Loop ---
    # ... (The rest of the image processing loop remains exactly the same as before) ...
    # It reads from PRODUCTS_DIR and writes to OUTPUT_DIR
    for i, product_path in enumerate(files_to_process_paths):
        relative_path = os.path.relpath(product_path, PRODUCTS_DIR)
        base_fname = os.path.basename(product_path)
        status_text.text(f"Processing: {base_fname} ({i + 1}/{len(files_to_process_paths)})")

        output_sub_dir = os.path.dirname(os.path.join(OUTPUT_DIR, relative_path))
        if not os.path.exists(output_sub_dir):
             os.makedirs(output_sub_dir, exist_ok=True)

        try:
            product_img = Image.open(product_path).convert("RGBA")
            watermark_layer = Image.new("RGBA", product_img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(watermark_layer)

            # === Logo Application ===
            logo_base = original_logo.copy()
            target_width = max(1, int(product_img.width * logo_scale))
            aspect_ratio = logo_base.height / logo_base.width if logo_base.width > 0 else 1
            target_height = max(1, int(target_width * aspect_ratio))

            try:
                from PIL.Image import Resampling
                logo_resized = logo_base.resize((target_width, target_height), Resampling.LANCZOS)
            except ImportError:
                 logo_resized = logo_base.resize((target_width, target_height), Image.LANCZOS)

            x_logo = product_img.width - logo_resized.width - padding
            y_logo = product_img.height - logo_resized.height - padding
            logo_position = (x_logo, y_logo)

            if add_logo_backdrop:
                shadow_img = Image.new("RGBA", logo_resized.size, DEFAULT_BACKDROP_COLOR)
                shadow_position = (logo_position[0] + DEFAULT_BACKDROP_OFFSET[0], logo_position[1] + DEFAULT_BACKDROP_OFFSET[1])
                watermark_layer.paste(shadow_img, shadow_position, shadow_img)

            watermark_layer.paste(logo_resized, logo_position, logo_resized)

            # === Repeating Text Watermark ===
            cleaned_brand_name = brand_name.strip()
            if cleaned_brand_name and font:
                try:
                    text_bbox = draw.textbbox((0, 0), cleaned_brand_name, font=font, anchor="lt")
                    text_width = text_bbox[2] - text_bbox[0]; text_height = text_bbox[3] - text_bbox[1]

                    if text_width > 0 and text_height > 0:
                        if position == "Top": text_y = padding
                        elif position == "Middle": text_y = (product_img.height - text_height) // 2
                        else: text_y = product_img.height - text_height - padding

                        step = text_width + horizontal_spacing; step = max(1, step)
                        start_x = -(text_width % step if step > 0 else 0)

                        for x_text in range(start_x, product_img.width, step):
                            draw.text((x_text, text_y), cleaned_brand_name, font=font, fill=text_color, anchor="lt")
                    # else: # Don't warn for every file if text is empty/bad
                    #      if i == 0: st.warning(f"⚠️ Zero text dimensions for '{cleaned_brand_name}'. Skipping text.")

                except AttributeError as e:
                    if i == 0: # Only warn once per run for pillow issues
                       if 'textbbox' in str(e) or 'anchor' in str(e): st.warning(f"⚠️ Pillow version issue. Update Pillow? Skipping text.")
                       else: st.error(f"❌ Text attribute error: {e}. Skipping text.")
                    error_count += 1 # Still count error
                except Exception as text_err:
                    st.error(f"❌ Error drawing text for {base_fname}: {text_err}. Skipping text.")
                    error_count += 1

            # === Composite and Save ===
            final_image = Image.alpha_composite(product_img, watermark_layer)
            out_fname_base = os.path.splitext(base_fname)[0]
            out_fname = f"{out_fname_base}_branded.png"
            out_path = os.path.join(output_sub_dir, out_fname)
            final_image.save(out_path, "PNG")
            processed_files.append(out_path)
            processed_count += 1

        except Exception as img_err:
            st.error(f"❌ Failed to process image `{base_fname}`: {img_err}")
            st.error(traceback.format_exc())
            error_count += 1

        progress_bar.progress((i + 1) / len(files_to_process_paths))

    status_text.text(f"Processing complete. {processed_count} images processed, {error_count} errors.")
    progress_bar.empty()

    if not processed_files:
        st.error("🚫 No images were processed successfully.")
        st.stop()

    # --- Preview ---
    st.subheader("🖼️ Preview (First 5 Images)")
    # ... (Preview logic remains the same) ...
    if processed_files:
        num_columns = min(len(processed_files), 5)
        cols = st.columns(num_columns)
        for idx, path in enumerate(processed_files[:num_columns]):
             try:
                 with cols[idx]:
                    st.image(path, caption=os.path.basename(path), use_container_width=True)
             except Exception as e:
                 st.error(f"Error displaying preview for {os.path.basename(path)}: {e}")
    else:
        st.info("No images available for preview.")


    # --- Zip and Download ---
    st.subheader("⬇️ Download Results")
    # ... (Zip and Download logic remains the same) ...
    if processed_files:
        with st.spinner("Zipping processed images..."):
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file_path in processed_files:
                    arcname = os.path.relpath(file_path, OUTPUT_DIR)
                    zipf.write(file_path, arcname=arcname)
            zip_buffer.seek(0)
        st.download_button(
            label=f"📦 Download All ({processed_count}) Branded Images as ZIP",
            data=zip_buffer, file_name="branded_images.zip", mime="application/zip", key="download_zip_button")
    else:
        st.warning("No files were successfully processed to include in the ZIP.")

except Exception as e:
    st.error("An unexpected error occurred:")
    st.error(e)
    st.error(traceback.format_exc())
