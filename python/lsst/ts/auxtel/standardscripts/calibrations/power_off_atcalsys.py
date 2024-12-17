# This file is part of ts_auxtel_standardscripts
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

__all__ = ["PowerOffATCalSys"]

import asyncio

from lsst.ts import salobj
from lsst.ts.idl.enums import ATWhiteLight


class PowerOffATCalSys(salobj.BaseScript):
    """Powers off the ATCalSys dome flat illuminator
    turning white lamp off, closing the shutter and
    stopping the chiller.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    """

    def __init__(self, index, add_remotes: bool = True):
        super().__init__(
            index=index,
            descr="Power OFF AT Calibration System ",
        )

        self.white_light_source = None

        # White lamp config
        self.timeout_lamp_cool_down = 60 * 20
        self.cmd_timeout = 30

        # Shutter
        self.timeout_close_shutter = 60 * 2

    @classmethod
    def get_schema(cls):
        return None

    async def configure(self, config):
        # This script does not require any configuration

        self.log.info("Configure started")

        if self.white_light_source is None:
            self.white_light_source = salobj.Remote(
                domain=self.domain,
                name="ATWhiteLight",
            )

        await self.white_light_source.start_task

        self.log.info("Configure completed")

    def set_metadata(self, metadata):
        """Compute estimated duration."""

        metadata.duration = self.timeout_lamp_cool_down

    async def run(self):
        """Run script."""
        await self.assert_components_enabled()

        await self.checkpoint("Turning lamp off")
        await self.switch_lamp_off()

        await self.checkpoint("Closing the shutter")
        await self.white_light_source.cmd_closeShutter.start(
            timeout=self.timeout_close_shutter
        )

        await self.checkpoint("Waiting for lamp to cool down")
        await self.wait_for_lamp_to_cool_down()

        await self.checkpoint("Stopping chiller")
        await self.white_light_source.cmd_stopChiller.start(timeout=self.cmd_timeout)

    async def switch_lamp_off(self):
        """Switches white light source lamp off"""
        self.white_light_source.evt_lampState.flush()

        await self.white_light_source.cmd_turnLampOff.start(
            timeout=self.timeout_lamp_cool_down
        )

    async def wait_for_lamp_to_cool_down(self):
        """Confirm the white lamp has switched OFF and has cooled down
        to proceed with stopping the chiller.

        Raises
        ------
        TimeOutError:
            If the lamp doesn't cool down and fails to turn off
            in self.timeout_lamp_cool_down.
        """
        lamp_state = await self.white_light_source.evt_lampState.aget(
            timeout=self.timeout_lamp_cool_down
        )
        self.log.info(
            f"Lamp state: {ATWhiteLight.LampBasicState(lamp_state.basicState)!r}."
        )
        while lamp_state.basicState != ATWhiteLight.LampBasicState.OFF:
            try:
                lamp_state = await self.white_light_source.evt_lampState.next(
                    flush=False, timeout=self.timeout_lamp_cool_down
                )

                self.log.info(
                    f"Lamp state: {ATWhiteLight.LampBasicState(lamp_state.basicState)!r}. "
                )
            except asyncio.TimeoutError:
                raise RuntimeError(
                    f"White Light Lamp failed to turn off after {self.timeout_lamp_cool_down} s."
                )

    async def assert_components_enabled(self):
        """Check if ATWhiteLight is ENABLED

        Raises
        ------
        RunTimeError:
            If ATWhiteLight is not ENABLED"""
        summary_state = await self.white_light_source.evt_summaryState.aget(
            timeout=self.cmd_timeout
        )
        if summary_state.summaryState != salobj.State.ENABLED:
            raise RuntimeError("ATWhiteLight is not ENABLED")
