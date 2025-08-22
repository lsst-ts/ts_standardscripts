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

import unittest

from lsst.ts import standardscripts
from lsst.ts.standardscripts.base_take_image import BaseTakeImage


class GenericTakeImage(BaseTakeImage):
    """
    This script implements the essential interface needed by the
    core tests, such as `configure`
    """

    def __init__(self, index=None):
        super().__init__(index=index, descr="Generic Take Image script")
        self.mtcs = None  # Will be mocked in the tests
        self.lsstcam = None  # Will be mocked in the tests
        self.instrument_name = "GenericCam"

    @property
    def tcs(self):
        return self.mtcs

    @property
    def camera(self):
        return self.lsstcam

    def get_instrument_configuration(self):
        """Get instrument configuration.

        Returns
        -------
        instrument_configuration: `dict`
            Dictionary with instrument configuration.
        """
        return dict()

    def get_instrument_name(self):
        """Get instrument name.

        Returns
        -------
        instrument_name: `string`
        """
        return self.instrument_name

    @classmethod
    def get_schema(cls):
        url = "https://github.com/"
        path = "lsst-ts/ts_standardscripts/tree/develop/tests/test_base_take_image.yaml"
        schema_dict = super().get_schema()
        schema_dict["$id"] = f"{url}{path}"
        schema_dict["title"] = "GenericTakeImage v1"
        schema_dict["description"] = "Configuration for GenericTakeImage."

        return schema_dict


class TestBaseTakeImage(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    """Test BaseTakeImage using the GenericTakeImage script."""

    async def basic_make_script(self, index):
        self.script = GenericTakeImage(index=index)
        self.script.mtcs = unittest.mock.AsyncMock()
        self.script.lsstcam = unittest.mock.AsyncMock()
        self.script.lsstcam.read_out_time = 2.0  # Needed for set_metadata
        self.script.lsstcam.shutter_time = 1  # Needed for set_metadata

        return (self.script,)

    async def test_configure_ignore(self):
        configuration_basic_with_ignore = dict(
            visit_metadata=dict(
                ra="10:00:00",
                dec="-10:00:00",
                rot_sky=0.0,
            ),
            exp_times=[0, 2, 0.5],
            image_type="OBJECT",
            reason="Unit testing",
            program="UTEST",
            note="Note_utest",
            nimages=3,
            ignore=["mtm1m3", "mtrotator", "mtoods", "not-comp"],
        )

        async with self.make_script():
            await self.configure_script(**configuration_basic_with_ignore)
            # Verify ignoring components
            self.script.tcs.disable_checks_for_components.assert_called_once_with(
                components=configuration_basic_with_ignore["ignore"]
            )

    async def test_assert_feasibility_called(self):
        async with self.make_script():
            await self.configure_script(
                exp_times=0,
                image_type="BIAS",
                nimages=1,
            )

            # Mock camera interactions to allow run to proceed
            self.script.camera.setup_instrument = unittest.mock.AsyncMock()
            self.script.camera.take_imgtype = unittest.mock.AsyncMock()

            # Spy on feasibility hook
            self.script.assert_feasibility = unittest.mock.AsyncMock()

            await self.run_script()

            self.script.assert_feasibility.assert_awaited_once()

    async def test_assert_feasibility_failure(self):
        from lsst.ts.xml.enums import Script as ScriptEnums

        async with self.make_script():
            await self.configure_script(
                exp_times=0,
                image_type="BIAS",
                nimages=1,
            )

            # Mock camera interactions
            self.script.camera.setup_instrument = unittest.mock.AsyncMock()
            self.script.camera.take_imgtype = unittest.mock.AsyncMock()

            # Make feasibility fail
            self.script.assert_feasibility = unittest.mock.AsyncMock(
                side_effect=RuntimeError("Not feasible")
            )

            await self.run_script(expected_final_state=ScriptEnums.ScriptState.FAILED)
