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

import contextlib
import unittest
import warnings

from lsst.ts import standardscripts
from lsst.ts.standardscripts.dummy_block_script import DummyBlockScript


class TestBaseBlockScript(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    """Test BaseBlockScript using the DummyBlockScript script."""

    async def basic_make_script(self, index):
        self.script = DummyBlockScript(index=index)

        return (self.script,)

    @contextlib.asynccontextmanager
    async def make_dry_script(self):
        async with self.make_script():
            self.script.mtcs = unittest.mock.AsyncMock()
            self.script.mtcs.components_attr = ["mtm1m3"]
            yield

    async def test_deprecation_warning(self):
        """Test that instantiating a BaseBlockScript issues a deprecation
        warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            async with self.make_dry_script():
                deprecation_warnings = [
                    warning
                    for warning in w
                    if issubclass(warning.category, DeprecationWarning)
                ]
                assert len(deprecation_warnings) >= 1
                assert "BaseBlockScript is deprecated" in str(
                    deprecation_warnings[0].message
                )

    @unittest.mock.patch(
        "lsst.ts.standardscripts.BaseBlockScript.obs_id", "202306060001"
    )
    async def test_config_reason_program(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            async with self.make_dry_script():
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

                assert self.script.program == program
                assert self.script.reason == reason
                assert self.script.test_case is None
                # The obs_id should be None now
                assert self.script.obs_id is None
                # Accept the actual format with two spaces, since we don't want
                #  to change the deprecated code
                assert (
                    self.script.checkpoint_message
                    == "DummyBlockScript BLOCK-123  SITCOM-321"
                )

            # Check for both types of deprecation warnings
            # 1. BaseBlockScript deprecation (from script instantiation)
            base_warnings = [
                warning
                for warning in w
                if issubclass(warning.category, DeprecationWarning)
                and "BaseBlockScript is deprecated" in str(warning.message)
            ]
            assert len(base_warnings) >= 1

            # 2. get_obs_id deprecation (from configure -> get_obs_id call)
            get_obs_id_warnings = [
                warning
                for warning in w
                if issubclass(warning.category, DeprecationWarning)
                and "get_obs_id method" in str(warning.message)
            ]
            assert len(get_obs_id_warnings) >= 1

    async def test_get_obs_id_returns_none(self):
        """Test that get_obs_id now returns None and issues a deprecation
        warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            async with self.make_dry_script():
                self.script.program = "BLOCK-123"
                obs_id = await self.script.get_obs_id()

                # Check if method returns None
                assert obs_id is None

            # Check for get_obs_id deprecation warning
            get_obs_id_warnings = [
                warning
                for warning in w
                if issubclass(warning.category, DeprecationWarning)
                and "get_obs_id method" in str(warning.message)
            ]
            assert len(get_obs_id_warnings) >= 1

    async def test_run(self):
        async with self.make_dry_script():
            self.script.get_obs_id = unittest.mock.AsyncMock(side_effect=[None])

            ra = [0.0, 10.0, 20.0]
            dec = [80.0, 70.0, 60.0]
            timeout = 100.0
            program = "BLOCK-T123"
            reason = "SITCOM-321"

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
            self.script.mtcs.dummy_move_radec.assert_has_awaits(expected_calls)

            assert not self.script.evt_largeFileObjectAvailable.has_data
