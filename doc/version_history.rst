.. py:currentmodule:: lsst.ts.maintel.standardscripts

.. _lsst.ts.maintel.standardscripts.version_history:

===============
Version History
===============

.. towncrier release notes start

v1.40.0 (2024-12-05)
====================

New Features
------------

- Use the new method ``ATCS.assert_ataos_corrections_enabled`` in auxtel scripts (`DM-38823 <https://rubinobs.atlassian.net/browse/DM-38823>`_)
- Add ``ParkDome`` SAL Script for ``maintel``. (`DM-45609 <https://rubinobs.atlassian.net/browse/DM-45609>`_)
- Add ``UnparkDome`` SAL Script for ``maintel``. (`DM-45610 <https://rubinobs.atlassian.net/browse/DM-45610>`_)
- New SalScript for powering on the Tunable Laser standalone (`DM-45729 <https://rubinobs.atlassian.net/browse/DM-45729>`_)
- In  ``offset_camera_hexapod.py`` and ``offset_m2_hexapod.py``:

  - Added an option to reset hexapod offsets before applying new ones.
    This ensures that the offsets are first reset to zero before applying the user-provided offsets.
  - Added an option to reset hexapod offsets to zero without performing any additional actions.
    This allows the user to reset the hexapod offsets to zero without applying new offsets. (`DM-45817 <https://rubinobs.atlassian.net/browse/DM-45817>`_)
- Add SAL script to slew main telescope dome to a desired azimuth. (`DM-45821 <https://rubinobs.atlassian.net/browse/DM-45821>`_)
- Establish ``µm`` as the unit for hexapod offsets (configuration attributes ``focus_window`` and ``focus_step_sequence``) in ``BaseFocusSweep`` and implement conversion to ``mm`` for AuxTel in ``FocusSweepLatiss``. (`DM-45823 <https://rubinobs.atlassian.net/browse/DM-45823>`_)
- Extend TCS readiness check to other image types beyond OBJECT, such as:
  ENGTEST, CWFS and ACQ.

  Configure TCS synchronization to the following script:
  - auxtel/daytime_checkout/slew_and_take_image_checkout.py
  - auxtel/take_image_latiss.py
  - maintel/take_image_comcam.py
  - maintel/take_image_lsstcam.py
  - maintel/take_triplet_comcam.py (`DM-46179 <https://rubinobs.atlassian.net/browse/DM-46179>`_)
- Added expected_final_state argument to run_script method in BaseScriptTestCase

  We use this argument to test the overall state of the script execution.
  expected_final_state defaults to ScriptState.DONE if not passed. (`DM-46179 <https://rubinobs.atlassian.net/browse/DM-46179>`_)
- Now maintel/base_close_loop receives the ``wep_config`` attribute as an object. (`DM-46180 <https://rubinobs.atlassian.net/browse/DM-46180>`_)
- In check_actuators.py, refractor loop to store failures and add unit test. (`DM-46201 <https://rubinobs.atlassian.net/browse/DM-46201>`_)
- Add open and close mirror covers SAL Scripts for ``maintel``. (`DM-46309 <https://rubinobs.atlassian.net/browse/DM-46309>`_)
- Add infocus image in closed_loop script. (`DM-46978 <https://rubinobs.atlassian.net/browse/DM-46978>`_)
- In maintel/base_close_loop, take_intra_extra_focal_images to wait for images to be ingested before returning. (`DM-46978 <https://rubinobs.atlassian.net/browse/DM-46978>`_)
- Update maintel/take_image_lsstcam to add option to setup Guider ROI. (`DM-46978 <https://rubinobs.atlassian.net/browse/DM-46978>`_)
- Add SAL scripts to park and unpark the TMA for ``maintel``. (`DM-46979 <https://rubinobs.atlassian.net/browse/DM-46979>`_)
- Add home dome SAL Script for ``maintel``. (`DM-46980 <https://rubinobs.atlassian.net/browse/DM-46980>`_)
- Add option to mute watcher alarms when setting CSCs to OFFLINE
    
  Added `mute_alarms` and `mute_duration` parameters to the `set_summary_state` script
  configuration.
  `mute_alarms` defaults to `False`
  `mute_duration` defaults to `30 mins`
    
  E.g.
         data:
           -
             - MTMount
             - Offline
         mute_alarms: true
    
       or
  
         data:
           -
             - MTMount
             - Offline
         mute_alarms: true
         mute_duration: 60.0
    
  When `mute_alarms` is enabled and a component is transitioned to OFFLINE, related watcher
  alarms are temporarily muted for the specified duration, defaulting to 30 minutes.
    
  Muting is applied only to components transitioning to OFFLINE state. (`DM-47086 <https://rubinobs.atlassian.net/browse/DM-47086>`_)
- Add new `set_dof.py`` to set absolute DOF position (`DM-47363 <https://rubinobs.atlassian.net/browse/DM-47363>`_)
- In ``base_track_target.py``, add log to debug check feature. (`DM-47381 <https://rubinobs.atlassian.net/browse/DM-47381>`_)
- In ``base_track_target_and_take_image.py``, add instrument name to metadata and propagate to instrument scripts. (`DM-47381 <https://rubinobs.atlassian.net/browse/DM-47381>`_)
- In ``track_target_and_take_image_comcam.py``, add StateTransition usages to MTCS and ComCam usages. (`DM-47381 <https://rubinobs.atlassian.net/browse/DM-47381>`_)
- In ``track_target_and_take_iamge_comcam.py``, simplify the _handle_slew_and_change_filter method. (`DM-47381 <https://rubinobs.atlassian.net/browse/DM-47381>`_)
- In ``base_track-target_and_take_image.py``, add support for single filters or array of filters in metadata. (`DM-47381 <https://rubinobs.atlassian.net/browse/DM-47381>`_)
- In ``base_close_loop.py``, add gain_sequence. (`DM-47381 <https://rubinobs.atlassian.net/browse/DM-47381>`_)
- In ``maintel/take_aos_sequence_comcam.py``, use all topics from the camera. (`DM-47381 <https://rubinobs.atlassian.net/browse/DM-47381>`_)
- Add support for ignoring ``MTCS`` components in open and close mirror covers operation. (`DM-47552 <https://rubinobs.atlassian.net/browse/DM-47552>`_)
- Add ``last_failed`` option to the ``CheckActuators`` script to run bump tests on actuators that failed their last test. (`DM-47618 <https://rubinobs.atlassian.net/browse/DM-47618>`_)
- Update HomeBothAxis script to re-enable the force balance system after homing the mount. (`DM-47641 <https://rubinobs.atlassian.net/browse/DM-47641>`_)
- In base_track_target, update track_azel routine to remove stop_tracking before start_tracking. (`DM-47641 <https://rubinobs.atlassian.net/browse/DM-47641>`_)
- In maintel/base_close_loop.py, make filter required. (`DM-47641 <https://rubinobs.atlassian.net/browse/DM-47641>`_)


