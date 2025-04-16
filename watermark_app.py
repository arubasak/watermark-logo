# -*- coding: utf-8 -*- # Add this line for better encoding support
import streamlit as st
import os
import shutil
import zipfile
from PIL import Image, ImageDraw, ImageFont, ImageColor
from io import BytesIO
import hashlib
import traceback # Added for potentially more detailed error logging

# --- Constants ---
PRODUCTS_DIR = "products"
OUTPUT_DIR = "branded_products"
# Ensure 'arial.ttf' exists or use a guaranteed system font path if possible.
# On Linux/macOS, you might find fonts in standard locations.
# On Windows: "C:/Windows/Fonts/arial.ttf"
# For cross-platform, consider bundling the font or using a library that finds fonts.
FONT_PATH = "arial.ttf"
DEFAULT_FONT_SIZE = 50
DEFAULT_WATERMARK_COLOR = "#ffffff"
DEFAULT_OPACITY = 0.5
DEFAULT_LOGO_SCALE = 0.15
DEFAULT_PADDING = 30
DEFAULT_BRAND_NAME = "JhumJhum  "

# --- Password Protection ---
def check_password():
    """Checks if the user is authenticated using secrets."""
    if "APP_PASSWORD_HASH" not in st.secrets:
        st.error("Password configuration missing in st.secrets.")
        st.warning("Please add `APP_PASSWORD_HASH = 'your_sha256_hash'` to your Streamlit secrets.")
        # Generate a hash example:
        # import hashlib
        # print(hashlib.sha256("your_password".encode()).hexdigest())
        st.stop()
        return False

    APP_PASSWORD_HASH = st.secrets["APP_PASSWORD_HASH"]

    def password_entered():
        """Callback function when password input changes."""
        entered_hash = hashlib.sha256(st.session_state["password"].encode()).hexdigest()
        if entered_hash == APP_PASSWORD_HASH:
            st.session_state["authenticated"] = True
            # Clear the password input field if desired (uncomment)
            # st.session_state["password"] = ""
        else:
            st.session_state["authenticated"] = False
            st.error("❌ Incorrect password")

    # Initialize session state if it doesn't exist
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    # If already authenticated, return True
    if st.session_state.get("authenticated", False):
        return True

    # Show password input if not authenticated
    st.text_input(
        "Enter password:",
        type="password",
        on_change=password_entered,
        key="password"
    )
    if not st.session_state.get("authenticated", False):
         st.warning("Please enter the correct password to proceed.")
         st.stop() # Stop execution until password is correct

    # This part should technically not be reached if authentication fails due to st.stop()
    return st.session_state.get("authenticated", False)

# --- Main App Logic ---
# Authenticate first
if not check_password():
    st.stop() # Stop if authentication fails

st.set_page_config(layout="wide") # Optional: Use wider layout

st.title("🖼️ Add Your Logo and Brand Watermark to Product Images")

# Ensure folders exist without clearing (default behavior)
for folder in [PRODUCTS_DIR, OUTPUT_DIR]:
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError as e:
        st.error(f"Error ensuring folder exists {folder}: {e}")
        st.stop()


# --- File Uploads ---
col1, col2 = st.columns(2)
with col1:
    logo_file = st.file_uploader("1. Upload your logo (PNG with transparency preferred)", type=["png"], key="logo_uploader")
with col2:
    product_zip_file = st.file_uploader("2. Upload a ZIP containing product images (PNG/JPG/JPEG)", type=["zip"], key="zip_uploader")

# --- Guard Clauses ---
if not logo_file:
    st.info("💡 Please upload a logo file to continue.")
    st.stop()

if not product_zip_file:
    st.info("💡 Please upload a ZIP file with product images to continue.")
    st.stop()

