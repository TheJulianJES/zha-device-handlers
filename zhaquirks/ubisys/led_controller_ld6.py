"""Ubisys LD6 LED Controller quirk.

Exposes a select entity for the 23 output configuration profiles defined in the
ubisys LD6 technical reference. Each profile maps 6 PWM channels to 1-6 light
endpoints with different capabilities (dimmable, CCT, RGB, RGBW, etc.).
"""

import logging
from typing import Any, Final

from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl import (
    AttributeReadEvent,
    AttributeReportedEvent,
    AttributeUpdatedEvent,
    AttributeWrittenEvent,
    foundation,
)
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    DefaultResponse,
    WriteAttributesStructuredResponseSchema,
    ZCLAttributeDef,
)

from zhaquirks import LocalDataCluster
from zhaquirks.ubisys import UbisysCluster

_LOGGER = logging.getLogger(__name__)


class OutputMode(t.enum8):
    """Output configuration profiles for the ubisys LD6."""

    Dimmable_1x = 0x00
    CCT_1x = 0x01
    RGB_1x = 0x02
    RGBW_1x = 0x03
    RGBCW_1x = 0x04
    Extended_color_1x = 0x05
    Dimmable_2x = 0x06
    CCT_2x = 0x07
    RGBW_1x_CCT_1x = 0x08
    RGB_1x_CCT_1x = 0x09
    RGB_1x_dimmable_1x = 0x0A
    RGBW_1x_dimmable_1x = 0x0B
    RGBCW_1x_dimmable_1x = 0x0C
    RGB_2x = 0x0D
    Dimmable_3x = 0x0E
    CCT_3x = 0x0F
    RGB_1x_dimmable_2x = 0x10
    RGB_1x_CCT_1x_dimmable_1x = 0x11
    RGBW_1x_dimmable_2x = 0x12
    Dimmable_4x = 0x13
    RGB_1x_dimmable_3x = 0x14
    Dimmable_5x = 0x15
    Dimmable_6x = 0x16


# Unused channel slot
_OFF = bytes([0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])