Bug Fixes
---------

- In auxtel/calibrations/run_calibration_sequence.py, update call to ATCalsys.prepare_for_flat use named argument sequence_name instead of config_name. (`DM-46201 <https://rubinobs.atlassian.net/browse/DM-46201>`_)
- In ``scheduler/add_block.py``, convert override config to str. (`DM-46458 <https://rubinobs.atlassian.net/browse/DM-46458>`_)
- In ``maintel/offset_camera_hexapod.py``, update ``offsets_to_apply`` to have defaults to 0. (`DM-46636 <https://rubinobs.atlassian.net/browse/DM-46636>`_)
- In ``maintel/offset_m2_hexapod.py``, update ``offsets_to_apply`` to have defaults to 0. (`DM-46636 <https://rubinobs.atlassian.net/browse/DM-46636>`_)
- Fix in laser_tracker/align.py comparison for tolerance. (`DM-46978 <https://rubinobs.atlassian.net/browse/DM-46978>`_)
- In maintel/take_aos_sequence_comcam.py, update take_aos_sequence to wait for images to be ingested in OODS before sending request to the OCPS. (`DM-46978 <https://rubinobs.atlassian.net/browse/DM-46978>`_)
- Fix use_ocps in wep_config for base_close_loop.py (`DM-46978 <https://rubinobs.atlassian.net/browse/DM-46978>`_)
- Fix instrument to ComCam in take_aos_sequence.py. (`DM-46978 <https://rubinobs.atlassian.net/browse/DM-46978>`_)
- Fix take_aos_sequence so intra has negative focusZ and extra positive focusZ. (`DM-46978 <https://rubinobs.atlassian.net/browse/DM-46978>`_)
- In maintel/focus_sweep_comcam, add StateTransition to ComCam Usages. (`DM-46978 <https://rubinobs.atlassian.net/browse/DM-46978>`_)
- In maintel/apply_dof, fix configure method to skip parameters that are not DOFName. (`DM-46978 <https://rubinobs.atlassian.net/browse/DM-46978>`_)
- In ``maintel/take_aos_sequence_comcam.py``, wait for all images to be ingested before starting OCPS process. (`DM-47381 <https://rubinobs.atlassian.net/browse/DM-47381>`_)
- In ``maintel/base_close_loop.py``, flush evt_degreeOfFreedom. (`DM-47381 <https://rubinobs.atlassian.net/browse/DM-47381>`_)
- In ``maintel/take_aos_sequence_comcam.py``, fix call to ready_to_take_data. (`DM-47381 <https://rubinobs.atlassian.net/browse/DM-47381>`_)
- Use supplemented_group_id ``maintel/base_close_loop.py``. (`DM-47641 <https://rubinobs.atlassian.net/browse/DM-47641>`_)


Performance Enhancement
-----------------------

- - Add note configuration parameter to `take_triplet_comcam.py` (`DM-46451 <https://rubinobs.atlassian.net/browse/DM-46451>`_)
- In ``set_summary_state.py``, increase command timeout from 10 to 60 s. (`DM-46636 <https://rubinobs.atlassian.net/browse/DM-46636>`_)
- In ``maintel/apply_dof.py``, add new configuration parameter to ignore degrees of freedom. (`DM-46636 <https://rubinobs.atlassian.net/browse/DM-46636>`_)
- Add note configuration parameter to `close_loop_comcam.py` script (`DM-46695 <https://rubinobs.atlassian.net/browse/DM-46695>`_)
- Update `take_triplet_comcam` to `take_aos_sequence_comcam.py` to allow for doublets and triplets. (`DM-46864 <https://rubinobs.atlassian.net/browse/DM-46864>`_)
- Add dofs vector option for `apply_dof.py` script. (`DM-46883 <https://rubinobs.atlassian.net/browse/DM-46883>`_)
- Improve the ``maintel/m1m3/check_hardpoint.py`` to run tests concurrently. (`DM-47223 <https://rubinobs.atlassian.net/browse/DM-47223>`_)
- In ``maintel/take_aos_sequence_comcam.py``, allow for only intra and extra focal pair. (`DM-47744 <https://rubinobs.atlassian.net/browse/DM-47744>`_)


Other Changes and Additions
---------------------------

- In ``mtdome/crawl_az.py``, fix typo. (`DM-46636 <https://rubinobs.atlassian.net/browse/DM-46636>`_)


v1.38.0 (2024-09-03)
====================

New Features
------------

- Add ``PrepareForCO2Cleanup`` SAL script for ``auxtel``. (`DM-42061 <https://rubinobs.atlassian.net/browse/DM-42061>`_)
- Add `DisableATAOSCorrections` SAL script for `auxtel`. (`DM-44630 <https://rubinobs.atlassian.net/browse/DM-44630>`_)
- - Modified `SetSummaryState` to send all instances of a CSC to a desired state. (`DM-45216 <https://rubinobs.atlassian.net/browse/DM-45216>`_)
- Add configuration option to pass focus sweep steps as array to ``BaseFocusSweep``. (`DM-45266 <https://rubinobs.atlassian.net/browse/DM-45266>`_)
- Update unit tests for BaseBlockScript to work with the latest version of salobj that adds support for block to BaseScript. (`DM-45637 <https://rubinobs.atlassian.net/browse/DM-45637>`_)
- In ``base_track_target.py``, remove limits from azimuth configuration schema. (`DM-45747 <https://rubinobs.atlassian.net/browse/DM-45747>`_)


Bug Fixes
---------

- Update configuration of ``BaseFocusSweep`` to avoid re-centering a user provided set of focus steps via the ``focus_steps_sequence`` config. (`DM-45774 <https://rubinobs.atlassian.net/browse/DM-45774>`_)


