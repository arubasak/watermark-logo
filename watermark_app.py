import streamlit as st
import os
import shutil
import zipfile
from PIL import Image
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

st.title("🖼️ Add Your Logo to Product Images")

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

# ⚙️ Config
logo_opacity = 1.0
logo_scale = 0.15
padding = 30
add_shadow = True

# Load logo
original_logo = Image.open(logo_file).convert("RGBA")

# Process images
processed_files = []
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
    logo_alpha = logo.split()[3].point(lambda p: int(p * logo_opacity))
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
