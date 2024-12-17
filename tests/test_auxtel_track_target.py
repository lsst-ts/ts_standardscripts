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

import logging
import random
import unittest

from lsst.ts import standardscripts, utils
from lsst.ts.auxtel.standardscripts import TrackTarget, get_scripts_dir
from lsst.ts.xml.enums.MTPtg import Planets

random.seed(47)  # for set_random_lsst_dds_partition_prefix

logging.basicConfig()


class TestATTrackTarget(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    """Test Auxiliary Telescope track target script.

    Both AT and MT Slew scripts uses the same base script class. This unit
    test performs the basic checks on Script integrity. For a more detailed
    unit testing routine check the MT version.
    """

    async def basic_make_script(self, index):
        self.script = TrackTarget(index=index)

        return (self.script,)

    async def test_configure_with_slew_planet(self):
        async with self.make_script():
            self.script._atcs = unittest.mock.AsyncMock()
            self.script._atcs.start_task = utils.make_done_future()

            # Script can be configured with slew_planet
            await self.configure_script(slew_planet=dict(planet_name="PLUTO"))

    async def test_configure_with_slew_ephem(self):
        async with self.make_script():
            self.script._mtcs = unittest.mock.AsyncMock()
            self.script._mtcs.start_task = utils.make_done_future()

            # Script can be configured with slew_ephem
            await self.configure_script(
                slew_ephem=dict(ephem_file="filename.txt", object_name="Chariklo")
            )

    async def test_run_slew_target_name(self):
        async with self.make_script():
            self.script.tcs.slew_icrs = unittest.mock.AsyncMock()
            self.script.tcs.slew_object = unittest.mock.AsyncMock()
            self.script.tcs.stop_tracking = unittest.mock.AsyncMock()

            # Check running with target_name only
            await self.configure_script(target_name="eta Car")

            await self.run_script()

            self.assert_slew_target_name()

    async def test_run_slew_radec(self):
        async with self.make_script():
            self.script.tcs.slew_icrs = unittest.mock.AsyncMock()
            self.script.tcs.slew_object = unittest.mock.AsyncMock()
            self.script.tcs.stop_tracking = unittest.mock.AsyncMock()

            self.script.tcs.slew_object.reset_mock()
            self.script.tcs.slew_icrs.reset_mock()

            # Check running with ra dec only
            config = dict(slew_icrs=dict(ra=1.0, dec=-10.0))

            await self.configure_script(**config)

            await self.run_script()

            self.assert_slew_radec()

    async def test_run_slew_azel(self):
        async with self.make_script():
            self.script.tcs.slew_icrs = unittest.mock.AsyncMock()
            self.script.tcs.slew_object = unittest.mock.AsyncMock()
            self.script.tcs.find_target = unittest.mock.AsyncMock(
                return_value="eta Car"
            )
            self.script.tcs.stop_tracking = unittest.mock.AsyncMock()

            self.script.tcs.slew_object.reset_mock()
            self.script.tcs.slew_icrs.reset_mock()

            # Check running with ra dec only
            config = dict(find_target=dict(az=0.0, el=80.0, mag_limit=1.0))

            await self.configure_script(**config)

            await self.run_script()

            self.assert_slew_azel(find_target_config=config["find_target"])

    async def test_run_slew_planet(self):
        async with self.make_script():
            self.script.tcs.slew_to_planet = unittest.mock.AsyncMock()
            self.script.tcs.stop_tracking = unittest.mock.AsyncMock()

            # Get planet name
            planet_name = Planets["PLUTO"].name

            # Check running with planet name
            config = dict(slew_planet=dict(planet_name=planet_name))

            await self.configure_script(**config)

            await self.run_script()

            self.assert_slew_planet(planet_name)

    async def test_run_slew_ephem(self):
        async with self.make_script():
            self.script._atcs = unittest.mock.AsyncMock()
            self.script._atcs.start_task = utils.make_done_future()
            self.script.tcs.slew_ephem_target = unittest.mock.AsyncMock()
            self.script.tcs.stop_tracking = unittest.mock.AsyncMock()

            # Check running with ephem file
            config = dict(
                slew_ephem=dict(ephem_file="filename.txt", object_name="Chariklo")
            )

            await self.configure_script(**config)

            await self.run_script()

            self.assert_slew_ephem_target(
                ephem_file=config["slew_ephem"]["ephem_file"],
                object_name=config["slew_ephem"]["object_name"],
            )

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "track_target.py"
        await self.check_executable(script_path)

    def assert_slew_radec(self):
        self.script.tcs.slew_icrs.assert_awaited_once()
        self.script.tcs.slew_icrs.assert_awaited_with(
            ra=self.script.config.slew_icrs["ra"],
            dec=self.script.config.slew_icrs["dec"],
            rot=self.script.config.rot_value,
            rot_type=self.script.config.rot_type,
            target_name=getattr(self.script.config, "target_name", "slew_icrs"),
            dra=self.script.config.differential_tracking["dra"],
            ddec=self.script.config.differential_tracking["ddec"],
            offset_x=self.script.config.offset["x"],
            offset_y=self.script.config.offset["y"],
            az_wrap_strategy=self.script.config.az_wrap_strategy,
            time_on_target=self.script.config.track_for,
            slew_timeout=240.0,
        )
        self.script.tcs.slew_object.assert_not_awaited()
        self.script.tcs.stop_tracking.assert_not_awaited()

    def assert_slew_target_name(self):
        self.script.tcs.slew_object.assert_awaited_once()
        self.script.tcs.slew_object.assert_awaited_with(
            name="eta Car",
            rot=self.script.config.rot_value,
            rot_type=self.script.config.rot_type,
            dra=self.script.config.differential_tracking["dra"],
            ddec=self.script.config.differential_tracking["ddec"],
            offset_x=self.script.config.offset["x"],
            offset_y=self.script.config.offset["y"],
            az_wrap_strategy=self.script.config.az_wrap_strategy,
            time_on_target=self.script.config.track_for,
            slew_timeout=240.0,
        )
        self.script.tcs.slew_icrs.assert_not_awaited()
        self.script.tcs.stop_tracking.assert_not_awaited()

    def assert_slew_azel(self, find_target_config):
        self.script.tcs.find_target.assert_awaited_once()
        self.script.tcs.find_target.assert_awaited_with(**find_target_config)
        self.assert_slew_target_name()

    def assert_slew_planet(self, planet_name):
        planet_enum = Planets[planet_name]
        self.script.tcs.slew_to_planet.assert_awaited_once()
        self.script.tcs.slew_to_planet.assert_awaited_with(
            planet=planet_enum,
            rot_sky=self.script.config.rot_value,
            slew_timeout=self.script.config.slew_timeout,
        )
        self.script.tcs.stop_tracking.assert_not_awaited()

    def assert_slew_ephem_target(self, ephem_file, object_name):
        self.script.tcs.slew_ephem_target.assert_awaited_once()
        self.script.tcs.slew_ephem_target.assert_awaited_with(
            ephem_file=ephem_file,
            target_name=object_name,
            rot_sky=self.script.config.rot_value,
            slew_timeout=self.script.config.slew_timeout,
        )

        self.script.tcs.stop_tracking.assert_not_awaited()

    def assert_config(self, config, config_validated):
        pass


if __name__ == "__main__":
    unittest.main()
