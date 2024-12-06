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

__all__ = ["SetDOF"]

import os

import numpy as np
import yaml
from astropy.time import Time, TimeDelta
from lsst_efd_client import EfdClient

from .apply_dof import ApplyDOF

STD_TIMEOUT = 30

EFD_NAMES = dict(
    tucson="tucson_teststand_efd",
    base="base_efd",
    summit="summit_efd",
)


class SetDOF(ApplyDOF):
    """Set absolute positions DOF to the main telescope, either bending
    mode or hexapod position.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**
    "Setting DOF..." - The DOF absolute position is being applied.

    """

    def __init__(self, index):
        super().__init__(index=index)

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/maintel/SetDOF.yaml
            title: SetDOF v1
            description: Configuration for SetDOF.
            type: object
            properties:
              day:
                description: Day obs to be used for synchronizing the state.
                type: number
                default: null
              seq:
                description: Sequence number to be used for synchronizing the state.
                type: number
                default: null
            anyOf:
                - required:
                    - day
                    - seq
                - required:
                    - dofs
            additionalProperties: false
        """
        schema_dict = yaml.safe_load(schema_yaml)

        base_schema_dict = super(ApplyDOF, cls).get_schema()

        for prop in base_schema_dict["properties"]:
            schema_dict["properties"][prop] = base_schema_dict["properties"][prop]

        return schema_dict

    async def configure(self, config) -> None:
        """Configure script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Script configuration, as defined by `schema`.
        """
        super(ApplyDOF, self).configure(config)

        self.day = getattr(config, "day", None)
        self.seq = getattr(config, "seq", None)

    async def get_image_time(self, client, day, seq):
        """Get the image time from the given day and sequence number.

        Parameters
        ----------
        day : `int`
            Day obs to be used for synchronizing the state.
        seq : `int`
            Sequence number to be used for synchronizing the state.

        Returns
        -------
        end_time : `astropy.time.Time`
            End time of the image.

        Raises
        ------
        RuntimeError
            Error querying time for image {day}:{seq}.
        """
        try:
            query = f"""
                SELECT  "imageDate", "imageNumber"
                FROM "efd"."autogen"."lsst.sal.CCCamera.logevent_endReadout"
                WHERE imageDate =~ /{day}/ AND imageNumber = {seq}
            """
            end_time = await client.influx_client.query(query)
            return Time(end_time.iloc[0].name)
        except Exception:
            raise RuntimeError(f"Error querying time for image {day}:{seq}.")

    async def get_last_issued_state(self):
        """Get the state from the given day and sequence number.

        Returns
        -------
        state : `dict`
            State of the system.
        """

        client = await self.get_efd_client()
        end_time = self.get_image_time(client, self.day, self.seq)

        topics = [f"aggregatedDoF{i}" for i in range(50)]
        lookback_interval = TimeDelta(1, format="jd")
        state = await client.select_time_series(
            "lsst.sal.MTAOS.logevent_degreeOfFreedom",
            topics,
            end_time - lookback_interval,
            end_time,
        )

        if not state.empty:
            state = state.iloc[[-1]]
            return state.values.squeeze()
        else:
            self.log.warning("No state found.")
            return np.zeros(50)

    async def get_efd_client(self) -> str:
        """Get the EFD name.

        Returns
        -------
        EfdClient
            Client instance to query the EFD.

        Raises
        ------
        RuntimeError
            Wrong EFd name
        """
        site = os.environ.get("LSST_SITE")
        if site is None or site not in EFD_NAMES:
            message = (
                "LSST_SITE environment variable not defined"
                if site is None
                else (f"No image server url for {site=}.")
            )
            raise RuntimeError("Wrong EFD name: " + message)
        else:
            return EfdClient(EFD_NAMES[site])

    async def run(self) -> None:
        """Run script.

        Raises
        ------
        RuntimeError
            Unable to connect to EFD.
        """
        # Assert feasibility
        await self.assert_feasibility()

        if self.day is not None and self.seq is not None:
            self.dofs = await self.get_last_issued_state()

        await self.checkpoint("Setting DOF...")
        current_dof = await self.mtcs.rem.mtaos.evt_degreeOfFreedom.aget(
            timeout=STD_TIMEOUT
        )
        dof_data = self.mtcs.rem.mtaos.cmd_offsetDOF.DataType()
        for i, dof_absolute in enumerate(self.dofs):
            dof_data.value[i] = dof_absolute - current_dof.aggregatedDoF[i]
        await self.mtcs.rem.mtaos.cmd_offsetDOF.start(data=dof_data)
