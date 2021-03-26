"""
Integration that will perform text detection.
"""
import io
import logging
import re
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util
import voluptuous as vol
from homeassistant.components.image_processing import (
    CONF_SOURCE,
    CONF_ENTITY_ID,
    CONF_NAME,
    DOMAIN,
    PLATFORM_SCHEMA,
    ImageProcessingEntity,
)
from homeassistant.core import split_entity_id
from homeassistant.util.pil import draw_box

from homeassistant.const import ATTR_ENTITY_ID, ATTR_NAME, CONF_UNIT_OF_MEASUREMENT

_LOGGER = logging.getLogger(__name__)

CONF_REGION = "region_name"
CONF_ACCESS_KEY_ID = "aws_access_key_id"
CONF_SECRET_ACCESS_KEY = "aws_secret_access_key"

DEFAULT_REGION = "us-east-1"
SUPPORTED_REGIONS = [
    "us-east-1",
    "us-east-2",
    "us-west-1",
    "us-west-2",
    "ca-central-1",
    "eu-west-1",
    "eu-central-1",
    "eu-west-2",
    "eu-west-3",
    "ap-southeast-1",
    "ap-southeast-2",
    "ap-northeast-2",
    "ap-northeast-1",
    "ap-south-1",
    "sa-east-1",
]

RED = (255, 0, 0)
DATETIME_FORMAT = "%Y-%m-%d_%H-%M-%S"

REQUIREMENTS = ["boto3"]
CONF_BOTO_RETRIES = "boto_retries"
DEFAULT_BOTO_RETRIES = 5

EROSION_MAP = {"low": 3, "medium": 5, "high": 9}

CONF_ERODE = "erode"
CONF_MAKE_BW = "make_bw"
CONF_NUMBERS_ONLY = "numbers_only"
CONF_ROI_Y_MIN = "roi_y_min"
CONF_ROI_X_MIN = "roi_x_min"
CONF_ROI_Y_MAX = "roi_y_max"
CONF_ROI_X_MAX = "roi_x_max"
CONF_SAVE_FILE_FOLDER = "save_file_folder"
CONF_SAVE_TIMESTAMPTED_FILE = "save_timestamped_file"

DEFAULT_ROI_Y_MIN = 0.0
DEFAULT_ROI_Y_MAX = 1.0
DEFAULT_ROI_X_MIN = 0.0
DEFAULT_ROI_X_MAX = 1.0


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_REGION, default=DEFAULT_REGION): vol.In(SUPPORTED_REGIONS),
        vol.Required(CONF_ACCESS_KEY_ID): cv.string,
        vol.Required(CONF_SECRET_ACCESS_KEY): cv.string,
        vol.Optional(CONF_ROI_Y_MIN, default=DEFAULT_ROI_Y_MIN): cv.small_float,
        vol.Optional(CONF_ROI_X_MIN, default=DEFAULT_ROI_X_MIN): cv.small_float,
        vol.Optional(CONF_ROI_Y_MAX, default=DEFAULT_ROI_Y_MAX): cv.small_float,
        vol.Optional(CONF_ROI_X_MAX, default=DEFAULT_ROI_X_MAX): cv.small_float,
        vol.Optional(CONF_NUMBERS_ONLY, default=False): cv.boolean,
        vol.Optional(CONF_MAKE_BW, default=False): cv.boolean,
        vol.Optional(CONF_ERODE, default=None): vol.In([None, "low", "medium", "high"]),
        vol.Optional(CONF_SAVE_FILE_FOLDER): cv.isdir,
        vol.Optional(CONF_SAVE_TIMESTAMPTED_FILE, default=False): cv.boolean,
        vol.Optional(CONF_UNIT_OF_MEASUREMENT, default=""): cv.string,
        vol.Optional(CONF_BOTO_RETRIES, default=DEFAULT_BOTO_RETRIES): vol.All(
            vol.Coerce(int), vol.Range(min=0)
        ),
    }
)


def get_valid_filename(name: str) -> str:
    return re.sub(r"(?u)[^-\w.]", "", str(name).strip().replace(" ", "_"))


