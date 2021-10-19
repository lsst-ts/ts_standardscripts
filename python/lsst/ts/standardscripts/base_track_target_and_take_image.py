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

__all__ = ["BaseTrackTargetAndTakeImage"]

import abc
import yaml
import asyncio

from lsst.ts import salobj
from lsst.ts.idl.enums.Script import ScriptState


class BaseTrackTargetAndTakeImage(salobj.BaseScript):
    """Track target and take image script.

    This script implements a simple visit consisting of slewing to a target,
    start tracking and take image.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.
    add_remotes : `bool` (optional)
        Create remotes to control components (default: `True`)? If False, the
        script will not work for normal operations. Useful for unit testing.
    """

    __test__ = False  # stop pytest from warning that this is not a test

    def __init__(self, index: int, descr: str, add_remotes: bool = True):
        super().__init__(index=index, descr=descr)

        self.config = None

        # Flag to monitor if tracking started for cleanup task.
        self.tracking_started = False

    @classmethod
    def get_base_schema(cls):
        schema_yaml = """
$schema: http://json-schema.org/draft-07/schema#
$id: https://github.com/lsst-ts/ts_standardscripts/base_track_target_and_take_image.py
title: BaseTrackTargetAndTakeImage v1
description: Configuration for BaseTrackTargetAndTakeImage.
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
      The position angle in the Sky. 0 deg means that North is pointing up
      in the images.
    type: number
  name:
    description: Target name.
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
required:
  - ra
  - dec
  - rot_sky
  - name
  - obs_time
  - num_exp
  - exp_times
  - band_filter
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

        await self.checkpoint(
            f"Track target and setup instrument::[target_name={self.config.name}; "
            f"ra={self.config.ra}, dec={self.config.dec};"
            f"rot={self.config.rot_sky}]"
        )

        await self.track_target_and_setup_instrument()

        await self.checkpoint("Taking data")

        await self.take_data()

        await self.checkpoint("done")

    @abc.abstractstaticmethod
    async def track_target_and_setup_instrument(self):
        """Implement slewing and setting up instrumment.

        Ideally this would be done in parallel to save time.
        """
        raise NotImplementedError()

    @abc.abstractstaticmethod
    async def take_data(self):
        """Implement method to take data."""
        raise NotImplementedError()

    @abc.abstractstaticmethod
    async def stop_tracking(self):
        """Implement method to stop tracking."""
        raise RuntimeError()

    async def cleanup(self):

        if self.state.state != ScriptState.ENDING:
            # abnormal termination
            if self.tracking_started:
                self.log.warning(
                    f"Terminating with state={self.state.state}: stop tracking."
                )
                try:
                    await asyncio.wait_for(self.stop_tracking(), timeout=5)
                except asyncio.TimeoutError:
                    self.log.exception(
                        "Stop tracking command timed out during cleanup procedure."
                    )
                except Exception:
                    self.log.exception("Unexpected exception in stop_tracking.")
