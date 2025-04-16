import streamlit as st
import os
import shutil
import zipfile
from PIL import Image, ImageDraw, ImageFont, ImageColor
from io import BytesIO
import hashlib

# --- Constants ---
PRODUCTS_DIR = "products"
OUTPUT_DIR = "branded_products"
FONT_PATH = "arial.ttf" # Consider making this configurable or ensuring font exists
DEFAULT_FONT_SIZE = 50
DEFAULT_WATERMARK_COLOR = "#ffffff"
DEFAULT_OPACITY = 0.5
DEFAULT_LOGO_SCALE = 0.15
DEFAULT_PADDING = 30
DEFAULT_BRAND_NAME = "12Taste "

# 🔐 Password protection using SHA256
def check_password():
    # Use st.query_params for potential future password passing (though secrets is better)
    # st.secrets is the preferred way for sensitive data like passwords
    if "APP_PASSWORD_HASH" not in st.secrets:
        st.error("Password configuration missing in secrets.")
        st.stop()
        return False # Explicitly return False

    APP_PASSWORD_HASH = st.secrets["APP_PASSWORD_HASH"]

    def password_entered():
        entered_hash = hashlib.sha256(st.session_state["password"].encode()).hexdigest()
        if entered_hash == APP_PASSWORD_HASH:
            st.session_state["authenticated"] = True
            # Clear the password input after successful login (optional)
            # st.session_state["password"] = ""
        else:
            st.session_state["authenticated"] = False
            st.error("❌ Incorrect password")

    if st.session_state.get("authenticated", False):
         return True # Already authenticated

    # Show password input only if not authenticated
    st.text_input(
        "Enter password:",
        type="password",
        on_change=password_entered,
        key="password"
        )
    # Add a visual separator or instruction
    st.warning("Please enter the password to proceed.")
    st.stop() # Stop execution until password is correct
    return False # Explicitly return False, though st.stop() prevents reaching here

# --- Main App Logic ---
if not check_password():
    # check_password() already called st.stop(), but this adds clarity
    st.stop()

st.title("🖼️ Add Your Logo and Brand Watermark to Product Images")

# 🧹 Clean folders (Only if needed, maybe make optional?)
# Consider if cleaning every run is desired, might delete ongoing work
# if st.button("Clear Working Folders"): # Make it explicit
with st.spinner("Preparing folders..."):
    for folder in [PRODUCTS_DIR, OUTPUT_DIR]:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
            except OSError as e:
                st.error(f"Error removing folder {folder}: {e}")
                st.stop()
        try:
            os.makedirs(folder)
        except OSError as e:
            st.error(f"Error creating folder {folder}: {e}")
            st.stop()
    # st.success("Folders cleaned and recreated.") # Optional confirmation


# --- File Uploads ---
logo_file = st.file_uploader("1. Upload your logo (PNG with transparency preferred)", type=["png"])
product_zip_file = st.file_uploader("2. Upload a ZIP containing product images (PNG/JPG/JPEG)", type=["zip"])

# --- Guard Clauses ---
if not logo_file:
    st.info("Please upload a logo file to continue.")
    st.stop()

if not product_zip_file:
    st.info("Please upload a ZIP file with product images to continue.")
    st.stop()

