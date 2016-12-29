#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from ctypes import (c_bool, c_char_p, c_int, c_uint, c_ulong, c_void_p, byref, cdll,
                    create_string_buffer, sizeof)
from enum import IntEnum


log = logging.getLogger(__name__)


class LibAsoundError(Exception):
    pass


class SndPcmStream(IntEnum):
    PLAYBACK = 0
    CAPTURE = 1


class SndPcmFormat(IntEnum):
    S8 = 0
    U8 = 1
    S16_LE = 2
    S16_BE = 3
    U16_LE = 4
    U16_BE = 5
    S24_LE = 6
    S24_BE = 7
    U24_LE = 8
    U24_BE = 9
    S32_LE = 10
    S32_BE = 11
    U32_LE = 12
    U32_BE = 13
    FLOAT_LE = 14
    FLOAT_BE = 15
    FLOAT64_LE = 16
    FLOAT64_BE = 17
    IEC958_SUBFRAME_LE = 18
    IEC958_SUBFRAME_BE = 19
    MU_LAW = 20
    A_LAW = 21
    IMA_ADPCM = 22
    MPEG = 23
    GSM = 24
    SPECIAL = 31
    S24_3LE = 32
    S24_3BE = 33
    U24_3LE = 34
    U24_3BE = 35
    S20_3LE = 36
    S20_3BE = 37
    U20_3LE = 38
    U20_3BE = 39
    S18_3LE = 40
    S18_3BE = 41
    U18_3LE = 42
    U18_3BE = 43


PCM_RATES = (
    5512,
    8000,
    11025,
    16000,
    22050,
    32000,
    44100,
    48000,
    64000,
    88200,
    96000,
    176400,
    192000
)
PCM_BUFFER_SIZES = (
    32,
    64,
    128,
    256,
    512,
    1024,
    2048,
    4096
)
SND_PCM_NONBLOCK = 1

_lib = cdll.LoadLibrary("libasound.so.2")
_lib.snd_ctl_card_info_get_id.restype = c_char_p
_lib.snd_ctl_card_info_get_name.restype = c_char_p
_lib.snd_pcm_info_get_id.restype = c_char_p
_lib.snd_pcm_info_get_name.restype = c_char_p
_lib.snd_pcm_info_get_subdevice_name.restype = c_char_p
_lib.snd_pcm_format_name.restype = c_char_p
_lib.snd_pcm_format_mask_test.restype = c_bool
_lib.snd_strerror.restype = c_char_p


def decode_format_mask(fmask):
    return ((fmt, _lib.snd_pcm_format_name(c_int(fmt)).decode())
            for fmt in SndPcmFormat
            if _lib.snd_pcm_format_mask_test(fmask, c_int(fmt)))


def check_call(fn, args, msg="{errmsg}", **kwargs):
    if '{errmsg' not in msg:
        msg += ' {errmsg}'
    err = fn(*args)
    if err < 0:
        raise LibAsoundError(msg.format(errmsg=_lib.snd_strerror(err), **kwargs))


