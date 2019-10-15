ChangeLog
=========


1.4.0 (2019-10-15)
------------------

* Configuration file can be given via command line option (a5b9933).
* When a preset name is given on the command line, activate it
  also when jack-select was not already running (439cdf5).
* Updated man page (a1c6596).
* Major internal code restructuring (0f27755).
* Map all JACK settings to a D-BUS type explicitly (8c158d89).
* Support 'slave-driver' engine parameter (this is not present in
  QjackCtl's configuration file, though) (2601189).


1.3.1 (2019-09-25)
------------------

* Added support for missing JACK engine and driver parameters (a5705b8).
* Fixed and improved QjackCtl settings to JACK parameters mapping (878b8ca).
* Improved debug logging of setting changes when activating a preset
  (c865bab, a5705b8).


1.3.0 (2019-04-18)
------------------

* Added command line option ``-i``, ``--ignore-default`` to ignore the
  '(default)' preset if any other presets are stored in the QjackCtl
  configuration.
* Fixed handling different variants of the presence / non-presence of the
  '(default)' preset when reading the QjackCtl configuration.
* Added command line option ``--version`` to show the program version.
* Updated the UNIX manual page.


1.2.0 (2019-04-17)
------------------

* Now detects changes in connected ALSA devices and enables/disables
  menu entries for presets, which use these devices.
* Added command line option ``-a``, ``--no-alsa-monitor`` to disable
  ALSA device monitoring and filtering.
* Made some logging improvements.


1.1.2 (2018-09-15)
------------------

* Display underscores in configuration preset names as spaces in menu.


1.1.1 (2018-09-04)
------------------

* Exit cleanly without traceback on INT signal.
* Correctly parse QjackCtl.conf having only one default preset.


1.1.0 (2016-12-25)
------------------

* Add command line option to activate default JACK configuration preset.


1.0 (2016-05-30)
----------------

* First stable release.
