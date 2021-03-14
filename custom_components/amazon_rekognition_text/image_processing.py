"""
Integration that will perform text detection.
"""
import io
import logging
import re
import time

from PIL import Image

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

from homeassistant.const import ATTR_ENTITY_ID, ATTR_NAME

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

CONF_BOTO_RETRIES = "boto_retries"
DEFAULT_BOTO_RETRIES = 5

EVENT_TEXT_DETECTED = "rekognition.text_detected"

REQUIREMENTS = ["boto3"]


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_REGION, default=DEFAULT_REGION): vol.In(SUPPORTED_REGIONS),
        vol.Required(CONF_ACCESS_KEY_ID): cv.string,
        vol.Required(CONF_SECRET_ACCESS_KEY): cv.string,
        vol.Optional(CONF_BOTO_RETRIES, default=DEFAULT_BOTO_RETRIES): vol.All(
            vol.Coerce(int), vol.Range(min=0)
        ),
    }
)


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

    entities = []
    for camera in config[CONF_SOURCE]:
        entities.append(
            ObjectDetection(
                rekognition_client=rekognition_client,
                region=config.get(CONF_REGION),
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
        camera_entity,
        name=None,
    ):
        """Init with the client."""
        self._aws_rekognition_client = rekognition_client
        self._aws_region = region

        self._camera_entity = camera_entity
        if name:  # Since name is optional.
            self._name = name
        else:
            entity_name = split_entity_id(camera_entity)[1]
            self._name = f"rekognition_text_{entity_name}"
        self._state = None  # The number of instances of interest

    def process_image(self, image):
        """Process an image."""
        self._state = None
        response = self._aws_rekognition_client.detect_text(Image={"Bytes": image})
        self._state = [t['DetectedText'] for t in response['TextDetections']]

    @property
    def camera_entity(self):
        """Return camera entity id from process pictures."""
        return self._camera_entity

    @property
    def state(self):
        """Return the state of the entity."""
        return self._state

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "characters"

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        attr = {}
        return attr
