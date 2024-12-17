# This file is part of ts_maintel_standardscripts
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

import contextlib
import unittest

import pytest
from lsst.ts import salobj, standardscripts
from lsst.ts.maintel.standardscripts import MoveP2P, get_scripts_dir


class TestMoveP2P(standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase):
    async def basic_make_script(self, index):
        self.script = MoveP2P(index=index)

        return (self.script,)

    @contextlib.asynccontextmanager
    async def make_dry_script(self):
        async with self.make_script():
            self.script.mtcs = unittest.mock.AsyncMock()
            self.script.mtcs.components_attr = ["mtm1m3"]
            yield

    async def test_config_fail_az_no_el(self) -> None:
        async with self.make_dry_script():
            with pytest.raises(
                salobj.ExpectedError,
                match="is not valid under any of the given schemas",
            ):
                await self.configure_script(az=0.0)

    async def test_config_fail_el_no_az(self) -> None:
        async with self.make_dry_script():
            with pytest.raises(
                salobj.ExpectedError,
                match="is not valid under any of the given schemas",
            ):
                await self.configure_script(el=0.0)

    async def test_config_fail_ra_no_dec(self) -> None:
        async with self.make_dry_script():
            with pytest.raises(
                salobj.ExpectedError,
                match="is not valid under any of the given schemas",
            ):
                await self.configure_script(ra=0.0)

    async def test_config_fail_dec_no_ra(self) -> None:
        async with self.make_dry_script():
            with pytest.raises(
                salobj.ExpectedError,
                match="is not valid under any of the given schemas",
            ):
                await self.configure_script(dec=0.0)

    async def test_config_fail_no_defaults(self) -> None:
        async with self.make_dry_script():
            with pytest.raises(
                salobj.ExpectedError,
                match="is not valid under any of the given schemas",
            ):
                await self.configure_script()

    async def test_config_fail_azel_radec(self) -> None:
        async with self.make_dry_script():
            az = 0.0
            el = 80.0
            ra = 0.0
            dec = -30.0
            with pytest.raises(
                salobj.ExpectedError,
                match="Failed validating 'oneOf' in schema",
            ):
                await self.configure_script(
                    az=az,
                    el=el,
                    ra=ra,
                    dec=dec,
                )

    async def test_config_az_el_scalars(self) -> None:
        async with self.make_dry_script():
            az = 0.0
            el = 80.0
            self.script.configure_tcs = unittest.mock.AsyncMock()

            await self.configure_script(
                az=az,
                el=el,
            )

            self.script.configure_tcs.assert_awaited_once()
            assert "azel" in self.script.grid
            assert "az" in self.script.grid["azel"]
            assert "el" in self.script.grid["azel"]
            assert len(self.script.grid["azel"]["az"]) == 1
            assert len(self.script.grid["azel"]["el"]) == 1
            assert az in self.script.grid["azel"]["az"]
            assert el in self.script.grid["azel"]["el"]
            assert self.script.pause_for == 0
            assert self.script.program is None
            assert self.script.reason is None
            assert self.script.checkpoint_message is None

    async def test_config_ignore(self) -> None:
        async with self.make_dry_script():
            az = 0.0
            el = 80.0

            await self.configure_script(az=az, el=el, ignore=["mtm1m3", "no_comp"])
            assert self.script.mtcs.check.mtm1m3 is False
            self.script.mtcs.check.no_comp.assert_not_called()

    async def test_config_az_el_arrays(self) -> None:
        async with self.make_dry_script():
            az = [0.0, 10.0, 20.0]
            el = [80.0, 70.0, 60.0]
            await self.configure_script(
                az=az,
                el=el,
            )

            assert "azel" in self.script.grid
            assert "az" in self.script.grid["azel"]
            assert "el" in self.script.grid["azel"]
            assert self.script.grid["azel"]["az"] == az
            assert self.script.grid["azel"]["el"] == el
            assert self.script.pause_for == 0
            assert self.script.program is None
            assert self.script.reason is None
            assert self.script.checkpoint_message is None

    async def test_config_az_scalar_el_array(self) -> None:
        async with self.make_dry_script():
            az = 0.0
            el = [80.0, 70.0, 60.0]
            await self.configure_script(
                az=az,
                el=el,
            )

            assert "azel" in self.script.grid
            assert "az" in self.script.grid["azel"]
            assert "el" in self.script.grid["azel"]
            assert self.script.grid["azel"]["az"] == [az] * len(el)
            assert self.script.grid["azel"]["el"] == el
            assert self.script.pause_for == 0
            assert self.script.program is None
            assert self.script.reason is None
            assert self.script.checkpoint_message is None

    async def test_config_az_array_el_scalar(self) -> None:
        async with self.make_dry_script():
            az = [0.0, 10.0, 20.0]
            el = 80.0
            await self.configure_script(
                az=az,
                el=el,
            )

            assert "azel" in self.script.grid
            assert "az" in self.script.grid["azel"]
            assert "el" in self.script.grid["azel"]
            assert self.script.grid["azel"]["az"] == az
            assert self.script.grid["azel"]["el"] == [el] * len(az)
            assert self.script.pause_for == 0
            assert self.script.program is None
            assert self.script.reason is None
            assert self.script.checkpoint_message is None

    async def test_config_ra_dec_scalars(self) -> None:
        async with self.make_dry_script():
            ra = 0.0
            dec = -30.0
            await self.configure_script(
                ra=ra,
                dec=dec,
            )

            assert "radec" in self.script.grid
            assert "ra" in self.script.grid["radec"]
            assert "dec" in self.script.grid["radec"]
            assert len(self.script.grid["radec"]["ra"]) == 1
            assert len(self.script.grid["radec"]["dec"]) == 1
            assert ra in self.script.grid["radec"]["ra"]
            assert dec in self.script.grid["radec"]["dec"]
            assert self.script.pause_for == 0
            assert self.script.program is None
            assert self.script.reason is None
            assert self.script.checkpoint_message is None

    async def test_config_ra_dec_arrays(self) -> None:
        async with self.make_dry_script():
            ra = [0.0, 10.0, 20.0]
            dec = [80.0, 70.0, 60.0]
            await self.configure_script(
                ra=ra,
                dec=dec,
            )

            assert "radec" in self.script.grid
            assert "ra" in self.script.grid["radec"]
            assert "dec" in self.script.grid["radec"]
            assert self.script.grid["radec"]["ra"] == ra
            assert self.script.grid["radec"]["dec"] == dec
            assert self.script.pause_for == 0
            assert self.script.program is None
            assert self.script.reason is None
            assert self.script.checkpoint_message is None

    async def test_config_ra_scalar_dec_array(self) -> None:
        async with self.make_dry_script():
            ra = 0.0
            dec = [80.0, 70.0, 60.0]
            await self.configure_script(
                ra=ra,
                dec=dec,
            )

            assert "radec" in self.script.grid
            assert "ra" in self.script.grid["radec"]
            assert "dec" in self.script.grid["radec"]
            assert self.script.grid["radec"]["ra"] == [ra] * len(dec)
            assert self.script.grid["radec"]["dec"] == dec
            assert self.script.pause_for == 0
            assert self.script.program is None
            assert self.script.reason is None
            assert self.script.checkpoint_message is None

    async def test_config_ra_array_dec_scalar(self) -> None:
        async with self.make_dry_script():
            ra = [0.0, 10.0, 20.0]
            dec = 80.0
            await self.configure_script(
                ra=ra,
                dec=dec,
            )

            assert "radec" in self.script.grid
            assert "ra" in self.script.grid["radec"]
            assert "dec" in self.script.grid["radec"]
            assert self.script.grid["radec"]["ra"] == ra
            assert self.script.grid["radec"]["dec"] == [dec] * len(ra)
            assert self.script.pause_for == 0
            assert self.script.program is None
            assert self.script.reason is None
            assert self.script.checkpoint_message is None

    @unittest.mock.patch(
        "lsst.ts.standardscripts.BaseBlockScript.obs_id", "202306060001"
    )
    async def test_config_pause_for_reason_program(self) -> None:
        async with self.make_dry_script():
            self.script.get_obs_id = unittest.mock.AsyncMock(
                side_effect=["202306060001"]
            )

            az = 0.0
            el = 80.0
            pause_for = 10.0
            program = "BLOCK-123"
            reason = "SITCOM-321"
            await self.configure_script(
                az=az,
                el=el,
                pause_for=pause_for,
                program=program,
                reason=reason,
            )

            assert "azel" in self.script.grid
            assert "az" in self.script.grid["azel"]
            assert "el" in self.script.grid["azel"]
            assert len(self.script.grid["azel"]["az"]) == 1
            assert len(self.script.grid["azel"]["el"]) == 1
            assert az in self.script.grid["azel"]["az"]
            assert el in self.script.grid["azel"]["el"]
            assert self.script.pause_for == pause_for
            assert self.script.program == program
            assert self.script.reason == reason
            assert (
                self.script.checkpoint_message
                == "MoveP2P BLOCK-123 202306060001 SITCOM-321"
            )

    async def test_run_azel(self):
        async with self.make_dry_script():
            self.script.get_obs_id = unittest.mock.AsyncMock(
                side_effect=["202306060001"]
            )

            az = [0.0, 10.0, 20.0]
            el = [80.0, 70.0, 60.0]
            timeout = 321.0
            program = "BLOCK-123"
            reason = "SITCOM-321"

            await self.configure_script(
                az=az,
                el=el,
                program=program,
                reason=reason,
                move_timeout=timeout,
            )

            await self.run_script()

            expected_calls = [
                unittest.mock.call(az=_az, el=_el, timeout=timeout)
                for _az, _el in zip(az, el)
            ]
            self.script.mtcs.move_p2p_azel.assert_has_awaits(expected_calls)

    async def test_run_radec(self):
        async with self.make_dry_script():
            self.script.get_obs_id = unittest.mock.AsyncMock(
                side_effect=["202306060001"]
            )

            ra = [0.0, 10.0, 20.0]
            dec = [80.0, 70.0, 60.0]
            program = "BLOCK-123"
            reason = "SITCOM-321"
            timeout = 321.0

            await self.configure_script(
                ra=ra,
                dec=dec,
                program=program,
                reason=reason,
                move_timeout=timeout,
            )

            await self.run_script()

            expected_calls = [
                unittest.mock.call(ra=_ra, dec=_dec, timeout=timeout)
                for _ra, _dec in zip(ra, dec)
            ]
            self.script.mtcs.move_p2p_radec.assert_has_awaits(expected_calls)

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "move_p2p.py"
        await self.check_executable(script_path)
