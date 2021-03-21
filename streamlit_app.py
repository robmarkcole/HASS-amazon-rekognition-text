import streamlit as st
from PIL import Image
import numpy as np
import io

DEMO_IMAGE = "test-images/smart_meter.jpg"

def pil_image_to_byte_array(image):
    imgByteArr = io.BytesIO()
    image.save(imgByteArr, "PNG")
    return imgByteArr.getvalue()

st.title("Integration config helper app")
img_file_buffer = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])

if img_file_buffer is not None:
    image_bytes = pil_image_to_byte_array(Image.open(img_file_buffer))
    image_array = np.array(Image.open(img_file_buffer))

else:
    image_bytes = open(DEMO_IMAGE, "rb").read()
    image_array = np.array(Image.open(DEMO_IMAGE))

st.image(
    image_array, use_column_width=True,
)