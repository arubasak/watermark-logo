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
DEFAULT_BRAND_NAME = "JhumJhum " # Default Brand Name as per user code
DEFAULT_ADD_LOGO_BACKDROP = True
DEFAULT_BACKDROP_COLOR = (255, 255, 255, 180) # White with alpha 180/255
DEFAULT_BACKDROP_OFFSET = (2, 2)
ALLOWED_IMAGE_TYPES = ["png", "jpg", "jpeg"]
ALLOWED_UPLOAD_TYPES = ["zip"] + ALLOWED_IMAGE_TYPES
# List of known MIME types for ZIP files
KNOWN_ZIP_MIMES = ["application/zip", "application/x-zip", "application/x-zip-compressed"]

# --- Password Protection ---
def check_password():
    """Checks if the user is authenticated using secrets."""
    if "APP_PASSWORD_HASH" not in st.secrets:
        st.error("Password configuration missing in st.secrets.")
        st.warning("Please add `APP_PASSWORD_HASH = 'your_sha256_hash'` to your Streamlit secrets.")
        st.stop(); return False # Stop execution and return False
    APP_PASSWORD_HASH = st.secrets["APP_PASSWORD_HASH"]

    def password_entered():
        """Callback function when password input changes."""
        entered_hash = hashlib.sha256(st.session_state["password"].encode()).hexdigest()
        st.session_state["authenticated"] = (entered_hash == APP_PASSWORD_HASH)
        if not st.session_state["authenticated"]: st.error("❌ Incorrect password")

    # Initialize session state if it doesn't exist
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    # If already authenticated, return True
    if st.session_state.get("authenticated", False): return True

    # Show password input if not authenticated
    st.text_input("Enter password:", type="password", on_change=password_entered, key="password")
    if not st.session_state.get("authenticated", False):
         st.warning("Please enter the correct password to proceed.")
         st.stop() # Stop execution until password is correct

    # This part should technically not be reached if authentication fails due to st.stop()
    return st.session_state.get("authenticated", False)


