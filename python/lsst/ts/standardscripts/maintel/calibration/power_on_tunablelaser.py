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

__all__ = ["PowerOnATCalSys"]

import asyncio
import time as time

import yaml
from lsst.ts import salobj


class PowerOnTunableLaser(salobj.BaseScript):
    """Starts propagating the Tunable Laser for functional
    testing. 

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    """

    def __init__(self, index, add_remotes: bool = True):
        super().__init__(
            index=index,
            descr="Power On Tunable Laser",
        )

        self.laser = None
        self.laser_warmup = 20. #some time for Laser to warmup

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/auxtel/calibrations/power_on_tunablelaser.yaml
            title: PowerOnTunableLaser v1
            description: Configuration for PowerOnTunableLaser.
              Each attribute can be specified as a scalar or array.
              All arrays must have the same length (one item per image).
            type: object
            properties:
              mode:
                description: Continuous or Burst Mode
                type: str
                default: Continuous

              optical_configuration:
                description: Output Configuration
                type: string
                default: SCU

              wavelength:
                description: Wavelength (nm). 0 nm is for white light.
                type: number
                default: 500.
                minimum: 250.

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

        self.mode = config.mode
        self.optical_configuration = config.optical_configuration
        self.wavelength = config.wavelength

        if self.laser is None:
            self.laser = salobj.Remote(
                domain=self.domain,
                name="TunableLaser",
            )

        self.laser.start_task

        self.log.info("Configure completed")

    def set_metadata(self, metadata):
        """Compute estimated duration.

        Parameters
        ----------
        metadata : SAPY_Script.Script_logevent_metadataC
        """
        metadata.duration = self.laser_warmup

    async def run(self):
        """Run script."""
        await self.assert_components_enabled()

        await self.checkpoint("Configuring TunableLaser")
        await self.configure_tunablelaser()

        await self.checkpoint("Starting laser propagation")
        await self.start_propagation_on()

    async def start_propagation_on(self):
        """Starts propagation of the laser"""
        self.laser.evt_lampState.flush()

        await self.laser.cmd_startPropagateLaser.start(
            timeout=self.laser_warmup
        )

    async def configure_tunablelaser(self):
        """Configure the TunableLaser for the mode and optical configuration"""
        await self.laser.changeWavelength.set_start(wavelength=self.wavelength, timeout=self.long_timeout
        )
        await self.laser.setOpticalConfiguration.set_start(configuration=self.optical_configuration, timeout=self.long_timeout)
        if self.mode == "Continuous":
            await self.laser.setContinuousMode.start(timeout=self.long_timeout)
        elif self.mode == "Burst":
            await self.laser.setBurstMode.start(timeout=self.long_timeout)

        params = await self.get_laser_parameters()

        self.log.info(
            f"Laser Configuration is {params[0]}, \n"
            f"wavelength is {params[1]}, \n"
            f"Interlock is {params[2]}, \n"
            f"Burst mode is {params[3]}, \n"
            f"Cont. mode is {params[4]}"
        )

    async def get_monochromator_parameters(self):
        """Gets ATMonochromator configuration"""
        return await asyncio.gather(
            self.laser.evt_opticalConfiguration.aget(timeout=self.cmd_timeout),
            self.laser.evt_wavelengthChanged.aget(timeout=self.cmd_timeout),
            self.laser.evt_interlockState.aget(timeout=self.cmd_timeout),
            self.laser.evt_burstModeSet.aget(timeout=self.cmd_timeout),
            self.laser.evt_continuousModeSet.aget(timeout=self.cmd_timeout),
        )

    async def assert_components_enabled(self):
        """Checks if ATWhiteLight and ATMonochromator are ENABLED

        Raises
        ------
        RunTimeError:
            If either component is not ENABLED"""

        comps = [self.laser]

        for comp in comps:
            summary_state = await comp.evt_summaryState.aget()
            if salobj.State(summary_state.summaryState) != salobj.State(
                salobj.State.ENABLED
            ):
                raise RuntimeError(f"{comp} is not ENABLED")

