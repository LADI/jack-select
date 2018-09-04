#!/usr/bin/env python
# -*- coding: utf-8 -*-

import setuptools


setuptools.setup(
    name="jack-select",
    version="1.1.1",
    url="https://github.com/SpotlightKid/jack-select",
    author="Christopher Arndt",
    author_email="chris@chrisarndt.de",
    description="A systray app to set the JACK configuration from QjackCtl "
                "presets via DBus",
    keywords="JACK,systray,GTK,DBus,audio",
    packages=setuptools.find_packages(),
    include_package_data=True,
    install_requires=[
        'PyGObject',
        'dbus-python',
        'pyxdg'
    ],
    entry_points = {
        'console_scripts': [
            'jack-select = jackselect.jackselect:main',
        ]
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Environment :: X11 Applications :: GTK',
        'Topic :: Multimedia :: Sound/Audio'
    ],
)
