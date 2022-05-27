SAL scripts to operate the LSST.

Each script is a subclass of `lsst.ts.scriptqueue.ScriptBase`.
Scripts may be grouped by putting them in suitable subdirectories.
Scripts must be command-line executables that take a single
command-line argument: the SAL index for the script.
