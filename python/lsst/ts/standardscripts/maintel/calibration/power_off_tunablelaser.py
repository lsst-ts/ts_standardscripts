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

__all__ = ["PowerOffTunableLaser"]


import yaml
from lsst.ts import salobj
from lsst.ts.observatory.control.maintel.mtcalsys import MTCalsys


class PowerOffTunableLaser(salobj.BaseScript):
    """Stope the propagation of the Tunable Laser for functional
    testing.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    """

    def __init__(self, index):
        super().__init__(
            index=index,
            descr="Power Off Tunable Laser",
        )

        self.laser = None
        self.mtcalsys = None

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/maintel/calibrations/power_on_tunablelaser.yaml
            title: PowerOffTunableLaser v1
            description: Configuration for PowerOffTunableLaser.
              Each attribute can be specified as a scalar or array.
              All arrays must have the same length (one item per image).
            type: object
            properties:
              sequence_name:
                description: Name of sequence in MTCalsys
                type: string
                default: laser_functional

            additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    def set_metadata(self, metadata):
        metadata.duration = 30

    async def configure(self, config):
        """Configure the script.

        Parameters
        ----------
        config : ``self.cmd_configure.DataType``

        """
        self.log.info("Configure started")
        if self.mtcalsys is None:
            self.log.debug("Creating MTCalSys.")
            self.mtcalsys = MTCalsys(domain=self.domain, log=self.log)
            await self.mtcalsys.start_task

        self.sequence_name = config.sequence_name
        self.mtcalsys.load_calibration_config_file()
        self.mtcalsys.assert_valid_configuration_option(name=self.sequence_name)

        self.config_data = self.mtcalsys.get_calibration_configuration(
            self.sequence_name
        )

        if self.laser is None:
            self.laser = salobj.Remote(
                domain=self.domain,
                name="TunableLaser",
            )

        self.laser.start_task

        self.log.info("Configure completed")

    async def run(self):
        """Run script."""
        await self.assert_components_enabled()

        await self.checkpoint("Configuring TunableLaser")

        params = await self.mtcalsys.get_laser_parameters()

        self.log.info(
            f"Laser Configuration is {params[0]}, \n"
            f"wavelength is {params[1]}, \n"
            f"Interlock is {params[2]}, \n"
            f"Burst mode is {params[3]}, \n"
            f"Cont. mode is {params[4]}"
        )

        await self.checkpoint("Stopping laser propagation")
        await self.start_propagation_off()

    async def start_propagation_off(self):
        """Starts propagation of the laser"""

        await self.mtcalsys.laser_stop_propagate()

    async def assert_components_enabled(self):
        """Checks if TunableLaser is ENABLED

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
