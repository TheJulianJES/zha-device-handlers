"""Test that all quirks can be initialized."""

import pytest
import zigpy.quirks as zq
from zigpy.quirks import CustomDevice

import zhaquirks

zhaquirks.setup()

# get v1 quirks
ALL_QUIRK_CLASSES: list[zq.CustomDevice] = []
for manufacturer in zq._DEVICE_REGISTRY._registry.values():
    for model_quirk_list in manufacturer.values():
        for quirk in model_quirk_list:
            if quirk in ALL_QUIRK_CLASSES:
                continue
            ALL_QUIRK_CLASSES.append(quirk)


# get v2 quirks
ALL_QUIRK_V2_NAMES: set[tuple[str, str]] = set()

for quirks in zq._DEVICE_REGISTRY._registry_v2.values():
    for quirk_reg_entry in quirks:
        for model_tuple in quirk_reg_entry.manufacturer_model_metadata:
            ALL_QUIRK_V2_NAMES.add((model_tuple.manufacturer, model_tuple.model))


@pytest.mark.parametrize("quirk", ALL_QUIRK_CLASSES)
async def test_quirk_v1_init(zigpy_device_from_quirk, quirk: CustomDevice) -> None:
    """Test all v1 quirks can be initialized."""
    zigpy_device_from_quirk(quirk)


@pytest.mark.parametrize("manufacturer, model", ALL_QUIRK_V2_NAMES)
def test_quirk_v2_init(
    zigpy_device_from_v2_quirk, manufacturer: str, model: str
) -> None:
    """Test all v2 quirks can be initialized."""
    # We don't know what endpoints a specific quirk uses, so we just add all used ones,
    # so if a quirk requires specific endpoints (e.g. to remove), they are present.
    # It's not an issue if they remain unused, but are present on the mock device.
    zigpy_device_from_v2_quirk(manufacturer, model, endpoint_ids=[1, 2, 3, 5, 11, 21])
