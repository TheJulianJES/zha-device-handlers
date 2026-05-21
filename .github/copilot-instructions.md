This file provides guidance to AI coding agents when working with code in this repository.

## Overview

ZHA-Quirks provides device-specific handlers for ZHA (Zigbee Home Automation) in Home Assistant. Quirks handle devices that don't follow standard ZCL (Zigbee Cluster Library) specifications by defining custom attributes, clusters, and entity mappings.

## Commands

```bash
script/setup                              # Initial setup (uv sync + pre-commit install)
uv sync                                   # Sync deps after branch switch / pull
pytest tests/                             # All tests (or pass a path / `::test_name`)
pre-commit run --all-files                # ruff + mypy + codespell
ruff check zhaquirks/                     # Lint only
ruff format zhaquirks/                    # Format only
mypy zhaquirks/                           # Type check only
```

## Zigbee Concepts

**Clusters**: Functionality groupings containing attributes and commands.
- **in_clusters** (Server clusters): Control the device, send attribute reports. E.g., `OnOff` on a light bulb.
- **out_clusters** (Client clusters): Send commands to other devices. E.g., `OnOff` on a remote control.

**Endpoints**: Groupings of clusters. Multi-gang switches have separate endpoints per switch.

## Quirk Architecture

### V2 Quirks (Preferred for New Quirks)

Use `QuirkBuilder` from `zigpy.quirks.v2` for declarative quirk definition:

```python
from zigpy.quirks.v2 import QuirkBuilder

(
    QuirkBuilder("Manufacturer", "Model")
    .applies_to("AltManufacturer", "Model")  # Additional models
    .replaces(CustomClusterClass)             # Replace standard cluster
    .device_automation_triggers({...})        # Button/action mappings
    .switch(attribute_name=..., fallback_name=...)  # HA entity
    .add_to_registry()
)
```

#### QuirkBuilder Methods Reference

**Device Matching:**
- `.applies_to(manufacturer, model)` - Add manufacturer/model pair to match
- `.filter(filter_function)` - Custom filter function `(device) -> bool`
- `.firmware_version_filter(min_version, max_version, allow_missing)` - Filter by firmware version

Firmware version filtering is useful when different firmware versions need different quirks. `min_version` is inclusive, `max_version` is exclusive, `allow_missing=True` matches devices that don't report a version. Two-quirk split (OLD < `0x191B3685` ≤ NEW) — the same version appears in both because of the inclusive/exclusive split:
```python
QuirkBuilder("innr", "SP 240").firmware_version_filter(max_version=0x191B3685, allow_missing=False).replaces(OldFirmwareCluster).add_to_registry()
QuirkBuilder("innr", "SP 240").firmware_version_filter(min_version=0x191B3685, allow_missing=True).replaces(NewFirmwareCluster).add_to_registry()
```

**Cluster Modification:**
- `.adds(cluster, endpoint_id=1, cluster_type=ClusterType.Server, constant_attributes={})` - Add a cluster. `constant_attributes` dict forces specific attribute values (same as `_CONSTANT_ATTRIBUTES` on a custom cluster)
- `.removes(cluster_id, endpoint_id=1, cluster_type=ClusterType.Server)` - Remove a cluster
- `.replaces(replacement_cluster_class, endpoint_id=1, cluster_type=ClusterType.Server)` - Replace cluster with custom implementation
- `.replace_cluster_occurrences(cluster_class, replace_server=True, replace_client=True)` - Replace across all endpoints

`cluster_type` can be `ClusterType.Server` (in_clusters) or `ClusterType.Client` (out_clusters).

**Endpoint Modification:**
- `.adds_endpoint(endpoint_id, profile_id, device_type)`
- `.removes_endpoint(endpoint_id)`
- `.replaces_endpoint(endpoint_id, profile_id, device_type)` - Change endpoint's profile/device type

Example: Change device type so HA creates correct entity (ZHA profile used by default):
```python
.replaces_endpoint(1, device_type=zha.DeviceType.DIMMABLE_LIGHT)
```

