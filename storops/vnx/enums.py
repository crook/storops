# coding=utf-8
# Copyright (c) 2015 EMC Corporation.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
from __future__ import unicode_literals

import logging
import re

import six

from storops.lib.common import Enum, cache, JsonPrinter

log = logging.getLogger(__name__)


def to_hex(number):
    h = hex(number)
    if h.endswith('L'):
        h = h[:-1]
    return h


class VNXEnum(JsonPrinter, Enum):
    def _get_properties(self, dec=0):
        return {'value': self.value}

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value


class VNXSPEnum(VNXEnum):
    SP_A = 'SP A'
    SP_B = 'SP B'
    CONTROL_STATION = 'Celerra'

    @classmethod
    def get_int_index(cls):
        return None, cls.SP_A, cls.SP_B, cls.CONTROL_STATION

    @classmethod
    @cache
    def get_to_remove(cls):
        return re.compile('[_. ]')

    @classmethod
    def is_sp(cls, name):
        name = cls.parse(name)
        return name in (cls.SP_A, cls.SP_B)

    @classmethod
    def _normalize(cls, value):
        ret = re.sub(cls.get_to_remove(), '', value)
        if ret is None:
            pass
        elif ret.endswith('a') and not ret.endswith('rra'):
            ret = 'spa'
        elif ret.endswith('b'):
            ret = 'spb'
        elif ret == 'cs':
            ret = 'celerra'
        return ret

    @classmethod
    def from_str(cls, value):
        value = value.lower()
        value = cls._normalize(value)
        ret = None
        for item in cls.get_all():
            if cls._normalize(item.value.lower()) in value:
                ret = item
                break
        else:
            log.warn('cannot parse "{}" to a vnx sp.'.format(value))
        return ret

    @classmethod
    def get_sp_index(cls, value):
        value = cls.parse(value)
        if value is None:
            raise ValueError('"{}" is not a valid sp name.'.format(value))
        return value.value.lower()[-1]


class VNXProvisionEnum(VNXEnum):
    # value of spec "provisioning:type"
    THIN = 'thin'
    THICK = 'thick'
    COMPRESSED = 'compressed'
    DEDUPED = 'deduplicated'

    @classmethod
    def get_option_map(cls):
        return {
            cls.THIN: ['-type', 'Thin'],
            cls.THICK: ['-type', 'NonThin'],
            cls.COMPRESSED: ['-type', 'Thin'],
            cls.DEDUPED: ['-type', 'Thin', '-deduplication', 'on']}


