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

import unittest
from unittest.mock import AsyncMock, Mock, patch

from lsst.ts import standardscripts
from lsst.ts.auxtel.standardscripts import get_scripts_dir
from lsst.ts.auxtel.standardscripts.prepare_for import PrepareForVent


class TestPrepareForOnSky(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = PrepareForVent(index=index, remotes=False)

        return (self.script,)

    async def test_config(self):
        async with self.make_script():
            config = dict()
            await self.configure_script(**config)
            assert self.script.config.end_at_sun_elevation == 0

            config = dict(end_at_sun_elevation=10.0)
            await self.configure_script(**config)
            assert (
                self.script.config.end_at_sun_elevation
                == config["end_at_sun_elevation"]
            )

    async def test_assert_vent_feasibility(self):
        expected_feasibility = [
            False,
            True,
            True,
            True,
            True,
            True,
            True,
            True,
            True,
            True,
            False,
            False,
        ]
        sun_azel_sample = [
            (116.51, 0.59),
            (107.35, 16.61),
            (99.06, 33.42),
            (90.18, 50.61),
            (76.71, 67.76),
            (24.81, 82.10),
            (292.31, 73.68),
            (273.66, 56.82),
            (263.92, 39.58),
            (255.63, 22.60),
            (245.19, 3.38),
            (243.40, 0.55),
        ]

        async with self.make_script():
            for feasibility, sun_azel in zip(expected_feasibility, sun_azel_sample):
                with self.subTest(feasibility=feasibility, sun_azel=sun_azel):
                    if feasibility:
                        self.script.assert_vent_feasibility(*sun_azel)
                    else:
                        with self.assertRaisesRegex(
                            RuntimeError, "Vent constraints not met."
                        ):
                            self.script.assert_vent_feasibility(*sun_azel)

    async def test_estimate_duration(self):
        async with self.make_script():
            duration = self.script.estimate_duration()
            assert duration > 0

    @patch.multiple(
        PrepareForVent,
        get_sun_azel=Mock(
            side_effect=[
                (255.63, 22.60),
                (245.19, 3.38),
                (243.40, -0.55),
            ]
        ),
        prepare_for_vent=AsyncMock(),
        reposition_telescope_and_dome=AsyncMock(),
    )
    async def test_run(self):
        async with self.make_script():
            await self.configure_script()
            self.script.track_sun_sleep_time = 0.5
            await self.run_script()

            self.script.get_sun_azel.assert_called()
            self.script.prepare_for_vent.assert_awaited()
            self.script.reposition_telescope_and_dome.assert_awaited()

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "prepare_for" / "vent.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