# --- Function to Prepare Input Images ---
def prepare_input_images(uploaded_files, target_dir):
    """
    Clears the target directory and populates it with images from uploaded files.
    Handles both ZIP archives and individual image files.
    Returns True if processing finished (even with errors), False on critical setup errors.
    Returns False if no valid image files were found after processing.
    """
    if not uploaded_files:
        st.warning("No files uploaded.")
        return False # No files to process

    # Clear the target directory before processing new files
    if os.path.exists(target_dir):
        try:
            shutil.rmtree(target_dir)
        except OSError as e:
            st.error(f"Error clearing previous input directory {target_dir}: {e}")
            return False # Critical error
    try:
        os.makedirs(target_dir)
    except OSError as e:
        st.error(f"Error creating input directory {target_dir}: {e}")
        return False # Critical error

    any_processing_error = False # Flag to track if any non-critical error occurred
    with st.spinner("Preparing uploaded images..."):
        for uploaded_file in uploaded_files:
            try:
                # --- MODIFIED ZIP CHECK ---
                is_zip = False
                # 1. Check if MIME type is in our known list
                if uploaded_file.type in KNOWN_ZIP_MIMES:
                    is_zip = True
                # 2. Fallback: Check file extension (case-insensitive)
                elif uploaded_file.name and uploaded_file.name.lower().endswith(".zip"): # Check name exists
                     st.write(f"Info: Treating file '{uploaded_file.name}' as ZIP based on extension (MIME type was: '{uploaded_file.type}')")
                     is_zip = True

                if is_zip:
                # --- END MODIFIED ZIP CHECK ---
                    st.write(f"Extracting ZIP file: `{uploaded_file.name}`")
                    try:
                        # Use BytesIO for reading file content in memory from UploadedFile
                        zip_file_bytes = BytesIO(uploaded_file.getvalue()) # Use getvalue()
                        with zipfile.ZipFile(zip_file_bytes, "r") as zip_ref:
                            zip_ref.extractall(target_dir)
                        st.success(f"✅ Extracted `{uploaded_file.name}`")
                    except zipfile.BadZipFile:
                        st.error(f"❌ Invalid or corrupted ZIP file: `{uploaded_file.name}`. Skipping.")
                        any_processing_error = True # Mark that an error occurred
                    except Exception as e:
                        st.error(f"❌ Error extracting ZIP `{uploaded_file.name}`: {e}")
                        st.error(traceback.format_exc()) # More details on error
                        any_processing_error = True

                # Check if it's an allowed image type (only if not identified as zip)
                elif uploaded_file.type and uploaded_file.type.split('/')[-1] in ALLOWED_IMAGE_TYPES: # Check type exists
                    st.write(f"Processing image file: `{uploaded_file.name}`")
                    img_path = os.path.join(target_dir, uploaded_file.name)
                    try:
                        # Use getvalue() to get bytes from UploadedFile
                        with open(img_path, "wb") as f:
                            f.write(uploaded_file.getvalue())
                    except Exception as e:
                         st.error(f"❌ Error saving image `{uploaded_file.name}`: {e}")
                         any_processing_error = True
                else:
                    # Handle cases where file name or type might be None
                    file_name_for_log = getattr(uploaded_file, 'name', '[Unknown Filename]')
                    file_type_for_log = getattr(uploaded_file, 'type', '[Unknown Type]')
                    st.warning(f"⚠️ Skipping unsupported file type: `{file_name_for_log}` (Reported MIME type: {file_type_for_log})")

            except Exception as e:
                st.error(f"❌ Unexpected error processing file `{getattr(uploaded_file, 'name', '[Unknown Filename]')}`: {e}")
                st.error(traceback.format_exc()) # More details on error
                any_processing_error = True # Mark that an error occurred

    if any_processing_error:
         st.warning("Some files could not be processed or extracted correctly. Check logs above.")

    # Check if any valid images ended up in the directory *after* processing
    try:
        image_files_found = any(f.lower().endswith(tuple(f".{ext}" for ext in ALLOWED_IMAGE_TYPES))
                               for _, _, files in os.walk(target_dir) for f in files)
    except Exception as walk_err:
         st.error(f"Error checking for image files in {target_dir}: {walk_err}")
         return False # Cannot verify output

    if not image_files_found:
        if any_processing_error:
             st.error("❌ Processing failed and no valid image files were found.")
        else:
             st.error("❌ No valid image files were found after processing uploads (check ZIP content or file types).")
        return False # No usable images found

    # Return true if the process finished and at least one image was found
    return True


# --- Main App Logic ---
if not check_password():
    st.stop()

st.set_page_config(layout="wide")
st.title("🖼️ Add Logo & Brand Watermark")

