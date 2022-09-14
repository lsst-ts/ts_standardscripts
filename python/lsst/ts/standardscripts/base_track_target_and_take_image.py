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

    def __init__(self, index: int, descr: str, add_remotes: bool = True):
        super().__init__(index=index, descr=descr)

        self.config = None

        # Flag to monitor if tracking started for cleanup task.
        self.tracking_started = False
        self.run_started = False

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
    anyOf:
      - type: array
        minItems: 1
        items:
          type: string
      - type: string
  reason:
    description: Optional reason for taking the data.
    anyOf:
      - type: string
      - type: "null"
    default: null
  program:
    description: Optional name of the program this data belongs to, e.g. WFD, DD, etc.
    anyOf:
      - type: string
      - type: "null"
    default: null
  camera_playlist:
    description: >-
      Optional name a camera playlist to load before running the script.
      This parameter is mostly designed to use for integration tests and is
      switched off by default (e.g. null).
    anyOf:
      - type: string
      - type: "null"
    default: null
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

        self.run_started = True

        await self.assert_feasibility()

        if self.config.camera_playlist is not None:
            await self.checkpoint(f"Loading playlist: {self.config.camera_playlist}.")
            self.log.warning(
                f"Running script with playlist: {self.config.camera_playlist}. "
                "This is only suitable for test-type run and should not be used for "
                "on-sky observations. If you are on sky, check your script configuration."
            )
            await self.load_playlist()

        await self.checkpoint(
            f"[{self.config.name}; "
            f"ra={self.config.ra}, dec={self.config.dec};"
            f"rot={self.config.rot_sky:0.2f}]::"
            "Track target and setup instrument."
        )

        await self.track_target_and_setup_instrument()

        await self.checkpoint(
            f"[{self.config.name}; "
            f"ra={self.config.ra}, dec={self.config.dec};"
            f"rot={self.config.rot_sky:0.2f}]::"
            "Take data."
        )

        await self.take_data()

        await self.checkpoint(
            f"[{self.config.name}; "
            f"ra={self.config.ra}, dec={self.config.dec};"
            f"rot={self.config.rot_sky:0.2f}]::"
            "done"
        )

    @abc.abstractstaticmethod
    async def load_playlist(self):
        """Load playlist."""
        raise NotImplementedError()

    @abc.abstractstaticmethod
    async def assert_feasibility(self):
        """Verify that the system is in a feasible state to execute the
        script.
        """
        raise NotImplementedError()

    @abc.abstractstaticmethod
    async def track_target_and_setup_instrument(self):
        """slewing of telescope and setting up of instrument.

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
            if self.run_started or self.tracking_started:
                self.log.warning(
                    f"Terminating with state={self.state.state}: stop tracking. "
                    f"Run started: {self.run_started}. "
                    f"Tracking started: {self.tracking_started}."
                )
                try:
                    await asyncio.wait_for(self.stop_tracking(), timeout=5)
                except asyncio.TimeoutError:
                    self.log.exception(
                        "Stop tracking command timed out during cleanup procedure."
                    )
                except Exception:
                    self.log.exception("Unexpected exception in stop_tracking.")
