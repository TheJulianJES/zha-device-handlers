"""ADUROLIGHT Adurolight_NCC dimmer remote."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import LevelControl, OnOff

from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STEP,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    PARAMS,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
)

# The "Adurolight_NCC" and "AduroLight_NCC" (note the capital "L") variants share
# the same layout and emit identical on/off/step events. They only differ in the
# model string and in whether LevelControl is also listed as an input cluster, so
# a single v2 quirk matches both. LevelControl is removed from the input clusters
# (no-op on the variant that doesn't have it there) to avoid a spurious entity.
(
    QuirkBuilder("ADUROLIGHT", "Adurolight_NCC")
    .applies_to("ADUROLIGHT", "AduroLight_NCC")
    .removes(LevelControl.cluster_id, endpoint_id=1)
    .device_automation_triggers(
        {
            (SHORT_PRESS, TURN_ON): {
                COMMAND: COMMAND_ON,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 1,
            },
            (SHORT_PRESS, TURN_OFF): {
                COMMAND: COMMAND_OFF,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 1,
            },
            (SHORT_PRESS, DIM_UP): {
                COMMAND: COMMAND_STEP,
                CLUSTER_ID: LevelControl.cluster_id,
                ENDPOINT_ID: 1,
                PARAMS: {"step_mode": 0},
            },
            (SHORT_PRESS, DIM_DOWN): {
                COMMAND: COMMAND_STEP,
                CLUSTER_ID: LevelControl.cluster_id,
                ENDPOINT_ID: 1,
                PARAMS: {"step_mode": 1},
            },
        }
    )
    .add_to_registry()
)
