##################
ts_standardscripts
##################

Standard SAL scripts for operating the LSST via the `lsst.ts.scriptqueue.ScriptQueue`.
Each script is a subclass of `lsst.ts.scriptqueue.ScriptBase`.

Put common code and complicated implementations in ``python/lsst/ts/standardscripts``
and the actual scripts in ``scripts`` in the desired hierarchy.

This code is automatically formatted by ``black`` using a git pre-commit hook.
To enable this:

* Install the ``black`` Python package.
* Run ``git config core.hooksPath .githooks`` once in this repository.
