"""Boot counter and reset reason in the Basic cluster (diagnostics)."""
from client import StubProc
from conftest import Device

ZCL_CLUSTER_BASIC = 0x0000
ZCL_ATTR_BASIC_BOOT_COUNT = 0xFF03
ZCL_ATTR_BASIC_RESET_INFO = 0xFF04


def test_boot_count_and_reset_info_readable():
    p = StubProc(device_config="X;Y;LC2i;XC4C0fB5f;CD7D2D4A0;").start()
    try:
        d = Device(p)
        assert int(d.read_zigbee_attr(1, ZCL_CLUSTER_BASIC, ZCL_ATTR_BASIC_BOOT_COUNT)) == 1
        assert int(d.read_zigbee_attr(1, ZCL_CLUSTER_BASIC, ZCL_ATTR_BASIC_RESET_INFO)) == 0
    finally:
        p.stop()
