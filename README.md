# HASS-amazon-rekognition-text
Home Assistant integration to extract text from digital and mechanical displays using AWS rekognition.

Adds an entity where the state of the entity is the detected text in the camera image. A region of interest (`roi`) should be used to select the region of the image containing the text you wish to read.

**Note** that to view the configured `roi` you must configure the `save_file_folder` and view the latest saved image, which can be displayed on the HA UI with a [local_file camera](https://www.home-assistant.io/integrations/local_file/)

Example config:
```yaml
image_processing:
  - platform: amazon_rekognition_text
    aws_access_key_id: yours
    aws_secret_access_key: yours
    region_name: eu-west-1 # optional region, default is us-east-1
    roi_x_min: 0.35
    roi_x_max: 0.83
    roi_y_min: 0.7
    roi_y_max: 0.9
    save_file_folder: /config/rekognition/
    source:
      - entity_id: camera.local_file
```

Configuration variables:
- **aws_access_key_id**: Your AWS key ID
- **aws_secret_access_key**: Your AWS key secret
- **region_name**: Your preferred AWS region
- **roi_x_min**: (optional, default 0), range 0-1, must be less than roi_x_max
- **roi_x_max**: (optional, default 1), range 0-1, must be more than roi_x_min
- **roi_y_min**: (optional, default 0), range 0-1, must be less than roi_y_max
- **roi_y_max**: (optional, default 1), range 0-1, must be more than roi_y_min
- **save_file_folder**: (Optional) The folder to save processed images to. Note that folder path should be added to [whitelist_external_dirs](https://www.home-assistant.io/docs/configuration/basic/)
- **source**: Must be a camera.

For the ROI, the (x=0,y=0) position is the top left pixel of the image, and the (x=1,y=1) position is the bottom right pixel of the image. It might seem a bit odd to have y running from top to bottom of the image, but that is the coordinate system used by pillow. A streamlit app is provided to help with configuration of the ROI values, documented at the end of this readme.

<p align="center">
<img src="https://github.com/robmarkcole/HASS-amazon-rekognition-text/blob/main/docs/usage.png" width="500">
</p>

## `local_file` camera example
Example config for displaying the latest saved image:
```yaml
camera:
  - platform: local_file
    name: rekognition_text
    file_path: /config/rekognition/rekognition_text_local_file_1_latest.png
```

## Streamlit app
A streamlit app is available to help with config. To use a hosted version go to:
- [https://share.streamlit.io/robmarkcole/hass-amazon-rekognition-text/main](https://share.streamlit.io/robmarkcole/hass-amazon-rekognition-text/main)

Or run locally following the instructions below:
* Create a venv: `python3 -m venv venv`
* Activate venv: `source venv/bin/activate`
* Install requirements: `pip3 install -r requirements-app.txt`
* Run streamlit app: `streamlit run streamlit_app.py`

<p align="center">
<img src="https://github.com/robmarkcole/HASS-amazon-rekognition-text/blob/main/docs/streamlit_app.png" width="900">
</p>