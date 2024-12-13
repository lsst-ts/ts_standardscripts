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

import types
import unittest
from unittest.mock import patch

from lsst.ts import standardscripts
from lsst.ts.idl.enums.Script import ScriptState
from lsst.ts.maintel.standardscripts import Mode, TakeAOSSequenceComCam
from lsst.ts.observatory.control.maintel.comcam import ComCam, ComCamUsages
from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages
from lsst.ts.utils import index_generator

index_gen = index_generator()


class TestTakeAOSSequenceComCam(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = TakeAOSSequenceComCam(index=index)

        self.script.mtcs = MTCS(
            domain=self.script.domain,
            intended_usage=MTCSUsages.DryTest,
            log=self.script.log,
        )

        self.script.camera = ComCam(
            domain=self.script.domain,
            intended_usage=ComCamUsages.DryTest,
            log=self.script.log,
        )

        self.script.ocps = unittest.mock.AsyncMock()

        self.script.mtcs.offset_camera_hexapod = unittest.mock.AsyncMock()
        self.script.camera.expose = unittest.mock.AsyncMock(
            side_effect=self._get_visit_id
        )
        self.script.camera.setup_instrument = unittest.mock.AsyncMock()
        self.script.camera.rem.ccoods = unittest.mock.AsyncMock()
        self.script.camera.rem.ccoods.configure_mock(
            **{
                "evt_imageInOODS.next.side_effect": self._get_next_image_in_oods,
            }
        )

        self._dayobs = 2024111900000
        self._visit_index = next(index_gen)

        return (self.script,)

    async def _get_visit_id(self, *args, **kwargs):
        self._visit_index = next(index_gen)
        return [self._dayobs + self._visit_index]

    async def _get_next_image_in_oods(self, *args, **kwargs):
        return types.SimpleNamespace(
            obsid=f"CC_O_{int(self._dayobs/100000)}_{self._visit_index:06d}",
            raft=0,
            sensor=0,
        )

    async def test_configure(self):
        async with self.make_script():
            exposure_time = 15.0
            filter = "g"
            dz = 2000.0
            n_sequences = 15
            mode = "INTRA"

            await self.configure_script(
                filter=filter,
                exposure_time=exposure_time,
                dz=dz,
                n_sequences=n_sequences,
                mode=mode,
            )
            assert self.script.exposure_time == exposure_time
            assert self.script.filter == filter
            assert self.script.dz == 2000.0
            assert self.script.n_sequences == n_sequences
            assert self.script.mode == Mode.INTRA

    async def test_configure_ignore(self):
        async with self.make_script():
            self.script.mtcs.check.mtmount = True
            self.script.mtcs.check.mtrotator = True
            self.script.mtcs.check.mtm2 = True
            self.script.camera.check.ccoods = True

            exposure_time = 15.0
            filter = "g"
            dz = 2000.0
            n_sequences = 15
            mode = "INTRA"
            ignore = ["mtrotator", "mtm2", "ccoods"]

            await self.configure_script(
                filter=filter,
                exposure_time=exposure_time,
                dz=dz,
                n_sequences=n_sequences,
                ignore=ignore,
                mode=mode,
            )
            assert self.script.exposure_time == exposure_time
            assert self.script.filter == filter
            assert self.script.dz == 2000.0
            assert self.script.n_sequences == n_sequences
            assert self.script.mode == Mode.INTRA
            assert self.script.mtcs.check.mtmount
            assert not self.script.mtcs.check.mtrotator
            assert not self.script.mtcs.check.mtm2
            assert not self.script.camera.check.ccoods

    async def run_take_triplets_test(
        self, mock_ready_to_take_data=None, expect_exception=None
    ):
        async with self.make_script():
            self.script.camera.ready_to_take_data = mock_ready_to_take_data

            exposure_time = 15.0
            filter = "g"
            dz = 2000.0
            n_sequences = 3
            mode = "TRIPLET"

            await self.configure_script(
                filter=filter,
                exposure_time=exposure_time,
                dz=dz,
                n_sequences=n_sequences,
                mode=mode,
            )

            # Wrap `take_cwfs` and `take_acq` to count calls
            with patch.object(
                self.script.camera, "take_cwfs", wraps=self.script.camera.take_cwfs
            ) as mock_take_cwfs, patch.object(
                self.script.camera, "take_acq", wraps=self.script.camera.take_acq
            ) as mock_take_acq:

                if expect_exception is not None:
                    await self.run_script(expected_final_state=ScriptState.FAILED)
                    self.assertEqual(self.script.state.state, ScriptState.FAILED)
                    self.assertIn(
                        str(mock_ready_to_take_data.side_effect),
                        self.script.state.reason,
                    )
                    # the first image taken is type  cwfs and in this case
                    # it should throw and exception for TCS not being ready
                    expected_take_cwfs_calls = 1
                    expected_take_acq_calls = 0
                else:
                    await self.run_script()
                    self.assertEqual(self.script.state.state, ScriptState.DONE)
                    expected_take_cwfs_calls = n_sequences * 2
                    expected_take_acq_calls = n_sequences

                expected_tcs_ready_calls = (
                    expected_take_cwfs_calls + expected_take_acq_calls
                )
                if expected_take_acq_calls > 0:
                    # number of calls to the expose method
                    # in BaseCamera.take_imgtype
                    expected_expose_calls = expected_tcs_ready_calls
                else:
                    expected_expose_calls = 0

                if mock_ready_to_take_data is not None:
                    self.assertEqual(
                        mock_ready_to_take_data.await_count,
                        expected_tcs_ready_calls,
                        f"ready_to_take_data was called {mock_ready_to_take_data.await_count} times, "
                        f"expected {expected_tcs_ready_calls}",
                    )
                else:
                    with self.assertRaises(AttributeError):
                        self.script.camera.ready_to_take_data.assert_not_called()

                self.assertEqual(
                    self.script.camera.expose.await_count,
                    expected_expose_calls,
                    f"expose was called {self.script.camera.expose.await_count} times, "
                    f"expected {expected_expose_calls}",
                )
                self.assertEqual(
                    mock_take_cwfs.await_count,
                    expected_take_cwfs_calls,
                    f"take_cwfs was called {mock_take_cwfs.await_count} times, "
                    f"expected {expected_take_cwfs_calls}",
                )
                self.assertEqual(
                    mock_take_acq.await_count,
                    expected_take_acq_calls,
                    f"take_acq was called {mock_take_acq.await_count} times, "
                    f"expected {expected_take_acq_calls}",
                )

    async def test_take_triplets(self):
        await self.run_take_triplets_test()

    async def test_take_triplets_tcs_ready(self):
        mock_ready = unittest.mock.AsyncMock(return_value=None)
        await self.run_take_triplets_test(
            mock_ready_to_take_data=mock_ready,
        )

    async def test_take_triplets_tcs_not_ready(self):
        mock_ready = unittest.mock.AsyncMock(side_effect=RuntimeError("TCS not ready"))
        await self.run_take_triplets_test(
            mock_ready_to_take_data=mock_ready, expect_exception=RuntimeError
        )

    async def test_take_doublet(self):
        async with self.make_script():
            self.script.camera.take_cwfs = unittest.mock.AsyncMock()
            self.script.camera.take_acq = unittest.mock.AsyncMock()

            exposure_time = 15.0
            filter = "g"
            dz = 2000.0
            n_sequences = 3
            mode = "INTRA"

            await self.configure_script(
                filter=filter,
                exposure_time=exposure_time,
                dz=dz,
                n_sequences=n_sequences,
                mode=mode,
            )

            await self.run_script()

            assert n_sequences == self.script.camera.take_cwfs.await_count
            assert n_sequences == self.script.camera.take_acq.await_count

    async def test_executable_lsstcam(self) -> None:
        """Test that the script is executable."""
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "maintel" / "take_aos_sequence_comcam.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
