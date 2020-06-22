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

# import pathlib
import unittest

from lsst.ts import standardscripts


class TestUtils(unittest.TestCase):
    def test_get_scripts_dir(self):
        scripts_dir = standardscripts.get_scripts_dir()
        print(f"*** script dir: {scripts_dir}")
        self.assertTrue(scripts_dir.is_dir())

        # This does not work when doing pip install or conda build
        # pkg_path = pathlib.Path(__file__).resolve().parent.parent
        # predicted_path = pkg_path / "scripts"
        # print(f"*** predicted path: {predicted_path}")
        # self.assertTrue(scripts_dir.samefile(predicted_path))


if __name__ == "__main__":
    unittest.main()
