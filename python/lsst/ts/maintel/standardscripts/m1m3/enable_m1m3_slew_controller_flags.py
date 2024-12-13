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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

__all__ = ["EnableM1M3SlewControllerFlags"]


import yaml
from lsst.ts.observatory.control.maintel import MTCS
from lsst.ts.salobj import type_hints
from lsst.ts.standardscripts.base_block_script import BaseBlockScript
from lsst.ts.xml.enums import MTM1M3


class EnableM1M3SlewControllerFlags(BaseBlockScript):
    """Set M1M3 Slew Controller Settings for the main telescope.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.
    flag_names : `list`[`str`]
        List of M1M3 slew controller flags names to change.
    enable : `list`[`bool`]
        Corresponding booleans to enable or disable each flag.

    Returns
    -------
    `list`[`MTM1M3.SetSlewControllerSettings`]
        List of enum values associated with the flag names.
    """

    def __init__(self, index: int) -> None:
        super().__init__(
            index, descr="Set M1M3 Slew Controller Settings for the main telescope."
        )
        self.mtcs = None
        self.config = None

    async def configure_tcs(self) -> None:
        """Handle creating MTCS object and waiting for remote to start."""
        if self.mtcs is None:
            self.log.debug("Creating MTCS.")
            self.mtcs = MTCS(domain=self.domain, log=self.log)
            await self.mtcs.start_task
        else:
            self.log.debug("MTCS already defined, skipping.")

    @classmethod
    def get_schema(cls):
        schema_yaml = """
        $schema: http://json-schema.org/draft-07/schema#
        $id: https://github.com/lsst-ts/ts_standardscripts/EnableM1M3SlewControllerFlags/v1
        title: EnableM1M3SlewControllerFlags v1
        description: Configuration for EnableM1M3SlewControllerFlags script.
        type: object
        properties:
          slew_flags:
            description: >-
              List of M1M3 slew controller flags to change or "default" for a
              predefined combination of flags.
            oneOf:
              - type: string
                enum: ["default"]
              - type: array
                items:
                  type: string
                  enum: ["ACCELERATIONFORCES", "BALANCEFORCES", "VELOCITYFORCES", "BOOSTERVALVES"]
          enable:
            description: >-
              Corresponding booleans to enable or disable each flag. It will be
              [True, True, False, True] if the slew_flag is "default".
            type: array
            items:
              type: boolean
        required:
          - slew_flags
        """
        schema_dict = yaml.safe_load(schema_yaml)

        base_schema_dict = super().get_schema()

        for properties in base_schema_dict["properties"]:
            schema_dict["properties"][properties] = base_schema_dict["properties"][
                properties
            ]

        return schema_dict

    def set_metadata(self, metadata: type_hints.BaseMsgType) -> None:
        """Set script metadata."""

        # Estimate time per flag setting operation
        time_per_operation = 3.0  # Adjust this based on empirical data

        metadata.duration = time_per_operation * len(self.config.slew_flags)

    def get_default_slew_flags(self):
        """Return the default slew flags and enables.

        Returns
        -------
        `tuple`[`list`[`MTM1M3.SetSlewControllerSettings`], `list`[`bool`]]
            Default slew flags and enables.
        """
        default_flags = [
            MTM1M3.SetSlewControllerSettings.ACCELERATIONFORCES,
            MTM1M3.SetSlewControllerSettings.BALANCEFORCES,
            MTM1M3.SetSlewControllerSettings.VELOCITYFORCES,
            MTM1M3.SetSlewControllerSettings.BOOSTERVALVES,
        ]
        default_enables = [True, True, False, True]

        return default_flags, default_enables

    def convert_flag_names_to_enum(self, flag_names):
        """Convert flag names to enumeration values."""
        return [MTM1M3.SetSlewControllerSettings[flag_name] for flag_name in flag_names]

    async def configure(self, config):
        """Configure the script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration
        """
        self.config = config

        if self.config.slew_flags == "default":
            self.config.slew_flags, self.config.enable = self.get_default_slew_flags()
        else:
            if len(self.config.slew_flags) != len(self.config.enable):
                raise ValueError(
                    "slew_flags and enable arrays must have the same length."
                )
            # Convert flag names to enumeration values and
            # store them back in config
            self.config.slew_flags = self.convert_flag_names_to_enum(
                self.config.slew_flags
            )

        await self.configure_tcs()

        await super().configure(config=config)

    async def run_block(self):

        async with self.mtcs.m1m3_in_engineering_mode():
            for flag, enable in zip(self.config.slew_flags, self.config.enable):
                self.log.info(f"Setting m1m3 slew flag {flag.name} to {enable}.")
                await self.mtcs.set_m1m3_slew_controller_settings(flag, enable)