def get_cards(stream=SndPcmStream.PLAYBACK):

    if stream not in SndPcmStream:
        raise Exception("Unknown stream type: {}".format(stream))

    cards = {}
    c_card = c_int(-1)
    c_dev = c_int(-1)
    c_min = c_uint()
    c_max = c_uint()
    c_min_long = c_ulong()
    c_max_long = c_ulong()
    c_handle = c_void_p()
    c_pcm = c_void_p()
    c_info = (c_void_p * int(_lib.snd_ctl_card_info_sizeof() / sizeof(c_void_p)))()
    c_pcminfo = (c_void_p * int(_lib.snd_pcm_info_sizeof() / sizeof(c_void_p)))()
    c_pars = (c_void_p * int(_lib.snd_pcm_hw_params_sizeof() / sizeof(c_void_p)))()
    c_fmask = (c_void_p * int(_lib.snd_pcm_format_mask_sizeof() / sizeof(c_void_p)))()
    s_stream = 'playback' if stream == SndPcmStream.PLAYBACK else 'capture'

    # card enumeration
    while True:
        _lib.snd_card_next(byref(c_card))
        if c_card.value < 0:
            log.debug("End of card enumeration list reached.")
            break

        cards[c_card.value] = card = {}
        hwdev = "hw:{}".format(c_card.value)
        b_hwdev = create_string_buffer(hwdev.encode())

        err = _lib.snd_ctl_open(byref(c_handle), b_hwdev, c_card)
        if err < 0:
            _lib.snd_ctl_close(c_handle)
            continue

        _lib.snd_ctl_card_info(c_handle, c_info)

        card["id"] = _lib.snd_ctl_card_info_get_id(c_info).decode()
        card["name"] = _lib.snd_ctl_card_info_get_name(c_info).decode()
        log.debug("Discovered card %(id)s (%(name)s).", card)
        card["devices"] = devices = {}

        # device enumeration
        while True:
            _lib.snd_ctl_pcm_next_device(c_handle, byref(c_dev))
            if c_dev.value < 0:
                log.debug("End of device enumeration list reached.")
                break

            _lib.snd_pcm_info_set_device(c_pcminfo, c_dev)
            _lib.snd_pcm_info_set_subdevice(c_pcminfo, 0)
            _lib.snd_pcm_info_set_stream(c_pcminfo, c_int(stream))

            err = _lib.snd_ctl_pcm_info(c_handle, c_pcminfo)
            if err < 0:
                log.debug("Could not get info for PCM %s device #%i.", s_stream, c_dev.value)
                continue

            devices[c_dev.value] = device = {}
            device["id"] = bytes.decode(_lib.snd_pcm_info_get_id(c_pcminfo))
            device["name"] = bytes.decode(_lib.snd_pcm_info_get_name(c_pcminfo))
            device['stream'] = stream
            log.debug("Discovered %s device %s (%s).", s_stream, device['id'], device['name'])

            # count subdevices
            nsubd = _lib.snd_pcm_info_get_subdevices_count(c_pcminfo)
            log.debug("Device has %i subdevice(s).", nsubd)
            device["subdevices"] = subdevices = []

            if not nsubd:
                continue

            # open sound device
            hwdev = "hw:{},{}".format(c_card.value, c_dev.value)
            b_hwdev = create_string_buffer(hwdev.encode('ascii'))

            try:
                check_call(_lib.snd_pcm_open, (byref(c_pcm), b_hwdev, c_int(stream),
                           SND_PCM_NONBLOCK), "Could not open PCM {stream} device '{dev}'.",
                           stream=s_stream, dev=hwdev)

                # Get hardware parameter space
                check_call(_lib.snd_pcm_hw_params_any, (c_pcm, c_pars),
                           "Could not get params for {stream} device '{dev}'.", stream=s_stream,
                           dev=hwdev)

                # Get supported channel counts
                check_call(_lib.snd_pcm_hw_params_get_channels_min, (c_pars, byref(c_min)),
                           "Could not get minimum channels count.")

                check_call(_lib.snd_pcm_hw_params_get_channels_max, (c_pars, byref(c_max)),
                           "Could not get maximum channels count.")

                log.debug("Min/max channels: %i, %i", c_min.value, c_max.value)
                device["channels"] = [
                    ch for ch in range(c_min.value, c_max.value + 1)
                    if _lib.snd_pcm_hw_params_test_channels(c_pcm, c_pars, ch) == 0]

                # Get supported sample rates
                check_call(_lib.snd_pcm_hw_params_get_rate_min, (c_pars, byref(c_min)),
                           "Could not get minimum sample rate.")

                check_call(_lib.snd_pcm_hw_params_get_rate_max, (c_pars, byref(c_max)),
                           "Could not get maximum sample rate.")

                log.debug("Min/max sample rate: %i, %i", c_min.value, c_max.value)
                device["rate"] = [
                    rate for rate in PCM_RATES
                    if c_min.value <= rate <= c_max.value and
                    _lib.snd_pcm_hw_params_test_rate(c_pcm, c_pars, rate, 0) == 0]

                # Get supported sample formats
                check_call(_lib.snd_pcm_hw_params_get_format_mask, (c_pars, c_fmask),
                           "Could not get sample formats.")

                log.debug("Sample format mask: %r", list(c_fmask))
                device["format"] = tuple(decode_format_mask(c_fmask))

                # Get supported period times
                check_call(_lib.snd_pcm_hw_params_get_periods_min, (c_pars, byref(c_min)),
                           "Could not get minimum periods count.")

                check_call(_lib.snd_pcm_hw_params_get_periods_max, (c_pars, byref(c_max), 0),
                           "Could not get minimum periods count.")

                log.debug("Min/max periods count: (%i, %i)", c_min.value, c_max.value)
                device['periods'] = (c_min.value, c_max.value)

                # Get supported buffer sizes
                check_call(_lib.snd_pcm_hw_params_get_buffer_size_min,
                           (c_pars, byref(c_min_long), 0),
                           "Could not get minimum buffer time.")

                check_call(_lib.snd_pcm_hw_params_get_buffer_size_max,
                           (c_pars, byref(c_max_long), 0),
                           "Could not get minimum buffer time.")

                log.debug("Min/max buffer time: (%i, %i) us", c_min_long.value, c_max_long.value)
                device['buffer_size'] = [
                    size for size in PCM_BUFFER_SIZES
                    if c_min_long.value <= size <= c_max_long.value and
                    _lib.snd_pcm_hw_params_test_buffer_size(c_pcm, c_pars, size) == 0]

                # List subdevices
                for subd in range(0, nsubd):
                    _lib.snd_pcm_info_set_subdevice(c_pcminfo, c_int(subd))
                    sub_name = _lib.snd_pcm_info_get_subdevice_name(c_pcminfo).decode()
                    log.debug("Subdevice: %s", sub_name)
                    subdevices.append(sub_name)
            except LibAsoundError as exc:
                log.warning(exc)
            finally:
                _lib.snd_pcm_close(c_pcm)

        _lib.snd_ctl_close(c_handle)

    return cards


