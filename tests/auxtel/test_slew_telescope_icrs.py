import logging
import pathlib
import random
import sys
import unittest
import asyncio

import yaml

from lsst.ts import salobj
from lsst.ts import scriptqueue

import SALPY_Script
import SALPY_ATPtg
import SALPY_ATMCS

random.seed(47)

index_gen = salobj.index_generator()


def make_script(index):
    tests_dir = pathlib.Path(__file__).resolve().parent.parent.parent
    script_dir = tests_dir / "scripts" / "auxtel"
    orig_path = sys.path
    try:
        sys.path.append(str(script_dir))
        import slew_telescope_icrs
        script = slew_telescope_icrs.SlewTelescopeIcrs(index=index)
    finally:
        sys.path[:] = orig_path
    script.log.setLevel(logging.INFO)
    script.log.addHandler(logging.StreamHandler())
    return script


class Harness:
    def __init__(self):
        self.index = next(index_gen)

        self.test_index = next(index_gen)

        self.script = make_script(index=self.index)

        # mock controllers that use callback functions defined below
        # to handle the expected commands
        self.atptg = salobj.Controller(SALPY_ATPtg)
        self.atmcs = salobj.Controller(SALPY_ATMCS)
        self.atptg.evt_summaryState.set_put(summaryState=salobj.State.ENABLED)
        self.atmcs.evt_summaryState.set_put(summaryState=salobj.State.ENABLED)

        self.n_mcs_start_tracking_calls = 0
        self.n_mcs_stop_tracking_calls = 0
        self.atptg_target = None

        # assign the command callback functions
        self.atmcs.cmd_startTracking.callback = self.startTracking
        self.atmcs.cmd_stopTracking.callback = self.stopTracking
        self.atptg.cmd_raDecTarget.callback = self.raDecTarget

    async def startTracking(self, id_data):
        """Callback for ATMCS startTracking command."""
        self.n_mcs_start_tracking_calls += 1

    async def stopTracking(self, id_data):
        """Callback for ATMCS stopTracking command."""
        self.n_mcs_stop_tracking_calls += 1

    async def raDecTarget(self, id_data):
        """Callback for ATPtg raDecTarget command.
        """
        self.atptg_target = id_data.data


