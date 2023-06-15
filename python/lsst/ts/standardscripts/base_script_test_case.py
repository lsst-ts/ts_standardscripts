# This file is part of ts_standardscripts.
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__all__ = ["BaseScriptTestCase"]

import abc
import asyncio
import contextlib
import logging
import os
import pathlib
import time
import types

import astropy.time
import yaml
from lsst.ts import salobj, utils
from lsst.ts.idl.enums import Script

MAKE_TIMEOUT = 90  # Default time for make_script (seconds)


class BaseScriptTestCase(metaclass=abc.ABCMeta):
    """Base class for Script tests.

    Subclasses must:

    * Inherit both from this and `unittest.IsolatedAsyncioTestCase`.
    * Override `basic_make_script` to make the script and any other
      controllers, remotes and such, and return a list of scripts,
      controllers and remotes that you made.

    A typical test will look like this:

        async def test_something(self):
            async with make_script():
                await self.configure_script(...)
                # ... test the results of configuring the script (self.script)

                await self.run_script()  # (unless only testing configuration)
                # ... test the results of running the script
    """

    _index_iter = utils.index_generator()

    @abc.abstractmethod
    async def basic_make_script(self, index):
        """Make a script as self.script.

        Make all other controllers and remotes, as well
        and return a list of the items made.

        Parameters
        ----------
        index : `int`
            The SAL index of the script.

        Returns
        -------
        items : `List` [``any``]
            Controllers, Remotes and Script, or any other items
            for which to initially wait for ``item.start_task``
            and finally wait for ``item.close()``.

        Notes
        -----
        This is a coroutine in the unlikely case that you might
        want to wait for something.
        """
        raise NotImplementedError()

    async def close(self):
        """Optional cleanup before closing the scripts and etc."""
        pass

    async def check_executable(self, script_path):
        """Check that an executable script can be launched.

        Parameter
        ---------
        script_path : `str`
            Full path to script.
        """
        salobj.set_random_lsst_dds_partition_prefix()

        index = self.next_index()

        script_path = pathlib.Path(script_path).resolve()

        assert script_path.is_file()

        async with salobj.Domain() as domain, salobj.Remote(
            domain=domain, name="Script", index=index
        ) as remote:
            initial_path = os.environ["PATH"]
            process = None
            try:
                os.environ["PATH"] = str(script_path.parent) + ":" + initial_path
                process = await asyncio.create_subprocess_exec(
                    str(script_path), str(index)
                )

                state = await remote.evt_state.next(flush=False, timeout=MAKE_TIMEOUT)
                assert state.state == Script.ScriptState.UNCONFIGURED
            finally:
                if process is not None:
                    process.terminate()
                os.environ["PATH"] = initial_path

    async def configure_script(self, **kwargs):
        """Configure the script and set the group ID (if using ts_salobj
        4.5 or later).

        Sets the script state to UNCONFIGURED.
        This allows you to call configure_script multiple times.

        Parameters
        ----------
        kwargs : `dict`
            Keyword arguments for configuration.

        Returns
        -------
        config : `types.SimpleNamespace`
            ``kwargs`` expressed as a SimpleNamespace.
            This is provided as a convenience, to avoid boilerplate
            and duplication in your unit tests. The data is strictly
            based on the input arguments; it has nothing to do
            with the script.
        """
        await self.script.set_state(Script.ScriptState.UNCONFIGURED)
        config = types.SimpleNamespace(**kwargs)
        config_data = self.script.cmd_configure.DataType()
        if kwargs:
            config_data.config = yaml.safe_dump(kwargs)
        await self.script.do_configure(config_data)
        assert self.script.state.state == Script.ScriptState.CONFIGURED
        if hasattr(self.script, "cmd_setGroupId"):
            group_id_data = self.script.cmd_setGroupId.DataType(
                groupId=astropy.time.Time.now().isot
            )
            await self.script.do_setGroupId(group_id_data)
        return config

    @contextlib.asynccontextmanager
    async def make_script(
        self, log_level=logging.INFO, timeout=MAKE_TIMEOUT, verbose=False
    ):
        """Create a Script.

        The script is accessed as ``self.script``.

        Parameters
        ----------
        name : `str`
            Name of SAL component.
        log_level : `int` (optional)
            Logging level, such as `logging.INFO`.
        timeout : `float`
            Timeout (sec) for waiting for ``item.start_task`` and
            ``item.close()`` for each item returned by `basic_make_script`,
            and `self.close`.
        verbose : `bool`
            Log data? This can be helpful for setting ``timeout``.
        """
        salobj.set_random_lsst_dds_partition_prefix()

        items_to_await = await self.wait_for(
            self.basic_make_script(index=self.next_index()),
            timeout=timeout,
            description="self.basic_make_script()",
            verbose=verbose,
        )
        try:
            await self.wait_for(
                asyncio.gather(*[item.start_task for item in items_to_await]),
                timeout=timeout,
                description=f"item.start_task for {len(items_to_await)} items",
                verbose=verbose,
            )
            yield
        finally:
            await self.wait_for(
                self.close(),
                timeout=timeout,
                description="self.close()",
                verbose=verbose,
            )
            await self.wait_for(
                asyncio.gather(*[item.close() for item in items_to_await]),
                timeout=timeout,
                description=f"item.close() for {len(items_to_await)} items",
                verbose=verbose,
            )

    def next_index(self):
        return next(self._index_iter)

    async def run_script(self):
        """Run the script.

        Requires that the script be configured and the group ID set
        (if using ts_salobj 4.5 or later).
        """
        run_data = self.script.cmd_run.DataType()
        await self.script.do_run(run_data)
        await self.script.done_task
        assert self.script.state.state == Script.ScriptState.DONE

    async def wait_for(self, coro, timeout, description, verbose):
        """A wrapper around asyncio.wait_for that prints timing information.

        Parameters
        ----------
        coro : ``awaitable``
            Coroutine or task to await.
        timeout : `float`
            Timeout (seconds)
        description : `str`
            Description of what is being awaited.
        verbose : `bool`
            If True then print a message before waiting
            and another after that includes how long it waited.
            If False only print a message if the wait times out.
        """
        t0 = time.monotonic()
        if verbose:
            print(f"wait for {description}")
        try:
            result = await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            dt = time.monotonic() - t0
            print(f"{description} timed out after {dt:0.1f} seconds")
            raise
        if verbose:
            dt = time.monotonic() - t0
            print(f"{description} took {dt:0.1f} seconds")
        return result
