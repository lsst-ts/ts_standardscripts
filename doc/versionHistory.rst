.. _Version_History:

===============
Version History
===============

v1.6.5
------

* Update `BaseTakeImage`:
 * Add instrument setup time to duration estimation.
 * Only setup instrument configuration in the first image.
 * Update unit tests.

v1.6.4
------

* Use unittest instead of the deprecated asynctest package.

v1.6.3
------

* Add offline scripts for auxtel.
* Add offline scripts for maintel.
* Update ``tests/SConscript`` to make scons work when building with the licensed version of OpenSplice.

v1.6.2
------

* Reformat code using black 20.
* Enabled pytest-black.
* Pin version of ts-conda-build to 0.3 in conda recipe.
* Update documentation format.
