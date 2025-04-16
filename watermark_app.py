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
DEFAULT_BRAND_NAME = "12Taste "

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

st.title("🖼️ Add Your Logo and Brand Watermark to Product Images")

# Option to explicitly clean folders (might be safer than always cleaning)
# if st.sidebar.button("⚠️ Clear Working Folders (Deletes Previous Runs)"):
#     with st.spinner("Clearing working folders..."):
#         for folder in [PRODUCTS_DIR, OUTPUT_DIR]:
#             if os.path.exists(folder):
#                 try:
#                     shutil.rmtree(folder)
#                 except OSError as e:
#                     st.error(f"Error removing folder {folder}: {e}")
#                     st.stop()
#         # Recreate folders after clearing
#         for folder in [PRODUCTS_DIR, OUTPUT_DIR]:
#             try:
#                 os.makedirs(folder, exist_ok=True) # exist_ok=True is safer
#             except OSError as e:
#                 st.error(f"Error creating folder {folder}: {e}")
#                 st.stop()
#         st.sidebar.success("Folders cleared and recreated.")
# else:
# Ensure folders exist without clearing (default behavior)
for folder in [PRODUCTS_DIR, OUTPUT_DIR]:
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError as e:
        st.error(f"Error ensuring folder exists {folder}: {e}")
        st.stop()


