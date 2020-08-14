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

__all__ = ["BaseSlew"]

import abc
import yaml
import asyncio

from lsst.ts import salobj
from lsst.ts.idl.enums.Script import ScriptState


class BaseSlew(salobj.BaseScript, metaclass=abc.ABCMeta):
    """Base slew script.

    This script implements the basic configuration and run procedures for
    slewing. It is a base class for both the Main and Auxiliary Telescope.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    **Details**

    """

    __test__ = False  # stop pytest from warning that this is not a test

    def __init__(self, index, descr):
        super().__init__(index=index, descr=descr)

        self.config = None

        # Flag to monitor if tracking started for cleanup task.
        self.tracking_started = False

        # Flag to specify which type of slew will be performend:
        # slew_icrs or slew_object
        self.slew_icrs = False

    @property
    @abc.abstractmethod
    def tcs(self):
        raise NotImplementedError()

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/base_slew.yaml
            title: BaseSlew v1
            description: Configuration for BaseSlew
            type: object
            properties:
              ra:
                description: ICRS right ascension (hour)
                anyOf:
                  - type: number
                    minimum: 0
                    maximum: 24
              dec:
                description: ICRS declination (deg)
                anyOf:
                  - type: number
                    minimum: -90
                    maximum: 90
              rot_value:
                description: >-
                  Rotator position value. Actual meaning depends on rot_strategy.
                type: number
                default: 0
              rot_strategy:
                description: Rotator strategy.
                type: string
                enum: ["sky", "parallactic", "physical_sky"]
                default: sky
              target_name:
                description: Target name
                type: string
            if:
              properties:
                ra:
                  const: null
                dec:
                  const: null
              required: ["target_name"]
            else:
              required: ["ra", "dec"]
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

        self.config = config

        if hasattr(self.config, "ra"):
            self.slew_icrs = True

        if self.config.rot_strategy != "sky":
            # TODO: Implement other rotation strategies (DM-26321).
            raise NotImplementedError(
                f"(DM-26321): {self.config.rot_strategy} not implemented. Use sky."
            )

    def set_metadata(self, metadata):
        """Compute estimated duration.

        Parameters
        ----------
        metadata : SAPY_Script.Script_logevent_metadataC
        """
        metadata.duration = 1

    async def run(self):

        target_name = getattr(self.config, "target_name", "slew_icrs")

        self.tracking_started = True

        if self.slew_icrs:
            self.log.info(
                f"Slew and track target_name={target_name}; "
                f"ra={self.config.ra}, dec={self.config.dec};"
                f"rot_value={self.config.rot_value}; rot_strategy={self.config.rot_strategy}"
            )

            # TODO: Implement other rotation strategies (DM-26321).
            await self.tcs.slew_icrs(
                ra=self.config.ra,
                dec=self.config.dec,
                rot_sky=self.config.rot_value,
                target_name=target_name,
            )
        else:
            self.log.info(
                f"Slew and track target_name={target_name}; "
                f"rot_value={self.config.rot_value}; rot_strategy={self.config.rot_strategy}"
            )
            # TODO: Implement other rotation strategies (DM-26321).
            await self.tcs.slew_object(name=target_name, rot_sky=self.config.rot_value)

    async def cleanup(self):

        if self.state.state != ScriptState.ENDING:
            # abnormal termination
            if self.tracking_started:
                self.log.warning(
                    f"Terminating with state={self.state.state}: stop tracking."
                )
                try:
                    await asyncio.wait_for(self.tcs.stop_tracking(), timeout=5)
                except asyncio.TimeoutError:
                    self.log.exception(
                        "Stop tracking command timed out during cleanup procedure."
                    )
                except Exception:
                    self.log.exception("Unexpected exception in stop_tracking.")
