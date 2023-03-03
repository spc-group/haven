#!/usr/bin/env python3

from caproto.server import (
    pvproperty,
    run,
    PvpropertyDouble,
    PvpropertyString,
)

from haven.simulated_ioc import ResponsiveMotorFields, IOC as IOC_


class IOC(IOC_):
    """
    An IOC that looks like an undulator.

    E.g. "25IDds:Energy"

    """
    esaf_cycle = pvproperty(value="2023-1", name="esaf:cycle", dtype=PvpropertyString)
    esaf_description = pvproperty(value="", name="esaf:description", dtype=PvpropertyString)
    esaf_enddate = pvproperty(value="", name="esaf:endDate", dtype=PvpropertyString)
    esaf_id = pvproperty(value="", name="esaf:id", dtype=PvpropertyString)
    default_prefix = "bss:"


if __name__ == "__main__":
    pvdb, run_options = IOC.parse_args()
    run(pvdb, **run_options)
