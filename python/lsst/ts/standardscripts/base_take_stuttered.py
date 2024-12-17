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

__all__ = ["BaseTakeStuttered"]

import abc

import yaml
from lsst.ts import salobj


class BaseTakeStuttered(salobj.BaseScript, metaclass=abc.ABCMeta):
    """Base class for take stuttered images script.

    Parameters
    ----------
    index : `int`
        SAL index of this Script

    Notes
    -----
    **Checkpoints**

    * exposure {n} of {m}: before sending the ``takeImages`` command
    """

    def __init__(self, index, descr):
        super().__init__(index=index, descr=descr)

        self.config = None

        self.instrument_setup_time = 0.0

    @property
    @abc.abstractmethod
    def camera(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def get_instrument_configuration(self):
        """Get instrument configuration.

        Returns
        -------
        instrument_configuration: `dict`
            Dictionary with instrument configuration.
        """
        raise NotImplementedError()

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/base_take_stuttered.py
            title: BaseTakeImage v2
            description: Configuration for BaseTakeImage.
            type: object
            properties:
              n_images:
                description: The number of images to take.
                minimum: 0
                type: integer
                default: 1
              n_shift:
                description: Number of shift-expose sequences.
                minimum: 1
                type: integer
                default: 20
              row_shift:
                description: How many rows to shift at each sequence.
                minimum: 1
                type: integer
                default: 100
              change_focus:
                description: Whether or not to change focus between shifts.
                minimum: 0
                type: boolean
                default: False
              focus_step:
                description: Amount to shift focus if shift_focus is True.
                minimum: 0
                type: number
                default: 0.025
              exp_time:
                description: The exposure time (sec).
                type: number
                minimum: 0
              reason:
                description: Optional reason for taking the data.
                type: string
              program:
                description: Name of the program this data belongs to, e.g. WFD, DD, etc.
                type: string
              note:
                description: A descriptive note about the image being taken.
                type: string
            required: [exp_time]
            additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        """Configure script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Script configuration, as defined by `schema`.
        """
        self.config = config

    def set_metadata(self, metadata):
        metadata.duration = self.instrument_setup_time + (
            self.config.n_shift
            * self.config.row_shift
            * self.config.n_images
            * self.config.exp_time
        )
    async def offset_hexapod(self, msg):
        await self.checkpoint(msg)
        await self.atcs.rem.ataos.cmd_offset.set_start(z=self.config.focus_step)

    async def run(self):
        note = getattr(self.config, "note", None)
        reason = getattr(self.config, "reason", None)
        program = getattr(self.config, "program", None)

        await self.checkpoint("setup instrument")
        await self.camera.setup_instrument(**self.get_instrument_configuration())

        await self.checkpoint("Take stuttered")
        if self.config.change_focus:
            # Change moveWhileWhileExposing parameter to allow hexapod
            # to move while shutter is open
            await self.atcs.rem.ataos.cmd_disableCorrection.set_start(hexapod=True)
            await atcs.rem.ataos.cmd_enableCorrection.set_start(hexapod=True, moveWhileExposing=True)

        if self.config.change_focus:
            checkpoint=self.offset_hexapod
        else:
            checkpoint=None

        await self.camera.take_stuttered(
            exptime=self.config.exp_time,
            n_shift=self.config.n_shift,
            row_shift=self.config.row_shift,
            n=self.config.n_images,
            checkpoint=checkpoint,
            reason=reason,
            program=program,
            group_id=self.group_id,
            note=note,
        )
        if self.config.change_focus:
            # Put moveWhileExposing back to False
            await self.atcs.rem.ataos.cmd_disableCorrection.set_start(hexapod=True)
            await atcs.rem.ataos.cmd_enableCorrection.set_start(hexapod=True, moveWhileExposing=False)
