##################
ts_maintel_standardscripts
##################

Standard SAL scripts for operating the LSST via the `lsst.ts.scriptqueue.ScriptQueue`.
Each script is a subclass of `lsst.ts.scriptqueue.ScriptBase`.

`Documentation <https://ts-maintel-standardscripts.lsst.io>`_

This code uses ``pre-commit`` to maintain ``black`` formatting and ``flake8`` compliance.
To enable this:

* Run ``pre-commit install`` once.
* If directed, run ``git config --unset-all core.hooksPath`` once.
