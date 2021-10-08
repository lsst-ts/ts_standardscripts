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

__all__ = ["TrackTargetAndTakeImage"]

import yaml
import asyncio

from lsst.ts import salobj
from lsst.ts.idl.enums.Script import ScriptState

from lsst.ts.observatory.control.utils import RotType
from lsst.ts.observatory.control.auxtel import ATCS, ATCSUsages, LATISS, LATISSUsages


class TrackTargetAndTakeImage(salobj.BaseScript):
    """Track target and take image script.

    This script implements a simple visit consistig of slewing to a target,
    start tracking and take image.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.
    descr : `str`
        Short Script description.

    """

    __test__ = False  # stop pytest from warning that this is not a test

    def __init__(self, index):
        super().__init__(index=index, descr="Track target and take image.")

        self.atcs = ATCS(self.domain, intended_usage=ATCSUsages.Slew, log=self.log)
        self.latiss = LATISS(
            self.domain, intended_usage=LATISSUsages.TakeImageFull, log=self.log
        )

        self.config = None

        # Flag to monitor if tracking started for cleanup task.
        self.tracking_started = False

    @classmethod
    def get_schema(cls):
        schema_yaml = """
$schema: http://json-schema.org/draft-07/schema#
$id: https://github.com/lsst-ts/ts_standardscripts/auxtel/track_target_and_take_image.py
title: TrackTargetAndTakeImage v1
description: Configuration for TrackTargetAndTakeImage.
type: object
properties:
  targetid:
    description: Id of the target.
    type: integer
  ra:
    description: ICRS right ascension (hour).
    anyOf:
      - type: number
        minimum: 0
        maximum: 24
      - type: string
  dec:
    description: ICRS declination (deg).
    anyOf:
      - type: number
        minimum: -90
        maximum: 90
      - type: string
  rot_sky:
    description: >-
      The position angle in the Sky. 0 deg means that North is pointing up >- 
      in the images.
    type: number
  name:
    description: Target name
    type: string
  obs_time:
    type: number
    description: When should slew start.
  estimated_slew_time:
    type: number
    description: An estimative of how much a slew will take.
    default: 0
  num_exp:
    type: integer
    description: Number of exposures.
  exp_times:
    description: Exposure times in seconds.
    type: array
    minItems: 1
    items:
      type: number
      minimum: 0
  band_filter:
    description: Name of the filter for observation.
    type: string
  grating:
    description: Name of the grating for observation.
    type: string
required:
  - ra
  - dec
  - rot_sky
  - name
  - obs_time
  - num_exp
  - exp_times
  - band_filter
  - grating
additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        """Configure the script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration
        """

        self.log.debug(f"Configured with {config}.")
        self.config = config

    def set_metadata(self, metadata):
        """Compute estimated duration.

        Parameters
        ----------
        metadata : `Script_logevent_metadata`
        """
        metadata.duration = sum(self.config.exp_times) + self.config.estimated_slew_time

    async def run(self):

        self.tracking_started = True

        await self.checkpoint(
            f"Slew and track target_name={self.config.name}; "
            f"ra={self.config.ra}, dec={self.config.dec};"
            f"rot={self.config.rot_sky}; rot_type={RotType.Sky}"
        )

        await asyncio.gather(
            self.atcs.slew_icrs(
                ra=self.config.ra,
                dec=self.config.dec,
                rot=self.config.rot_sky,
                rot_type=RotType.Sky,
                target_name=self.config.name,
            ),
            self.latiss.setup_atspec(
                grating=self.config.grating, filter=self.config.band_filter
            ),
        )

        await self.checkpoint("Taking data")

        tasks = [
            asyncio.create_task(self.take_data()),
            asyncio.create_task(self.atcs.check_tracking()),
        ]

        await self.atcs.process_as_completed(tasks)

        await self.checkpoint("done")

    async def take_data(self):

        for exptime in self.config.exp_times:
            await self.latiss.take_object(exptime = exptime)

    async def cleanup(self):

        if self.state.state != ScriptState.ENDING:
            # abnormal termination
            if self.tracking_started:
                self.log.warning(
                    f"Terminating with state={self.state.state}: stop tracking."
                )
                try:
                    await asyncio.wait_for(self.atcs.stop_tracking(), timeout=5)
                except asyncio.TimeoutError:
                    self.log.exception(
                        "Stop tracking command timed out during cleanup procedure."
                    )
                except Exception:
                    self.log.exception("Unexpected exception in stop_tracking.")
