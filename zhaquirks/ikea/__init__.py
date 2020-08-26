"""Ikea module."""
import logging

import zigpy.types as t
from zigpy.quirks import CustomCluster
from zigpy.zcl.clusters.general import Scenes
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink
from zigpy.zcl.foundation import ReadAttributeRecord

_LOGGER = logging.getLogger(__name__)
IKEA = "IKEA of Sweden"


class LightLinkCluster(CustomCluster, LightLink):
    """Ikea LightLink cluster."""

    async def bind(self):
        """Bind LightLink cluster to coordinator."""
        application = self._endpoint.device.application
        try:
            coordinator = application.get_device(application.ieee)
        except KeyError:
            _LOGGER.warning("Aborting - unable to locate required coordinator device.")
            return
        group_list = await self.get_group_identifiers(0)
        try:
            group_record = group_list[2]
            group_id = group_record[0].group_id
        except IndexError:
            _LOGGER.warning(
                "unable to locate required group info - falling back to group 0x0000."
            )
            group_id = 0x0000
        status = await coordinator.add_to_group(group_id)
        return [status]


class ScenesCluster(CustomCluster, Scenes):
    """Ikea Scenes cluster."""

    manufacturer_server_commands = {
        0x0007: ("press", (t.int16s, t.int8s, t.int8s), False),
        0x0008: ("hold", (t.int16s, t.int8s), False),
        0x0009: ("release", (t.int16s,), False),
    }


class ColorTemperatureCluster(CustomCluster, Color):
    """Ikea Color Temperature cluster."""

    cluster_id = Color.cluster_id

    CURRENT_X_ID = 0x0003
    CURRENT_Y_ID = 0x0004
    COLOR_TEMPERATURE_ID = 0x0007
    COLOR_CAPABILITIES_ID = 0x400A

    _CONSTANT_ATTRIBUTES = {
        # COLOR_TEMPERATURE_ID: 300,
        COLOR_CAPABILITIES_ID: t.bitmap16(0x001F),
    }

    # manufacturer_attributes = {0x0007: ("color_temperature", t.uint16_t)}

    # def __init__(self, *args, **kwargs):
    #     """Init."""
    #     super().__init__(*args, **kwargs)
    #     # self.endpoint.device.color_temperature_bus.add_listener(self)

    def _update_attribute(self, attrid, value):
        _LOGGER.debug(
            "update_attribute IKEA: id: " + str(attrid) + " value: " + str(value)
        )

        if attrid == self.CURRENT_X_ID:
            super()._update_attribute(self.COLOR_TEMPERATURE_ID, 301)

        if attrid == self.CURRENT_Y_ID:
            super()._update_attribute(self.COLOR_TEMPERATURE_ID, 302)

        if attrid == self.COLOR_TEMPERATURE_ID:
            value = 303
            _LOGGER.debug("updating ikea attribute color temperature to 303")

        super()._update_attribute(attrid, value)
        # if value is not None and value >= 0:
        #     _LOGGER.debug("updating ikea attribute color temperature to 153")
        #     super()._update_attribute(self.COLOR_TEMPERATURE_ID, 153)
        # self.endpoint.device.color_temperature_bus.listener_event(
        #     "color_temperature_reported", 153 # value
        # )

    async def read_attributes_raw(self, attributes, manufacturer=None):
        _LOGGER.debug("Reading attributes IKEA: " + str(attributes))

        if self.COLOR_TEMPERATURE_ID in attributes:
            self._update_attribute(self.COLOR_TEMPERATURE_ID, 304)
        read = await super().read_attributes_raw(attributes, manufacturer)

        _LOGGER.debug(
            "Reading attributes IKEA returnt type:"
            + str(type(read))
            + " and returning: "
            + str(read)
        )
        for var in read:
            _LOGGER.debug(str(type(var)))
            _LOGGER.debug(str(var))
            # if isinstance(var, ReadAttributeRecord):
            #     _LOGGER.debug(var.value)

        return read

    # def color_temperature_reported(self, value):
    #     """Color temperature reported."""
    #     self._update_attribute(self.COLOR_TEMPERATURE_ID, value)
