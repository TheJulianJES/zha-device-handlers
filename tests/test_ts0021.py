"""Tests for TS0021 quirks."""

from unittest import mock

import pytest
from zigpy.profiles import zha
import zigpy.types as t

import zhaquirks
from zhaquirks.const import (
    ATTRIBUTE_ID,
    ATTRIBUTE_NAME,
    COMMAND_ATTRIBUTE_UPDATED,
    VALUE,
)
from zhaquirks.tuya import TuyaNewManufCluster
import zhaquirks.tuya.ts0021
from zhaquirks.tuya.ts0021 import ATTR_BTN_1_PRESSED, ATTR_BTN_2_PRESSED, TS0021

zhaquirks.setup()

# Tuya ZCL packet structure:
#   ZCL header: frame_ctrl=0x09, seq=0x00, cmd=0x02 (set_data_response)
#   TuyaCommand: status=0x00, tsn=0x00
#   TuyaDatapoint: dp(1), dp_type=0x04 (ENUM), function=0x00, len=0x01, value(1)
#
# DP 1 = btn_1_pressed, DP 2 = btn_2_pressed
# Values: 0=short press, 1=double press, 2=long press
_ZCL_HDR = b"\x09\x00\x02\x00\x00"
_ENUM_TYPE = b"\x04\x00\x01"


def _tuya_pkt(dp: int, value: int) -> bytes:
    return _ZCL_HDR + bytes([dp]) + _ENUM_TYPE + bytes([value])


@pytest.mark.parametrize(
    "packet, expected_attr, expected_value",
    [
        (_tuya_pkt(1, 0), ATTR_BTN_1_PRESSED, 0),
        (_tuya_pkt(1, 1), ATTR_BTN_1_PRESSED, 1),
        (_tuya_pkt(1, 2), ATTR_BTN_1_PRESSED, 2),
        (_tuya_pkt(2, 0), ATTR_BTN_2_PRESSED, 0),
        (_tuya_pkt(2, 1), ATTR_BTN_2_PRESSED, 1),
        (_tuya_pkt(2, 2), ATTR_BTN_2_PRESSED, 2),
    ],
)
async def test_ts0021_zha_events(
    zigpy_device_from_quirk, packet, expected_attr, expected_value
):
    """Test that TuyaCustomCluster emits ZHA events via EventableCluster on button presses."""
    device = zigpy_device_from_quirk(TS0021)
    device._packet_debouncer.filter = mock.MagicMock(return_value=False)

    cluster = device.endpoints[1].tuya_manufacturer
    zha_listener = mock.MagicMock()
    cluster.add_listener(zha_listener)

    with mock.patch.object(cluster, "send_default_rsp"):
        device.packet_received(
            t.ZigbeePacket(
                profile_id=zha.PROFILE_ID,
                src_ep=1,
                cluster_id=TuyaNewManufCluster.cluster_id,
                data=t.SerializableBytes(packet),
            )
        )

    assert zha_listener.zha_send_event.call_count == 1
    zha_listener.zha_send_event.assert_called_once_with(
        COMMAND_ATTRIBUTE_UPDATED,
        {
            ATTRIBUTE_ID: expected_attr,
            ATTRIBUTE_NAME: "Unknown",
            VALUE: expected_value,
        },
    )
