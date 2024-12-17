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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

__all__ = ["ATGetStdFlatDataset"]

import numpy as np
import yaml
from lsst.ts import salobj
from lsst.ts.observatory.control.auxtel import LATISS, LATISSUsages


class ATGetStdFlatDataset(salobj.BaseScript):
    """Implement script to get sensor characterization data.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    The definition is spelled out in https://jira.lsstcorp.org/browse/CAP-203
    and https://jira.lsstcorp.org/browse/CAP-206.

    This script does the following:

    - Take a set of dark images (shutter closed).
    - Take a set of bias images.
    - Take a sequence of flat field iamges, as follows:

        - Take a set of pairs of flat fields at a set of approximately
          logarithmically spaced intensity levels starting at 500 DN
          and increasing by a factor of 2 (i.e. 500, 1000, 2000, ...).
          The exact levels are not important, but they must be well known;
          both the flux level and shutter time must be well measured
          (if shutter is opened before and closed after the lamp is turned on
          then the shutter time need not be well measured).
    - Take another set of bias images.
    """

    def __init__(self, index):
        super().__init__(
            index=index, descr="Take Flat field sensor characterization data."
        )

        self.latiss = LATISS(self.domain, intended_usage=LATISSUsages.TakeImageFull)

        self.read_out_time = self.latiss.read_out_time
        self.cmd_timeout = 30.0
        self.end_readout_timeout = 120.0

        # FIXME: Get this parameter from the camera configuration once late
        # joiner is working on the open network.
        self.maximum_exp_time = 401.0  # Maximum exposure time in seconds.

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/auxtel/ATGetStdFlatDataset.yaml
            title: ATGetStdFlatDataset v1
            description: Configuration for ATGetStdFlatDataset
            type: object
            properties:
              n_dark:
                description: Number of dark images.
                type: integer
                default: 10
                minimum: 1
              t_dark:
                description: Exposure time for each dark image (sec).
                type: number
                default: 400
                exclusiveMinimum: 0
              n_bias:
                description: Number of bias images.
                type: integer
                default: 10
                minimum: 1
              n_flat:
                description: Number of sets of flat images.
                type: integer
                default: 2
                minimum: 1
              flat_base_exptime:
                description: Base exposure time flat images (sec).
                type: number
                default: 0.5
                exclusiveMinimum: 0
              flat_dn_range:
                description: Multipliers for flat exposure time (sec).
                  Flat exposure times = flat_base_exptime * flat_dn_range.
                type: array
                items:
                    type: number
                    exclusiveMinimum: 0
                default: [1, 2, 4, 8, 16, 32, 64, 128]
              filter:
                description: ATSpectrograph filter name or ID. Omit to leave unchanged.
                anyOf:
                  - type: string
                  - type: integer
                    minimum: 1
                  - type: "null"
                default: null
              grating:
                description: ATSpectrograph grating name or ID. Omit to leave unchanged.
                anyOf:
                  - type: string
                  - type: integer
                    minimum: 1
                  - type: "null"
                default: null
              linear_stage:
                description: Position of ATSpectrograph linear stage. Omit to leave unchanged.
                anyOf:
                  - type: number
                  - type: "null"
                default: null
              read_out_time:
                description: Approximate readout time of camera (sec).
                  Used to estimate script duration.
                type: number
                default: 2
                exclusiveMinimum: 0
            required:
              - n_dark
              - t_dark
              - n_bias
              - n_flat
              - flat_base_exptime
              - flat_dn_range
              - filter
              - grating
              - linear_stage
              - read_out_time
            additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        """Configure the script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Script configuration, as defined by `schema`.
        """
        self.config = config
        self.flat_exp_times = self.config.flat_base_exptime * np.array(
            self.config.flat_dn_range, dtype=float
        )

        max_flat_time = self.flat_exp_times.max()
        if max_flat_time > self.maximum_exp_time:
            raise ValueError(
                f"Maximum flat time = {max_flat_time:0.2f} > "
                f"maximum allowed={self.maximum_exp_time} (sec)"
            )

    async def run(self):
        """Run the script."""
        self.log.info(f"Taking {self.config.n_bias} pre-flat bias images...")
        await self.latiss.take_bias(
            nbias=self.config.n_bias,
            checkpoint=self.checkpoint,
            group_id=self.group_id,
        )

        self.log.info(f"Taking {self.config.n_flat} flat-field images")
        for flat_exp_time in self.flat_exp_times:
            await self.latiss.take_flats(
                exptime=flat_exp_time,
                nflats=self.config.n_flat,
                filter=self.config.filter,
                grating=self.config.grating,
                linear_stage=self.config.linear_stage,
                checkpoint=self.checkpoint,
                group_id=self.group_id,
            )

        self.log.info(f"Taking {self.config.n_bias} post-flat bias images...")
        await self.latiss.take_bias(
            nbias=self.config.n_bias,
            checkpoint=self.checkpoint,
            group_id=self.group_id,
        )

        self.log.info(f"Taking {self.config.n_dark} dark images...")
        await self.latiss.take_darks(
            exptime=self.config.t_dark,
            ndarks=self.config.n_dark,
            checkpoint=self.checkpoint,
            group_id=self.group_id,
        )

        await self.checkpoint("done")

    def set_metadata(self, metadata):
        dark_time = self.config.n_dark * (self.read_out_time + self.config.t_dark)
        # Note, biases are taken twice: before flats and after flats
        bias_time = 2 * self.config.n_bias * self.read_out_time
        flat_time = self.config.n_flat * (
            self.read_out_time + self.flat_exp_times.mean()
        )
        metadata.duration = dark_time + bias_time + flat_time
