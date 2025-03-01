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

from lsst.ts import standardscripts
from lsst.ts.standardscripts import get_scripts_dir


class TestExecutables(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    def setUp(self) -> None:
        self.scripts_dir = get_scripts_dir() / "auxtel"
        return super().setUp()

    async def basic_make_script(self, index):
        yield

    async def test_atpneumatics_checkout(self):
        script_path = self.scripts_dir / "daytime_checkout" / "atpneumatics_checkout.py"
        await self.check_executable(script_path)

    async def test_calsys_takedata(self):
        script_path = self.scripts_dir / "calsys_takedata.py"
        await self.check_executable(script_path)

    async def test_close_dome(self):
        script_path = self.scripts_dir / "atdome" / "close_dome.py"
        await self.check_executable(script_path)

    async def test_close_dropout_door(self):
        script_path = self.scripts_dir / "atdome" / "close_dropout_door.py"
        await self.check_executable(script_path)

    async def test_detector_characterization_std_flat_dataset(self):
        script_path = (
            self.scripts_dir / "detector_characterization" / "get_std_flat_dataset.py"
        )
        await self.check_executable(script_path)

    async def test_disable_ataos_corrections(self):
        script_path = self.scripts_dir / "disable_ataos_corrections.py"
        await self.check_executable(script_path)

    async def test_disable_dome_following(self):
        script_path = self.scripts_dir / "atdome" / "disable_dome_following.py"
        await self.check_executable(script_path)

    async def test_enable_atcs(self):
        script_path = self.scripts_dir / "enable_atcs.py"
        await self.check_executable(script_path)

    async def test_enable_dome_following(self):
        script_path = self.scripts_dir / "atdome" / "enable_dome_following.py"
        await self.check_executable(script_path)

    async def test_enable_latiss(self):
        script_path = self.scripts_dir / "enable_latiss.py"
        await self.check_executable(script_path)

    async def test_focus_sweep_latiss(self):
        script_path = self.scripts_dir / "focus_sweep_latiss.py"
        await self.check_executable(script_path)

    async def test_home_dome(self):
        script_path = self.scripts_dir / "atdome" / "home_dome.py"
        await self.check_executable(script_path)

    async def test_latiss_checkout(self):
        script_path = self.scripts_dir / "daytime_checkout" / "latiss_checkout.py"
        await self.check_executable(script_path)

    async def test_offline_atcs(self):
        script_path = self.scripts_dir / "offline_atcs.py"
        await self.check_executable(script_path)

    async def test_offline_latiss(self):
        script_path = self.scripts_dir / "offline_latiss.py"
        await self.check_executable(script_path)

    async def test_open_dome(self):
        script_path = self.scripts_dir / "atdome" / "open_dome.py"
        await self.check_executable(script_path)

    async def test_open_dropout_door(self):
        script_path = self.scripts_dir / "atdome" / "open_dropout_door.py"
        await self.check_executable(script_path)

    async def test_point_azel(self):
        script_path = self.scripts_dir / "point_azel.py"
        await self.check_executable(script_path)

    async def test_power_off_atcalsys(self):
        script_path = self.scripts_dir / "calibrations" / "power_off_atcalsys.py"
        await self.check_executable(script_path)

    async def test_latiss_take_sequence(self):
        script_path = self.scripts_dir / "latiss_take_sequence.py"
        await self.check_executable(script_path)

    async def test_offset_ataos(self):
        script_path = self.scripts_dir / "offset_ataos.py"
        await self.check_executable(script_path)

    async def test_offset_atcs(self):
        script_path = self.scripts_dir / "offset_atcs.py"
        await self.check_executable(script_path)

    async def test_power_on_atcalsys(self):
        script_path = self.scripts_dir / "calibrations" / "power_on_atcalsys.py"
        await self.check_executable(script_path)

    async def test_prepare_for_co2_cleanup(self):
        script_path = self.scripts_dir / "prepare_for" / "co2_cleanup.py"
        await self.check_executable(script_path)

    async def test_prepare_for_flat(self):
        script_path = self.scripts_dir / "prepare_for" / "flat.py"
        await self.check_executable(script_path)

    async def test_prepare_for_onsky(self):
        script_path = self.scripts_dir / "prepare_for" / "onsky.py"
        await self.check_executable(script_path)

    async def test_prepare_for_vent(self):
        script_path = self.scripts_dir / "prepare_for" / "vent.py"
        await self.check_executable(script_path)

    async def test_run_calibration_sequence(self):
        script_path = self.scripts_dir / "calibrations" / "run_calibration_sequence.py"
        await self.check_executable(script_path)

    async def test_scheduler_add_block(self):
        script_path = self.scripts_dir / "scheduler" / "add_block.py"
        await self.check_executable(script_path)

    async def test_scheduler_enable(self):
        script_path = self.scripts_dir / "scheduler" / "enable.py"
        await self.check_executable(script_path)

    async def test_scheduler_load_snapshot(self):
        script_path = self.scripts_dir / "scheduler" / "load_snapshot.py"
        await self.check_executable(script_path)

    async def test_scheduler_resume(self):
        script_path = self.scripts_dir / "scheduler" / "resume.py"
        await self.check_executable(script_path)

    async def test_scheduler_standby(self):
        script_path = self.scripts_dir / "scheduler" / "standby.py"
        await self.check_executable(script_path)

    async def test_scheduler_stop(self):
        script_path = self.scripts_dir / "scheduler" / "stop.py"
        await self.check_executable(script_path)

    async def test_shutdown(self):
        script_path = self.scripts_dir / "shutdown.py"
        await self.check_executable(script_path)

    async def test_slew_and_take_image_checkout(self):
        script_path = (
            self.scripts_dir / "daytime_checkout" / "slew_and_take_image_checkout.py"
        )
        await self.check_executable(script_path)

    async def test_slew_dome(self):
        script_path = self.scripts_dir / "atdome" / "slew_dome.py"
        await self.check_executable(script_path)

    async def test_standby_atcs(self):
        script_path = self.scripts_dir / "standby_atcs.py"
        await self.check_executable(script_path)

    async def test_standby_latiss(self):
        script_path = self.scripts_dir / "standby_latiss.py"
        await self.check_executable(script_path)

    async def test_startup(self):
        script_path = self.scripts_dir / "prepare_for" / "onsky.py"
        await self.check_executable(script_path)

    async def test_stop(self):
        script_path = self.scripts_dir / "stop.py"
        await self.check_executable(script_path)

    async def test_stop_tracking(self):
        script_path = self.scripts_dir / "stop_tracking.py"
        await self.check_executable(script_path)

    async def test_take_image_latiss(self):
        script_path = self.scripts_dir / "take_image_latiss.py"
        await self.check_executable(script_path)

    async def test_take_stuttered_latiss(self):
        script_path = self.scripts_dir / "take_stuttered_latiss.py"
        await self.check_executable(script_path)

    async def test_telescope_and_dome_checkout(self):
        script_path = (
            self.scripts_dir / "daytime_checkout" / "telescope_and_dome_checkout.py"
        )
        await self.check_executable(script_path)

    async def test_track_target(self):
        script_path = self.scripts_dir / "track_target.py"
        await self.check_executable(script_path)

    async def test_track_target_and_take_image(self):
        script_path = self.scripts_dir / "track_target_and_take_image.py"
        await self.check_executable(script_path)

    async def test_enable_ataos_corrections(self):
        script_path = self.scripts_dir / "enable_ataos_corrections.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