Performance Enhancement
-----------------------

- * Fixed `maintel/base_closed_loop.py` to pass filter name and rotator angle to OFC. (`DM-45551 <https://rubinobs.atlassian.net/browse/DM-45551>`_)


v1.37.0 (2024-07-30)
====================

New Features
------------

- Add `EnableATAOSCorrections` SAL script for `auxtel`. (`DM-44629 <https://rubinobs.atlassian.net/browse/DM-44629>`_)
- Introduced auxtel/atdome/disable_dome_following.py, a script for disabling ATDome following. (`DM-44766 <https://rubinobs.atlassian.net/browse/DM-44766>`_)
- Introduced auxtel/atdome/enable_dome_following.py, a script for enabling ATDome following. (`DM-44766 <https://rubinobs.atlassian.net/browse/DM-44766>`_)
- Introduced auxtel/atdome/slew_dome.py, a script for slewing the AT dome. (`DM-44766 <https://rubinobs.atlassian.net/browse/DM-44766>`_)
- Add ``EnableDomeFollowing`` and ``DisableDomeFollowing`` scripts for ``MTDome``. (`DM-44916 <https://rubinobs.atlassian.net/browse/DM-44916>`_)
- Enhance `base_block_script.py` to support Block Test Cases by adding regular expression-based parsing for program names, accommodating both `BLOCK-NNNN` for block tickets and `BLOCK-TNNNN`` for block test cases. (`DM-45229 <https://rubinobs.atlassian.net/browse/DM-45229>`_)
- Add takeStutteredComCam script. (`DM-45350 <https://rubinobs.atlassian.net/browse/DM-45350>`_)
- Add takeStutteredLSSTCam script. (`DM-45350 <https://rubinobs.atlassian.net/browse/DM-45350>`_)
- Add more metadata to the exposures in the LATISS daytime checkout (`DM-45351 <https://rubinobs.atlassian.net/browse/DM-45351>`_)


Bug Fixes
---------

- In latiss_checkout.py, remove metadata from the bias test frame, add group_id to the engtest image and set the instrument configuration to be empty/empty (no optical element in the beam). (`DM-45232 <https://rubinobs.atlassian.net/browse/DM-45232>`_)


v1.36.1 (2024-07-15)
====================

Documentation
-------------

- Update version history notes and towncrier ticket links to use cloud jira project. (`DM-44192 <https://rubinobs.atlassian.net/browse/DM-44192>`_)


v1.36.0 (2024-07-15)
====================

New Features
------------

- - Introduced a suite of scripts for taking focus sweep images with LSSTCam, LSSTComCam and LATISS:
    - `base_focus_sweep.py`: Base class for running common operations.
    - `focus_sweep_lsstcam.py`: Script for taking focus sweep images with Simonyi Telescope using LSSTCam.
    - `focus_sweep_comcam.py`: Script for taking focus sweep images with Simonyi Telescope using LSSTComCam.
    - `focus_sweep_latiss.py`: Script for taking focus sweep images with Auxiliary Telescope using LATISS. (`DM-44821 <https://rubinobs.atlassian.net/browse/DM-44821>`_)
- In maintel/take_image_comcam, remove setting instrument_setup_time.

  This will fallback to the default value of 0. (`DM-44824 <https://rubinobs.atlassian.net/browse/DM-44824>`_)
- In maintel/offset_camera_hexapod, fix units for xyz offsets in the script configuration. (`DM-44824 <https://rubinobs.atlassian.net/browse/DM-44824>`_)
- Update ``maintel/m1m3/enable_m1m3_slew_controller_flags.py`` to simplify how it sets the slew flags.

  Set one at a time in a loop instead of trying to set them all at once. (`DM-44824 <https://rubinobs.atlassian.net/browse/DM-44824>`_)
- In ``maintel/take_triplet_comcam.py``, update how ComCam is setup to include state transition events. (`DM-44824 <https://rubinobs.atlassian.net/browse/DM-44824>`_)
- In maintel/take_triplet_comcam, use suplemented group id for the CWFS images. (`DM-44824 <https://rubinobs.atlassian.net/browse/DM-44824>`_)
- Update BaseTrackTarget to add a sleep between stop tracking and start tracking when doing track_azel. (`DM-44824 <https://rubinobs.atlassian.net/browse/DM-44824>`_)
- In maintel/offset_m2_hexapod, fix units for xyz offsets in the script configuration. (`DM-44824 <https://rubinobs.atlassian.net/browse/DM-44824>`_, `DM-44824 <https://rubinobs.atlassian.net/browse/DM-44824>`_)


Bug Fixes
---------

- In auxtel/daytime_checkout/atpneumatics_checkout.py, await for atcs.start_task after creating ATCS instance. (`DM-45154 <https://rubinobs.atlassian.net/browse/DM-45154>`_)
- In auxtel/calibrations/power_on_atcalsys, increase timeout waiting for the lamp to be ready to 20 minutes.

  This operations takes at least 15 minutes on the CSC side, so having the script timeout also be 15 minutes causes frequent issues running the script. (`DM-45154 <https://rubinobs.atlassian.net/browse/DM-45154>`_)
- In auxtel/calibrations/power_off_atcalsys, increase timeout waiting for the lamp to be ready to 20 minutes.

  This operations takes at least 15 minutes on the CSC side. This script had it as 16 minutes but increasing it further helps reduce false timeout issues. (`DM-45154 <https://rubinobs.atlassian.net/browse/DM-45154>`_)


v1.35.0 (2024-06-17)
====================

New Features
------------

- In ``auxtel/calibrations/power_on_atcalsys.py``, change ``configure_monochromator`` method to use the ``updateMonochromatorSetup`` command. (`DM-44674 <https://rubinobs.atlassian.net/browse/DM-44674>`_)
- Add ``OffsetM2Hexapod`` script.

  This is basically a copy of the OffsetCameraHexapod Script but will move m2 hexapod instead. (`DM-44674 <https://rubinobs.atlassian.net/browse/DM-44674>`_)
- In ``base_take_image``, add FOCUS to the list of valid image types. (`DM-44674 <https://rubinobs.atlassian.net/browse/DM-44674>`_)
- In ``maintel/take_triplet_comcam.py``, add feature to ignore components in MTCS and ComCam. (`DM-44674 <https://rubinobs.atlassian.net/browse/DM-44674>`_)
- In ``auxtel/calibrations/power_on_atcalsys.py``, update default entrance/exit slit widths to new max range. (`DM-44674 <https://rubinobs.atlassian.net/browse/DM-44674>`_)


