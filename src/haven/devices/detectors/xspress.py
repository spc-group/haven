"""An Xspress3 pulse processor, built on top of an EPICS area detector.

This device disables dead-time correction during staging since it is
not always reliable:
https://github.com/epics-modules/xspress3/issues/57

"""

# The datatype cannot be reliably determined from DataType_RBV if
# deadtime correction is enabled. Since dead-time correction is
# disabled it doesn't matter for now but if that changes, read out
# whether deadtime correction is enabled and determine the datatype
# that way.
#
# https://github.com/epics-modules/xspress3/issues/57


import asyncio
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from dataclasses import dataclass
from typing import SupportsIndex

import numpy as np
from ophyd_async.core import (
    Array1D,
    AsyncStatus,
    DetectorTrigger,
    DetectorTriggerLogic,
    Device,
    DeviceVector,
    PathProvider,
    SignalR,
    StrictEnum,
    TriggerInfo,
    derived_signal_r,
    soft_signal_r_and_setter,
)
from ophyd_async.epics.adcore import (
    ADArmLogic,
    ADBaseDataType,
    ADBaseIO,
    ADWriterType,
    AreaDetector,
    NDAttributeDataType,
    NDAttributeParam,
    NDPluginBaseIO,
    ndattributes_to_xml,
    prepare_exposures,
)
from ophyd_async.epics.core import epics_signal_r, epics_signal_rw, epics_signal_x

from .area_detectors import default_path_provider


class XspressTriggerMode(StrictEnum):
    SOFTWARE = "Software"
    INTERNAL = "Internal"
    IDC = "IDC"
    TTL_VETO_ONLY = "TTL Veto Only"
    TTL_BOTH = "TTL Both"
    LVDS_VETO_ONLY = "LVDS Veto Only"
    LVDS_BOTH = "LVDS Both"
    SOFTWARE_INTERNAL = "Software + Internal"


class XspressDriverIO(ADBaseIO):
    data_type: ADBaseDataType

    def __init__(self, prefix, *, name=""):
        self.trigger_mode = epics_signal_rw(XspressTriggerMode, f"{prefix}TriggerMode")
        self.erase_on_start = epics_signal_rw(bool, f"{prefix}EraseOnStart")
        self.erase = epics_signal_x(f"{prefix}ERASE")
        self.deadtime_correction = epics_signal_rw(bool, f"{prefix}CTRL_DTC")
        self.number_of_elements = epics_signal_r(int, f"{prefix}MaxSizeY_RBV")
        self.data_type = derived_signal_r(
            self._data_type, deadtime_corrected=self.deadtime_correction
        )
        super().__init__(prefix=prefix, name=name)

    def _data_type(self, deadtime_corrected: bool) -> ADBaseDataType:
        """Determine the correct data type the detector will produce.

        There is a bug in the xspress3 EPICS driver that means it does
        not report the datatype correctly, so we'll handle it in the
        ophyd-async device
        instead. https://github.com/epics-modules/xspress3/issues/57

        """
        return ADBaseDataType.FLOAT32 if deadtime_corrected else ADBaseDataType.UINT32


@dataclass
class XspressTriggerLogic(DetectorTriggerLogic):
    driver: ADBaseIO

    def get_deadtime(self, exposure: float) -> float:
        # Arbitrary value. To-do: fill this in when we know what to
        # include
        return 1e-6

    async def prepare_common(self, num: int):
        # Hardware deadtime correction is not reliable
        # https://github.com/epics-modules/xspress3/issues/57
        await self.driver.deadtime_correction.set(False)

    async def prepare_internal(self, num: int, livetime: float, deadtime: float):
        await asyncio.gather(
            self.prepare_common(num),
            prepare_exposures(self.driver, num, livetime, deadtime),
            self.driver.trigger_mode.set(XspressTriggerMode.INTERNAL),
        )

    async def prepare_level(self, num: int):
        await asyncio.gather(
            self.prepare_common(num),
            prepare_exposures(self.driver, num),
            self.driver.trigger_mode.set(XspressTriggerMode.TTL_VETO_ONLY),
        )