# Ensure working directories exist
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
    # Read logo into memory once
    logo_bytes = BytesIO(logo_file.getvalue())
    original_logo = Image.open(logo_bytes).convert("RGBA")

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
        # Check if file exists before trying to load
        if os.path.exists(FONT_FILENAME):
            font = ImageFont.truetype(FONT_FILENAME, font_size)
            font_load_status.info(f"✅ Loaded: '{FONT_FILENAME}' (Size: {font_size}pt)")
        else:
             raise IOError(f"Font file '{FONT_FILENAME}' not found in script directory.")
    except IOError as e:
        font_load_status.error(f"❌ {e}")
        st.sidebar.warning("Using default bitmap font. Size slider will be ineffective.")
        font = ImageFont.load_default()
    except Exception as e_font:
        font_load_status.error(f"❌ Error loading font '{FONT_FILENAME}': {e_font}")
        st.sidebar.warning("Using default bitmap font due to error.")
        font = ImageFont.load_default()


    # --- Prepare Input Images ---
    # Call the function to handle uploaded files (ZIP or individual)
    if not prepare_input_images(uploaded_files, PRODUCTS_DIR):
        # Error messages are handled within the function
        st.warning("Stopping processing due to issues preparing input images.")
        st.stop() # Stop if preparation failed or resulted in no images

    # --- Image Processing Setup ---
    processed_files = []
    files_to_process_paths = []
    # Find all image files recursively within PRODUCTS_DIR
    for root, _, files in os.walk(PRODUCTS_DIR):
        for f in files:
             # Filter more robustly
             file_path_lower = os.path.join(root, f).lower()
             if file_path_lower.endswith(tuple(f".{ext}" for ext in ALLOWED_IMAGE_TYPES)) and not os.path.basename(f).startswith('.') and '__macosx' not in file_path_lower:
                 full_path = os.path.join(root, f)
                 files_to_process_paths.append(full_path)

    if not files_to_process_paths:
        st.warning("⚠️ No valid image files found in the prepared input directory after filtering.")
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

    # Clear output directory before processing
    if os.path.exists(OUTPUT_DIR):
        try:
            shutil.rmtree(OUTPUT_DIR); os.makedirs(OUTPUT_DIR)
        except OSError as e:
            st.error(f"Error clearing output directory {OUTPUT_DIR}: {e}"); st.stop()


    # --- Image Processing Loop ---
    for i, product_path in enumerate(files_to_process_paths):
        relative_path = os.path.relpath(product_path, PRODUCTS_DIR)
        base_fname = os.path.basename(product_path)
        status_text.text(f"Processing: {base_fname} ({i + 1}/{len(files_to_process_paths)})")

        # Create output subdirectories if they existed in the input
        output_sub_dir = os.path.dirname(os.path.join(OUTPUT_DIR, relative_path))
        if not os.path.exists(output_sub_dir):
             os.makedirs(output_sub_dir, exist_ok=True)

        try:
            # Open product image
            product_img = Image.open(product_path).convert("RGBA")
            # Create a transparent layer for watermarks
            watermark_layer = Image.new("RGBA", product_img.size, (0, 0, 0, 0)) # Fully transparent base
            draw = ImageDraw.Draw(watermark_layer)

            # === Logo Application ===
            logo_base = original_logo.copy() # Use the in-memory logo
            # Calculate target size
            target_width = max(1, int(product_img.width * logo_scale))
            aspect_ratio = logo_base.height / logo_base.width if logo_base.width > 0 else 1
            target_height = max(1, int(target_width * aspect_ratio))

            # Resize logo
            try:
                from PIL.Image import Resampling
                logo_resized = logo_base.resize((target_width, target_height), Resampling.LANCZOS)
            except ImportError:
                 logo_resized = logo_base.resize((target_width, target_height), Image.LANCZOS)

            # Calculate position (bottom-right)
            x_logo = product_img.width - logo_resized.width - padding
            y_logo = product_img.height - logo_resized.height - padding
            logo_position = (x_logo, y_logo)

            # Optional backdrop (paste onto watermark layer first)
            if add_logo_backdrop:
                shadow_img = Image.new("RGBA", logo_resized.size, DEFAULT_BACKDROP_COLOR)
                shadow_position = (logo_position[0] + DEFAULT_BACKDROP_OFFSET[0], logo_position[1] + DEFAULT_BACKDROP_OFFSET[1])
                watermark_layer.paste(shadow_img, shadow_position, shadow_img) # Use shadow as mask

            # Paste logo onto watermark layer (on top of backdrop if added)
            watermark_layer.paste(logo_resized, logo_position, logo_resized) # Use logo mask

            # === Repeating Text Watermark ===
            cleaned_brand_name = brand_name.strip()
            if cleaned_brand_name and font: # Check font object exists
                try:
                    # Use textbbox with anchor for better positioning
                    text_bbox = draw.textbbox((0, 0), cleaned_brand_name, font=font, anchor="lt")
                    text_width = text_bbox[2] - text_bbox[0]; text_height = text_bbox[3] - text_bbox[1]

                    if text_width > 0 and text_height > 0:
                        # Calculate vertical position
                        if position == "Top": text_y = padding
                        elif position == "Middle": text_y = (product_img.height - text_height) // 2
                        else: text_y = product_img.height - text_height - padding # Bottom

                        # Calculate horizontal repetition step
                        step = text_width + horizontal_spacing; step = max(1, step) # Ensure step > 0
                        start_x = -(text_width % step if step > 0 else 0) # Start slightly left

                        # Draw repeating text
                        for x_text in range(start_x, product_img.width + text_width, step): # Extend range slightly
                            draw.text((x_text, text_y), cleaned_brand_name, font=font, fill=text_color, anchor="lt")
                    # else: # Optional: Warn about zero dimensions only once
                    #      if i == 0: st.warning(f"⚠️ Zero text dimensions for '{cleaned_brand_name}'. Skipping text.")

                except AttributeError as e_text:
                    if i == 0: # Only warn once per run for pillow issues
                       if 'textbbox' in str(e_text) or 'anchor' in str(e_text): st.warning(f"⚠️ Pillow version/feature issue for text processing. Update Pillow? Skipping text.")
                       else: st.error(f"❌ Text attribute error: {e_text}. Skipping text.")
                    error_count += 1 # Still count error
                except Exception as text_err:
                    st.error(f"❌ Error drawing text for {base_fname}: {text_err}. Skipping text.")
                    error_count += 1

            # === Composite and Save ===
            # Alpha composite the watermark layer onto the product image
            final_image = Image.alpha_composite(product_img, watermark_layer)

            # Prepare output path and save as PNG
            out_fname_base = os.path.splitext(base_fname)[0]
            out_fname = f"{out_fname_base}_branded.png"
            out_path = os.path.join(output_sub_dir, out_fname)
            final_image.save(out_path, "PNG")
            processed_files.append(out_path)
            processed_count += 1

        # --- Error handling for individual image processing ---
        except Image.UnidentifiedImageError:
             st.error(f"❌ Failed to process image `{base_fname}`: Cannot identify image file. Skipping.")
             error_count += 1
        except Exception as img_err:
            st.error(f"❌ Failed to process image `{base_fname}`: {img_err}")
            st.error(traceback.format_exc()) # Show detailed traceback
            error_count += 1

        # Update progress bar
        progress_bar.progress((i + 1) / len(files_to_process_paths))

    status_text.text(f"Processing complete. {processed_count} images processed, {error_count} errors.")
    progress_bar.empty() # Clear progress bar

    if not processed_files:
        st.error("🚫 No images were processed successfully.")
        st.stop()

    # --- Preview ---
    st.subheader("🖼️ Preview (First 5 Images)")
    if processed_files:
        num_columns = min(len(processed_files), 5)
        cols = st.columns(num_columns)
        for idx, path in enumerate(processed_files[:num_columns]):
             try:
                 with cols[idx]:
                    # Display image, fit to column width
                    st.image(path, caption=os.path.basename(path), use_container_width=True)
             except Exception as e:
                 st.error(f"Error displaying preview for {os.path.basename(path)}: {e}")
    else:
        st.info("No images available for preview.")


    # --- Zip and Download ---
    st.subheader("⬇️ Download Results")
    if processed_files:
        with st.spinner("Zipping processed images..."):
            zip_buffer = BytesIO()
            # Use compression for smaller zip file
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file_path in processed_files:
                    # Use relative path within the zip file
                    arcname = os.path.relpath(file_path, OUTPUT_DIR)
                    zipf.write(file_path, arcname=arcname)
            zip_buffer.seek(0) # Rewind buffer to start

        # Create download button
        st.download_button(
            label=f"📦 Download All ({processed_count}) Branded Images as ZIP",
            data=zip_buffer,
            file_name="branded_images.zip",
            mime="application/zip",
            key="download_zip_button" # Add key for potential state use
        )
    else:
        st.warning("No files were successfully processed to include in the ZIP.")

# --- Catch-all for unexpected errors in the main try block ---
except Exception as e:
    st.error("An unexpected error occurred during the main processing workflow:")
    st.error(e)
    st.error(traceback.format_exc()) # Provide detailed traceback for debugging
