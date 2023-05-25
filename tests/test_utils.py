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

import pathlib
import unittest

import pytest

from lsst.ts import standardscripts


class TestUtils(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