# --- Process Files (only if both uploads are present) ---
try:
    # Load logo (do this once after upload)
    original_logo = Image.open(logo_file).convert("RGBA")

    # Extract uploaded ZIP
    st.write(f"Processing uploaded file: {product_zip_file.name}")
    with st.spinner("Extracting product images..."):
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
            st.stop()

    # --- Configuration ---
    st.sidebar.header("⚙️ Customization")
    logo_opacity = st.sidebar.slider("Watermark Text Opacity", 0.0, 1.0, DEFAULT_OPACITY, 0.05)
    watermark_color_hex = st.sidebar.color_picker("Watermark Text Color", DEFAULT_WATERMARK_COLOR)
    position = st.sidebar.selectbox("Watermark Text Position", ["Top", "Middle", "Bottom"], index=1) # Default Middle
    logo_scale = st.sidebar.slider("Logo Size (relative to image width)", 0.05, 0.5, DEFAULT_LOGO_SCALE, 0.01)
    padding = st.sidebar.slider("Logo Padding (pixels from edge)", 5, 100, DEFAULT_PADDING, 5)
    font_size = st.sidebar.slider("Watermark Font Size", 10, 100, DEFAULT_FONT_SIZE, 5)
    brand_name = st.sidebar.text_input("Watermark Text", DEFAULT_BRAND_NAME)
    # add_shadow = st.sidebar.checkbox("Add white shadow to logo", True) # Removed as it wasn't used effectively

    # --- Font Loading ---
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except IOError:
        st.warning(f"Font '{FONT_PATH}' not found. Using default font.")
        try:
            # Attempt to load a known system font as a better fallback
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            font = ImageFont.load_default() # Absolute fallback

    # --- Image Processing ---
    processed_files = []
    files_to_process = [f for f in os.listdir(PRODUCTS_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg"))]

    if not files_to_process:
        st.warning("No valid image files (PNG, JPG, JPEG) found in the extracted ZIP.")
        st.stop()

    st.write(f"Found {len(files_to_process)} images to process.")
    progress_bar = st.progress(0)
    processed_count = 0

    # Prepare watermark color with opacity
    try:
        base_text_color = ImageColor.getrgb(watermark_color_hex)
        text_color = base_text_color + (int(255 * logo_opacity),) # Add alpha channel
    except ValueError:
        st.error(f"Invalid color format: {watermark_color_hex}. Using default white.")
        base_text_color = ImageColor.getrgb(DEFAULT_WATERMARK_COLOR)
        text_color = base_text_color + (int(255 * logo_opacity),)

    for i, fname in enumerate(files_to_process):
        product_path = os.path.join(PRODUCTS_DIR, fname)
        try:
            product = Image.open(product_path).convert("RGBA")
            # Create a transparent layer for watermarking
            watermark_layer = Image.new("RGBA", product.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(watermark_layer)

            # --- Logo Application ---
            logo = original_logo.copy()
            target_width = int(product.width * logo_scale)
            if target_width == 0: # Prevent zero-size logo
                target_width = 1
            aspect_ratio = logo.height / logo.width
            target_height = int(target_width * aspect_ratio)
            if target_height == 0:
                target_height = 1
            logo = logo.resize((target_width, target_height), Image.LANCZOS)

            # Paste logo onto the watermark layer (bottom-right)
            x_logo = product.width - logo.width - padding
            y_logo = product.height - logo.height - padding
            watermark_layer.paste(logo, (x_logo, y_logo), logo) # Use logo's alpha mask

            # --- Repeating Text Watermark ---
            if brand_name.strip(): # Only add text if brand name is not empty
                text_width, text_height = draw.textsize(brand_name, font=font)

                if position == "Top":
                    text_y = padding # Use padding for consistency
                elif position == "Middle":
                    text_y = product.height // 2 - text_height // 2
                else: # Bottom
                    text_y = product.height - text_height - padding # Use padding

                # Repeat the brand name horizontally
                for x_text in range(-text_width, product.width + text_width, text_width + 50): # Add spacing
                     draw.text((x_text, text_y), brand_name, font=font, fill=text_color)

            # Composite the watermark layer onto the product image
            final = Image.alpha_composite(product, watermark_layer)

            # Save result (convert back to RGB if original was JPG to avoid PNG size increase)
            out_fname = os.path.splitext(fname)[0] + ".png" # Always save as PNG to preserve transparency
            out_path = os.path.join(OUTPUT_DIR, out_fname)
            final.save(out_path, "PNG")
            processed_files.append(out_path)
            processed_count += 1
            progress_bar.progress(processed_count / len(files_to_process))

        except Exception as e:
            st.error(f"Error processing image {fname}: {e}")

    progress_bar.empty() # Clear progress bar after completion

    if not processed_files:
        st.error("No images were processed successfully.")
        st.stop()

    # --- Preview ---
    st.subheader("🖼️ Preview (First 5 Images)")
    for path in processed_files[:5]:
        try:
            st.image(path, caption=os.path.basename(path))
        except Exception as e:
            st.error(f"Error displaying preview for {os.path.basename(path)}: {e}")


    # --- Zip and Download ---
    st.subheader("⬇️ Download Results")
    with st.spinner("Zipping processed images..."):
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in processed_files:
                zipf.write(file_path, arcname=os.path.basename(file_path))
        zip_buffer.seek(0)

    st.download_button(
        label="📦 Download All Branded Images as ZIP",
        data=zip_buffer,
        file_name="branded_images.zip",
        mime="application/zip"
    )

except Exception as e:
    st.error(f"An unexpected error occurred: {e}")
    # Add more detailed traceback if needed for debugging
    # import traceback
    # st.error(traceback.format_exc())
