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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

__all__ = ["BaseTakeImage"]

import abc
import asyncio
import collections

import astropy.units
import numpy as np
import yaml
from astropy.coordinates import ICRS, Angle
from lsst.ts import salobj
from lsst.ts.xml.enums.Script import MetadataCoordSys, MetadataRotSys


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

        self.instrument_setup_time = 0.0

    @property
    @abc.abstractmethod
    def tcs(self):
        raise NotImplementedError()

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

    @abc.abstractmethod
    def get_instrument_name(self):
        """Get instrument name.

        Returns
        -------
        instrument_name: `string`
        """
        raise NotImplementedError()

    def get_instrument_filter(self):
        """Get instrument filter configuration.
        Returns
        -------
        instrument_filter: `string`
        """
        return self.get_instrument_configuration().get("filter", "")

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
                description: Image type (a.k.a. IMGTYPE) (e.g. BIAS, DARK, FLAT, OBJECT)
                type: string
                enum: ["BIAS", "DARK", "FLAT", "OBJECT", "ENGTEST", "ACQ", "SPOT", "CWFS", "FOCUS"]
              reason:
                description: Optional reason for taking the data.
                type: string
              program:
                description: Name of the program this data belongs to, e.g. WFD, DD, etc.
                type: string
              note:
                description: A descriptive note about the image being taken.
                type: string
                maxLength: 62
              slew_time:
                description: Emulate a slewttime by sleeping before taking data.
                type: number
                default: 0
              sleep_for:
                description: Add a sleep time in between exposures.
                type: number
                default: 0
              visit_metadata:
                type: object
                properties:
                  ra:
                    description: ICRS right ascension (hour). Note this is ONLY used for script queue.
                    anyOf:
                    - type: number
                      minimum: 0
                      maximum: 24
                    - type: string
                  dec:
                    description: ICRS declination (deg). Note this is ONLY used for script queue metadata.
                    anyOf:
                    - type: number
                      minimum: -90
                      maximum: 90
                    - type: string
                  rot_sky:
                    description: >-
                      The position angle in the Sky. 0 deg means that North is pointing up
                      in the images. Note this is ONLY used for script queue metadata.
                    type: number
                required: [ra, dec, rot_sky]
              ignore:
                  description: >-
                    CSCs from the groups to ignore in status check. Name must
                    match those in self.tcs.components, e.g.; mthexapod_1, atdome.
                  type: array
                  items:
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
        if isinstance(self.config.exp_times, collections.abc.Iterable):
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

        if hasattr(config, "ignore"):
            self.log.debug("Ignoring TCS components.")
            self.tcs.disable_checks_for_components(components=config.ignore)

    def set_metadata(self, metadata):
        nimages = len(self.config.exp_times)
        mean_exptime = np.mean(self.config.exp_times)
        sleep_time = self.config.sleep_for
        metadata.duration = (
            self.instrument_setup_time
            + self.config.slew_time
            + (
                mean_exptime
                + sleep_time
                + self.camera.read_out_time
                + self.camera.shutter_time * 2
                if self.camera.shutter_time
                else 0
            )
            * nimages
        )
        metadata.nimages = len(self.config.exp_times)
        metadata.instrument = self.get_instrument_name()

        if hasattr(self.config, "program"):
            metadata.survey = self.config.program

        if hasattr(self.config, "visit_metadata"):
            metadata.coordinateSystem = MetadataCoordSys.ICRS
            radec_icrs = ICRS(
                Angle(self.config.visit_metadata["ra"], unit=astropy.units.hourangle),
                Angle(self.config.visit_metadata["dec"], unit=astropy.units.deg),
            )
            metadata.position = [radec_icrs.ra.deg, radec_icrs.dec.deg]
            metadata.rotationSystem = MetadataRotSys.SKY
            metadata.cameraAngle = self.config.visit_metadata["rot_sky"]

        if self.get_instrument_filter() is not None:
            metadata.filters = str(self.get_instrument_filter())

    async def run(self):
        nimages = len(self.config.exp_times)
        note = getattr(self.config, "note", None)
        reason = getattr(self.config, "reason", None)
        program = getattr(self.config, "program", None)

        setup_tasks = [
            self.camera.setup_instrument(**self.get_instrument_configuration())
        ]

        if self.config.slew_time > 0:
            await self.checkpoint(
                f"Setup instrument and concurrently sleep for {self.config.slew_time}s "
                "before data acquisition."
            )
            setup_tasks.append(asyncio.sleep(self.config.slew_time))
        else:
            await self.checkpoint("setup instrument")

        await asyncio.gather(*setup_tasks)
        for i, exposure in enumerate(self.config.exp_times):
            self.log.debug(
                f"Exposing image {i+1} of {nimages} with exp_time={exposure}s."
            )
            await self.checkpoint(f"exposure {i+1} of {nimages}")
            await self.camera.take_imgtype(
                self.config.image_type,
                exposure,
                1,
                n_snaps=1,
                reason=reason,
                program=program,
                group_id=self.group_id,
                note=note,
            )

            if self.config.sleep_for > 0:
                self.log.info(
                    f"Sleeping for {self.config.sleep_for}s before next image."
                )
                await asyncio.sleep(self.config.sleep_for)
