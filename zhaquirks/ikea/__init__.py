"""Ikea module."""

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, PowerConfiguration, Scenes

from zhaquirks import EventableCluster

IKEA = "IKEA of Sweden"
IKEA_CLUSTER_ID = 0xFC7C  # decimal = 64636
WWAH_CLUSTER_ID = 0xFC57  # decimal = 64599 ('Works with all Hubs' cluster)

IKEA_SHORTCUT_CLUSTER_V1_ID = 0xFC7F  # decimal = 64639 Shortcut V1 commands
IKEA_MATTER_SWITCH_CLUSTER_ID = 0xFC80  # decimal = 64640 Shortcut V2 commands
COMMAND_SHORTCUT_V1 = "shortcut_v1_events"

# PowerConfiguration cluster attributes
BATTERY_VOLTAGE = PowerConfiguration.attributes_by_name["battery_voltage"].id
BATTERY_SIZE = PowerConfiguration.attributes_by_name["battery_size"].id
BATTERY_QUANTITY = PowerConfiguration.attributes_by_name["battery_quantity"].id
BATTERY_RATED_VOLTAGE = PowerConfiguration.attributes_by_name[
    "battery_rated_voltage"
].id


class ScenesCluster(CustomCluster, Scenes):
    """Ikea Scenes cluster."""

    server_commands = Scenes.server_commands.copy()
    server_commands.update(
        {
            0x0007: foundation.ZCLCommandDef(
                "press",
                {"param1": t.int16s, "param2": t.int8s, "param3": t.int8s},
                False,
                is_manufacturer_specific=True,
            ),
            0x0008: foundation.ZCLCommandDef(
                "hold",
                {"param1": t.int16s, "param2": t.int8s},
                False,
                is_manufacturer_specific=True,
            ),
            0x0009: foundation.ZCLCommandDef(
                "release",
                {
                    "param1": t.int16s,
                },
                False,
                is_manufacturer_specific=True,
            ),
        }
    )


class ShortcutV1Cluster(EventableCluster):
    """Ikea Shortcut Button Cluster Variant 1."""

    cluster_id = IKEA_SHORTCUT_CLUSTER_V1_ID

    server_commands = {
        0x01: foundation.ZCLCommandDef(
            COMMAND_SHORTCUT_V1,
            {
                "shortcut_button": t.int8s,
                "shortcut_event": t.int8s,
            },
            False,
            is_manufacturer_specific=True,
        ),
    }


class ShortcutV2Cluster(EventableCluster):
    """Ikea Shortcut Button Cluster Variant 2."""

    cluster_id = IKEA_MATTER_SWITCH_CLUSTER_ID

    server_commands = {
        0x00: foundation.ZCLCommandDef(
            "switch_latched",
            {
                "new_position": t.int8s,
            },
            False,
            is_manufacturer_specific=True,
        ),
        0x01: foundation.ZCLCommandDef(
            "initial_press",
            {
                "new_position": t.int8s,
            },
            False,
            is_manufacturer_specific=True,
        ),
        0x02: foundation.ZCLCommandDef(
            "long_press",
            {
                "previous_position": t.int8s,
            },
            False,
            is_manufacturer_specific=True,
        ),
        0x03: foundation.ZCLCommandDef(
            "short_release",
            {
                "previous_position": t.int8s,
            },
            False,
            is_manufacturer_specific=True,
        ),
        0x04: foundation.ZCLCommandDef(
            "long_release",
            {
                "previous_position": t.int8s,
            },
            False,
            is_manufacturer_specific=True,
        ),
        0x05: foundation.ZCLCommandDef(
            "multi_press_ongoing",
            {
                "new_position": t.int8s,
                # "current_number_of_presses_counted": t.int8s, # not implemented
            },
            False,
            is_manufacturer_specific=True,
        ),
        0x06: foundation.ZCLCommandDef(
            "multi_press_complete",
            {
                "previous_position": t.int8s,
                "total_number_of_presses_counted": t.int8s,
            },
            False,
            is_manufacturer_specific=True,
        ),
    }