**Entity Creation (Home Assistant):**
All entity methods require `fallback_name`. Common parameters:
- `attribute_name`: ZCL attribute to expose
- `cluster_id`: Cluster containing the attribute
- `endpoint_id`: Endpoint (default 1)
- `translation_key`: For HA translations (required if no device_class)
- `fallback_name`: English name in sentence case (always required)
- `entity_type`: `EntityType.STANDARD`, `CONFIG`, or `DIAGNOSTIC`
- `initially_disabled`: Start disabled in HA
- `device_class`: HA device class for the entity
- `reporting_config`: Configure ZCL attribute reporting
- `unique_id_suffix`: Suffix appended to the entity's unique_id. Defaults to `attribute_name` (or `command_name` for command-based entities). Required when creating multiple entities from the same attribute/command on the same endpoint, since otherwise the default suffixes collide. See **Entity unique_id format** below before changing this on existing quirks.

**Parameter order convention:** `attribute_name`, `cluster_id`, `endpoint_id` first; `translation_key` and `fallback_name` always last (in that order). Use keyword arguments for clarity.

`reporting_config` sets up automatic attribute reporting from the device:
```python
from zigpy.quirks.v2 import ReportingConfig

.sensor(
    attribute_name="measured_value",
    cluster_id=VOCIndex.cluster_id,
    reporting_config=ReportingConfig(
        min_interval=60,      # Minimum seconds between reports
        max_interval=120,     # Maximum seconds between reports
        reportable_change=1,  # Minimum change to trigger report
    ),
    ...
)
```

**Entity Methods:** All take the common parameters above. Method-specific extras:

- `.switch(attribute_name, cluster_id, ...)` — extras: `force_inverted`, `off_value` (default 0), `on_value` (default 1)
- `.sensor(attribute_name, cluster_id, ...)` — extras: `divisor`, `multiplier`, `suggested_display_precision`, `state_class`, `unit` (use constants, not strings)
- `.binary_sensor(attribute_name, cluster_id, ...)` — extras: `attribute_converter=lambda v: ...` to derive boolean (e.g., `lambda v: bool(v & IasZone.ZoneStatus.Tamper)`); pair with `unique_id_suffix` when multiple entities share an attribute
- `.number(attribute_name, cluster_id, ...)` — extras: `min_value`, `max_value`, `step`, `mode` (`"box"` or `"slider"`), `multiplier` (see semantics below), `unit`
- `.enum(attribute_name, enum_class, cluster_id, ...)` — defaults to SELECT (writable). Pass `entity_platform=EntityPlatform.SENSOR` for a read-only display.
- `.write_attr_button(attribute_name, attribute_value, cluster_id, ...)` — writes `attribute_value` to the attribute on press
- `.command_button(command_name, cluster_id, ...)` — extras: `command_args`, `command_kwargs`; executes a ZCL command on press

For `cluster_type=ClusterType.Client` use the client-side cluster (out_clusters).

**Number `multiplier` semantics:** Defined on the entity by ZHA. HA Core is a pure pass-through — it does no scaling itself. The conversion is:
- Display: `native_value = raw_attr_value * multiplier`
- Write: `raw_attr_value = int(ha_value / multiplier)`

If the underlying attribute is an integer representing a fractional unit (e.g., the ZCL `local_temperature_calibration` attribute is `int8s` storing tenths of a degree), pair fractional `step` with the matching `multiplier` so HA values are scaled correctly. The attribute's raw type comes from the cluster's `AttributeDefs` — for `.number()` (unlike `.tuya_number()`) you don't pass a `type`. Without a `multiplier` (default `1`), `int()` silently truncates fractional input on write and raw values are displayed unscaled.

```python
# ZCL Thermostat local_temperature_calibration: int8s, tenths of a degree.
# HA range -2.5..2.5 °C ↔ raw attribute value -25..25
.number(
    attribute_name=Thermostat.AttributeDefs.local_temperature_calibration.name,
    cluster_id=Thermostat.cluster_id,
    min_value=-2.5,
    max_value=2.5,
    step=0.1,
    multiplier=0.1,   # required: pairs with step=0.1
    unit=UnitOfTemperature.CELSIUS,
    translation_key="local_temperature_calibration",
    fallback_name="Local temperature calibration",
)
```