class XspressElement(Device):
    """Data and controls for an individual Xspress3 detector element."""

    def __init__(self, prefix: str, element_index: int, name: str = ""):
        """Parameters
        ==========
        prefix
          The detector's overall PV prefix, not including the
          e.g. "MCA1:" part.
        element_index
          This elements positional index, e.g. the first element will
          have *element_index*=0.

        """
        elem_num = element_index + 1
        self.spectrum = epics_signal_r(
            Array1D[np.float64], f"{prefix}MCA{elem_num}:ArrayData"
        )
        self.dead_time_percent = epics_signal_r(
            float, f"{prefix}C{elem_num}SCA:10:Value_RBV"
        )
        self.dead_time_factor = epics_signal_r(
            float, f"{prefix}C{elem_num}SCA:9:Value_RBV"
        )
        super().__init__(name=name)


class Xspress3Detector(AreaDetector):
    """A detector controlled by Xspress3 electronics.

    The elements of the detector are represented on the *mcas*
    attribute. The number of mcas is determined by passing *elements*
    when initializing an object. *elements* can be either an integer,
    in which case it represents to number of elements, or an iterator
    representing the index of each element.

    The following lines are equivalent.

    .. code-block:: python

      det = Xspress3Detector(..., elements=4)

      det = Xspress3Detector(..., elements=[0, 1, 2, 3])

      det = Xspress3Detector(..., elements=range(4))

    The parameter *ev_per_bin* controls the conversion from histogram
    bin to energy. This is set during calibration; changing the value
    passed into this class without re-calibrating the detector **will
    result in an incorrect conversion**.

    """

    _ophyd_labels_ = {"detectors", "xrf_detectors"}
    _old_xml_file: str | None = None

    detector_trigger: DetectorTrigger = DetectorTrigger.EXTERNAL_LEVEL

    def __init__(
        self,
        prefix: str,
        sensor_material: str,
        sensor_thickness_mm: int | float,
        path_provider: PathProvider | None = None,
        driver_suffix="det1:",
        writer_type: ADWriterType | None = ADWriterType.HDF,
        writer_suffix: str | None = None,
        plugins: dict[str, NDPluginBaseIO] | None = None,
        config_sigs: Sequence[SignalR] = (),
        name: str = "",
        ev_per_bin: float = 10.0,
        elements: int | Sequence[int] = 1,
    ):
        # Per-element MCA devices
        if isinstance(elements, SupportsIndex):
            elements = range(elements)
        self.elements = DeviceVector(
            {idx: XspressElement(prefix, element_index=idx) for idx in elements}
        )
        # Extra configuration signals
        self.ev_per_bin, _ = soft_signal_r_and_setter(float, initial_value=ev_per_bin)
        self.sensor_material, _ = soft_signal_r_and_setter(
            str, initial_value=sensor_material
        )
        self.sensor_thickness, _ = soft_signal_r_and_setter(
            float, initial_value=sensor_thickness_mm, units="mm"
        )
        # Area detector IO and control
        driver = XspressDriverIO(f"{prefix}{driver_suffix}")
        if path_provider is None:
            path_provider = default_path_provider()
        config_sigs = (
            driver.acquire_period,
            driver.acquire_time,
            self.ev_per_bin,
            self.sensor_material,
            self.sensor_thickness,
            *config_sigs,
        )
        # We need the driver to be a plugin so that NDAttributes get saved
        # Can be removed once this bug is fixed upstream:
        # https://github.com/bluesky/ophyd-async/issues/821
        # writer._plugins["camera"] = driver
        super().__init__(
            prefix=prefix,
            driver=driver,
            arm_logic=ADArmLogic(driver),
            trigger_logic=XspressTriggerLogic(driver),
            path_provider=path_provider,
            writer_type=writer_type,
            writer_suffix=writer_suffix,
            plugins=plugins,
            config_sigs=config_sigs,
            name=name,
        )

    async def setup_ndattributes(self, device_name: str, elements: Sequence[int]):
        params = ndattribute_params(device_name=device_name, elements=elements)
        xml = ndattributes_to_xml(params)
        await self.driver.nd_attributes_file.set(xml)

    @AsyncStatus.wrap
    async def stage(self) -> None:
        await super().stage()
        self._old_xml_file = await self.driver.nd_attributes_file.get_value()
        await asyncio.gather(
            self.setup_ndattributes(
                device_name=self.name, elements=self.elements.keys()
            ),
            self.driver.erase_on_start.set(False),
            self.driver.erase.trigger(),
        )

    @AsyncStatus.wrap
    async def unstage(self) -> None:
        if self._old_xml_file is not None:
            # Restore the original XML attributes file
            await self.driver.nd_attributes_file.set(self._old_xml_file)
            self._old_xml_file = None
        await super().unstage()

    @property
    def default_time_signal(self):
        return self.driver.acquire_time

    def validate_trigger_info(self, value: TriggerInfo) -> TriggerInfo:
        """Xspress3 supports internal and gate triggering."""
        if value.trigger == DetectorTrigger.EXTERNAL_EDGE:
            value = value.model_copy(update={"trigger": DetectorTrigger.EXTERNAL_LEVEL})
        if value.deadtime == 0 and value.trigger != DetectorTrigger.INTERNAL:
            value = value.model_copy(update={"deadtime": 1e-5})
        return value


