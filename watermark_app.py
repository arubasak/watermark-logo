import streamlit as st
import os
import shutil
import zipfile
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import hashlib

# 🔐 Password protection using SHA256
def check_password():
    def password_entered():
        entered_hash = hashlib.sha256(st.session_state["password"].encode()).hexdigest()
        if entered_hash == st.secrets["APP_PASSWORD_HASH"]:
            st.session_state["authenticated"] = True
        else:
            st.session_state["authenticated"] = False
            st.error("❌ Incorrect password")

    if "authenticated" not in st.session_state:
        st.text_input("Enter password:", type="password", on_change=password_entered, key="password")
        st.stop()
    elif not st.session_state["authenticated"]:
        st.text_input("Enter password:", type="password", on_change=password_entered, key="password")
        st.stop()

check_password()

# 🧹 Clean folders
products_dir = "products"
output_dir = "branded_products"
for folder in [products_dir, output_dir]:
    if os.path.exists(folder):
        shutil.rmtree(folder)
    os.makedirs(folder)

st.title("🖼️ Add Your Logo and Brand Watermark to Product Images")

# 📤 Upload logo file
logo_file = st.file_uploader("Upload your logo (PNG with transparency preferred)", type=["png"])
if not logo_file:
    st.stop()

# 📤 Upload ZIP of product images
product_zip_file = st.file_uploader("Upload a ZIP containing product images (PNG/JPG/JPEG)", type=["zip"])
if not product_zip_file:
    st.stop()

# Extract uploaded ZIP
with zipfile.ZipFile(product_zip_file, "r") as zip_ref:
    zip_ref.extractall(products_dir)
st.success("✅ Product images extracted.")

# ⚙️ Config - Sliders and Selectors for customization
logo_opacity = st.slider("Watermark Opacity", 0.0, 1.0, 0.5)  # Slider to control opacity
watermark_color = st.color_picker("Watermark Color", "#ffffff")  # Color picker for text color

# Select watermark position (Top, Middle, or Bottom)
position = st.selectbox("Watermark Position", ["Top", "Middle", "Bottom"])

logo_scale = 0.15
padding = 30
add_shadow = True

# Load logo
original_logo = Image.open(logo_file).convert("RGBA")

# Load font (adjust the path to a ttf file if needed)
try:
    font = ImageFont.truetype("arial.ttf", 50)  # Try loading a system font
except IOError:
    font = ImageFont.load_default()  # Fall back to default if not available

# Process images
processed_files = []
brand_name = "12Taste "  # The brand name to be used in the watermark

for fname in os.listdir(products_dir):
    if not fname.lower().endswith((".png", ".jpg", ".jpeg")):
        continue

    product_path = os.path.join(products_dir, fname)
    product = Image.open(product_path).convert("RGBA")
    final = product.copy()

    # Resize logo
    logo = original_logo.copy()
    target_width = int(product.width * logo_scale)
    aspect_ratio = logo.height / logo.width
    logo = logo.resize((target_width, int(target_width * aspect_ratio)), Image.LANCZOS)

    # Set full opacity
    logo_alpha = logo.split()[3].point(lambda p: int(p * 1.0))
    logo.putalpha(logo_alpha)

    # Optional white shadow
    if add_shadow:
        shadow = Image.new("RGBA", logo.size, (255, 255, 255, 180))
        shadow_offset = (2, 2)
        shadow_position = (
            product.width - logo.width - padding + shadow_offset[0],
            product.height - logo.height - padding + shadow_offset[1],
        )
        final.paste(shadow, shadow_position, shadow)

    # Paste logo
    x = product.width - logo.width - padding
    y = product.height - logo.height - padding
    final.paste(logo, (x, y), logo)

    # Add repeating watermark text
    draw = ImageDraw.Draw(final)
    text_width, text_height = draw.textsize(brand_name, font=font)
    
    # Position calculation
    if position == "Top":
        text_y = 30
    elif position == "Middle":
        text_y = product.height // 2 - text_height // 2
    elif position == "Bottom":
        text_y = product.height - text_height - 30
    
    # Convert hex color to RGB
    text_color = ImageColor.getrgb(watermark_color)

    # Repeat the brand name horizontally
    for i in range(0, product.width, text_width):
        draw.text((i, text_y), brand_name, font=font, fill=text_color)

    # Save result
    out_path = os.path.join(output_dir, os.path.splitext(fname)[0] + ".png")
    final.save(out_path)
    processed_files.append(out_path)

# Preview processed images
st.subheader("🖼️ Preview")
for path in processed_files[:5]:  # limit preview to 5 images
    st.image(path, caption=os.path.basename(path))

# Zip output images
zip_buffer = BytesIO()
with zipfile.ZipFile(zip_buffer, "w") as zipf:
    for file in processed_files:
        zipf.write(file, arcname=os.path.basename(file))
zip_buffer.seek(0)

# Provide download button
st.download_button("📦 Download All Branded Images as ZIP", zip_buffer, file_name="branded_images.zip", mime="application/zip")