`min_value`/`max_value` are HA-side values (after the multiplier), not raw attribute values. Confirm the device's raw value range and pick HA-side limits accordingly.

**Entity unique_id format:**

HA uses `unique_id` to identify an entity across restarts. If a quirk change causes it to change, HA treats the result as a new entity — the old one is orphaned and anything referencing it breaks.

**For v2 quirk entities** the format is:

```
{device.ieee}-{endpoint_id}-{suffix}
```

Note there is **no cluster_id** between the endpoint and the suffix. This differs from the format used by ZHA-native entities (see below).

`{suffix}` resolves in this order:
1. Explicit `unique_id_suffix=` on the builder call
2. Otherwise `attribute_name` (attribute-based entities)
3. Otherwise `command_name` (for `.command_button()`)
4. Otherwise no suffix

**Breaking-change implications:**
- Renaming `attribute_name` on a custom cluster used by an existing v2 quirk changes the default suffix and **breaks existing entities**. Avoid unless necessary.
- Moving an entity to a different `endpoint_id` also changes the unique_id and breaks existing entities.
- `translation_key` and `fallback_name` do **not** affect unique_id — renaming these is safe.
- If a rename is genuinely required, preserve the old suffix via `unique_id_suffix=` on each affected entity. Flag the breakage in the PR.
- When reviewing PRs that rename attributes in an existing v2 quirk (or move entities to different endpoints), call this out before it lands.

**ZHA-native entities (not created by a v2 quirk):**

Some entities are not created by a v2 quirk's entity declarations — they come from a class defined in the ZHA library itself. These entities go through ZHA's standard discovery path in `PlatformEntity.__init__`, which uses a different format:

```
{device.ieee}-{endpoint_id}-{cluster_id}-{suffix}
```

