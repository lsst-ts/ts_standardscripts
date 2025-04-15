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
from lsst.ts.standardscripts.base_track_target_and_take_image import (
    BaseTrackTargetAndTakeImage,
)


class GenericTrackTargetAndTakeImage(BaseTrackTargetAndTakeImage):
    """
    This script implements the essential interface needed by the
    core tests, such as `configure`
    """

    def __init__(self, index=None):
        super().__init__(
            index=index, descr="Generic Track Target and Take Image script"
        )
        self.mtcs = None  # Will be mocked in the tests
        self.lsstcam = None  # Will be mocked in the tests
        self.instrument_name = "GenericCam"

    @property
    def tcs(self):
        return self.mtcs

    @property
    def camera(self):
        return self.lsstcam

    @classmethod
    def get_schema(cls):
        url = "https://github.com/"
        path = "lsst-ts/ts_standardscripts/tree/develop/tests/test_base_track_target_and_take_image.yaml"
        schema_dict = cls.get_base_schema()
        schema_dict["$id"] = f"{url}{path}"
        schema_dict["title"] = "GenericTrackTargetAndTakeImage v1"
        schema_dict["description"] = "Configuration for GenericTargetAndTakeImage."

        return schema_dict

    async def load_playlist(self):
        """Load playlist."""
        raise NotImplementedError()

    async def assert_feasibility(self):
        """Verify that the system is in a feasible state to execute the
        script.
        """
        raise NotImplementedError()

    async def track_target_and_setup_instrument(self):
        """slewing of telescope and setting up of instrument.

        Ideally this would be done in parallel to save time.
        """
        raise NotImplementedError()

    async def take_data(self):
        """Implement method to take data."""
        raise NotImplementedError()

    async def stop_tracking(self):
        """Implement method to stop tracking."""
        raise NotImplementedError()

    def get_instrument_name(self):
        """Get instrument name.

        Returns
        -------
        instrument_name: `string`
        """
        return self.instrument_name


class TestBaseTrackTargetAndTakeImage(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    """Test BaseTrackTargetAndTakeImage using the DummyBlockScript script."""

    async def basic_make_script(self, index):
        self.script = GenericTrackTargetAndTakeImage(index=index)
        self.script.mtcs = unittest.mock.AsyncMock()
        self.script.lsstcam = unittest.mock.AsyncMock()

        return (self.script,)

    async def test_configure_ignore(self):
        configuration_basic_with_ignore = dict(
            ra="10:00:00",
            dec="-10:00:00",
            rot_sky=0.0,
            name="unit_test_target",
            obs_time=7.0,
            num_exp=2,
            exp_times=[2.0, 1.0],
            band_filter="r",
            reason="Unit testing",
            program="UTEST",
            note="Note_utest",
            ignore=["mtm1m3", "mtrotator", "mtoods", "not-comp"],
        )

        async with self.make_script():
            await self.configure_script(**configuration_basic_with_ignore)
            # Verify ignoring components
            self.script.tcs.disable_checks_for_components.assert_called_once_with(
                components=configuration_basic_with_ignore["ignore"]
            )
