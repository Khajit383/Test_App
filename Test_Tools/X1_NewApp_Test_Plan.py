#!/usr/bin/env python

"""
This application presents a 'console' prompt to the user asking for commands.

The 'readrecord' and 'writerecord' commands are used with record oriented files,
and the 'readstream' and 'writestream' commands are used with stream oriented
files.
"""

import random
# import copy
import time
from datetime import datetime
from fpdf import FPDF
import os
import sys
from tabulate import tabulate
#
# from collections import defaultdict
# from bacpypes.debugging import bacpypes_debugging, ModuleLogger
import json
import pyfiglet

# from mycmd import *

from bacpypes.errors import *
from bacpypes.basetypes import *
from bacpypes.apdu import *

from bacpypes.comm import bind
from bacpypes.udp import UDPActor, UDPDirector
from bacpypes.debugging import bacpypes_debugging, ModuleLogger, xtob
from bacpypes.consolelogging import ConfigArgumentParser
from bacpypes.consolecmd import ConsoleCmd

from bacpypes.core import run, enable_sleeping, deferred
from bacpypes.iocb import IOCB

from bacpypes.pdu import Address, GlobalBroadcast, LocalBroadcast, RemoteBroadcast

from bacpypes.app import BIPSimpleApplication
from bacpypes.local.device import LocalDeviceObject

from bacpypes.npdu import WhoIsRouterToNetwork

from bacpypes.comm import PDU

from bacpypes.debugging import bacpypes_debugging, ModuleLogger
from bacpypes.consolelogging import ConfigArgumentParser
from bacpypes.consolecmd import ConsoleCmd

from bacpypes.core import run, enable_sleeping
from bacpypes.iocb import IOCB

from bacpypes.pdu import Address
from bacpypes.object import get_object_class, Object, ReadableProperty, \
    WritableProperty, register_object_type, LoopObject

from bacpypes.object import get_datatype as _get_datatype

from bacpypes.apdu import SimpleAckPDU, \
    ReadPropertyRequest, ReadPropertyACK, ReadPropertyMultipleACK, WritePropertyRequest
from bacpypes.primitivedata import Null, Atomic, Boolean, Unsigned, Integer, \
    Real, Double, OctetString, CharacterString, BitString, Date, Time, ObjectIdentifier, CharacterString
from bacpypes.constructeddata import Array, Any, AnyAtomic, ListOf

from bacpypes.netservice import NetworkServiceElement

from bacpypes.app import BIPSimpleApplication
from bacpypes.local.device import LocalDeviceObject

from bacpypes.bvll import Result, WriteBroadcastDistributionTable, \
    ReadBroadcastDistributionTable, ReadBroadcastDistributionTableAck, \
    ForwardedNPDU, RegisterForeignDevice, ReadForeignDeviceTable, \
    ReadForeignDeviceTableAck, FDTEntry, DeleteForeignDeviceTableEntry, \
    DistributeBroadcastToNetwork, OriginalUnicastNPDU, \
    OriginalBroadcastNPDU

from bacpypes.pdu import RemoteStation

from time import sleep
from datetime import datetime
import webRestApi
from math import isclose

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# who_is_counter = defaultdict(int)
# i_am_counter = defaultdict(int)
acknowledgeAlarmEarlierTime = False
acknowledgeAlarmWrongType = False
iut_address = "192.168.1.100"
iut_address_list = {} #{'1': "192.168.1.100", '2': "192.168.1.110" }
default_BTL_addresses = []

lastEventNotification = None
confirmedEventNotificationApduList = []
unconfirmedEventNotificationApduList = []

# reference a simple application
this_application = None

# Cannot use nonstandard properties.
# @register_object_type(vendor_id=5)
# class VAVLoopObject(LoopObject):
#
#     properties = [
#         WritableProperty(603, Boolean),
#         ReadableProperty(601, CharacterString),
#     ]
   
class XT_UI_Type(Enumerated):
    enumerations = \
        {    'XT_UI_5V':0,
    'XT_UI_10V':1,
    'XT_UI_4TO20MA':2,
    'XT_UI_INTERNAL_NTC':3,
    'XT_UI_USER_NTC':4,
    'XT_UI_0TO20MA':5,
    'XT_UI_PULSE':6,
    'XT_UI_INTERNAL_NTC_10K2':7,
    'XT_UI_INTERNAL_NTC_3K':8,
    'XT_UI_INTERNAL_NTC_20K':9,
    'XT_UI_DIGITAL':10,
    'XT_UI_PT':11,
    'XT_UI_IR_EXT':12
    }

expand_enumerations(XT_UI_Type)

class VAV_OTA_FW_type(Enumerated):
    enumerations = \
    {'ESP32':0,
    'STM32':1,
    'Thermostat':2,
    'none':255
    }
expand_enumerations(VAV_OTA_FW_type)

xtec_datatypes = {
    "loop": {
        600: {"name": 'PROP_VAV_LOOP_DEADBAND', "type": Real},
        601: {"name": 'PROP_VAV_LOOP_MAX_INTEGRAL', "type": Real}
    },
    "analogInput": {
         512: {"name": 'PROP_XT_OFFSET', "type": Real},
         513: {"name": 'PROP_XT_UI_TYPE', "type": XT_UI_Type},
         514: {"name": 'PROP_XT_UI', "type": Unsigned},
         551: {"name": 'PROP_XT_AI_SAMPLES', "type": Unsigned},
         552: {"name": 'PROP_XT_AI_SCALE_MIN', "type": Real},
         553: {"name": 'PROP_XT_AI_SCALE_MAX', "type": Real}
    },
    "analogOutput": {
         522: {"name": 'PROP_XT_RANGE_MAX', "type": Real},
         523: {"name": 'PROP_XT_RANGE_MIN', "type": Real},
         524: {"name": 'PROP_XT_OUTPUT_MAX', "type": Real},
         525: {"name": 'PROP_XT_OUTPUT_MIN', "type": Real}
    },
    "analogOutput": {
         522: {"name": 'PROP_XT_RANGE_MAX', "type": Real},
         523: {"name": 'PROP_XT_RANGE_MIN', "type": Real},
         524: {"name": 'PROP_XT_OUTPUT_MAX', "type": Real},
         525: {"name": 'PROP_XT_OUTPUT_MIN', "type": Real}
    },
    "binaryInput": {
         517: {"name": 'PROP_XT_DELAY_ON', "type": Unsigned},
         518: {"name": 'PROP_XT_DELAY_OFF', "type": Unsigned},
         514: {"name": 'PROP_XT_UI', "type": Unsigned}
    },
    "file": {
        603: {"name": 'PROP_VAV_OTA_FW_TYPE', "type": VAV_OTA_FW_type},
        606: {"name": 'PROP_VAV_OTA_FW_MD5', "type": CharacterString}
    }
}

def value_to_string(value):
    if isinstance(value,PriorityArray):
        pa = []
        for x in value:
            k = x.dict_contents().keys()
            for v in k:
                pa.append(x.dict_contents()[v])
        value = pa
    if isinstance(value,TimeStamp):
        v = value.dict_contents()
        if 'time' in v:
            value = Time(v['time'])
        if 'dateTime' in v:
            value = v['dateTime']
        if 'sequenceNumber' in v:
            value = v['sequenceNumber']
    if isinstance(value,DateTime):
        v = value.dict_contents()
        value = v
        # print(v)
        # for k in v.keys():
        #     print(k, v[k])
        # if 'date' in v:
        #     print(Date(v['date']))
        #     print(Time(v['time']))
    if isinstance(value,ObjectPropertyReference):
        v = value.dict_contents()
        if 'objectIdentifier' in v and 'propertyIdentifier' in v:
            value = "{} {}".format(v['objectIdentifier'], v['propertyIdentifier'])
            if 'propertyArrayIndex' in v:
                value += "[{}]".format(v['propertyArrayIndex'])
    if isinstance(value,SetpointReference):
        v = value.dict_contents()
        if 'setpointReference' in v:
            v = v['setpointReference']
            if 'objectIdentifier' in v and 'propertyIdentifier' in v:
                value = "{} {}".format(v['objectIdentifier'], v['propertyIdentifier'])
                if 'propertyArrayIndex' in v:
                    value += "[{}]".format(v['propertyArrayIndex'])
        elif len(v):
            value = v
        else:
            value = '()'
    return value

@bacpypes_debugging
def get_datatype(object_type, propid, vendor_id=0):
    """Return the datatype for the property of an object."""
    prop = _get_datatype(object_type, propid, vendor_id)
    #print(prop)
    print(object_type)
    if prop is None:
        if propid.isnumeric():
            propid = int(propid)
        if object_type in xtec_datatypes.keys():
            if propid in xtec_datatypes[object_type]:
                prop = xtec_datatypes[object_type][propid]['type']
        else:
            print ("prop is None", object_type, propid)

    return prop

class MessageStore():
    def __init__(self):
        self.address_list = []
        self.apdu_list = []

    def set_address_list(self, list):
        self.address_list = []
        for a in list:
            self.address_list.append(a.lower())

    def add_address(self, address):
            self.address_list.append(address.lower())

    def get_msg(self):
        return self.apdu_list

    def clear_msg(self):
        self.apdu_list = []

    def msg(self, apdu):
        if len(self.address_list) > 0:
            if self.address_list[0] == 'all' or apdu.dict_contents()['source'] in self.address_list:
                self.apdu_list.append(apdu)

msg_store = MessageStore()

def pa_to_array(PA):
    res = [None]*16
    try:
        pa = PA.dict_contents()
        for index, x in enumerate(pa):
            for y in x:
                if y != 'null':
                    print(index,y,x,x[y])
                    res[index] = x[y]
        return res
    except:
        return "error"
#
#   WhoIsIAmApplication
#

# class ChillerAlarmObject(Object):
#     objectType = 128
#     properties = \
#         [ ReadableProperty(528,Enumerated)
#         , ReadableProperty(529,Enumerated)
#         , ReadableProperty(530,Enumerated)
#         , ReadableProperty(531,Enumerated)
#         ]
#
# register_object_type(ChillerAlarmObject, vendor_id=979)

class UndefinedRequest(ConfirmedRequestSequence):
    serviceChoice = 40
    sequenceElements = \
        [ Element('objectIdentifier', ObjectIdentifier, 0)
        , Element('propertyIdentifier', PropertyIdentifier, 1)
        , Element('propertyArrayIndex', Unsigned, 2, True)
        ]

register_confirmed_request_type(UndefinedRequest)

class UndefinedRequest_13(ConfirmedRequestSequence):
    serviceChoice = 13
    sequenceElements = \
        [ Element('objectIdentifier', ObjectIdentifier, 0)
        , Element('propertyIdentifier', PropertyIdentifier, 1)
        , Element('propertyArrayIndex', Unsigned, 2, True)
        ]

register_confirmed_request_type(UndefinedRequest_13)


class UndefinedRequest_24(ConfirmedRequestSequence):
    serviceChoice = 24
    sequenceElements = \
        [ Element('objectIdentifier', ObjectIdentifier, 0)
        , Element('propertyIdentifier', PropertyIdentifier, 1)
        , Element('propertyArrayIndex', Unsigned, 2, True)
        ]

register_confirmed_request_type(UndefinedRequest_24)


class UndefinedRequest_25(ConfirmedRequestSequence):
    serviceChoice = 25
    sequenceElements = \
        [ Element('objectIdentifier', ObjectIdentifier, 0)
        , Element('propertyIdentifier', PropertyIdentifier, 1)
        , Element('propertyArrayIndex', Unsigned, 2, True)
        ]

register_confirmed_request_type(UndefinedRequest_25)


class UndefinedRequest_30(ConfirmedRequestSequence):
    serviceChoice = 30
    sequenceElements = \
        [ Element('objectIdentifier', ObjectIdentifier, 0)
        , Element('propertyIdentifier', PropertyIdentifier, 1)
        , Element('propertyArrayIndex', Unsigned, 2, True)
        ]

register_confirmed_request_type(UndefinedRequest_30)

class UndefinedRequest_31(ConfirmedRequestSequence):
    serviceChoice = 31
    sequenceElements = \
        [ Element('objectIdentifier', ObjectIdentifier, 0)
        , Element('propertyIdentifier', PropertyIdentifier, 1)
        , Element('propertyArrayIndex', Unsigned, 2, True)
        ]

register_confirmed_request_type(UndefinedRequest_31)

class UndefinedRequest_32(ConfirmedRequestSequence):
    serviceChoice = 32
    sequenceElements = \
        [ Element('objectIdentifier', ObjectIdentifier, 0)
        , Element('propertyIdentifier', PropertyIdentifier, 1)
        , Element('propertyArrayIndex', Unsigned, 2, True)
        ]

register_confirmed_request_type(UndefinedRequest_32)

class UndefinedRequest_33(ConfirmedRequestSequence):
    serviceChoice = 33
    sequenceElements = \
        [ Element('objectIdentifier', ObjectIdentifier, 0)
        , Element('propertyIdentifier', PropertyIdentifier, 1)
        , Element('propertyArrayIndex', Unsigned, 2, True)
        ]

register_confirmed_request_type(UndefinedRequest_33)

class DestinationList(Sequence):
    sequenceElements = \
        [ Element('destination1', Destination)
        , Element('destination2', Destination)
        ]

class DestinationList4(Sequence):
    sequenceElements = \
        [ Element('destination1', Destination)
        , Element('destination2', Destination)
        , Element('destination3', Destination)
        , Element('destination4', Destination)
        ]

class UDPActor1(UDPActor):
    def fred():
        print("UDPActor, fred")

    def indication(self, pdu):
        print("UDPActor1 indication")
        UDPActor.indication(self, pdu)

    def response(self, pdu):
        print("UDPActor1 response from {} {}".format(self.peer, pdu))
        UDPActor.response(self, pdu)

class BVLL_Capture():
    def __init__(self):
        self.apdu_list = []

    def clear_list(self):
        self.apdu_list = []

    def get_list(self):
        return self.apdu_list

    def confirmation(self, apdu):
        # print("BVLL_Capture, confirmation", apdu)
        try:
            self.apdu_list.append(apdu)
            # print(apdu.dict_contents())
        except Exception as error:
            print("BVLL_Capture {}".format(error))

    def indication(self, apdu):
        # print("BVLL_Capture, confirmation", apdu)
        try:
            self.apdu_list.append(apdu)
            # print(apdu.dict_contents())
        except Exception as error:
            print("BVLL_Capture {}".format(error))

class NSE_Capture(NetworkServiceElement):
    def __init__(self):
        self.npdu_list = []

    def clear_list(self):
        self.npdu_list = []

    def get_list(self):
        return self.npdu_list

    def confirmation(self, adapter, npdu):
        print("NSE_capture confirmation", adapter, npdu)

    def RejectMessageToNetwork(self, adapter, npdu):
        self.npdu_list.append(npdu)
        print("NSE_capture RejectMessageToNetwork", npdu.dict_contents())
        # print(adapter)
        # print(npdu)
        # print(npdu.debug_contents())

@bacpypes_debugging
class WhoIsIAmApplication(BIPSimpleApplication):
    # global lastEventNotification
    # global confirmedEventNotificationApduList
    # global unconfirmedEventNotificationApduList

    def __init__(self, device, address):
        if _debug: WhoIsIAmApplication._debug("__init__ %r %r", device, address)
        BIPSimpleApplication.__init__(self, device, address)

    def do_ConfirmedEventNotificationRequest(self, apdu):
        lastEventNotification = copy.deepcopy(apdu)
        confirmedEventNotificationApduList.append(copy.deepcopy(apdu))
        print("Confirmed Event Notification")
        BIPSimpleApplication.do_ConfirmedEventNotificationRequest(self, apdu)

    def do_UnconfirmedEventNotificationRequest(self, apdu):
        """Resond to a ConfirmedEventNotificationRequest"""
        global lastEventNotification
        global confirmedEventNotificationApduList
        global unconfirmedEventNotificationApduList
        if apdu.notifyType == "alarm":
            lastEventNotification = copy.deepcopy(apdu)
        unconfirmedEventNotificationApduList.append(copy.deepcopy(apdu))
        print ("Unconfirmed Event Notification")
        if apdu.ackRequired:
            ackReq = "ackRequired"
        else:
            ackReq = "noAck"

        # print ("\t{}\t{}\t{}\t{}\n\t{}\t{}->{}".format(
        #     apdu.initiatingDeviceIdentifier,
        #     apdu.eventObjectIdentifier,
        #     apdu.eventType,
        #     apdu.notifyType,
        #     ackReq,
        #     apdu.fromState,
        #     apdu.toState))
        # if apdu.eventValues:
        #     if apdu.eventValues.outOfRange:
        #         print ("\tvalue: {} Status Flags {} deadband {} exceededLimit {}".format(
        #             apdu.eventValues.outOfRange.exceedingValue,
        #             apdu.eventValues.outOfRange.statusFlags,
        #             apdu.eventValues.outOfRange.deadband,
        #             apdu.eventValues.outOfRange.exceededLimit))

    def do_WhoIsRequest(self, apdu):
        """Respond to a Who-Is request."""
        if _debug: WhoIsIAmApplication._debug("do_WhoIsRequest %r", apdu)

        # build a key from the source and parameters
        # key = (str(apdu.pduSource),
        #     apdu.deviceInstanceRangeLowLimit,
        #     apdu.deviceInstanceRangeHighLimit,
        #     )

        # count the times this has been received
        # who_is_counter[key] += 1

        # continue with the default implementation
        BIPSimpleApplication.do_WhoIsRequest(self, apdu)

    def do_IAmRequest(self, apdu):
        """Given an I-Am request, cache it."""
        if _debug: WhoIsIAmApplication._debug("do_IAmRequest %r", apdu)

        address = apdu.dict_contents()['source']
        print("I AM",address)
        if address not in iut_address_list.values():
            iut_address_list[str(len(iut_address_list) + 1)] = address
        # build a key from the source, just use the instance number
        # key = (str(apdu.pduSource),
        #     apdu.iAmDeviceIdentifier[1],
        #     )

        # count the times this has been received
        # i_am_counter[key] += 1

        # continue with the default implementation
        BIPSimpleApplication.do_IAmRequest(self, apdu)

    def confirmation(self, apdu):
        if _debug: WhoIsIAmApplication._debug("confirmation %r", apdu)
        print('confirmation')
        print(apdu)
        msg_store.msg(apdu)
        # print("Received Confirmation",apdu.dict_contents())
        # forward it along
        BIPSimpleApplication.confirmation(self, apdu)

    def indication(self, apdu):
        if _debug: WhoIsIAmApplication._debug("indication %r", apdu)
        # print('indication')
        # print(apdu)
        msg_store.msg(apdu)
        # try:
        #     print(apdu.dict_contents())
        #     print(apdu.debug_contents())
        # except Exception as error:
        #     print(None, name + error)

        msg_store.msg(apdu)
        # print("Received Indication",apdu.dict_contents())
        #
        # if (isinstance(apdu, IAmRequest)):
        #     print("Test1 received")
        # else:
        #     print("other indication", apdu)
        #     print(apdu.pduData)
        #     print(apdu.apdu_contents())
        #
        # if (isinstance(self._request, WhoIsRequest)) and (isinstance(apdu, IAmRequest)):
        #     device_type, device_instance = apdu.iAmDeviceIdentifier
        #     if device_type != 'device':
        #         raise DecodingError("invalid object type")
        #
        #     if (self._request.deviceInstanceRangeLowLimit is not None) and \
        #             (device_instance < self._request.deviceInstanceRangeLowLimit):
        #         pass
        #     elif (self._request.deviceInstanceRangeHighLimit is not None) and \
        #             (device_instance > self._request.deviceInstanceRangeHighLimit):
        #         pass
        #     else:
        #         # print out the contents
        #         sys.stdout.write('pduSource = ' + repr(apdu.pduSource) + '\n')
        #         sys.stdout.write('iAmDeviceIdentifier = ' + str(apdu.iAmDeviceIdentifier) + '\n')
        #         sys.stdout.write('maxAPDULengthAccepted = ' + str(apdu.maxAPDULengthAccepted) + '\n')
        #         sys.stdout.write('segmentationSupported = ' + str(apdu.segmentationSupported) + '\n')
        #         sys.stdout.write('vendorID = ' + str(apdu.vendorID) + '\n')
        #         sys.stdout.flush()

        # forward it along
        BIPSimpleApplication.indication(self, apdu)
#
#   TestConsoleCmd
#

def analog_obj_list_for_vav(ai=None, ao=None, av=None):
    list = []
    if ai is None:
        ai = []
        for i in range(1,5):
            ai.append(i)
    if ao is None:
        ao = []
        for i in range(1,4):
            ao.append(i)
    if av is None:
        av = []
        for i in range(1,59):
            av.append(i)

    for i in ai:
        list.append({"object": "analogInput:{}".format(i), "min":-99999, "max":99999})
    for i in ao:
        list.append({"object": "analogOutput:{}".format(i), "min":0, "max":100})
    for i in av:
        list.append({"object": "analogValue:{}".format(i), "min":-99999, "max":99999})
    return list

def binary_obj_list_for_vav(bi=None, bo=None, bv=None):
    list = []
    if bi is None:
        bi = []
        for i in range(1,3):
            bi.append(i)
    if bo is None:
        bo = []
        for i in range(1,8):
            bo.append(i)
    if bv is None:
        bv = []
        for i in range(1,28):
            bv.append(i)
    for i in bi:
        list.append({"object": "binaryInput:{}".format(i), "min":'inactive', "max":'active'})
    for i in bo:
        list.append({"object": "binaryOutput:{}".format(i), "min":'inactive', "max":'active'})
    for i in bv:
        list.append({"object": "binaryValue:{}".format(i), "min":'inactive', "max":'active'})
    return list

def ao_obj_list_for_vav():
    list = []
    for i in range(1,4):
        list.append({"object": "analogOutput:{}".format(i), "min":0, "max":100})
    return list

def loop_obj_list_for_vav():
    list = []
    for i in range(1,5):
        min = 0
        max = 100
        if i == 3:
            min = 10
            max = 25
        list.append({"object": "loop:{}".format(i), "min":min, "max":max})
    return list

