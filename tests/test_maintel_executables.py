#!/usr/bin/env python
# This file is part of ts_maintel_standardscripts.
#
# Developed for the Vera C. Rubin Observatory Telescope and Site Systems.
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

import unittest

from lsst.ts import standardscripts
from lsst.ts.standardscripts import get_scripts_dir


class TestExecutables(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    def setUp(self) -> None:
        self.scripts_dir = get_scripts_dir() / "maintel"
        return super().setUp()

    async def basic_make_script(self, script_path):
        yield

    async def test_apply_dof(self):
        script_path = self.scripts_dir / "apply_dof.py"
        await self.check_executable(script_path)

    async def test_change_filter_lsstcam(self):
        script_path = self.scripts_dir / "change_filter_lsstcam.py"
        await self.check_executable(script_path)

    async def test_close_loop_lsstcam(self):
        script_path = self.scripts_dir / "close_loop_lsstcam.py"
        await self.check_executable(script_path)

    async def test_close_loop_comcam(self):
        script_path = self.scripts_dir / "close_loop_comcam.py"
        await self.check_executable(script_path)

    async def test_close_mirror_covers(self):
        script_path = self.scripts_dir / "close_mirror_covers.py"
        await self.check_executable(script_path)

    async def test_csc_end_of_night(self):
        script_path = self.scripts_dir / "csc_end_of_night.py"
        await self.check_executable(script_path)

    async def test_disable_aos_closed_loop(self):
        script_path = self.scripts_dir / "disable_aos_closed_loop.py"
        await self.check_executable(script_path)

    async def test_disable_dome_following(self):
        script_path = self.scripts_dir / "mtdome" / "disable_dome_following.py"
        await self.check_executable(script_path)

    async def test_disable_hexapod_compensation_mode(self):
        script_path = self.scripts_dir / "disable_hexapod_compensation_mode.py"
        await self.check_executable(script_path)

    async def test_disable_m1m3_balance_system(self):
        script_path = self.scripts_dir / "m1m3" / "disable_m1m3_balance_system.py"
        await self.check_executable(script_path)

    async def test_enable_aos_closed_loop(self):
        script_path = self.scripts_dir / "enable_aos_closed_loop.py"
        await self.check_executable(script_path)

    async def test_enable_comcam(self):
        script_path = self.scripts_dir / "enable_comcam.py"
        await self.check_executable(script_path)

    async def test_enable_dome_following(self):
        script_path = self.scripts_dir / "mtdome" / "enable_dome_following.py"
        await self.check_executable(script_path)

    async def test_enable_hexapod_compensation_mode(self):
        script_path = self.scripts_dir / "enable_hexapod_compensation_mode.py"
        await self.check_executable(script_path)

    async def test_enable_m1m3_balance_system(self):
        script_path = self.scripts_dir / "m1m3" / "enable_m1m3_balance_system.py"
        await self.check_executable(script_path)

    async def test_enable_mtcs(self):
        script_path = self.scripts_dir / "enable_mtcs.py"
        await self.check_executable(script_path)

    async def test_focus_sweep_comcam(self):
        script_path = self.scripts_dir / "focus_sweep_comcam.py"
        await self.check_executable(script_path)

    async def test_focus_sweep_lsstcam(self):
        script_path = self.scripts_dir / "focus_sweep_lsstcam.py"
        await self.check_executable(script_path)

    async def test_home_both_axes(self):
        script_path = self.scripts_dir / "home_both_axes.py"
        await self.check_executable(script_path)

    async def test_lasertracker_align(self):
        script_path = self.scripts_dir / "laser_tracker" / "align.py"
        await self.check_executable(script_path)

    async def test_lasertracker_measure(self):
        script_path = self.scripts_dir / "laser_tracker" / "measure.py"
        await self.check_executable(script_path)

    async def test_lasertracker_set_up(self):
        script_path = self.scripts_dir / "laser_tracker" / "set_up.py"
        await self.check_executable(script_path)

    async def test_lasertracker_shut_down(self):
        script_path = self.scripts_dir / "laser_tracker" / "shut_down.py"
        await self.check_executable(script_path)

    async def test_lower_m1m3(self):
        script_path = self.scripts_dir / "m1m3" / "lower_m1m3.py"
        await self.check_executable(script_path)

    async def test_m1m3_check_actuators(self):
        script_path = self.scripts_dir / "m1m3" / "check_actuators.py"
        await self.check_executable(script_path)

    async def test_m1m3_check_hardpoint(self):
        script_path = self.scripts_dir / "m1m3" / "check_hardpoint.py"
        await self.check_executable(script_path)

    async def test_m1m3_enable_m1m3_controller_flags(self):
        script_path = self.scripts_dir / "m1m3" / "enable_m1m3_slew_controller_flags.py"
        await self.check_executable(script_path)

    async def test_m2_check_actuators(self):
        script_path = self.scripts_dir / "m2" / "check_actuators.py"
        await self.check_executable(script_path)

    async def test_m2_disable_closed_loop(self):
        script_path = self.scripts_dir / "m2" / "disable_m2_closed_loop.py"
        await self.check_executable(script_path)

    async def test_m2_enable_closed_loop(self):
        script_path = self.scripts_dir / "m2" / "enable_m2_closed_loop.py"
        await self.check_executable(script_path)

    async def test_move_p2p(self):
        script_path = self.scripts_dir / "move_p2p.py"
        await self.check_executable(script_path)

    async def test_mtdome_close_dome(self):
        script_path = self.scripts_dir / "mtdome" / "close_dome.py"
        await self.check_executable(script_path)

    async def test_mtdome_crawl_az(self):
        script_path = self.scripts_dir / "mtdome" / "crawl_az.py"
        await self.check_executable(script_path)

    async def test_mtdome_home_dome(self):
        script_path = self.scripts_dir / "mtdome" / "home_dome.py"
        await self.check_executable(script_path)

    async def test_mtdome_open_dome(self):
        script_path = self.scripts_dir / "mtdome" / "open_dome.py"
        await self.check_executable(script_path)

    async def test_mtdome_slew_dome(self):
        script_path = self.scripts_dir / "mtdome" / "slew_dome.py"
        await self.check_executable(script_path)

    async def test_mtmount_park_mount(self):
        script_path = self.scripts_dir / "mtmount" / "park_mount.py"
        await self.check_executable(script_path)

    async def test_mtmount_unpark_mount(self):
        script_path = self.scripts_dir / "mtmount" / "unpark_mount.py"
        await self.check_executable(script_path)

    async def test_mtrotator_move_rotator(self):
        script_path = self.scripts_dir / "mtrotator" / "move_rotator.py"
        await self.check_executable(script_path)

    async def test_offline_comcam(self):
        script_path = self.scripts_dir / "offline_comcam.py"
        await self.check_executable(script_path)

    async def test_offline_mtcs(self):
        script_path = self.scripts_dir / "offline_mtcs.py"
        await self.check_executable(script_path)

    async def test_offset_camera_hexapod(self):
        script_path = self.scripts_dir / "offset_camera_hexapod.py"
        await self.check_executable(script_path)

    async def test_offset_m2_hexapod(self):
        script_path = self.scripts_dir / "offset_m2_hexapod.py"
        await self.check_executable(script_path)

    async def test_offset_mtcs(self):
        script_path = self.scripts_dir / "offset_mtcs.py"
        await self.check_executable(script_path)

    async def test_open_mirror_covers(self):
        script_path = self.scripts_dir / "open_mirror_covers.py"
        await self.check_executable(script_path)

    async def test_park_dome(self):
        script_path = self.scripts_dir / "mtdome" / "park_dome.py"
        await self.check_executable(script_path)

    async def test_point_azel(self):
        script_path = self.scripts_dir / "point_azel.py"
        await self.check_executable(script_path)

    async def test_power_off_tunablelaser(self):
        script_path = self.scripts_dir / "calibration" / "power_off_tunablelaser.py"
        await self.check_executable(script_path)

    async def test_power_on_tunablelaser(self):
        script_path = self.scripts_dir / "calibration" / "power_on_tunablelaser.py"
        await self.check_executable(script_path)

    async def test_prepare_for_align(self):
        script_path = self.scripts_dir / "prepare_for" / "align.py"
        await self.check_executable(script_path)

    async def test_raise_m1m3(self):
        script_path = self.scripts_dir / "m1m3" / "raise_m1m3.py"
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

    async def test_set_dof(self):
        script_path = self.scripts_dir / "set_dof.py"
        await self.check_executable(script_path)

    async def test_setup_mtcs(self):
        script_path = self.scripts_dir / "setup_mtcs.py"
        await self.check_executable(script_path)

    async def test_standby_comcam(self):
        script_path = self.scripts_dir / "standby_comcam.py"
        await self.check_executable(script_path)

    async def test_standby_mtcs(self):
        script_path = self.scripts_dir / "standby_mtcs.py"
        await self.check_executable(script_path)

    async def test_stop(self):
        script_path = self.scripts_dir / "stop.py"
        await self.check_executable(script_path)

    async def test_stop_rotator(self):
        script_path = self.scripts_dir / "stop_rotator.py"
        await self.check_executable(script_path)

    async def test_stop_tracking(self):
        script_path = self.scripts_dir / "stop_tracking.py"
        await self.check_executable(script_path)

    async def test_take_aos_sequence_comcam(self):
        script_path = self.scripts_dir / "take_aos_sequence_comcam.py"
        await self.check_executable(script_path)

    async def test_take_aos_sequence_lsstcam(self):
        script_path = self.scripts_dir / "take_aos_sequence_lsstcam.py"
        await self.check_executable(script_path)

    async def test_take_image_anycam(self):
        script_path = self.scripts_dir / "take_image_anycam.py"
        await self.check_executable(script_path)

    async def test_take_image_comcam(self):
        script_path = self.scripts_dir / "take_image_comcam.py"
        await self.check_executable(script_path)

    async def test_take_stuttered_comcam(self):
        script_path = self.scripts_dir / "take_stuttered_comcam.py"
        await self.check_executable(script_path)

    async def test_take_stuttered_lsstcam(self):
        script_path = self.scripts_dir / "take_stuttered_lsstcam.py"
        await self.check_executable(script_path)

    async def test_track_target(self):
        script_path = self.scripts_dir / "track_target.py"
        await self.check_executable(script_path)

    async def test_track_target_and_take_image_comcam(self):
        script_path = self.scripts_dir / "track_target_and_take_image_comcam.py"
        await self.check_executable(script_path)

    async def test_track_target_and_take_image_gencam(self):
        script_path = self.scripts_dir / "track_target_and_take_image_gencam.py"
        await self.check_executable(script_path)

    async def test_unpark_dome(self):
        script_path = self.scripts_dir / "mtdome" / "unpark_dome.py"
        await self.check_executable(script_path)
