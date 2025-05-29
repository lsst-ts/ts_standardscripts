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

__all__ = ["Enable"]

import types
import typing

import yaml
from lsst.ts import salobj
from lsst.ts.xml.enums.Scheduler import SalIndex

from .set_desired_state import SetDesiredState


class Enable(SetDesiredState):
    """A base script that implements enable functionality for the Scheduler.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.
    scheduler_index : `int`
        Index of the Scheduler to enable.
    """

    def __init__(self, index: int, scheduler_index: SalIndex) -> None:
        super().__init__(
            index=index,
            descr=f"Enable {scheduler_index.name} Scheduler",
            scheduler_index=scheduler_index,
            desired_state=salobj.State.ENABLED,
        )

    @classmethod
    def get_schema(cls) -> typing.Optional[typing.Dict[str, typing.Any]]:
        return yaml.safe_load(
            """
$schema: http://json-schema.org/draft-07/schema#
$id: https://github.com/lsst-ts/ts_standardscripts/scheduler/base_enable.py
title: BaseEnable v1
description: Configuration for enable scheduler.
type: object
properties:
    config:
        description: Scheduler configuration.
        type: string
required:
    - config
additionalProperties: false
        """
        )

    async def configure(self, config: types.SimpleNamespace) -> None:
        """Configure the script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration.
        """

        self.log.info(f"Scheduler configuration: {config.config}")

        self.configuration = config.config