@bacpypes_debugging
class TestConsoleCmd(ConsoleCmd):

    global lastEventNotification
    global confirmedEventNotificationApduList
    global unconfirmedEventNotificationApduList
    global default_BTL_addresses
    def __init__(self):
        self.test_results = []
        ConsoleCmd.__init__(self)

    def get_iut_address(self):
        global iut_address
        return iut_address

    def do_BTL_manual(self, args):
        """BTL_manual"""
        addresses = default_BTL_addresses
        print("Do BTL {}".format(args))
        # self.BTL_13_9_X1(addresses)
        # self.BTL_14_1_10()
        # self.BTL_14_1_8()
        self.BTL_14_1_X11()
        print("Test Summary")
        for a in self.test_results:
            print(a)

    def do_BTL(self, args):
        """BTL"""
        addresses = ['192.168.0.203']
        print("Do BTL {}".format(args))
        # try:
        #     print("2.1 Basic Functionality")
        #     self.BTL_13_4_3(addresses)
        #     self.BTL_13_4_4(addresses)
        #     self.BTL_13_4_5(addresses)
        #     self.BTL_9_39_1(addresses)
        #     self.BTL_9_39_2(addresses)
        #     self.BTL_13_1_12_1(addresses)
        #     self.BTL_13_9_X1(addresses)  #manual check
        # except Exception as error:
        #     self.test_results.append("exception during Basic Funtionality {}".format(error))
        #
        # try:
        #     print("2.3 Private Transfer Services")
        #     self.BTL_9_25_1_1(addresses[0:2])
        #     self.BTL_9_25_1_2(addresses[0:2])
        # except Exception as error:
        #     self.test_results.append("exception during Private Transfer Services {}".format(error))
        #
        # try:
        #     print("3.1 Analog Input Objects")
        #     self.BTL_7_3_1_1_X1(addresses[0:2], analog_obj_list_for_vav(ao=[], av=[]))
        # except Exception as error:
        #     self.test_results.append("exception during Analog Input Objects {}".format(error))

        # try:
        #     print("3.2 Analog Output Objects")
        #     self.BTL_7_3_1_2(addresses[0:2], ao_obj_list_for_vav())
        #     self.BTL_7_3_1_3(addresses[0:2], ao_obj_list_for_vav())
        #     self.BTL_7_3_1_1_X1(addresses[0:2], analog_obj_list_for_vav(ai=[], av=[]))
        # except Exception as error:
        #     self.test_results.append("exception during Analog Output Objects {}".format(error))

        # try:
        #     print("3.3 Analog Value Objects")
        #     self.BTL_7_3_1_1_X1(addresses[0:2], analog_obj_list_for_vav(ai=[], ao=[]))
        # except Exception as error:
        #     self.test_results.append("exception during Analog Value Objects {}".format(error))
        #
        # try:
        #     print("3.5 Binary Input Objects")
        #     self.BTL_7_3_1_1_X1(addresses[0:2], binary_obj_list_for_vav(bo=[], bv=[]))
        #     settings = self.get_ui_settings(addresses[0])
        #     tmp_set = {'analogInput:1': {513: 0, 514: 0}, 'analogInput:2': {513: 0, 514: 0}, 'binaryInput:1': {514: 1}, 'binaryInput:2': {514: 2}}
        #     self.write_ui_settings(addresses[0], tmp_set)
        #     self.BTL_7_3_2_5_3(addresses[0:2], binary_obj_list_for_vav(bo=[], bv=[]))
        #     self.write_ui_settings(addresses[0], settings)
        # except Exception as error:
        #     self.test_results.append("exception during Binary Input Objects {}".format(error))

        # try:
        #     print("3.3 Binary Output Objects")
        #     self.BTL_7_3_1_2(addresses[0:2], binary_obj_list_for_vav(bi=[], bv=[]))
        #     self.BTL_7_3_1_3(addresses[0:2], binary_obj_list_for_vav(bi=[], bv=[]))
        #     # self.BTL_7_3_1_1_X1(addresses[0:2], binary_obj_list_for_vav(bi=[],bv=[]))
        #     # self.test_results.append(["---No Test---","135.1-2019 - 7.3.2.6.3 - Polarity Property Tests"])
        # except Exception as error:
        #     self.test_results.append("exception during Binary Output Objects {}".format(error))

        # try:
        #     print("3.3 Binary Value Objects")
        #     self.BTL_7_3_1_1_X1(addresses[0:2], binary_obj_list_for_vav(bi=[],bo=[]))
        # except Exception as error:
        #     self.test_results.append("exception during Binary Value Objects {}".format(error))
        #
        # try:
        #     print("3.10 Device Object")
        #     self.BTL_7_3_2_10_6(addresses)
        #     self.BTL_7_3_2_10X(addresses)
        # except Exception as error:
        #     self.test_results.append("exception during Device Object {}".format(error))
        #
        # try:
        #     print("3.10 Loop Object")
        #     self.BTL_7_3_1_1_X1(addresses[0:2], loop_obj_list_for_vav())
        #     self.BTL_7_3_2_17_all(addresses[0:2], loop_obj_list_for_vav())
        # except Exception as error:
        #     self.test_results.append("exception during Loop Object {}".format(error))
        #
        try:
            print("3.61 File Object")
            #self.BTL_9_3_1_2_1(addresses[0:2])
            self.BTL_9_3_1_2_5(addresses[0:2])
            # self.BTL_9_3_2_2_1(addresses[0:2])
            # self.BTL_9_3_2_2_2(addresses[0:2])
            # self.BTL_9_3_2_2_4(addresses[0:2])
        except Exception as error:
            self.test_results.append("exception during File Object {}".format(error))
        #
        # try:
        #     print("4.2 Data Sharing - Read Property - B")
        #     self.BTL_9_18_2_1(addresses)
        #     self.BTL_9_18_2_2(addresses)
        #     self.BTL_9_18_2_3(addresses)
        #     self.BTL_9_18_2_4(addresses)
        #     self.BTL_9_18_1_3(addresses)
        #     self.BTL_9_18_1_X4(addresses)
        #     self.BTL_9_18_1_X1(addresses)
        #     self.BTL_9_18_1_X1(addresses)
        #     self.BTL_9_18_1_X1(addresses)
        #     self.BTL_9_18_1_X1(addresses)
        #     self.BTL_9_18_1_X1(addresses)
        #     self.BTL_9_18_1_X1(addresses)
        #     self.BTL_9_18_1_X1(addresses)
        #     self.BTL_9_18_1_X1(addresses)
        #     self.BTL_9_18_1_X1(addresses)
        #     self.BTL_9_18_1_X1(addresses)
        #     self.BTL_9_18_1_X1(addresses)
        #     self.BTL_9_18_1_X1(addresses)
        # except Exception as error:
        #     self.test_results.append("exception during Data Sharing - Read Property - B {}".format(error))

        print("Test Summary")


        for a in self.test_results:
            print(a)

    def do_results(self, args):
        for a in self.test_results:
            print(a)

    def do_BTL1(self, args):
        msg_store.add_address("979:0xAC67B2F26910")

    def do_BTL2(self, args):
        msg_store.add_address("2:1")

    def BTL_13_4_3(self, addresses):
        self.test_results.append("BTL - 13.4.3 Invalid Tag")
        for address in addresses:
            request = self.raw_request("0c004000011955 {}".format(address))
            if request is not None:
                result = {'apduType': 'ComplexAckPDU', 'source': request.dict_contents()['destination']}
                self.run_test(request, result, name = "Valid Tag, " + address)

            request = self.raw_request("0c004000013955 {}".format(address))
            if request is not None:
                    # Reject Reason =
                    # INVALID_TAG |
                    # INCONSISTENT_PARAMETERS |
                    # INVALID_PARAMETER_DATA_TYPE |
                    # MISSING_REQUIRED_PARAMETER |
                    # TOO_MANY_ARGUMENTS
                result = {
                    'apduType': 'RejectPDU',
                    'source': request.dict_contents()['destination'],
                    'apduAbortRejectReason': [4, 2,3,5,7]
                    }
                self.run_test(request, result, name = "Invalid Tag, " + address)

    def BTL_13_4_4(self, addresses):
        self.test_results.append("BTL - 13.4.4 Missing Parameter")
        for address in addresses:
            request = self.raw_request("0c00400001 {}".format(address))
            if request is not None:
                    # Reject Reason =
                    # MISSING_REQUIRED_PARAMETER |
                    # INVALID_TAG
                result = {
                    'apduType': 'RejectPDU',
                    'source': request.dict_contents()['destination'],
                    'apduAbortRejectReason': [5, 4]
                    }
                self.run_test(request, result, name = "BTL - 13.4.4 Missing Parameter, " + address)

    def BTL_13_4_5(self, addresses):
        self.test_results.append("BTL - 13.4.5 Too Many Arguments")
        for address in addresses:
            request = self.raw_request("0c004000011955194d {}".format(address))
            if request is not None:
                    # Reject Reason =
                    # MISSING_REQUIRED_PARAMETER |
                    # INVALID_TAG
                result = {
                    'apduType': 'RejectPDU',
                    'source': request.dict_contents()['destination'],
                    'apduAbortRejectReason': [7]
                    }
                self.run_test(request, result, name = "BTL - 13.4.5 Too Many Arguments, " + address)

                # This one would be array index
        # self.test_results.append("BTL - 13.4.5 Too Many Arguments")
        # for address in addresses:
        #     request = self.raw_request("0c004000011955294d {}".format(address))
        #     if request is not None:
        #             # Reject Reason =
        #             # MISSING_REQUIRED_PARAMETER |
        #             # INVALID_TAG
        #         result = {
        #             'apduType': 'RejectPDU',
        #             'source': request.dict_contents()['destination'],
        #             'apduAbortRejectReason': [7]
        #             }
        #         self.run_test(request, result, name = "BTL - 13.4.5 Too Many Arguments, " + address)

    def BTL_9_39_1(self, addresses):
        supported_services = {
        "2:1": [False,False,False,False,False,False,True,True,False,False,False,False,True,False,True,True,True,True,True,False,True,False,False,False,False,False,False,False,False,False,False,False,False,True,True,False,True,False,False,False,False],
        "979:0xAC67B2F26910": [False,False,False,False,False,False,True,True,False,False,False,False,True,False,True,True,True,True,True,False,True,False,False,False,False,False,False,False,False,False,False,False,False,True,True,False,True,False,False,False,False],
        "192.168.1.30": [True,False,False,False,False,True,True,True,False,False,True,True,True,False,True,True,True,True,True,False,True,False,False,False,False,False,True,False,False,False,False,False,False,True,True,True,True,False,False,True,False]
        }
        self.test_results.append("BTL - 9.39.1 Unsupported Confirmed Services Test")
        for address in addresses:
            for service in range(0,34):
                if service < len(supported_services[address]) and not supported_services[address][service]:
                    request = self.create_confirmed_service_request(address, service)
                    if request is not None:
                            # Reject Reason =
                            # MISSING_REQUIRED_PARAMETER |
                            # INVALID_TAG
                        result = {
                            'apduType': 'RejectPDU',
                            'source': request.dict_contents()['destination'],
                            'apduAbortRejectReason': [9] # REJECT_REASON_UNRECOGNIZED_SERVICE = 9,
                            }
                        self.run_test(request, result, name = "BTL - 9.39.1 Unsupported Confirmed Services Test ({} {})".format(service,address))

        self.test_results.append("BTL - 9.39.1B Unsupported Confirmed Services Test (undefined request)")
        for address in addresses:
            for service in [40]:
                request = self.create_confirmed_service_request(address, service)
                if request is not None:
                        # Reject Reason =
                        # MISSING_REQUIRED_PARAMETER |
                        # INVALID_TAG
                    result = {
                        'apduType': 'RejectPDU',
                        'source': request.dict_contents()['destination'],
                        'apduAbortRejectReason': [9] # REJECT_REASON_UNRECOGNIZED_SERVICE = 9,
                        }
                    self.run_test(request, result, name = "BTL - 9.39.1 Unsupported Confirmed Services Test  (undefined request) ({} {})".format(service,address))

        self.test_results.append("BTL - 9.39.1B Unsupported Confirmed Services Test (undefined request)")
        for address in addresses:
            for service in [40]:
                request = self.create_confirmed_service_request(address, service)
                if request is not None:
                        # Reject Reason =
                        # MISSING_REQUIRED_PARAMETER |
                        # INVALID_TAG
                    result = {
                        'apduType': 'RejectPDU',
                        'source': request.dict_contents()['destination'],
                        'apduAbortRejectReason': [9] # REJECT_REASON_UNRECOGNIZED_SERVICE = 9,
                        }
                    self.run_test(request, result, name = "BTL - 9.39.1 Unsupported Confirmed Services Test  (undefined request) ({} {})".format(service,address))

        self.test_results.append("BTL - 9.39.1B Unsupported Confirmed Services Test (CPT other vendor)")
        for address in addresses:
            for service in [ConfirmedPrivateTransferRequest().serviceChoice]:
                request = self.create_confirmed_service_request(address, service)
                if request is not None:
                        # Reject Reason =
                        # MISSING_REQUIRED_PARAMETER |
                        # INVALID_TAG
                    result = {
                        'apduType': 'RejectPDU',
                        'source': request.dict_contents()['destination'],
                        'apduAbortRejectReason': [9] # REJECT_REASON_UNRECOGNIZED_SERVICE = 9,
                        }
                    self.run_test(request, result, name = "BTL - 9.39.1 Unsupported Confirmed Services Test  (undefined request) ({} {})".format(service,address))


    def BTL_9_39_2(self, addresses):
        self.test_results.append("BTL - 9.39.2 Unsupported Unconfirmed Services Test")
        supported_services = {
        "2:1": [False,False,False,False,False,False,True,True,False,False,False,False,True,False,True,True,True,True,True,False,True,False,False,False,False,False,False,False,False,False,False,False,False,True,True,False,True,False,False,False,False],
        "979:0xAC67B2F26910": [False,False,False,False,False,False,True,True,False,False,False,False,True,False,True,True,True,True,True,False,True,False,False,False,False,False,False,False,False,False,False,False,False,True,True,False,True,False,False,False,False],
        "192.168.1.30": [True,False,False,False,False,True,True,True,False,False,True,True,True,False,True,True,True,True,True,False,True,False,False,False,False,False,True,False,False,False,False,False,False,True,True,True,True,False,False,True,False]
        }
        for address in addresses:
            self.do_iut(address)
            msg_store.set_address_list = [address]
            status = self.read_value('device:4194303 systemStatus')
            for service in [4,5]: #range(0,11):
                # msg_store.clear_msg()
                # self.apdu_list = []
                request = self.create_unconfirmed_service_request(address, service)
                if request is not None:
                        # Reject Reason =
                        # MISSING_REQUIRED_PARAMETER |
                        # INVALID_TAG
                    self.run_test_unconfirmed(request, expected="none", wait_time=6, name = "BTL - 9.39.1 Unsupported Unconfirmed Services Test({} {})".format(service,address))
                    # sleep(6)
                    # msglst = msg_store.get_msg()
                    # if len(msglst) > 0:
                    #     print ("\n---FAIL---\n")
                    #     for x in msglst:
                    #         print(x.dict_contents())
            self.test_results.append("Status pre: {} post {}".format(status, self.read_value('device:4194303 systemStatus')))

    def BTL_13_1_12_1(self, addresses):
        self.test_results.append("13.1.12.1 IUT Does Not Support Segmented Response")
        supported_services = {
        "2:1": [False,False,False,False,False,False,True,True,False,False,False,False,True,False,True,True,True,True,True,False,True,False,False,False,False,False,False,False,False,False,False,False,False,True,True,False,True,False,False,False,False],
        "979:0xAC67B2F26910": [False,False,False,False,False,False,True,True,False,False,False,False,True,False,True,True,True,True,True,False,True,False,False,False,False,False,False,False,False,False,False,False,False,True,True,False,True,False,False,False,False],
        "192.168.1.30": [True,False,False,False,False,True,True,True,False,False,True,True,True,False,True,True,True,True,True,False,True,False,False,False,False,False,True,False,False,False,False,False,False,True,True,True,True,False,False,True,False]
        }
        max_apdu = this_application.localDevice.maxApduLengthAccepted
        this_application.localDevice.maxApduLengthAccepted = 50
        for address in addresses:
            self.do_iut(address)
            prop_reference_list = []
            for x in range(0,6):
                prop_reference = PropertyReference(propertyIdentifier='objectIdentifier')
                prop_reference_list.append(prop_reference)
            read_access_spec = ReadAccessSpecification(
                objectIdentifier = 'device:4194303',
                listOfPropertyReferences= prop_reference_list
            )
            request = ReadPropertyMultipleRequest(
                listOfReadAccessSpecs=[read_access_spec]
            )
            request.pduDestination = Address(address)
            result = {
            'source': address.lower(),
            'apduType': 'AbortPDU',
            'apduSrv': [True],
            'apduAbortRejectReason': [4]
            }
            self.run_test(request, expected=result, name="13.1.12.1 IUT Does Not Support Segmented Response ({})".format(address))
        this_application.localDevice.maxApduLengthAccepted = max_apdu

    def BTL_13_9_X1(self, addresses):
        self.test_results.append("BTL - 13.9.X1 Ignore Confirmed Broadcast Requests")
        self.test_results.append(" --- Note: Must manually verify no response.  ")
        retries = this_application.localDevice.numberOfApduRetries
        this_application.localDevice.numberOfApduRetries = 0
        for address in addresses:
            msg_store.set_address_list = [address]
            add = Address(address)
            if add.addrType == Address.localStationAddr:
                add = LocalBroadcast()
            elif add.addrType == Address.remoteStationAddr:
                add = RemoteBroadcast(add.addrNet)
            else:
                print("Address is not a local or remote station.  Invalid")
            request = ReadPropertyRequest(
                objectIdentifier = 'device:4194303',
                propertyIdentifier = 'objectIdentifier'
            )
            request.pduDestination = add
            # result = "none"
            result = "manual"
            self.run_test_unconfirmed(request, expected=result, name="BTL - 13.9.X1 Ignore Confirmed Broadcast Requests ({})".format(address))
        this_application.localDevice.numberOfApduRetries = retries

    def BTL_9_25_1_1(self, addresses):
        self.test_results.append("BTL - 9.25.1.1 Correctly Executes a Supported ConfirmedPrivateTransfer Service")
        for address in addresses:
            request = ConfirmedPrivateTransferRequest(
                vendorID = 979,
                serviceNumber = 1
            )
            request.pduDestination = Address(address)
            a = Any()
            a.cast_in(CharacterString('{"read": {"object-counts": ["all"]}}'))
            request.serviceParameters = a
            result = {
                'source': address.lower(),
                'apduType': 'ComplexAckPDU',
                'apduService': 'ConfirmedPrivateTransferRequest',
                'function': 'ConfirmedPrivateTransferACK',
                'vendorID': [979],
                'serviceNumber': [1],
                # 'resultBlock': {'class': 1, 'number': 1, 'lvt': 164}
                }
            self.run_test(request, expected=result, name="BTL - 9.25.1.1 Correctly Executes a Supported ConfirmedPrivateTransfer Service({})".format(address))

    def BTL_9_25_1_2(self, addresses):
        self.test_results.append("BTL - 9.25.2.1 Correctly Executes a Non-Supported ConfirmedPrivateTransfer Service")
        for address in addresses:
            request = ConfirmedPrivateTransferRequest(
                vendorID = 200,
                serviceNumber = 9
            )
            request.pduDestination = Address(address)
            a = Any()
            a.cast_in(CharacterString('{"read": {"object-counts": ["all"]}}'))
            request.serviceParameters = a
            result = {
                'source': address.lower(), 'apduType': 'RejectPDU',
                'apduAbortRejectReason': [9]
                }
            self.run_test(request, expected=result, name="BTL - 9.25.2.1 Correctly Executes a Non-Supported ConfirmedPrivateTransfer Service (Other Vendor)({})".format(address))
            request = ConfirmedPrivateTransferRequest(
                vendorID = 979,
                serviceNumber = 34
            )
            request.pduDestination = Address(address)
            a = Any()
            a.cast_in(CharacterString('{"read": {"object-counts": ["all"]}}'))
            request.serviceParameters = a
            result = {
                'source': address.lower(), 'apduType': 'RejectPDU',
                'apduAbortRejectReason': [9]
                }
            self.run_test(request, expected=result, name="BTL - 9.25.2.1 Correctly Executes a Non-Supported ConfirmedPrivateTransfer Service (Unsupported Service)({})".format(address))

    def BTL_7_3_1_1_X1(self, addresses, objects):
        name = "BTL - 7.3.1.1.X1 Out_Of_Service, Status_Flags, and Reliability Test"
        for address in addresses:
            for obj in objects:
                object = obj['object']
                testname = "{} [{}] [{}]".format(name, address, object)
                print(address, object)
                result = []
                self.do_iut(address)
                orig_val = self.read_value('{} presentValue'.format(object))
                oos = self.read_value('{} outOfService'.format(object))
                if oos:
                    self.write_value("{} outOfService False".format(object))
                    # """write <type> <inst> <prop> <value> [ <indx> ] [ <priority> ]"""
                    oos = self.read_value('{} outOfService'.format(object))
                SF1 = self.read_value('{} statusFlags'.format(object))
                R1 = self.read_value('{} reliability'.format(object))
                #Write Out of Service = True
                self.write_value("{} outOfService True".format(object))
                #4 Verify Out of Service = TRUE
                if not (self.read_value('{} outOfService'.format(object)) == True):
                    print("Failed to verify outOfService = True")
                    return False
                #5 Verify Status_Flags = (?, ?, ?, TRUE)
                sf = self.read_value('{} statusFlags'.format(object))
                if sf[3] != True:
                    result.append(5)
                #6 Repeat X values meeting the functional range requirements of 7.2.1
                if obj['min'] == 'inactive':
                    for value in ['inactive', 'active', 'inactive', orig_val]:
                        self.write_value("{} presentValue {}".format(object, value))
                        val = self.read_value("{} presentValue".format(object))
                        print("comparing:", val, value)
                        if val != value:
                            result.append(6)
                            print("error, wrote {} but read {}".format(value, val))
                else:
                    if obj['min'] < 0:
                        values = [obj['min'], obj['min'] *.01,0,20.1,obj['max'] * .05, obj['max'], orig_val]
                    else:
                        range = obj['max'] - obj['min']
                        min = obj['min']
                        values = [min, min + range * .05, min + range * 0.5, min + range * 0.9, obj['max'], orig_val]
                    for value in values:
                        self.write_value("{} presentValue {}".format(object, value))
                        val = self.read_value("{} presentValue".format(object))
                        print("comparing:", val, value)
                        if not isclose(val,value, rel_tol=1e-4):
                            result.append(6)
                            print("error, wrote {} but read {}".format(value, val))
                #Reliability is not Writable, skip step 7.
                #WRITE Out_Of_Service = FALSE
                self.write_value("{} outOfService False".format(object))
                # VERIFY Out_Of_Service = FALSE
                if not (self.read_value('{} outOfService'.format(object)) == False):
                    print("Failed to verify outOfService = False")
                    continue
                SF2 = self.read_value('{} statusFlags'.format(object))
                R2 = self.read_value('{} reliability'.format(object))
                if SF1 != SF2:
                    print("Status flags do not match {} {}".format(SF1, SF2))
                if R1 != R2:
                    print("Reliability does not match {} {}".format(R1, R2))
                if len(result) > 0:
                    self.test_results.append(["---FAIL--- {}".format(result), testname])
                else:
                    self.test_results.append(["pass", testname])

    def BTL_7_3_1_2(self, addresses, objects):
        name = "7.3.1.2 Relinquish Default Test"
        for address in addresses:
            self.do_iut(address)
            for obj in objects:
                result = []
                object = obj['object']
                testname = "{} [{}] [{}]".format(name, address, object)
                print(address, object)
                PA = self.read_value('{} priorityArray'.format(object))
                print (PA)
                pa = PA.dict_contents()
                for index, x in enumerate(pa):
                    for y in x:
                        if y != 'null':
                            self.write_value('{} presentValue null - {}'.format(object, index + 1))
                            PA = None
                if PA == None:
                    PA = self.read_value('{} priorityArray'.format(object))
                    pa = PA.dict_contents()
                    for index, x in enumerate(pa):
                        for y in x:
                            if y != 'null':
                                result.append("{}:{}({})".format(index, y, x[y]))
                # 1. VERIFY Priority_Array = (NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
                # NULL, NULL, NULL, NULL, NULL)
                if len(result) > 0:
                    self.test_results.append(["---FAIL--- {}".format(result), testname])
                    continue
                PV = self.read_value('{} presentValue'.format(object))
                RD = self.read_value('{} relinquishDefault'.format(object))
                if PV != RD:
                    result.append("PV:{} RD:{}".format(PV,RD))
        # 2. TRANSMIT ReadProperty-Request,
            # 'Object Identifier' = (the object being tested),
            # 'Property Identifier' = Present_Value
        # 3. RECEIVE ReadProperty-ACK,
            # 'Object Identifier' = (the object being tested),
            # 'Property Identifier' = Present_Value
            # 'Property Value' = (any valid value, X)
        # 4, VERIFY Relinquish_Default = X
                if 'analog' in object:
                    values = [0, 50, 100, RD]
                    for value in values:
                        self.write_value('{} relinquishDefault {}'.format(object, value))
                        PV1 = self.read_value('{} presentValue'.format(object))
                        RD1 = self.read_value('{} relinquishDefault'.format(object))
                        if PV1 != RD1 or not isclose(value, PV1, rel_tol=1e-4):
                            result.append("Wr: {} PV:{} RD:{}".format(value,PV1,RD1))
                        print("Wr: {} PV:{} RD:{}".format(value,PV1,RD1))
                elif 'binary' in object:
                    values = ['active', 'inactive', RD]
                    for value in values:
                        self.write_value('{} relinquishDefault {}'.format(object, value))
                        PV1 = self.read_value('{} presentValue'.format(object))
                        RD1 = self.read_value('{} relinquishDefault'.format(object))
                        if PV1 != RD1 or PV1 != value:
                            result.append("Wr: {} PV:{} RD:{}".format(value,PV1,RD1))
                        print("Wr: {} PV:{} RD:{}".format(value,PV1,RD1))
        # 5. IF (Relinquish_Default is writable) THEN
            # WRITE Relinquish_Default = (any valid value, Y, other than the one returned in step 3)
            # VERIFY Present_Value = Y
                if len(result) > 0:
                    self.test_results.append(["---FAIL--- {}".format(result), testname])
                else:
                    self.test_results.append(["pass", testname])


    def BTL_7_3_1_3(self, addresses, objects):
        name = "7.3.1.3 Command Prioritization Test"
        Vlow = 20
        Vmed = 50
        Vhigh = 90
        Plow = 4
        Pmed = 3
        Phigh = 2
        binary = False
        for address in addresses:
            self.do_iut(address)
            for obj in objects:
                result = []
                object = obj['object']
                if 'analog' in object:
                    Vlow = 20
                    Vmed = 50
                    Vhigh = 90
                    binary = False
                elif 'binary' in object:
                    Vlow = 'active'
                    Vmed = 'inactive'
                    Vhigh = 'active'
                    binary = True
                testname = "{} [{}] [{}]".format(name, address, object)
                print(address, object)
                PA = self.read_value('{} priorityArray'.format(object))
                pa = PA.dict_contents()
                for index, x in enumerate(pa):
                    for y in x:
                        if y != 'null':
                            self.write_value('{} presentValue null - {}'.format(object, index + 1))
                            PA = None
                if PA == None:
                    PA = self.read_value('{} priorityArray'.format(object))
                    pa = PA.dict_contents()
                    for index, x in enumerate(pa):
                        for y in x:
                            if y != 'null':
                                result.append("{}:{}({})".format(index, y, x[y]))
                # 1. VERIFY Priority_Array = (NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
                # NULL, NULL, NULL, NULL, NULL)
                if len(result) > 0:
                    self.test_results.append(["---FAIL--- {}".format(result), testname])
                    continue
                # 1. WRITE Present_Value = V low , PRIORITY = P low
                # 2. VERIFY Present_Value = V low
                # 3. VERIFY Priority_Array = V low , ARRAY INDEX = P low
                # 4. REPEAT Z = (each index 1 through 5 not equal to P low ) DO {
                #     VERIFY Priority_Array = NULL, ARRAY INDEX = Z
                #     }
                self.write_value('{} presentValue {} - {}'.format(object, Vlow, Plow))
                PV = self.read_value('{} presentValue'.format(object))
                PA = self.read_value('{} priorityArray'.format(object))
                pa = pa_to_array(PA)
                if binary:
                    if pa[Plow - 1] is None or PV != Vlow or BinaryPV(pa[Plow - 1]) != Vlow:
                        result.append("Plow: {}, Vlow: {}, PV: {}, PA[Plow]: {}".format(Plow,Vlow,PV,pa[Plow-1]))
                else:
                    if pa[Plow - 1] is None or not isclose(PV, Vlow, rel_tol=1e-4) or not isclose(pa[Plow - 1], Vlow, rel_tol=1e-4):
                        result.append("Plow: {}, Vlow: {}, PV: {}, PA[Plow]: {}".format(Plow,Vlow,PV,pa[Plow-1]))
                for Z in range(0,5):
                    if Z != (Plow - 1) and pa[Z] != None:
                        result.append("4: Z={} pa[Z]={}".format(Z,pa[Z]))

                # 5. WRITE Present_Value = V high , PRIORITY = P high
                # 6. VERIFY Present_Value = V high
                # 7. VERIFY Priority_Array = V high , ARRAY INDEX = P high
                # 8. REPEAT Z = (each index 1 through 5 not equal to P low or P high ) DO {
                #     VERIFY Priority_Array = NULL, ARRAY INDEX = Z
                #     }
                self.write_value('{} presentValue {} - {}'.format(object, Vhigh, Phigh))
                PV = self.read_value('{} presentValue'.format(object))
                PA = self.read_value('{} priorityArray'.format(object))
                pa = pa_to_array(PA)
                if binary:
                    if pa[Phigh - 1] is None or PV != Vhigh or BinaryPV(pa[Phigh - 1]) != Vhigh:
                        result.append("Phigh: {}, Vhigh: {}, PV: {}, PA[Phigh]: {}".format(Phigh,Vhigh,PV,pa[Phigh-1]))
                else:
                    if pa[Phigh - 1] is None or not isclose(PV, Vhigh, rel_tol=1e-4) or not isclose(pa[Phigh - 1], Vhigh, rel_tol=1e-4):
                        result.append("Phigh: {}, Vhigh: {}, PV: {}, PA[Phigh]: {}".format(Phigh,Vhigh,PV,pa[Phigh-1]))
                for Z in range(0,5):
                    if ((Z + 1) not in [Plow, Phigh]) and pa[Z] != None:
                        result.append("4: Z={} pa[Z]={}".format(Z,pa[Z]))

                # 09. WRITE Present_Value = V med , PRIORITY = P med
                # 10. VERIFY Present_Value = V high
                # 11. VERIFY Priority_Array = V med , ARRAY INDEX = P med
                # 12. REPEAT Z = (each index 1 through 5 not equal to P low , P med or P high ) DO {
                #     VERIFY Priority_Array = NULL, ARRAY INDEX = Z
                #     }
                self.write_value('{} presentValue {} - {}'.format(object, Vmed, Pmed))
                PV = self.read_value('{} presentValue'.format(object))
                PA = self.read_value('{} priorityArray'.format(object))
                pa = pa_to_array(PA)
                if binary:
                    if PV != Vhigh:
                        result.append("PV != Vhigh [{},{}]".format(PV,Vhigh))
                    if pa[Pmed - 1] is None or BinaryPV(pa[Pmed - 1]) != Vmed:
                        result.append("PA[Pmed] != Vmed [{},{}]".format(pa[Pmed-1],Vmed))
                else:
                    if not isclose(PV, Vhigh, rel_tol=1e-4):
                        result.append("PV != Vhigh [{},{}]".format(PV,Vhigh))
                    if pa[Pmed - 1] is None or not isclose(pa[Pmed - 1], Vmed, rel_tol=1e-4):
                        result.append("PA[Pmed] != Vmed [{},{}]".format(pa[Pmed-1],Vmed))
                for Z in range(0,5):
                    if ((Z + 1) not in [Plow, Pmed, Phigh]) and pa[Z] != None:
                        result.append("4: Z={} pa[Z]={}".format(Z,pa[Z]))



                # 13. WRITE Present_Value = NULL, PRIORITY = P high
                # 14. VERIFY Present_Value = V med
                # 15. REPEAT Z = (each index 1 through 5 not equal to P low or P med ) DO {
                #     VERIFY Priority_Array = NULL, ARRAY INDEX = Z
                #     }
                self.write_value('{} presentValue {} - {}'.format(object, 'null', Phigh))
                PV = self.read_value('{} presentValue'.format(object))
                PA = self.read_value('{} priorityArray'.format(object))
                pa = pa_to_array(PA)
                if binary:
                    if PV != Vmed:
                        result.append("PV != Vmed [{},{}]".format(PV,Vmed))
                else:
                    if not isclose(PV, Vmed, rel_tol=1e-4):
                        result.append("PV != Vmed [{},{}]".format(PV,Vmed))
                for Z in range(0,5):
                    if ((Z + 1) not in [Plow, Pmed]) and pa[Z] != None:
                        result.append("4: Z={} pa[Z]={}".format(Z,pa[Z]))
                # 16. WRITE Present_Value = NULL, PRIORITY = P med
                # 17. VERIFY Present_Value = V low
                # 18. REPEAT Z = (each index 1 through 5 not equal to P low ) DO {
                #     VERIFY Priority_Array = NULL, ARRAY INDEX = Z
                #     }
                self.write_value('{} presentValue {} - {}'.format(object, 'null', Pmed))
                PV = self.read_value('{} presentValue'.format(object))
                PA = self.read_value('{} priorityArray'.format(object))
                pa = pa_to_array(PA)
                if binary:
                    if PV != Vlow:
                        result.append("PV != Vlow [{},{}]".format(PV,Vlow))
                else:
                    if not isclose(PV, Vlow, rel_tol=1e-4):
                        result.append("PV != Vlow [{},{}]".format(PV,Vlow))
                for Z in range(0,5):
                    if ((Z + 1) not in [Plow]) and pa[Z] != None:
                        result.append("4: Z={} pa[Z]={}".format(Z,pa[Z]))
                # 19. WRITE Present_Value = NULL, PRIORITY = P low
                # 20. REPEAT Z = (each index 1 through 5) DO {
                #     VERIFY Priority_Array = NULL, ARRAY INDEX = Z
                #     }
                self.write_value('{} presentValue {} - {}'.format(object, 'null', Plow))
                PV = self.read_value('{} presentValue'.format(object))
                PA = self.read_value('{} priorityArray'.format(object))
                pa = pa_to_array(PA)
                for Z in range(0,5):
                    if pa[Z] != None:
                        result.append("4: Z={} pa[Z]={}".format(Z,pa[Z]))

                if len(result) > 0:
                    self.test_results.append(["---FAIL--- {}".format(result), testname])
                else:
                    self.test_results.append(["pass", testname])

    def BTL_7_3_2_5_3(self, addresses, objects):
        name = "7.3.2.5.3 Polarity Property Tests Binary Input"
        for address in addresses:
            self.do_iut(address)
            for obj in objects:

                result = []
                object = obj['object']
                testname = "{} [{}] [{}]".format(name, address, object)

                POL = self.read_value('{} polarity'.format(object))
                PV = self.read_value('{} presentValue'.format(object))
                if POL == 'normal':
                    wr_pol = 'reverse'
                else:
                    wr_pol = 'normal'
                self.write_value('{} polarity {}'.format(object, wr_pol))
                POL1 = self.read_value('{} polarity'.format(object))
                if not (POL1 == wr_pol):
                    result.append("P1 = {} write {} P2 = {}".format(POL, wr_pol, POL1))
                time.sleep(2)
                PV2 = self.read_value('{} presentValue'.format(object))
                if not ((PV == 'active' and PV2 == 'inactive') or (PV == 'inactive' and PV2 == 'active')):
                    result.append("P1 = {} write {} P2 = {}".format(POL, wr_pol, POL1))
                self.write_value('{} polarity {}'.format(object, POL))
                print("[Pol: {}, Value: {}] [Pol: {}, Value: {}]".format(POL, PV, POL1, PV2))
                if len(result) > 0:
                    self.test_results.append(["---FAIL--- {}".format(result), testname])
                else:
                    self.test_results.append(["pass", testname])

    def BTL_7_3_2_10_6(self, addresses):
        name = "7.3.2.10.6 Successful increment of the Database_Revision property after changing the Object_Identifier property of an object"
        #Need to change the device object identifier, then change it back.  (Only object we can change)
        for address in addresses:
            testname = "{} [{}]".format(name, address)
            self.do_iut(address)
            new_id = 4194302
            id = self.read_value("device:4194303 objectIdentifier")
            if id[1] == new_id:
                new_id = 4194301
            print(id[1])
            db = self.read_value("device:4194303 databaseRevision")
            self.write_value("device:{} objectIdentifier device:{}".format(id[1], new_id))
            id2 = self.read_value("device:4194303 objectIdentifier")
            db2 = self.read_value("device:4194303 databaseRevision")
            self.write_value("device:{} objectIdentifier device:{}".format(id2[1],id[1]))
            id3 = self.read_value("device:4194303 objectIdentifier")
            db3 = self.read_value("device:4194303 databaseRevision")
            result = []
            if id != id3:
                result.append('id not restored [{},{}]'.format(id,id3))
            if  not db2 > db or not db3 > db2:
                result.append('database revision not increasing [{},{},{}]'.format(db, db2, db3))
            if id2[1] != new_id:
                result.append('id not written [{},{}]'.format(id2[1],new_id))
            print('[{},{},{}]'.format(db, db2, db3))
            if len(result) > 0:
                self.test_results.append(["---FAIL--- {}".format(result), testname])
            else:
                self.test_results.append(["pass", testname])

    def BTL_7_3_2_10X(self, addresses):
        name = "7.3.2.10.X Ensure UTC_Offset is Configurable"
        #Need to change the device object identifier, then change it back.  (Only object we can change)
        for address in addresses:
            result = []
            testname = "{} [{}]".format(name, address)
            print(testname)
            self.do_iut(address)
            id = self.read_value("device:4194303 objectIdentifier")
            utc = self.read_value("device:4194303 utcOffset")
            for val in [-1440, -780, -15 * 33, 0, 29 * 15, 780, 1440, utc]:
                self.write_value("device:{} utcOffset {}".format(id[1], val))
                value = self.read_value("device:4194303 utcOffset")
                print("write: {} read: {}".format(val, value))
                if value != val:
                    result.append('[{},{}]'.format(val,value))
            if len(result) > 0:
                self.test_results.append(["---FAIL--- {}".format(result), testname])
            else:
                self.test_results.append(["pass", testname])

    def BTL_7_3_2_17_all(self, addresses, objects):
        name = "7.3.2.17.1 Manipulated_Variable_Reference Tracking"
        for address in addresses:
            self.do_iut(address)
            for obj in objects:
                object = obj['object']
                mvr = self.read_value("{} manipulatedVariableReference".format(object))
                mvr = mvr.dict_contents()
                mvr_obj = mvr['objectIdentifier']
                mvr_prop = mvr['propertyIdentifier']
                mv_pv = self.read_value("{}:{} {}".format(mvr_obj[0], mvr_obj[1], mvr_prop))
                cvr = self.read_value("{} controlledVariableReference".format(object))
                cvr = cvr.dict_contents()
                cvr_obj = cvr['objectIdentifier']
                cvr_prop = cvr['propertyIdentifier']
                cv_pv = self.read_value("{}:{} {}".format(cvr_obj[0], cvr_obj[1], cvr_prop))
                spr = self.read_value("{} setpointReference".format(object))
                spr = spr.dict_contents()
                print(cvr,spr)
                if 'setpointReference' in spr:
                    spr_obj = spr['setpointReference']['objectIdentifier']
                    spr_prop = spr['setpointReference']['propertyIdentifier']
                    sp_pv = self.read_value("{}:{} {}".format(spr_obj[0], spr_obj[1], spr_prop))
                else:
                    sp_pv = None
                priority = self.read_value("{} priorityForWriting".format(object))
                loop_pv = self.read_value("{} presentValue".format(object))
                loop_cvv = self.read_value("{} controlledVariableValue".format(object))
                loop_spv = self.read_value("{} setpoint".format(object))
                print(object, "MV", mvr, mv_pv, loop_pv)
                print(object, "CV", cvr, cv_pv, loop_cvv)
                print(object, "SP", spr, sp_pv, loop_spv)

                # print(mvr.dict_contents(), priority, loop_pv)
                # print(cvr, cvr.dict_contents())
                # print(cvr, spr)
                #example of dict_contents for bacpypes.basetypes.ObjectPropertyReference (mvr, cvr): {'objectIdentifier': ('analogValue', 28), 'propertyIdentifier': 'presentValue'}
                # print(spr, spr.dict_contents())
                #xample of dict_contents for bacpypes.basetypes.SetpointReference (spr): {'setpointReference': {'objectIdentifier': ('analogInput', 0), 'propertyIdentifier': 'presentValue'}}

