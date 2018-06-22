#!/usr/bin/env python
'''
Example of embedding an image manually via `VGG16`.

This example has the same effect as `embed_image.py` except that it directly
uses the low-level functionality rather than the higher level `Featurizer`
functionality. It is included here for pedagogical reasons with ETA.

Copyright 2017-2018, Voxel51, LLC
voxel51.com

Jason Corso, jjc@voxel51.com
Brian Moore, brian@voxel51.com
'''
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
import os
import sys

import tensorflow as tf
import numpy as np

import eta.core.image as etai
import eta.core.utils as etau
import eta.core.vgg16 as etav


logger = logging.getLogger(__name__)


def embed_image(impath):
    '''Embeds the image using VGG-16 with the default weights.

    Stores the embedded vector as an .npz file on disk.

    Args:
        impath: path to an image to embed
    '''
    img = etai.read(impath)
    rimg = etai.resize(img, 224, 224)

    vgg16 = etav.VGG16()
    embedded_vector = vgg16.evaluate(rimg, layer=vgg16.fc2l)

    logger.info("Image embedded to vector of length %d", len(embedded_vector))
    logger.info("%s", embedded_vector)

    outpath = _abspath("out/result_embed_image.npz")
    etau.ensure_basedir(outpath)
    np.savez_compressed(outpath, v=embedded_vector)
    logger.info("Result saved to '%s'", outpath)


def _abspath(path):
    return os.path.realpath(os.path.join(os.path.dirname(__file__), path))


if __name__ == "__main__":
    if len(sys.argv) == 2:
        impath = sys.argv[1]
    else:
        impath = _abspath("../data/water.jpg")

    embed_image(impath)