def image_to_byte_array(image: Image) -> bytes:
    """Convert pil image to bytes"""
    imgByteArr = io.BytesIO()
    image.save(imgByteArr, format="png")
    imgByteArr = imgByteArr.getvalue()
    return imgByteArr


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up ObjectDetection."""

    import boto3

    _LOGGER.debug("boto_retries setting is {}".format(config[CONF_BOTO_RETRIES]))

    aws_config = {
        CONF_REGION: config[CONF_REGION],
        CONF_ACCESS_KEY_ID: config[CONF_ACCESS_KEY_ID],
        CONF_SECRET_ACCESS_KEY: config[CONF_SECRET_ACCESS_KEY],
    }

    retries = 0
    success = False
    while retries <= config[CONF_BOTO_RETRIES]:
        try:
            rekognition_client = boto3.client("rekognition", **aws_config)
            success = True
            break
        except KeyError:
            _LOGGER.info("boto3 client failed, retries={}".format(retries))
            retries += 1
            time.sleep(1)

    if not success:
        raise Exception(
            "Failed to create boto3 client. Maybe try increasing "
            "the boto_retries setting. Retry counter was {}".format(retries)
        )

    save_file_folder = config.get(CONF_SAVE_FILE_FOLDER)
    if save_file_folder:
        save_file_folder = Path(save_file_folder)

    entities = []
    for camera in config[CONF_SOURCE]:
        entities.append(
            ObjectDetection(
                rekognition_client=rekognition_client,
                region=config.get(CONF_REGION),
                roi_y_min=config.get(CONF_ROI_Y_MIN),
                roi_x_min=config.get(CONF_ROI_X_MIN),
                roi_y_max=config.get(CONF_ROI_Y_MAX),
                roi_x_max=config.get(CONF_ROI_X_MAX),
                numbers_only=config.get(CONF_NUMBERS_ONLY),
                make_bw=config.get(CONF_MAKE_BW),
                erode=config.get(CONF_ERODE),
                save_file_folder=save_file_folder,
                save_timestamped_file=config.get(CONF_SAVE_TIMESTAMPTED_FILE),
                unit_of_measurement=config.get(CONF_UNIT_OF_MEASUREMENT),
                camera_entity=camera.get(CONF_ENTITY_ID),
                name=camera.get(CONF_NAME),
            )
        )
    add_devices(entities)


class ObjectDetection(ImageProcessingEntity):
    """Perform object and label recognition."""

    def __init__(
        self,
        rekognition_client,
        region,
        roi_y_min,
        roi_x_min,
        roi_y_max,
        roi_x_max,
        numbers_only,
        make_bw,
        erode,
        save_file_folder,
        save_timestamped_file,
        unit_of_measurement,
        camera_entity,
        name=None,
    ):
        """Init with the client."""
        self._aws_rekognition_client = rekognition_client
        self._aws_region = region
        self._y_min = roi_y_min
        self._x_min = roi_x_min
        self._y_max = roi_y_max
        self._x_max = roi_x_max
        self._numbers_only = numbers_only
        self._make_bw = make_bw
        self._erode = erode
        self._save_file_folder = save_file_folder
        self._save_timestamped_file = save_timestamped_file
        self._unit_of_measurement = unit_of_measurement

        self._camera_entity = camera_entity
        if name:  # Since name is optional.
            self._name = name
        else:
            entity_name = split_entity_id(camera_entity)[1]
            self._name = f"rekognition_text_{entity_name}"
        self._state = None

    def process_image(self, image):
        """Process an image."""
        self._image = Image.open(io.BytesIO(bytearray(image)))  # used for saving only
        self._image_width, self._image_height = self._image.size
        (left, upper, right, lower) = (
            self._x_min * self._image_width,
            self._y_min * self._image_height,
            self._x_max * self._image_width,
            self._y_max * self._image_height,
        )

        # Crop and process the image before sending to AWS
        img_cropped = self._image.crop((left, upper, right, lower))
        if self._make_bw:
            img_cropped = img_cropped.convert("L")  # convert to black and white
        if self._erode:
            erode_factor = EROSION_MAP.get(
                self._erode
            )  # returns value ad configured sensitivity
            img_cropped = img_cropped.filter(
                ImageFilter.MinFilter(erode_factor)
            )  # erode

        response = self._aws_rekognition_client.detect_text(
            Image={"Bytes": image_to_byte_array(img_cropped)}
        )
        detected_text = {
            t["DetectedText"]: round(t["Confidence"], 2)
            for t in response["TextDetections"]
            if t["Type"] == "WORD"
        }  # e.g. {'1352': 89.22, 'the': 70.25}

        if len(detected_text) == 0:
            _LOGGER.info("Rekognition_text found no text")
            return

        # SInce we have text, get the result with the highest confidence
        max_confidence = max(detected_text.values())
        most_confident_text = [
            k for k, v in detected_text.items() if v == max_confidence
        ][
            0
        ]  # keep highest confidence result

        if self._numbers_only:  # attempt to return numbers
            found_numbers = re.sub("[^0-9,.]", "", most_confident_text)
            if found_numbers:
                self._state = found_numbers
        else:
            self._state = most_confident_text

        if self._save_file_folder:
            self.save_image()

    def save_image(self):
        draw = ImageDraw.Draw(self._image)
        roi_tuple = (self._y_min, self._x_min, self._y_max, self._x_max)
        draw_box(
            draw,
            roi_tuple,
            self._image_width,
            self._image_height,
            color=RED,
        )

        latest_save_path = (
            self._save_file_folder
            / f"{get_valid_filename(self._name).lower()}_latest.png"
        )
        self._image.save(latest_save_path)
        _LOGGER.info("Rekognition_text saved file %s", latest_save_path)
        if self._save_timestamped_file:
            now_str = dt_util.now().strftime(DATETIME_FORMAT)
            timestamp_save_path = self._save_file_folder / f"{self._name}_{now_str}.png"
            self._image.save(timestamp_save_path)
            _LOGGER.info("Rekognition_text saved file %s", timestamp_save_path)

    @property
    def camera_entity(self):
        """Return camera entity id from process pictures."""
        return self._camera_entity

    @property
    def state(self):
        """Return the state of the entity."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        attr = {}
        if self._numbers_only:
            attr[CONF_NUMBERS_ONLY] = self._numbers_only
        if self._make_bw:
            attr[CONF_MAKE_BW] = self._make_bw
        if self._erode:
            attr[CONF_ERODE] = self._erode
        if self._save_file_folder:
            attr[CONF_SAVE_FILE_FOLDER] = str(self._save_file_folder)
            attr[CONF_SAVE_TIMESTAMPTED_FILE] = self._save_timestamped_file
        return attr
