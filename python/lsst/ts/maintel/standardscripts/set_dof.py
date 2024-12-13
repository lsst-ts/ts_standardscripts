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

from .apply_dof import ApplyDOF

STD_TIMEOUT = 30


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

    async def run(self) -> None:
        """Run script."""
        # Assert feasibility
        await self.assert_feasibility()

        await self.checkpoint("Setting DOF...")
        current_dof = await self.mtcs.rem.mtaos.evt_degreeOfFreedom.aget(
            timeout=STD_TIMEOUT
        )
        dof_data = self.mtcs.rem.mtaos.cmd_offsetDOF.DataType()
        for i, dof_absolute in enumerate(self.dofs):
            dof_data.value[i] = dof_absolute - current_dof.aggregatedDoF[i]
        await self.mtcs.rem.mtaos.cmd_offsetDOF.start(data=dof_data)