def ndattribute_xml(params):
    """Convert a set of NDAttribute params to XML."""
    root = ET.Element("Attributes")
    for ndattribute in params:
        ET.SubElement(
            root,
            "Attribute",
            name=ndattribute.name,
            type="PARAM",
            source=ndattribute.param,
            addr=str(ndattribute.addr),
            datatype=ndattribute.datatype.value,
            description=ndattribute.description,
        )
    xml_text = ET.tostring(root, encoding="unicode")
    return xml_text


def ndattribute_params(
    device_name: str, elements: Sequence[int]
) -> Sequence[NDAttributeParam]:
    """Create a set of ndattribute params that can be written to the AD's
    HDF5 file.

    These parameters can then be used with something like
    :py:func:`ophyd_async.plan_stubs.setup_ndattributes` to build the
    XML.

    """
    params = []
    for idx in elements:
        new_params = [
            NDAttributeParam(
                name=f"{device_name}-element{idx}-deadtime_factor",
                param="XSP3_CHAN_DTFACTOR",
                datatype=NDAttributeDataType.DOUBLE,
                addr=idx,
                description=f"Chan {idx} DTC Factor",
            ),
            NDAttributeParam(
                name=f"{device_name}-element{idx}-deadtime_percent",
                param="XSP3_CHAN_DTPERCENT",
                datatype=NDAttributeDataType.DOUBLE,
                addr=idx,
                description=f"Chan {idx} DTC Percent",
            ),
            # NDAttributeParam(
            #     name=f"{device_name}-element{idx}-event_width",
            #     param="XSP3_EVENT_WIDTH",
            #     datatype=NDAttributeDataType.DOUBLE,
            #     addr=idx,
            #     description=f"Chan {idx} Event Width",
            # ),
            NDAttributeParam(
                name=f"{device_name}-element{idx}-clock_ticks",
                param="XSP3_CHAN_SCA0",
                datatype=NDAttributeDataType.DOUBLE,
                addr=idx,
                description=f"Chan {idx} ClockTicks",
            ),
            # NDAttributeParam(
            #     name=f"{device_name}-element{idx}-reset_ticks",
            #     param="XSP3_CHAN_SCA1",
            #     datatype=NDAttributeDataType.DOUBLE,
            #     addr=idx,
            #     description=f"Chan {idx} ResetTicks",
            # ),
            # NDAttributeParam(
            #     name=f"{device_name}-element{idx}-reset_counts",
            #     param="XSP3_CHAN_SCA2",
            #     datatype=NDAttributeDataType.DOUBLE,
            #     addr=idx,
            #     description=f"Chan {idx} ResetCounts",
            # ),
            # NDAttributeParam(
            #     name=f"{device_name}-element{idx}-all_event",
            #     param="XSP3_CHAN_SCA3",
            #     datatype=NDAttributeDataType.DOUBLE,
            #     addr=idx,
            #     description=f"Chan {idx} AllEvent",
            # ),
            # NDAttributeParam(
            #     name=f"{device_name}-element{idx}-all_good",
            #     param="XSP3_CHAN_SCA4",
            #     datatype=NDAttributeDataType.DOUBLE,
            #     addr=idx,
            #     description=f"Chan {idx} AllGood",
            # ),
            # NDAttributeParam(
            #     name=f"{device_name}-element{idx}-pileup",
            #     param="XSP3_CHAN_SCA7",
            #     datatype=NDAttributeDataType.DOUBLE,
            #     addr=idx,
            #     description=f"Chan {idx} Pileup",
            # ),
        ]
        params.extend(new_params)
    return params


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman, Yanna Chen
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2025, UChicago Argonne, LLC
#
# Distributed under the terms of the 3-Clause BSD License
#
# The full license is in the file LICENSE, distributed with this software.
#
# DISCLAIMER
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# -----------------------------------------------------------------------------