v1.34.0 (2024-06-10)
====================

New Features
------------

- Add new ``auxtel/atdome`` scripts and unit tests to open and close the dome dropout door,
  including wind speed checks before opening. (`DM-41806 <https://rubinobs.atlassian.net/browse/DM-41806>`_)
- In auxtel/calibrations/power_on_atcalsys.py, update grating_type enumerations and default value. (`DM-44231 <https://rubinobs.atlassian.net/browse/DM-44231>`_)
- Add new ``maintel/take_triplet_comcam`` script and unit tests to take a triplet (intra focal, extra focal, and in-focus image) sequence with ComCam. (`DM-44317 <https://rubinobs.atlassian.net/browse/DM-44317>`_)
- Add new auxtel run_calibration_sequence script. (`DM-44454 <https://rubinobs.atlassian.net/browse/DM-44454>`_)
- Add TRACK_AZEL mode to base_track_target.py (`DM-44611 <https://rubinobs.atlassian.net/browse/DM-44611>`_)


Bug Fixes
---------

- Some bugfixes to the maintel base_close_loop script and expanding the script configuration to allow passing overrided to the wep pipeline. (`DM-44028 <https://rubinobs.atlassian.net/browse/DM-44028>`_)
- Fix issue with offset_atcs.
  When calling ``ATCS.offset_radec`` there is no relative/absolute arguments. (`DM-44231 <https://rubinobs.atlassian.net/browse/DM-44231>`_)


v1.33.0 (2024-04-24)
====================

New Features
------------

- In ``maintel/base_close_loop``, add feature to ignore individual MTCS components. (`DM-43740 <https://rubinobs.atlassian.net/browse/DM-43740>`_)
- In ``base_take_image.py``, add CWFS to the list of valid image types. (`DM-43740 <https://rubinobs.atlassian.net/browse/DM-43740>`_)
- In ``maintel/offset_camera_hexapod``, add feature to ignore individual MTCS components. (`DM-43740 <https://rubinobs.atlassian.net/browse/DM-43740>`_)


Bug Fixes
---------

- In base_close_loop.py, adding await to cmd_runWEP (`DM-43740 <https://rubinobs.atlassian.net/browse/DM-43740>`_)
- In base_close_loop.py, fixing move_camera_hexapod in base_close_loop.py (`DM-43740 <https://rubinobs.atlassian.net/browse/DM-43740>`_)
- In ``base_close_loop.py``, move hexapod back to focus after intra/extra images (`DM-43740 <https://rubinobs.atlassian.net/browse/DM-43740>`_)
- In ``maintel/base_close_loop``, remove await from flush function. (`DM-43740 <https://rubinobs.atlassian.net/browse/DM-43740>`_)


v1.32.0 (2024-04-11)
====================

New Features
------------

- Add new ``auxtel/atdome`` scripts and unit tests to open, close, and home the dome. (`DM-42269 <https://rubinobs.atlassian.net/browse/DM-42269>`_)
- In `data/scripts` add executable scripts to interact with OCS Scheduler:

   - `ocs/scheduler/enable.py`: It enables the OCS Scheduler.
   - `ocs/scheduler/load_snapshot.py`: It loads a snapshot into the OCS Scheduler.
   - `ocs/scheduler/resume.py`: It resumes the OCS Scheduler.
   - `ocs/scheduler/standby.py`: It puts the OCS Scheduler into standby mode.
   - `ocs/scheduler/stop.py`: It stops the OCS Scheduler. (`DM-43547 <https://rubinobs.atlassian.net/browse/DM-43547>`_)
- Add script to run blocks from the Scheduler. 

  In ``scheduler/testutils/``, add feature to mock addBlock cmd. (`DM-43548 <https://rubinobs.atlassian.net/browse/DM-43548>`_)


v1.31.0 (2024-03-28)
====================

New Features
------------

- Extended the `slew_ephem_target` functionality of the `base_tcs` to `base_track_target`, enabling the tracking of targets based on ephemeris data for both Simonyi and Auxiliary telescopes. (`DM-41340 <https://rubinobs.atlassian.net/browse/DM-41340>`_)
- Add a new ``maintel/take_image_anycam.py`` script to take data with any of the Simonyi cameras concurrently. (`DM-42516 <https://rubinobs.atlassian.net/browse/DM-42516>`_)
- Update the following scripts to block scripts:

    - ``maintel/laser_tracker/shut_down``.

    - ``maintel/laser_tracker/set_up``.

    - ``maintel/laser_tracker/measure``.

    - ``maintel/laser_tracker/align``.

  Add Script to move the dome.

  In ``auxtel/prepare_for/vent``:

    - remove azimuth constraints for venting.

    - adjust elevation limit to allow venting at elevations higher than 5 degrees.

    - Partially open ATDome when venting.

  Ignore m1m3 in offset_mtcs.

  In ``take_image_anycam``, add the ability to ignore a component when initializing mtcs.

  In ``base_track_target``, load local catalog.

  In ``base_take_image``:

    - Make sure filter is of type string.
    - Add a configuration parameter to allow specifying a "slew_time" (in seconds).
    - Return the full filter name when retrieving filter name for configuration.

  In ``take_image_comcam``, add a configuration option to specify data is being taken with comcam in simulation mode.

  Add new ``maintel/mtdome/crawl_az.py`` script to move the MTDome is a particular direction. (`DM-43038 <https://rubinobs.atlassian.net/browse/DM-43038>`_)
  - In ``base_take_image.py``, add new section to populate additional optional nextVisit metadata as part of config. 
  - In ``maintel/take_image_comcam.py`` and ``maintel/take_image_lsstcam``, add hooks for nextVisit metadata. 
  - In ``auxtel/take_image_latiss.py``, add hooks for nextVisit metadata. (`DM-43298 <https://rubinobs.atlassian.net/browse/DM-43298>`_)


Bug Fixes
---------

- In ``point_azel``, fix error configuring TCS.

  In ``take_image_anycam``, fix call to ``take_imgtype``. (`DM-43038 <https://rubinobs.atlassian.net/browse/DM-43038>`_)


