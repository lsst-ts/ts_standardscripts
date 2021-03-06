# This file is part of ts_standardscripts
#
# Developed for the LSST Telescope and Site Systems.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License

__all__ = ["BaseTakeImage"]

import abc
import collections

import numpy as np
import yaml

from lsst.ts import salobj


class BaseTakeImage(salobj.BaseScript, metaclass=abc.ABCMeta):
    """Base take images script.

    Parameters
    ----------
    index : `int`
        SAL index of this Script

    Notes
    -----
    **Checkpoints**

    * exposure {n} of {m}: before sending the ``takeImages`` command
    """

    def __init__(self, index, descr):
        super().__init__(index=index, descr=descr)

        self.config = None

    @property
    @abc.abstractmethod
    def camera(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def get_instrument_configuration(self):
        """Get instrument configuration.

        Returns
        -------
        instrument_configuration: `dict`
            Dictionary with instrument configuration.
        """
        raise NotImplementedError()

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/auxtel/LatissTakeImage.yaml
            title: BaseTakeImage v2
            description: Configuration for BaseTakeImage.
            type: object
            properties:
              nimages:
                description: The number of images to take; if omitted then use the length of
                    exp_times or take a single exposure if exp_times is a scalar.
                anyOf:
                  - type: integer
                    minimum: 1
                  - type: "null"
                default: null
              exp_times:
                description: The exposure time of each image (sec). If a single value,
                  then the same exposure time is used for each exposure.
                anyOf:
                  - type: array
                    minItems: 1
                    items:
                      type: number
                      minimum: 0
                  - type: number
                    minimum: 0
                default: 0
              image_type:
                description: Image type (a.k.a. IMGTYPE) (e.g. e.g. BIAS, DARK, FLAT, OBJECT)
                type: string
                enum: ["BIAS", "DARK", "FLAT", "OBJECT", "ENGTEST", "SPOT"]
              group_id:
                description: A group ID for the set of images.
                type: string
              note:
                description: A descriptive note about the image being taken.
                type: string
            required: [image_type]
            additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        """Configure script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Script configuration, as defined by `schema`.
        """
        self.config = config

        nimages = self.config.nimages
        if isinstance(self.config.exp_times, collections.Iterable):
            if nimages is not None:
                if len(self.config.exp_times) != nimages:
                    raise ValueError(
                        f"nimages={nimages} specified and "
                        f"exp_times={self.config.exp_times} is an array, "
                        f"but the length does not match nimages"
                    )
        else:
            # exp_time is a scalar; if nimages is specified then
            # take that many images, else take 1 image
            if nimages is None:
                nimages = 1
            self.config.exp_times = [self.config.exp_times] * nimages

    def set_metadata(self, metadata):
        nimages = len(self.config.exp_times)
        mean_exptime = np.mean(self.config.exp_times)
        metadata.duration = (
            mean_exptime + self.camera.read_out_time + self.camera.shutter_time * 2
            if self.camera.shutter_time
            else 0
        ) * nimages

    async def run(self):
        nimages = len(self.config.exp_times)
        group_id = getattr(self.config, "group_id", self.group_id)
        note = getattr(self.config, "note", None)
        for i, exposure in enumerate(self.config.exp_times):
            self.log.debug(
                f"Exposing image {i+1} of {nimages} with exp_time={exposure}s."
            )
            await self.checkpoint(f"exposure {i+1} of {nimages}")
            await self.camera.take_imgtype(
                self.config.image_type,
                exposure,
                1,
                group_id=group_id,
                note=note,
                **self.get_instrument_configuration(),
            )
