"""AduroSmart Eria ADUROLIGHT_CSC scene remote."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import LevelControl, OnOff, Scenes

from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_RECALL,
    COMMAND_STOP,
    COMMAND_STORE,
    COMMAND_TOGGLE,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    PARAMS,
    SHORT_PRESS,
    TURN_ON,
)

# The remote has a power button (top) and three scene buttons. Each scene button
# recalls a fixed scene on short press and stores it on long press. The scene ids
# are constant across devices (the group id, in contrast, is derived from the
# device IEEE and is therefore not matched on).
(
    QuirkBuilder("AduroSmart Eria", "ADUROLIGHT_CSC")
    .device_automation_triggers(
        {
            # Power button (top): toggle on short press, dim while held, stop on release.
            (SHORT_PRESS, TURN_ON): {
                COMMAND: COMMAND_TOGGLE,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 1,
            },
            (LONG_PRESS, TURN_ON): {
                COMMAND: COMMAND_MOVE,
                CLUSTER_ID: LevelControl.cluster_id,
                ENDPOINT_ID: 1,
            },
            (LONG_RELEASE, TURN_ON): {
                COMMAND: COMMAND_STOP,
                CLUSTER_ID: LevelControl.cluster_id,
                ENDPOINT_ID: 1,
            },
            # Scene buttons 1-3: recall on short press, store on long press.
            (SHORT_PRESS, BUTTON_1): {
                COMMAND: COMMAND_RECALL,
                CLUSTER_ID: Scenes.cluster_id,
                ENDPOINT_ID: 1,
                PARAMS: {"scene_id": 253},
            },
            (LONG_PRESS, BUTTON_1): {
                COMMAND: COMMAND_STORE,
                CLUSTER_ID: Scenes.cluster_id,
                ENDPOINT_ID: 1,
                PARAMS: {"scene_id": 253},
            },
            (SHORT_PRESS, BUTTON_2): {
                COMMAND: COMMAND_RECALL,
                CLUSTER_ID: Scenes.cluster_id,
                ENDPOINT_ID: 1,
                PARAMS: {"scene_id": 254},
            },
            (LONG_PRESS, BUTTON_2): {
                COMMAND: COMMAND_STORE,
                CLUSTER_ID: Scenes.cluster_id,
                ENDPOINT_ID: 1,
                PARAMS: {"scene_id": 254},
            },
            (SHORT_PRESS, BUTTON_3): {
                COMMAND: COMMAND_RECALL,
                CLUSTER_ID: Scenes.cluster_id,
                ENDPOINT_ID: 1,
                PARAMS: {"scene_id": 255},
            },
            (LONG_PRESS, BUTTON_3): {
                COMMAND: COMMAND_STORE,
                CLUSTER_ID: Scenes.cluster_id,
                ENDPOINT_ID: 1,
                PARAMS: {"scene_id": 255},
            },
        }
    )
    .add_to_registry()
)