# ZCL compliant IKEA power configuration clusters:
class PowerConfig1AAACluster(CustomCluster, PowerConfiguration):
    """Updating power attributes: 2 AAA."""

    _CONSTANT_ATTRIBUTES = {
        BATTERY_SIZE: 4,
        BATTERY_QUANTITY: 1,
        BATTERY_RATED_VOLTAGE: 15,
    }


class PowerConfig2AAACluster(CustomCluster, PowerConfiguration):
    """Updating power attributes: 2 AAA."""

    _CONSTANT_ATTRIBUTES = {
        BATTERY_SIZE: 4,
        BATTERY_QUANTITY: 2,
        BATTERY_RATED_VOLTAGE: 15,
    }


class PowerConfig2CRCluster(CustomCluster, PowerConfiguration):
    """Updating power attributes: 2 CR2032."""

    _CONSTANT_ATTRIBUTES = {
        BATTERY_SIZE: 10,
        BATTERY_QUANTITY: 2,
        BATTERY_RATED_VOLTAGE: 30,
    }


class PowerConfig1CRCluster(CustomCluster, PowerConfiguration):
    """Updating power attributes: 1 CR2032."""

    _CONSTANT_ATTRIBUTES = {
        BATTERY_SIZE: 10,
        BATTERY_QUANTITY: 1,
        BATTERY_RATED_VOLTAGE: 30,
    }


class PowerConfig1CRXCluster(CustomCluster, PowerConfiguration):
    """Updating power attributes: 1 CR2032 and zero voltage."""

    _CONSTANT_ATTRIBUTES = {
        BATTERY_VOLTAGE: 0,
        BATTERY_SIZE: 10,
        BATTERY_QUANTITY: 1,
        BATTERY_RATED_VOLTAGE: 30,
    }


# doubling IKEA power configuration clusters:


class DoublingPowerConfigClusterIKEA(CustomCluster, PowerConfiguration):
    """PowerConfiguration cluster implementation for IKEA devices.

    This implementation doubles battery pct remaining for IKEA devices with old firmware.
    """

    def _update_attribute(self, attrid, value):
        if attrid == PowerConfiguration.AttributeDefs.battery_percentage_remaining.id:
            # get sw_build_id from attribute cache if available
            sw_build_id = self.endpoint.basic.get(
                Basic.AttributeDefs.sw_build_id.id, None
            )

            # if sw_build_id is not available, create task to read from device, since it should be awake now
            # this will be used for next time battery percentage is updated
            if sw_build_id is None:
                self.create_catching_task(
                    self.endpoint.basic.read_attributes(
                        [Basic.AttributeDefs.sw_build_id.id]
                    )
                )

            # double value if sw_build_id is not available or major version is less than 24
            if sw_build_id is None or int(sw_build_id.split(".")[0]) < 24:
                value = value * 2
        super()._update_attribute(attrid, value)


class DoublingPowerConfig2AAACluster(
    DoublingPowerConfigClusterIKEA, PowerConfig2AAACluster
):
    """Doubling power configuration cluster. Updating power attributes: 2 AAA."""


class DoublingPowerConfig2CRCluster(
    DoublingPowerConfigClusterIKEA, PowerConfig2CRCluster
):
    """Doubling power configuration cluster. Updating power attributes: 2 CR2032."""


class DoublingPowerConfig1CRCluster(
    DoublingPowerConfigClusterIKEA, PowerConfig1CRCluster
):
    """Doubling power configuration cluster. Updating power attributes: 1 CR2032."""


class DoublingPowerConfig1CRXCluster(
    DoublingPowerConfigClusterIKEA, PowerConfig1CRXCluster
):
    """Doubling power configuration cluster. Updating power attributes: 1 CR2032 and zero voltage."""