Performance Enhancement
-----------------------

- In ``maintel/take_image_anycam.py``, a ``nimages`` parameter has been added to facilitate capturing multiple images with a single exposure time.
  This eliminates the necessity of entering ``exp_times`` as a list when multiple images with identical exposure times are required.
  Furthermore, this enhancement aligns with the standard behavior of other image capture scripts. (`DM-43030 <https://rubinobs.atlassian.net/browse/DM-43030>`_)


v1.30.0 (2024-02-13)
====================

New Features
------------

- Add new `mute_alarms` SAL Script. (`DM-41610 <https://rubinobs.atlassian.net/browse/DM-41610>`_)
- Introduce SAL scripts to enable/disable M2 closed-loop. (`DM-41611 <https://rubinobs.atlassian.net/browse/DM-41611>`_)
- Introduce SAL scripts to enable/disable hexapods compensation mode of the Simonyi Survey Telescope:
  - ``enable_hexapods_compensation``: enable hexapods compensation mode.
  - ``disable_hexapods_compensation``: disable hexapods compensation mode. (`DM-41799 <https://rubinobs.atlassian.net/browse/DM-41799>`_)
- Introduce a SAL Script to set the m1m3 slew controller flags. (`DM-42403 <https://rubinobs.atlassian.net/browse/DM-42403>`_)
- Update ``maintel/home_both_axes`` to add a configuration option to ignore the m1m3.

  Update ``auxtel/prepare_for/vent`` to not partially open the dome. (`DM-42690 <https://rubinobs.atlassian.net/browse/DM-42690>`_)


Bug Fixes
---------

- `run_m2_actuator_bump_test` call updated to use `actuator` instead of `actuator_id` (`DM-42105 <https://rubinobs.atlassian.net/browse/DM-42105>`_)
- Increase `timeout_std`` to 130s for `laser_tracker/measure.py` script (`DM-42339 <https://rubinobs.atlassian.net/browse/DM-42339>`_)


Other Changes and Additions
---------------------------

- Update all m1m3 scripts to only setup their instance of the ``MTCS`` class during the configuration stage.

  This also removes the ``add_remotes`` parameter from their initialization.
  Instantiation of the class is now done in the ``configure`` method.

  Update ``tests/test_maintel_lasertracker_align.py`` unit tests to remove use of the ``add_remotes`` parameter and to create a dry test instance of ``MTCS`` during the initialization phase.

  In ``maintel/laser_tracker/align.py``, update script to only create instance of ``MTCS`` and the ``RemoteGroup`` for the laser tracker in the configuration stage.
  This also removes the need for the ``add_remotes`` parameter.

  Update ``tests/test_maintel_disable_hexapod_compensation_mode.py`` to ignore order of calls in the assertion.

  Update ``tests/test_auxtel_atpneumatics_checkout.py`` unit tests to remove use of the ``add_remotes`` parameter and to create a dry test instance of ``ATCS`` during the initialization phase.

  Update ``tests/test_maintel_home_both_axes.py`` unit tests to remove use of the ``add_remotes`` parameter and to create a dry test instance of ``MTCS`` during the initialization phase.

  In ``python/lsst/ts/standardscripts/maintel/home_both_axes.py``, update script to only create instance of ``MTCS`` in the configuration stage.
  This also removes the need for the ``add_remotes`` parameter.

  In ``auxtel/daytime_checkout/atpneumatics_checkout.py``, update Script to only create instance of ``ATCS`` during the configuration stage.
  This also removes the need of the ``add_remotes`` parameter in the initialization.

  Update unit tests for m1m3 scripts.
  This basically removes the add_remotes parameter when instantiating the Scripts class and creates an instance of ``MTCS`` configured with ``DryRun`` for testing.

  Update all m1m3 scripts to only setup their instance of the ``MTCS`` class during the configuration stage.
  This also removes the ``add_remotes`` parameter from their initialization.
  Instantiation of the class is now done in the ``configure`` method. (`DM-42517 <https://rubinobs.atlassian.net/browse/DM-42517>`_)


v1.29.0 (2023-12-14)
====================

New Features
------------

- Add new maintel/laser_tracker/measure.py script, unit test, and executable. (`DM-42122 <https://rubinobs.atlassian.net/browse/DM-42122>`_)


Bug Fixes
---------

- In ``maintel/m1m3/check_actuators``, add a timer task that will be set to wait for ``time_one_bump`` 
  when a bump test fails.

  In ``base_point_azel``, call ``configure_tcs`` in the ``configure`` method. (`DM-41870 <https://rubinobs.atlassian.net/browse/DM-41870>`_)


v1.28.0 (2023-11-29)
====================

New Features
------------

- Introduce the ``maintel/m2/check_actuators.py`` script.
  This new addition allows users to run M2 bump tests. (`DM-40554 <https://rubinobs.atlassian.net/browse/DM-40554>`_)
- Introduce the ``pause_queue.py`` script. This new addition allows users to sent an indefinte pause command to the script queue. (`DM-41094 <https://rubinobs.atlassian.net/browse/DM-41094>`_)
- Extended the `slew_to_planet` functionality of the `base_tcs` to `base_track_target`, enabling the tracking of planets of the Solar system for both Simonyi and Auxiliary telescopes. (`DM-41338 <https://rubinobs.atlassian.net/browse/DM-41338>`_)
- In ``latiss_take_sequence``, add optional config parameters for ra, dec, and rot_sky for script queue metadata. (`DM-41538 <https://rubinobs.atlassian.net/browse/DM-41538>`_)


Bug Fixes
---------

- In ``prepare_for/onsky``, make sure the start_task is awaited.

  In ``maintel/laser_tracker/align.py``, fix scalar units.

  In ``maintel/mtrotator/move_rotator``, fix call to ``mtcs.move_rotator``. (`DM-41538 <https://rubinobs.atlassian.net/browse/DM-41538>`_)


v1.27.0 (2023-11-02)
====================

New Features
------------