# TRANSMIT ReadProperty-Request,
# 'Object Identifier' =
# (the Loop object being tested),
# 'Property Identifier' =
# Manipulated_Variable_Reference
# RECEIVE BACnet-ComplexACK-PDU,
# 'Object Identifier' =
# (the Loop object being tested),
# 'Property Identifier' =
# Manipulated_Variable_Reference,
# 'Property Value' =
# (any valid object property reference)
# TRANSMIT ReadProperty-Request,
# 'Object Identifier' =
# (the Loop object being tested),
# 'Property Identifier' =
# Priority_For_Writing
# RECEIVE BACnet-ComplexACK-PDU,
# 'Object Identifier' =
# (the Loop object being tested),
# 'Property Identifier' =
# Priority_For_Writing,
# 'Property Value' =
# (any priority from 1 to 16)
# TRANSMIT ReadProperty-Request,
# 'Object Identifier' =
# (the Loop object being tested),
# 'Property Identifier' =
# Present_Value
# RECEIVE BACnet-ComplexACK-PDU,
# 'Object Identifier' =
# (the Loop object being tested),
# 'Property Identifier' =
# Present_Value,
# 'Property Value' =
# (any valid value)
# IF (the manipulated variable reference is commandable) THEN
# VERIFY (the manipulated variable reference object),
# (the referenced property) = (the Present_Value from step 6),
# ARRAY INDEX = (the Priority_For_Writing from step 4)
# ELSE
# VERIFY (the manipulated variable reference object),
# (the referenced property) = (the Present_Value from step 6)

    def BTL_9_3_1_2_1(self, addresses):
        name = "9.13.1.2.1 Writing an Entire File"
        object = "file:1"
        contentToWrite = "Hello"
        # for address in addresses:
        for address in addresses:
            result = []
            testname = "{} [{}] [{}]".format(name, address, object)
            print(address)
            self.do_iut(address)
            #set up to write file.
            #first, set type to 2 (Thermostat unused)
            # self.do_writeProprietary("{} 603 2 Enumerated".format(object))
            self.write_value("{} fileSize 5".format(object))
            self.do_writestream("{} {} 0 {}".format(address, 1, contentToWrite))
            value = self.readstream ("{} {} 0 5".format(address, 1))
            if value.decode("utf-8") != contentToWrite:
                result.append("written: [{}] Read: [{}]".format(contentToWrite, value.decode("utf-8")))
            print(value)
            if len(result) > 0:
                self.test_results.append(["---FAIL--- {}".format(result), testname])
            else:
                self.test_results.append(["pass", testname])


    def BTL_9_3_1_2_5(self, addresses):

        name = "9.13.1.2.5 Deleting a File"
        object = "file:1"
        sizeToWrite = 10
        # for address in addresses:
        for address in addresses:
            result = []
            testname = "{} [{}] [{}]".format(name, address, object)
            print(address)
            self.do_iut(address)
            #set up to write file.
            #first, set type to 2 (Thermostat unused)
            # self.do_writeProprietary("{} 603 2 Enumerated".format(object))
            self.write_value("{} fileSize {}".format(object, sizeToWrite))
            self.do_writestream("{} {} 0 Hello".format(address, 1))

            size = self.read_value("{} fileSize".format(object))
            value = self.readstream ("{} {} 0 20".format(address, 1))
            fileLength = len(value)
            print("Response length: {}".format(fileLength))
            if fileLength != sizeToWrite:
                result.append("fileLength [{}] ! = lengthWritten [{}]".format(fileLength, sizeToWrite))
            print("[{}]".format(value))
            write_res = self.write_value("{} fileSize 0".format(object))
            #print(write_res)
            if write_res != "Ack":
                result.append("error to write fileSize = 0: [{}]".format(write_res))
            size = self.read_value("{} fileSize".format(object))
            if size != 0:
                result.append("fileLength [{}] ! = 0 after writing 0".format(fileLength))
            if len(result) > 0:
                self.test_results.append(["---FAIL--- {}".format(result), testname])
            else:
                self.test_results.append(["pass", testname])

    def BTL_9_3_2_2_1(self, addresses):

        name = "9.13.2.2.1 Writing to a Stream Access File using Record Access"
        object = "file:1"
        contentToWrite = "Hello"
        # for address in addresses:
        for address in addresses:
            result = []
            testname = "{} [{}] [{}]".format(name, address, object)
            print(address)
            self.do_iut(address)
            #set up to write file.
            #first, set type to 2 (Thermostat unused)
            # self.do_writeProprietary("{} 603 2 Enumerated".format(object))
            self.write_value("{} fileSize 5".format(object))
            write_res = self.writerecord()
            print(write_res)
            if 'invalidFileAccessMethod' not in "{}".format(write_res):
                result.append(write_res)
            #delete file
            self.write_value("{} fileSize 0".format(object))
            print(write_res)
            if len(result) > 0:
                self.test_results.append(["---FAIL--- {}".format(result), testname])
            else:
                self.test_results.append(["pass", testname])

    def BTL_9_3_2_2_2(self, addresses):
        name = "9.13.2.2.2 Writing to a File with an Invalid Starting Position"
        object = "file:1"
        contentToWrite = "Hello"
        # for address in addresses:
        for address in addresses:
            for start_pos in [-5, -1, 150]:
                result = []
                testname = "{} [{}] [{}] [{}]".format(name, address, object, start_pos)
                print(address)
                self.do_iut(address)
                #set up to write file.
                #first, set type to 2 (Thermostat unused)
                # self.do_writeProprietary("{} 603 2 Enumerated".format(object))
                self.write_value("{} fileSize 100".format(object))
                write_res = self.writestream(object="file:1", start_position=start_pos, data="ThisIsTestData")
                if "invalidFileStartPosition" not in "{}".format(write_res):
                    result.append(write_res)
                if len(result) > 0:
                    self.test_results.append(["---FAIL--- {}".format(result), testname])
                else:
                    self.test_results.append(["pass", testname])

    def BTL_9_3_2_2_4(self, addresses):
        name = "9.13.2.2.4 Writing to a Nonexistent File"
        object = "file:2"
        contentToWrite = "Hello"
        for address in addresses:
            result = []
            testname = "{} [{}] [{}]".format(name, address, object)
            print(address)
            self.do_iut(address)
            #set up to write file.
            #first, set type to 2 (Thermostat unused)
            # self.do_writeProprietary("{} 603 2 Enumerated".format(object))
            self.write_value("{} fileSize 100".format(object))
            write_res = self.writestream(object=object, data=contentToWrite)
            if "unknownObject" not in "{}".format(write_res):
                result.append(write_res)
            if len(result) > 0:
                self.test_results.append(["---FAIL--- {}".format(result), testname])
            else:
                self.test_results.append(["pass", testname])

    def do_test123(self, args):
        args = args.split()
        print(args)
        self.BTL_9_18_2_1(args)

    def BTL_9_18_2_1(self, addresses):
        name = "9.18.2.1 Reading Non-Array Properties with an Array Index"
        objects = [["device:4194303","vendorName"],
                ["analogInput:1","presentValue"],
                ["analogOutput:1","presentValue"],
                ["analogValue:1","presentValue"],
                ["binaryInput:1","presentValue"],
                ["binaryOutput:1","presentValue"],
                ["binaryValue:1","presentValue"],
                ["file:1","fileSize"],
                ["loop:1","presentValue"]
                ]
        for address in addresses:
            for object, prop in objects:
                testname = "{} [{}] [{}]".format(name, address, object)
                # build a request
                request = ReadPropertyRequest(
                    objectIdentifier=object,
                    propertyIdentifier=prop,
                    )
                request.pduDestination = Address(address)
                request.propertyArrayIndex = 1

                result = {
                    'source': address.lower(), 'apduType': 'ErrorPDU',
                    'apduService': 'Error', 'function': 'Error',
                    'errorClass': 'property', 'errorCode': 'propertyIsNotAnArray'
                    }
                self.run_test(request, expected=result, name=testname)

    def BTL_9_18_2_2(self, addresses):
        name = "9.18.2.2 Reading Array Properties with an Array Index that is Out of Range"
        objects = [["device:4194303","objectList"],
                ["analogInput:1","propertyList"],
                ["analogOutput:1","propertyList"],
                ["analogValue:1","propertyList"],
                ["binaryInput:1","propertyList"],
                ["binaryOutput:1","propertyList"],
                ["binaryValue:1","propertyList"],
                ["file:1","propertyList"],
                ["loop:1","propertyList"]
                ]
        for address in addresses:
            for object, prop in objects:
                testname = "{} [{}] [{}]".format(name, address, object)
                # build a request
                request = ReadPropertyRequest(
                    objectIdentifier=object,
                    propertyIdentifier=prop,
                    )
                request.pduDestination = Address(address)
                request.propertyArrayIndex = 200

                result = {
                    'source': address.lower(), 'apduType': 'ErrorPDU',
                    'apduService': 'Error', 'function': 'Error',
                    'errorClass': 'property', 'errorCode': 'invalidArrayIndex'
                    }
                self.run_test(request, expected=result, name=testname)

    def BTL_9_18_2_3(self, addresses):
        name = "9.18.2.3 Reading an Unknown Object"
        objects = [["device:333","vendorName"],
                ["analogInput:333","presentValue"],
                ["analogOutput:333","presentValue"],
                ["analogValue:333","presentValue"],
                ["binaryInput:333","presentValue"],
                ["binaryOutput:333","presentValue"],
                ["binaryValue:333","presentValue"],
                ["file:333","fileSize"],
                ["loop:333","presentValue"]
                ]
        for address in addresses:
            for object, prop in objects:
                testname = "{} [{}] [{}]".format(name, address, object)
                # build a request
                request = ReadPropertyRequest(
                    objectIdentifier=object,
                    propertyIdentifier=prop,
                    )
                request.pduDestination = Address(address)
                result = {
                    'source': address.lower(), 'apduType': 'ErrorPDU',
                    'apduService': 'Error', 'function': 'Error',
                    'errorClass': 'object', 'errorCode': 'unknownObject'
                    }
                self.run_test(request, expected=result, name=testname)

    def BTL_9_18_2_4(self, addresses):
        name = "9.18.2.4 Reading an Unknown Property"
        objects = [["device:4194303","presentValue"],
                ["analogInput:1","vendorName"],
                ["analogOutput:1","vendorName"],
                ["analogValue:1","vendorName"],
                ["binaryInput:1","vendorName"],
                ["binaryOutput:1","vendorName"],
                ["binaryValue:1","vendorName"],
                ["file:1","vendorName"],
                ["loop:1","vendorName"],
                ["device:4194303",511],
                        ["analogInput:1",511],
                        ["analogOutput:1",4194304],
                        ["analogValue:1",511],
                        ["binaryInput:1",4194309],
                        ["binaryOutput:1",511],
                        ["binaryValue:1",511],
                        ["file:1",511],
                        ["loop:1",511]
                ]
        for address in addresses:
            for object, prop in objects:
                testname = "{} [{}] [{}]".format(name, address, object)
                # build a request
                request = ReadPropertyRequest(
                    objectIdentifier=object,
                    propertyIdentifier=prop,
                    )
                request.pduDestination = Address(address)
                result = {
                    'source': address.lower(), 'apduType': 'ErrorPDU',
                    'apduService': 'Error', 'function': 'Error',
                    'errorClass': 'property', 'errorCode': 'unknownProperty'
                    }
                self.run_test(request, expected=result, name=testname)

    def BTL_9_18_1_3(self, addresses):
        name = "9.18.1.3 Reading a Property From the Device Object using the Unknown Instance"
        objects = [["device:4194303","objectIdentifier"]]

        for address in addresses:
            self.do_iut(address)
            for object, prop in objects:
                result = []
                testname = "{} [{}] [{}]".format(name, address, object)
                obj_id = self.read_value("{} {}".format(object, prop))
                obj_id2 = self.read_value("{}:{} {}".format(obj_id[0], obj_id[1], prop))
                if obj_id != obj_id2:
                    result.append("obj_id ({}) != obj_id2 ({})".format(obj_id, obj_id2))
                if len(result) > 0:
                    self.test_results.append(["---FAIL--- {}".format(result), testname])
                else:
                    self.test_results.append(["pass", testname])


    def BTL_9_18_1_X4(self, addresses):
        print("not implemented: BTL_9_18_1_X4")

    def BTL_9_18_1_X1(self, addresses):
        print("not implemented: BTL_9_18_1_X1")

    def BTL_9_18_1_X1(self, addresses):
        print("not implemented: BTL_9_18_1_X1")

    def BTL_9_18_1_X1(self, addresses):
        print("not implemented: BTL_9_18_1_X1")

    def BTL_9_18_1_X1(self, addresses):
        print("not implemented: BTL_9_18_1_X1")

    def BTL_9_18_1_X1(self, addresses):
        print("not implemented: BTL_9_18_1_X1")

    def BTL_9_18_1_X1(self, addresses):
        print("not implemented: BTL_9_18_1_X1")

    def BTL_9_18_1_X1(self, addresses):
        print("not implemented: BTL_9_18_1_X1")

    def BTL_9_18_1_X1(self, addresses):
        print("not implemented: BTL_9_18_1_X1")

    def BTL_9_18_1_X1(self, addresses):
        print("not implemented: BTL_9_18_1_X1")

    def BTL_9_18_1_X1(self, addresses):
        print("not implemented: BTL_9_18_1_X1")

    def BTL_9_18_1_X1(self, addresses):
        print("not implemented: BTL_9_18_1_X1")

    def BTL_9_18_1_X1(self, addresses):
        print("not implemented: BTL_9_18_1_X1")

    def do_BTL_9(self, args):
        # self.BTL_9_24_2_1(args.split())
        # self.BTL_9_24_2_2(args.split())
        # self.BTL_9_24_1_3(args.split())
        # self.BTL_9_24_1_4(args.split())
        # self.BTL_9_24_1_1(args.split())
        # self.BTL_9_24_1_2(args.split())
        # self.BTL_9_24_1_5(args.split())
        self.BTL_9_24_2_3(args.split())
        self.BTL_9_27_2_X(args.split())
        # self.BTL_9_27_1_2(args.split())
        # self.BTL_9_27_1_4(args.split())
        # self.BTL_9_27_2_3(args.split())
        # self.BTL_9_27_2_4(args.split())

    def do_utc(self, args):
        """utc [address] <date yyyy-mm-dd dow> <time hh:mm:ss.hh>\n utc *:* 2021-03-24 fri 3:15:13.53"""
        address = None
        date = Date(datetime.utcnow().strftime('%Y-%m-%d %a'))    #Date().now()
        time = Time(datetime.utcnow().strftime('%H:%M:%S.%f')[0:11])   #Time().now()
        args = args.split()
        if len(args) > 0:
            address = args[0]
        if len(args) > 2:
            date = Date("{} {}".format(args[1], args[2]))
        if len(args) > 3:
            time = Time(args[3])
        if address is not None:
            self.send_utc_sync(address=address, datetime=DateTime(date=date, time=time))
        else:
            self.send_utc_sync()

        # """utc <day> <month> <year> <hour> <minute> <second> <hundreth>"""
        # args = args.split()
        # try:
        #     while len(args) < 7:
        #         args.append(0)
        #     for i in range (0,7):
        #         args[i] = int(args[i])
        #     d1 = (args[0] - 1900, args[1], args[2], 255)
        #     t1 = (args[3], args[4], args[5], args[6])
        #     request = UTCTimeSynchronizationRequest(
        #         time = DateTime(date=d1, time=t1)
        #         )
        #     request.pduDestination = Address("192.168.1.100")
        #     iocb = IOCB(request)
        #     if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)
        #
        #     # give it to the application
        #     this_application.request_io(iocb)
        # except Exception as error:
        #     TestConsoleCmd._exception("exception: %r", error)


    def send_utc_sync(self, address='*', datetime=None):
        if datetime is None:
            datetime = DateTime(date=Date().now(), time=Time().now())
        print(datetime.date, datetime.time, address)
        request = UTCTimeSynchronizationRequest(
                time = datetime
                )
        request.pduDestination = Address(address)
        iocb = IOCB(request)
        if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

        # give it to the application
        this_application.request_io(iocb)

    def do_VAV_issue22(self, args):
        """VAV_issue22 [address] [address]"""
        self.BTL_9_24_2_3(args.split())
        self.BTL_9_27_2_X(args.split())

    def BTL_9_24_1_1(self, addresses):
        name = "9.24.1.1 DCC Indefinite Time Duration Restored by DeviceCommunicationControl"
        dcc_time = 1
        for address in addresses:
            testname = "{} [{}]".format(name, address)
            result = []
            self.do_iut(address)
            dest = LocalBroadcast()
            if len(address.split(":")) > 1:
                dest = RemoteBroadcast(int(address.split(":")[0]))
                # dest = Address("2:*")
                # print("sending remoteBroadcast to network 2")

            self.send_whois(dest=dest)
            status = self.read_value("device:4194303 systemStatus")
            dcc_result = self.dcc(state="disable", password="123adftech123")
            start_time = time.time()
            print(start_time)
            msg_store.set_address_list = [address]
            msg_store.clear_msg()
            while (time.time() - start_time) < (dcc_time * 60):
                status2 = self.read_no_wait("device:4194303 systemStatus")
                self.send_whois(dest=dest)
                time.sleep(1)
            print("test time: ",time.time() - start_time)
            time.sleep(10)
            print("Check messages during DCC disabled")
            print(msg_store.get_msg())
            dcc_result2 = self.dcc(state="enable", password="123adftech123")
            status2 = self.read_value("device:4194303 systemStatus")
            if dcc_result != "ack":
                result.append("dcc result {} not an ack".format(dcc_result))
            if dcc_result != "ack":
                result.append("dcc result2 {} not an ack".format(dcc_result2))
            if status != status2:
                result.append("status before:{} post: {} do not match".format(status, status2))
            print("test time: ",time.time() - start_time)
            print("check messages after dcc has ben enabled.")
            print(msg_store.get_msg())
            if len(result):
                self.test_results.append(["failed", result, testname])
            else:
                self.test_results.append(["manual - verify no communication from DCC disable to DCC enable.".format(dcc_time * 60), testname])

    def BTL_9_24_1_2(self, addresses):
        name = "9.24.1.2 DCC Indefinite Time Duration Restored by ReinitializeDevice"
        dcc_time = 1
        for address in addresses:
            testname = "{} [{}]".format(name, address)
            result = []
            self.do_iut(address)
            dest = LocalBroadcast()
            if len(address.split(":")) > 1:
                dest = RemoteBroadcast(int(address.split(":")[0]))
                # dest = Address("2:*")
                # print("sending remoteBroadcast to network 2")

            self.send_whois(dest=dest)
            status = self.read_value("device:4194303 systemStatus")
            dcc_result = self.dcc(state="disable", password="123adftech123")
            start_time = time.time()
            print(start_time)
            msg_store.set_address_list = [address]
            msg_store.clear_msg()
            while (time.time() - start_time) < (dcc_time * 60):
                status2 = self.read_no_wait("device:4194303 systemStatus")
                self.send_whois(dest=dest)
                time.sleep(1)
            print("test time: ",time.time() - start_time)
            time.sleep(10)
            print("Check messages during DCC disabled")
            print(msg_store.get_msg())
            rd_result = self.rd(state="warmstart", password="123adftech123")
            #Wait for VAV to restart
            time.sleep(5)
            status2 = self.read_value("device:4194303 systemStatus")
            if dcc_result != "ack":
                result.append("dcc result {} not an ack".format(dcc_result))
            if rd_result != "ack":
                result.append("rd result2 {} not an ack".format(rd_result))
            if status != status2:
                result.append("status before:{} post: {} do not match".format(status, status2))
            print("test time: ",time.time() - start_time)
            print("check messages after dcc has ben enabled.")
            print(msg_store.get_msg())
            if len(result):
                self.test_results.append(["failed", result, testname])
            else:
                self.test_results.append(["manual - verify no communication from DCC disable to warmstart.".format(dcc_time * 60), testname])

    def BTL_9_24_1_3(self, addresses):
        name = "9.24.1.3 DCC Finite Time Duration"
        dcc_time = 2
        for address in addresses:
            testname = "{} [{}]".format(name, address)
            result = []
            self.do_iut(address)
            dest = LocalBroadcast()
            if len(address.split(":")) > 1:
                dest = RemoteBroadcast(int(address.split(":")[0]))
                # dest = Address("2:*")
                # print("sending remoteBroadcast to network 2")

            self.send_whois(dest=dest)
            status = self.read_value("device:4194303 systemStatus")
            dcc_result = self.dcc(state="disable", duration=dcc_time, password="123adftech123")
            start_time = time.time()
            print(start_time)
            while (time.time() - start_time) < (dcc_time * 60):
                status2 = self.read_no_wait("device:4194303 systemStatus")
                self.send_whois(dest=dest)
                time.sleep(1)
            print("test time: ",time.time() - start_time)
            self.test_results.append(["manual - verify no communication for {} seconds from DCC.".format(dcc_time * 60), testname])


    def BTL_9_24_1_4(self, addresses):
        name = "9.24.1.4 DCC Finite Time DurationRestored by DeviceCommunicationControl"
        dcc_time = 1
        for address in addresses:
            testname = "{} [{}]".format(name, address)
            result = []
            self.do_iut(address)
            dest = LocalBroadcast()
            if len(address.split(":")) > 1:
                dest = RemoteBroadcast(int(address.split(":")[0]))
                # dest = Address("2:*")
                # print("sending remoteBroadcast to network 2")

            self.send_whois(dest=dest)
            status = self.read_value("device:4194303 systemStatus")
            dcc_result = self.dcc(state="disable", duration=dcc_time+2, password="123adftech123")
            start_time = time.time()
            print(start_time)
            while (time.time() - start_time) < (dcc_time * 60):
                status2 = self.read_no_wait("device:4194303 systemStatus")
                self.send_whois(dest=dest)
                time.sleep(1)
            time.sleep(10)
            dcc_result2 = self.dcc(state="enable", password="123adftech123")
            status2 = self.read_value("device:4194303 systemStatus")
            if dcc_result != "ack":
                result.append("dcc result {} not an ack".format(dcc_result))
            if dcc_result != "ack":
                result.append("dcc result2 {} not an ack".format(dcc_result2))
            if status != status2:
                result.append("status before:{} post: {} do not match".format(status, status2))
            print("test time: ",time.time() - start_time)
            if len(result):
                self.test_results.append(["failed", result, testname])
            else:
                self.test_results.append(["manual - verify no communication for {} seconds from DCC.".format(dcc_time * 60), testname])

    def BTL_9_24_1_5(self, addresses):
        name = "9.24.1.5 DCC Finite Time Duration Restored by ReinitializeDevice"
        dcc_time = 1
        for address in addresses:
            testname = "{} [{}]".format(name, address)
            result = []
            self.do_iut(address)
            dest = LocalBroadcast()
            if len(address.split(":")) > 1:
                dest = RemoteBroadcast(int(address.split(":")[0]))
                # dest = Address("2:*")
                # print("sending remoteBroadcast to network 2")

            self.send_whois(dest=dest)
            obj_name = self.read_value("device:4194303 objectName")
            dcc_result = self.dcc(state="disable", duration=dcc_time + 5, password="123adftech123")
            start_time = time.time()
            print(start_time)
            msg_store.set_address_list = [address]
            msg_store.clear_msg()
            while (time.time() - start_time) < (dcc_time * 60):
                status2 = self.read_no_wait("device:4194303 systemStatus")
                self.send_whois(dest=dest)
                time.sleep(1)
            print("test time: ",time.time() - start_time)
            time.sleep(10)
            print("Check messages during DCC disabled")
            print(msg_store.get_msg())
            rd_result = self.rd(state="warmstart", password="123adftech123")
            #Wait for VAV to restart
            time.sleep(5)
            obj_name2 = self.read_value("device:4194303 objectName")
            if dcc_result != "ack":
                result.append("dcc result {} not an ack".format(dcc_result))
            if rd_result != "ack":
                result.append("rd result2 {} not an ack".format(rd_result))
            if obj_name != obj_name2:
                result.append("status before:{} post: {} do not match".format(obj_name, obj_name2))
            print("test time: ",time.time() - start_time)
            print("check messages after dcc has ben enabled.")
            print(msg_store.get_msg())
            if len(result):
                self.test_results.append(["failed", result, testname])
            else:
                self.test_results.append(["manual - verify no communication from DCC disable to warmstart.".format(dcc_time * 60), testname])

    def BTL_9_24_2_1(self, addresses):
        name = "9.24.2.1 DCC Invalid Password"

        for address in addresses:
            testname = "{} [{}]".format(name, address)
            result = []
            self.do_iut(address)
            status = self.read_value("device:4194303 systemStatus")
            dcc_result = self.dcc(state="disable", password="wrong")
            status2 = self.read_value("device:4194303 systemStatus")

            print (status, dcc_result, status2)
            if dcc_result == "security: passwordFailure":
                print(testname, "success")
            else:
                result.append("dcc result [{}] is not passwordFailure".format(dcc_result))
            if status != status2:
                result.append("systemStatus before:{} after:{}".format(status, status2))
            if status != "operational":
                result.append("systemStatus [{}] is not operational".format(status))
            if len(result) > 0:
                self.test_results.append(["---FAIL--- {}".format(result), testname])
            else:
                self.test_results.append(["pass", testname])

    def BTL_9_24_2_2(self, addresses):
        name = "9.24.2.2 DCC Missing Password"

        for address in addresses:
            testname = "{} [{}]".format(name, address)
            result = []
            self.do_iut(address)
            status = self.read_value("device:4194303 systemStatus")
            dcc_result = self.dcc(state="disable")
            status2 = self.read_value("device:4194303 systemStatus")

            print (status, dcc_result, status2)
            if dcc_result == "security: passwordFailure" or dcc_result == "services: missingRequiredParameter":
                print(testname, "success")
            else:
                result.append("dcc result [{}] is not passwordFailure".format(dcc_result))
            if status != status2:
                result.append("systemStatus before:{} after:{}".format(status, status2))
            if status != "operational":
                result.append("systemStatus [{}] is not operational".format(status))
            if len(result) > 0:
                self.test_results.append(["---FAIL--- {}".format(result), testname])
            else:
                self.test_results.append(["pass", testname])

    def BTL_9_24_2_3(self, addresses):
        name = "9.24.2.3 DCC Restore by ReinitializeDevice with Invalid 'Reinitialized State of Device'"
        dcc_time = 5
        for address in addresses:
            testname = "{} [{}]".format(name, address)
            result = []
            self.do_iut(address)
            dest = LocalBroadcast()
            if len(address.split(":")) > 1:
                dest = RemoteBroadcast(int(address.split(":")[0]))
                # dest = Address("2:*")
                # print("sending remoteBroadcast to network 2")

            self.send_whois(dest=dest)
            obj_name = self.read_value("device:4194303 objectName")
            dcc_result = self.dcc(state="disable", duration=dcc_time + 5, password="123adftech123")
            if dcc_result != "ack":
                result.append("dcc result {} not an ack".format(dcc_result))

            msg_store.set_address_list = [address]
            msg_store.clear_msg()
            for self.mode in ["startBackup", "endBackup", "startRestore", "endRestore", "abortRestore"]:
                rd_result = self.rd(state=self.mode, password="123adftech123")
                if rd_result not in ["services: communicationDisabled", "services: optionalFunctionalityNotSupported"]:#Current response: ["services: rejectUnrecognizedService"]
                    result.append("rd response incorrect: {}:{}".format(self.mode, rd_result))

            obj_name2 = self.read_value("device:4194303 objectName")
            if not isinstance(obj_name2, dict):
                result.append("device responded to a read request when communication should be disabled")
            elif obj_name2['apduAbortRejectReason'] != 65:
                result.append("device responded to a read request when communication should be disabled with error {}".format(obj_name2['apduAbortRejectReason']))
            dcc_result = self.dcc(state="enable", duration=dcc_time + 5, password="123adftech123")
            obj_name2 = self.read_value("device:4194303 objectName")
            for self.mode in ["startBackup", "endBackup", "startRestore", "endRestore", "abortRestore"]:
                rd_result = self.rd(state=self.mode, password="123adftech123")
                    # if rd_result not in ["services: communicationDisabled", "services: optionalFunctionalityNotSupported"]:#Current response: ["services: rejectUnrecognizedService"]
                    #     result.append("rd response incorrect: {}:{}".format(self.mode, rd_result))
            if obj_name2 != obj_name:
                result.append("object name not the same before / after. [{}, {}]".format(obj_name, obj_name2))
            if len(result):
                self.test_results.append(["failed", result, testname])
            else:
                self.test_results.append(["pass".format(dcc_time * 60), testname])

    def BTL_9_27_1_2(self, addresses):
        name = "9.27.1.2 COLDSTART with a Correct Password"
        dcc_time = 5
        for address in addresses:
            testname = "{} [{}]".format(name, address)
            result = []
            self.do_iut(address)
            time1 = self.read_value("device:4194303 timeOfDeviceRestart")
            reason1 = self.read_value("device:4194303 lastRestartReason")
            print(time1.dateTime.time, time1.dateTime.date, reason1)
            rd_result = self.rd(state="coldstart", password="123adftech123")
            if rd_result != "ack":
                result.append("rd result is not an ack [{}]".format(rd_result))
            time.sleep(5)
            time2 = self.read_value("device:4194303 timeOfDeviceRestart")
            reason2 = self.read_value("device:4194303 lastRestartReason")
            print(time2.dateTime.time, time2.dateTime.date, reason2)
            if time1.dateTime.time == time2.dateTime.time:
                result.append("Last restart time did not change. {} {}".format(time1.dateTime.time, time2.dateTime.time))
            if reason2 != "coldstart":
                result.append("Last Restart reason is not coldstart ({})".format(reason2))
            if len(result):
                self.test_results.append(["failed", result, testname])
            else:
                self.test_results.append(["pass", testname])

    def BTL_9_27_1_4(self, addresses):
        name = "9.27.1.4 WARMSTART with a Correct Password"
        dcc_time = 5
        for address in addresses:
            testname = "{} [{}]".format(name, address)
            result = []
            self.do_iut(address)
            time1 = self.read_value("device:4194303 timeOfDeviceRestart")
            reason1 = self.read_value("device:4194303 lastRestartReason")
            print(time1.dateTime.time, time1.dateTime.date, reason1)
            rd_result = self.rd(state="warmstart", password="123adftech123")
            if rd_result != "ack":
                result.append("rd result is not an ack [{}]".format(rd_result))
            time.sleep(5)
            time2 = self.read_value("device:4194303 timeOfDeviceRestart")
            reason2 = self.read_value("device:4194303 lastRestartReason")
            print(time2.dateTime.time, time2.dateTime.date, reason2)
            if time1.dateTime.time == time2.dateTime.time:
                result.append("Last restart time did not change. {} {}".format(time1.dateTime.time, time2.dateTime.time))
            if reason2 != "warmstart":
                result.append("Last Restart reason is not warmstart ({})".format(reason2))
            if len(result):
                self.test_results.append(["failed", result, testname])
            else:
                self.test_results.append(["pass", testname])

    def BTL_9_27_2_3(self, addresses):
        name = "9.27.2.3 COLDSTART with Missing or Invalid Password"
        for address in addresses:
            testname = "{} [{}]".format(name, address)
            result = []
            self.do_iut(address)
            time1 = self.read_value("device:4194303 timeOfDeviceRestart")
            if isinstance(time1, TimeStamp):
                time1 = time1.dateTime.time
            reason1 = self.read_value("device:4194303 lastRestartReason")
            print(time1, reason1)
            rd_result = self.rd(state="coldstart")
            if rd_result == "ack":
                result.append("rd result with missing password is an ack ".format(rd_result))
            elif rd_result not in ["security: passwordFailure"]:
                result.append("rd result is not passwordFailure [{}]".format(rd_result))
            rd_result = self.rd(state="coldstart", password="wrong")
            if rd_result == "ack":
                result.append("rd result with wrong password is an ack ".format(rd_result))
            elif rd_result not in ["security: passwordFailure"]:
                result.append("rd result is not passwordFailure [{}]".format(rd_result))

            time2 = self.read_value("device:4194303 timeOfDeviceRestart")
            if isinstance(time2, TimeStamp):
                time2 = time2.dateTime.time
            reason2 = self.read_value("device:4194303 lastRestartReason")
            print(time2, reason2)
            if time1 != time2:
                result.append("Last restart time changed. {} {}".format(time1, time2))
            if reason2 != reason1:
                result.append("Last Restart reason has changed ({},{})".format(reason1, reason2))
            if len(result):
                self.test_results.append(["failed", result, testname])
            else:
                self.test_results.append(["pass", testname])

    def BTL_9_27_2_4(self, addresses):
        name = "9.27.2.4 WARMSTART with Missing or Invalid Password"
        for address in addresses:
            testname = "{} [{}]".format(name, address)
            result = []
            self.do_iut(address)
            time1 = self.read_value("device:4194303 timeOfDeviceRestart")
            if isinstance(time1, TimeStamp):
                time1 = time1.dateTime.time
            reason1 = self.read_value("device:4194303 lastRestartReason")
            print(time1, reason1)
            rd_result = self.rd(state="warmstart")
            if rd_result == "ack":
                result.append("rd result with missing password is an ack ".format(rd_result))
            elif rd_result not in ["security: passwordFailure"]:
                result.append("rd result is not passwordFailure [{}]".format(rd_result))
            rd_result = self.rd(state="warmstart", password="wrong")
            if rd_result == "ack":
                result.append("rd result with wrong password is an ack ".format(rd_result))
            elif rd_result not in ["security: passwordFailure"]:
                result.append("rd result is not passwordFailure [{}]".format(rd_result))

            time2 = self.read_value("device:4194303 timeOfDeviceRestart")
            if isinstance(time2, TimeStamp):
                time2 = time2.dateTime.time
            reason2 = self.read_value("device:4194303 lastRestartReason")
            print(time2, reason2)
            if time1 != time2:
                result.append("Last restart time changed. {} {}".format(time1, time2))
            if reason2 != reason1:
                result.append("Last Restart reason has changed ({},{})".format(reason1, reason2))
            if len(result):
                self.test_results.append(["failed", result, testname])
            else:
                self.test_results.append(["pass", testname])

    def BTL_9_27_2_X(self, addresses):
        name = "9.27.2.X Rejects Unsupported Reinitialize Types"
        dcc_time = 5
        for address in addresses:
            testname = "{} [{}]".format(name, address)
            result = []
            self.do_iut(address)

            for self.mode in ["startBackup", "endBackup", "startRestore", "endRestore", "abortRestore"]:
                rd_result = self.rd(state=self.mode, password="123adftech123")
                if rd_result not in ["services: optionalFunctionalityNotSupported"]:#Current response: ["services: rejectUnrecognizedService"]
                    result.append("rd response incorrect: {}:{}".format(self.mode, rd_result))
            if len(result):
                self.test_results.append(["failed", result, testname])
            else:
                self.test_results.append(["pass".format(dcc_time * 60), testname])



    def send_whohas(self, lowlimit=None, highlimit=None, objectID=None, objectName=None):
        whohaslimits = WhoHasLimits()
        if lowlimit is not None:
            whohaslimits.deviceInstanceRangeLowLimit = lowlimit
        if highlimit is not None:
            whohaslimits.deviceInstanceRangeHighLimit = highlimit
        whohasobject = WhoHasObject()
        if objectID is not None:
            whohasobject.objectIdentifier = ObjectIdentifier(objectID)
        if lowlimit is not None:
            whohasobject.objectName = objectName
        request = WhoHasRequest(
            limits=whohaslimits,
            object=whohasobject
        )
        request.pduDestination = GlobalBroadcast()
        try:
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)
        except Exception as error:
            print("error: {}".format(error))

    def do_whohas(self, args):
        """whohas ["Name" or objectType:Instance] [lowlimit] [highlimit]"""
        lowlimit = None
        highlimit = None
        objectID = None
        objectName = None
        try:
            if '"' in args:
                args = args.split('"')
                objectName = args[1]
                args = args[2].split()
            else:
                args = args.split()
                objectID = args.pop(0)
            if len(args) >= 2:
                lowlimit = int(args[0])
                highlimit = int(args[1])
        except Exception as error:
            print("whohas - fail to get parameters [{}]".format(error))
        self.send_whohas(lowlimit=lowlimit, highlimit=highlimit, objectID=objectID, objectName=objectName)

    def do_whois_blast(self, args):
        for i in range(0,10):
            self.do_whois_addr(args)

    def do_whois_addr(self, args):
        """whois_addr <Address> <low> <high>"""
        args = args.split()
        addr = None
        high = None
        low = None

        if len(args) >= 1:
            addr = Address(args[0])
        if len(args) >= 3:
            low = int(args[1])
            high = int(args[2])
        self.send_whois(lowlimit=low, highlimit=high, dest=addr)

    def send_whois(self, lowlimit=None, highlimit=None, dest=None):
                request = WhoIsRequest(
                    # deviceInstanceRangeLowLimit=whohaslimits,
                    # deviceInstanceRangeHighLimit=whohasobject
                )
                if lowlimit is not None:
                    request.deviceInstanceRangeLowLimit = lowlimit
                if highlimit is not None:
                    request.deviceInstanceRangeHighLimit = highlimit
                if dest is None:
                    request.pduDestination = GlobalBroadcast()
                else:
                    request.pduDestination = dest
                try:
                    iocb = IOCB(request)
                    if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

                    # give it to the application
                    this_application.request_io(iocb)
                except Exception as error:
                    print("error: {}".format(error))

    def do_whois(self, args):
        """whois lowlimit highlimit"""
        lowlimit = None
        highlimit = None
        args = args.split()
        try:
            if len(args) >= 2:
                lowlimit = int(args[0])
                highlimit = int(args[1])
        except Exception as error:
            print("error in decoding limits [{}]".format(error))
        self.send_whois(lowlimit=lowlimit, highlimit=highlimit)

    def run_test_unconfirmed(self, request, expected="none", name="none", wait_time=6):
        print("Running Test {}".format(name))
        print(request.dict_contents())
        if expected == "none":
            msg_store.clear_msg()

        try:
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)
        except Exception as error:
            self.test_results.append([None, name + error])

        sleep(wait_time)
        msglst = msg_store.get_msg()
        if expected=="manual":
            self.test_results.append(["--Manual Check--", name])
        elif len(msglst) > 0:
            print ("\n---FAIL---\n")
            for x in msglst:
                print(x.dict_contents())
            self.test_results.append(["---FAIL---", name])
        else:
            self.test_results.append(["pass", name])


    def run_test(self, request, expected, name="none"):
        print("Running Test {}".format(name))
        print(request.dict_contents())
        try:
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            apdu = None

            if expected=="SEGMENTATION_NOT_SUPPORTED":
                print("expecting segmentation not supported.")
                if iocb.ioError:
                    print(iocb.ioError.dict_contents())
                    if isinstance(iocb.ioError, SegmentationNotSupported):
                        print("\n\tPASS", name,"\n\n")
                        self.test_results.append(["pass", name])
                        return True
                print("\n\t-----Fail-----", name,"\n\n")
                self.test_results.append(["---FAIL---", name])
                return False

            # do something for success
            if iocb.ioResponse:
                apdu = iocb.ioResponse
                if isinstance(iocb.ioResponse, SimpleAckPDU):
                    print("SimpleAck recieved")
                elif isinstance(iocb.ioResponse, ComplexAckPDU):
                    print("ComplexAck received")
                print(apdu.dict_contents())

            # do something for error/reject/abort
            if iocb.ioError:
                apdu = iocb.ioError
                sys.stdout.write(str(iocb.ioError) + '\n')
                print(iocb.ioError.dict_contents())

            res = True
            if expected is not None and apdu is not None:
                apdu_res = apdu.dict_contents()
                for x in expected:
                    print('\n',x,':\nexpected =', expected[x],'\nreceived =', apdu_res[x])
                    if (type(apdu_res[x]) is str) or (type(apdu_res[x]) is int):
                        print('received type : {}\n'.format(type(apdu_res[x])))
                        if apdu_res[x] not in expected[x]:
                            print("FAIL\n")
                            res = False
                        else:
                            print("PASS\n")
                    elif type(apdu_res[x]) is list:
                        print('received type : {}\n'.format(type(apdu_res[x])))
                        if apdu_res[x] != expected[x]:
                            print("FAIL\n")
                            res = False
                        else:
                            print("PASS\n")
                    else:
                        print('Unsupported data type received\n')

            if res:
                print("\n\tPASS", name,"\n\n")
                self.test_results.append(["pass", name])
                return True
            else:
                print("\n\t-----Fail-----", name,"\n\n")
                self.test_results.append(["---FAIL---", name])
                return False

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)
            print("Test Failed")
            self.test_results.append([None, name])

    def do_showStuff(self, args):
        print("this_application", this_application)
        # print("this_application", this_application.dict_contents())unconfirmed request encoding error: TypeError('invalid constructor datatype',)

        print("this_application ASAP", this_application.asap)
        print(" - (ServiceAccessPoint.serviceID)", this_application.asap.serviceID)
        print(" - (ServiceAccessPoint.serviceElement)", this_application.asap.serviceElement)
        print(" - (ApplicationServiceElement.elementID)", this_application.asap.elementID)
        print(" - (ApplicationServiceElement.elementService)", this_application.asap.elementService)
        print("this_application SMAP", this_application.smap)
        print(" - (StateMachineAccessPoint.localDevice)", this_application.smap.localDevice)
        print(" - (StateMachineAccessPoint.deviceInfoCache)", this_application.smap.deviceInfoCache)
        print(" - (StateMachineAccessPoint.nextInvokeID)", this_application.smap.nextInvokeID)
        print(" - (StateMachineAccessPoint.clientTransactions)", this_application.smap.clientTransactions)
        print(" - (StateMachineAccessPoint.serverTransactions)", this_application.smap.serverTransactions)
        print(" - (StateMachineAccessPoint.numberOfApduRetries)", this_application.smap.numberOfApduRetries)
        print(" - (StateMachineAccessPoint.apduTimeout)", this_application.smap.apduTimeout)
        print(" - (StateMachineAccessPoint.maxApduLengthAccepted)", this_application.smap.maxApduLengthAccepted)
        print(" - (StateMachineAccessPoint.segmentationSupported)", this_application.smap.segmentationSupported)
        print(" - (StateMachineAccessPoint.segmentTimeout)", this_application.smap.segmentTimeout)
        print(" - (StateMachineAccessPoint.maxSegmentsAccepted)", this_application.smap.maxSegmentsAccepted)
        print(" - (StateMachineAccessPoint.proposedWindowSize)", this_application.smap.proposedWindowSize)
        print(" - (StateMachineAccessPoint.dccEnableDisable)", this_application.smap.dccEnableDisable)
        print(" - (StateMachineAccessPoint.applicationTimeout)", this_application.smap.applicationTimeout)
        print(" - (Client.clientID)", this_application.smap.clientID)
        print(" - (Client.clientPeer)", this_application.smap.clientPeer)
        print(" - (ServiceAccessPoint.serviceID)", this_application.smap.serviceID)
        print(" - (ServiceAccessPoint.serviceElement)", this_application.smap.serviceElement)

        print("this_application Network Service Element", this_application.nse)
        print(" - (ApplicationServiceElement.elementID)", this_application.nse.elementID)
        print(" - (ApplicationServiceElement.ElementService)", this_application.nse.elementService)
        print("this_application BIP", this_application.bip)
        print(" - (ServiceAccessPoint.serviceID)", this_application.bip.serviceID)
        print(" - (ServiceAccessPoint.serviceElement)", this_application.bip.serviceElement)
        print(" - (Client.clientID)", this_application.bip.clientID)
        print(" - (Client.clientPeer)", this_application.bip.clientPeer)
        print(" - (Server.serverID)", this_application.bip.serverID)
        print(" - (Server.serverPeer)", this_application.bip.serverPeer)
        print("this_application AnnexJ", this_application.annexj)
        print(" - (Client.clientID)", this_application.annexj.clientID)
        print(" - (Client.clientPeer)", this_application.annexj.clientPeer)
        print(" - (Server.serverID)", this_application.annexj.serverID)
        print(" - (Server.serverPeer)", this_application.annexj.serverPeer)
        print("this_application MUX", this_application.mux)
        print(" - (UDPmultiplexer.address)", this_application.mux.address)
        print(" - (UDPmultiplexer.addrTuple)", this_application.mux.addrTuple)
        print(" - (UDPmultiplexer.addrBroadcastTuple)", this_application.mux.addrBroadcastTuple)
        print(" - (UDPmultiplexer.broadcast)", this_application.mux.broadcast)
        print(" - (UDPmultiplexer.broadcastPort)", this_application.mux.broadcastPort)
        print(" - (UDPmultiplexer.annexH)", this_application.mux.annexH)
        print(" - (UDPmultiplexer.annexJ)", this_application.mux.annexJ)
        print(" - (UDPmultiplexer.directPort)", this_application.mux.directPort)
        print(" - (UDPmultiplexer.directPort.timeout)", this_application.mux.directPort.timeout)
        print(" - (UDPmultiplexer.directPort.peers)", this_application.mux.directPort.peers)
        for x in this_application.mux.directPort.peers:
            print(" - (UDPmultiplexer.directPort.peers)", this_application.mux.directPort.peers[x].peer)
        print(" - (UDPmultiplexer.broadcastPort)", this_application.mux.broadcastPort)
        print(" - (UDPmultiplexer.broadcastPort.timeout)", this_application.mux.broadcastPort.timeout)
        print(" - (UDPmultiplexer.broadcastPort.peers)", this_application.mux.broadcastPort.peers)
        for x in this_application.mux.broadcastPort.peers:
            print(" - (UDPmultiplexer.broadcastPort.peers)", this_application.mux.broadcastPort.peers[x].peer)

    def do_delActor(self, args):
        actor_list = []
        for x in this_application.mux.directPort.peers:
            actor_list.append(x)
        for x in actor_list:
            this_application.mux.directPort.del_actor(this_application.mux.directPort.peers[x])

    def do_udpDirector(self, args):
        # this_application.mux.directPort.close_socket()
        # this_application.mux.directPort = self.directPort = UDPDirector(this_application.mux.addrTuple, actorClass = UDPActor1)
        this_application.mux.directPort.add_actor(UDPActor1(this_application.mux.directPort, ('192.168.1.255', 47808)))
        this_application.mux.directPort.add_actor(UDPActor1(this_application.mux.directPort, ('192.168.1.155', 47808)))
        this_application.mux.directPort.add_actor(UDPActor1(this_application.mux.directPort, ('192.168.1.30', 47808)))
        this_application.mux.broadcastPort.add_actor(UDPActor1(this_application.mux.broadcastPort, ('192.168.1.255', 47808)))
        this_application.mux.broadcastPort.add_actor(UDPActor1(this_application.mux.broadcastPort, ('192.168.1.155', 47808)))
        this_application.mux.broadcastPort.add_actor(UDPActor1(this_application.mux.broadcastPort, ('192.168.1.30', 47808)))

    def BTL_14_1_1_6(self):
        # Note:  to capture the BVLL response, we are adding a service element to the BIPSimple in the application
        old_serviceelement = this_application.bip.serviceElement
        capture = BVLL_Capture()
        this_application.bip.serviceElement = capture

        test_list = []
        test = {}
        test['expected'] = {'type': 129, 'function': 'Result', 'length': 6, 'result_code': 16}
        test['name'] = "14.1.1 Write-Broadcast-Distribution-Table"
        address = args
        test['request'] = WriteBroadcastDistributionTable([])
        test['request'].pduDestination = Address(address)
        test_list.append(test)
        test = {}
        test['expected'] = {'type': 129, 'function': 'Result', 'length': 6, 'result_code': 32}
        test['name'] = "14.1.2 Read-Broadcast-Distribution-Table"
        test['request'] = ReadBroadcastDistributionTable()
        test['request'].pduDestination = Address(address)
        test_list.append(test)
        test = {}
        test['expected'] = {'type': 129, 'function': 'Result', 'length': 6, 'result_code': 48}
        test['name'] = "14.1.3 Register-Foreign-Device"
        test['request'] = RegisterForeignDevice(ttl=36)
        test['request'].pduDestination = Address(address)
        test_list.append(test)
        test = {}
        test['expected'] = {'type': 129, 'function': 'Result', 'length': 6, 'result_code': 80}
        test['name'] = "14.1.4 Delete-Foreign-Device-Entry"
        test['request'] = DeleteForeignDeviceTableEntry(addr=Address("192.168.1.5"))
        test['request'].pduDestination = Address(address)
        test_list.append(test)
        test = {}
        test['expected'] = {'type': 129, 'function': 'Result', 'length': 6, 'result_code': 64}
        test['name'] = "14.1.5 Read-Foreign-Device-Table"
        test['request'] = ReadForeignDeviceTable()
        test['request'].pduDestination = Address(address)
        test_list.append(test)
        test = {}
        test['expected'] = {'type': 129, 'function': 'Result', 'length': 6, 'result_code': 96}
        test['name'] = "14.1.6 Distribute-Broadcast-To-Network"
        whoisrequest = xtob('0120ffff00ff1008')  # Whois Request
        test['request'] = DistributeBroadcastToNetwork(whoisrequest)
        test['request'].pduDestination = Address(address)
        test_list.append(test)

        for x in test_list:
            print(x['name'])
            this_application.annexj.indication(x['request'])
            sleep(5)
            resp = capture.get_list()
            capture.clear_list()
            if len(resp) == 1:
                print(resp[0].dict_contents())
                if resp[0].dict_contents() == x['expected']:
                    print("PASS")
                    self.test_results.append(["pass", x['name']])
                else:
                    print("FAIL")
                    self.test_results.append(["---FAIL--- ({})".format(resp[0].dict_contents()), x['name']])
            else:
                self.test_results.append(["---FAIL--- (responses: {})".format(len(resp)), x['name']])
        this_application.bip.serviceElement = old_serviceelement

    def BTL_14_1_8(self):
        self.test_results.append("14.1.8 Original-Broadcast-NPDU")
        self.test_results.append("Manual check. verify an I-Am is sent from the device.")
        self.test_results.append("Manual check. verify no Forwarded-NPDUs are issued from the device.")
        # whoisrequest = xtob('0120ffff00ff1008')  # Whois Request
        self.send_whois()

        # def do_forward(self, args):
    def BTL_14_1_10(self, sourceAddr=xtob('c0a80104bac0')):
        self.test_results.append("14.1.10 Forwarded-NPDU (Two-hop Distribution)")
        self.test_results.append("Manual check. verify an I-Am is sent from the device.")
        self.test_results.append("Manual check. verify no Forwarded-NPDUs are issued from the device.")
        # whoisrequest = xtob('0120ffff00ff1008')  # Whois Request
        whoisrequest = WhoIsRequest()
        whoisrequest.addrAddr = LocalBroadcast()
        # test_apdu = APDU()
        test_apdu = WhoIsRequest()
        print(test_apdu, test_apdu.dict_contents())
        print(whoisrequest, whoisrequest.dict_contents())
        print(whoisrequest.encode(test_apdu))
        print(test_apdu)
        test_apdu.addrAddr = xtob('c0a80104bac0')

        # xpdu = ForwardedNPDU(whoisrequest, destination=None, user_data=pdu.pduUserData)
        xpdu = ForwardedNPDU(test_apdu, destination=LocalBroadcast())
        xpdu.pduData = xtob('0120ffff00ff1008')

        msg_store.set_address_list(['all'])
        msg_store.clear_msg()
        # xpdu.pduDestination = LocalBroadcast()
        this_application.bip.request(xpdu)
        sleep (6)

        # def do_forward(self, args):
    def BTL_14_1_X11(self, sourceAddr=xtob('c0a80204bac1')):
        self.test_results.append("14.1.X11 Processing Forwarded-NPDU request initiated from different port")
        self.test_results.append("Manual check. verify an I-Am is sent from the device.")
        self.test_results.append("Manual check. verify no Forwarded-NPDUs are issued from the device.")
        # whoisrequest = xtob('0120ffff00ff1008')  # Whois Request
        whoisrequest = WhoIsRequest()
        whoisrequest.addrAddr = LocalBroadcast()
        # test_apdu = APDU()
        test_apdu = WhoIsRequest()
        print(test_apdu, test_apdu.dict_contents())
        print(whoisrequest, whoisrequest.dict_contents())
        print(whoisrequest.encode(test_apdu))
        print(test_apdu)
        test_apdu.addrAddr = xtob('c0a80104bac0')

        # xpdu = ForwardedNPDU(whoisrequest, destination=None, user_data=pdu.pduUserData)
        xpdu = ForwardedNPDU(test_apdu, destination=LocalBroadcast())
        xpdu.pduData = xtob('0120ffff00ff1008')

        msg_store.set_address_list(['all'])
        msg_store.clear_msg()
        # xpdu.pduDestination = LocalBroadcast()
        this_application.bip.request(xpdu)
        sleep (6)

    def create_confirmed_service_request(self, address, service):
        try:
            if service == ConfirmedPrivateTransferRequest().serviceChoice:
                request = ConfirmedPrivateTransferRequest(
                    vendorID = 200,
                    serviceNumber = 0
                )
                request.pduDestination = Address(address)
            else:
                request = ConfirmedRequestPDU()
                request.apduService = service
                request.pduDestination = Address(address)
            return request
        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)
            return None

    def create_unconfirmed_service_request(self, address, service):
        try:
            if service == 4:#UnconfirmedPrivateTransferRequest.serviceChoice: #4
                request = UnconfirmedRequestPDU()
                request.apduService = service
                request.pduDestination = Address(address)
                # request = UnconfirmedPrivateTransferRequest(
                    # vendorID=750,
                    # serviceNumber=45
                # )
                # a = Any()
                # a.cast_in(CharacterString('serviceParamsA'))
                # request.serviceParameters = a
                addHex(request, "09c81920")
            if service == UnconfirmedTextMessageRequest.serviceChoice: #5
                request = UnconfirmedTextMessageRequest(
                    textMessageSourceDevice = 99,
                    messagePriority=UnconfirmedTextMessageRequestMessagePriority(0),
                    message="Testing"
                )
                request.pduDestination = Address(address)
            else:
                request = UnconfirmedRequestPDU()
                request.apduService = service
                request.pduDestination = Address(address)
            return request
        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)
            return None

    def get_ui_settings(self, address):
        results = {}
        self.do_iut(address)
        for obj in ['analogInput:1', 'analogInput:2', 'binaryInput:1', 'binaryInput:2']:
            results[obj] = {}
            ui = self.read_unsigned(obj, 514)
            results[obj][514] = ui
            if 'analog' in obj:
                type = self.read_enumerated(obj, 513)
                results[obj][513] = type
        print(results)
        return results

    def write_ui_settings(self, address, settings):
        # Set all inputs to disconnected from ui.
        print(settings)
        self.do_iut(address)
        for obj in settings:
            self.do_writeProprietary("{} {} {} Unsigned".format(obj,514,0))
        for obj in settings:
            for prop in settings[obj]:
                print(obj, prop, settings[obj][prop])
                if prop == 514 and settings[obj][prop] != 0:
                    self.do_writeProprietary("{} {} {} Unsigned".format(obj,514,settings[obj][prop]))
                if prop == 513 and settings[obj][514] != 0:
                    self.do_writeProprietary("{} {} {} Enumerated".format(obj,prop,settings[obj][prop]))

    def do_abcdef(self, args):
        for x in range(0, 10):
            self.do_iut('77:0x4c11aedfe7e4')
            print(str(self.read_value('analogInput:2 presentValue')))
            print(str(self.read_value('analogInput:1 presentValue')))
            self.do_iut('192.168.1.100')
            print(str(self.read_value('analogOutput:2 presentValue')))
            print(str(self.read_value('analogOutput:1 presentValue')))


    def do_send_csv(self,args):
        webRestApi.test_json()

    def do_mbcsv(self,args):
        self.do_webGET('xt/serial/2/modbus/csv')

    def do_mbstart(self,args):
        self.do_webPATCH('xt/serial/2/modbus {"command":"start"}')

    def do_mbstop(self,args):
        self.do_webPATCH('xt/serial/2/modbus {"command":"stop"}')
        

    def do_testAdd(self,args):
        self.do_addModbusList('')
        for i in Range(0,60):
            self.do_webDELETE('xt/serial/2/modbus/list {"index":0}')

    def do_addModbusList(self, args):
        
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"abc002","bacnet_id":2,"device_id":1,"address":1,"format_str":"Int32","order_str":"CDAB","type":"Register","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"abc003","bacnet_id":3,"device_id":1,"address":1,"format_str":"Int32","order_str":"CDAB","type":"Register","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"abc004","bacnet_id":4,"device_id":1,"address":1,"format_str":"Int32","order_str":"CDAB","type":"Register","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"abc005","bacnet_id":5,"device_id":1,"address":1,"format_str":"Int32","order_str":"CDAB","type":"Register","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"abc006","bacnet_id":6,"device_id":1,"address":1,"format_str":"Int32","order_str":"CDAB","type":"Register","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"abc007","bacnet_id":7,"device_id":1,"address":1,"format_str":"Int32","order_str":"CDAB","type":"Register","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"abc008","bacnet_id":8,"device_id":1,"address":1,"format_str":"Int32","order_str":"CDAB","type":"Register","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":100,"format_str":"Uint32","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":102,"format_str":"Uint32","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":2}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":104,"format_str":"Uint32","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":3}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":106,"format_str":"Uint32","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":4}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":108,"format_str":"Uint32","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":110,"format_str":"Uint32","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":2}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":112,"format_str":"Uint32","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":3}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":200,"format_str":"Uint64","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":204,"format_str":"Uint64","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":2}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":208,"format_str":"Uint64","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":3}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":212,"format_str":"Uint64","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":4}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":300,"format_str":"Int32","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":302,"format_str":"Int32","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":2}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":304,"format_str":"Int32","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":3}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":306,"format_str":"Int32","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":4}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":308,"format_str":"Int32","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":310,"format_str":"Int32","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":2}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":312,"format_str":"Int32","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":3}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":400,"format_str":"Int64","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":404,"format_str":"Int64","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":2}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":408,"format_str":"Int64","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":3}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":412,"format_str":"Int64","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":4}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":500,"format_str":"Float","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":502,"format_str":"Float","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":2}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":504,"format_str":"Float","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":3}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":506,"format_str":"Float","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":4}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":508,"format_str":"Float","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":510,"format_str":"Float","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":2}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":512,"format_str":"Float","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":3}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":600,"format_str":"Double","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":604,"format_str":"Double","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":2}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":608,"format_str":"Double","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":3}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":612,"format_str":"Double","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":4}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":700,"format_str":"Bit","order_str":"BADC","type":"Bit","bacnet_object":4,"bacnet_property":85,"bacnet_id":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":701,"format_str":"Bit","order_str":"BADC","type":"Bit","bacnet_object":4,"bacnet_property":85,"bacnet_id":2}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":702,"format_str":"Bit","order_str":"BADC","type":"Bit","bacnet_object":4,"bacnet_property":85,"bacnet_id":3}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":703,"format_str":"Bit","order_str":"BADC","type":"Bit","bacnet_object":4,"bacnet_property":85,"bacnet_id":4}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":704,"format_str":"Bit","order_str":"BADC","type":"Bit","bacnet_object":4,"bacnet_property":85,"bacnet_id":5}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":705,"format_str":"Bit","order_str":"BADC","type":"Bit","bacnet_object":4,"bacnet_property":85,"bacnet_id":6}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":706,"format_str":"Bit","order_str":"BADC","type":"Bit","bacnet_object":4,"bacnet_property":85,"bacnet_id":7}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":800,"format_str":"Uint16","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":801,"format_str":"Uint16","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":2}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":803,"format_str":"Uint16","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":4}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":804,"format_str":"Uint16","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":805,"format_str":"Uint16","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":2}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":806,"format_str":"Uint16","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":3}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":802,"format_str":"Uint16","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":3}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":900,"format_str":"Int16","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":901,"format_str":"Int16","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":2}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":902,"format_str":"Int16","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":3}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":903,"format_str":"Int16","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":4}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":904,"format_str":"Int16","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":905,"format_str":"Int16","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":2}')
        self.do_webPOST('xt/serial/2/modbus/list {"address":906,"format_str":"Int16","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":3}')
        self.do_webGET('xt/serial/2/modbus/list')

    def do_readuint(self, args):
        print ("ABCD")
        self.do_read('positiveIntegerValue:11 presentValue')
        print ("BADC")
        self.do_read('positiveIntegerValue:12 presentValue')
        print ("CDAB")
        self.do_read('positiveIntegerValue:13 presentValue')
        print ("DCBA")
        self.do_read('positiveIntegerValue:14 presentValue')

    def do_readuint64(self, args):
        print ("ABCD")
        self.do_read('positiveIntegerValue:7 presentValue')
        print ("BADC")
        self.do_read('positiveIntegerValue:8 presentValue')
        print ("CDAB")
        self.do_read('positiveIntegerValue:9 presentValue')
        print ("DCBA")
        self.do_read('positiveIntegerValue:10 presentValue')

    def do_readfloat(self, args):
        print ("ABCD")
        self.do_read('analogValue:1 presentValue')
        print ("BADC")
        self.do_read('analogValue:2 presentValue')
        print ("CDAB")
        self.do_read('analogValue:3 presentValue')
        print ("DCBA")
        self.do_read('analogValue:4 presentValue')

    def do_writeuint64(self, args):
        try:
            value, format = args.split(" ")
            value = int(value)
            format = int(format)
            cmd = 'positiveIntegerValue:{} presentValue {}'.format(format + 7, value)
            print (cmd)
            self.do_write(cmd)
        except:
            print ("argument must be an int")

    def do_writeuint(self, args):
        try:
            value, format = args.split(" ")
            value = int(value)
            format = int(format)
            cmd = 'positiveIntegerValue:{} presentValue {}'.format(format + 11, value)
            print (cmd)
            self.do_write(cmd)
        except:
            print ("argument must be an int")

    def do_writefloat(self, args):
        try:
            value, format = args.split(" ")
            value = float(value)
            format = int(format)
            cmd = 'analogValue:{} presentValue {}'.format(format + 1, value)
            print (cmd)
            self.do_write(cmd)
        except:
            print ("argument must be a float")

    def do_test64(self, args):
        print (int("123456789abcdef1", 16))
        self.do_webPATCH('xt/serial/2/modbus/write {"device":1,"address":1,"type":"Register","value":"1234","value2":"5678","value3":"9abc","value4":"def1","format":0}')
        sleep(3)
        self.do_read('positiveIntegerValue:7 presentValue')
        self.do_read('positiveIntegerValue:8 presentValue')
        self.do_read('positiveIntegerValue:9 presentValue')
        self.do_read('positiveIntegerValue:10 presentValue')
        self.do_webPATCH('xt/serial/2/modbus/write {"device":1,"address":1,"type":"Register","value":"1234","value2":"5678","value3":"9abc","value4":"def1","format":1}')
        sleep(3)
        self.do_read('positiveIntegerValue:7 presentValue')
        self.do_read('positiveIntegerValue:8 presentValue')
        self.do_read('positiveIntegerValue:9 presentValue')
        self.do_read('positiveIntegerValue:10 presentValue')
        self.do_webPATCH('xt/serial/2/modbus/write {"device":1,"address":1,"type":"Register","value":"1234","value2":"5678","value3":"9abc","value4":"def1","format":2}')
        sleep(3)
        self.do_read('positiveIntegerValue:7 presentValue')
        self.do_read('positiveIntegerValue:8 presentValue')
        self.do_read('positiveIntegerValue:9 presentValue')
        self.do_read('positiveIntegerValue:10 presentValue')
        self.do_webPATCH('xt/serial/2/modbus/write {"device":1,"address":1,"type":"Register","value":"1234","value2":"5678","value3":"9abc","value4":"def1","format":3}')
        sleep(3)
        self.do_read('positiveIntegerValue:7 presentValue')
        self.do_read('positiveIntegerValue:8 presentValue')
        self.do_read('positiveIntegerValue:9 presentValue')
        self.do_read('positiveIntegerValue:10 presentValue')

    def do_test32(self, args):
        print (int("12345678", 16))
        self.do_webPATCH('xt/serial/2/modbus/write {"device":1,"address":1,"type":"Register","value":"1234","value2":"5678","format":0}')
        sleep(3)
        self.do_read('positiveIntegerValue:11 presentValue')
        self.do_read('positiveIntegerValue:12 presentValue')
        self.do_read('positiveIntegerValue:13 presentValue')
        self.do_read('positiveIntegerValue:14 presentValue')
        self.do_webPATCH('xt/serial/2/modbus/write {"device":1,"address":1,"type":"Register","value":"1234","value2":"5678","format":1}')
        sleep(3)
        self.do_read('positiveIntegerValue:11 presentValue')
        self.do_read('positiveIntegerValue:12 presentValue')
        self.do_read('positiveIntegerValue:13 presentValue')
        self.do_read('positiveIntegerValue:14 presentValue')
        self.do_webPATCH('xt/serial/2/modbus/write {"device":1,"address":1,"type":"Register","value":"1234","value2":"5678","format":2}')
        sleep(3)
        self.do_read('positiveIntegerValue:11 presentValue')
        self.do_read('positiveIntegerValue:12 presentValue')
        self.do_read('positiveIntegerValue:13 presentValue')
        self.do_read('positiveIntegerValue:14 presentValue')
        self.do_webPATCH('xt/serial/2/modbus/write {"device":1,"address":1,"type":"Register","value":"1234","value2":"5678","format":3}')
        sleep(3)
        self.do_read('positiveIntegerValue:11 presentValue')
        self.do_read('positiveIntegerValue:12 presentValue')
        self.do_read('positiveIntegerValue:13 presentValue')
        self.do_read('positiveIntegerValue:14 presentValue')

    def do_test32b(self, args):
        print (int("12345678", 16))
        self.do_write('positiveIntegerValue:11 presentValue {}'.format(int("12345678", 16)))
        sleep(3)
        self.do_read('positiveIntegerValue:11 presentValue')
        self.do_read('positiveIntegerValue:12 presentValue')
        self.do_read('positiveIntegerValue:13 presentValue')
        self.do_read('positiveIntegerValue:14 presentValue')
        self.do_write('positiveIntegerValue:12 presentValue {}'.format(int("12345678", 16)))
        sleep(3)
        self.do_read('positiveIntegerValue:11 presentValue')
        self.do_read('positiveIntegerValue:12 presentValue')
        self.do_read('positiveIntegerValue:13 presentValue')
        self.do_read('positiveIntegerValue:14 presentValue')
        self.do_write('positiveIntegerValue:13 presentValue {}'.format(int("12345678", 16)))
        sleep(3)
        self.do_read('positiveIntegerValue:11 presentValue')
        self.do_read('positiveIntegerValue:12 presentValue')
        self.do_read('positiveIntegerValue:13 presentValue')
        self.do_read('positiveIntegerValue:14 presentValue')
        self.do_write('positiveIntegerValue:14 presentValue {}'.format(int("12345678", 16)))
        sleep(3)
        self.do_read('positiveIntegerValue:11 presentValue')
        self.do_read('positiveIntegerValue:12 presentValue')
        self.do_read('positiveIntegerValue:13 presentValue')
        self.do_read('positiveIntegerValue:14 presentValue')

    def getAddress(self, addr):
        if(len(addr.split(".")) < 4):
            return RemoteStation(int(addr.split(':')[0]),int(addr.split(':')[1]))
        else:
            return Address(addr)

    def do_compare_file(self, args):
        """compare_file <file1> <file2> <file3>"""
        file1, file2 = args.split()
        f1 = open(file1, 'rb')
        f2 = open(file2, 'rb')
        f1c = f1.read()
        f2c = f2.read()
        if (f1.read() != f2.read()):
            print("files are different.")
            f3 = open(file3, 'wb+')
            fw.write(f2c)
            f3.close()
        f1.close()
        f2.close()



    def do_read_all_files(self,args):
        self.do_iut("192.168.1.100")
        self.do_mstpCapture("enable 1")
        for a in range(2,11):
            self.do_iut("2:{}".format(a))
            self.do_readfile("2 logic2-{}.bin".format(a))
        self.do_iut("192.168.1.100")
        self.do_mstpCapture("disable 1")
        webRestApi.xt_download(self.get_iut_address(),path,'mstpcap.pcap')

    def do_test_routing_fix(self, args):
        self.do_read_no_wait("101 1 analogValue:1 presentValue")
        self.do_read_no_wait("102 1 analogValue:1 presentValue")
        self.do_read_no_wait("103 1 analogValue:1 presentValue")
        self.do_read_no_wait("104 1 analogValue:1 presentValue")
        self.do_read_no_wait("105 1 analogValue:1 presentValue")

    def do_read_test2(self, args):
        device = 2
        for a in range(1,30):
            for deviceabc in range(2):
                for av in range(1,90):
                    self.do_read_no_wait("2 {} analogValue:{} {}".format(device, av, "presentValue"))

    def do_read_test(self, args):
        for a in ['presentValue', 'eventState', 'objectType', 'statusFlags', 'units', 'objectName', 'objectIdentifier']:
            for device in [3]:
                for av in range(1,90):
                    self.do_read_no_wait("2 {} analogValue:{} {}".format(device, av, a))

    def do_read_test1(self, args):
        for a in ['presentValue', 'eventState', 'objectType', 'statusFlags', 'units', 'objectName', 'objectIdentifier']:
            for device in [2,11]:
                for av in range(1,91):
                    self.do_read_no_wait("2 {} analogValue:{} {}".format(device, av, a))

    def do_setAO(self,args):
        """setAO <value>"""
        val = args.split()[0]
        self.do_write("analogOutput:1 presentValue {}".format(val))
        self.do_write("analogOutput:2 presentValue {}".format(val))
        self.do_write("analogOutput:3 presentValue {}".format(val))
        self.do_write("analogOutput:4 presentValue {}".format(val))

    def do_webPOST(self,args):
        """webPOST <path> <json_payload>"""
        path, json_payload = args.split()[:2]
        # print (json_payload)
        json_payload = eval(json_payload)
        # print (json_payload)
        webRestApi.xt_web_POST(self.get_iut_address(), path, json_payload)

    def do_webDELETE(self,args):
        """webDELETE <path> <json_payload>"""
        path, json_payload = args.split()[:2]
        # print (json_payload)
        json_payload = eval(json_payload)
        # print (json_payload)
        webRestApi.xt_web_DELETE(self.get_iut_address(), path, json_payload)

    def do_webPATCH(self,args):
        """webPATCH <path> <json_payload>"""
        path, json_payload = args.split()[:2]
        # print (json_payload)
        json_payload = eval(json_payload)
        # print (json_payload)
        webRestApi.xt_web_PATCH(self.get_iut_address(), path, json_payload)

    def do_webPATCH_file(self,args):
        """webPATCH_file <path> <filename>"""
        path, filename = args.split()[:2]
        webRestApi.xt_web_PATCH_file(self.get_iut_address(), path, filename)

    def do_webGET(self,args):
        """webGET <path>"""
        path = args.split()[0]
        webRestApi.xt_web_GET(self.get_iut_address(),path)

    def do_testTO(self, args):
        """testTO"""
        for i in range(1,11):
            self.do_write("binaryOutput:{} presentValue active".format(i))
            sleep(1)
        for i in range(1,11):
            self.do_write("binaryOutput:{} polarity reverse".format(i))
            sleep(0.5)
        for i in range(1,11):
            self.do_write("binaryOutput:{} presentValue inactive".format(i))
            sleep(0.5)
        for i in range(1,11):
            self.do_write("binaryOutput:{} polarity normal".format(i))
            sleep(0.5)

    def do_deleteMultiple(self, args):
        """deleteMultiple <type> <start> <end>  ex: deleteMultiple analogInput 0 20"""
        args = args.split()
        if len(args) == 3:
            type, start, end = args
            for x in range(int(start), int(end)):
                self.do_delete("{}:{}".format(type, x))

    def do_btl19(self, args):
        """btl19 tests read range"""
        print("Creating calendar:0")
        self.do_create("calendar:0")
        #Write dates to datelist
        self.do_raw("01040243050f0c0180000019173e0c760905030c760906040c760908060c76090a013f")
        #ReadRange (no range)
        print("ReadRange with no Range")
        self.do_raw("010400030a1a0c018000001917")
        #ReadRange
        print("ReadRange position 1 2")
        self.do_rr("calendar:0 dateList position 1 2")
        print("ReadRange position 1 10")
        self.do_rr("calendar:0 dateList position 1 10")
        print("ReadRange position 3 10")
        self.do_rr("calendar:0 dateList position 3 10")
        print("ReadRange position 3 -10")
        self.do_rr("calendar:0 dateList position 3 -10")
        print("ReadRange position 4 -10")
        self.do_rr("calendar:0 dateList position 4 -10")

        print("Creating notificationClass:0")
        self.do_create("notificationClass:0")
        print("Adding recipient")
        self.do_addRec("0")
        print("ReadRange position 1 2")
        self.do_rr("notificationClass:0 recipientList position 1 2")
        print("ReadRange with no Range")
        self.do_raw("010400030a1a0c03c000001966")

        print("Creating schedule:0")
        self.do_create("schedule:0")
        #readRange with no range.
        print("ReadRange with no Range")
        self.do_raw("010400030a1a0c044000401936")
        #readrange 1 - 10
        print("ReadRange position 1 10")
        self.do_rr("schedule:4 listOfObjectPropertyReferences position 1 10")



    def do_tl_test(self,args):
        """tl_test -- create TL:3 and enable"""
        self.do_create("trendLog:3")
        # set log device object property AV:0, present value
        self.do_raw("010400050e0f0c0500000319843e0c0080000019553c023fffff3f")
        self.do_write("trendLog:3 logInterval 100")
        self.do_rpm("trendLog:3 all")
        # write event enable 111
        self.do_raw("01040075050f0c0500000319233e8205e03f4910")
        self.do_read("trendLog:3 eventEnable")
        #write event_enable 110
        self.do_raw("01040075050f0c0500000319233e8205c03f4910")
        self.do_read("trendLog:3 eventEnable")
        #write event_enable 010
        self.do_raw("01040075050f0c0500000319233e8205403f4910")
        #write event_enable 101
        self.do_raw("01040075050f0c0500000319233e8205a03f4910")
        self.do_read("trendLog:3 eventEnable")
        self.do_write("trendLog:3 notificationClass 0")

    def do_eventNotificationTest(self, args):
        """eventNotificationTest - test routing of event notifications"""
        #stop and start mstp capture to start fresh.
        self.do_iut("192.168.1.200:47809")
        self.do_mstpCapture("disable 1")
        self.do_mstpCapture("enable 1")
        self.do_iut("192.168.1.100:47808")
        self.do_write("analogValue:0 presentValue 50")
        #webRestApi.xt_web_PATCH("192.168", path, json_payload)
        self.do_mstpCapture("disable 1")
        self.do_mstpCapture("enable 1")
        print ("Set recipient to DNET 0 MAC 15 (0x0f), set analogValue:0 presentValue to 90")
        self.do_btl22("0 15")
        sleep(0.5)
        self.do_write("analogValue:0 presentValue 90")
        sleep(0.5)
        print ("Set recipient to DNET 7(0x07) MAC 15 (0x0f), set analogValue:0 presentValue to 41")
        self.do_btl22("7 15")
        sleep(0.5)
        self.do_write("analogValue:0 presentValue 41")
        sleep(0.5)
        print ("Set recipient to DNET 10(0x0a) MAC 15 (0x0f), set analogValue:0 presentValue to 92")
        self.do_btl22("10 15")
        sleep(0.5)
        self.do_write("analogValue:0 presentValue 92")
        sleep(0.5)
        print ("Set recipient to DNET 0 MAC 192.168.1.100:47808, set analogValue:0 presentValue to 43")
        self.do_btl22("0 192.168.1.100:47808")
        sleep(0.5)
        self.do_write("analogValue:0 presentValue 43")
        sleep(0.5)
        print ("Set recipient to DNET 7(0x07) MAC 192.168.1.100:47808, set analogValue:0 presentValue to 94")
        self.do_btl22("7 192.168.1.100:47808")
        sleep(0.5)
        self.do_write("analogValue:0 presentValue 94")
        sleep(0.5)
        print ("Set recipient to DNET 10(0x0a) MAC 192.168.1.100:47808, set analogValue:0 presentValue to 45")
        self.do_btl22("10 192.168.1.100:47808")
        sleep(0.5)
        self.do_write("analogValue:0 presentValue 45")
        sleep(0.5)
        print ("Set recipient to DNET 1(0x01) MAC 15 (0x0f), set analogValue:0 presentValue to 96")
        self.do_btl22("1 15")
        sleep(0.5)
        self.do_write("analogValue:0 presentValue 96")
        sleep(0.5)
        print ("Set recipient to DNET 1 MAC 192.168.1.100:47808, set analogValue:0 presentValue to 47")
        self.do_btl22("1 192.168.1.100:47808")
        sleep(0.5)
        self.do_write("analogValue:0 presentValue 47")
        sleep(0.5)
        print ("end test")
        self.do_mstpCapture("disable 1")
        self.do_iut("192.168.1.200:47809")
        self.do_mstpCapture("disable 1")
        self.do_iut("192.168.1.100:47808")

    def do_eventNotificationTest2(self, args):
        """eventNotificationTest - test routing of event notifications"""
        #stop and start mstp capture to start fresh.
        self.do_iut("192.168.1.200")
        self.do_mstpCapture("disable 1")
        self.do_mstpCapture("enable 1")
        self.do_mstpCapture("disable 2")
        self.do_mstpCapture("enable 2")
        self.do_iut("192.168.1.200:47809")
        #self.do_iut("192.168.1.100:47808")
        self.do_write("analogValue:1 presentValue 50")
        #webRestApi.xt_web_PATCH("192.168", path, json_payload)
        #self.do_mstpCapture("disable 1")
        #self.do_mstpCapture("enable 1")
        print ("Set recipient to DNET 0 MAC 15 (0x0f), set analogValue:0 presentValue to 90")
        self.do_btl22("0 15")
        sleep(0.5)
        self.do_write("analogValue:1 presentValue 90")
        sleep(1)
        print ("Set recipient to DNET 2(0x02) MAC 15 (0x0f), set analogValue:0 presentValue to 41")
        self.do_btl22("2 15")
        sleep(1)
        self.do_write("analogValue:1 presentValue 41")
        sleep(1)
        print ("Set recipient to DNET 10(0x0a) MAC 15 (0x0f), set analogValue:0 presentValue to 92")
        self.do_btl22("10 15")
        sleep(1)
        self.do_write("analogValue:1 presentValue 92")
        sleep(1)
        print ("Set recipient to DNET 6(0x02) MAC 15 (0x0f), set analogValue:0 presentValue to 41")
        self.do_btl22("6 15")
        sleep(1)
        self.do_write("analogValue:1 presentValue 41.5")
        sleep(1)
        print ("Set recipient to DNET 1(0x0a) MAC 15 (0x0f), set analogValue:0 presentValue to 92")
        self.do_btl22("7 15")
        sleep(1)
        self.do_write("analogValue:1 presentValue 92.5")
        sleep(1)
        print ("Set recipient to DNET 0 MAC 192.168.1.4:47808, set analogValue:0 presentValue to 43")
        self.do_btl22("0 192.168.1.4:47808")
        sleep(1)
        self.do_write("analogValue:1 presentValue 43")
        sleep(1)
        print ("Set recipient to DNET 7(0x07) MAC 192.168.1.4:47808, set analogValue:0 presentValue to 94")
        self.do_btl22("7 192.168.1.4:47808")
        sleep(1)
        self.do_write("analogValue:1 presentValue 94")
        sleep(1)
        print ("Set recipient to DNET 10(0x0a) MAC 192.168.1.4:47808, set analogValue:0 presentValue to 45")
        self.do_btl22("10 192.168.1.4:47808")
        sleep(1)
        self.do_write("analogValue:1 presentValue 45")
        sleep(1)
        print ("Set recipient to DNET 2(0x01) MAC 15 (0x0f), set analogValue:0 presentValue to 96")
        self.do_btl22("2 15")
        sleep(1)
        self.do_write("analogValue:1 presentValue 96")
        sleep(1)
        print ("Set recipient to DNET 1 MAC 192.168.1.4:47808, set analogValue:0 presentValue to 47")
        self.do_btl22("1 192.168.1.4:47808")
        sleep(1)
        self.do_write("analogValue:1 presentValue 47")
        sleep(1)
        print ("Set recipient to 0xFFFF = BACNET broadcast, set analogValue:0 presentValue to 98")
        self.do_raw("010402434d0f0c03c0000019663e8201feb400000000b4173b3b631e22ffff601f2104108205e03f")
        sleep(1)
        self.do_write("analogValue:1 presentValue 98")
        sleep(1)
        print ("Set recipient to DNET 1 MAC '', set analogValue:0 presentValue to 49")
        self.do_raw("010402434d0f0c03c0000019663e8201feb400000000b4173b3b631e2101601f2104108205e03f")
        sleep(1)
        self.do_write("analogValue:1 presentValue 49")
        sleep(1)
        print ("Set recipient to DNET 2 MAC '', set analogValue:0 presentValue to 99.1")
        self.do_raw("010402434d0f0c03c0000019663e8201feb400000000b4173b3b631e2102601f2104108205e03f")
        sleep(1)
        self.do_write("analogValue:1 presentValue 99.1")
        sleep(1)
        print ("Set recipient to DNET 0 MAC '', set analogValue:0 presentValue to 50")
        self.do_raw("010402434d0f0c03c0000019663e8201feb400000000b4173b3b631e2100601f2104108205e03f")
        sleep(1)
        self.do_write("analogValue:1 presentValue 50")
        sleep(1)
        print ("Set recipient to DNET 6 MAC '', set analogValue:0 presentValue to 99.2")
        self.do_raw("010402434d0f0c03c0000019663e8201feb400000000b4173b3b631e2106601f2104108205e03f")
        sleep(1)
        self.do_write("analogValue:1 presentValue 99.2")
        sleep(1)
        print ("Set recipient to DNET 10 MAC '', set analogValue:0 presentValue to 51")
        self.do_raw("010402434d0f0c03c0000019663e8201feb400000000b4173b3b631e210a601f2104108205e03f")
        sleep(1)
        self.do_write("analogValue:1 presentValue 51")
        sleep(1)
        print ("end test")
        self.do_iut("192.168.1.200")
        self.do_mstpCapture("disable 1")
        self.do_mstpCapture("disable 2")
        self.do_iut("192.168.1.200:47809")


    def do_mstpCapture(self, args):
        """mstpCapture <enable | disable> <1 | 2>"""
        if len(args) == 0:
            self.do_help("mstpCapture")
        else:
            args = args.split()
            args.append("")
            if args[0] == "enable":
                enable = "True"
            else:
                enable = "False"
            if args[1] == '2':
                port = '2'
            else:
                port = '1'
            self.do_webPATCH('xt/serial/{}/mstp {}"capture_enable":{}{}'.format(port, "{", enable, "}"))

    

    def do_test_piv(self, args):
        self.do_raw("01040243140f0c0c00000119553e2501113f")
        sleep(0.2)
        self.do_read("positiveIntegerValue:1 presentValue")
        self.do_raw("01040243140f0c0c00000119553e250211223f")
        sleep(0.2)
        self.do_read("positiveIntegerValue:1 presentValue")
        self.do_raw("01040243140f0c0c00000119553e25031122333f")
        sleep(0.2)
        self.do_read("positiveIntegerValue:1 presentValue")
        self.do_raw("01040243140f0c0c00000119553e2504112233443f")
        sleep(0.2)
        self.do_read("positiveIntegerValue:1 presentValue")
        self.do_raw("01040243140f0c0c00000119553e250511223344553f")
        sleep(0.2)
        self.do_read("positiveIntegerValue:1 presentValue")
        self.do_raw("01040243140f0c0c00000119553e25061122334455663f")
        sleep(0.2)
        self.do_read("positiveIntegerValue:1 presentValue")
        self.do_raw("01040243140f0c0c00000119553e2507112233445566773f")
        sleep(0.2)
        self.do_read("positiveIntegerValue:1 presentValue")
        self.do_raw("01040243140f0c0c00000119553e250811223344556677883f")
        sleep(0.2)
        self.do_read("positiveIntegerValue:1 presentValue")

    def do_test_iv(self, args):
        self.do_raw("01040243140f0c0b40000119553e3501113f")
        sleep(0.2)
        self.do_read("integerValue:1 presentValue")
        self.do_raw("01040243140f0c0b40000119553e350211223f")
        sleep(0.2)
        self.do_read("integerValue:1 presentValue")
        self.do_raw("01040243140f0c0b40000119553e35031122333f")
        sleep(0.2)
        self.do_read("integerValue:1 presentValue")
        self.do_raw("01040243140f0c0b40000119553e3504112233443f")
        sleep(0.2)
        self.do_read("integerValue:1 presentValue")
        self.do_raw("01040243140f0c0b40000119553e350511223344553f")
        sleep(0.2)
        self.do_read("integerValue:1 presentValue")
        self.do_raw("01040243140f0c0b40000119553e35061122334455663f")
        sleep(0.2)
        self.do_read("integerValue:1 presentValue")
        self.do_raw("01040243140f0c0b40000119553e3507112233445566773f")
        sleep(0.2)
        self.do_read("integerValue:1 presentValue")
        self.do_raw("01040243140f0c0b40000119553e350811223344556677883f")
        sleep(0.2)
        self.do_read("integerValue:1 presentValue")

    def do_test_iv2(self, args):
        print ("send 0")
        self.do_raw("01040243140f0c0b40000119553e3501003f")
        sleep(0.2)
        self.do_read("integerValue:1 presentValue")
        print ("send -1")
        self.do_raw("01040243140f0c0b40000119553e3501FF3f")
        sleep(0.2)
        self.do_read("integerValue:1 presentValue")
        self.do_raw("01040243140f0c0b40000119553e350291223f")
        sleep(0.2)
        self.do_read("integerValue:1 presentValue")
        self.do_raw("01040243140f0c0b40000119553e35039122333f")
        sleep(0.2)
        self.do_read("integerValue:1 presentValue")
        self.do_raw("01040243140f0c0b40000119553e3504912233443f")
        sleep(0.2)
        self.do_read("integerValue:1 presentValue")
        self.do_raw("01040243140f0c0b40000119553e350591223344553f")
        sleep(0.2)
        self.do_read("integerValue:1 presentValue")
        self.do_raw("01040243140f0c0b40000119553e35069122334455663f")
        sleep(0.2)
        self.do_read("integerValue:1 presentValue")
        self.do_raw("01040243140f0c0b40000119553e3507912233445566773f")
        sleep(0.2)
        self.do_read("integerValue:1 presentValue")
        self.do_raw("01040243140f0c0b40000119553e350891223344556677883f")
        sleep(0.2)
        self.do_read("integerValue:1 presentValue")

    def do_continuousRead(self, args):
        for x in range(0,20):
            sleep(0.5)
            self.do_read("analogInput:1 presentValue")

    def do_test_lav(self, args):
        print( "send 0")
        self.do_raw("01040243140f0c0b80000119553e550800000000000000003f")
        sleep(0.2)
        self.do_read("largeAnalogValue:1 presentValue")
        print( "send 1")
        self.do_raw("01040243140f0c0b80000119553e55083ff00000000000003f")
        sleep(0.2)
        self.do_read("largeAnalogValue:1 presentValue")
        print ("send 1")
        self.do_raw("01040243140f0c0b80000119553e5508bff00000000000003f")
        sleep(0.2)
        self.do_read("largeAnalogValue:1 presentValue")
        print ("send 1.0000000000000002, the smallest number > 1")
        self.do_raw("01040243140f0c0b80000119553e55083ff00000000000013f")
        sleep(0.2)
        self.do_read("largeAnalogValue:1 presentValue")
        print ("send 1.0000000000000004")
        self.do_raw("01040243140f0c0b80000119553e55083ff00000000000023f")
        sleep(0.2)
        self.do_read("largeAnalogValue:1 presentValue")
        print ("send 2")
        self.do_raw("01040243140f0c0b80000119553e550840000000000000003f")
        sleep(0.2)
        self.do_read("largeAnalogValue:1 presentValue")


        print ("send 3")
        self.do_raw("01040243140f0c0b80000119553e550840080000000000003f")
        sleep(0.2)
        self.do_read("largeAnalogValue:1 presentValue")
        print ("send 4")
        self.do_raw("01040243140f0c0b80000119553e550840100000000000003f")
        sleep(0.2)
        self.do_read("largeAnalogValue:1 presentValue")


    def do_setupSchedule(self, args):
        """sets up a schedule for an integer object"""
        self.do_rpm("schedule:1 all")
        #set scheduleDefault to integer 4.
        self.do_write("schedule:1 scheduleDefault i:4")
        #setup a schedule
        self.do_raw("01040243020f0c04400001197b3e0eb4080000003108b40e00000000b411000000312a0f0eb4080000003108b40e00000000b411000000312a0f0eb4080000003108b40e00000000b411000000312a0f0eb4080000003108b40e00000000b411000000312a0f0eb4080000003108b40e00000000b411000000312a0f0eb4080000003108b40e00000000b411000000312a0f0eb4080000003108b40e00000000b411000000312a0f3f")
        #write to schedule:1, list of property references: integerValue:1, presentValue
        self.do_raw("01040243080f0c0440000119363e0c0b40000119553f")
        self.do_rpm("schedule:1 all")

    # example of running multiple other commands with one command in the console.
    def do_script(self, args):
        """script"""
        self.do_rpm("analogValue:9 all")
        self.do_write("analogValue:9 presentValue 50")
        self.do_write("analogValue:9 presentValue 90")
        self.do_alarmAck("")

    def do_btl20(self, args):
        print("Read binaryInput:0 outOfService")
        self.do_read("binaryInput:0 outOfService")
        print("Read binaryInput:0 polarity")
        self.do_read("binaryInput:0 polarity")
        print("Read binaryInput:0 presentValue")
        self.do_read("binaryInput:0 presentValue")
        print("Write binaryInput:0 polarity reverse")
        self.do_write("binaryInput:0 polarity reverse")
        print("Read binaryInput:0 polarity")
        self.do_read("binaryInput:0 polarity")
        print("Read binaryInput:0 presentValue")
        self.do_read("binaryInput:0 presentValue")

    def do_biConfig(self, args):
        """biConfig <instance> <"UI:xx" or "PI:xx"> [<delay_on> <delay_off>]"""
        args = args.split()
        while len(args) < 4:
            args.append(None)
        instance, link, delayOn, delayOff = args[:4]
        values = []
        if instance is not None:
            if link[0:2] == "UI" or link[0:2] == "ui":
                values.append([516,1])
                values.append([514,int(link[3:])])
            elif link[0:2] == "PI" or link[0:2] == "pi":
                values.append([516,2])
                values.append([515,int(link[3:])])
            else:
                values.append([516,0])
            if delayOn is not None:
                values.append([517,int(delayOn)])
            if delayOff is not None:
                values.append([518,int(delayOff)])
        for prop, val in values:
            if prop == 516:
                self.do_writeProprietary("binaryInput:{} {} {} Enumerated".format(instance,prop,val))
            else:
                self.do_writeProprietary("binaryInput:{} {} {} Unsigned".format(instance,prop,val))
        self.do_getBiConfig("binaryInput:{}".format(instance))

    def do_getBiConfig(self, args):
        """getBiConfig <obj_id>"""
        obj_id = ObjectIdentifier(args)
        request = ReadPropertyRequest(
            objectIdentifier = obj_id,
            propertyIdentifier = 516
            )
        request.pduDestination = Address(self.get_iut_address())

        # make an IOCB
        iocb = IOCB(request)
        this_application.request_io(iocb)
        iocb.wait()
        if iocb.ioResponse:
            apdu = iocb.ioResponse
            if not isinstance(apdu, ReadPropertyACK):
                print ("error")
            value = apdu.propertyValue.cast_out(Enumerated)
            print (value)
            if int(value) == 1:
                type = "UI"
                prop = 514
            elif int(value) == 2:
                type = "PI"
                prop = 515
            else:
                type = "none"
                prop = None
        if prop is not None:
            request = ReadPropertyRequest(
                objectIdentifier = obj_id,
                propertyIdentifier = prop
                )
            request.pduDestination = Address(self.get_iut_address())
            # make an IOCB
            iocb = IOCB(request)
            this_application.request_io(iocb)
            iocb.wait()
            if iocb.ioResponse:
                apdu = iocb.ioResponse
                if not isinstance(apdu, ReadPropertyACK):
                    print ("error")
                value = apdu.propertyValue.cast_out(Unsigned)
                print ("Link: {}:{}".format(type,value))
        self.do_rpm(args + " reliability")

    def do_aiConfig(self, args):
        """aiConfig <instance> <"UI:xx"> <type> [ <offset>]"""
        args = args.split()
        while len(args) < 4:
            args.append(None)
        instance, link, inputType, xtOffset = args[:4]
        values = []
        if instance is not None:
            if link[0:2] == "UI" or link[0:2] == "ui":
                values.append([514,int(link[3:])])
            else:
                values.append([516,0])
            if inputType is not None:
                values.append([513,int(inputType)])
            if xtOffset is not None:
                values.append([512,int(xtOffset)])
        for prop, val in values:
            if (prop == 516) or (prop == 513):
                self.do_writeProprietary("analogInput:{} {} {} Enumerated".format(instance,prop,val))
            elif prop == 512:
                self.do_writeProprietary("analogInput:{} {} {} Real".format(instance,prop,val))
            else:
                self.do_writeProprietary("analogInput:{} {} {} Unsigned".format(instance,prop,val))
        self.do_getAiConfig("analogInput:{}".format(instance))

    def do_getAiConfig(self, args):
        """getAiConfig <obj_id>"""
        ui_types = ["5V", "10V", "4-20mA", "internal NTC", "user NTC", "0-20mA", "pulse", "NTC 10K2", "NTC 3K", "NTC 20K", "DIGITAL", "PT"]
        ui_link = None
        ui_type = None
        xt_offset = None
        obj_id = ObjectIdentifier(args)
        request = ReadPropertyRequest(
            objectIdentifier = obj_id,
            propertyIdentifier = 514
            )
        request.pduDestination = Address(self.get_iut_address())

        # make an IOCB
        iocb = IOCB(request)
        this_application.request_io(iocb)
        iocb.wait()
        if iocb.ioResponse:
            apdu = iocb.ioResponse
            if not isinstance(apdu, ReadPropertyACK):
                print ("error")
            ui_link = apdu.propertyValue.cast_out(Unsigned)
        request = ReadPropertyRequest(
            objectIdentifier = obj_id,
            propertyIdentifier = 512
            )
        request.pduDestination = Address(self.get_iut_address())
        # make an IOCB
        iocb = IOCB(request)
        this_application.request_io(iocb)
        iocb.wait()
        if iocb.ioResponse:
            apdu = iocb.ioResponse
            if not isinstance(apdu, ReadPropertyACK):
                print ("error")
            xt_offset = apdu.propertyValue.cast_out(Real)
        request = ReadPropertyRequest(
            objectIdentifier = obj_id,
            propertyIdentifier = 513
            )
        request.pduDestination = Address(self.get_iut_address())
        # make an IOCB
        iocb = IOCB(request)
        this_application.request_io(iocb)
        iocb.wait()
        if iocb.ioResponse:
            apdu = iocb.ioResponse
            if not isinstance(apdu, ReadPropertyACK):
                print ("error")
            ui_type = apdu.propertyValue.cast_out(Enumerated)

        print ("Link: UI:{} {}:{}".format(ui_link,ui_types[ui_type],xt_offset))

        self.do_rpm(args + " reliability")

    def do_cpt(self, args):
        """cpt <vendor_id> <service number> [ <service_params> ]"""
        args = args.split()
        vendorId = None
        serviceNum = None
        serviceParamsA = False
        serviceParamsB = False
        if len(args) > 3:
            print ("more than three ..")
            vendorId, serviceNum, serviceParamsA, serviceParamsB = args[:4]
            print("{} {} {}".format(vendorId, serviceNum, serviceParamsA))
        if len(args) > 2:
            print ("more than two ..")
            vendorId, serviceNum, serviceParamsA = args[:3]
            print("{} {} {}".format(vendorId, serviceNum, serviceParamsA))
        elif len(args) == 2:
            vendorId, serviceNum = args[:2]
        if vendorId is not None:
            request = ConfirmedPrivateTransferRequest(
                vendorID = int(vendorId),
                serviceNumber = int(serviceNum)
                )
            # Element('serviceParameters', Any, 2, True)
            request.pduDestination = Address(self.get_iut_address())
            print("{} {} {}".format(vendorId, serviceNum, serviceParamsA))
            a = Any()
            a.cast_in(CharacterString(serviceParamsA))
            request.serviceParameters = a
            # b = Any()
            # b.cast_in(CharacterString(serviceParamsB))
            # request.serviceParameters = a + b
            #     for i in range(0,len(serviceParamsList) + 1):

            # if serviceParamsA:
            #     serviceParamsList = serviceParamsA.split(',')
            #     tempList = ListOf(OctetString)
            #     for i in range(0,len(serviceParamsList) + 1):
            #         serviceParamsList[i] = OctetString(serviceParamsList[i])
            #         tempList.append(tempList, serviceParamsList[i])
            #     serviceParamsA = Any()
            #     serviceParamsA.cast_in(tempList)
        # make an IOCB
        iocb = IOCB(request)
        this_application.request_io(iocb)
        iocb.wait()
        if iocb.ioResponse:
            apdu = iocb.ioResponse
            if not isinstance(apdu, ConfirmedPrivateTransferACK):
                print( "error")
            print(apdu.dict_contents())
            print(apdu.apdu_contents())
            try:
                print(apdu.resultBlock.dict_contents())
            except Exception as Error:
                print(Error)
            try:
                print(apdu.resultBlock[0])
            except Exception as Error:
                print(Error)
            try:
                print(apdu.resultBlock)
            except Exception as Error:
                print(Error)
            try:
                for x in apdu.resultBlock:
                    print(x)
            except Exception as Error:
                print(Error)
            try:
                print("cast out as TagList")
                tag_list = apdu.resultBlock.tagList
                for x in tag_list:
                    print("{}{}{}{}".format(x.tagClass,x.tagNumber,x.tagLVT,x.tagData))

            except Exception as Error:
                print(Error)
            try:
                xyz = apdu.resultBlock
                print(xyz.tagList)
                print(xyz.tagList.get_context(0).tagData)
                print(xyz.tagList.get_context(1).tagData)
                print(xyz.tagList.get_context(2).tagData)
                print(xyz.dict_contents())
            except Exception as Error:
                print(Error)
            try:
                print(apdu.resultBlock.tagList.debug_contents())
            except Exception as Error:
                print(Error)
            try:
                print(apdu.dict_contents())
            except Exception as Error:
                print(Error)
            try:
                value = apdu.resultBlock.cast_out(OctetString)
                print(value)
            except Exception as Error:
                print(Error)

    def do_alarmSetup(self, args):
        """alarmSetup <obj_id = av:0> <nc = 0>"""
        args = args.split()
        while len(args) < 2:
            args.append(0)
        obj_id, nc = args[:2]
        if obj_id == 0:
            obj_id = "analogValue:0"
        self.do_create(obj_id)
        self.do_create("notificationClass:{}".format(nc))
        self.do_write("{} lowLimit 20".format(obj_id))
        self.do_write("{} highLimit 80".format(obj_id))
        self.do_write("{} notificationClass {}".format(obj_id, nc))
        self.do_add4Rec("{}".format(nc))
        self.do_enableAlarms(obj_id)

    def do_whatisnetworknumber(self, args):
        if len(args) > 0:
            address = Address(args)
            this_application.nse.what_is_network_number(address=address)
        else:
            this_application.nse.what_is_network_number()

    def do_add4Rec(self, args):
        """addRec <NC Instance>  """
        args = args.split()
        obj_id = ObjectIdentifier("notificationClass:"+args[0]).value

        try:
            request = WritePropertyRequest(
                objectIdentifier=obj_id,
                propertyIdentifier="recipientList"
                )
            request.pduDestination = Address(self.get_iut_address())

            recipient = Destination(
                validDays = DaysOfWeek([1,1,1,1,1,1,1]),
                fromTime = Time("00:00:00.00"),
                toTime = Time("23:59:59.00"),
                recipient = Recipient(address = DeviceAddress(networkNumber = 0, macAddress = OctetString('\x09'))),
                processIdentifier = Unsigned(10009),
                issueConfirmedNotifications = Boolean(False),
                transitions = EventTransitionBits([1,1,1])
                )

            recipient4 = Destination(
                validDays = DaysOfWeek([1,1,1,1,1,1,1]),
                fromTime = Time("00:00:00.00"),
                toTime = Time("23:59:59.00"),
                recipient = Recipient(address = DeviceAddress(networkNumber = 7, macAddress = OctetString('\x09'))),
                #recipient = Recipient(device = ObjectIdentifier("device:979000")),
                processIdentifier = Unsigned(10001),
                issueConfirmedNotifications = Boolean(False),
                transitions = EventTransitionBits([1,1,1])
                )
            recipient3 = Destination(
                validDays = DaysOfWeek([1,1,1,1,1,1,1]),
                fromTime = Time("00:00:00.00"),
                toTime = Time("23:59:59.00"),
                recipient = Recipient(address = DeviceAddress(networkNumber = 1, macAddress = OctetString('\xc0\xa8\x01\x04\xba\xc0'))),
                processIdentifier = Unsigned(10006),
                issueConfirmedNotifications = Boolean(False),
                transitions = EventTransitionBits([1,1,1])
                )

            recipient2 = Destination(
                validDays = DaysOfWeek([1,1,1,1,1,1,1]),
                fromTime = Time("00:00:00.00"),
                toTime = Time("23:59:59.00"),
                recipient = Recipient(address = DeviceAddress(networkNumber = 0, macAddress = OctetString('\xc0\xa8\x01\x04\xba\xc0'))),
                processIdentifier = Unsigned(10003),
                issueConfirmedNotifications = Boolean(False),
                transitions = EventTransitionBits([1,1,1])
                )

            recipientList = DestinationList4()
            recipientList.destination1 = recipient
            recipientList.destination2 = recipient2
            recipientList.destination3 = recipient3
            recipientList.destination4 = recipient4


            # save the value
            request.propertyValue = Any()

            try:
                request.propertyValue.cast_in(recipientList)
            except Exception as error:
                TestConsoleCmd._exception("WriteProperty cast error: %r", error)

            # make an IOCB
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            # do something for success
            if iocb.ioResponse:
                # should be an ack
                if not isinstance(iocb.ioResponse, SimpleAckPDU):
                    if _debug: TestConsoleCmd._debug("    - not an ack")
                    return

                sys.stdout.write("ack\n")

            # do something for error/reject/abort
            if iocb.ioError:
                sys.stdout.write(str(iocb.ioError) + '\n')

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)

    def do_addRec(self, args):
        """addRec <NC Instance>  """
        args = args.split()
        obj_id = ObjectIdentifier("notificationClass:"+args[0]).value

        try:
            request = WritePropertyRequest(
                objectIdentifier=obj_id,
                propertyIdentifier="recipientList"
                )
            request.pduDestination = Address(self.get_iut_address())

            recipient = Destination(
                validDays = DaysOfWeek([1,1,1,1,1,1,1]),
                fromTime = Time("00:00:00.00"),
                toTime = Time("23:59:59.00"),
                recipient = Recipient(address = DeviceAddress(networkNumber = 7, macAddress = OctetString('\x0f'))),
                processIdentifier = Unsigned(10009),
                issueConfirmedNotifications = Boolean(False),
                transitions = EventTransitionBits([1,1,1])
                )

            recipient2 = Destination(
                validDays = DaysOfWeek([1,1,1,1,1,1,1]),
                fromTime = Time("00:00:00.00"),
                toTime = Time("23:59:59.00"),
                #recipient = Recipient(device = ObjectIdentifier("device:979001")),
                recipient = Recipient(address = DeviceAddress(networkNumber = 0, macAddress = OctetString('\xc0\xa8\x01\x04\xba\xc0'))),
                processIdentifier = Unsigned(10009),
                issueConfirmedNotifications = Boolean(False),
                transitions = EventTransitionBits([1,1,1])
                )

            recipientList = DestinationList()
            recipientList.destination1 = recipient
            recipientList.destination2 = recipient2


            # save the value
            request.propertyValue = Any()

            try:
                request.propertyValue.cast_in(recipientList)
            except Exception as error:
                TestConsoleCmd._exception("WriteProperty cast error: %r", error)

            # make an IOCB
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            # do something for success
            if iocb.ioResponse:
                # should be an ack
                if not isinstance(iocb.ioResponse, SimpleAckPDU):
                    if _debug: TestConsoleCmd._debug("    - not an ack")
                    return

                sys.stdout.write("ack\n")

            # do something for error/reject/abort
            if iocb.ioError:
                sys.stdout.write(str(iocb.ioError) + '\n')

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)

    def do_checkAlarms(self, args):
        """checkAlarms"""
        listOfObjects = ["accumulator",
            "analogInput",
            "analogOutput",
            "analogValue",
            "binaryInput",
            "binaryValue",
            "integerValue",
            #"largeIntegerValue",
            "positiveIntegerValue",
            "trendLog"]
        for i in range(0,2):
            for object in listOfObjects:
                print ("{}:{}".format(object, i))
                self.do_alarmAck("0 0 "+ "{}:{}".format(object, i))

    def Test(Self, args):
        """wpmTest.  sample wpm"""
        try:
            limitEnable = BitString([1,1])
            eventEnable = BitString([1,1,1])
            write_access_list = []
            properties_list = []

            eventValue = Any()
            eventValue.cast_in(eventEnable)
            a = PropertyValue(
                propertyIdentifier = PropertyIdentifier("eventEnable"),
                value = eventValue
                )
            limitValue = Any()
            limitValue.cast_in(limitEnable)
            b = PropertyValue(
                propertyIdentifier = PropertyIdentifier("limitEnable"),
                value = limitValue
                )
            eventDetection = Any()
            eventDetection.cast_in(Boolean("true"))
            c = PropertyValue(
                propertyIdentifier = PropertyIdentifier("eventDetectionEnable"),
                value = eventDetection
            )
            properties_list.append(a)
            properties_list.append(b)
            properties_list.append(c)
            writeAccessSpecList = WriteAccessSpecification(
                objectIdentifier = "analogOutput:1",
                listOfProperties = properties_list
            )
            write_access_list.append(writeAccessSpecList)
            writeAccessSpecList2 = WriteAccessSpecification(
                objectIdentifier = "analogOutput:2",
                listOfProperties = properties_list
            )
            write_access_list.append(writeAccessSpecList2)

            request = WritePropertyMultipleRequest(
                listOfWriteAccessSpecs=write_access_list
                )
            request.pduDestination = Address(self.get_iut_address())

            # make an IOCB
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            # do something for success
            if iocb.ioResponse:
                # should be an ack
                if not isinstance(iocb.ioResponse, SimpleAckPDU):
                    if _debug: TestConsoleCmd._debug("    - not an ack")
                    return

                sys.stdout.write("ack\n")

            # do something for error/reject/abort
            if iocb.ioError:
                sys.stdout.write(str(iocb.ioError) + '\n')

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)


    def do_enableAlarms(Self, args):
        """enableAlarms <obj_id> <eventEnable> <limitEnable>"""
        args = args.split()

        try:
            print (args[0])
            obj_id = ObjectIdentifier(args[0])
            eventEnable = [1,1,1]
            limitEnable = [1,1]
            if len(args) > 1:
                if len(args[1]) >=3:
                    for i in range(0,3):
                        if int(args[1][i]) == 0:
                            eventEnable[i] = 0
            if len(args) > 1:
                if len(args[2]) >=2:
                    for i in range(0,2):
                        if int(args[2][i]) == 0:
                            limitEnable[i] = 0
            limitEnable = BitString(limitEnable)
            eventEnable = BitString(eventEnable)
            write_access_list = []
            properties_list = []

            eventValue = Any()
            eventValue.cast_in(eventEnable)
            a = PropertyValue(
                propertyIdentifier = PropertyIdentifier("eventEnable"),
                value = eventValue
                )
            limitValue = Any()
            limitValue.cast_in(limitEnable)
            b = PropertyValue(
                propertyIdentifier = PropertyIdentifier("limitEnable"),
                value = limitValue
                )
            eventDetection = Any()
            eventDetection.cast_in(Boolean("true"))
            c = PropertyValue(
                propertyIdentifier = PropertyIdentifier("eventDetectionEnable"),
                value = eventDetection
            )
            properties_list.append(a)
            properties_list.append(b)
            properties_list.append(c)
            writeAccessSpecList = WriteAccessSpecification(
                objectIdentifier = obj_id,
                listOfProperties = properties_list
            )
            write_access_list.append(writeAccessSpecList)

            request = WritePropertyMultipleRequest(
                listOfWriteAccessSpecs=write_access_list
                )
            request.pduDestination = Address(self.get_iut_address())

            # make an IOCB
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            # do something for success
            if iocb.ioResponse:
                # should be an ack
                if not isinstance(iocb.ioResponse, SimpleAckPDU):
                    if _debug: TestConsoleCmd._debug("    - not an ack")
                    return

                sys.stdout.write("ack\n")

            # do something for error/reject/abort
            if iocb.ioError:
                sys.stdout.write(str(iocb.ioError) + '\n')

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)

    def do_rr(self, args):
        """rr <obj_id> <property> <type> <reference> <count>"""
        args = args.split()

        try:
            while len(args) < 5:
                args.append("")
            obj_id, prop, type, ref, count = args
            if type == "position":
                rangeData = RangeByPosition(
                    referenceIndex = Unsigned(int(ref)),
                    count = Integer(int(count))
                    )
                RRrange = Range(byPosition = rangeData)
            elif type == "sequence":
                rangeData = RangeBySequenceNumber(
                    referenceIndex = Unsigned(int(ref)),
                    count = Integer(int(count))
                    )
                RRrange = Range(bySequenceNumber = rangeData)
            elif type == "time":
                rangeData = RangeByTime(
                    referenceTime = DateTime(ref),
                    count = Integer(int(count))
                )
                RRrange = Range(byTime = rangeData)
            request = ReadRangeRequest(
                objectIdentifier = ObjectIdentifier(obj_id),
                propertyIdentifier = PropertyIdentifier(prop),
                range = RRrange
                )
            request.pduDestination = Address(self.get_iut_address())
            if _debug: TestConsoleCmd._debug("    - request: %r", request)
            # make an IOCB
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            # do something for success
            if iocb.ioResponse:
                apdu = iocb.ioResponse

            # do something for success
            if iocb.ioResponse:
                apdu = iocb.ioResponse
                if isinstance(iocb.ioResponse, SimpleAckPDU):
                    print("SimpleAck recieved")
                if isinstance(apdu, ReadRangeACK):
                    print("rrAck: {} {} items:{} ResultFlags:{}".format(
                        apdu.objectIdentifier,
                        apdu.propertyIdentifier,
                        apdu.itemCount,
                        apdu.resultFlags
                        ))
                    if int(apdu.itemCount) > 0:
                        datatype = get_datatype(apdu.objectIdentifier[0], apdu.propertyIdentifier)
                        if _debug: ReadRangeConsoleCmd._debug("    - datatype: %r", datatype)
                        if not datatype:
                            raise TypeError("unknown datatype")
                        # cast out the data into a list
                        value = apdu.itemData[0].cast_out(datatype)

                        # dump it out
                        for i, item in enumerate(value):
                            sys.stdout.write("[%d]\n" % (i,))
                            item.debug_contents(file=sys.stdout, indent=2)
                        sys.stdout.flush()

            # do something for error/reject/abort
            if iocb.ioError:
                sys.stdout.write(str(iocb.ioError) + '\n')

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)



    def do_readrecord(self, args):
        """readrecord <addr> <inst> <start> <count>"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_readrecord %r", args)

        try:
            addr, obj_inst, start_record, record_count = args

            obj_type = 'file'
            obj_inst = int(obj_inst)
            start_record = int(start_record)
            record_count = int(record_count)

            # build a request
            request = AtomicReadFileRequest(
                fileIdentifier=(obj_type, obj_inst),
                accessMethod=AtomicReadFileRequestAccessMethodChoice(
                    recordAccess=AtomicReadFileRequestAccessMethodChoiceRecordAccess(
                        fileStartRecord=start_record,
                        requestedRecordCount=record_count,
                        ),
                    ),
                )
            request.pduDestination = self.getAddress(addr)
            # if(len(addr.split(".")) < 4):
            #     request.pduDestination = RemoteStation(addr.split(':')[0],addr.split(':')[1])
            # else:
            #     request.pduDestination = Address(addr)
            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # make an IOCB
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            # do something for success
            if iocb.ioResponse:
                apdu = iocb.ioResponse

                # should be an ack
                if not isinstance(apdu, AtomicReadFileACK):
                    if _debug: TestConsoleCmd._debug("    - not an ack")
                    return

                # suck out the record data
                if apdu.accessMethod.recordAccess:
                    value = apdu.accessMethod.recordAccess.fileRecordData
                elif apdu.accessMethod.streamAccess:
                    value = apdu.accessMethod.streamAccess.fileData
                if _debug: TestConsoleCmd._debug("    - value: %r", value)

                sys.stdout.write(repr(value) + '\n')
                sys.stdout.flush()

            # do something for error/reject/abort
            if iocb.ioError:
                sys.stdout.write(str(iocb.ioError) + '\n')

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)

    def readstream(self, args):
        """readstream <addr> <inst> <start> <count>"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_readstream %r", args)
        value = None
        try:
            addr, obj_inst, start_position, octet_count = args

            obj_type = 'file'
            obj_inst = int(obj_inst)
            start_position = int(start_position)
            octet_count = int(octet_count)

            # build a request
            request = AtomicReadFileRequest(
                fileIdentifier=(obj_type, obj_inst),
                accessMethod=AtomicReadFileRequestAccessMethodChoice(
                    streamAccess=AtomicReadFileRequestAccessMethodChoiceStreamAccess(
                        fileStartPosition=start_position,
                        requestedOctetCount=octet_count,
                        ),
                    ),
                )
            request.pduDestination = Address(addr)
            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # make an IOCB
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            # do something for success
            if iocb.ioResponse:
                apdu = iocb.ioResponse

                # should be an ack
                if not isinstance(apdu, AtomicReadFileACK):
                    if _debug: TestConsoleCmd._debug("    - not an ack")
                    return

                # suck out the record data
                if apdu.accessMethod.recordAccess:
                    value = apdu.accessMethod.recordAccess.fileRecordData
                elif apdu.accessMethod.streamAccess:
                    value = apdu.accessMethod.streamAccess.fileData
                if _debug: TestConsoleCmd._debug("    - value: %r", value)

                sys.stdout.write(repr(value) + '\n')
                sys.stdout.flush()

            # do something for error/reject/abort
            if iocb.ioError:
                sys.stdout.write(str(iocb.ioError) + '\n')

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)
        return value

    def writerecord(self, object="file:1", start_record=1, data=["test1", "test2"]):
        addr = self.get_iut_address()
        try:
            record_count = len(data)
            record_data = [arg.encode('utf-8') for arg in data]

            # build a request
            request = AtomicWriteFileRequest(
                fileIdentifier=(object),
                accessMethod=AtomicWriteFileRequestAccessMethodChoice(
                    recordAccess=AtomicWriteFileRequestAccessMethodChoiceRecordAccess(
                        fileStartRecord=start_record,
                        recordCount=record_count,
                        fileRecordData=record_data,
                        ),
                    ),
                )
            request.pduDestination = Address(addr)
            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # make an IOCB
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            # do something for success
            if iocb.ioResponse:
                apdu = iocb.ioResponse

                # should be an ack
                if not isinstance(apdu, AtomicWriteFileACK):
                    if _debug: TestConsoleCmd._debug("    - not an ack")
                    return

                # suck out the record data
                if apdu.fileStartPosition is not None:
                    value = apdu.fileStartPosition
                elif apdu.fileStartRecord is not None:
                    value = apdu.fileStartRecord
                return value

            # do something for error/reject/abort
            if iocb.ioError:
                sys.stdout.write(str(iocb.ioError) + '\n')
                return iocb.ioError

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)
            return "exception: {}".format(error)

    def do_writerecord(self, args):
        """writerecord <addr> <inst> <start> <count> [ <data> ... ]"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_writerecord %r", args)

        try:
            addr, obj_inst, start_record, record_count = args[0:4]

            obj_type = 'file'
            obj_inst = int(obj_inst)
            start_record = int(start_record)
            record_count = int(record_count)
            record_data = [arg.encode('utf-8') for arg in list(args[4:])]

            # build a request
            request = AtomicWriteFileRequest(
                fileIdentifier=(obj_type, obj_inst),
                accessMethod=AtomicWriteFileRequestAccessMethodChoice(
                    recordAccess=AtomicWriteFileRequestAccessMethodChoiceRecordAccess(
                        fileStartRecord=start_record,
                        recordCount=record_count,
                        fileRecordData=record_data,
                        ),
                    ),
                )
            request.pduDestination = Address(addr)
            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # make an IOCB
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            # do something for success
            if iocb.ioResponse:
                apdu = iocb.ioResponse

                # should be an ack
                if not isinstance(apdu, AtomicWriteFileACK):
                    if _debug: TestConsoleCmd._debug("    - not an ack")
                    return

                # suck out the record data
                if apdu.fileStartPosition is not None:
                    value = apdu.fileStartPosition
                elif apdu.fileStartRecord is not None:
                    value = apdu.fileStartRecord
                TestConsoleCmd._debug("    - value: %r", value)

                sys.stdout.write(repr(value) + '\n')
                sys.stdout.flush()

            # do something for error/reject/abort
            if iocb.ioError:
                sys.stdout.write(str(iocb.ioError) + '\n')

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)

    def writestream(self, object="file:1", start_position=0, data="ThisIsTestData"):
        addr = self.get_iut_address()

        try:
            data = data.encode('utf-8')

            # build a request
            request = AtomicWriteFileRequest(
                fileIdentifier=(object),
                accessMethod=AtomicWriteFileRequestAccessMethodChoice(
                    streamAccess=AtomicWriteFileRequestAccessMethodChoiceStreamAccess(
                        fileStartPosition=start_position,
                        fileData=data,
                        ),
                    ),
                )
            request.pduDestination = Address(addr)
            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # make an IOCB
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            # do something for success
            if iocb.ioResponse:
                apdu = iocb.ioResponse

                # should be an ack
                if not isinstance(apdu, AtomicWriteFileACK):
                    if _debug: TestConsoleCmd._debug("    - not an ack")
                    return

                # suck out the record data
                if apdu.fileStartPosition is not None:
                    value = apdu.fileStartPosition
                elif apdu.fileStartRecord is not None:
                    value = apdu.fileStartRecord
                return value

            # do something for error/reject/abort
            if iocb.ioError:
                sys.stdout.write(str(iocb.ioError) + '\n')
                return iocb.ioError

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)
            return "exception: {}".format(error)

    def do_writestream(self, args):
        """writestream <addr> <inst> <start> <data>"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_writestream %r", args)

        try:
            addr, obj_inst, start_position, data = args

            obj_type = 'file'
            obj_inst = int(obj_inst)
            start_position = int(start_position)
            data = data.encode('utf-8')

            # build a request
            request = AtomicWriteFileRequest(
                fileIdentifier=(obj_type, obj_inst),
                accessMethod=AtomicWriteFileRequestAccessMethodChoice(
                    streamAccess=AtomicWriteFileRequestAccessMethodChoiceStreamAccess(
                        fileStartPosition=start_position,
                        fileData=data,
                        ),
                    ),
                )
            request.pduDestination = Address(addr)
            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # make an IOCB
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            # do something for success
            if iocb.ioResponse:
                apdu = iocb.ioResponse

                # should be an ack
                if not isinstance(apdu, AtomicWriteFileACK):
                    if _debug: TestConsoleCmd._debug("    - not an ack")
                    return

                # suck out the record data
                if apdu.fileStartPosition is not None:
                    value = apdu.fileStartPosition
                elif apdu.fileStartRecord is not None:
                    value = apdu.fileStartRecord
                TestConsoleCmd._debug("    - value: %r", value)

                sys.stdout.write(repr(value) + '\n')
                sys.stdout.flush()

            # do something for error/reject/abort
            if iocb.ioError:
                sys.stdout.write(str(iocb.ioError) + '\n')

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)

    def do_mycmd(self, args):
        """mycmd <arg1>"""
        args = args.split()
        try:
            argument = ''
            service = 0
            bval = 0
            if len(args) == 1:
                argument = args[0]
            elif len(args) == 2:
                argument, service = args
            elif len(args) == 3:
                argument, service, bval = args
            if (argument == 'a'):
                argument = x1_test1()
            if (argument == 'b'):
                argument = x1_test2()
            sys.stdout.write("my command, argument: " + argument + '\n')
            # build a request
            request = ConfirmedRequestPDU()
            request.pduDestination = Address(self.get_iut_address())
            request.apduService = int(float(service))
            if bval == '1':
                addHex(request,'09011d0e0031323361646674656368313231')
            if bval == '2':
                addHex(request,'09011d0e0031323361646674656368313233')

            # make an IOCB
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            # do something for success
            if iocb.ioResponse:
                apdu = iocb.ioResponse

                # should be an ack
                if isinstance(apdu, SimpleAckPDU):
                    apdu.debug_contents()
                    print ("service: {} invokeId:{}".format(apdu.apduService, apdu.apduInvokeID))

                # suck out the record data
                if apdu.accessMethod.recordAccess:
                    value = apdu.accessMethod.recordAccess.fileRecordData
                elif apdu.accessMethod.streamAccess:
                    value = apdu.accessMethod.streamAccess.fileData
                if _debug: TestConsoleCmd._debug("    - value: %r", value)

                sys.stdout.write(repr(value) + '\n')
                sys.stdout.flush()

            # do something for error/reject/abort
            if iocb.ioError:
                sys.stdout.write(str(iocb.ioError) + '\n')
                if iocb.ioError == 26:
                    print ("ok..")
                if str(iocb.ioError) == 'security: passwordFailure':
                    print ("by text..")
                print (iocb)
                print (iocb.ioError)
                apdu = iocb.ioResponse
        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)

    def do_create(self, args):
        """create <type>:<inst>"""
        print (args)
        try:
            request = CreateObjectRequest(
                objectSpecifier=CreateObjectRequestObjectSpecifier(objectIdentifier = ObjectIdentifier(args))
                )
            request.pduDestination = Address(self.get_iut_address())

            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            # do something for success
            if iocb.ioResponse:
                response = iocb.ioResponse
                apdu = iocb.ioResponse

                # should be an ack
                if isinstance(apdu, CreateObjectACK):
                    print ("CreateObjectACK - service: {} invokeId:{} Object:{}".format(apdu.apduService, apdu.apduInvokeID, apdu.objectIdentifier))
                    self.do_read("device:979201 databaseRevision")
            # do something for error/reject/abort
            if iocb.ioError:
                sys.stdout.write(str(iocb.ioError) + '\n')
                if iocb.ioError == 26:
                    print ("ok..")
                    if str(iocb.ioError) == 'security: passwordFailure':
                        print ("by text..")
                        print (iocb)
                        print (iocb.ioError)
                        apdu = iocb.ioResponse

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)

    def do_delete(self, args):
        """create <type>:<inst>"""
        print (args)
        try:
            request = DeleteObjectRequest(
                objectIdentifier = ObjectIdentifier(args)
                )
            request.pduDestination = Address(self.get_iut_address())

            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            # do something for success
            if iocb.ioResponse:
                response = iocb.ioResponse
                apdu = iocb.ioResponse

                # should be an ack
                if isinstance(apdu, SimpleAckPDU):
                    print( "Simple Ack, Object Deleted: {}".format(ObjectIdentifier(args).value))

            # do something for error/reject/abort
            if iocb.ioError:
                sys.stdout.write(str(iocb.ioError) + '\n')
                if iocb.ioError == 26:
                    print ("ok..")
                    if str(iocb.ioError) == 'security: passwordFailure':
                        print ("by text..")
                        print (iocb)
                        print( iocb.ioError)
                        apdu = iocb.ioResponse

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)


    def do_run(self, args):
        """run <arg1>"""
        args = args.split()
        try:
            argument = ''
            service = 0
            bval = 0
            if len(args) == 1:
                argument = args[0]
            elif len(args) == 2:
                argument, service = args
            elif len(args) == 3:
                argument, service, bval = args

            if (argument == 'a'):
                argument = x1_test1()
            if (argument == 'b'):
                argument = x1_test2()
            sys.stdout.write("my command, argument: " + argument + '\n')
            # build a request
            tests = get_tests(a = argument)

            for test in tests:
                if test.request:
                    # make an IOCB
                    iocb = IOCB(test.request)
                    if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

                    # give it to the application
                    this_application.request_io(iocb)

                    # wait for it to complete
                    iocb.wait()

                    # do something for success
                    if iocb.ioResponse:
                        test.response = iocb.ioResponse
                        apdu = iocb.ioResponse

                        # should be an ack
                        if isinstance(apdu, SimpleAckPDU):
                            print ("Simple Ack - service: {} invokeId:{}".format(apdu.apduService, apdu.apduInvokeID))

                        if isinstance(apdu, ComplexAckPDU):
                            print ("Complex Ack - service: {} invokeId:{}".format(apdu.apduService, apdu.apduInvokeID))


                    # suck out the record data
                    # if apdu.accessMethod.recordAccess:
                    #     value = apdu.accessMethod.recordAccess.fileRecordData
                    # elif apdu.accessMethod.streamAccess:
                    #     value = apdu.accessMethod.streamAccess.fileData
                    # if _debug: TestConsoleCmd._debug("    - value: %r", value)
                    #
                    # sys.stdout.write(repr(value) + '\n')
                    # sys.stdout.flush()

                    # do something for error/reject/abort
                    if iocb.ioError:
                        sys.stdout.write(str(iocb.ioError) + '\n')
                    #     if iocb.ioError == 26:
                    #         print ("ok..")
                    #         if str(iocb.ioError) == 'security: passwordFailure':
                    #             print ("by text..")
                    #             print (iocb)
                    #             print (iocb.ioError)
                    #             apdu = iocb.ioResponse
        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)

    def do_btl07(self, args):
        """btl07"""
        print ("btl07 testing..")




    def raw_request(self, args):
        args = args.split()
        service = 12 #Read Property
        confirmed = True
        address = self.get_iut_address()
        hex = args[0]
        request = None
        if len(args) >= 4:
            service = args[3]
        if len(args) >= 3:
            confirmed = True and args[2]
        if len(args) >= 2:
            if len(args[1]) > 2:
                address = args[1]
        if len(args) == 1:
            address = self.get_iut_address()
            if hex[3] == '4':
                confirmed = True
                service = int(hex[10:12],16)
                hex = hex[12:]
            elif hex[3] == '0':
                confirmed = False
                service = int(hex[6:8],16)
                hex = hex[8:]
        try:
            if confirmed:
                request = ConfirmedRequestPDU()
                request.apduService = service
                request.pduDestination = Address(address)
                addHex(request, hex)
            else:
                request = UnconfirmedRequestPDU()
                request.apduService = service
                request.pduDestination = Address(address)
                addHex(request, hex)
            # make an IOCB
        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)
        return request

    def do_raw(self, args):
        """raw <bytes> address [confirmed] [service]"""
        args = args.split()
        service = 12 #Read Property
        confirmed = True
        address = self.get_iut_address()
        hex = args[0]
        if len(args) >= 4:
            service = args[3]
        if len(args) >= 3:
            confirmed = True and args[2]
        if len(args) >= 2:
            if len(args[1]) > 2:
                address = args[1]
        if len(args) == 1:
            address = self.get_iut_address()
            if hex[3] == '4':
                confirmed = True
                service = int(hex[10:12],16)
                hex = hex[12:]
            elif hex[3] == '0':
                confirmed = False
                service = int(hex[6:8],16)
                hex = hex[8:]
        try:
            if confirmed:
                request = ConfirmedRequestPDU()
                request.apduService = service
                request.pduDestination = Address(address)
                addHex(request, hex)
                print(request.dict_contents())
            else:
                request = UnconfirmedRequestPDU()
                request.apduService = service
                request.pduDestination = Address(address)
                addHex(request, hex)
                print(request.dict_contents())
            # make an IOCB
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            # do something for success
            if iocb.ioResponse:
                apdu = iocb.ioResponse
                if isinstance(iocb.ioResponse, SimpleAckPDU):
                    print("SimpleAck recieved")
                elif isinstance(iocb.ioResponse, ComplexAckPDU):
                    print("ComplexAck received")
                print(apdu.dict_contents())

            # do something for error/reject/abort
            if iocb.ioError:
                sys.stdout.write(str(iocb.ioError) + '\n')

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)

    def do_raw_check(self, args):
        """raw <bytes>"""
        args = args.split()
        hex = args[0]
        try:
            if hex[3] == '4':
                request = ConfirmedRequestPDU()
                request.apduService = int(hex[10:12],16)
                request.pduDestination = Address(self.get_iut_address())
                addHex(request, hex[12:])
            elif hex[3] == '0':
                request = UnconfirmedRequestPDU()
                request.apduService = int(hex[6:8],16)
                request.pduDestination = Address(self.get_iut_address())
                addHex(request, hex[8:])
            # make an IOCB
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            # do something for success
            if iocb.ioResponse:
                apdu = iocb.ioResponse
                print(apdu)
                print(apdu.dict_contents())
                if isinstance(iocb.ioResponse, SimpleAckPDU):
                    print("SimpleAck recieved")
                elif isinstance(iocb.ioResponse, ComplexAckPDU):
                    print("ComplexACK received")

            # do something for error/reject/abort
            if iocb.ioError:
                sys.stdout.write(str(iocb.ioError) + '\n')

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)

    def do_read_no_wait(self, args):
        """read <network> <mac> <objid> <prop>"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_read %r", args)

        try:
            network, mac, obj_id, prop_id = args[:4]
            obj_id = ObjectIdentifier(obj_id).value

            datatype = get_datatype(obj_id[0], prop_id)
            if not datatype:
                raise ValueError("invalid property for object type")

            # build a request
            request = ReadPropertyRequest(
                objectIdentifier=obj_id,
                propertyIdentifier=prop_id,
                )
            # request.pduDestination = RemoteStation(int(network), int(mac))
            request.pduDestination = Address("{}:{}".format(network,mac))

            # if len(args) == 4:
            #     request.propertyArrayIndex = int(args[3])
            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # make an IOCB
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)
            iocb.add_callback(self.complete_request)

            # give it to the application
            this_application.request_io(iocb)

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)

    def complete_request(self, iocb):
        if _debug: PrairieDog._debug("complete_request %r", iocb)
        print("got response..")
        print(iocb)
        print(iocb.ioResponse)
        # now we are not busy
        self.is_busy = False

        # do something for success
        if iocb.ioResponse:
            printf ('response...' + ioResponse)
            return
            apdu = iocb.ioResponse

            # should be an ack
            if  isinstance(apdu, ReadPropertyACK):
                print("Read PropertyAck recieved")
                # if _debug: ReadPropertyMultipleConsoleCmd._debug("    - not an ack")
                # return

            # if not isinstance(apdu, ReadPropertyMultipleACK):
            #     if _debug: ReadPropertyMultipleConsoleCmd._debug("    - not an ack")
            #     print("Not a ReadPropertyMultipleACK")
            #     return

            # loop through the results
            for result in apdu.listOfReadAccessResults:
                # here is the object identifier
                objectIdentifier = result.objectIdentifier
                if _debug: ReadPropertyMultipleConsoleCmd._debug("    - objectIdentifier: %r", objectIdentifier)

                # now come the property values per object
                for element in result.listOfResults:
                    # get the property and array index
                    propertyIdentifier = element.propertyIdentifier
                    if _debug: ReadPropertyMultipleConsoleCmd._debug("    - propertyIdentifier: %r", propertyIdentifier)
                    propertyArrayIndex = element.propertyArrayIndex
                    if _debug: ReadPropertyMultipleConsoleCmd._debug("    - propertyArrayIndex: %r", propertyArrayIndex)

                    # here is the read result
                    readResult = element.readResult

                    sys.stdout.write(str(propertyIdentifier))
                    if propertyArrayIndex is not None:
                        sys.stdout.write("[" + str(propertyArrayIndex) + "]")

                    # check for an error
                    if readResult.propertyAccessError is not None:
                        sys.stdout.write(" ! " + str(readResult.propertyAccessError) + '\n')

                    else:
                        # here is the value
                        propertyValue = readResult.propertyValue

                        # find the datatype
                        datatype = get_datatype(objectIdentifier[0], propertyIdentifier)
                        if _debug: ReadPropertyMultipleConsoleCmd._debug("    - datatype: %r", datatype)
                        if not datatype:
                            value = '?'
                        else:
                            # special case for array parts, others are managed by cast_out
                            if issubclass(datatype, Array) and (propertyArrayIndex is not None):
                                if propertyArrayIndex == 0:
                                    value = propertyValue.cast_out(Unsigned)
                                else:
                                    value = propertyValue.cast_out(datatype.subtype)
                            else:
                                value = propertyValue.cast_out(datatype)
                            if _debug: ReadPropertyMultipleConsoleCmd._debug("    - value: %r", value)

                        sys.stdout.write(" = " + str(value) + '\n')
                    sys.stdout.flush()
        else:
            print( "else...")
        # do something for error/reject/abort
        if iocb.ioError:
            sys.stdout.write(str(iocb.ioError) + '\n')

        deferred(self.next_request)

    def do_read(self, args):
        """read <objid> <prop> [ <indx> ]"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_read %r", args)

        try:
            obj_id, prop_id = args[:2]
            obj_id = ObjectIdentifier(obj_id).value

            datatype = get_datatype(obj_id[0], prop_id)
            if not datatype:
                prop_id = int(prop_id)
                # raise ValueError("invalid property for object type")

            # build a request
            request = ReadPropertyRequest(
                objectIdentifier=obj_id,
                propertyIdentifier=prop_id,
                )
            request.pduDestination = Address(self.get_iut_address())

            if len(args) == 4:
                request.propertyArrayIndex = int(args[3])
            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # make an IOCB
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            # do something for success
            if iocb.ioResponse:
                apdu = iocb.ioResponse

                # should be an ack
                if not isinstance(apdu, ReadPropertyACK):
                    if _debug: TestConsoleCmd._debug("    - not an ack")
                    return

                # find the datatype
                datatype = get_datatype(apdu.objectIdentifier[0], apdu.propertyIdentifier)
                if _debug: TestConsoleCmd._debug("    - datatype: %r", datatype)
                if not datatype:
                    raise TypeError("unknown datatype")

                # special case for array parts, others are managed by cast_out
                if issubclass(datatype, Array) and (apdu.propertyArrayIndex is not None):
                    if apdu.propertyArrayIndex == 0:
                        value = apdu.propertyValue.cast_out(Unsigned)
                    else:
                        value = apdu.propertyValue.cast_out(datatype.subtype)
                else:
                    value = apdu.propertyValue.cast_out(datatype)
                if _debug: TestConsoleCmd._debug("    - value: %r", value)

                sys.stdout.write(str(value) + '\n')
                if hasattr(value, 'debug_contents'):
                    value.debug_contents(file=sys.stdout)
                sys.stdout.flush()

            # do something for error/reject/abort
            if iocb.ioError:
                sys.stdout.write(str(iocb.ioError) + '\n')

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)

    def read_no_wait(self, args):
        """read <objid> <prop> [ <indx> ]"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_read %r", args)
        value = "none"
        try:
            obj_id, prop_id = args[:2]
            obj_id = ObjectIdentifier(obj_id).value
            datatype = get_datatype(obj_id[0], prop_id)
            # if not datatype:
            #     raise ValueError("invalid property for object type")

            # build a request
            request = ReadPropertyRequest(
                objectIdentifier=obj_id,
                propertyIdentifier=prop_id,
                )
            request.pduDestination = Address(self.get_iut_address())

            if len(args) == 4:
                request.propertyArrayIndex = int(args[3])
            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # make an IOCB
            iocb = IOCB(request)
            iocb.set_timeout(1)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)
        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)
        return value

    def read_value(self, args):
        """read <objid> <prop> [ <indx> ]"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_read %r", args)
        value = "none"
        try:
            obj_id, prop_id = args[:2]
            obj_id = ObjectIdentifier(obj_id).value
            datatype = get_datatype(obj_id[0], prop_id)
            formatted_output = f"BACnet Id: {obj_id[1]}" #obj_id[1] is the number of which BACnet
            print(formatted_output)
            # if not datatype:
            #     raise ValueError("invalid property for object type")

            # build a request
            request = ReadPropertyRequest(
                objectIdentifier=obj_id,
                propertyIdentifier=prop_id,
                )
            request.pduDestination = Address(self.get_iut_address())
            if len(args) == 3:
                request.propertyArrayIndex = int(args[2])
            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # make an IOCB
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            # do something for success
            if iocb.ioResponse:
                apdu = iocb.ioResponse

                # should be an ack
                if not isinstance(apdu, ReadPropertyACK):
                    if _debug: TestConsoleCmd._debug("    - not an ack")
                    return

                # find the datatype
                datatype = get_datatype(apdu.objectIdentifier[0], apdu.propertyIdentifier)
                if _debug: TestConsoleCmd._debug("    - datatype: %r", datatype)
                # if not datatype:
                #     raise TypeError("unknown datatype")

                # special case for array parts, others are managed by cast_out
                if issubclass(datatype, Array) and (apdu.propertyArrayIndex is not None):
                    if apdu.propertyArrayIndex == 0:
                        value = apdu.propertyValue.cast_out(Unsigned)
                    else:
                        value = apdu.propertyValue.cast_out(datatype.subtype)
                else:
                    value = apdu.propertyValue.cast_out(datatype)
                if _debug: TestConsoleCmd._debug("    - value: %r", value)

                # sys.stdout.write(str(value) + '\n')
                # if hasattr(value, 'debug_contents'):
                    # value.debug_contents(file=sys.stdout)
                # sys.stdout.flush()

            # do something for error/reject/abort
            if iocb.ioError:
                value = iocb.ioError.dict_contents()
                # sys.stdout.write(str(iocb.ioError) + '\n')

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)
        return value
    
    def read_object_data(self):
        object_list = self.read_object_list_short()
        output_data_list = []
        for object_item in object_list:
            present_value = self.read_value("{}:{} presentValue".format(object_item[0], object_item[1]))
            if isinstance(present_value, (int, float, str)):
                output_data_list.append(["{} {}".format(object_item[0], object_item[1]), present_value])
        print(output_data_list)
        ##
        # num_columns = 15
        # reshaped_list = [output_data_list[i:i+num_columns] for i in range(0, len(output_data_list), num_columns)]

        # # Pad the last chunk with empty strings if needed
        # last_chunk_length = len(reshaped_list[-1])
        # if last_chunk_length < num_columns:
        #     reshaped_list[-1].extend([''] * (num_columns - last_chunk_length))

        # try:
        #     # Convert tuples to strings to remove brackets and single quotes
        #     reshaped_list = [[f"{item[0]} {item[1]}: {item[2]}" for item in chunk] for chunk in reshaped_list]

        #     # Pad the strings so that they have the same length
        #     max_length = max(len(item) for chunk in reshaped_list for item in chunk)
        #     reshaped_list = [[item.ljust(max_length) for item in chunk] for chunk in reshaped_list]

        #     # Print the table using tabulate
        #     headers = ['Object Type & ID'] * num_columns
        #     print(tabulate(reshaped_list, headers=headers, tablefmt='orgtbl'))
        # except IndexError as e:
        #     print("IndexError occurred:", e)
        #     print("Length of reshaped list:", len(reshaped_list))
        ##
        headers = ["Object Type & ID", "Present Value"]
        print(tabulate(output_data_list, headers=headers, tablefmt="grid"))
        ##
        # for item in output_data_list:
        #     print("-- {} {} = {}".format(item[0][0], item[0][1], item[1]))
        
        return output_data_list
    
    def read_object_list_short(self):
        objectlist=[]
        buffer = self.read_value("device:979000 objectList 0")
        for i in range(1,buffer+1):
            objectlist.append(self.read_value("device:979000 objectList {}".format(i)))
        return objectlist
    
    def read_object_data_no_table(self):
        object_list = self.read_object_list_short()
        output_data_list = []
        for object_item in object_list:
            present_value = self.read_value("{}:{} presentValue".format(object_item[0], object_item[1]))
            if isinstance(present_value, (int, float, str)):
                output_data_list.append(["{} {}".format(object_item[0], object_item[1]), present_value])
        return output_data_list
    
    
    
    def read_property_list(self, obj_id):
        objectlist=[]
        buffer = self.read_value("{} propertyList 0".format(obj_id))
        for i in range(1,buffer+1):
            objectlist.append(self.read_value("{} propertyList {}".format(obj_id, i)))
        return objectlist

    def read_object_list(self):
        objectlist = []
        buffer = self.read_value("device:979000 objectList 0")
        for i in range(1, buffer + 1):
            read_object = self.read_value("device:979000 objectList {}".format(i))
            objectlist.append(read_object)
        
        filtered_list = []
        for item in objectlist:
            if isinstance(item, tuple) and not (item[1] <= 2 and item[0] in ('loop', 'file', 'program', 'networkPort', 'device')):
                filtered_list.append(item)
    
        #print(tabulate(filtered_list, headers=['Bacnet Type', 'Num'], tablefmt='orgtbl'))
        # # Reshape the filtered list to create new columns
        # num_columns = 3  # Change this to the desired number of columns
        # reshaped_list = [filtered_list[i:i+num_columns] for i in range(0, len(filtered_list), num_columns)]
    
        # # Print each column separately
        # for column in zip(*reshaped_list):
        #     print(tabulate(column, headers=['BACnet Type', 'Num'], tablefmt='orgtbl'))
        #     print()  # Add an empty line between columns
        
        # # Reshape the filtered list to create new rows and columns
        # num_columns = 30  # Change this to the desired number of columns
        # #num_rows = -(-len(filtered_list) // num_columns)  # Round up division
        # #reshaped_list = [filtered_list[i*num_rows:(i+1)*num_rows] for i in range(num_columns)]
        # reshaped_list = [filtered_list[i:i+num_columns] for i in range(0, len(filtered_list), num_columns)]
    
        # # Transpose the reshaped list to have rows as columns
        # transposed_list = list(map(list, zip(*reshaped_list)))

        # # Convert tuples to strings , To remove bracket and single qoute for List data
        # for row in transposed_list:
        #     for i, item in enumerate(row):
        #         row[i] = f"{item[0]} {item[1]}"
    
        # Print the table using tabulate
        print(" ")
        print("Total objects before filtering:", len(objectlist))
        print("Total objects after filtering:", len(filtered_list))
        print(tabulate(filtered_list, headers=['BACnet Type', 'ID'], tablefmt='grid'))
    
        return filtered_list

    def read_enumerated(self, obj_id, prop_id):
        return self.read_type(Enumerated, obj_id, prop_id)

    def read_unsigned(self, obj_id, prop_id):
        return self.read_type(Unsigned, obj_id, prop_id)

    def read_type(self, type, obj_id, prop_id):
        """read <objid> <prop> [ <indx> ]"""
        if _debug: TestConsoleCmd._debug("do_read %r", args)
        value = "none"
        try:
            obj_id = ObjectIdentifier(obj_id).value

            # if not datatype:
            #     raise ValueError("invalid property for object type")

            # build a request
            request = ReadPropertyRequest(
                objectIdentifier=obj_id,
                propertyIdentifier=prop_id,
                )
            request.pduDestination = Address(self.get_iut_address())

            # make an IOCB
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            # do something for success
            if iocb.ioResponse:
                apdu = iocb.ioResponse

                # should be an ack
                if not isinstance(apdu, ReadPropertyACK):
                    if _debug: TestConsoleCmd._debug("    - not an ack")
                    return
                value = apdu.propertyValue.cast_out(type)
                if _debug: TestConsoleCmd._debug("    - value: %r", value)
            # do something for error/reject/abort
            if iocb.ioError:
                value = "error"
                # sys.stdout.write(str(iocb.ioError) + '\n')

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)
            return "error"
        return value

    def do_alarmAck(self, args):
        """alarmAck <time> <type> <objId>"""
        apdu = lastEventNotification
        printEventNotification(apdu)
        bInvalidTime = False
        InvalidType = False
        args = args.split()
        if len(args) >= 1:
            if args[0] != '0':
                bInvalidTime = True
        if len(args) >= 2:
            InvalidType = int(args[1]) + 1
        print ("AlarmAck b:{} type:{}".format(
            bInvalidTime,
            InvalidType - 1))
        request =  AcknowledgeAlarmRequest(
            acknowledgingProcessIdentifier = 1,
            eventObjectIdentifier = apdu.eventObjectIdentifier,
            eventStateAcknowledged = apdu.toState,
            timeStamp = copy.deepcopy(apdu.timeStamp),
            acknowledgmentSource = "me",
            timeOfAcknowledgment = copy.deepcopy(apdu.timeStamp)
            )
        request.pduDestination = Address(self.get_iut_address())
        if bInvalidTime:
            time = request.timeOfAcknowledgment.dateTime.time
            print (request.timeOfAcknowledgment)
            print (request.timeOfAcknowledgment.dateTime.time)
            print (request.timeOfAcknowledgment.dateTime.date)
            print (request.timeStamp)
            print (request.timeStamp.dateTime.time)
            print (request.timeStamp.dateTime.date)
            #request.timeOfAcknowledgment.dateTime.time = Time((time[0] - 1, time[1], time[2], time[3]))
            request.timeStamp.dateTime.time = Time((time[0] - 1, time[1], time[2], time[3]))
            print (request.timeOfAcknowledgment)
            print (request.timeOfAcknowledgment.dateTime.time)
            print (request.timeOfAcknowledgment.dateTime.date)
            print (request.timeStamp)
            print (request.timeStamp.dateTime.time)
            print (request.timeStamp.dateTime.date)
        if InvalidType:
            request.eventStateAcknowledged = InvalidType - 1
        if len(args) > 2:
            request.eventObjectIdentifier = ObjectIdentifier(args[2]).value
        # make an IOCB
        iocb = IOCB(request)
        if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

        # give it to the application
        this_application.request_io(iocb)

    def do_writeProprietary(self, args):
        """writeProprietary <obj_id> <prop> <value> <type>"""
        args = args.split()
        obj_id, prop, value, type = args
        request = WritePropertyRequest(
            objectIdentifier= ObjectIdentifier(obj_id),
            propertyIdentifier=int(prop)
            )
        request.pduDestination = Address(self.get_iut_address())
        request.propertyValue = Any()
        if type == "Unsigned":
            value = Unsigned(int(value))
        elif type == "Enumerated":
            value = Enumerated(int(value))
        elif type == "Real":
            value = Enumerated(float(value))
        try:
            request.propertyValue.cast_in(value)
        except Exception as error:
            TestConsoleCmd._exception("WriteProperty cast error: %r", error)
        try:
            indx = None
            # optional array index
            if indx is not None:
                request.propertyArrayIndex = indx
            priority = None
            # optional priority
            if priority is not None:
                request.priority = priority

            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # make an IOCB
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            # do something for success
            if iocb.ioResponse:
                # should be an ack
                if not isinstance(iocb.ioResponse, SimpleAckPDU):
                    if _debug: TestConsoleCmd._debug("    - not an ack")
                    return

                sys.stdout.write("ack\n")

            # do something for error/reject/abort
            if iocb.ioError:
                sys.stdout.write(str(iocb.ioError) + '\n')
        except Exception as error:
            TestConsoleCmd._exception("WriteProperty cast error: %r", error)

    def do_write_objectpropertyreference(self, args):
        """write_objectpropertyreference <type>:<inst> <cv/mv> <type>:<inst>,<prop>"""
        args = args.split()
        TestConsoleCmd._debug("do_write_setpointreference %r", args)

        try:
            obj_id, prop_id, value = args[:3]
            if prop_id == 'cv':
                prop_id = 'controlledVariableReference'
            if prop_id == 'mv':
                prop_id = 'manipulatedVariableReference'

            obj_id = ObjectIdentifier(obj_id).value


            indx = None
            if len(args) >= 4:
                if args[3] != "-":
                    indx = int(args[3])
            if _debug: TestConsoleCmd._debug("    - indx: %r", indx)

            priority = None
            if len(args) >= 5:
                priority = int(args[4])
            if _debug: TestConsoleCmd._debug("    - priority: %r", priority)

            # get the datatype
            datatype = get_datatype(obj_id[0], prop_id)
            if _debug: TestConsoleCmd._debug("    - datatype: %r", datatype)


            if datatype ==  ObjectPropertyReference:
                ref_obj, ref_prop = value.split(',')
                value = ObjectPropertyReference(
                    objectIdentifier = ref_obj,
                    propertyIdentifier = ref_prop
                )

            # build a request
            request = WritePropertyRequest(
                objectIdentifier=obj_id,
                propertyIdentifier=prop_id
                )
            request.pduDestination = Address(self.get_iut_address())

            # save the value
            request.propertyValue = Any()
            try:
                request.propertyValue.cast_in(value)
            except Exception as error:
                TestConsoleCmd._exception("WriteProperty cast error: %r", error)

            # optional array index
            if indx is not None:
                request.propertyArrayIndex = indx

            # optional priority
            if priority is not None:
                request.priority = priority

            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # make an IOCB
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            # do something for success
            if iocb.ioResponse:
                # should be an ack
                if isinstance(iocb.ioResponse, SimpleAckPDU):
                    return True
            return False

            # if iocb.ioResponse:
            #     if not isinstance(iocb.ioResponse, SimpleAckPDU):
            #         if _debug: TestConsoleCmd._debug("    - not an ack")
            #         return False
            #     else: return True
            #
            #     sys.stdout.write("ack\n")
            #
            # # do something for error/reject/abort
            # if iocb.ioError:
            #     sys.stdout.write(str(iocb.ioError) + '\n')

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)
            return False

    def do_write_setpointreference(self, args):
        """write_setpointreference <type>:<inst> <type>:<inst>,<prop>"""
        args = args.split()
        TestConsoleCmd._debug("do_write_setpointreference %r", args)

        try:
            obj_id, value = args[:2]
            prop_id = 'setpointReference'
            obj_id = ObjectIdentifier(obj_id).value


            indx = None
            if len(args) >= 4:
                if args[3] != "-":
                    indx = int(args[3])
            if _debug: TestConsoleCmd._debug("    - indx: %r", indx)

            priority = None
            if len(args) >= 5:
                priority = int(args[4])
            if _debug: TestConsoleCmd._debug("    - priority: %r", priority)

            # get the datatype
            datatype = get_datatype(obj_id[0], prop_id)
            if _debug: TestConsoleCmd._debug("    - datatype: %r", datatype)


            if datatype == SetpointReference:
                if value == 'none':
                    value = SetpointReference()
                else:
                    ref_obj, ref_prop = value.split(',')
                    obj_ref = ObjectPropertyReference(
                        objectIdentifier = ref_obj,
                        propertyIdentifier = ref_prop
                    )
                    value = SetpointReference(
                        setpointReference = obj_ref
                    )

            # build a request
            request = WritePropertyRequest(
                objectIdentifier=obj_id,
                propertyIdentifier=prop_id
                )
            request.pduDestination = Address(self.get_iut_address())

            # save the value
            request.propertyValue = Any()
            try:
                request.propertyValue.cast_in(value)
            except Exception as error:
                TestConsoleCmd._exception("WriteProperty cast error: %r", error)

            # optional array index
            if indx is not None:
                request.propertyArrayIndex = indx

            # optional priority
            if priority is not None:
                request.priority = priority

            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # make an IOCB
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            # # do something for success
            # if iocb.ioResponse:
            #     # should be an ack
            #     if isinstance(iocb.ioResponse, SimpleAckPDU):
            #         return True
            # return False

            # if iocb.ioResponse:
            #     if not isinstance(iocb.ioResponse, SimpleAckPDU):
            #         if _debug: TestConsoleCmd._debug("    - not an ack")
            #         return False
            #     else: return True
            #
            #     sys.stdout.write("ack\n")
            #
            # # do something for error/reject/abort
            # if iocb.ioError:
            #     sys.stdout.write(str(iocb.ioError) + '\n')

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)
            # return False

    def write_value(self, args):
        """write <type> <inst> <prop> <value> [ <indx> ] [ <priority> ]"""
        args = args.split()
        TestConsoleCmd._debug("do_write %r", args)

        try:
            obj_id, prop_id = args[:2]
            obj_id = ObjectIdentifier(obj_id).value
            value = args[2]

            indx = None
            if len(args) >= 4:
                if args[3] != "-":
                    indx = int(args[3])
            if _debug: TestConsoleCmd._debug("    - indx: %r", indx)

            priority = None
            if len(args) >= 5:
                priority = int(args[4])
            if _debug: TestConsoleCmd._debug("    - priority: %r", priority)

            # get the datatype
            datatype = get_datatype(obj_id[0], prop_id)
            if _debug: TestConsoleCmd._debug("    - datatype: %r", datatype)
            # change atomic values into something encodeable, null is a special case
            if (value == 'null'):
                value = Null()
            elif issubclass(datatype, AnyAtomic):
                dtype, dvalue = value.split(':', 1)
                if _debug: TestConsoleCmd._debug("    - dtype, dvalue: %r, %r", dtype, dvalue)


                datatype = {
                    'b': Boolean,
                    'u': lambda x: Unsigned(int(x)),
                    'i': lambda x: Integer(int(x)),
                    'r': lambda x: Real(float(x)),
                    'd': lambda x: Double(float(x)),
                    'o': OctetString,
                    'c': CharacterString,
                    'bs': BitString,
                    'date': Date,
                    'time': Time,
                    'id': ObjectIdentifier,
                    'scale_f': Scale #lambda x: Scale(floatScale=Real(float(x))),
                    #'scale_u': lambda x: Scale(integerScale=Integer(int(x))),
                    }[dtype]
                if _debug: TestConsoleCmd._debug("    - datatype: %r", datatype)

                value = datatype(dvalue)
                if _debug: TestConsoleCmd._debug("    - value: %r", value)

            elif issubclass(datatype, Atomic):
                if datatype is Integer:
                    value = int(value)
                elif datatype is Real:
                    value = float(value)
                elif datatype is Unsigned:
                    value = int(value)
                value = datatype(value)
            elif issubclass(datatype, Array) and (indx is not None):
                if indx == 0:
                    value = Integer(value)
                elif issubclass(datatype.subtype, Atomic):
                    value = datatype.subtype(value)
                elif not isinstance(value, datatype.subtype):
                    raise TypeError("invalid result datatype, expecting %s" % (datatype.subtype.__name__,))
            elif value.split(':')[0] == 'scale':
                tmp, dtype, dvalue = value.split(':', 2)
                value = Scale()
                value.integerScale = Unsigned(int(17))
                if dtype == 'r':
                    value.floatScale = Real(float(dvalue))
                elif dtype == 'u':
                    value.integerScale = Unsigned(int(dvalue))
                else:
                    print ("value should be scale:r:35.61 or scale:u:18")
            elif not isinstance(value, datatype):
                raise TypeError("invalid result datatype, expecting %s" % (datatype.__name__,))
            if _debug: TestConsoleCmd._debug("    - encodeable value: %r %s", value, type(value))

            # build a request
            request = WritePropertyRequest(
                objectIdentifier=obj_id,
                propertyIdentifier=prop_id
                )
            request.pduDestination = Address(self.get_iut_address())

            # save the value
            request.propertyValue = Any()
            try:
                request.propertyValue.cast_in(value)
            except Exception as error:
                TestConsoleCmd._exception("WriteProperty cast error: %r", error)

            # optional array index
            if indx is not None:
                request.propertyArrayIndex = indx

            # optional priority
            if priority is not None:
                request.priority = priority

            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # make an IOCB
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            # do something for success
            if iocb.ioResponse:
                # should be an ack
                if isinstance(iocb.ioResponse, SimpleAckPDU):
                    return "Ack"

            if iocb.ioError:
                return iocb.ioError
            return "None"

            # if iocb.ioResponse:
            #     if not isinstance(iocb.ioResponse, SimpleAckPDU):
            #         if _debug: TestConsoleCmd._debug("    - not an ack")
            #         return False
            #     else: return True
            #
            #     sys.stdout.write("ack\n")
            #
            # # do something for error/reject/abort
            # if iocb.ioError:
            #     sys.stdout.write(str(iocb.ioError) + '\n')

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)
            return "exception: {}".format(error)

    def do_write(self, args):
        """write <type> <inst> <prop> <value> [ <indx> ] [ <priority> ]"""
        args = args.split()
        TestConsoleCmd._debug("do_write %r", args)
        

        try:
            obj_id, prop_id = args[:2]
            if prop_id.isnumeric():
                prop_id = int(prop_id)
            obj_id = ObjectIdentifier(obj_id).value
            value = args[2]
            

            indx = None
            if len(args) >= 4:
                if args[3] != "-":
                    indx = int(args[3])
            if _debug: TestConsoleCmd._debug("    - indx: %r", indx)

            priority = None
            if len(args) >= 5:
                priority = int(args[4])
            if _debug: TestConsoleCmd._debug("    - priority: %r", priority)

            # get the datatype
            formatted_output = f"{obj_id[0]} {obj_id[1]}" #obj_id[1] is the number of which binary
            print(formatted_output)

            datatype = get_datatype(obj_id[0], prop_id)
            if _debug: TestConsoleCmd._debug("    - datatype: %r", datatype)
            # print (datatype)
            print (value)
            # change atomic values into something encodeable, null is a special case
            if (value == 'null'):
                value = Null()
            elif issubclass(datatype, AnyAtomic):
                dtype, dvalue = value.split(':', 1)
                if _debug: TestConsoleCmd._debug("    - dtype, dvalue: %r, %r", dtype, dvalue)


                datatype = {
                    'b': Boolean,
                    'u': lambda x: Unsigned(int(x)),
                    'i': lambda x: Integer(int(x)),
                    'r': lambda x: Real(float(x)),
                    'd': lambda x: Double(float(x)),
                    'o': OctetString,
                    'c': CharacterString,
                    'bs': BitString,
                    'date': Date,
                    'time': Time,
                    'id': ObjectIdentifier,
                    'scale_f': Scale #lambda x: Scale(floatScale=Real(float(x))),
                    #'scale_u': lambda x: Scale(integerScale=Integer(int(x))),
                    }[dtype]
                if _debug: TestConsoleCmd._debug("    - datatype: %r", datatype)

                value = datatype(dvalue)
                if _debug: TestConsoleCmd._debug("    - value: %r", value)

            elif issubclass(datatype, Atomic):
                if datatype is Integer:
                    value = int(value)
                elif datatype is Real:
                    value = float(value)
                elif datatype is Double:
                    value = float(value)
                elif datatype is Unsigned:
                    value = int(value)
                elif issubclass(datatype, Enumerated):
                    if value.isnumeric():
                        value = int(value)
                value = datatype(value)
            elif issubclass(datatype, Array) and (indx is not None):
                if indx == 0:
                    value = Integer(value)
                elif issubclass(datatype.subtype, Atomic):
                    value = datatype.subtype(value)
                elif not isinstance(value, datatype.subtype):
                    raise TypeError("invalid result datatype, expecting %s" % (datatype.subtype.__name__,))
            elif value.split(':')[0] == 'scale':
                tmp, dtype, dvalue = value.split(':', 2)
                value = Scale()
                value.integerScale = Unsigned(int(17))
                if dtype == 'r':
                    value.floatScale = Real(float(dvalue))
                elif dtype == 'u':
                    value.integerScale = Unsigned(int(dvalue))
                else:
                    print ("value should be scale:r:35.61 or scale:u:18")
            elif not isinstance(value, datatype):
                raise TypeError("invalid result datatype, expecting %s" % (datatype.__name__,))
            if _debug: TestConsoleCmd._debug("    - encodeable value: %r %s", value, type(value))

            # build a request
            request = WritePropertyRequest(
                objectIdentifier=obj_id,
                propertyIdentifier=prop_id
                )
            request.pduDestination = Address(self.get_iut_address())

            # save the value
            request.propertyValue = Any()
            try:
                request.propertyValue.cast_in(value)
            except Exception as error:
                TestConsoleCmd._exception("WriteProperty cast error: %r", error)

            # optional array index
            if indx is not None:
                request.propertyArrayIndex = indx

            # optional priority
            if priority is not None:
                request.priority = priority

            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # make an IOCB
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            # do something for success
            if iocb.ioResponse:
                # should be an ack
                if not isinstance(iocb.ioResponse, SimpleAckPDU):
                    if _debug: TestConsoleCmd._debug("    - not an ack")
                    return

                sys.stdout.write("ack\n")

            # do something for error/reject/abort
            if iocb.ioError:
                sys.stdout.write(str(iocb.ioError) + '\n')

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)

    def do_iut(self, args):
        """iut  [ <addr> ]"""
        args = args.split()
        global iut_address
        global iut_address_list
        if len(args) == 0:
            if len(iut_address_list) == 0:
                self.do_whois("")
                time.sleep(2)
            sys.stdout.write("IUT: " + self.get_iut_address() + '\n')
            for key in list(iut_address_list):
                sys.stdout.write('"{}": {} \n'.format(key, iut_address_list[key]))
        elif len(args) == 2:
            value, key = args
            if value == 'del':
                del iut_address_list[key]
            else:
                iut_address_list[key] = value
            self.do_iut("")
        else:
            if args[0] in iut_address_list:
                args[0] = iut_address_list[args[0]]
            iut_address = args[0]
            sys.stdout.write("IUT: " + self.get_iut_address() + '\n')

    def rpm_value(self, args):
        """read <addr> ( <objid> ( <prop> [ <indx> ] )... )..."""
        args = args.split()
        return_buffer = {}
        if _debug: TestConsoleCmd._debug("do_read %r", args)

        try:
            i = 0
            addr = args[i]
            i += 1

            read_access_spec_list = []
            while i < len(args):
                obj_id = ObjectIdentifier(args[i]).value
                i += 1

                prop_reference_list = []
                while i < len(args):
                    prop_id = args[i]
                    if prop_id not in PropertyIdentifier.enumerations:
                        break

                    i += 1
                    if prop_id in ('all', 'required', 'optional'):
                        pass
                    else:
                        datatype = get_datatype(obj_id[0], prop_id)
                        # if not datatype:
                        #     raise ValueError("invalid property for object type")

                    # build a property reference
                    prop_reference = PropertyReference(
                        propertyIdentifier=prop_id,
                        )

                    # check for an array index
                    if (i < len(args)) and args[i].isdigit():
                        prop_reference.propertyArrayIndex = int(args[i])
                        i += 1

                    # add it to the list
                    prop_reference_list.append(prop_reference)

                # check for at least one property
                if not prop_reference_list:
                    raise ValueError("provide at least one property")

                # build a read access specification
                read_access_spec = ReadAccessSpecification(
                    objectIdentifier=obj_id,
                    listOfPropertyReferences=prop_reference_list,
                    )

                # add it to the list
                read_access_spec_list.append(read_access_spec)

            # check for at least one
            if not read_access_spec_list:
                raise RuntimeError("at least one read access specification required")

            # build the request
            request = ReadPropertyMultipleRequest(
                listOfReadAccessSpecs=read_access_spec_list,
                )
            request.pduDestination = Address(addr)
            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # make an IOCB
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            deferred(this_application.request_io, iocb)
            print("give it to the application")

            # wait for it to complete
            iocb.wait()
            print("wait for it to complete")

            # do something for success
            if iocb.ioResponse:
                apdu = iocb.ioResponse

                # should be an ack
                if not isinstance(apdu, ReadPropertyMultipleACK):
                    if _debug: TestConsoleCmd._debug("    - not an ack")
                    return

                # loop through the results
                for result in apdu.listOfReadAccessResults:
                    # here is the object identifier
                    objectIdentifier = result.objectIdentifier
                    if _debug: TestConsoleCmd._debug("    - objectIdentifier: %r", objectIdentifier)
                    return_buffer[objectIdentifier] = {}

                    # now come the property values per object
                    for element in result.listOfResults:
                        # get the property and array index
                        propertyIdentifier = element.propertyIdentifier
                        if _debug: TestConsoleCmd._debug("    - propertyIdentifier: %r", propertyIdentifier)
                        propertyArrayIndex = element.propertyArrayIndex
                        if _debug: TestConsoleCmd._debug("    - propertyArrayIndex: %r", propertyArrayIndex)

                        # here is the read result
                        readResult = element.readResult

                        sys.stdout.write(str(propertyIdentifier))
                        return_buffer[objectIdentifier][propertyIdentifier] = {}
                        if propertyArrayIndex is not None:
                            sys.stdout.write("[" + str(propertyArrayIndex) + "]")
                            return_buffer[objectIdentifier][propertyIdentifier]['arrayIndex'] = propertyArrayIndex

                        # check for an error
                        if readResult.propertyAccessError is not None:
                            sys.stdout.write(" ! " + str(readResult.propertyAccessError) + '\n')
                            return_buffer[objectIdentifier][propertyIdentifier]['error'] = readResult.propertyAccessError.dict_contents()

                        else:
                            # here is the value
                            propertyValue = readResult.propertyValue

                            # find the datatype
                            datatype = get_datatype(objectIdentifier[0], propertyIdentifier)
                            if _debug: TestConsoleCmd._debug("    - datatype: %r", datatype)
                            if not datatype:
                                value = '?'
                            else:
                                # special case for array parts, others are managed by cast_out
                                if issubclass(datatype, Array) and (propertyArrayIndex is not None):
                                    if propertyArrayIndex == 0:
                                        value = propertyValue.cast_out(Unsigned)
                                    else:
                                        value = propertyValue.cast_out(datatype.subtype)
                                else:
                                    value = propertyValue.cast_out(datatype)
                                if _debug: TestConsoleCmd._debug("    - value: %r", value)

                            sys.stdout.write(" = " + str(value) + '\n')
                            return_buffer[objectIdentifier][propertyIdentifier]['value'] = value
                        sys.stdout.flush()

            # do something for error/reject/abort
            if iocb.ioError:
                sys.stdout.write(str(iocb.ioError) + '\n')
                return_buffer['ioError'] = iocb.ioError.dict_contents()
                print(iocb.ioError.dict_contents())

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)
        print(return_buffer)
        return return_buffer

    def do_rpm2(self, args):
        """rpm2 <addr> ( <objid> ( <prop> [ <indx> ] )... )..."""
        buffer = self.rpm_value(self.get_iut_address() + " " + args)
        for i in buffer:
            print(i)
            for j in buffer[i]:
                if 'value' in buffer[i][j]:
                    value = buffer[i][j]['value']
                    if isinstance(value, (TimeStamp,
                                        PriorityArray,
                                        DateTime,
                                        ObjectPropertyReference,
                                        SetpointReference)):
                        value = value_to_string(value)
                    print("\t{} = {}".format(j, value))
                elif 'error' in buffer[i][j]:
                    print("\t{} = {}".format(j, buffer[i][j]['error'], sep=': '))


    def do_rpm(self, args):
        """rpm <addr> ( <objid> ( <prop> [ <indx> ] )... )..."""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_read %r", args)

        try:
            i = 0
            addr = self.get_iut_address()

            read_access_spec_list = []
            while i < len(args):
                obj_id = ObjectIdentifier(args[i]).value
                i += 1

                prop_reference_list = []
                while i < len(args):
                    prop_id = args[i]
                    if prop_id not in PropertyIdentifier.enumerations:
                        break

                    i += 1
                    if prop_id in ('all', 'required', 'optional'):
                        pass
                    else:
                        datatype = get_datatype(obj_id[0], prop_id)
                        if not datatype:
                            raise ValueError("invalid property for object type")

                    # build a property reference
                    prop_reference = PropertyReference(
                        propertyIdentifier=prop_id,
                        )

                    # check for an array index
                    if (i < len(args)) and args[i].isdigit():
                        prop_reference.propertyArrayIndex = int(args[i])
                        i += 1

                    # add it to the list
                    prop_reference_list.append(prop_reference)

                # check for at least one property
                if not prop_reference_list:
                    raise ValueError("provide at least one property")

                # build a read access specification
                read_access_spec = ReadAccessSpecification(
                    objectIdentifier=obj_id,
                    listOfPropertyReferences=prop_reference_list,
                    )

                # add it to the list
                read_access_spec_list.append(read_access_spec)

            # check for at least one
            if not read_access_spec_list:
                raise RuntimeError("at least one read access specification required")

            # build the request
            request = ReadPropertyMultipleRequest(
                listOfReadAccessSpecs=read_access_spec_list,
                )
            request.pduDestination = Address(addr)
            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # make an IOCB
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            # do something for success
            if iocb.ioResponse:
                apdu = iocb.ioResponse

                # should be an ack
                if not isinstance(apdu, ReadPropertyMultipleACK):
                    if _debug: TestConsoleCmd._debug("    - not an ack")
                    return

                # loop through the results
                for result in apdu.listOfReadAccessResults:
                    # here is the object identifier
                    objectIdentifier = result.objectIdentifier
                    if _debug: TestConsoleCmd._debug("    - objectIdentifier: %r", objectIdentifier)

                    # now come the property values per object
                    for element in result.listOfResults:
                        # get the property and array index
                        propertyIdentifier = element.propertyIdentifier
                        if _debug: TestConsoleCmd._debug("    - propertyIdentifier: %r", propertyIdentifier)
                        propertyArrayIndex = element.propertyArrayIndex
                        if _debug: TestConsoleCmd._debug("    - propertyArrayIndex: %r", propertyArrayIndex)

                        # here is the read result
                        readResult = element.readResult

                        sys.stdout.write(str(propertyIdentifier))
                        if propertyArrayIndex is not None:
                            sys.stdout.write("[" + str(propertyArrayIndex) + "]")

                        # check for an error
                        if readResult.propertyAccessError is not None:
                            sys.stdout.write(" ! " + str(readResult.propertyAccessError) + '\n')

                        else:
                            # here is the value
                            propertyValue = readResult.propertyValue

                            # find the datatype
                            datatype = get_datatype(objectIdentifier[0], propertyIdentifier)
                            if _debug: TestConsoleCmd._debug("    - datatype: %r", datatype)
                            if not datatype:
                                print(objectIdentifier[0], propertyIdentifier)
                                value = '?'
                            else:
                                # special case for array parts, others are managed by cast_out
                                if issubclass(datatype, Array) and (propertyArrayIndex is not None):
                                    if propertyArrayIndex == 0:
                                        value = propertyValue.cast_out(Unsigned)
                                    else:
                                        value = propertyValue.cast_out(datatype.subtype)
                                else:
                                    value = propertyValue.cast_out(datatype)
                                if _debug: TestConsoleCmd._debug("    - value: %r", value)
                            if isinstance(value, (TimeStamp,
                                                PriorityArray,
                                                DateTime,
                                                ObjectPropertyReference,
                                                SetpointReference)):
                                value = value_to_string(value)
                            if isinstance(datatype, Date):
                                value = "{}".format(Date(value))

                            sys.stdout.write(" = " + str(value) + '\n')
                        sys.stdout.flush()

            # do something for error/reject/abort
            if iocb.ioError:
                sys.stdout.write(str(iocb.ioError) + '\n')

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)

    def do_cpt_json(self, args):
        """cpt_json <JSON>"""
        request = ConfirmedPrivateTransferRequest(
            vendorID = 979,
            serviceNumber = 1
        )
        request.pduDestination = Address(self.get_iut_address())
        a = Any()
        a.cast_in(CharacterString(args))
        request.serviceParameters = a

        # make an IOCB
        iocb = IOCB(request)
        if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

        # give it to the application
        this_application.request_io(iocb)

        # wait for it to complete
        iocb.wait()

        if iocb.ioResponse:
            print (iocb.ioResponse)
            if isinstance(iocb.ioResponse,ConfirmedPrivateTransferACK):
                # print (iocb.ioResponse.dict_contents())
                # print(iocb.ioResponse.resultBlock)
                # print(iocb.ioResponse.resultBlock.dict_contents())
                # print(iocb.ioResponse.resultBlock.tagList)
                # print(iocb.ioResponse.resultBlock.tagList[0])
                # print(iocb.ioResponse.resultBlock.tagList[0].tagLVT)
                # print(iocb.ioResponse.resultBlock.tagList[0].tagLVT)
                # print(iocb.ioResponse.resultBlock.tagList[0].debug_contents())
                # print(iocb.ioResponse.resultBlock.tagList[0].tagData)
                value = bytes(iocb.ioResponse.resultBlock.tagList[0].tagData[1:])
                # print(value)
                # print(json.loads(value))
                try:
                    value = bytes(iocb.ioResponse.resultBlock.tagList[0].tagData[1:])
                    # value=iocb.ioResponse.resultBlock.cast_out(CharacterString)
                    # This works if modify VAV to encode a CharacterString insteadof Context Encoded CharacterString.
                    print(value)
                except Exception as error:
                    print(error)