# --- Process Files (only if both uploads are present) ---
try:
    # Load logo (do this once after upload)
    original_logo = Image.open(logo_file).convert("RGBA")

    # Extract uploaded ZIP
    st.write(f"Processing uploaded file: `{product_zip_file.name}`")
    with st.spinner("Extracting product images..."):
        # Clear the products directory before extraction to avoid mixing runs
        if os.path.exists(PRODUCTS_DIR):
            try:
                shutil.rmtree(PRODUCTS_DIR)
                os.makedirs(PRODUCTS_DIR) # Recreate it immediately
            except OSError as e:
                st.error(f"Error clearing previous products in {PRODUCTS_DIR}: {e}")
                st.stop()

        try:
            # Read the file content into BytesIO
            zip_file_bytes = BytesIO(product_zip_file.read())
            with zipfile.ZipFile(zip_file_bytes, "r") as zip_ref:
                zip_ref.extractall(PRODUCTS_DIR)
            st.success("✅ Product images extracted.")
        except zipfile.BadZipFile:
            st.error("❌ Invalid ZIP file. Please upload a valid ZIP archive.")
            st.stop()
        except Exception as e:
            st.error(f"An error occurred during ZIP extraction: {e}")
            st.error(traceback.format_exc()) # Show detailed error
            st.stop()

    # --- Configuration ---
    st.sidebar.header("⚙️ Customization")
    opacity = st.sidebar.slider("Watermark Text Opacity", 0.0, 1.0, DEFAULT_OPACITY, 0.05, key="opacity_slider")
    watermark_color_hex = st.sidebar.color_picker("Watermark Text Color", DEFAULT_WATERMARK_COLOR, key="color_picker")
    position = st.sidebar.selectbox("Watermark Text Position", ["Top", "Middle", "Bottom"], index=1, key="position_select") # Default Middle
    logo_scale = st.sidebar.slider("Logo Size (relative to image width)", 0.05, 0.5, DEFAULT_LOGO_SCALE, 0.01, key="logo_scale_slider")
    padding = st.sidebar.slider("Logo/Text Padding (pixels from edge)", 5, 100, DEFAULT_PADDING, 5, key="padding_slider")
    font_size = st.sidebar.slider("Watermark Font Size", 10, 150, DEFAULT_FONT_SIZE, 5, key="fontsize_slider") # Increased max size
    brand_name = st.sidebar.text_input("Watermark Text", DEFAULT_BRAND_NAME, key="brand_text_input")
    horizontal_spacing = st.sidebar.slider("Horizontal Text Spacing", 10, 200, 50, 10, key="hspacing_slider")


    # --- Font Loading ---
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
        # st.sidebar.info(f"Using font: {FONT_PATH}") # Can be noisy, optional
    except IOError:
        st.sidebar.warning(f"Font '{FONT_PATH}' not found. Trying system 'arial.ttf'.")
        try:
            # Attempt common system font paths
            font = ImageFont.truetype("arial.ttf", font_size)
            # st.sidebar.info("Using system font: arial.ttf") # Optional
        except IOError:
            st.sidebar.error("System 'arial.ttf' not found. Using default built-in font (basic).")
            font = ImageFont.load_default() # Absolute fallback (might not respect size well)

    # --- Image Processing ---
    processed_files = []
    files_to_process_paths = [] # Store full paths for processing
    # Find all image files recursively
    for root, _, files in os.walk(PRODUCTS_DIR):
        for f in files:
             # Filter for valid image extensions and ignore macOS metadata/hidden files
             if f.lower().endswith((".png", ".jpg", ".jpeg")) and not f.startswith('.') and '__MACOSX' not in root:
                 full_path = os.path.join(root, f)
                 files_to_process_paths.append(full_path)


    if not files_to_process_paths:
        st.warning("⚠️ No valid image files (PNG, JPG, JPEG) found in the extracted ZIP structure.")
        st.stop()

    st.write(f"Found {len(files_to_process_paths)} images to process.")
    progress_bar = st.progress(0)
    status_text = st.empty() # Placeholder for status updates
    processed_count = 0
    error_count = 0

    # Prepare watermark color with opacity
    try:
        base_text_color = ImageColor.getrgb(watermark_color_hex)
        # Ensure opacity is applied correctly to the alpha channel (0-255)
        text_color = base_text_color + (int(255 * opacity),)
    except ValueError:
        st.error(f"Invalid color format: {watermark_color_hex}. Using default white.")
        base_text_color = ImageColor.getrgb(DEFAULT_WATERMARK_COLOR)
        text_color = base_text_color + (int(255 * opacity),)

    # Clear the output directory before processing
    if os.path.exists(OUTPUT_DIR):
        try:
            shutil.rmtree(OUTPUT_DIR)
            os.makedirs(OUTPUT_DIR) # Recreate it
        except OSError as e:
            st.error(f"Error clearing output directory {OUTPUT_DIR}: {e}")
            st.stop()


    for i, product_path in enumerate(files_to_process_paths):
        relative_path = os.path.relpath(product_path, PRODUCTS_DIR)
        base_fname = os.path.basename(product_path) # Get filename for messages
        status_text.text(f"Processing: {base_fname} ({i + 1}/{len(files_to_process_paths)})")

        # Create the same subdirectory structure in the output if needed
        output_sub_dir = os.path.dirname(os.path.join(OUTPUT_DIR, relative_path))
        if not os.path.exists(output_sub_dir):
             os.makedirs(output_sub_dir, exist_ok=True)

        try:
            product = Image.open(product_path).convert("RGBA")
            # Create a transparent layer for watermarking of the same size
            watermark_layer = Image.new("RGBA", product.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(watermark_layer)

            # --- Logo Application ---
            logo = original_logo.copy()
            # Calculate target logo width based on product image width
            target_width = int(product.width * logo_scale)
            if target_width == 0: target_width = 1 # Ensure minimum width
            # Calculate target height preserving aspect ratio
            if logo.width > 0:
                aspect_ratio = logo.height / logo.width
            else:
                 aspect_ratio = 1 # Avoid division by zero if logo width is 0
            target_height = int(target_width * aspect_ratio)
            if target_height == 0: target_height = 1 # Ensure minimum height

            # Resize logo using high-quality resampling filter
            try:
                # Pillow >= 9.1.0 prefers Resampling enums
                from PIL.Image import Resampling
                logo_resized = logo.resize((target_width, target_height), Resampling.LANCZOS)
            except ImportError:
                 # Fallback for older Pillow versions
                 logo_resized = logo.resize((target_width, target_height), Image.LANCZOS)


            # Calculate logo position (bottom-right with padding)
            x_logo = product.width - logo_resized.width - padding
            y_logo = product.height - logo_resized.height - padding
            # Paste logo onto the watermark layer using its own alpha channel as mask
            watermark_layer.paste(logo_resized, (x_logo, y_logo), logo_resized) # Use resized logo mask

            # --- Repeating Text Watermark ---
            cleaned_brand_name = brand_name.strip()
            if cleaned_brand_name: # Only add text if brand name is not empty
                try:
                    # --- Use textbbox to get text dimensions ---
                    text_bbox = draw.textbbox((0, 0), cleaned_brand_name, font=font, anchor="lt") # Use anchor for consistency
                    text_width = text_bbox[2] - text_bbox[0]  # right - left
                    text_height = text_bbox[3] - text_bbox[1] # bottom - top

                    if text_width <= 0 or text_height <= 0:
                        st.warning(f"⚠️ Calculated zero dimensions for text '{cleaned_brand_name}' with selected font/size. Skipping text watermark for {base_fname}.")
                    else:
                        # Calculate vertical position based on selection
                        if position == "Top":
                            text_y = padding # Position top of text at padding
                        elif position == "Middle":
                            text_y = (product.height - text_height) // 2 # Center block
                        else: # Bottom
                            text_y = product.height - text_height - padding # Position top so bottom is at padding

                        step = text_width + horizontal_spacing
                        if step <= 0 : step = 1

                        start_x = -(text_width % step if step > 0 else 0)

                        for x_text in range(start_x, product.width, step):
                            draw.text((x_text, text_y), cleaned_brand_name, font=font, fill=text_color, anchor="lt") # Use anchor

                except AttributeError as e:
                    if 'textbbox' in str(e):
                         st.error("❌ Pillow version might be too old and lacks textbbox. Please update Pillow (`pip install --upgrade Pillow`). Skipping text watermark.")
                    elif 'anchor' in str(e):
                         st.warning("⚠️ Pillow version too old for text 'anchor'. Text positioning might be less precise. Consider upgrading Pillow.")
                         # Fallback drawing without anchor if needed (might require position adjustments)
                         draw.text((x_text, text_y), cleaned_brand_name, font=font, fill=text_color) # Simple draw
                    else:
                        st.error(f"❌ Text drawing error for {base_fname}: {e}. Skipping text watermark.")
                    error_count += 1
                except Exception as text_err:
                    st.error(f"❌ Error calculating/drawing text for {base_fname}: {text_err}. Skipping text watermark.")
                    error_count += 1


            # Composite the watermark layer onto the original product image
            final_image = Image.alpha_composite(product, watermark_layer)

            # Save the final image
            out_fname_base = os.path.splitext(base_fname)[0]
            out_fname = f"{out_fname_base}_branded.png"
            out_path = os.path.join(output_sub_dir, out_fname)

            final_image.save(out_path, "PNG")
            processed_files.append(out_path)
            processed_count += 1

        except Exception as img_err:
            st.error(f"❌ Failed to process image `{base_fname}`: {img_err}")
            st.error(traceback.format_exc()) # More details for image processing errors
            error_count += 1

        progress_bar.progress((i + 1) / len(files_to_process_paths))

    status_text.text(f"Processing complete. {processed_count} images processed, {error_count} errors.")
    progress_bar.empty() # Clear progress bar

    if not processed_files:
        st.error("🚫 No images were processed successfully.")
        st.stop()

    # --- Preview ---
    st.subheader("🖼️ Preview (First 5 Images)")
    preview_count = 0
    if processed_files:
        # Determine number of columns based on how many images we have, max 5
        num_columns = min(len(processed_files), 5)
        cols = st.columns(num_columns)
        for idx, path in enumerate(processed_files[:num_columns]):
             try:
                 with cols[idx]:
                    st.image(path, caption=os.path.basename(path), use_container_width=True) # Use container width here
                    preview_count += 1
             except Exception as e:
                 st.error(f"Error displaying preview for {os.path.basename(path)}: {e}")
    else:
        st.info("No images available for preview.")


    # --- Zip and Download ---
    st.subheader("⬇️ Download Results")
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
            data=zip_buffer,
            file_name="branded_images.zip",
            mime="application/zip",
            key="download_zip_button"
        )
    else:
        st.warning("No files were successfully processed to include in the ZIP.")

except Exception as e:
    st.error("An unexpected error occurred during the main processing workflow:")
    st.error(e)
    st.error(traceback.format_exc()) # Provide detailed traceback for debugging
