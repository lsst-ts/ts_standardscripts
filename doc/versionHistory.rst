.. _Version_History:

===============
Version History
===============

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
