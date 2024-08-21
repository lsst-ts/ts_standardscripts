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

import os
import pathlib
import unittest

import pytest
from lsst.ts import salobj, standardscripts
from lsst.ts.standardscripts.utils import find_running_instances


# class TestUtils(unittest.TestCase):
class TestUtils(
    unittest.IsolatedAsyncioTestCase
):  # Use IsolatedAsyncioTestCase for async tests

    @classmethod
    def setUpClass(cls) -> None:
        salobj.set_random_lsst_dds_partition_prefix()
        os.environ["LSST_SITE"] = "test"

    async def add_test_cscs(self, initial_state=salobj.State.STANDBY):
        """Add a Test controller"""
        if not hasattr(self, "mock_cscs"):
            self.mock_cscs = []
        index = len(self.mock_cscs) + 1  # Ensure indices are unique
        mock_csc = salobj.TestCsc(index=index, initial_state=initial_state)
        await mock_csc.start_task  # Start the controller asynchronously
        self.mock_cscs.append(mock_csc)

    def test_get_scripts_dir(self):
        scripts_dir = standardscripts.get_scripts_dir()
        print(f"*** script dir: {scripts_dir}")
        assert scripts_dir.is_dir()

        pkg_path = pathlib.Path(__file__).resolve().parent.parent
        predicted_path = (
            pkg_path / "python" / "lsst" / "ts" / "standardscripts" / "data" / "scripts"
        )
        print(f"*** predicted path: {predicted_path}")
        assert scripts_dir.samefile(predicted_path)

    def test_format_as_list(self):
        recurrences = 4
        # Check case of single values sent
        test_case = ["string", 2, 2.0]
        for test in test_case:
            new_list = standardscripts.utils.format_as_list(test, recurrences)
            print(new_list)
            assert new_list.count(test) == recurrences

        # Verify that if input is correct it just returns
        test_case = ["test", "test"]
        recurrences = 2
        new_list = standardscripts.utils.format_as_list(test_case, recurrences)
        assert new_list is test_case

        # Verify that it will fail if a list is provided with the wrong number
        # of occurrences
        with pytest.raises(ValueError):
            recurrences = 3
            new_list = standardscripts.utils.format_as_list(test_case, recurrences)

    async def test_find_running_instances(self):
        """Test find_running_instances utility function."""
        # Create multiple CSCs with same name but different states
        await self.add_test_cscs(initial_state=salobj.State.OFFLINE)
        await self.add_test_cscs(initial_state=salobj.State.STANDBY)
        await self.add_test_cscs(initial_state=salobj.State.STANDBY)
        await self.add_test_cscs(initial_state=salobj.State.DISABLED)
        await self.add_test_cscs(initial_state=salobj.State.ENABLED)

        # Note: Skip the OFFLINE CSC domain as it is not set. Hence,
        # mock_cscs[1], is skipped. Any valid domain would work.
        component, component_indices = await find_running_instances(
            self.mock_cscs[1].domain, "Test"
        )

        # Verify the results
        assert component == "Test"
        assert (
            len(component_indices) == 4
        )  # Note: An OFFLINE CSC doesn't have a remote, hence is not discoverable


if __name__ == "__main__":
    unittest.main()