class TestSlewTelescopeIcrs(unittest.TestCase):
    def setUp(self):
        salobj.test_utils.set_random_lsst_dds_domain()

        # arbitrary sample data for use by most tests
        self.ra = 100
        self.dec = 5
        self.rot_pa = 1
        self.target_name = "test target"

    def make_config_data(self, send_start_tracking):
        """Make config data using the default ra, dec, etc.

        Parameters
        ----------
        send_start_tracking : `bool` (optional)
            Issue the ``startTracking`` command to ATMCS?

        Returns
        -------
        config_data : `SALPY_Script.Script_command_configureC`
            Data for the script's config command.
        """
        config_kwargs = dict(
            ra=self.ra,
            dec=self.dec,
            rot_pa=self.rot_pa,
            target_name=self.target_name,
            send_start_tracking=send_start_tracking,
        )
        config_data = SALPY_Script.Script_command_configureC()
        config_data.config = yaml.safe_dump(config_kwargs)
        return config_data

    def test_configure(self):
        index = next(index_gen)

        async def doit():
            script = make_script(index=index)

            # configure requires ra and dec
            with self.assertRaises(TypeError):
                await script.configure()
            with self.assertRaises(TypeError):
                await script.configure(ra=100)
            with self.assertRaises(TypeError):
                await script.configure(dec=100)
            with self.assertRaises(ValueError):
                await script.configure(ra="strings instead of", dec="floats")

            await script.configure(ra=5, dec=6)
            self.assertEqual(script.ra, 5)
            self.assertEqual(script.dec, 6)
            self.assertEqual(script.rot_pa, 0)
            self.assertEqual(script.target_name, "")
            self.assertTrue(script.send_start_tracking)

            await script.configure(ra=7, dec=8, rot_pa=-9, target_name="target", send_start_tracking=False)
            self.assertEqual(script.ra, 7)
            self.assertEqual(script.dec, 8)
            self.assertEqual(script.rot_pa, -9)
            self.assertEqual(script.target_name, "target")
            self.assertFalse(script.send_start_tracking)

        asyncio.get_event_loop().run_until_complete(doit())

    def xtest_run_with_start_tracking(self):
        async def doit():
            harness = Harness()
            config_data = self.make_config_data(send_start_tracking=True)
            await harness.script.do_configure(id_data=salobj.CommandIdData(cmd_id=1, data=config_data))
            self.assertEqual(harness.script.state.state, scriptqueue.ScriptState.CONFIGURED)

            await harness.script.do_run(id_data=salobj.CommandIdData(cmd_id=2, data=None))
            await harness.script.done_task
            self.assertEqual(harness.script.state.state, scriptqueue.ScriptState.DONE)

            self.assertEqual(harness.n_mcs_start_tracking_calls, 1)
            self.assertEqual(harness.n_mcs_stop_tracking_calls, 0)
            self.assertEqual(harness.atptg_target.ra, self.ra)
            self.assertEqual(harness.atptg_target.declination, self.dec)
            self.assertEqual(harness.atptg_target.rotPA, self.rot_pa)
            self.assertEqual(harness.atptg_target.targetName, self.target_name)

        asyncio.get_event_loop().run_until_complete(doit())

    def test_run_without_start_tracking(self):
        async def doit():
            harness = Harness()
            config_data = self.make_config_data(send_start_tracking=False)
            await harness.script.do_configure(id_data=salobj.CommandIdData(cmd_id=1, data=config_data))
            self.assertEqual(harness.script.state.state, scriptqueue.ScriptState.CONFIGURED)

            await harness.script.do_run(id_data=salobj.CommandIdData(cmd_id=2, data=None))
            await harness.script.done_task
            self.assertEqual(harness.script.state.state, scriptqueue.ScriptState.DONE)

            self.assertEqual(harness.n_mcs_start_tracking_calls, 0)
            self.assertEqual(harness.n_mcs_stop_tracking_calls, 0)
            self.assertEqual(harness.atptg_target.ra, self.ra)
            self.assertEqual(harness.atptg_target.declination, self.dec)
            self.assertEqual(harness.atptg_target.rotPA, self.rot_pa)
            self.assertEqual(harness.atptg_target.targetName, self.target_name)

        asyncio.get_event_loop().run_until_complete(doit())

    def test_run_atmcs_not_enabled(self):
        async def doit():
            harness = Harness()
            harness.atmcs.evt_summaryState.set_put(summaryState=salobj.State.DISABLED)
            # the value of send_start_tracking should not matter
            config_data = self.make_config_data(send_start_tracking=False)
            await harness.script.do_configure(id_data=salobj.CommandIdData(cmd_id=1, data=config_data))
            self.assertEqual(harness.script.state.state, scriptqueue.ScriptState.CONFIGURED)

            await harness.script.do_run(id_data=salobj.CommandIdData(cmd_id=2, data=None))
            await harness.script.done_task
            self.assertEqual(harness.script.state.state, scriptqueue.ScriptState.FAILED)

            self.assertEqual(harness.n_mcs_start_tracking_calls, 0)
            self.assertEqual(harness.n_mcs_stop_tracking_calls, 0)
            self.assertIsNone(harness.atptg_target)

        asyncio.get_event_loop().run_until_complete(doit())

    def xtest_run_atptg_not_enabled(self):
        async def doit():
            harness = Harness()
            harness.atptg.evt_summaryState.set_put(summaryState=salobj.State.DISABLED)
            # the value of send_start_tracking should not matter
            config_data = self.make_config_data(send_start_tracking=False)
            await harness.script.do_configure(id_data=salobj.CommandIdData(cmd_id=1, data=config_data))
            self.assertEqual(harness.script.state.state, scriptqueue.ScriptState.CONFIGURED)

            await harness.script.do_run(id_data=salobj.CommandIdData(cmd_id=2, data=None))
            await harness.script.done_task
            self.assertEqual(harness.script.state.state, scriptqueue.ScriptState.FAILED)

            self.assertEqual(harness.n_mcs_start_tracking_calls, 0)
            self.assertEqual(harness.n_mcs_stop_tracking_calls, 0)
            self.assertIsNone(harness.atptg_target)

        asyncio.get_event_loop().run_until_complete(doit())

    def test_run_stop_early(self):
        async def doit():
            harness = Harness()
            # Set send_start_tracking True so stopTracking will be sent
            # when the script stops early
            config_data = self.make_config_data(send_start_tracking=True)
            await harness.script.do_configure(id_data=salobj.CommandIdData(cmd_id=1, data=config_data))
            self.assertEqual(harness.script.state.state, scriptqueue.ScriptState.CONFIGURED)

            # set the script to stop at the "slew" checkpoint; this should
            # result in one startTracking and stopTracking call to ATMCS
            harness.script.evt_checkpoints.set(stop="slew")

            await harness.script.do_run(id_data=salobj.CommandIdData(cmd_id=2, data=None))
            await harness.script.done_task
            self.assertEqual(harness.script.state.state, scriptqueue.ScriptState.STOPPED)

            self.assertEqual(harness.n_mcs_start_tracking_calls, 1)
            self.assertEqual(harness.n_mcs_stop_tracking_calls, 1)
            self.assertIsNone(harness.atptg_target)

        asyncio.get_event_loop().run_until_complete(doit())


if __name__ == '__main__':
    unittest.main()