- Update ``maintel/track_target_and_take_image_gencam_.py`` to allow taking images with multiple cameras. (`DM-38338 <https://rubinobs.atlassian.net/browse/DM-38338>`_)
- Add new maintel/take_image_lsstcam.py script, test and executable. (`DM-40208 <https://rubinobs.atlassian.net/browse/DM-40208>`_)
- Add new base_close_loop.py script, and executable. 
  This script allows to run the closed loop, that is, taking images, processing them, and apply ts_ofc corrections.

  Add new maintel/close_loop_comcam.py script, unit test, and executable.

  Add new maintel/close_loop_lsstcam.py script, unit test, and executable. (`DM-40213 <https://rubinobs.atlassian.net/browse/DM-40213>`_)
- Add new maintel/apply_dof.py script, unit test, and executable. (`DM-40219 <https://rubinobs.atlassian.net/browse/DM-40219>`_)
- In ``auxtel/prepare_for/onsky``, allow users to ignore components from ``LATISS`` as well. (`DM-40580 <https://rubinobs.atlassian.net/browse/DM-40580>`_)
- Introduced the following scripts to position the respective telescope based on (az, el, rot_tel) coordinates:

  - `maintel/point_azel.py`: tailored for the Main Telescope.
  - `auxtel/point_azel.py`: designed for the Auxiliary Telescope.

  The specialized methods were built upon the generic module `base_point_azel.py`. (`DM-40700 <https://rubinobs.atlassian.net/browse/DM-40700>`_)
- * Add new ``maintel/mtrotator/move_rotator.py`` SAL Script. (`DM-41081 <https://rubinobs.atlassian.net/browse/DM-41081>`_)
- Introduce the ``sleep.py`` script. This new addition allows users to sent a sleep command to the script queue for a desired duration. (`DM-41082 <https://rubinobs.atlassian.net/browse/DM-41082>`_)
- Add new maintel/stop_rotator.py script, executable, and unit test. (`DM-41083 <https://rubinobs.atlassian.net/browse/DM-41083>`_)


Other Changes and Additions
---------------------------

- Update several unit tests to be compatible with the kafka version of salobj.
  This should be a backward compatible change and should work with both DDS and kafka versions of salobj.

  In ``base_script_test_case.py``, add compatibility with the kafka version of salobj.

  In ``auxtel/prepare_for/onsky.py``, postpone creating ``ATMCS`` and ``LATISS`` classes to the configure method.
  This is more inline with the most recent guidelines for script development and improve reliability for the kafka version of salobj.

  Update ``.gitignore`` to ignore files from ruff and clang-format.

  In ``tests/test_system_wide_shutdown.py``, make test resilient to changing order of the component index.

  In ``system_wide_shutdown``:

      - Update to get list of components from ts-xml and to limit the number of components it checks at a single time.

      - Treat non-index component the same way indexed components are treated, e.g. wait for at least ``min_heartbeat`` heartbeat events before deming it alive. (`DM-40580 <https://rubinobs.atlassian.net/browse/DM-40580>`_)


v1.26.0 (2023-10-06)
====================

New Features
------------

- Add new maintel/offset_camera_hexapod.py script, unit test, and executable. (`DM-40852 <https://rubinobs.atlassian.net/browse/DM-40852>`_)


Documentation
-------------

- Integrate towncrier for release notes and change log management (`DM-40534 <https://rubinobs.atlassian.net/browse/DM-40534>`_)


Other Changes and Additions
---------------------------

- Update the `lsst.ts.criopy`` imports in `m1m3/check_actuators.py`` to ensure compatibility with the latest criopy version. 
  The `ts.criopy.M1M3FATable` table is now living in the `ts.xml.tables.m1m3` module. (`DM-40534 <https://rubinobs.atlassian.net/browse/DM-40534>`_)
- In ``auxtel/calibrations/power_off_atcalsys``, remove temporary work-around to missing ACK from faulty shutter limit switch. (`DM-40852 <https://rubinobs.atlassian.net/browse/DM-40852>`_)


v1.25.5
=======

* In ``auxtel/calibrations/power_off_atcalsys``, add temporary work-around to missing ACK from faulty shutter limit switch.
* In ``auxtel/daytime_checkout/slew_and_take_image_checkout``, add ``stop_tracking`` after ``point_azel``.

v1.25.4
=======

* In ``maintel/m1m3``, fix typo in import warning.


v1.25.3
=======

* In ``maintel/m1m3``, fix lsst.ts.xml imports for DetailedStates.


v1.25.2
=======

* In ``auxtel/calibrations/power_on_atcalsys.py``, add boolean config to use ATMonochromator, update unit test, and edit log message outputs.


v1.25.1
=======

* In ``auxtel/daytime_checkout/latiss_checkout.py`` script and unit test, add check to linear stage position.

v1.25.0
=======

* Add new ``auxtel/calibrations/power_off_atcalsys.py`` script, unit test and executable to turn off the ATCalSys white light.
* Add new ``auxtel/calibrations/power_on_atcalsys.py`` script, unit test and executable to turn on and set up the ATCalSys (ATWhiteLight and ATMonochromator) to take flats.

v1.24.2
=======

Update ``check_actuators.py`` to give the ability to ignore actuators in a bump test.

v1.24.1
=======

* In ``maintel/laser_tracker/align.py``:

  * Skip alignment if tolerances are zero.
  * Get last ``offsetPublished`` if new event is not available.
  * Fix enum values.
  * Skip error if laserTracker status is not available.

* In ``system_wide_shutdown.py``, add more logging information.
* Update ``tests/test_maintel_home_both_axes.py`` to check that force balance was disabled before homing.
* In ``maintel/home_both_axes.py``, update execution to switch off force balance before homing.

* Update Jenkinsfile to add ts_cRIOpy as an extra package.
* In ``maintel/m1m3/check_actuators.py``, update to use latest version of ts_cRIOpy package.

v1.24.0
=======

* Patch ``base_block_script.py`` to add ``test_case`` attribute.
* Add new ``maintel/m1m3/enable_m1m3_balance_system.py`` and ``maintel/m1m3/disable_m1m3_balance_system.py`` sal scripts and associated files.

v1.23.1
=======

* ``Jenkinsfile``: use the new shared library.
* In ``base_block_script.py``, update address of the camera image server at the summit.
* In ``pyproject.toml``, stop using pytest-black and pytest-flake8 plugins for unit tests.
* In ``base_track_target.py``, add ``slew_timeout`` configuration parameter.
* In ``maintel/move_p2p.py``:

  * Stop motion if script fails or is stopped.
  * Add ``move_timeout`` configuration parameter to allow users to control how long the move command can take, for long slews with reduced speed.

