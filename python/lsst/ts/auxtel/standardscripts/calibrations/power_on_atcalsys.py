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

__all__ = ["PowerOnATCalSys"]

import asyncio
import time as time

import yaml
from lsst.ts import salobj
from lsst.ts.idl.enums import ATWhiteLight


class PowerOnATCalSys(salobj.BaseScript):
    """Powers on the ATCalSys dome flat illuminator
    (ATWhiteLight and ATMonochromator)
    required to perform image calibrations over white light.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    """

    def __init__(self, index, add_remotes: bool = True):
        super().__init__(
            index=index,
            descr="Power On AT Calibration System ",
        )

        self.white_light_source = None
        self.monochromator = None

        # White lamp config
        self.timeout_lamp_warm_up = 60 * 20
        self.track_lamp_warmup = 60
        self.cmd_timeout = 30
        self.timeout_std = 20

        # Chiller config
        self.timeout_chiller_cool_down = 60 * 15
        self.chiller_temp_tolerance_relative = 0.2

        # Shutter
        self.timeout_open_shutter = 60 * 3

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/auxtel/calibrations/power_on_atcalsys.yaml
            title: PowerOnATCalSys v1
            description: Configuration for PowerOnATCalSys.
              Each attribute can be specified as a scalar or array.
              All arrays must have the same length (one item per image).
            type: object
            properties:
              chiller_temperature:
                description: Set temperature for the chiller
                type: number
                default: 20
                minimum: 10

              whitelight_power:
                description: White light power.
                type: number
                default: 910
                minimum: 0

              wavelength:
                description: Wavelength (nm). 0 nm is for white light.
                type: number
                default: 0
                minimum: 0

              grating_type:
                description: Grating type for each image. The choices are 0=mirror, 1=blue, 2=red.
                type: integer
                enum: [0, 1, 2]
                default: 0

              entrance_slit_width:
                description: Width of the monochrometer entrance slit (mm)
                type: number
                minimum: 0
                default: 5

              exit_slit_width:
                description: Width of the monochromator entrance slit (mm)
                type: number
                minimum: 0
                default: 5

              use_atmonochromator:
                description: Is the monochromator available and can be configured?
                    If False, the monochromator will be left as it is.
                    If True, the monochromator will be configured for white light.
                type: boolean
                default: false

            additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        """Configure the script.

        Parameters
        ----------
        config : ``self.cmd_configure.DataType``

        """
        self.log.info("Configure started")

        self.chiller_temperature = config.chiller_temperature
        self.whitelight_power = config.whitelight_power
        self.wavelength = config.wavelength
        self.grating_type = config.grating_type
        self.entrance_slit_width = config.entrance_slit_width
        self.exit_slit_width = config.exit_slit_width
        self.use_atmonochromator = config.use_atmonochromator

        if self.white_light_source is None:
            self.white_light_source = salobj.Remote(
                domain=self.domain,
                name="ATWhiteLight",
            )

        if self.monochromator is None:
            self.monochromator = salobj.Remote(
                domain=self.domain,
                name="ATMonochromator",
            )

        await asyncio.gather(
            self.white_light_source.start_task,
            self.monochromator.start_task,
        )

        self.log.info("Configure completed")

    def set_metadata(self, metadata):
        """Compute estimated duration.

        Parameters
        ----------
        metadata : SAPY_Script.Script_logevent_metadataC
        """
        metadata.duration = self.timeout_chiller_cool_down + self.timeout_lamp_warm_up

    async def run(self):
        """Run script."""
        await self.assert_components_enabled()

        await self.checkpoint("Starting chiller")
        await self.start_chiller()

        await self.checkpoint("Waiting for chiller to cool to set temperature")
        await self.wait_for_chiller_temp_within_tolerance()

        await self.checkpoint("Opening the shutter")
        await self.open_white_light_shutter()

        await self.checkpoint("Turning on lamp")
        await self.switch_lamp_on()

        await self.checkpoint("Waiting for lamp to warm up")
        await self.wait_for_lamp_to_warm_up()

        if self.use_atmonochromator:
            await self.checkpoint("Configuring ATMonochromator")
            await self.configure_atmonochromator()

    async def start_chiller(self):
        """Starts chiller to run at self.chiller_temperature"""
        await self.white_light_source.cmd_setChillerTemperature.set_start(
            temperature=self.chiller_temperature, timeout=self.cmd_timeout
        )
        await self.white_light_source.cmd_startChiller.start(
            timeout=self.timeout_chiller_cool_down
        )

    async def wait_for_chiller_temp_within_tolerance(self):
        """Checks if chiller reaches set self.chiller_temperature within
        set self.chiller_temp_tolerance_relative in
        less than self.timeout_chiller_cool_down s.

        Raises
        ------
        TimeOutError:
            If the chiller doesn't reach self.chiller_temperature
            within tolerance in self.timeout_chiller_cool_down s."""
        start_chill_time = time.time()
        while time.time() - start_chill_time < self.timeout_chiller_cool_down:
            chiller_temps = await self.white_light_source.tel_chillerTemperatures.next(
                flush=True, timeout=self.timeout_std
            )
            tel_chiller_temp = chiller_temps.supplyTemperature
            self.log.debug(
                f"Chiller supply temperature: {tel_chiller_temp:0.1f} deg "
                f"[set:{chiller_temps.setTemperature} deg]."
            )
            if (
                abs(chiller_temps.setTemperature - tel_chiller_temp)
                / chiller_temps.setTemperature
                <= self.chiller_temp_tolerance_relative
            ):
                chill_time = time.time() - start_chill_time
                self.log.info(
                    f"Chiller reached target temperature, {tel_chiller_temp:0.1f} deg "
                    f"within tolerance, in {chill_time:0.1f} s."
                )
                break
        else:
            raise TimeoutError(
                f"Timeout waiting after {self.timeout_chiller_cool_down} s "
                f"for the chiller to chill to {chiller_temps.setTemperature} deg. "
                f"Stayed at {tel_chiller_temp:0.1f} deg."
            )

    async def open_white_light_shutter(self):
        """Opens shutter so the output of the beam can illuminate the
        calibration screen"""
        await self.white_light_source.cmd_openShutter.start(
            timeout=self.timeout_open_shutter
        )

    async def switch_lamp_on(self):
        """Switches on the white light source with an output
        power of self.whitelight_power W"""
        self.white_light_source.evt_lampState.flush()

        await self.white_light_source.cmd_turnLampOn.set_start(
            power=self.whitelight_power, timeout=self.timeout_lamp_warm_up
        )

    async def wait_for_lamp_to_warm_up(self):
        """Confirms the white light source has warmed up and is on.

        Raises:
        ------
        TimeOutError:
            If the lamp fails to turn on after self.timeout_lamp_warm_up"""
        lamp_state = await self.white_light_source.evt_lampState.aget(
            timeout=self.timeout_lamp_warm_up
        )
        self.log.info(
            f"Lamp state: {ATWhiteLight.LampBasicState(lamp_state.basicState)!r}."
        )
        while lamp_state.basicState != ATWhiteLight.LampBasicState.ON:
            try:
                lamp_state = await self.white_light_source.evt_lampState.next(
                    flush=False, timeout=self.timeout_lamp_warm_up
                )
                self.log.info(
                    f"Lamp state: {ATWhiteLight.LampBasicState(lamp_state.basicState)!r}."
                )
            except asyncio.TimeoutError:
                raise RuntimeError(
                    f"White Light Lamp failed to turn on after {self.timeout_lamp_warm_up} s."
                )

    async def configure_atmonochromator(self):
        """ATMonochromator configures the output beam to use
        the self.grating_type grating, wavelength of self.wavelength nm,
        and the entry and exit slits to be self.entrance_slit_width and
        self.exit_slit_width mm opened"""
        await self.monochromator.cmd_updateMonochromatorSetup.set_start(
            gratingType=self.grating_type,
            fontExitSlitWidth=self.exit_slit_width,
            fontEntranceSlitWidth=self.entrance_slit_width,
            wavelength=self.wavelength,
            timeout=self.cmd_timeout,
        )

        params = await self.get_monochromator_parameters()

        self.log.info(
            f"ATMonochromator grating is {params[0]}, \n"
            f"wavelength is {params[1]}, \n"
            f"with entry slit width {params[2]}, \n"
            f"and exit slit width {params[3]}"
        )

    async def get_monochromator_parameters(self):
        """Gets ATMonochromator configuration"""
        return await asyncio.gather(
            self.monochromator.evt_selectedGrating.aget(timeout=self.cmd_timeout),
            self.monochromator.evt_wavelength.aget(timeout=self.cmd_timeout),
            self.monochromator.evt_entrySlitWidth.aget(timeout=self.cmd_timeout),
            self.monochromator.evt_exitSlitWidth.aget(timeout=self.cmd_timeout),
        )

    async def assert_components_enabled(self):
        """Checks if ATWhiteLight and ATMonochromator are ENABLED

        Raises
        ------
        RunTimeError:
            If either component is not ENABLED"""

        comps = [self.white_light_source]
        if self.use_atmonochromator:
            comps = [self.white_light_source, self.monochromator]

        for comp in comps:
            summary_state = await comp.evt_summaryState.aget()
            if salobj.State(summary_state.summaryState) != salobj.State(
                salobj.State.ENABLED
            ):
                raise RuntimeError(f"{comp} is not ENABLED")
