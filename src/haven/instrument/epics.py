import asyncio

from epics import PV


async def caget(pvname: str, timeout: float = 2.0):
    """Asynchronous wrapper around pyepics.caget.

    Returns
    =======
    value
      Current PV value retrieved from the IOC.

    """
    loop = asyncio.get_running_loop()
    future = loop.create_future()

    # Callback for when the value changes
    def check_value(pvname, value, status, **kwargs):
        if status is None:
            # Not a real update
            return
        elif status == 0:
            future.set_result(value)
        else:
            exc = RuntimeError(f"Could not caget value for PV {pvname}")
            future.set_exception(exc)

    # Wait for the real value to come in from the IOC
    pv = PV(pvname, callback=check_value, auto_monitor=True)
    await asyncio.wait_for(future, timeout=timeout)
    # Clean up
    del pv
    return future.result()