# --- File Uploads ---
logo_file = st.file_uploader("1. Upload your logo (PNG with transparency preferred)", type=["png"])
product_zip_file = st.file_uploader("2. Upload a ZIP containing product images (PNG/JPG/JPEG)", type=["zip"])

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
    opacity = st.sidebar.slider("Watermark Text Opacity", 0.0, 1.0, DEFAULT_OPACITY, 0.05)
    watermark_color_hex = st.sidebar.color_picker("Watermark Text Color", DEFAULT_WATERMARK_COLOR)
    position = st.sidebar.selectbox("Watermark Text Position", ["Top", "Middle", "Bottom"], index=1) # Default Middle
    logo_scale = st.sidebar.slider("Logo Size (relative to image width)", 0.05, 0.5, DEFAULT_LOGO_SCALE, 0.01)
    padding = st.sidebar.slider("Logo/Text Padding (pixels from edge)", 5, 100, DEFAULT_PADDING, 5)
    font_size = st.sidebar.slider("Watermark Font Size", 10, 150, DEFAULT_FONT_SIZE, 5) # Increased max size
    brand_name = st.sidebar.text_input("Watermark Text", DEFAULT_BRAND_NAME)
    horizontal_spacing = st.sidebar.slider("Horizontal Text Spacing", 10, 200, 50, 10)


    # --- Font Loading ---
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
        st.sidebar.info(f"Using font: {FONT_PATH}")
    except IOError:
        st.sidebar.warning(f"Font '{FONT_PATH}' not found. Trying system 'arial.ttf'.")
        try:
            # Attempt common system font paths
            font = ImageFont.truetype("arial.ttf", font_size)
            st.sidebar.info("Using system font: arial.ttf")
        except IOError:
            st.sidebar.error("System 'arial.ttf' not found. Using default built-in font (basic).")
            font = ImageFont.load_default() # Absolute fallback (might not respect size well)

    # --- Image Processing ---
    processed_files = []
    # Filter for valid image extensions and ignore macOS metadata files
    files_to_process = [
        f for f in os.listdir(PRODUCTS_DIR)
        if f.lower().endswith((".png", ".jpg", ".jpeg")) and not f.startswith('__MACOSX') and not f.startswith('.')
    ]
    # Also handle cases where images might be in a subdirectory within the zip
    for root, _, files in os.walk(PRODUCTS_DIR):
        for f in files:
             if f.lower().endswith((".png", ".jpg", ".jpeg")) and not f.startswith('.') and os.path.join(root, f) not in files_to_process:
                 # Add the relative path to the list if it's an image
                 relative_path = os.path.relpath(os.path.join(root, f), PRODUCTS_DIR)
                 if relative_path not in files_to_process: # Avoid duplicates if already found at top level
                     files_to_process.append(relative_path)


    if not files_to_process:
        st.warning("⚠️ No valid image files (PNG, JPG, JPEG) found in the extracted ZIP structure.")
        st.stop()

    st.write(f"Found {len(files_to_process)} images to process.")
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


    for i, relative_fname in enumerate(files_to_process):
        product_path = os.path.join(PRODUCTS_DIR, relative_fname)
        # Create the same subdirectory structure in the output if needed
        output_sub_dir = os.path.dirname(os.path.join(OUTPUT_DIR, relative_fname))
        if output_sub_dir != OUTPUT_DIR:
             os.makedirs(output_sub_dir, exist_ok=True)

        base_fname = os.path.basename(relative_fname) # Get filename for messages
        status_text.text(f"Processing: {base_fname} ({i + 1}/{len(files_to_process)})")

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
                logo = logo.resize((target_width, target_height), Resampling.LANCZOS)
            except ImportError:
                 # Fallback for older Pillow versions
                 logo = logo.resize((target_width, target_height), Image.LANCZOS)


            # Calculate logo position (bottom-right with padding)
            x_logo = product.width - logo.width - padding
            y_logo = product.height - logo.height - padding
            # Paste logo onto the watermark layer using its own alpha channel as mask
            watermark_layer.paste(logo, (x_logo, y_logo), logo)

            # --- Repeating Text Watermark ---
            cleaned_brand_name = brand_name.strip()
            if cleaned_brand_name: # Only add text if brand name is not empty
                try:
                    # --- Use textbbox to get text dimensions ---
                    # Calculate bounding box starting at (0,0) to get width/height
                    # bbox = (left, top, right, bottom)
                    text_bbox = draw.textbbox((0, 0), cleaned_brand_name, font=font)
                    text_width = text_bbox[2] - text_bbox[0]  # right - left
                    text_height = text_bbox[3] - text_bbox[1] # bottom - top

                    # Handle cases where font/text might result in zero dimensions
                    if text_width <= 0 or text_height <= 0:
                        st.warning(f"⚠️ Calculated zero dimensions for text '{cleaned_brand_name}' with selected font/size. Skipping text watermark for {base_fname}.")
                    else:
                        # Calculate vertical position based on selection
                        if position == "Top":
                            # Position the top of the text bbox at padding distance
                            text_y = padding
                        elif position == "Middle":
                            # Center the text block vertically
                            text_y = (product.height - text_height) // 2
                        else: # Bottom
                            # Position the bottom of the text bbox at padding distance from bottom
                            text_y = product.height - text_height - padding

                        # Repeat the brand name horizontally
                        step = text_width + horizontal_spacing
                        if step <= 0 : step = 1 # Prevent infinite loop if spacing is negative/zero

                        # Start slightly left to make the pattern seem continuous
                        start_x = -(text_width % step if step > 0 else 0)

                        for x_text in range(start_x, product.width, step):
                            # Draw text at calculated (x, y) position using specified color and font
                            draw.text((x_text, text_y), cleaned_brand_name, font=font, fill=text_color)

                except AttributeError:
                    # Should not happen with modern Pillow, but good to keep
                    st.error("❌ Pillow version might be too old and lacks textbbox. Please update Pillow (`pip install --upgrade Pillow`). Skipping text watermark.")
                    error_count += 1
                except Exception as text_err:
                    st.error(f"❌ Error calculating text dimensions or drawing text for {base_fname}: {text_err}. Skipping text watermark.")
                    # st.error(traceback.format_exc()) # Uncomment for more debug info
                    error_count += 1


            # Composite the watermark layer onto the original product image
            final_image = Image.alpha_composite(product, watermark_layer)

            # Save the final image
            # Always save as PNG to preserve potential transparency in logo/watermark
            # Use the relative path structure for output
            out_fname_base = os.path.splitext(base_fname)[0]
            out_fname = f"{out_fname_base}_branded.png"
            out_path = os.path.join(output_sub_dir, out_fname)

            # Convert back to RGB if the original was likely JPG/JPEG for potentially smaller size,
            # but this LOSES transparency if the original had none. PNG is safer.
            # if product_path.lower().endswith((".jpg", ".jpeg")):
            #     final_image = final_image.convert("RGB")
            #     final_image.save(out_path, "JPEG", quality=95) # Or save as JPEG
            # else:
            #     final_image.save(out_path, "PNG")
            final_image.save(out_path, "PNG") # Sticking to PNG for consistency

            processed_files.append(out_path)
            processed_count += 1

        except Exception as img_err:
            st.error(f"❌ Failed to process image `{base_fname}`: {img_err}")
            # st.error(traceback.format_exc()) # Uncomment for detailed traceback
            error_count += 1

        # Update progress bar
        progress_bar.progress((i + 1) / len(files_to_process))

    status_text.text(f"Processing complete. {processed_count} images processed, {error_count} errors.")
    progress_bar.empty() # Clear progress bar

    if not processed_files:
        st.error("🚫 No images were processed successfully.")
        st.stop()

    # --- Preview ---
    st.subheader("🖼️ Preview (First 5 Images)")
    preview_count = 0
    for path in processed_files:
        if preview_count < 5:
            try:
                st.image(path, caption=os.path.basename(path), use_column_width=True)
                preview_count += 1
            except Exception as e:
                st.error(f"Error displaying preview for {os.path.basename(path)}: {e}")
        else:
            break


    # --- Zip and Download ---
    st.subheader("⬇️ Download Results")
    if processed_files:
        with st.spinner("Zipping processed images..."):
            zip_buffer = BytesIO()
            # Use ZIP_DEFLATED for compression
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file_path in processed_files:
                    # Add file to zip using its base name (or relative path from OUTPUT_DIR)
                    arcname = os.path.relpath(file_path, OUTPUT_DIR)
                    zipf.write(file_path, arcname=arcname)
            zip_buffer.seek(0) # Rewind buffer to the beginning

        st.download_button(
            label=f"📦 Download All ({processed_count}) Branded Images as ZIP",
            data=zip_buffer,
            file_name="branded_images.zip",
            mime="application/zip",
            key="download_zip_button" # Added key for potential state management
        )
    else:
        st.warning("No files were successfully processed to include in the ZIP.")

except Exception as e:
    st.error("An unexpected error occurred during the main processing workflow:")
    st.error(e)
    st.error(traceback.format_exc()) # Provide detailed traceback for debugging
