# This is the instrument-specific file for the PS4000 series of instruments.
#
# pico-python is Copyright (c) 2013-2014 By:
# Colin O'Flynn <coflynn@newae.com>
# Mark Harfouche <mark.harfouche@gmail.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
This is the low level driver file for a specific Picoscope.

By this, I mean if parameters want to get passed as strings, they should be
handled by PSBase
All functions here should take things as close to integers as possible, the
only exception here is for array parameters. Array parameters should be passed
in a pythonic way through numpy since the PSBase class should not be aware of
the specifics behind how the clib is called.

The functions should not have any default values as these should be handled
by PSBase.

"""

from __future__ import division

import math

# to load the proper dll
import platform

# Do not import or use ill definied data types
# such as short int or long
# use the values specified in the h file
# float is always defined as 32 bits
# double is defined as 64 bits
from ctypes import byref, POINTER, create_string_buffer, c_float, \
    c_int16, c_int32, c_uint32, c_void_p
from ctypes import c_int32 as c_enum

from picobase import PSBase


class PS4000(PSBase):

    """The following are low-level functions for the PS4000."""

    LIBNAME = "ps4000"

    NUM_CHANNELS = 4
    CHANNELS     =  {"A": 0, "B": 1, "C": 2, "D": 3,
                     "External": 4, "MaxChannels": 4, "TriggerAux": 5}
    
    EXT_RANGE_VOLTS = 1

    #has_sig_gen = True
    WAVE_TYPES = {"Sine": 0, "Square": 1, "Triangle": 2,
                  "RampUp": 3, "RampDown": 4,
                  "Sinc": 5, "Gaussian": 6, "HalfSine": 7, "DCVoltage": 8,
                  "WhiteNoise": 9}

    SIGGEN_TRIGGER_TYPES = {"Rising": 0, "Falling": 1,
                            "GateHigh": 2, "GateLow": 3}
    SIGGEN_TRIGGER_SOURCES = {"None": 0, "ScopeTrig": 1, "AuxIn": 2,
                              "ExtIn": 3, "SoftTrig": 4, "TriggerRaw": 5}

    # This is actually different depending on the AB/CD models
    # I wonder how we could detect the difference between the oscilloscopes
    # I believe we can obtain this information from the setInfo function
    # by readign the hardware version
    # for the PS6403B version, the hardware version is "1 1",
    # an other possibility is that the PS6403B shows up as 6403 when using
    # VARIANT_INFO and others show up as PS6403X where X = A,C or D

    AWGPhaseAccumulatorSize = 32
    AWGBufferAddressWidth   = 14
    AWGMaxSamples           = 2 ** AWGBufferAddressWidth

    AWGDACInterval          = 5E-9  # in seconds
    AWGDACFrequency         = 1 / AWGDACInterval

    # Note this is NOT what is written in the Programming guide as of version
    # 10_5_0_28
    # This issue was acknowledged in this thread
    # http://www.picotech.com/support/topic13217.html
    AWGMaxVal               = 0x0FFF
    AWGMinVal               = 0x0000

    AWG_INDEX_MODES = {"Single": 0, "Dual": 1, "Quad": 2}

    def __init__(self, serialNumber=None, connect=True):
        """Load DLL etc"""
        if platform.system() == 'Linux':
            from ctypes import cdll
            self.lib = cdll.LoadLibrary("lib" + self.LIBNAME + ".so")
        else:
            from ctypes import windll
            self.lib = windll.LoadLibrary(self.LIBNAME + ".dll")

        super(PS4000, self).__init__(serialNumber, connect)

    def _lowLevelOpenUnit(self, sn):
        c_handle = c_int16()
        if sn is not None:
            serialNullTermStr = create_string_buffer(sn)
        else:
            serialNullTermStr = None
        # Passing None is the same as passing NULL
        m = self.lib.ps4000OpenUnit(byref(c_handle), serialNullTermStr)
        self.checkResult(m)
        self.handle = c_handle.value

    def _lowLevelCloseUnit(self):
        m = self.lib.ps4000CloseUnit(c_int16(self.handle))
        self.checkResult(m)

    def _lowLevelSetChannel(self, chNum, enabled, coupling, VRange, VOffset,
                            BWLimited):
        m = self.lib.ps4000SetChannel(c_int16(self.handle), c_enum(chNum),
                                      c_int16(enabled), c_enum(coupling),
                                      c_enum(VRange), c_float(VOffset),
                                      c_enum(BWLimited))
        self.checkResult(m)

    def _lowLevelStop(self):
        m = self.lib.ps4000Stop(c_int16(self.handle))
        self.checkResult(m)

    def _lowLevelGetUnitInfo(self, info):
        s = create_string_buffer(256)
        requiredSize = c_int16(0)

        m = self.lib.ps4000GetUnitInfo(c_int16(self.handle), byref(s),
                                       c_int16(len(s)), byref(requiredSize),
                                       c_enum(info))
        self.checkResult(m)
        if requiredSize.value > len(s):
            s = create_string_buffer(requiredSize.value + 1)
            m = self.lib.ps4000GetUnitInfo(c_int16(self.handle), byref(s),
                                           c_int16(len(s)),
                                           byref(requiredSize), c_enum(info))
            self.checkResult(m)

        return s.value

    def _lowLevelFlashLed(self, times):
        m = self.lib.ps4000FlashLed(c_int16(self.handle), c_int16(times))
        self.checkResult(m)

    def _lowLevelSetSimpleTrigger(self, enabled, trigsrc, threshold_adc,
                                  direction, timeout_ms, auto):
        m = self.lib.ps4000SetSimpleTrigger(
            c_int16(self.handle), c_int16(enabled),
            c_enum(trigsrc), c_int16(threshold_adc),
            c_enum(direction), c_uint32(timeout_ms), c_int16(auto))
        self.checkResult(m)

    def _lowLevelRunBlock(self, numPreTrigSamples, numPostTrigSamples,
                          timebase, oversample, segmentIndex):
        timeIndisposedMs = c_int32()
        m = self.lib.ps4000RunBlock(
            c_int16(self.handle), c_uint32(numPreTrigSamples),
            c_uint32(numPostTrigSamples), c_uint32(timebase),
            c_int16(oversample), byref(timeIndisposedMs),
            c_uint32(segmentIndex), c_void_p(), c_void_p())
        self.checkResult(m)
        return timeIndisposedMs.value

    def _lowLevelIsReady(self):
        ready = c_int16()
        m = self.lib.ps4000IsReady(c_int16(self.handle), byref(ready))
        self.checkResult(m)
        if ready.value:
            return True
        else:
            return False

    def _lowLevelGetTimebase(self, tb, noSamples, oversample, segmentIndex):
        """ returns (timeIntervalSeconds, maxSamples). """
        maxSamples = c_int32()
        sampleRate = c_float()

        m = self.lib.ps4000GetTimebase2(c_int16(self.handle), c_uint32(tb),
                                        c_uint32(noSamples), byref(sampleRate),
                                        c_int16(oversample), byref(maxSamples),
                                        c_uint32(segmentIndex))
        self.checkResult(m)

        return (sampleRate.value / 1.0E9, maxSamples.value)

    def getTimeBaseNum(self, sampleTimeS):
        """Convert sample time in S to something to pass to API Cal."""
        maxSampleTime = (((2 ** 32 - 1) - 4) / 156250000)

        if sampleTimeS < 6.4E-9:
            st = math.floor(math.log(sampleTimeS * 5E9, 2))
            st = max(st, 0)
        else:
            #Otherwise in range 2^32-1
            if sampleTimeS > maxSampleTime:
                sampleTimeS = maxSampleTime

            st = math.floor((sampleTimeS * 156250000) + 4)

        # is this cast needed?
        st = int(st)
        return st

    def getTimestepFromTimebase(self, timebase):
        if timebase < 5:
            dt = 2. ** timebase / 5E9
        else:
            dt = (timebase - 4.) / 156250000.
        return dt

    def _lowLevelSetAWGSimpleDeltaPhase(self, waveform, deltaPhase,
                                        offsetVoltage, pkToPk, indexMode,
                                        shots, triggerType, triggerSource):
        """ waveform should be an array of shorts. """

        waveformPtr = waveform.ctypes.data_as(POINTER(c_int16))

        m = self.lib.ps4000SetSigGenArbitrary(
            c_int16(self.handle),
            c_uint32(int(offsetVoltage * 1E6)),  # offset voltage in microvolts
            c_uint32(int(pkToPk * 1E6)),         # pkToPk in microvolts
            c_uint32(int(deltaPhase)),           # startDeltaPhase
            c_uint32(int(deltaPhase)),           # stopDeltaPhase
            c_uint32(0),                         # deltaPhaseIncrement
            c_uint32(0),                         # dwellCount
            waveformPtr,                         # arbitraryWaveform
            c_int32(len(waveform)),              # arbitraryWaveformSize
            c_enum(0),                           # sweepType for deltaPhase
            c_enum(0),            # operation (adding random noise and whatnot)
            c_enum(indexMode),                   # single, dual, quad
            c_uint32(shots),
            c_uint32(0),                         # sweeps
            c_uint32(triggerType),
            c_uint32(triggerSource),
            c_int16(0))                          # extInThreshold
        self.checkResult(m)

    def _lowLevelSetDataBuffer(self, channel, data, downSampleMode, segmentIndex):
        """
        data should be a numpy array.

        Be sure to call _lowLevelClearDataBuffer
        when you are done with the data array
        or else subsequent calls to GetValue will still use the same array.

        segmentIndex is unused, but required by other versions of the API (eg PS5000a)
        """
        dataPtr = data.ctypes.data_as(POINTER(c_int16))
        numSamples = len(data)

        m = self.lib.ps4000SetDataBuffer(c_int16(self.handle), c_enum(channel),
                                         dataPtr, c_uint32(numSamples),
                                         c_enum(downSampleMode))
        self.checkResult(m)

    def _lowLevelClearDataBuffer(self, channel, segmentIndex):
        """data should be a numpy array."""
        m = self.lib.ps4000SetDataBuffer(c_int16(self.handle), c_enum(channel),
                                         c_void_p(), c_uint32(0), c_enum(0))
        self.checkResult(m)

    def _lowLevelGetValues(self, numSamples, startIndex, downSampleRatio,
                           downSampleMode, segmentIndex):
        numSamplesReturned = c_uint32()
        numSamplesReturned.value = numSamples
        overflow = c_int16()
        m = self.lib.ps4000GetValues(
            c_int16(self.handle), c_uint32(startIndex),
            byref(numSamplesReturned), c_uint32(downSampleRatio),
            c_enum(downSampleMode), c_uint32(segmentIndex),
            byref(overflow))
        self.checkResult(m)
        return (numSamplesReturned.value, overflow.value)

    def _lowLevelSetSigGenBuiltInSimple(self, offsetVoltage, pkToPk, waveType,
                                        frequency, shots, triggerType,
                                        triggerSource):
        # TODO, I just noticed that V2 exists
        # Maybe change to V2 in the future
        m = self.lib.ps4000SetSigGenBuiltIn(
            c_int16(self.handle),
            c_int32(int(offsetVoltage * 1000000)),
            c_int32(int(pkToPk        * 1000000)),
            c_int16(waveType),
            c_float(frequency), c_float(frequency),
            c_float(0), c_float(0), c_enum(0), c_enum(0),
            c_uint32(shots), c_uint32(0),
            c_enum(triggerType), c_enum(triggerSource),
            c_int16(0))
        self.checkResult(m)

    ####################################################################
    # Untested functions below                                         #
    #                                                                  #
    ####################################################################

    def _lowLevelEnumerateUnits():
        count = c_int16(0)
        m = self.lib.ps4000EnumerateUnits(byref(count), None, None)
        self.checkResult(m)
        # a serial number is rouhgly 8 characters
        # an extra character for the comma
        # and an extra one for the space after the comma?
        # the extra two also work for the null termination
        sertialLth = count.value * (8 + 2)
        serials = create_string_buffer(sertialLth + 1)

        m = self.lib.ps4000EnumerateUnits(byref(count), serials, byref(serialLth))
        self.checkResult(m)

        serialList = str(serials).split(',')

        serialList = [x.strip() for x in serialList]

        return serialList

    def _lowLevelGetAnalogueOffset(self, range, coupling):
        # TODO, populate properties with this function
        maximumVoltage = c_float()
        minimumVoltage = c_float()

        m = self.lib.ps4000GetAnalogueOffset(
            c_int16(self.handle), c_enum(range), c_enum(coupling),
            byref(maximumVoltage), byref(minimumVoltage))
        self.checkResult(m)

        return (maximumVoltage.value, minimumVoltage.value)

    def _lowLevelGetMaxDownSampleRatio(self, noOfUnaggregatedSamples,
                                       downSampleRatioMode, segmentIndex):
        maxDownSampleRatio = c_uint32()

        m = self.lib.ps4000GetMaxDownSampleRatio(
            c_int16(self.handle), c_uint32(noOfUnaggregatedSamples), byref(maxDownSampleRatio),
            c_enum(downSampleRatioMode), c_uint32(segmentIndex))
        self.checkResult(m)

        return maxDownSampleRatio.value

    def _lowLevelGetNoOfCaptures():
        nCaptures = c_utin32()

        m = self.lib.ps4000GetNoOfCaptures(c_int16(self.handle), byref(nCaptures))
        self.checkResult(m)

        return nCaptures.value

    def _lowLevelGetTriggerTimeOffset(self, segmentIndex):
        time = c_uint64()
        timeUnits = c_enum()

        m = self.lib.ps4000GetTriggerTimeOffset64(c_int16(self.handle), byref(time),
                                                  byref(timeUnits), c_uint32(segmentIndex))
        self.checkResult(m)

        if timeUnits == 0:    # PS4000_FS
            return time.value * 1E-15
        elif timeUnits == 1:  # PS4000_PS
            return time.value * 1E-12
        elif timeUnits == 2:  # PS4000_NS
            return time.value * 1E-9
        elif timeUnits == 3:  # PS4000_US
            return time.value * 1E-6
        elif timeUnits == 4:  # PS4000_MS
            return time.value * 1E-3
        elif timeUnits == 5:  # PS4000_S
            return time.value * 1E0

    def _lowLevelMemorySegments(self, nSegments):
        nMaxSamples = c_utin32()

        m = self.lib.ps4000MemorySegments(c_int16(self.handle),
                                          c_uint32(nSegments), byref(nMaxSamples))
        self.checkResult(m)

        return nMaxSamples.value

    def _lowLevelOpenUnitAsync(self, sn):
        c_status = c_int16()
        if sn is not None:
            serialNullTermStr = create_string_buffer(sn)
        else:
            serialNullTermStr = None

        # Passing None is the same as passing NULL
        m = self.lib.ps4000OpenUnitAsync(byref(c_status), serialNullTermStr)
        self.checkResult(m)

        return c_status.value

    def _lowLevelOpenUnitProgress(self):
        complete = c_int16()
        progressPercent = c_int16()
        handle = c_int16()

        m = self.lib.ps4000OpenUnitProgress(byref(handle), byref(progressPercent), byref(complete))
        self.checkResult(m)

        # if we only wanted to return one value, we could do somethign like
        # progressPercent = progressPercent * (1 - 0.1 * complete)
        return (progressPercent, complete)

    def _lowLevelSetDataBuffers(self, channel, bufferMax, bufferMin, downSampleRatioMode):
        bufferMaxPtr = bufferMax.ctypes.data_as(POINTER(c_int16))
        bufferMinPtr = bufferMin.ctypes.data_as(POINTER(c_int16))
        bufferLth = len(bufferMax)

        m = self.lib.ps4000SetDataBuffers(c_int16(self.handle), c_enum(channel),
                                          bufferMaxPtr, bufferMinPtr, c_uint32(bufferLth),
                                          c_enum(downSampleRatioMode))
        self.checkResult(m)

    def _lowLevelClearDataBuffers(self, channel):
        m = self.lib.ps4000SetDataBuffers(c_int16(self.handle), c_enum(channel),
                                          c_void_p(), c_void_p(), c_uint32(0), c_enum(0))
        self.checkResult(m)

    # Bulk values.
    # These would be nice, but the user would have to provide us
    # with an array.
    # we would have to make sure that it is contiguous amonts other things
    def _lowLevelGetValuesBulk(self, numSamples, fromSegmentIndex, toSegmentIndex,
                               downSampleRatio, downSampleRatioMode):
        noOfSamples = c_uint32(numSamples)
        overflow = c_int16()

        m = self.lib.ps4000GetvaluesBulk(
            c_int16(self.handle),
            c_uint32(fromSegmentIndex), c_uint32(toSegmentIndex),
            c_uint32(downSampleRatio), c_enum(downSampleRatioMode),
            byref(overflow))
        self.checkResult(m)
        return (noOfSamples.value, overflow.value)

    def _lowLevelSetDataBufferBulk(self, channel, buffer, waveform, downSampleRatioMode):
        bufferPtr = buffer.ctypes.data_as(POINTER(c_int16))
        bufferLth = len(buffer)

        m = self.lib.ps4000SetDataBufferBulk(
            c_int16(self.handle),
            c_enum(channel), bufferPtr, c_uint32(bufferLth),
            c_uint32(waveform), c_enum(downSampleRatioMode))
        self.checkResult(m)

    def _lowLevelSetDataBuffersBulk(self, channel, bufferMax, bufferMin,
                                    waveform, downSampleRatioMode):
        bufferMaxPtr = bufferMax.ctypes.data_as(POINTER(c_int16))
        bufferMinPtr = bufferMin.ctypes.data_as(POINTER(c_int16))

        bufferLth = len(bufferMax)

        m = self.lib.ps4000SetDataBuffersBulk(
            c_int16(self.handle), c_enum(channel),
            bufferMaxPtr, bufferMinPtr, c_uint32(bufferLth),
            c_uint32(waveform), c_enum(downSampleRatioMode))
        self.checkResult(m)

    def _lowLevelSetNoOfCaptures(self, nCaptures):
        m = self.lib.ps4000SetNoOfCaptures(c_int16(self.handle), c_uint32(nCaptures))
        self.checkResult(m)

    # ETS Functions
    def _lowLevelSetEts():
        pass

    def _lowLevelSetEtsTimeBuffer():
        pass

    def _lowLevelSetEtsTimeBuffers():
        pass

    def _lowLevelSetExternalClock():
        pass

    # Complicated triggering
    # need to understand structs for this one to work
    def _lowLevelIsTriggerOrPulseWidthQualifierEnabled():
        pass

    def _lowLevelGetValuesTriggerTimeOffsetBulk():
        pass

    def _lowLevelSetTriggerChannelConditions():
        pass

    def _lowLevelSetTriggerChannelDirections():
        pass

    def _lowLevelSetTriggerChannelProperties():
        pass

    def _lowLevelSetPulseWidthQualifier():
        pass

    def _lowLevelSetTriggerDelay():
        pass

    # Async functions
    # would be nice, but we would have to learn to implement callbacks
    def _lowLevelGetValuesAsync():
        pass

    def _lowLevelGetValuesBulkAsync():
        pass

    # overlapped functions
    def _lowLevelGetValuesOverlapped():
        pass

    def _lowLevelGetValuesOverlappedBulk():
        pass

    # Streaming related functions
    def _lowLevelGetStreamingLatestValues():
        pass

    def _lowLevelNoOfStreamingValues(self):
        noOfValues = c_uint32()

        m = self.lib.ps4000NoOfStreamingValues(c_int16(self.handle), byref(noOfValues))
        self.checkResult(m)

        return noOfValues.value

    def _lowLevelRunStreaming():
        pass

    def _lowLevelStreamingReady():
        pass
