"""Tradfri Light Quirk."""
from zigpy.profiles import zha, zll
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PollControl,
    Scenes,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink

from . import IKEA, ColorTemperatureCluster
from .. import Bus
from ..const import (
    ENDPOINTS,
    MODELS_INFO,
    PROFILE_ID,
    DEVICE_TYPE,
    INPUT_CLUSTERS,
    OUTPUT_CLUSTERS,
)


class TradfriLED1624G9(CustomDevice):
    """
    Tradfri LED1624G9 light bulbs, dimmable, color, white spectrum.
    """

    # def __init__(self, *args, **kwargs):
    #     """Init."""
    #     self.color_temperature_bus = Bus()
    #     super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [
            (IKEA, "TRADFRI bulb E14 CWS opal 600lm"),
            (IKEA, "TRADFRI bulb E27 CWS opal 600lm"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=49246 device_type=512
            # device_version=2
            # input_clusters=[0, 3, 4, 5, 6, 8, 768, 2821, 4096]
            # output_clusters=[5, 25, 32, 4096]>
            1: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.COLOR_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    Diagnostic.cluster_id,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Scenes.cluster_id,
                    Ota.cluster_id,
                    PollControl.cluster_id,
                    LightLink.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.EXTENDED_COLOR_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    ColorTemperatureCluster,  # Color.cluster_id,
                    Diagnostic.cluster_id,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Scenes.cluster_id,
                    Ota.cluster_id,
                    PollControl.cluster_id,
                    LightLink.cluster_id,
                ],
            }
        }
    }