class AlsaInfo:
    def __init__(self):
        self._playback = get_cards()
        self._capture = get_cards(SndPcmStream.CAPTURE)

    @property
    def playback_devices(self):
        devs = []
        for card, info in self._playback.items():
            devs.append('hw:%s' % info['id'])
            devs.append('hw:%i' % card)

            for dev, dinfo in info['devices'].items():
                devs.append('hw:%i,%i' % (card, dev))
                devs.append('hw:%s,%i' % (info['id'], dev))
                devs.append('hw:%s,%s' % (info['id'], dinfo['id']))

        return devs

    @property
    def capture_devices(self):
        devs = []
        for card, info in self._capture.items():
            devs.append('hw:%s' % info['id'])
            devs.append('hw:%i' % card)

            for dev, dinfo in info['devices'].items():
                devs.append('hw:%i,%i' % (card, dev))
                devs.append('hw:%s,%i' % (info['id'], dev))
                devs.append('hw:%s,%s' % (info['id'], dinfo['id']))

        return devs

    @property
    def devices(self):
        devs = set(self.playback_devices)
        return list(devs.union(self.capture_devices))


if __name__ == "__main__":
    import pprint
    import sys

    logging.basicConfig(level=logging.DEBUG if '-v' in sys.argv[1:] else logging.INFO,
                        format="[%(name)s] %(levelname)s: %(message)s")

    if '-r' in sys.argv[1:]:
        pprint.pprint(get_cards(SndPcmStream.CAPTURE))
    else:
        pprint.pprint(get_cards())
