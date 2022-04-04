.. py:currentmodule:: lsst.ts.standardscripts

.. _lsst.ts.standardscripts.version_history:

===============
Version History
===============

v1.10.1
-------

* Make auxtel/prepare_for_onsky.py script not gather ATCS config and just assert enabled.

v1.10.0
-------

* Change archiver references to oods ones due to image creation process change (DMTN-143).

v1.9.0
------

* Update for ts_salobj v7, which is required.
  This also requires ts_xml 11.

v1.8.0
------

* In `BaseTrackTargetAndTakeImage` allow filter to be a list or a single string.
* In `auxtel.TrackTargetAndTakeImage`, allow grating to be a list or a string, implement handling of list of grating/filters.
* Update unit tests for `auxtel.TrackTargetAndTakeImage` to account for handling lists of filters/grating.
* In `auxtel.TrackTargetAndTakeImage` add prefix for filter name.
* Update to use ts_utils

v1.7.0
------

* Implement new reason/program image feature on auxtel and comcam scripts.

v1.6.9
------

* Remove AuxTel integration test scripts (some of which were broken).
  Integration tests now use Jupyter notebooks.
* Remove unnecessary `__test__ = False` statements.
  These are only useful for classes whose names begin with "Test".
* Modernize the unit tests to use bare assert.
* Clean up the package documentation.

v1.6.8
------

* Add new BaseTrackTargetAndTakeImage script, that implements a simple script to track a target and take images.
* Update auxtel/track_target_and_take_image script to use the new BaseTrackTargetAndTakeImage.
* Adds maintel/track_target_and_take_image_comcam script to do a simple track target and take image with the Main Telescope and ComCam.

v1.6.7
------

* Add track target and take image script for auxtel.
* Add stop tracking scrit for auxtel.

v1.6.6
------

* Update prepare for onsky Script to check that LATISS components are enabled before executing.
* Fix import statement in `prepare_for_onsky`

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