* In ``maintel/home_both_axes.py``, call start instead of set.

v1.23.0
=======

* In ``base_block_script.py``, expand ``BaseBlockScript`` functionality to support generating JIRA test case artifacts from scripts.

* Update ``MoveP2P`` script to add test step annotations.

* In ``utils.py``, add ``get_s3_bucket`` to generate a ``salobj.AsyncS3Bucket`` based on the running environment.

v1.22.0
=======

* Update the ``maintel/m1m3/check_actuators.py`` script with improved logging and detailed state assertions.

* Add new ``maintel/home_both_axes.py`` script to home both MTMount axes.

* Add new ``base_block_script.py``, which defines a base class for developing scripts to be executed as part of observing blocks.

* Convert ``base_track_target.py`` and all ``maintel/m1m3`` scripts to block scripts.

* In ``base_track_target.py``:

  * Add a new ``configure_tcs`` method that, by default, awaits for the ``tcs.start_task``.
  * Add support for configuring with sexagesimal strings coordinates.

* In ``maintel/track_target``, overwrites the new ``configure_tcs`` method from the base class to postpone creation of the ``tcs`` class until configuration stage.
  This will allow the script to startup and become alive more quickly, and will also prevent spending time loading ``MTCS`` for scripts that are misconfigured.

* In ``utils.py``:

  * Fix typo in ``format_as_list`` docstring.
  * Add new ``format_grid`` utility method.

* Add new ``MoveP2P`` maintel script.

v1.21.0
=======

* Add new ``maintel/m1m3/check_actuators.py`` script to run the actuators bump test.
* Add new ``maintel/m1m3/lower_m1m3.py`` sal script and associated files.
* Add new ``auxtel/offset_ataos.py`` script to offset the ATAOS.
* Add new ``maintel/m1m3/check_hardpoint.py`` script to check hardpoints.
* Add missing comment line in all script files.
* In ``auxtel/offset_ataos.py``, fix bug in call to resetOffset and change handling for reset all configuration.
* Update unit test for ``auxtel/offset_ataos.py``
* In ``auxtel/daytime_checkout/atpneumatics_checkout.py``, update detailed description.

v1.20.1
=======

* In ``prepare_for/vent``, fix passing ``partially_open_dome``.
* Update ``auxtel/latiss_take_sequence.py`` to configure synchronization between ``ATCS`` and ``LATISS``.
* Update ts-pre-commit configuration.
* In ``base_offset_tcs.py``:
  * Add new option to execute ``offset_pa``.
  * Add checkpoints for each action.

v1.20.0
=======

* Add new ``base_offset_tcs.py`` script to offset generic tcs class.
* Add new ``auxtel/offset_atcs.py`` script to offset the ATCS.
* Add new ``maintel/offset_,tcs.py`` script to offset the MTCS.

* Add new ``auxtel/latiss_take_sequence.py`` script, unit tests, and executables.
* Add new ``maintel/m1m3/raise_m1m3.py`` to raise MainTel M1M3 mirror.
* Add new ``laser_tracker/set_up.py`` script to set up and turn on the laser tracker.
* Add new ``laser_tracker/shut_down.py`` script to switch off the laser tracker.
* Add new ``laser_tracker/align.py`` script to align mtcs with laser tracker.
* Add new ``maintel/prepare_for/align.py`` script to prepare for align mtcs with laser tracker.

v1.19.2
=======

* In ``auxtel/daytime_checkout/slew_and_take_image_checkout.py``:
  * add check that M3 is in position for observations with LATISS
  * update unit test ``tests/test_auxtel_slew_and_take_image_checkout.py``

v1.19.1
=======

* In ``auxtel/daytime_checkout/atpneumatics_checkout.py``:
  * add slew to park position to ensure telescope is in safe range for ATAOS operation.
  * add sleep to allow mirror to arrive at commanded pressure before logging value.
  * add check that M1 arrives at pressure commanded by ATAOS after enable/disable.
  * update unit test ``tests/test_auxtel_atpneumatics_checkout.py``

v1.19.0
=======

* Update pre-commit to use black 23, isort 5.12 and check-yaml 4.4.

v1.18.0
=======

* Add new ``system_wide_shutdown`` script to help shutdown the entire system.
* In ``auxtel/daytime_checkout/`` update script metadata.duration values.

v1.17.0
=======

* In ``maintel/track_target_and_take_image_gencam.py``:

  * Update ``get_schema`` method to stop deleting ``band_filter`` from the required configuration attributes.

    Previously we thought it would be ok to remove this attribute from the configuration since the generic cameras, which this script is designed to work with, don't necessarily have a filter wheel or instrument configuration.
    But this oversight doesn't take into account the fact that this Script is designed to work with the Scheduler and, for this type of Script, we can not remove any of the basic set of required parameters.
    Adding new parameters is ok though.

    If calling this script from the script queue one can simply pass in an empty string for ``band_filter``.
    But, keep in mind this one in particular is designed to work with the Scheduler.

  * Update ``track_target_and_setup_instrument`` to pass in ``az_wrap_strategy`` to slew_icrs.

  * Implement new ``tcs`` abstract property introduced in ``BaseTrackTargetAndTakeImage``.

* In ``maintel/track_target_and_take_image_comcam.py``:

  * Update ``track_target_and_setup_instrument`` and ``_handle_slew_and_change_filter`` to pass in ``az_wrap_strategy``.

  * Implement new ``tcs`` abstract property introduced in ``BaseTrackTargetAndTakeImage``.

* In ``auxtel/track_target_and_take_image.py``, update ``track_target_and_setup_instrument`` to pass ``az_wrap_strategy`` to ``atcs.slew_icrs``.

* In ``base_track_target_and_take_image.py``:

  * Add ``az_wrap_strategy`` to the script configuration.

    This allows users to specify the azimuth wrap strategy the TCS should use when slewing to a target.
    The parameter is exposed as an enumeration with all the available options.
    Users select an option by adding one of the available strings.
    When configuring the Script, the ``configure`` method will convert the string into the appropriate enumeration, calling in the ``tcs`` property to return the ``WrapStrategy`` enumeration.

  * Update ``set_metadata`` to use ``get_estimated_time_on_target`` as the script estimated duration and also to fill up all the relevant metadata information.

    This update will make sure the ``nextVisit`` event published by this script has all the relevant information needed by prompt processing.

  * Add new method ``get_estimated_time_on_target`` that returns the estimated time on target, based on the script configuration.

    Having this method allows the Script to uniformly estimate its duration in different execution stages.

  * Add new ``tcs`` abstract property to ``BaseTrackTargetAndTakeImage``, which should return the instance of the tcs class on the script.

  This change goes in the direction of supporting higher level abstraction that require calling the TCS class from within the base class.