# do something for success
    def do_sendlogic(self, args):
        """sendlogic <file_name>"""
        in_file = open(args, "rb")
        position = 0
        while True:
            text = in_file.read(50)
            print (text)
            if len(text) > 0:
                self.do_writestream("{} {} {} {}".format(self.get_iut_address(), 2, position, text), 'xyz')
                #print ("{}\t{}\t{}".format(position, len(text), text))
            else:
                break
            position += len(text)
        in_file.close()

    def do_setSchedule(self, args):
        """setSchedule"""
        aTime = Time("00:00:00")
        aValue = Any()
        aValue.cast_in(Enumerated(1))
        daily = DailySchedule()
        daily.daySchedule = []
        daily.daySchedule.append(TimeValue(time = aTime, value = aValue))
        weeklySchedule=ArrayOf(DailySchedule)([
            DailySchedule(
                daySchedule=[
                    TimeValue(time=(8,0,0,0), value=Integer(8)),
                    TimeValue(time=(14,0,0,0), value=Null()),
                    TimeValue(time=(17,0,0,0), value=Integer(42)),
#                   TimeValue(time=(0,0,0,0), value=Null()),
                    ]
                ),
            ] * 7)
        request = WritePropertyRequest(
            objectIdentifier=ObjectIdentifier("schedule:1"),
            propertyIdentifier=PropertyIdentifier("weeklySchedule")
            )
        request.pduDestination = Address(self.get_iut_address())
        try:
            # save the value
            request.propertyValue = Any()
            try:
                request.propertyValue.cast_in(weeklySchedule)
            except Exception as error:
                TestConsoleCmd._exception("WriteProperty cast error: %r", error)

            # optional array index
            # if indx is not None:
            #     request.propertyArrayIndex = indx

            # optional priority
            # if priority is not None:
            #     request.priority = priority

            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # make an IOCB
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            # do something for success
            if iocb.ioResponse:
                # should be an ack
                if not isinstance(iocb.ioResponse, SimpleAckPDU):
                    if _debug: TestConsoleCmd._debug("    - not an ack")
                    return

                sys.stdout.write("ack\n")

            # do something for error/reject/abort
            if iocb.ioError:
                sys.stdout.write(str(iocb.ioError) + '\n')

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)


    def do_readstream(self, args):
        """readstream <addr> <inst> <start> <count>"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_readstream %r", args)

        try:
            addr, obj_inst, start_position, octet_count = args

            obj_type = 'file'
            obj_inst = int(obj_inst)
            start_position = int(start_position)
            octet_count = int(octet_count)

            # build a request
            request = AtomicReadFileRequest(
                fileIdentifier=(obj_type, obj_inst),
                accessMethod=AtomicReadFileRequestAccessMethodChoice(
                    streamAccess=AtomicReadFileRequestAccessMethodChoiceStreamAccess(
                        fileStartPosition=start_position,
                        requestedOctetCount=octet_count,
                        ),
                    ),
                )
            request.pduDestination = Address(addr)
            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # make an IOCB
            iocb = IOCB(request)
            if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

            # give it to the application
            this_application.request_io(iocb)

            # wait for it to complete
            iocb.wait()

            # do something for success
            if iocb.ioResponse:
                apdu = iocb.ioResponse

                # should be an ack
                if not isinstance(apdu, AtomicReadFileACK):
                    if _debug: TestConsoleCmd._debug("    - not an ack")
                    return

                # suck out the record data
                if apdu.accessMethod.recordAccess:
                    value = apdu.accessMethod.recordAccess.fileRecordData
                elif apdu.accessMethod.streamAccess:
                    value = apdu.accessMethod.streamAccess.fileData
                if _debug: TestConsoleCmd._debug("    - value: %r", value)

                sys.stdout.write(repr(value) + '\n')
                sys.stdout.flush()

            # do something for error/reject/abort
            if iocb.ioError:
                sys.stdout.write(str(iocb.ioError) + '\n')

        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)

    def do_readfile(self, args):
        """readfile <inst> <filename>"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_readstream %r", args)
        fileSize = 0

        try:
            obj_inst, filename = args
            start_position = 0
            octet_count = 100

            try:
                obj_id = ObjectIdentifier("file:"+str(obj_inst)).value
                prop_id = "fileSize"
                datatype = get_datatype(obj_id[0], prop_id)
                if not datatype:
                    raise ValueError("invalid property for object type")

                # build a request
                request = ReadPropertyRequest(
                    objectIdentifier=obj_id,
                    propertyIdentifier=prop_id,
                    )
                request.pduDestination = Address(self.get_iut_address())

                # make an IOCB
                iocb = IOCB(request)
                if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

                # give it to the application
                this_application.request_io(iocb)

                # wait for it to complete
                iocb.wait()

                # do something for success
                if iocb.ioResponse:
                    apdu = iocb.ioResponse

                    # should be an ack
                    if not isinstance(apdu, ReadPropertyACK):
                        if _debug: TestConsoleCmd._debug("    - not an ack")
                        return

                    # find the datatype
                    datatype = get_datatype(apdu.objectIdentifier[0], apdu.propertyIdentifier)
                    if _debug: TestConsoleCmd._debug("    - datatype: %r", datatype)
                    if not datatype:
                        raise TypeError("unknown datatype")

                    # special case for array parts, others are managed by cast_out
                    if issubclass(datatype, Array) and (apdu.propertyArrayIndex is not None):
                        if apdu.propertyArrayIndex == 0:
                            value = apdu.propertyValue.cast_out(Unsigned)
                        else:
                            value = apdu.propertyValue.cast_out(datatype.subtype)
                    else:
                        value = apdu.propertyValue.cast_out(datatype)
                    if _debug: TestConsoleCmd._debug("    - value: %r", value)

                    sys.stdout.write(str(value) + '\n')
                    if hasattr(value, 'debug_contents'):
                        value.debug_contents(file=sys.stdout)
                    sys.stdout.flush()
                    fileSize = int(value)
                # do something for error/reject/abort
                if iocb.ioError:
                    sys.stdout.write(str(iocb.ioError) + '\n')

            except Exception as error:
                TestConsoleCmd._exception("exception: %r", error)

            buffer = ""

            while (fileSize > 0):
                obj_type = 'file'
                obj_inst = int(obj_inst)
                start_position = int(len(buffer))
                octet_count = min(int(100), fileSize)

                # build a request
                request = AtomicReadFileRequest(
                    fileIdentifier=(obj_type, obj_inst),
                    accessMethod=AtomicReadFileRequestAccessMethodChoice(
                        streamAccess=AtomicReadFileRequestAccessMethodChoiceStreamAccess(
                            fileStartPosition=start_position,
                            requestedOctetCount=octet_count,
                            ),
                        ),
                    )
                request.pduDestination = Address(self.get_iut_address())
                if _debug: TestConsoleCmd._debug("    - request: %r", request)

                # make an IOCB
                iocb = IOCB(request)
                if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

                # give it to the application
                this_application.request_io(iocb)

                # wait for it to complete
                iocb.wait(2)

                # do something for success
                if iocb.ioResponse:
                    apdu = iocb.ioResponse

                    # should be an ack
                    if not isinstance(apdu, AtomicReadFileACK):
                        if _debug: TestConsoleCmd._debug("    - not an ack")
                        return

                    # suck out the record data
                    if apdu.accessMethod.recordAccess:
                        value = apdu.accessMethod.recordAccess.fileRecordData
                    elif apdu.accessMethod.streamAccess:
                        value = apdu.accessMethod.streamAccess.fileData
                    if _debug: TestConsoleCmd._debug("    - value: %r", value)

                    buffer = buffer + value;
                    fileSize = fileSize - octet_count;
                    sys.stdout.write("Read " + str(octet_count) + '\n')
                    sys.stdout.flush()

                # do something for error/reject/abort
                if iocb.ioError:
                    sys.stdout.write(str(iocb.ioError) + '\n')

            f = open(filename, 'w+b')
            f.write(bytearray(buffer))
            f.close()
            sys.stdout.write(repr(buffer) + '\n')
            sys.stdout.flush()
        except Exception as error:
            TestConsoleCmd._exception("exception: %r", error)


    def do_sendfile(self, args):
        """writestream <inst> <file>"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_writestream %r", args)
        obj_inst, filename = args
        self.do_write("file:{} fileSize 0".format(obj_inst))
        in_file = open(filename, "rb")
        position = 0
        while True:
            data = in_file.read(50)
            print (data)
            if len(data) < 1:
                break
            try:
                obj_type = 'file'
                obj_inst = int(obj_inst)
                data = data.encode('utf-8')

                # build a request
                request = AtomicWriteFileRequest(
                    fileIdentifier=(obj_type, obj_inst),
                    accessMethod=AtomicWriteFileRequestAccessMethodChoice(
                        streamAccess=AtomicWriteFileRequestAccessMethodChoiceStreamAccess(
                            fileStartPosition=position,
                            fileData=data,
                            ),
                        ),
                    )
                request.pduDestination = Address(self.get_iut_address())
                if _debug: TestConsoleCmd._debug("    - request: %r", request)

                # make an IOCB
                iocb = IOCB(request)
                if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

                # give it to the application
                this_application.request_io(iocb)

                # wait for it to complete
                iocb.wait()

                # do something for success
                if iocb.ioResponse:
                    apdu = iocb.ioResponse

                    # should be an ack
                    if not isinstance(apdu, AtomicWriteFileACK):
                        if _debug: TestConsoleCmd._debug("    - not an ack")
                        return

                    # suck out the record data
                    if apdu.fileStartPosition is not None:
                        value = apdu.fileStartPosition
                    elif apdu.fileStartRecord is not None:
                        value = apdu.fileStartRecord
                    TestConsoleCmd._debug("    - value: %r", value)

                    sys.stdout.write(repr(value) + '\n')
                    sys.stdout.flush()

                # do something for error/reject/abort
                if iocb.ioError:
                    sys.stdout.write(str(iocb.ioError) + '\n')

            except Exception as error:
                TestConsoleCmd._exception("exception: %r", error)
            position += len(data)


    def do_wirtn(self, args):
        """wirtn [dnet]"""
        if len(args) == 0:
            dnet = None
        else:
            dnet = int(args)
        nsap = this_application.nsap
        xnpdu = WhoIsRouterToNetwork(dnet)
        xnpdu.pduDestination = LocalBroadcast()

        # send it to all of the connected adapters
        for xadapter in nsap.adapters.values():
            nsap.sap_indication(xadapter, xnpdu)

    def do_BTL_10_2_2_7_1(self, args):
        self.BTL_10_2_2_7_1(args)

    def do_VAV_issue23(self, args):
        # for a in args.split():
        self.BTL_10_2_2_7_1(args.split())
        self.BTL_10_2_4_1(args.split())

    def do_VAV_issue34(self, args):
        self.do_BTL_10(args)

    def do_BTL_2_2_X1(self, args):
        """BTL_2_2_X1 [address]          This test is to send a specific packet through the router followed by a read property"""
        addresses = args.split()
        if len(addresses):
            for address in addresses:
                net, mac = address.split(':')
                net = int(net)
                router = self.find_net(net)
                if not isinstance(router, Address):
                    self.do_whois("")
                    time.sleep(5)
                    router = self.find_net(net)

                bvlc = [0x81, 0x0a, 0x00, 0x0c]
                npdu = [0x01, 0x00]
                npdu[1] |= 0x20 # Destination Specifier
                # npdu[1] |= 0x04 # Expecting reply
                npdu.append(int(net/256))
                npdu.append(net%256)
                if '0x' in mac:
                    npdu.append(6)
                    for x in range(2,14,2):
                        npdu.append(int(mac[x:x+2],16))
                else:
                    npdu.append(1)
                    npdu.append(int(mac)+2)
                npdu.append(33) # hop count
                apdu1 = [0x55, 0xFF, 0x05, 0xFF, 0x00, 0x01, 0xF5]

                bvlc[3] = len(bvlc) + len(npdu) + len(apdu1)
                rawpdu1_arg = "{} x'".format(router)
                for x in bvlc:
                    rawpdu1_arg += hex(x)[2:] + '.'
                for x in npdu:
                    rawpdu1_arg += hex(x)[2:] + '.'
                for x in apdu1:
                    rawpdu1_arg += hex(x)[2:] + '.'
                rawpdu1_arg = rawpdu1_arg[0:-1] + "'"

                self.do_rawpdu(rawpdu1_arg)
                self.do_iut(address)
                self.do_read("device:4194303 objectName")


    def do_BTL10_2_6(self, args): #BTL_10_2_6(self, addresses):
        """BTL10_2_6 [address] <address>...  Sends messages at set priority levels.  Check wireshark for results"""
        name = "10.2.6 Network Layer Priority"
        addresses = args.split()
        if len(addresses):
            for address in addresses:
                for priority in [0,1,2,3]:
                    testname = "{} [{} {}]".format(name, address, priority)
                    net, mac = address.split(':')
                    net = int(net)
                    router = self.find_net(net)
                    if not isinstance(router, Address):
                        self.do_whois("")
                        time.sleep(5)
                        router = self.find_net(net)

                    bvlc = [0x81, 0x0a, 0x00, 0x0c]
                    npdu = [0x01, 0x00]
                    npdu[1] |= 0x20 # Destination Specifier
                    npdu[1] |= 0x04 # Expecting reply
                    npdu[1] |= priority
                    npdu.append(int(net/256))
                    npdu.append(net%256)
                    if '0x' in mac:
                        npdu.append(6)
                        for x in range(2,14,2):
                            npdu.append(int(mac[x:x+2],16))
                    else:
                        npdu.append(1)
                        npdu.append(int(mac))
                    npdu.append(33) # hop count
                    apdu = [0x00, 0x43, 0x04, 0x0c, 0x0c, 0x02, 0x3f, 0xff, 0xff, 0x19, 0x4b] # read property device:4194303, object identifier
                    #81.0a.00.[0c] <- byte length
                    #.01.[20]. <- control
                    # ff.ff.00.02.10.08'
                    bvlc[3] = len(bvlc) + len(npdu) + len(apdu)
                    rawpdu_arg = "{} x'".format(router)
                    for x in bvlc:
                        rawpdu_arg += hex(x)[2:] + '.'
                    for x in npdu:
                        rawpdu_arg += hex(x)[2:] + '.'
                    for x in apdu:
                        rawpdu_arg += hex(x)[2:] + '.'
                    rawpdu_arg = rawpdu_arg[0:-1] + "'"
                    print(rawpdu_arg)
                    self.do_rawpdu(rawpdu_arg)
                    self.test_results.append(["manual check", testname])
                    # request = ReadPropertyRequest(
                    #     objectIdentifier = 'device:4194303',
                    #     propertyIdentifier = 'objectIdentifier'
                    # )
                    # request.pduDestination = Address("192.168.1.30")
                    # request.pduNetworkPriority = 2
                    # print(request.debug_contents())
                    # # make an IOCB
                    # iocb = IOCB(request)
                    # if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)
                    #
                    # # give it to the application
                    # this_application.request_io(iocb)
                    #
                    # # wait for it to complete
                    # iocb.wait()
                    #
                    # # do something for success
                    # if iocb.ioResponse:
                    #     # should be an ack
                    #     if isinstance(iocb.ioResponse, ReadPropertyACK):
                    #         print("ReadPropertyACK, priority= {}".format(iocb.ioResponse.pduNetworkPriority))
                    #     print(iocb.ioResponse.debug_contents())

    def do_BTL_10_2_4_1(self, args):
        self.BTL_10_2_4_1(args.split())

    def do_VAV_issue36(self, args):
        self.BTL_10_2_5(args.split())

    def BTL_10_2_5(self, addresses):
        msg_store.clear_msg()
        msg_store.set_address_list(['all'])

        self.do_rawpdu("* x'81.0a.00.0c.01.20.ff.ff.00.02.10.08'")
        time.sleep(6)
        apdu_list = msg_store.get_msg()
        msg_store.clear_msg()
        print("sent broadcast Who-Is with Hop Count of 2.  Expect replies.")
        for x in apdu_list:
            if ':' in str(x.pduSource):
                print(x.pduSource)
        self.do_rawpdu("* x'81.0a.00.0c.01.20.ff.ff.00.01.10.08'")
        time.sleep(6)
        apdu_list = msg_store.get_msg()
        print("sent broadcast Who-Is with Hop Count of 1.  Expect no replies from other networks.")
        iamlist = []
        for x in apdu_list:
            if ':' in str(x.pduSource):
                iamlist.append(x.pduSource)
        if len(iamlist) > 0:
            print("{} I-Am Requests received from other networks.".format(len(iamlist)))
            for x in iamlist:
                print(x)
        else:
            print("no I-Am Requests from other networks.")
        msg_store.clear_msg()
        # print(apdu_list)
        self.do_rawpdu("* x'81.0a.00.0c.01.20.ff.ff.00.00.10.08'")
        time.sleep(6)
        apdu_list = msg_store.get_msg()
        msg_store.clear_msg()
        print("sent broadcast Who-Is with Hop Count of 0.  Expect no replies from other networks.")
        iamlist = []
        for x in apdu_list:
            if ':' in str(x.pduSource):
                iamlist.append(x.pduSource)
        if len(iamlist) > 0:
            print("{} I-Am Requests received from other networks.".format(len(iamlist)))
            for x in iamlist:
                print(x)
        else:
            print("no I-Am Requests from other networks.")

    def BTL_10_2_4_1(self, addresses):
        name = "10.2.4.1 Ignore Local Broadcast Message Traffic"
        #Method to replace Network Service Element and then set it back.
        print(name,addresses)
        old_nse = this_application.nse
        capture = NSE_Capture()
        capture.elementService = old_nse.elementService
        this_application.nse = capture
        bind(this_application.nse,this_application.nsap)
        capture.clear_list()
        testname = "{} {}".format(name, addresses)
        result = []
        self.do_whois_addr('*')
        time.sleep(3)
        npdu_list = capture.get_list()
        if len(npdu_list) > 0:
            for x in npdu_list:
                if(x.pduSource in addresses):
                    result.append("{} sent a reject message to network".format(x.pduSource))
        if len(result):
            self.test_results.append(["failed", result, testname])
        else:
            self.test_results.append(["manual - verify no response", testname])

        #restore Network Service Element
        this_application.nse = old_nse
        bind(this_application.nse,this_application.nsap)

    def BTL_10_2_2_7_1(self, addresses):
        name = "10.2.2.7.1 Unknown Network"
        #Method to replace Network Service Element and then set it back.
        old_nse = this_application.nse
        capture = NSE_Capture()
        capture.elementService = old_nse.elementService
        this_application.nse = capture
        bind(this_application.nse,this_application.nsap)
        capture.clear_list()

        for address in addresses:
            net = 54321
            while net in self.infocache(address):
                net = net - 1
            self.infocache("{} add {}".format(address, net))
            # self.do_bugin("bacpypes.netservice.NetworkServiceElement")
            # apdu retries does not change # of retries to a router?
            # retries = this_application.smap.numberOfApduRetries
            # this_application.smap.numberOfApduRetries = 1
            # print("BTL 10.2.2.7.1 Please verify that Reject-Message-To-Network is received.")
            #Msg_store does not get network messages
            # msg_store.set_address_list(address)
            # msg_store.clear_msg()
            for mac in ['1', '0xac67b2f7769c']:
                result = []
                testname = "{} [{}, {}:{}]".format(name, address, net, mac)
                self.do_iut("{}:{}".format(net, mac))
                rejected = False

                try:
                    capture.clear_list()
                    self.do_read("analogInput:1 presentValue")
                    npdu_list = capture.get_list()
                    capture.clear_list()
                    if len(npdu_list) > 0:
                        for x in npdu_list:
                            y = x.dict_contents()
                            if y['function'] == 'RejectMessageToNetwork':
                                rejected = True
                            if y['reject_reason'] != 1:
                                result.append("reason: {}".format(y['reject_reason']))
                            if x.pduDestination == "*":
                                result.append("RejectMessageToNetwork is broadcast")

                    if not rejected:
                        result.append("Not rejected")

                    if len(result):
                        self.test_results.append(["failed", result, testname])
                    else:
                        self.test_results.append(["pass", testname])
                except Exception as Error:
                    print(Error)
                    self.test_results.append(["error: {}".format(Error), testname])

            # x = msg_store.get_msg()
            # for a in x:
            #     print(a)
            self.do_bugout("bacpypes.netservice.NetworkServiceElement")
        # this_application.smap.numberOfApduRetries = retries

        #restore Network Service Element
        this_application.nse = old_nse
        bind(this_application.nse,this_application.nsap)

    def do_rawpdu1(self, args):
        """rawpdu <address> <data x'00.00...'> [expect reply 0 or 1] [network priority 0 or 1]"""

    def do_BTL_10(self, args):
        print(args, args.split())
        self.BTL_10_2_2_7_2(args.split(), range_min=0x14, range_max=0x15)
        self.BTL_10_2_2_7_2(args.split(), range_min=0x81, range_max=0x82)

    def BTL_10_2_2_7_2(self, addresses, range_min=0x14, range_max = 0x7F):
        name = "10.2.2.7.2 Unknown Network Layer Message Type"
        #Method to replace Network Service Element and then set it back.
        old_nse = this_application.nse
        capture = NSE_Capture()
        capture.elementService = old_nse.elementService
        this_application.nse = capture
        bind(this_application.nse,this_application.nsap)
        capture.clear_list()

        for address in addresses:
            for message_type in range(range_min, range_max + 1):
                testname = "{} [{}, {}]".format(name, address, message_type)
                result = []
                data = ["81","0a","00","07","01","80",hex(message_type)[2:]]
                rejected = False

                try:
                    start_time = time.time()
                    self.rawpdu(address, data)
                    while not rejected and (time.time() - start_time) < 3:
                        time.sleep(.1)
                        npdu_list = capture.get_list()
                        capture.clear_list()
                        if len(npdu_list) > 0:
                            for x in npdu_list:
                                y = x.dict_contents()
                                if y['function'] == 'RejectMessageToNetwork' and y['reject_reason'] == 3:
                                    rejected = True
                                else:
                                    result.append("{}, reason: {}".format(y['function'], y['reject_reason']))
                                if x.pduDestination == "*":
                                    result.append("RejectMessageToNetwork is broadcast")
                    if not rejected:
                        result.append("Not rejected")
                    if len(result):
                        self.test_results.append(["failed", result, testname])
                    else:
                        self.test_results.append(["pass", testname])
                except Exception as Error:
                    print(Error)
                    self.test_results.append(["error: {}".format(Error), testname])

        this_application.nse = old_nse
        bind(this_application.nse,this_application.nsap)

    def do_rawpdu(self, args):
        """rawpdu <address> <data x'00.00...'> [expect reply 0 or 1] [network priority 0 or 1]"""
        args = args.split()
        data = ["81","0b","00","0c","01","20","ff","ff","00","ff","10","08"]
        address = "*"
        expect_reply = 0
        network_priority = 0
        try:
            print(len(args))
            if len(args) >= 4:
                if int(args[3]) in [0,1]:
                    network_priority = int(args[3])
                print(network_priority)
            if len(args) >= 3:
                if int(args[2]) in [0,1]:
                    expect_reply = int(args[2])
                # print(expect_reply)
            if len(args) >= 2:
                if args[1][0:2] == "x'" and args[1][len(args[1]) - 1] == "'":
                    data = args[1][2:len(args[1]) - 1].split('.')
            if len(args) >= 1:
                address = args[0]
            # print("expect_reply", expect_reply)
            self.rawpdu(address, data, expect_reply=0, network_priority=0)
        except Exception as error:
            print("failed to send due to {}".format(error))

    def rawpdu(self, addr, data, expect_reply = 0, network_priority = 0):
        myPDU = PDU()
        for x in data:
            myPDU.put(int("0x{}".format(x),16))
        myPDU.pduDestination = Address(addr)
        myPDU.pduExpectingReply = 0
        myPDU.pduNetworkPriority = 0
        # myPDU.pduData = x'81.0b.00.0c.01.20.ff.ff.00.ff.10.08'
        this_application.mux.indication(myPDU, myPDU)

    def find_net(self, network):
        for x in this_application.nsap.router_info_cache.routers:
            for y in this_application.nsap.router_info_cache.routers[x]:
        #             self.snet = snet        # source network
        # self.address = address  # address of the router
        # self.dnets = dnets      # list of reachable networks through this router
        # self.status = status    # router status
                z = this_application.nsap.router_info_cache.routers[x][y]
                if network in z.dnets:
                    return z.address
        return ""

    def do_infocache(self, args):
        result = self.infocache(args)
        if len(args.split()) == 1:
            print(result)

    def infocache(self, args):
        """infocache <obj_id> <property> <device>"""
        # print(this_application.smap.deviceInfoCache.dict_contents())
        print(this_application.nsap.router_info_cache.routers)
        if len(args) == 0:
            for x in this_application.nsap.router_info_cache.routers:
                for y in this_application.nsap.router_info_cache.routers[x]:
            #             self.snet = snet        # source network
            # self.address = address  # address of the router
            # self.dnets = dnets      # list of reachable networks through this router
            # self.status = status    # router status
                    z = this_application.nsap.router_info_cache.routers[x][y]
                    print(x, y)
                    print("snet",z.snet)
                    print("address",z.address)
                    print("dnets",z.dnets)
                    # print(this_application.nsap.router_info_cache.routers[x][y].status)
        else:
            args = args.split()
            net = None
            addr = Address(args[0])
            if len(args) == 1:
                result = []
                if None in this_application.nsap.router_info_cache.routers.keys():
                    if addr in this_application.nsap.router_info_cache.routers[None].keys():
                        print(addr, this_application.nsap.router_info_cache.routers[None][addr].dnets)
                        # result = this_application.nsap.router_info_cache.routers[None][addr].dnets.keys()
                        for x in this_application.nsap.router_info_cache.routers[None][addr].dnets:
                            print(x)
                            result.append(x)
                            print(result)
                print("results: {}".format(result))
                return result
            elif len(args) > 2:
                net = int(args[2])
                if args[1] == "add":
                    this_application.nsap.router_info_cache.update_router_info(None, address=addr, dnets=[net])
                if args[1] == "del":
                    #Note: should delete only the nets listed, but deletes all nets.
                    this_application.nsap.router_info_cache.delete_router_info(None, address=addr, dnets=[net])
        return []

    def do_setdopr(self, args):
        """setdopr <obj_id> <property> <device>"""
        if len(args.split()) == 3:
            obj_id, prop_id, dev_id = args.split()
        elif len(args.split()) == 2:
            obj_id, prop_id = args.split()
            dev_id = False
        devObjProRef = DeviceObjectPropertyReference(
            objectIdentifier = ObjectIdentifier(obj_id),
            propertyIdentifier = PropertyIdentifier(prop_id)
            )
        if dev_id:
            devObjProRef.deviceIdentifier = ObjectIdentifier("device:{}".format(dev_id))
        request = WritePropertyRequest(
            objectIdentifier=ObjectIdentifier("schedule:1"),
            propertyIdentifier=PropertyIdentifier("listOfObjectPropertyReferences")
            )
        request.pduDestination = Address(self.get_iut_address())

        # save the value
        request.propertyValue = Any()
        request.propertyValue.cast_in(devObjProRef)
        # make an IOCB
        iocb = IOCB(request)
        if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

        # give it to the application
        this_application.request_io(iocb)

        # wait for it to complete
        iocb.wait()

        # do something for success
        if iocb.ioResponse:
            # should be an ack
            if not isinstance(iocb.ioResponse, SimpleAckPDU):
                if _debug: TestConsoleCmd._debug("    - not an ack")
                return

            sys.stdout.write("ack\n")

        # do something for error/reject/abort
        if iocb.ioError:
            sys.stdout.write(str(iocb.ioError) + '\n')


    def do_program(self,args):
        """program <load|unload|restart> | <send> <filename>"""
        if len(args.split()) == 1:
            self.do_write("program:1 programChange {}".format(args))
        if len(args.split()) == 2:
            args = args.split()
            self.do_sendfile("2 {}".format(args[1]))

    def do_dcc(self, args):
        """dcc addr enable/disable duration [password]"""
        args = args.split()
        addr = None
        password = None
        duration = None
        state =  "enable"
        if len(args) > 0:
            addr = args[0]
        else:
            addr = None
        if len(args) > 1:
            state = args[1]
        if len(args) > 2:
            duration = int(args[2])
        if len(args) > 3:
            password = args[3]
        if addr is not None:
            self.dcc(addr=addr, state=state, duration=duration, password=password)

    def dcc(self, addr=None, state="enable", duration=None, password=None):
        if addr == None:
            addr = self.get_iut_address()
        print("dcc addr={} state={} duration={} password={}".format(addr, state, duration, password))
        state = DeviceCommunicationControlRequestEnableDisable(state)

        request = DeviceCommunicationControlRequest(
        enableDisable = state
        )
        if password is not None:
            request.password = CharacterString(password)
        if duration is not None:
            request.timeDuration = duration
        request.pduDestination = Address(addr)
        iocb = IOCB(request)
        if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

        # give it to the application
        this_application.request_io(iocb)

        # wait for it to complete
        iocb.wait()
        # do something for success
        if iocb.ioResponse:
            # should be an ack
            # if not isinstance(iocb.ioResponse, SimpleAckPDU):
            #     if _debug: Test._debug("    - not an ack")
            #     return
            print(iocb.ioResponse.dict_contents())
            sys.stdout.write("ack\n")
            return "ack"

        # do something for error/reject/abort
        if iocb.ioError:
            sys.stdout.write(str(iocb.ioError) + '\n')
            return str(iocb.ioError)

    def do_rd(self, args):
        """rd addr state [password]"""
        args = args.split()
        addr = None
        password = None
        state =  "warmstart"
        if len(args) > 0:
            addr = args[0]
        else:
            addr = None
        if len(args) > 1:
            state = args[1]
        if len(args) > 2:
            password = args[2]
        if addr is not None:
            self.rd(addr=addr, state=state, password=password)

    def rd(self, addr=None, state="warmstart", password=None):
        if addr == None:
            addr = self.get_iut_address()
        state = ReinitializeDeviceRequestReinitializedStateOfDevice(state)
        request = ReinitializeDeviceRequest(
        reinitializedStateOfDevice = state
        )
        if password is not None:
            request.password =  CharacterString(password)
        request.pduDestination = Address(addr)
        iocb = IOCB(request)
        if _debug: TestConsoleCmd._debug("    - iocb: %r", iocb)

        # give it to the application
        this_application.request_io(iocb)

        # wait for it to complete
        iocb.wait()
        # do something for success
        if iocb.ioResponse:
            # should be an ack
            # if not isinstance(iocb.ioResponse, SimpleAckPDU):
            #     if _debug: TestConsoleCmd._debug("    - not an ack")
            #     return

            sys.stdout.write("ack\n")
            return "ack"

        # do something for error/reject/abort
        if iocb.ioError:
            sys.stdout.write(str(iocb.ioError) + '\n')
            return str(iocb.ioError)

    def do_dcc_rd_test(self, args):
# def dcc(self, addr=self.get_iut_address(), state="enable", duration=None, password=None):
# def rd(self, addr=self.get_iut_address(), state="warmstart", password=None):

        choice = int(args)
        if choice == 0:
            print("dcc")
            self.dcc()
        if choice == 1:
            print("dcc 2:1 enable 32 123adftech123")
            self.dcc(addr=self.get_iut_address(), state="enable", duration=32, password="123adftech123")
        if choice == 2:
            print("dcc 2:1 enable 123adftech123")
            self.dcc(addr="2:1", state="enable", password="123adftech123")
        if choice == 3:
            print("dcc 2:1 disable 32 123adftech123")
            self.dcc(addr="2:1", state="disable", duration=32, password="123adftech123")
        if choice == 4:
            print("dcc 2:1 disable 123adftech123")
            self.dcc(addr="2:1", state="disable", password="123adftech123")
        if choice == 5:
            self.rd(password="123adftech123")

    

    # def do_test_create_variable(self, args):
        
    #     self.read_object_list() #Only show object list
    #     choose_read_type = input("""Please choose the number to the type you wish to CREATE:
    #     1. Binary Value
    #     2. Analog Value
    #     3. Binary Input
    #     4. Analog Input
    #     = """)
    #     if choose_read_type in ['Binary Value','1']:
    #         var_input = int(input("How many BO want to create? : "))

    #         for i in range (1, var_input + 1):
    #             self.do_create(f"binaryValue:{i}")
    #             print("------------------------")

    #     elif choose_read_type in ['Analog Value','2']:
    #         var_input = int(input("How many AV want to create? : "))
    #         for i in range (1, var_input + 1):
    #             self.do_create(f"analogValue:{i}")
    #             print("------------------------")

    #     elif choose_read_type in ['Binary Input','3']:
    #         var_input = int(input("How many BI want to create?(MAX22): "))
    #         for i in range (1, var_input + 1):
    #             self.do_create(f"binaryInput:{i}")
    #             print("------------------------")
        
    #     elif choose_read_type in ['Analog Input','4']:
    #         var_input = int(input("How many AI want to create?(MAX22) : "))
    #         for i in range (1, var_input + 1):
    #             self.do_create(f"analogInput:{i}")
    #             print("------------------------")

    #     else:
    #         print("Please enter Integer number 1,2,3,4,5 and so-on, easy")


    # def delete_auto_no_user(self, value_type, total_items): #This Deletion Function For automatic delete without user input. Just declare function.
    #     for i in range(1, total_items + 1):
    #             self.do_delete(f"{value_type}:{i}")
    #             print(f" Deleted {value_type}:{i}")

    # def delete_values_by_type(self, value_type):

    #     decision_all_or_one = input(f"Do you want to delete all items of type '{value_type}'? (yes/no) :")

    #     if decision_all_or_one == 'yes':
    #         total_items = int(input(f"How many '{value_type}' items do you want to delete? : "))
    #         for i in range(1, total_items + 1):
    #             self.do_delete(f"{value_type}:{i}")
    #             print(f" Deleted {value_type}:{i}")

    #     elif decision_all_or_one == 'no':
    #         item_id = int(input(f"Enter the ID of the {value_type} you want to delete: "))
    #         self.do_delete(f"{value_type}:{item_id}")
    #         print(f"Deleted {value_type}:{item_id}")
    #     else:
    #         print("Invalid input. Please enter 'yes' or 'no'.")

    # def do_test_delete_object(self,args):

    #     #self.read_object_list() #Only show object list, take too much time
    #     print("1. Binary Value")
    #     print("2. Binary Input")
    #     print("3. Analog Value")
    #     print("4. Analog Input")
    #     print("5. Accumulator")
    #     print("6. Positive Integer Value (PIV)")
    #     print("7. Integer Value (IV)")
    #     print("8. Large Analog Value (LAV)")
    #     print("9. Exit")

    #     choose_object_type = int(input(" Please Choose The Object Type To Delete (Integer Num) : "))

    #     if choose_object_type == 1:
    #         self.delete_values_by_type("binaryValue")
    #     elif choose_object_type == 2:
    #         self.delete_values_by_type("binaryInput")
    #     elif choose_object_type == 3:
    #         self.delete_values_by_type("analogValue")
    #     elif choose_object_type == 4:
    #         self.delete_values_by_type("analogInput")
    #     elif choose_object_type == 5:
    #         self.delete_values_by_type("accumulator")
    #     elif choose_object_type == 6:
    #         self.delete_values_by_type("positiveIntegerValue")
    #     elif choose_object_type == 7:
    #         self.delete_values_by_type("integerValue")
    #     elif choose_object_type == 8:
    #         self.delete_values_by_type("largeAnalogValue")
    #     elif choose_object_type == 9:
    #         print("Exit Deletion")
    #     else:
    #         print("Invalid Input")

    # def do_test_auto_delete(self, args):

    #     total_items = 10
    #     self.delete_auto_no_user("binaryValue" ,total_items)

    # def do_test_write_variable(self, args):

    #     self.read_object_data() #List of BACnet Object and presentValue
    #     choose_read_type = input("""Please choose the number corresponding to the type you wish to read:
    #     1. Binary Value
    #     2. Analog Value
    #     5. Binary Output
    #     6. Analog Output
    #     = """)
    #     if choose_read_type in ['Binary Value','1']:
    #         var_input = int(input("How many BV want to write? : "))
    #         same_value = input("Do you want to set all values to the same value? (yes/no): ").lower() == 'yes'
    #         if not same_value:
    #             value_input = None
    #         else:
    #             value_input = input("Type string 'active' (1) or 'inactive' (0) for all value : ")
    #         for i in range (1, var_input+1):
    #             if not same_value:
    #                 value_input = input(f"Type string 'active' (1) or 'inactive' (0) for Binary Value {i}: ")
    #                 self.do_write(f"binaryValue:{i} presentValue {value_input}")
    #             else:    
    #                 self.do_write(f"binaryValue:{i} presentValue {value_input}")

    #     elif choose_read_type in ['Analog Value','2']:
    #         var_input = int(input("How many AV want to write? : "))
    #         same_value = input("Do you want to set all values to the same value? (yes/no): ").lower() == 'yes'
    #         if not same_value:
    #             value_input = 0
    #         else:
    #             value_input = float(input("Enter the value for all analog value: "))

    #         for i in range(1, var_input + 1):
    #             if not same_value:
    #                 #    Prompt the user for the value of each analog value
    #                 value_input = input(f"Enter the value for each analogValue {i}: ")
    #                 self.do_write(f"analogValue:{i} presentValue {value_input}")
    #             else:
    #                 # Use the same value for all analog values
    #                 self.do_write(f"analogValue:{i} presentValue {value_input}")  

    #     if choose_read_type in ['Binary Output','5']:
    #         var_input = int(input("How many BO want to write? : "))
    #         same_value = input("Do you want to set all values to the same value? (yes/no): ").lower() == 'yes'
    #         if not same_value:
    #             value_input = None
    #         else:
    #             value_input = input("Type string 'active' (1) or 'inactive' (0) for all value : ")
    #         for i in range (1, var_input+1):
    #             if not same_value:
    #                 value_input = input(f"Type string 'active' (1) or 'inactive' (0) for Binary Output {i}: ")
    #                 self.do_write(f"binaryOutput:{i} presentValue {value_input}")
    #             else:    
    #                 self.do_write(f"binaryOutput:{i} presentValue {value_input}")

    #     elif choose_read_type in ['Analog Output','6']:
    #         var_input = int(input("How many AO want to write? : "))
    #         same_value = input("Do you want to set all values to the same value? (yes/no): ").lower() == 'yes'
    #         if not same_value:
    #             value_input = 0
    #         else:
    #             value_input = float(input("Enter the value for all analog output: "))

    #         for i in range(1, var_input + 1):
    #             if not same_value:
    #                 #    Prompt the user for the value of each analog value
    #                 value_input = input(f"Enter the value for each analogOutput {i}: ")
    #                 self.do_write(f"analogOutput:{i} presentValue {value_input}")
    #             else:
    #                 # Use the same value for all analog values
    #                 self.do_write(f"analogOutput:{i} presentValue {value_input}")   

    #     else:
    #         print("Only Choose 1 & 2, easy")

    def do_test_read_variable(self, args):

        self.read_object_data()
        
        # self.read_object_list()
        # print(' ')
        # print('test_read_variable')
        # choose_read_type = input(""" \n Please choose the number corresponding to the type you wish to read:
        # 1. Binary Value
        # 2. Analog Value
        # 3. Binary Input
        # 4. Analog Input
        # 5. Binary Output
        # 6. Analog Output
        # = """)
        # if choose_read_type in ['Binary Value','1']:
        #     self.read_object_data()
        #     # for i in range (1, var_input + 1):
        #     #     print(self.read_value(f"binaryValue:{i} presentValue"))
        #     #     print("------------------------")

        # elif choose_read_type in ['Analog Value','2']:
        #     var_input = int(input("How many AV want to read? : "))
        #     for i in range (1, var_input + 1):
        #         print(self.read_value(f"analogValue:{i} presentValue"))
        #         print("------------------------")

        # elif choose_read_type in ['Binary Input','3']:
        #     var_input = int(input("How many BI want to read? : "))
        #     for i in range (1, var_input + 1):
        #         print(self.read_value(f"binaryInput:{i} presentValue"))
        #         print("------------------------")

        # elif choose_read_type in ['Analog Input','4']:
        #     var_input = int(input("How many AI want to read? : "))
        #     for i in range (1, var_input + 1):
        #         print(self.read_value(f"analogInput:{i} presentValue"))
        #         print("------------------------")

        # elif choose_read_type in ['Binary Output','5']:
        #     var_input = int(input("How many BO want to read? : "))
        #     for i in range (1, var_input + 1):
        #         print(self.read_value(f"binaryOutput:{i} presentValue"))
        #         print("------------------------")

        # elif choose_read_type in ['Analog Output','6']:
        #     var_input = int(input("How many AO want to read? : "))
        #     for i in range (1, var_input + 1):
        #         print(self.read_value(f"analogOutput:{i} presentValue"))
        #         print("------------------------")

        # else:
        #     print("Only Choose 1 & 2, easy")

    ## ---------------------------------- ##
        
    def object_mode_set(self, args):
        self.cwrd_mode = {
            1 : self.do_create,
            2 : self.do_write,
            3 : self.do_read,
            4 : self.do_delete
        }
        
    def bacnet_object(self, args):
        self.bacnet_item = {
            1: 'binaryValue',
            2: 'binaryOutput',
            3: 'binaryInput',
            4: 'analogValue',
            5: 'analogOutput',
            6: 'analogInput',
            7: 'accumulator',
            8: 'positiveIntegerValue',
            9: 'integerValue',
            10: 'largeAnalogValue',
        }
    def cwrd_menu_list(self, args):
        self.mode = {
            1: 'create',
            2: 'write',
            3: 'read',
            4: 'delete',
            5: 'AutoTest CWRD object',
            6: 'AutoTest Create Write Read Only'
        }
            
    def do_test_cwrd_section(self, args):    
                                                                                # For CRUD (Create read update/write Delete) choice
        self.bacnet_object(args)                                                # Need to declare function before can use function data
        self.object_mode_set(args)
        self.cwrd_menu_list(args)
        total_items = 0

        for menulist in self.mode.keys():                                       # create a menu list for dictionary cwrd_menu_list, keys only show values
            print(f"{menulist}. {self.mode[menulist].capitalize()}")

        crud_number = int(input("Please Select CWRD mode for Object List: "))

        mode = self.mode.get(crud_number)                                              # data from dictionary cwrd_menu_list
        print(f"{self.mode.get(crud_number).capitalize()} mode")

        if self.mode.get(crud_number) == 'create':                              #self.mode.get(crud_number)  to collect values of dictionary at functions 
            self.cwrd_object(args, self.cwrd_mode[crud_number], mode)
        elif self.mode.get(crud_number) == 'write':
            self.cwrd_object(args, self.cwrd_mode[crud_number], mode)
        elif self.mode.get(crud_number) == 'read':
            self.read_object_data()                                             # no need object_self.mode_set, because read have special method and have table:D
        elif self.mode.get(crud_number) == 'delete':
            all_type_delection = input("All variable type delection or one type deletion [yes/no] : ")
            if all_type_delection == 'yes':
                total_items = int(input("Number to make delection for all type (int num): "))
                self.auto_deletion_object(args, total_items)
            else:
                self.cwrd_object(args, self.cwrd_mode[crud_number], mode)

        elif self.mode.get(crud_number) == 'AutoTest CWRD object':
            total_items = int(input("Please enter number of variable to create? (default = 5)(Enter an Int Num) : "))
            self.auto_cwrd_no_user(args, total_items, mode)
        elif self.mode.get(crud_number) == 'AutoTest Create Write Read Only':
            total_items = 10
            self.auto_cwrd_no_user(args, total_items, mode)

    def cwrd_object(self,args, cwrd_mode, mode):                                #function can be use for different usage

        for menulist in self.bacnet_item.keys():                                       # create a menu list for dictionary cwrd_menu_list, keys only show values
            print(f"{menulist}. {self.bacnet_item[menulist]}")

        choose_object_type = int(input(f"Please Choose The Object Type To {mode.capitalize()} (Integer Num) : "))

        if choose_object_type == 1:
            self.cwrd_values_by_type(self.bacnet_item[choose_object_type] , cwrd_mode ,mode )
        elif choose_object_type == 2:
            self.cwrd_values_by_type(self.bacnet_item[choose_object_type], cwrd_mode, mode)
        elif choose_object_type == 3:
            self.cwrd_values_by_type(self.bacnet_item[choose_object_type], cwrd_mode, mode)
        elif choose_object_type == 4:
            self.cwrd_values_by_type(self.bacnet_item[choose_object_type], cwrd_mode, mode)
        elif choose_object_type == 5:
            self.cwrd_values_by_type(self.bacnet_item[choose_object_type], cwrd_mode, mode)
        elif choose_object_type == 6:
            self.cwrd_values_by_type(self.bacnet_item[choose_object_type], cwrd_mode, mode)
        elif choose_object_type == 7:
            self.cwrd_values_by_type(self.bacnet_item[choose_object_type], cwrd_mode,mode)
        elif choose_object_type == 8:
            self.cwrd_values_by_type(self.bacnet_item[choose_object_type], cwrd_mode, mode)
        elif choose_object_type == 9:
            self.cwrd_values_by_type(self.bacnet_item[choose_object_type], cwrd_mode, mode)
        elif choose_object_type == 10:
            self.cwrd_values_by_type(self.bacnet_item[choose_object_type], cwrd_mode, mode)
        elif choose_object_type == 11:
            print("Exit CWRD OR CRUD :D")
        else:
            print("Invalid Input")


    def cwrd_values_by_type(self, value_type, cwrd_mode, mode): #
        object_values = " "
        values_status = " "
        
        decision_all_or_one = input(f"Do you want to {mode.capitalize()} all items of type '{value_type}'? (yes/no) :")

        if decision_all_or_one == 'yes':
            total_items = int(input(f"How many '{value_type}' items do you want to {mode.capitalize()}? : "))
            if mode == 'write':
                object_values = input("Please enter the value: ")
                values_status = 'presentValue'
            for i in range(1, total_items + 1):
                cwrd_mode(f"{value_type}:{i} {values_status} {object_values}")
                print(f"{mode.capitalize()} {value_type} {i} {values_status} {object_values}")

        elif decision_all_or_one == 'no':
            if mode == 'write':
                object_values = input("Please enter the value: ") 
                values_status = 'presentValue'
            item_id = int(input(f"Enter the ID of the {value_type} you want to {mode.capitalize()}: "))
            cwrd_mode(f"{value_type}:{item_id} {values_status} {object_values}")
            print(f"{mode.capitalize()} {value_type} {item_id} {values_status} {object_values}")
        else:
            print("Invalid input. Please enter 'yes' or 'no'.")
    ## ---------------------------------- ##
    
    def auto_cwrd_no_user(self, args, total_items, mode):                       # Auto Create Read Write Delete system
        Test_name = mode                                                                                              
        for value_type in self.bacnet_item.values():                            #call bacnet_item which is have 8 value_type.
            for i in range (1 , total_items + 1):                               # based on what total_object want to create
                self.do_create(f"{value_type}:{i}")
                if value_type in ['binaryValue', 'binaryInput' , 'binaryOutput']: #binaryValue and binaryInput presentvalue only accept active or inactive instead of number.
                    self.do_write(f"{value_type}:{i} presentValue active")
                else:
                    self.do_write(f"{value_type}:{i} presentValue 100")

        self.read_object_data() 
                                                        # no need object_self.mode_set, because read have special method and have table:D
        input("All of the 10 type are created and write ?\nProcess to Delete Object: \n")
        
        if mode == 'AutoTest CWRD object':                                      # Add on if have another test ex: ['AutoTest CWRD object', 'Autodes']
            self.auto_deletion_object(args, total_items)                        #This Deletion Function For automatic CRUD System 
            self.read_object_data()
            print(f"Deletion complete for {total_items} variable")
        else:
            print(f"Need Manual Deletion for {Test_name}")
        validity_response(Test_name)

    def auto_deletion_object(self, args, total_items):
        self.auto_write_for_output(args, total_items)
        for value_type in self.bacnet_item.values():                            #call bacnet_item which is have 8 value_type.
            for i in range (1 , total_items + 1):                               #total_items can be customized
                self.do_delete(f"{value_type}:{i}")
        
    def auto_write_for_output(self, args, total_items):
        for value_type in self.bacnet_item.values():                            #call bacnet_item which is have 8 value_type.
            if value_type == 'binaryOutput':
                for i in range (1 , total_items + 1):                               #total_items can be customized
                    self.do_write(f"{value_type}:{i} presentValue inactive")
            elif value_type == 'analogOutput':
                for i in range (1 , total_items + 1): 
                    self.do_write(f"{value_type}:{i} presentValue 0")

        

    ## ----------------------------------- ##

    def do_test_monkey_test(self, args):
        choose_read_type = input("""Please choose the number to Monkey Test (Random up to 2048 Object):
        1. Binary Value
        2. Analog Value
        3. Binary Output 
        4. Binary Output 2
        5. Analog Output
        = """)
        if choose_read_type in ['Binary Value','1']:
            var_input = random.randint(0,200)
            print (f"Number of random = {var_input}")

            for i in range (1, var_input + 1):
                self.do_create(f"binaryValue:{i}")
                rand1 = ['inactive' , 'active']
                random_output = random.choice(rand1)
                self.do_write(f"binaryValue:{i} presentValue {random_output}")
                print("------------------------")
            print("please see at ADf WEBPAGE :D")
            input("Already See the value at Webpage? Ready to Delete? Press Any Keys : ")
            input("Are you sure? Press Any Keys : ")
            for i in range (1, var_input + 1):
                self.do_delete(f"binaryValue:{i}")
                print("------------------------")

            print(">>Monkey (Random) BIN VAL Test Completed<<")
            print("------------------------")

        elif choose_read_type in ['Analog Value','2']:
            var_input = random.randint(0,200)
            print (f"Number of random = {var_input}")
            
            for i in range (1, var_input + 1):
                self.do_create(f"analogValue:{i}")
                print("------------------------")
                random_output = random.randint(0,30)
                self.do_write(f"analogValue:{i} presentValue {random_output}")

            print("please see at ADf WEBPAGE :D")
            input("Already See the value at Webpage? Ready to Delete? Press Any Keys ")
            input("Are you sure? Press Any Keys ")

            for i in range (1, var_input + 1):
                self.do_delete(f"analogValue:{i}")
                print("------------------------")

            print(">>Monkey (Random) ANA VAL Test Completed<<")
            print("------------------------")

        elif choose_read_type in ['Binary Output','3']:
            TO_TEST_ROUND = 2
            MAX_TO = 10
            retry = True

            while retry == True:
                for x in range(0, TO_TEST_ROUND):
                    for i in range(1, MAX_TO + 1): 
                        # Turn on each LED one by one
                        self.do_write(f"binaryOutput:{i} presentValue active")
                        time.sleep(delaytime/1000)
                        print("------------------------")
                        # Delay for 1 second

                    for i in range(MAX_TO, 0,-1): # Turn off each LED one by one
                        self.do_write(f"binaryOutput:{i} presentValue inactive")
                        time.sleep(delaytime/1000) 
                        print("------------------------")
                        # Delay for 1 second
                    
            
                print(">>BIN OUT TEST 1 COMPLETED<<")
                print("------------------------")
                retry = False

        elif choose_read_type in ['Binary Output 2','4']:
            MAX_TO = 10
            retry = True
            TO_TEST_ROUND = 2

            random_output1 = None
            random_sleep = random.randint(0,100)
            while retry == True:
                led_states = [random.choice([True, False]) for _ in range(MAX_TO)]

                for x in range(0, TO_TEST_ROUND):
                    for i in range(1, MAX_TO + 1):  
                        # Toggle each LED one by one
                        # Toggle the state of the current LED
                        led_states[i - 1] = not led_states[i - 1]
                        state = 'active' if led_states[i - 1] else 'inactive'
                        self.do_write(f"binaryOutput:{i} presentValue {state}")
                        time.sleep(random_sleep/ 1000)  
                        # Delay for 1 millisecond
                        print("------------------------")

                    # Toggle the state of the next stage's LED
                    for i in range(1, MAX_TO):  
                        # Exclude the last LED as there's no "next stage" for it
                        # Toggle the state of the next stage's LED
                        led_states[i] = not led_states[i]
                        state = 'active' if led_states[i] else 'inactive'
                        self.do_write(f"binaryOutput:{i + 1} presentValue {state}")
                        time.sleep(random_sleep / 1000)  
                        # Delay for 1 millisecond
                        print("------------------------")

                # Ensure all LEDs are turned off at the end
                for i in range(1, MAX_TO + 1):
                    self.do_write(f"binaryOutput:{i} presentValue inactive")
                    time.sleep(1 / 1000)  
                    # Delay for 1 millisecond
                print(">>BIN OUT TEST 2 COMPLETED<<")
                print("------------------------")
                retry = False
            
                
        elif choose_read_type in ['Analog Output','5']:
            var_input = random.randint(0,4)
            print (f"Number of random = {var_input}")
            
            for i in range (1, var_input + 1):
                self.do_create(f"analogOutput:{i}")
                print("------------------------")
                random_output = random.randint(0,30)
                self.do_write(f"analogOutput:{i} presentValue {random_output}")

            print("please see at ADf WEBPAGE :D")
            input("Already See the value at Webpage? Ready to RESET VALUE TO 0? Press Any Keys ")
            input("Are you sure? Press Any Keys ")
            
            for i in range (1, var_input + 1):
                self.do_write(f"analogOutput:{i} presentValue 0")
                print("------------------------")

            print(">>Monkey (Random) ANA OUTPUT Test Completed<<")
            print("------------------------")

        else:
            print("Only Choose 1 & 2, easy")

    # def do_mbstart(self,args):
    #     self.do_webPATCH('xt/serial/2/modbus {"command":"start"}')

    # def do_mbstop(self,args):
    #     self.do_webPATCH('xt/serial/2/modbus {"command":"stop"}')

    def do_test_rtu_p1_addModbus(self,args):
        #stop modbus before add Object List
        #self.do_webPATCH('xt/serial/2/modbus/stop {}')

        #X1 as a Master
        #self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"abc008","bacnet_id":8,"device_id":1,"address":1,"format_str":"Int32","order_str":"CDAB","type":"Register","poll_interval":1}')
        #self.do_webPOST('xt/serial/2/modbus/list {"address":100,"format_str":"Uint32","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":1}')
        Test_name = "Modbus RTU Port 1"
        self.do_webPATCH('xt/serial/2/modbus {"command":"stop"}')
        sleep(1)
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"ButtonUI2&T06","bacnet_id":207,"device_address":"1:1","address":3,"format_str":"Bit","order_str":"ABCD","type":"Bit","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"ButtonLB50004","bacnet_id":204,"device_address":"1:1","address":50004,"format_str":"Bit","order_str":"ABCD","type":"Bit","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"TempLW50001","bacnet_id":201,"device_address":"1:1","address":50001,"format_str":"Float","order_str":"BADC","type":"Register","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"Input202","bacnet_id":202,"device_address":"1:1","address":50002,"format_str":"Float","order_str":"BADC","type":"Register","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"Input206","bacnet_id":206,"device_address":"1:1","address":6,"format_str":"Float","order_str":"BADC","type":"Register","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"InputLW11","bacnet_id":210,"device_address":"1:1","address":11,"format_str":"Uint32","order_str":"BADC","type":"Register","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"LW14Display","bacnet_id":211,"device_address":"1:1","address":14,"format_str":"Uint32","order_str":"BADC","type":"Register","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"InputLW12","bacnet_id":212,"device_address":"1:1","address":12,"format_str":"Int32","order_str":"BADC","type":"Register","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"LW13Display","bacnet_id":213,"device_address":"1:1","address":13,"format_str":"Int32","order_str":"BADC","type":"Register","poll_interval":1}')
        sleep(1)
        self.do_webPATCH('xt/serial/2/modbus {"command":"start"}')
        print(" ")
        validity_response(Test_name)    
        #X1 as a Slave
        #Bacnet Object AI = 0 AO = 1 AV = 2 BI = 3 BO= 4 BV = 5 ACC = 6 IV = 7 LAV = 8 PIV = 9
        # self.do_webPOST('xt/serial/2/modbus/list {"address":101,"format_str":"Bit","order_str":"ABCD","type":"Bit","bacnet_object":4,"bacnet_property":85,"bacnet_id":2}')
        # self.do_webPOST('xt/serial/2/modbus/list {"address":104,"format_str":"Bit","order_str":"ABCD","type":"Bit","bacnet_object":4,"bacnet_property":85,"bacnet_id":3}')
        # self.do_webPOST('xt/serial/2/modbus/list {"address":106,"format_str":"Float","order_str":"BADC","type":"Register","bacnet_object":2,"bacnet_property":85,"bacnet_id":4}')
        # self.do_webPOST('xt/serial/2/modbus/list {"address":108,"format_str":"Float","order_str":"BADC","type":"Register","bacnet_object":2,"bacnet_property":85,"bacnet_id":1}')

        #self.do_webPATCH('xt/serial/2/modbus/start {}')

    def do_test_rtu_p2_addModbus(self,args):
        Test_name = "Modbus RTU Port 2"
        self.do_webPATCH('xt/serial/2/modbus {"command":"stop"}')
        sleep(1)
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"ButtonUI2&T06","bacnet_id":207,"device_address":"1","address":3,"format_str":"Bit","order_str":"ABCD","type":"Bit","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"ButtonLB50004","bacnet_id":204,"device_address":"1","address":50004,"format_str":"Bit","order_str":"ABCD","type":"Bit","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"TempLW50001","bacnet_id":201,"device_address":"1","address":50001,"format_str":"Float","order_str":"BADC","type":"Register","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"Input202","bacnet_id":202,"device_address":"1","address":50002,"format_str":"Float","order_str":"BADC","type":"Register","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"Input206","bacnet_id":206,"device_address":"1","address":6,"format_str":"Float","order_str":"BADC","type":"Register","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"InputLW11","bacnet_id":210,"device_address":"1","address":11,"format_str":"Uint32","order_str":"BADC","type":"Register","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"LW14Display","bacnet_id":211,"device_address":"1","address":14,"format_str":"Uint32","order_str":"BADC","type":"Register","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"InputLW12","bacnet_id":212,"device_address":"1","address":12,"format_str":"Int32","order_str":"BADC","type":"Register","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"LW13Display","bacnet_id":213,"device_address":"1","address":13,"format_str":"Int32","order_str":"BADC","type":"Register","poll_interval":1}')
        sleep(1)
        self.do_webPATCH('xt/serial/2/modbus {"command":"start"}')
        print(" ")
        validity_response(Test_name) 

    def do_test_tcp_addModbus(self,args):
        Test_name = "Modbus TCP/IP"
        #stop modbus before add Object List
        #self.do_webPATCH('xt/serial/2/modbus/stop {}')

        #X1 as a Master
        #self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"abc008","bacnet_id":8,"device_id":1,"address":1,"format_str":"Int32","order_str":"CDAB","type":"Register","poll_interval":1}')
        #self.do_webPOST('xt/serial/2/modbus/list {"address":100,"format_str":"Uint32","order_str":"BADC","type":"Register","bacnet_object":1,"bacnet_property":85,"bacnet_id":1}')
        self.do_webPATCH('xt/serial/2/modbus {"command":"stop"}')
        sleep(1)
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"ButtonUI2&T06","bacnet_id":307,"device_address":"192.168.1.108:8000","address":3,"format_str":"Bit","order_str":"ABCD","type":"Bit","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"ButtonLB50004","bacnet_id":304,"device_address":"192.168.1.108:8000","address":50004,"format_str":"Bit","order_str":"ABCD","type":"Bit","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"TempLW50001","bacnet_id":301,"device_address":"192.168.1.108:8000","address":50001,"format_str":"Float","order_str":"BADC","type":"Register","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"Input202","bacnet_id":302,"device_address":"192.168.1.108:8000","address":50002,"format_str":"Float","order_str":"BADC","type":"Register","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"Input206","bacnet_id":306,"device_address":"192.168.1.108:8000","address":6,"format_str":"Float","order_str":"BADC","type":"Register","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"InputLW11","bacnet_id":310,"device_address":"192.168.1.108:8000","address":11,"format_str":"Uint32","order_str":"BADC","type":"Register","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"LW14Display","bacnet_id":311,"device_address":"192.168.1.108:8000","address":14,"format_str":"Uint32","order_str":"BADC","type":"Register","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"InputLW12","bacnet_id":312,"device_address":"192.168.1.108:8000","address":12,"format_str":"Int32","order_str":"BADC","type":"Register","poll_interval":1}')
        self.do_webPOST('xt/serial/2/modbus/list {"bacnet_name":"LW13Display","bacnet_id":313,"device_address":"192.168.1.108:8000","address":13,"format_str":"Int32","order_str":"BADC","type":"Register","poll_interval":1}')
        sleep(1)
        self.do_webPATCH('xt/serial/2/modbus {"command":"start"}')
        print(" ")
        validity_response(Test_name)

    def do_test_modbus_function(self, args):
        Test_name = "Test Modbus"
        self.do_webPATCH('xt/serial/2/modbus {"command":"stop"}')
        self.do_webPATCH('xt/serial/2/modbus/test {"baud_rate":9600,"parity":78,"data_bits":8,"stop_bits":1,"device_address":"1:1","address":50004,"format_str":"Bit","order_str":"ABCD","type":"Bit","count":1,"poll_interval":1}')
        self.do_webPATCH('xt/serial/2/modbus/test {"baud_rate":9600,"parity":78,"data_bits":8,"stop_bits":1,"device_address":"1:1","address":6,"format_str":"Float","order_str":"BADC","type":"Register","count":1,"poll_interval":1}') 
        self.do_webPATCH('xt/serial/2/modbus/test {"baud_rate":9600,"parity":78,"data_bits":8,"stop_bits":1,"device_address":"1:1","address":12,"format_str":"Int32","order_str":"BADC","type":"Register","count":1,"poll_interval":1}')
        self.do_webPATCH('xt/serial/2/modbus/test {"baud_rate":9600,"parity":78,"data_bits":8,"stop_bits":1,"device_address":"1:1","address":11,"format_str":"Uint32","order_str":"BADC","type":"Register","count":1,"poll_interval":1}')
        self.do_webPATCH('xt/serial/2/modbus/test {"baud_rate":9600,"parity":78,"data_bits":8,"stop_bits":1,"device_address":"1:1","address":50002,"format_str":"Float","order_str":"BADC","type":"Register","count":1,"poll_interval":1}') 
        print("Please verify if the values at addresses 50004, 6, 12, 11, and 50002 on D1 are the same as in the test")
        validity_response(Test_name)

        self.do_webPATCH('xt/serial/2/modbus/test {"baud_rate":9600,"parity":78,"data_bits":8,"stop_bits":1,"device_address":"1:1","address":50002,"format_str":"Float","value":35,"order_str":"BACD","type":"Register","count":1,"poll_interval":1,"write":True}')
        self.do_webPATCH('xt/serial/2/modbus/test {"baud_rate":9600,"parity":78,"data_bits":8,"stop_bits":1,"device_address":"1:1","address":50004,"format_str":"Bit","value":1,"order_str":"ABCD","type":"Bit","count":1,"poll_interval":1,"write":True}')
        self.do_webPATCH('xt/serial/2/modbus/test {"baud_rate":9600,"parity":78,"data_bits":8,"stop_bits":1,"device_address":"1:1","address":6,"format_str":"Float","value":35,"order_str":"BACD","type":"Register","count":1,"poll_interval":1,"write":True}')
        
        print(" ")
        print("Please verify if the values at addresses 50004, 6, and 50002 on D1 are the same as in the test")
        print(">>Test Function has been completed<<")

    def do_test_DeleteModbusList(self, args):
        #stop modbus before add Object List
        #self.do_webPATCH('xt/serial/2/modbus/stop {}')
        """webDELETE <path> <json_payload>"""
        var_input = int(input("How many Modbus List want to Delete? : "))
        for i in range(1,var_input):
            self.do_webDELETE('xt/serial/2/modbus/list {"index":0}')
        # self.do_webGET('xt/serial/2/modbus/list')
            
    def do_test_create_report(self, args):
        data_list = []
        data_list = self.read_object_data_no_table()
        generate_objectlist_report(data_list)

        print(">> Generate Report Completed <<")
    