class VNXCompressionRate(VNXEnum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'


class VNXTieringPreference(VNXEnum):
    INVALID = 0
    NONE = 1
    LOWEST_AVAILABLE = 2
    HIGHEST_AVAILABLE = 3


class VNXRelocationPolicy(VNXEnum):
    INVALID = 0
    NONE = 1
    TIER_PREFERENCE = 2
    OPTIMAL = 3


class VNXMigrationRate(VNXEnum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    ASAP = 'asap'


class VNXTieringEnum(VNXEnum):
    NONE = 'none'
    HIGH_AUTO = 'starthighthenauto'
    AUTO = 'auto'
    HIGH = 'highestavailable'
    LOW = 'lowestavailable'
    NO_MOVE = 'nomovement'

    @classmethod
    def get_option_map(cls):
        return {
            cls.NONE: [],
            cls.HIGH_AUTO: [
                '-initialTier', 'highestAvailable',
                '-tieringPolicy', 'autoTier'],
            cls.AUTO: [
                '-initialTier', 'optimizePool',
                '-tieringPolicy', 'autoTier'],
            cls.HIGH: [
                '-initialTier', 'highestAvailable',
                '-tieringPolicy', 'highestAvailable'],
            cls.LOW: [
                '-initialTier', 'lowestAvailable',
                '-tieringPolicy', 'lowestAvailable'],
            cls.NO_MOVE: [
                '-initialTier', 'optimizePool',
                '-tieringPolicy', 'noMovement']
        }

    @classmethod
    def get_tier(cls, initial, policy):
        ret = None
        for k, v in cls.get_option_map().items():
            if len(v) >= 4:
                v_initial, v_policy = v[1], v[3]
                if (cls.match_option(initial, v_initial) and
                        cls.match_option(policy, v_policy)):
                    ret = k
                    break
                elif cls.match_option(policy, 'noMovement'):
                    """no movement could have different initial tier"""
                    ret = cls.NO_MOVE
                    break
        if ret is None:
            raise ValueError('Initial tier: {}, policy: {} is not valid.'
                             .format(initial, policy))
        return ret

    @staticmethod
    def match_option(output, option):
        return output.replace(' ', '').lower() == option.lower()


class VNXError(VNXEnum):
    GENERAL_NOT_FOUND = ('cannot find|'
                         'may not exist|'
                         'does not exist|'
                         'cannot be found')

    SP_NOT_AVAILABLE = ('^Error.*Message.*End of data stream.*|'
                        '.*Message.*connection refused.*|'
                        '^Error.*Message.*Service Unavailable.*|'
                        '^A network error occurred while trying to connect.*|'
                        '^Exception: Error occurred because of time out\s*')
    NOT_A_SP = ('.*CLI commands are not supported '
                'by the target storage system.*')

    SG_NAME_IN_USE = 'Storage Group name already in use'
    SG_LUN_ALREADY_EXISTS = ('LUN already exists in the '
                             'specified storage group|'
                             'Requested LUN has already '
                             'been added to this Storage Group')
    SG_HOST_LUN_NOT_EXISTS = 'No such Host LUN in this Storage Group'
    SG_HOST_LUN_USED = ('Requested Host LUN Number already in use|'
                        'LUN mapping still exists')

    LUN_ALREADY_EXPANDED = 0x712d8e04
    LUN_EXPAND_ERROR_SIZE = 0x712d8e04
    LUN_NAME_IN_USE = 0x712d8d04
    LUN_IS_PREPARING = 0x712d8e0e
    LUN_IN_SG = 'contained in a Storage Group|LUN mapping still exists'
    LUN_NOT_MIGRATING = ('The specified source LUN is '
                         'not currently migrating')
    LUN_IS_NOT_SMP = 'it is not a snapshot mount point'
    LUN_IN_CG = 0x716d8025

    COMPRESSION_ALREADY_ENABLED = 'already turned on'

    CG_IS_DELETING = 0x712d8801
    CG_EXISTED = 0x716d8021
    CG_SNAP_NAME_EXISTED = 0x716d8005
    CG_NOT_FOUND = "Cannot find the consistency group"

    SNAP_NAME_IN_USE = 0x716d8005
    SNAP_ATTACHED = 0x716d8003
    SNAP_ALREADY_MOUNTED = 0x716d8055
    SNAP_NOT_ATTACHED = ('The specified Snapshot mount point '
                         'is not currently attached.')

    MIGRATION_TGT_NOT_READY = 'not available for migration'

    NAS_GENERAL_ERROR = 13690601492

    INVALID_VDM_ID = 14227341325
    VDM_EXIST = 13421840550
    INVALID_MOVER_ID = 14227341323

    FS_NOT_FOUND = 18522112101
    FS_EXIST = 13691191325

    FS_SNAP_EXIST = 13690535947

    MOVER_INTERFACE_NAME_EXIST = 13421840550
    MOVER_INTERFACE_EXIST = 13691781136
    MOVER_INTERFACE_INVALID_VLAN_ID = 13421850371
    MOVER_INTERFACE_NON_EXISTANCE = 13691781134
    MOVER_INTERFACE_NOT_ATTACHED = 'not currently attached'

    JOIN_DOMAIN = 13157007726
    UNJOIN_DOMAIN = 13157007723

    @classmethod
    def _match(cls, output, error_code):
        is_match = False
        if isinstance(error_code, cls):
            error_code = error_code.value

        if isinstance(error_code, six.integer_types):
            error_code = to_hex(error_code)

        if hasattr(output, 'message'):
            output = output.message
        elif hasattr(output, 'why'):
            # for EvError
            output = getattr(output, 'why')
        elif hasattr(output, 'hex_problem_message_codes'):
            codes = getattr(output, 'hex_problem_message_codes')
            output = ' '.join(codes)
        else:
            try:
                output = output.get('why')
            except AttributeError:
                pass

        if isinstance(error_code, six.string_types):
            error_code = error_code.strip()
            flags = re.IGNORECASE | re.MULTILINE | re.DOTALL
            found = re.findall(error_code, output,
                               flags=flags)
            is_match = len(found) > 0

        return is_match

    @classmethod
    def has_error(cls, output, *error_codes):
        if error_codes is None or len(error_codes) == 0:
            error_codes = VNXError.get_all()
        return any([cls._match(output, error_code)
                    for error_code in error_codes])

    @classmethod
    def sp_not_available(cls, out):
        return len(out) < 500 and has_error(out, cls.SP_NOT_AVAILABLE)


def has_error(output, *error_codes):
    return VNXError.has_error(output, *error_codes)


def raise_if_err(out, ex_clz=None, msg=None, expected_error=None):
    def on_error():
        log.error(msg)
        raise ex_clz(msg)

    if msg is None:
        if hasattr(out, 'get_status_msg'):
            msg = out.get_status_msg()
        else:
            msg = out
    else:
        msg = '{}  detail:\n{}'.format(msg, out)
    if ex_clz is None:
        ex_clz = ValueError
    if not expected_error:
        # check if out is empty
        if out is not None and len(out) > 0:
            on_error()
    else:
        if not isinstance(expected_error, (list, tuple)):
            expected_error = [expected_error]
        if has_error(out, *expected_error):
            on_error()


class VNXPortType(VNXEnum):
    FC = 'FC'
    ISCSI = 'iSCSI'
    FCOE = 'FCoE'
    SAS = 'SAS'
    ETHERNET = 'ethernet'
    OTHER = 'other'

    @classmethod
    def get_int_index(cls):
        return None, cls.FC, cls.ISCSI, cls.FCOE, cls.SAS


class VNXSnapType(VNXEnum):
    LUN = 1
    CG = 2


class VNXMirrorViewRecoveryPolicy(VNXEnum):
    MANUAL = 'manual'
    AUTO = 'automatic'

    @classmethod
    def get_option_map(cls):
        return {
            cls.MANUAL: ['-recoverypolicy', 'manual'],
            cls.AUTO: ['-recoverypolicy', 'auto']
        }


class VNXMirrorViewSyncRate(VNXEnum):
    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'


class VNXLunType(VNXEnum):
    THIN = 'Thin'
    NON_THIN = 'NonThin'
    SNAP = 'Snap'
    SNAP_MOUNT_POINT = 'Snap'
    COMPRESSED = 'Compressed'
    NON_COMPRESSED = 'NonCompressed'
    DEDUPED = 'Deduped'
    NON_DEDUPED = 'NonDeduped'


class VNXRaidType(VNXEnum):
    RAID0 = 'r0'
    RAID1 = 'r1'
    RAID2 = 'r2'
    RAID3 = 'r3'
    RAID4 = 'r4'
    RAID5 = 'r5'
    RAID6 = 'r6'
    RAID10 = 'r1_0'


class VNXPoolRaidType(VNXEnum):
    RAID5 = 'r_5'
    RAID6 = 'r_6'
    RAID10 = 'r_10'


class VNXAccessLevel(VNXEnum):
    RW = 'rw'
    RO = 'ro'
    ACCESS = 'access'
    ROOT = 'root'


class VNXShareType(VNXEnum):
    NFS = 'nfs'
    CIFS = 'cifs'
