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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__all__ = ["BasePointAzEl"]

import abc
import asyncio
import time

import yaml
from lsst.ts.idl.enums.Script import ScriptState

from .base_block_script import BaseBlockScript


class BasePointAzEl(BaseBlockScript, metaclass=abc.ABCMeta):
    """A base Script that implements pointing the telescope
    to a fixed Az/El/Rot position.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    """

    def __init__(self, index, descr):
        super().__init__(index=index, descr=descr)

        self.config = None

    @property
    @abc.abstractmethod
    def tcs(self):
        raise NotImplementedError()

    @abc.abstractmethod
    async def configure_tcs(self):
        """Abstract method to configure the TCS."""
        raise NotImplementedError()

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/BasePointAzEl.yaml
            title: PointAzEl v1
            description: Configuration for PointAzEl command.
            type: object
            properties:
                az:
                    description: >-
                        Target Azimuth in degrees.
                    type: number
                el:
                    description: >-
                        Target Elevation in degrees.
                    type: number
                    minimum: 0.0
                    maximum: 90.0
                rot_tel:
                    description: >-
                        Rotator angle in mount physical coordinates (degrees).
                    type: number
                    default: 0.0
                target_name:
                    description: Name of the position.
                    type: string
                    default: "AzEl"
                wait_dome:
                    description: >-
                        Wait for dome to be in sync with the telescope?
                    type: boolean
                    default: false
                slew_timeout:
                    description: Timeout for slew procedure (in seconds).
                    type: number
                    default: 240.0
                ignore:
                    description: >-
                        CSCs from the group to ignore in status check. Name must
                        match those in self.group.components, e.g.; hexapod_1.
                    type: array
                    items:
                        type: string
            required:
                - az
                - el
            additionalProperties: false
        """
        schema_dict = yaml.safe_load(schema_yaml)

        base_schema_dict = super().get_schema()

        for properties in base_schema_dict["properties"]:
            schema_dict["properties"][properties] = base_schema_dict["properties"][
                properties
            ]

        return schema_dict

    async def configure(self, config):
        """Configure script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Script configuration, as defined by `schema`.
        """
        self.config = config

        await self.configure_tcs()

        if hasattr(self.config, "ignore"):
            self.tcs.disable_checks_for_components(components=config.ignore)

        await super().configure(config=config)

    async def assert_feasibility(self) -> None:
        """Verify that the telescope is in a feasible state to
        execute the script.
        """

        await self.tcs.assert_all_enabled()

    async def run_block(self):
        await self.assert_feasibility()

        start_time = time.monotonic()
        self.log.info(
            f"Start slew to Az: {self.config.az},  El: {self.config.el} and "
            f"Rot: {self.config.rot_tel}"
        )

        await self.tcs.point_azel(
            az=self.config.az,
            el=self.config.el,
            rot_tel=self.config.rot_tel,
            target_name=self.config.target_name,
            wait_dome=self.config.wait_dome,
            slew_timeout=self.config.slew_timeout,
        )
        await self.tcs.stop_tracking()

        elapsed_time = time.monotonic() - start_time

        self.log.info(f"Slew finished in {elapsed_time}.")

    async def cleanup(self):
        if self.state.state != ScriptState.STOPPING:
            # abnormal termination
            self.log.warning(
                f"Terminating with state={self.state.state}: stop telescope."
            )
            try:
                await self.tcs.stop_tracking()
            except asyncio.TimeoutError:
                self.log.exception(
                    "Stop tracking command timed out during cleanup procedure."
                )
            except Exception:
                self.log.exception("Unexpected exception while stopping telescope.")
