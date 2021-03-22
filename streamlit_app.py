import streamlit as st
from PIL import Image, ImageDraw
import numpy as np
import io
from typing import Tuple

DEMO_IMAGE = "test-images/smart_meter.jpg"
RED = (255, 0, 0)  # For objects within the ROI

DEFAULT_ROI_Y_MIN = 0.0
DEFAULT_ROI_Y_MAX = 1.0
DEFAULT_ROI_X_MIN = 0.0
DEFAULT_ROI_X_MAX = 1.0

st.sidebar.title("ROI")
ROI_X_MIN = st.sidebar.slider("x_min", 0.0, 1.0, DEFAULT_ROI_X_MIN)
ROI_Y_MIN = st.sidebar.slider("y_min", 0.0, 1.0, DEFAULT_ROI_Y_MIN)
ROI_X_MAX = st.sidebar.slider("x_max", 0.0, 1.0, DEFAULT_ROI_X_MAX)
ROI_Y_MAX = st.sidebar.slider("y_max", 0.0, 1.0, DEFAULT_ROI_Y_MAX)

ROI_TUPLE = (
    ROI_Y_MIN,
    ROI_X_MIN,
    ROI_Y_MAX,
    ROI_X_MAX,
)

def draw_box(
    draw: ImageDraw,
    box: Tuple[float, float, float, float],
    img_width: int,
    img_height: int,
    text: str = "",
    color: Tuple[int, int, int] = (255, 255, 0),
) -> None:
    """
    Draw a bounding box on and image.
    The bounding box is defined by the tuple (y_min, x_min, y_max, x_max)
    where the coordinates are floats in the range [0.0, 1.0] and
    relative to the width and height of the image.
    For example, if an image is 100 x 200 pixels (height x width) and the bounding
    box is `(0.1, 0.2, 0.5, 0.9)`, the upper-left and bottom-right coordinates of
    the bounding box will be `(40, 10)` to `(180, 50)` (in (x,y) coordinates).
    """

    line_width = 3
    font_height = 8
    y_min, x_min, y_max, x_max = box
    (left, right, top, bottom) = (
        x_min * img_width,
        x_max * img_width,
        y_min * img_height,
        y_max * img_height,
    )
    draw.line(
        [(left, top), (left, bottom), (right, bottom), (right, top), (left, top)],
        width=line_width,
        fill=color,
    )
    if text:
        draw.text(
            (left + line_width, abs(top - line_width - font_height)), text, fill=color
        )

st.title("Integration config helper app")
img_file_buffer = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])

if img_file_buffer is not None:
    pil_image = Image.open(img_file_buffer)

else: 
    pil_image = Image.open(DEMO_IMAGE)

draw = ImageDraw.Draw(pil_image)

draw_box(
    draw,
    ROI_TUPLE,
    pil_image.width,
    pil_image.height,
    color=RED,
)

st.text('Top left is (x=0, y=0), bottom left is (x=0, y=1), bottom right is (x=1, y=1)')

st.image(
    pil_image, use_column_width=True,
)