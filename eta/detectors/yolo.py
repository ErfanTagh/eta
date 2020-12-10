"""
Tnterface to the YOLOv4 object detection library available at
https://github.com/voxel51/darkflow.

Copyright 2017-2020, Voxel51, Inc.
voxel51.com

Brian Moore, brian@voxel51.com
"""
# pragma pylint: disable=redefined-builtin
# pragma pylint: disable=unused-wildcard-import
# pragma pylint: disable=wildcard-import
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import *

# pragma pylint: enable=redefined-builtin
# pragma pylint: enable=unused-wildcard-import
# pragma pylint: enable=wildcard-import

import logging
import warnings

import eta.constants as etac
from eta.core.config import Config, ConfigError
import eta.core.geometry as etag
import eta.core.learning as etal
import eta.core.objects as etao
import eta.core.tfutils as etat
import eta.core.utils as etau


_ERROR_MSG = """

You must clone and install a repository in order to use a YOLO model:

mkdir -p '{0}'
git clone https://github.com/voxel51/darkflow '{0}'
pip install -e '{0}'

""".format(
    etac.DARKFLOW_DIR
)


_ensure_tf1 = lambda: etau.ensure_package("tensorflow<2")
etau.lazy_import("tensorflow", callback=_ensure_tf1)

dnb = etau.lazy_import("darkflow.net.build", error_msg=_ERROR_MSG)


logger = logging.getLogger(__name__)


class YOLODetectorConfig(Config, etal.HasPublishedModel):
    """YOLO object detector configuration settings.

    Note that `config_dir` and `config_path` are passed through
    `eta.core.utils.fill_config_patterns` at load time, so they can contain
    patterns to be resolved.

    Attributes:
        model_name: the name of the published model to load. If this value is
            provided, `model_path` does not need to be
        model_path: the path to a Darkflow model weights file in `.weights`
            format to load. If this value is provided, `model_name` does not
            need to be
        config_dir: path to the darkflow configuration directory
        config_path: path to the darkflow model architecture file
        confidence_thresh: a confidence threshold to apply to candidate
            detections
    """

    def __init__(self, d):
        d = self.init(d)

        self.config_dir = etau.fill_config_patterns(
            self.parse_string(d, "config_dir")
        )
        self.config_path = etau.fill_config_patterns(
            self.parse_string(d, "config_path")
        )
        self.confidence_thresh = self.parse_number(
            d, "confidence_thresh", default=0
        )


class YOLODetector(etal.ObjectDetector):
    """Interface to the Darkflow YOLO object detector."""

    def __init__(self, config):
        """Constructs a YOLODetector instance.

        Args:
            config: a YOLODetectorConfig instance
        """
        self.config = config

        # Get path to model
        self.config.download_model_if_necessary()
        model_path = self.config.model_path

        try:
            # Get GPU usage from ETA
            tf_config = etat.make_tf_config()
            gpu = tf_config.gpu_options.per_process_gpu_memory_fraction
            logger.debug("Sending gpu: %g (from ETA config) to TFNet", gpu)
        except AttributeError:
            # By default, try to use all GPU
            gpu = 1.0
            logger.debug("Sending gpu: %g (default) to TFNet", gpu)

        # Block logging and warnings that we don't care about
        with etau.CaptureStdout():
            with warnings.catch_warnings(record=True):
                self._tfnet = dnb.TFNet(
                    {
                        "config": self.config.config_dir,
                        "model": self.config.config_path,
                        "load": model_path,
                        "json": True,
                        "summary": None,
                        "gpu": gpu,
                    }
                )

    @property
    def ragged_batches(self):
        """True/False whether :meth:`transforms` may return images of different
        sizes and therefore passing ragged lists of images to
        :meth:`detect_all` is not allowed.
        """
        return True

    @property
    def transforms(self):
        """The preprocessing transformation that will be applied to each image
        before detection, or ``None`` if no preprocessing is performed.
        """
        return None

    def detect(self, img):
        """Performs object detection on the input image.

        Args:
            img: an image

        Returns:
            objects: A DetectedObjectContainer describing the detected objects
                in the image
        """
        result = self._tfnet.return_predict(img)
        objects = [
            _to_detected_object(yd, img)
            for yd in result
            if yd["confidence"] >= self.config.confidence_thresh
        ]
        return etao.DetectedObjectContainer(objects=objects)


def _to_detected_object(yd, img):
    """Converts a YOLO detection to a DetectedObject.

    Args:
        yd: a YOLO detection dictionary
        img: the image on which the prediction was made

    Returns:
        a DetectedObject
    """
    tl = yd["topleft"]
    br = yd["bottomright"]
    bbox = etag.BoundingBox.from_abs_coords(
        tl["x"], tl["y"], br["x"], br["y"], img=img
    )
    return etao.DetectedObject(yd["label"], bbox, confidence=yd["confidence"])