# Reference configurations from the ubisys LD6 technical reference, section 6.13.3.4.
# Each profile maps to exactly 6 channel entries (one per PWM output).
# Byte format per channel: [EndpointAndFunction, Flux, CIE_x_lo, CIE_x_hi, CIE_y_lo, CIE_y_hi]
OUTPUT_MODE_DATA: dict[OutputMode, list[bytes]] = {
    # --- One light source ---
    OutputMode.Dimmable_1x: [
        bytes([0x10, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        _OFF,
        _OFF,
        _OFF,
        _OFF,
        _OFF,
    ],
    OutputMode.CCT_1x: [
        bytes([0x11, 0xFE, 0x42, 0x50, 0xD9, 0x52]),
        bytes([0x12, 0xFE, 0xB9, 0x75, 0x1D, 0x69]),
        _OFF,
        _OFF,
        _OFF,
        _OFF,
    ],
    OutputMode.RGB_1x: [
        bytes([0x13, 0x47, 0x06, 0xB1, 0xEF, 0x4E]),
        bytes([0x14, 0xA0, 0x39, 0x1D, 0x82, 0xD3]),
        bytes([0x15, 0x42, 0xC6, 0x1F, 0xCC, 0x0E]),
        _OFF,
        _OFF,
        _OFF,
    ],
    OutputMode.RGBW_1x: [
        bytes([0x13, 0x47, 0x06, 0xB1, 0xEF, 0x4E]),
        bytes([0x14, 0xA0, 0x39, 0x1D, 0x82, 0xD3]),
        bytes([0x15, 0x42, 0xC6, 0x1F, 0xCC, 0x0E]),
        bytes([0x11, 0xFE, 0x64, 0x61, 0x72, 0x60]),
        _OFF,
        _OFF,
    ],
    OutputMode.RGBCW_1x: [
        bytes([0x13, 0x47, 0x06, 0xB1, 0xEF, 0x4E]),
        bytes([0x14, 0xA0, 0x39, 0x1D, 0x82, 0xD3]),
        bytes([0x15, 0x42, 0xC6, 0x1F, 0xCC, 0x0E]),
        bytes([0x11, 0xFE, 0x42, 0x50, 0xD9, 0x52]),
        bytes([0x12, 0xFE, 0xB9, 0x75, 0x1D, 0x69]),
        _OFF,
    ],
    OutputMode.Extended_color_1x: [
        bytes([0x13, 0x45, 0x86, 0xB1, 0xEF, 0x4E]),
        bytes([0x16, 0xC6, 0x59, 0x9A, 0x80, 0x65]),
        bytes([0x14, 0xFE, 0x39, 0x1D, 0x82, 0xD3]),
        bytes([0x17, 0xB4, 0x9E, 0x0B, 0x83, 0x4B]),
        bytes([0x15, 0x4D, 0xC6, 0x1F, 0xCC, 0x0E]),
        bytes([0x18, 0x6C, 0x2D, 0x2C, 0x3A, 0x01]),
    ],
    # --- Two light sources ---
    OutputMode.Dimmable_2x: [
        bytes([0x10, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        bytes([0x50, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        _OFF,
        _OFF,
        _OFF,
        _OFF,
    ],
    OutputMode.CCT_2x: [
        bytes([0x11, 0xFE, 0x42, 0x50, 0xD9, 0x52]),
        bytes([0x12, 0xFE, 0xB9, 0x75, 0x1D, 0x69]),
        bytes([0x51, 0xFE, 0x42, 0x50, 0xD9, 0x52]),
        bytes([0x52, 0xFE, 0xB9, 0x75, 0x1D, 0x69]),
        _OFF,
        _OFF,
    ],
    OutputMode.RGBW_1x_CCT_1x: [
        bytes([0x13, 0x47, 0x06, 0xB1, 0xEF, 0x4E]),
        bytes([0x14, 0xA0, 0x39, 0x1D, 0x82, 0xD3]),
        bytes([0x15, 0x42, 0xC6, 0x1F, 0xCC, 0x0E]),
        bytes([0x11, 0xFE, 0x64, 0x61, 0x72, 0x60]),
        bytes([0x51, 0xFE, 0x42, 0x50, 0xD9, 0x52]),
        bytes([0x52, 0xFE, 0xB9, 0x75, 0x1D, 0x69]),
    ],
    OutputMode.RGB_1x_CCT_1x: [
        bytes([0x13, 0x47, 0x06, 0xB1, 0xEF, 0x4E]),
        bytes([0x14, 0xA0, 0x39, 0x1D, 0x82, 0xD3]),
        bytes([0x15, 0x42, 0xC6, 0x1F, 0xCC, 0x0E]),
        _OFF,
        bytes([0x51, 0xFE, 0x42, 0x50, 0xD9, 0x52]),
        bytes([0x52, 0xFE, 0xB9, 0x75, 0x1D, 0x69]),
    ],
    OutputMode.RGB_1x_dimmable_1x: [
        bytes([0x13, 0x47, 0x06, 0xB1, 0xEF, 0x4E]),
        bytes([0x14, 0xA0, 0x39, 0x1D, 0x82, 0xD3]),
        bytes([0x15, 0x42, 0xC6, 0x1F, 0xCC, 0x0E]),
        bytes([0x50, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        _OFF,
        _OFF,
    ],
    OutputMode.RGBW_1x_dimmable_1x: [
        bytes([0x13, 0x47, 0x06, 0xB1, 0xEF, 0x4E]),
        bytes([0x14, 0xA0, 0x39, 0x1D, 0x82, 0xD3]),
        bytes([0x15, 0x42, 0xC6, 0x1F, 0xCC, 0x0E]),
        bytes([0x11, 0xFE, 0x64, 0x61, 0x72, 0x60]),
        bytes([0x50, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        _OFF,
    ],
    OutputMode.RGBCW_1x_dimmable_1x: [
        bytes([0x13, 0x47, 0x06, 0xB1, 0xEF, 0x4E]),
        bytes([0x14, 0xA0, 0x39, 0x1D, 0x82, 0xD3]),
        bytes([0x15, 0x42, 0xC6, 0x1F, 0xCC, 0x0E]),
        bytes([0x11, 0xFE, 0x42, 0x50, 0xD9, 0x52]),
        bytes([0x12, 0xFE, 0xB9, 0x75, 0x1D, 0x69]),
        bytes([0x50, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
    ],
    OutputMode.RGB_2x: [
        bytes([0x13, 0x47, 0x06, 0xB1, 0xEF, 0x4E]),
        bytes([0x14, 0xA0, 0x39, 0x1D, 0x82, 0xD3]),
        bytes([0x15, 0x42, 0xC6, 0x1F, 0xCC, 0x0E]),
        bytes([0x53, 0x47, 0x06, 0xB1, 0xEF, 0x4E]),
        bytes([0x54, 0xA0, 0x39, 0x1D, 0x82, 0xD3]),
        bytes([0x55, 0x42, 0xC6, 0x1F, 0xCC, 0x0E]),
    ],
    # --- Three light sources ---
    OutputMode.Dimmable_3x: [
        bytes([0x10, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        bytes([0x50, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        bytes([0x60, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        _OFF,
        _OFF,
        _OFF,
    ],
    OutputMode.CCT_3x: [
        bytes([0x11, 0xFE, 0x42, 0x50, 0xD9, 0x52]),
        bytes([0x12, 0xFE, 0xB9, 0x75, 0x1D, 0x69]),
        bytes([0x51, 0xFE, 0x42, 0x50, 0xD9, 0x52]),
        bytes([0x52, 0xFE, 0xB9, 0x75, 0x1D, 0x69]),
        bytes([0x61, 0xFE, 0x42, 0x50, 0xD9, 0x52]),
        bytes([0x62, 0xFE, 0xB9, 0x75, 0x1D, 0x69]),
    ],
    OutputMode.RGB_1x_dimmable_2x: [
        bytes([0x13, 0x47, 0x06, 0xB1, 0xEF, 0x4E]),
        bytes([0x14, 0xA0, 0x39, 0x1D, 0x82, 0xD3]),
        bytes([0x15, 0x42, 0xC6, 0x1F, 0xCC, 0x0E]),
        bytes([0x50, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        bytes([0x60, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        _OFF,
    ],
    OutputMode.RGB_1x_CCT_1x_dimmable_1x: [
        bytes([0x13, 0x47, 0x06, 0xB1, 0xEF, 0x4E]),
        bytes([0x14, 0xA0, 0x39, 0x1D, 0x82, 0xD3]),
        bytes([0x15, 0x42, 0xC6, 0x1F, 0xCC, 0x0E]),
        bytes([0x60, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        bytes([0x51, 0xFE, 0x42, 0x50, 0xD9, 0x52]),
        bytes([0x52, 0xFE, 0xB9, 0x75, 0x1D, 0x69]),
    ],
    OutputMode.RGBW_1x_dimmable_2x: [
        bytes([0x13, 0x47, 0x06, 0xB1, 0xEF, 0x4E]),
        bytes([0x14, 0xA0, 0x39, 0x1D, 0x82, 0xD3]),
        bytes([0x15, 0x42, 0xC6, 0x1F, 0xCC, 0x0E]),
        bytes([0x11, 0xFE, 0x64, 0x61, 0x72, 0x60]),
        bytes([0x50, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        bytes([0x60, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
    ],
    # --- Four light sources ---
    OutputMode.Dimmable_4x: [
        bytes([0x10, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        bytes([0x50, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        bytes([0x60, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        bytes([0x70, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        _OFF,
        _OFF,
    ],
    OutputMode.RGB_1x_dimmable_3x: [
        bytes([0x13, 0x47, 0x06, 0xB1, 0xEF, 0x4E]),
        bytes([0x14, 0xA0, 0x39, 0x1D, 0x82, 0xD3]),
        bytes([0x15, 0x42, 0xC6, 0x1F, 0xCC, 0x0E]),
        bytes([0x50, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        bytes([0x60, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        bytes([0x70, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
    ],
    # --- Five light sources ---
    OutputMode.Dimmable_5x: [
        bytes([0x10, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        bytes([0x50, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        bytes([0x60, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        bytes([0x70, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        bytes([0x80, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        _OFF,
    ],
    # --- Six light sources ---
    OutputMode.Dimmable_6x: [
        bytes([0x10, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        bytes([0x50, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        bytes([0x60, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        bytes([0x70, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        bytes([0x80, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        bytes([0x90, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
    ],
}


def _match_output_mode(raw_configs: list[bytes]) -> OutputMode | None:
    """Match raw OutputConfigurations data to a known OutputMode.

    Compares only the first byte (EndpointAndFunction) of each slot,
    which is sufficient to identify the profile without being sensitive
    to user-customized chromaticity/flux calibration values.
    """
    raw_funcs = [c[0] if c else 0 for c in raw_configs]
    for mode, ref_configs in OUTPUT_MODE_DATA.items():
        ref_funcs = [c[0] for c in ref_configs]
        if raw_funcs == ref_funcs:
            return mode
    return None


class UbisysLD6SetupCluster(UbisysCluster):
    """UbisysCluster subclass for the LD6.

    Adds the output_configurations attribute and write method (only relevant
    for devices with the Versalight engine). Listens to its own attribute
    events and syncs the matched OutputMode to the local config cluster.
    """

    class AttributeDefs(UbisysCluster.AttributeDefs):
        """Extended attribute definitions with output_configurations."""

        output_configurations: Final = ZCLAttributeDef(
            id=0x0010, type=t.LVList[t.LVBytes, t.uint16_t], manufacturer_code=None
        )

    async def write_output_configurations(
        self, configs: list[bytes]
    ) -> WriteAttributesStructuredResponseSchema | DefaultResponse:
        """Write output_configurations using ZCL Write Attributes Structured."""
        arr = foundation.Array(
            type=foundation.DataTypeId.octstr,
            value=t.LVList[t.LVBytes, t.uint16_t](configs),
        )
        return await self.write_attributes_structured_raw(
            [
                foundation.WriteAttributeStructured(
                    attrid=self.AttributeDefs.output_configurations.id,
                    selector=foundation.Selector(depth=0),
                    value=foundation.TypeValue(
                        type=foundation.DataTypeId.array, value=arr
                    ),
                )
            ]
        )

    def __init__(self, *args, **kwargs):
        """Init and register self-listeners for output_configurations."""
        super().__init__(*args, **kwargs)
        self.on_event(AttributeReadEvent.event_type, self._handle_output_config_event)
        self.on_event(
            AttributeReportedEvent.event_type, self._handle_output_config_event
        )
        self.on_event(
            AttributeUpdatedEvent.event_type, self._handle_output_config_event
        )
        self.on_event(
            AttributeWrittenEvent.event_type, self._handle_output_config_event
        )

    def _handle_output_config_event(
        self,
        event: (
            AttributeReadEvent
            | AttributeReportedEvent
            | AttributeUpdatedEvent
            | AttributeWrittenEvent
        ),
    ) -> None:
        """Sync local output_mode when output_configurations changes."""
        if event.attribute_id != self.AttributeDefs.output_configurations.id:
            return
        if isinstance(event, AttributeWrittenEvent) and event.status != 0:
            return
        config_cluster = getattr(
            self.endpoint.device.endpoints.get(1),
            UbisysLD6OutputConfigCluster.ep_attribute,
            None,
        )
        if config_cluster is None:
            return
        mode = _match_output_mode(list(event.value))
        if mode is not None:
            config_cluster._update_attribute(
                UbisysLD6OutputConfigCluster.AttributeDefs.output_mode.id, mode
            )
        else:
            _LOGGER.debug(
                "ubisys LD6: output configuration does not match any known profile"
            )


class UbisysLD6OutputConfigCluster(LocalDataCluster):
    """Local cluster to configure LD6 output mode.

    Translates the selected OutputMode enum value into the raw 6-slot
    OutputConfigurations array and writes it to the device via EP232.
    """

    cluster_id = 0xFBFD
    name = "Ubisys LD6 Output Configuration"
    ep_attribute = "ubisys_ld6_output_config"

    class AttributeDefs(BaseAttributeDefs):
        """LD6 output configuration attribute definitions."""

        output_mode: Final = ZCLAttributeDef(id=0x0000, type=OutputMode)

    def __init__(self, *args, **kwargs):
        """Init with default output mode."""
        super().__init__(*args, **kwargs)
        if self.AttributeDefs.output_mode.id not in self._attr_cache:
            self._update_attribute(
                self.AttributeDefs.output_mode.id, OutputMode.Dimmable_1x
            )

    async def apply_custom_configuration(self, *args, **kwargs):
        """Read the device's current output configuration and sync the local enum."""
        setup = self.endpoint.device.endpoints[232].ubisys_cluster
        result = await setup.read_attributes(
            [UbisysLD6SetupCluster.AttributeDefs.output_configurations]
        )
        raw = result[0].get(
            UbisysLD6SetupCluster.AttributeDefs.output_configurations.name
        )
        if raw is not None:
            mode = _match_output_mode(list(raw))
            if mode is not None:
                self._update_attribute(self.AttributeDefs.output_mode.id, mode)
            else:
                _LOGGER.debug(
                    "ubisys LD6: output configuration does not match any known profile"
                )

    async def write_attributes(
        self,
        attributes: dict[str | int, Any],
        manufacturer=None,
        **kwargs,
    ) -> list:
        """Write output_mode by sending the configuration to the device."""
        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            if attr_def == self.AttributeDefs.output_mode:
                mode = OutputMode(value)
                configs = OUTPUT_MODE_DATA[mode]
                device_setup = self.endpoint.device.endpoints[232].ubisys_cluster
                await device_setup.write_output_configurations(configs)
                self._update_attribute(self.AttributeDefs.output_mode.id, mode)
                # The LD6 dynamically reconfigures its endpoints after an
                # output mode change.  Re-interview so ZHA picks up the new
                # endpoint layout (added/removed endpoints, changed device
                # types and clusters).
                await self.endpoint.device.reinterview()
                return [
                    [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
                ]

        raise KeyError(attributes)  # pragma: no cover


(
    QuirkBuilder(manufacturer="ubisys", model="LD6")
    .replaces(UbisysLD6SetupCluster, endpoint_id=232)
    .adds(UbisysLD6OutputConfigCluster)
    .enum(
        attribute_name=UbisysLD6OutputConfigCluster.AttributeDefs.output_mode.name,
        enum_class=OutputMode,
        cluster_id=UbisysLD6OutputConfigCluster.cluster_id,
        translation_key="output_mode",
        fallback_name="Output mode",
    )
    .add_to_registry()
)
