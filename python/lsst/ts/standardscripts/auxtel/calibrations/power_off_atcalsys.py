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

__all__ = ["PowerOffATCalSys"]

import asyncio
import time as time

from lsst.ts.idl.enums import ATWhiteLight

from lsst.ts import salobj


class PowerOffATCalSys(salobj.BaseScript):
    """Powers on the ATCalSys dome flat illuminator
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
        self.timeout_lamp_cool_down = 60 * 15
        self.cmd_timeout = 30

    @classmethod
    def get_schema(cls):
        return None

    async def configure(self, config):
        # This script does not require any configuration
        pass

    def set_metadata(self, metadata):
        """Compute estimated duration."""

        metadata.duration = self.timeout_lamp_cool_down

    async def run(self):
        """Run script."""
        await self.assert_components_enabled()

        await self.checkpoint("Turning lamp off")
        await self.white_light_source.cmd_turnLampOff.set_start(
            timeout=self.timeout_lamp_cool_down
        )

        await self.checkpoint("Closing the shutter")
        await self.white_light_source.cmd_closeShutter.start()

        await self.checkpoint("Waiting for lamp to cool down")
        await self.wait_for_lamp_to_cool_down()

        await self.checkpoint("Stopping chiller")
        await self.white_light_source.cmd_stopChiller.set_start(
            timeout=self.cmd_timeout
        )

    async def wait_for_lamp_to_cool_down(self):
        self.white_light_source.evt_lampState.flush()
        start_time_lamp_warm_up = time.time()
        while time.time() - start_time_lamp_warm_up < self.timeout_lamp_warm_up:
            lamp_state = await self.white_light_source.evt_lampState.next(
                flush=False, timeout=self.timeout_lamp_warm_up
            )
            if lamp_state.basicState == ATWhiteLight.LampBasicState.WARMUP:
                warmup_time_left = (
                    lamp_state.warmupEndTime - lamp_state.private_sndStamp
                )
                self.log.info(f"Time Left for lamp warmup: {warmup_time_left} min.")
                await asyncio.sleep(self.track_lamp_warmup)

            elif lamp_state.basicState == ATWhiteLight.LampBasicState.ON:
                self.log.info(
                    f"White Light Lamp is on after a warm up of {time.time() - start_time_lamp_warm_up} s"
                )
        else:
            raise TimeoutError(
                f"White Light Lamp failed to turn on after {self.timeout_lamp_warm_up} s"
            )

    async def assert_components_enabled(self):
        """Check if ATWhiteLight and ATMonochromator are ENABLED"""
        for comp in [self.white_light_source, self.monochromator]:
            summary_state = await comp.evt_summaryState.aget()
            if salobj.State(summary_state.summaryState) != salobj.State(
                salobj.State.ENABLED
            ):
                raise Exception(f"{comp} is not ENABLED")