def generate_objectlist_report(data_list):

    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Arial", size=16)
    pdf.cell(200, 10, txt="ADF Technology", ln=True, align="C")
    pdf.cell(200, 10, txt= current_date , ln=True, align="C")
    pdf.ln(10)
    
    # Table header
    pdf.set_font("Arial", size=11)                  # Set font for the content
    pdf.cell(60, 10, txt="Object", border=1)
    pdf.cell(40, 10, txt="Present Value", border=1)
    pdf.ln()

    # print("for step")
    # for item in data_list:
    #     text = f"{item[0]}: {item[1]}"
    #     pdf.cell(200, 10, txt=text, ln=True)
    # print("after end step")

    data_list_str = [[item[0], str(item[1])] if isinstance(item[1], float) else item for item in data_list]
    
    # Table data
    for item in data_list:
        pdf.cell(60, 10, txt= item[0], border=1)
        pdf.cell(40, 10, txt= f"{item[1]}", border=1)
        pdf.ln()                                   # Add a line break
    
    # Save PDF to file
    output_file = "X1_report_test.pdf"
    pdf.output(output_file)
    #print("end step")

def validity_response(Test_name):

    if Test_name == "Test Modbus":
        input(f"Please validate if the {Test_name} is working. Please any keys to continue: ")
    else:
        print(f"{Test_name} Test has been completed")