The cluster_id appears as a decimal integer. `{suffix}` comes from a hardcoded `_unique_id_suffix` class attribute on the ZHA-native entity class (typically matching the entity's `_attribute_name`, e.g. `"power_outage_memory"`, `"invert_switch"`, `"child_lock"`).

Note: several primary platform-entity classes use a shorter legacy `{ieee}-{endpoint_id}` format (no cluster_id, no suffix) for backwards compatibility — `Light`, `Shade`, `DeviceTracker`, `Switch` (main OnOff on light/smart-plug/ballast/plug-in-unit device types), and `Cover`/`Thermostat`/`Siren` when the endpoint's device type matches the entity's primary type. Config switches, numbers and sensors on the same device still use the standard cluster_id-included format above.

When migrating such an entity to a quirks v2 definition, the v2 entity must produce the same unique_id as the old one or HA will treat it as a new entity. Because v2 quirk unique_ids do **not** auto-include the cluster_id, the v2 `unique_id_suffix=` must include the cluster_id explicitly to match.

Example: for a ZHA-native entity on cluster_id `0xFCC0` (= `64704`) with attribute `child_lock`, the existing unique_id is `{ieee}-1-64704-child_lock`. To preserve that under v2, pass `unique_id_suffix="64704-child_lock"` on the corresponding `.switch(...)` call to get the same unique_id.

If you have access to a checkout of the ZHA library, you can find existing unique_ids in the device diagnostics dumps under `zha/tests/data/devices/`.

**Device Automation Triggers:**
```python
# Maps device events to HA automation triggers
# Format: {(action, subtype): {COMMAND: command_name, ...}}
.device_automation_triggers({
    (SHORT_PRESS, TURN_ON): {COMMAND: COMMAND_ON},
    (SHORT_PRESS, TURN_OFF): {COMMAND: COMMAND_OFF},
    (LONG_PRESS, DIM_UP): {COMMAND: COMMAND_STEP, CLUSTER_ID: 8, ENDPOINT_ID: 1},
})
```
The trigger tuple `(action, subtype)` appears in the HA UI. The dict value must uniquely match the `zha_event` fired by the device.

**Other Methods:**
- `.friendly_name(model="...", manufacturer="...")` — override device name shown in HA
- `.device_class(custom_device_class)` — use a `CustomDeviceV2` subclass (e.g. for special request handling)
- `.skip_configuration()` — skip attribute reporting configuration
- `.add_to_registry()` — **required**; registers the quirk

**Preventing default entity creation:** `.prevent_default_entity_creation(endpoint_id, cluster_id, function=None)` hides entities ZHA would create by default. `function` is an optional `lambda entity: bool` to match only specific entities.

**Changing default entity metadata:** `.change_entity_metadata(endpoint_id, cluster_id, new_primary=..., new_entity_category=..., ...)` overrides properties of default entities. Available `new_*` params: `new_primary`, `new_unique_id`, `new_translation_key`, `new_device_class`, `new_state_class`, `new_entity_category`, `new_fallback_name`.

### Tuya Devices (TuyaQuirkBuilder)

Tuya devices use datapoints (DPs) instead of ZCL attributes. Use `TuyaQuirkBuilder`:

```python
from zhaquirks.tuya.builder import TuyaQuirkBuilder

(
    TuyaQuirkBuilder("_TZE200_xxx", "TS0601")
    .tuya_temperature(dp_id=1, scale=10)
    .tuya_humidity(dp_id=2)
    .tuya_battery(dp_id=4)
    .tuya_switch(dp_id=5, attribute_name="valve", fallback_name="Valve")
    .skip_configuration()
    .add_to_registry()
)
```

See `tuya.md` for detailed Tuya quirk documentation including finding DPs and all available methods.

### V1 Quirks (Legacy)

Legacy form: a `CustomDevice` subclass with `signature` (must match device exactly) and `replacement` dicts (what ZHA uses instead). Prefer v2 for new quirks; refer to existing v1 quirks under `zhaquirks/` for the structure when modifying one.

### Custom Clusters

**Extending a ZCL cluster** - Add manufacturer-specific attributes to a standard cluster:

```python
from zigpy.quirks import CustomCluster
from zigpy.zcl.clusters.general import OnOff

class CustomOnOffCluster(CustomCluster, OnOff):
    """Custom OnOff with manufacturer-specific attributes."""

    class AttributeDefs(OnOff.AttributeDefs):
        custom_attr: Final = ZCLAttributeDef(
            id=0x8000, type=t.Bool, manufacturer_code=0x117C
        )
```

**Fully custom cluster** - For manufacturer-specific clusters not based on ZCL:

```python
from zigpy.quirks import CustomCluster
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

class VOCIndex(CustomCluster):
    """Custom cluster with no ZCL base."""

    cluster_id: t.uint16_t = 0xFC7E       # Manufacturer-specific cluster ID
    name: str = "IKEA VOC Index"
    ep_attribute: str = "voc_index"        # Attribute name on endpoint

    class AttributeDefs(BaseAttributeDefs):  # Note: BaseAttributeDefs, not a ZCL cluster
        measured_value: Final = ZCLAttributeDef(
            id=0x0000, type=t.Single, access="rp", manufacturer_code=0x117C
        )
```

**`manufacturer_code`**: hex code sent with read/write requests for the attribute. Required for vendor-specific attributes (e.g. `0x117C` IKEA, `0x115F` Xiaomi); without it the device may not respond. Set `manufacturer_code=None` to explicitly suppress it. Replaces the older `is_manufacturer_specific=True` approach.

**`access`**: defaults to `"rwp"`. Values: `"r"` read, `"w"` write, `"rw"` read+write, `"rp"` read+reportable, `"rwp"` all.

**Custom enum types** for attribute values — define `t.enum8` / `t.enum16` subclasses and use as `type=` in `ZCLAttributeDef`:
```python
class BoschOperatingMode(t.enum8):
    Schedule = 0x00
    Manual = 0x01
    Pause = 0x05
```

**`_CONSTANT_ATTRIBUTES`**: force specific attribute values, overriding what the device reports (useful when devices report wrong multiplier/divisor etc.):
```python
class MeteringClusterFixed(CustomCluster, Metering):
    _CONSTANT_ATTRIBUTES = {
        Metering.AttributeDefs.multiplier.id: 1,
        Metering.AttributeDefs.divisor.id: 100,
    }
```

Key base classes in `zhaquirks/__init__.py`:
- `LocalDataCluster`: Prevents remote calls, responds locally
- `EventableCluster`: Converts cluster requests to events

## Entity Creation Rules

When adding entities with v2 quirks:

1. **`fallback_name`** is always required - English entity name in sentence case (e.g., "Soil moisture" not "Soil Moisture"). Abbreviations like "LED" stay uppercase.

2. **`translation_key`** is optional but required when no device class is set. Typically the attribute name or slugified entity name.

3. Entity name priority in Home Assistant: translation_key → device_class name → fallback_name

## Testing

Test fixtures are in `tests/conftest.py`:

```python
# For v1 quirks
quirked = zigpy_device_from_quirk(quirk_class)

# For v2 quirks
quirked = zigpy_device_from_v2_quirk(model, manufacturer)

# Verify signature matches quirk (useful for v1 quirks)
def test_my_device_signature(assert_signature_matches_quirk):
    signature = {...}  # From HA device page "Zigbee Device Signature"
    assert_signature_matches_quirk(MyDeviceQuirk, signature)
```

**Tests NOT needed** for purely declarative v2 quirks (only `.applies_to()`, `.friendly_name()`, `.device_automation_triggers()`, `.skip_configuration()`, reusing already-tested custom clusters, etc.).

**Tests ARE needed** when a quirk adds custom logic — custom clusters with overridden methods (`handle_cluster_request`, `update_attribute`, ...), `attribute_converter` lambdas, or custom filter functions.

## Code Organization

Quirks are organized by manufacturer in `zhaquirks/<manufacturer>/`:
- `__init__.py`: Shared clusters, constants, base classes for the manufacturer
- `<device>.py`: Device-specific quirks

## Key Imports

- Signature/trigger constants (v1 quirks + device automation triggers): `zhaquirks.const` — e.g., `MODELS_INFO`, `ENDPOINTS`, `INPUT_CLUSTERS`, `OUTPUT_CLUSTERS`, `PROFILE_ID`, `DEVICE_TYPE`, `SKIP_CONFIGURATION`, `SHORT_PRESS`/`LONG_PRESS`/`DOUBLE_PRESS`/`TRIPLE_PRESS`, `COMMAND`, `COMMAND_ON`/`COMMAND_OFF`/`COMMAND_TOGGLE`
- Quirk building: `from zigpy.quirks.v2 import QuirkBuilder`; `from zhaquirks.tuya.builder import TuyaQuirkBuilder`
- HA-side enums/units: `from zigpy.quirks.v2.homeassistant import EntityPlatform, EntityType, UnitOfTemperature, UnitOfTime, UnitOfEnergy, UnitOfPower`; device-class enums under `zigpy.quirks.v2.homeassistant.{binary_sensor,number,sensor}`
- Clusters/types: `from zigpy.zcl import ClusterType`; `from zigpy.zcl.clusters.general import ...`; `import zigpy.types as t`

## Code Style

**Avoid magic numbers** for cluster/attribute/command IDs. Use definitions: `Metering.cluster_id`, `Metering.AttributeDefs.multiplier.id` (or `.name`), `WindowCovering.ServerCommandDefs.go_to_lift_percentage.id`, `IasZone.ClientCommandDefs.status_change_notification.id`. Don't write bare `0x0702` / `0x0301` / `0x00`.

**Access clusters via `ep_attribute`** (e.g., `IasZone.ep_attribute == "ias_zone"`):
```python
self.endpoint.ias_zone.update_attribute(IasZone.AttributeDefs.zone_status.id, IasZone.ZoneStatus.Alarm_1)
self.endpoint.device.endpoints[1].electrical_measurement.update_attribute(ElectricalMeasurement.AttributeDefs.active_power.id, value)
```

**In `handle_cluster_request`**, compare via command-def `.id`:
```python
def handle_cluster_request(self, hdr, args, *, dst_addressing=None):
    if hdr.command_id in (LevelControl.ServerCommandDefs.move.id, LevelControl.ServerCommandDefs.move_with_on_off.id):
        ...
```

## PR Requirements

- Run `pre-commit run --all-files` before submitting
- New quirks require device diagnostics data (download from HA device page → three dots → "Download diagnostics")
- Tests should verify entity creation
