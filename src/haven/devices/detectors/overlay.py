from ophyd_async.epics.adcore._core_io import NDPluginBaseIO
from ophyd_async.epics.core import epics_signal_r, epics_signal_rw, epics_signal_rw_rbv
from ophyd_async.core import DeviceVector, Device, StrictEnum


class Shape(StrictEnum):
    CROSS = "Cross"
    RECTANGLE = "Rectangle"
    ELLIPSE = "Ellipse"
    TEXT = "Text"


class DrawMode(StrictEnum):
    SET = "Set"
    XOR = "XOR"


class Font(StrictEnum):
    SIX_BY_THIRTEEN = "6x13"
    SIX_BY_THIRTEEN_BOLD = "6x13 Bold"
    NINE_BY_FIFTEEN = "9x15"
    NINE_BY_FIFTEEN_BOLD = "9x15 Bold"


class Overlay(Device):
    def __init__(self, prefix: str, name: str = ""):
        # Modal parameters
        self.use = epics_signal_rw_rbv(bool, f"{prefix}Use")
        self.description = epics_signal_rw_rbv(str, f"{prefix}Name")
        self.shape = epics_signal_rw_rbv(Shape, f"{prefix}Shape")
        self.draw_mode = epics_signal_rw_rbv(DrawMode, f"{prefix}DrawMode")
        self.red = epics_signal_rw_rbv(int, f"{prefix}Red")
        self.green = epics_signal_rw_rbv(int, f"{prefix}Green")
        self.blue = epics_signal_rw_rbv(int, f"{prefix}Blue")
        self.display_text = epics_signal_rw_rbv(str, f"{prefix}DisplayText")
        self.time_format = epics_signal_rw_rbv(str, f"{prefix}TimeStampFormat")
        self.font = epics_signal_rw_rbv(Font, f"{prefix}Font")
        # Overlay parameters
        self.position_x = epics_signal_rw_rbv(int, f"{prefix}PositionX")
        self.center_x = epics_signal_rw_rbv(int, f"{prefix}CenterX")
        self.size_x = epics_signal_rw_rbv(int, f"{prefix}SizeX")
        self.width_x = epics_signal_rw_rbv(int, f"{prefix}WidthX")
        self.position_y = epics_signal_rw_rbv(int, f"{prefix}PositionY")
        self.center_y = epics_signal_rw_rbv(int, f"{prefix}CenterY")
        self.size_y = epics_signal_rw_rbv(int, f"{prefix}SizeY")
        self.width_y = epics_signal_rw_rbv(int, f"{prefix}WidthY")
        super().__init__(name=name)


class OverlayPlugin(NDPluginBaseIO):
    def __init__(self, prefix: str, name: str = "", *args, **kwargs):
        overlays = 7
        self.overlays = DeviceVector({
            idx: Overlay(f"{prefix}{idx+1}:") for idx in range(overlays)
        })
        super().__init__(prefix=prefix, name=name, *args, **kwargs)