def check_response2():
    exit_program = False

    while True:
        user_input = input("Enter 'yes' to continue, 'exit' to quit: ").lower()
        
        if user_input == 'exit':
            print("Exiting the program.")
            return True
        elif user_input == 'yes':
            print("You entered 'yes'.")
            return False
        else:
            print("Invalid input. Please enter 'yes', 'no', or 'exit'.")
    
def title():
    text = "Anshari"
    ascii_art = pyfiglet.figlet_format(text)
    print(ascii_art)
    print("=====================================")
    print("X1 & X1 Lite Software Automation Test")
    print("=====================================")

    # def do_test_delete_object(self, args):
    #     for i in range(1,32+1):   
    #         self.do_delete("binaryValue:{}".format(i))
    #     # for i in range(1,2048+1):
    #     #   self.do_create("analogValue:{}".format(i))
    #         # self.do_create("binaryValue:{}".format(i))
    #         # self.do_create("positiveIntegerValue:{}".format(i))
    #         # self.do_create("integerValue:{}".format(i))
    #         # self.do_create("largeAnalogValue:{}".format(i))
    #         """write <type> <inst> <prop> <value> [ <indx> ] [ <priority> ]"""
        

#
#   __main__
#

def main():
    
    title()
    global this_application
    global default_BTL_addresses
    # parse the command line arguments
    args = ConfigArgumentParser(description=__doc__).parse_args()

    if _debug: _log.debug("initialization")
    if _debug: _log.debug("    - args: %r", args)

    # make a device object
    this_device = LocalDeviceObject(ini=args.ini)
    if _debug: _log.debug("    - this_device: %r", this_device)

    # make a simple application

    this_application = WhoIsIAmApplication(this_device, args.ini.address)
    default_BTL_addresses = args.ini.btl_list.split()
    print (default_BTL_addresses)

    # make a console
    this_console = TestConsoleCmd()
    if _debug: _log.debug("    - this_console: %r", this_console)

    # enable sleeping will help with threads
    enable_sleeping()

    _log.debug("running")

    run()

    _log.debug("fini")

if __name__ == "__main__":
    main()
