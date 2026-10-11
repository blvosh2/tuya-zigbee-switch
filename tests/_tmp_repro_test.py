import sys; sys.path.insert(0, "tests")
from client import StubProc
from conftest import Device, DEBOUNCE_MS, MINIMUM_SWITCH_TIME_MS
CFG = "cet6ch1r;TS130F-LT7;LC2i;XC4C0fB5f;CD7D2D4A0;"
def test_close_rate():
    p = StubProc(device_config=CFG).start()
    try:
        d = Device(p)
        for b in ("C4","C0","B5"): d.set_gpio(b, 1)
        d.step_time(MINIMUM_SWITCH_TIME_MS + DEBOUNCE_MS)
        d.zcl_cover_set_open_time(2, 240); d.zcl_cover_set_close_time(2, 220)
        d.step_time(500)
        d.click_button("C0")
        out=[]
        for i in range(12):
            d.step_time(1000)
            out.append((d.zcl_cover_get_position(2), d.zcl_cover_get_moving(2), int(d.get_gpio("A0", refresh=True))))
        print(out)
    finally:
        p.stop()