* In ``base_track_target``, add support for azimuth wrap strategy and differential tracking.

  * Include configuration parameters to allow users to specify values for azimuth wrap strategy and differential tracking.

  * Pass those values to ``slew_icrs`` and ``slew_object`` when running the script.

v1.16.1
=======

* Fix conda recipe by adding astroplan dependency and not running pytest.

v1.16.0
=======

* Add daytime_checkout SAL scripts, executables, and tests
* Move all "prepare_for" scripts to a submodule in auxtel.
* Add new ``prepare_for/vent.py``.
* Update pre-commit configuration.
* Run ``isort`` in the entire package.

v1.15.5
=======

* Update maintel/setup_mtcs.py
  * Now put the mount and the rotator into disabled state so they can share telemetry.
  * Do the homing of the mount

v1.15.4
=======

* Add maintel/track_target_and_take_image_comcam.py with new ``TrackTargetAndTakeImageGenCam``.
* Add unit tests for ``TrackTargetAndTakeImageGenCam``

v1.15.3
=======

* `BaseScriptTestCase` fix a potential unbound local variable error in ``check_executable``.
  This is only triggered if the process cannot be created or $PATH cannot be set, so it obscures some other problem.

v1.15.2
=======

* Update unit tests to be compatible with ts_salobj 7.2, while remaining backwards compatible.
* Remove unused dependencies, including ts_atdome, ts_atdometrajectory and ts_atmcssimulator.
* Modernize the CI Jenkinsfile.
* In ``auxtel/track_target_and_take_image.py``:
  * Use snaps instead of isolated observations when visit is standard.
  * Add a new configuration parameter "filter_suffix" to allow appending strings to the filter name.

v1.15.1
=======

* In python/lsst/ts/standardscripts/auxtel/track_target_and_take_image.py, implement new abstract method ``check_feasibility``.

* In python/lsst/ts/standardscripts/base_track_target_and_take_image.py, add new ``assert_feasibility`` abstract method to ``BaseTrackTargetAndTakeImage``, that is called before running to verify that the system is in a feasible state to execute the script.

* In python/lsst/ts/standardscripts/maintel/track_target_and_take_image_comcam.py, implement new abstract method ``assert_feasibility``.

v1.15.0
=======

* In ``BaseTrackTargetAndTakeImage``, add configuration parameter to allow specifying a camera playlist and, if specified, load it before running the script.

* In ``base_track_target_and_take_image``, improve checkpoints messages.

* In maintel/track_target_and_take_image_comcam.py implement ``load_playlist``.

* In auxtel/track_target_and_take_image, implement ``load_playlist`` method.

v1.14.3
=======

* In ``maintel/SetupMTCS``

  * fix bug that caused ``mtcs.raise_m1m3`` to start but not to complete.
  * fix ``mtcs.enable_compensation_mode`` argument.

v1.14.2
=======

* Create new script maintel/setup_mtcs.py with its associated class and unit tests.

v1.14.1
=======

* Update eups table to account for renaming of ts_ATMCSSimulator -> ts_atmcssimulator.
* Update conda recipe to improve handling python versions.

v1.14.0
=======

* Update build files to use pyproject.toml
* Update location of scripts directory
* Move scripts to python/.../data/scripts

v1.13.0
=======

* In ``BaseTrackTarget``:

  * Update schema to have a ``slew_icr`` session and a ``find_target`` session.
    The first works the same way the previous ra/dec parameters worked, the second will find a target around the specified az/el coordinate to track.

* In ``AuxTel/PrepareForOnsky`` add configuration to allow users to ignore certain CSCs.
* Add unit tests for ``prepare_for_onsky`` script.


v1.12.1
=======

* Wait for SalInfo instances to start before writing messages:

    * Call ``super().start()`` first in overrides of start methods.
    * test_auxtel_stop.py: await self.controller.start_task before writing.

* Remove ``cls`` argument from abstract static methods.
* doc/conf.py: make linters happier.
* git ignore .hypothesis.
* Use pre-commit to run flake8 and maintain black formatting.
* update build files to use ``pyproject.toml``.

v1.12.0
=======

* Add ``BaseTakeStuttered`` script to take stuttered images.
* In ``BaseTakeImage``, add option to take acquisition images.
* Add ``TakeStutteredLatiss`` script to take stuttered images with LATISS.
* In ``GetStdFlatDataset``, pass ``group_id`` to ``take_bias``, ``take_flats`` and ``take_darks`` to group data together.
* Update ``GetStdFlatDataset`` unit test to reduce script test time by reducing the exposure time for darks and using a smaller sequence of flat-fields.

v1.11.0
=======

* In ``auxtel/track_target_and_take_image`` implement taking data with n>1.
* Fix ``tests/test_auxtel_detector_characterization_std_flat_dataset.py`` to take into account snaps.
* In ``auxtel/track_target_and_take_image`` script, implement a rotator flipping routine.
  First it will try to slew the telescope with the provided rotation angle, if that doesn't work, flip 180 degrees and try again.
* Add unit tests for the load snapshot scheduler scripts.
* Add unit tests for the stop scheduler scripts.
* Add unit tests for the resume scheduler scripts.
* Add unit tests for the standby scheduler scripts.
* Add unit tests for the enable scheduler scripts.
* Add executables for the main telescope scheduler operational scripts.
* Add executables for the auxiliary telescope scheduler operational scripts.
* Add scheduler operations scripts for the Main Telescope.
* Add scheduler operations scripts for the Auxiliary Telescope.
* Add test utilities for the scheduler operational scripts.
* Add scheduler submodule with base scripts for operating the Scheduler.
  These are generic implementations that can be used for both the AT and MT schedulers.
* Update setup.cfg to specify async_mode for pytest.

v1.10.1
=======

* Make auxtel/prepare_for_onsky.py script not gather ATCS config and just assert enabled.

v1.10.0
=======

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
