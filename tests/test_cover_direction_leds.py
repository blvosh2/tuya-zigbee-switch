"""Direction LEDs on cover endpoints: C<open><close>[<open led>[i]<close led>[i]]."""
import pytest

from client import StubProc
from conftest import Device, DEBOUNCE_MS, MINIMUM_SWITCH_TIME_MS

# LoraTap SC400ZB-US-V7 layout: blue LED on the open button (D4) and on the
# close button (A0), both driven through transistors (active high).
LED_CONFIG = "cet6ch1r;TS130F-LT7;LC2i;XC4C0fB5f;CD7D2D4A0;"
COVER_EP = 2
OPEN_BTN, CLOSE_BTN, STOP_BTN = "C4", "C0", "B5"
OPEN_LED, CLOSE_LED = "D4", "A0"


def make_device(cfg: str) -> tuple[StubProc, Device]:
    p = StubProc(device_config=cfg).start()
    d = Device(p)
    # Touch outputs idle high (active low)
    for btn in (OPEN_BTN, CLOSE_BTN, STOP_BTN):
        d.set_gpio(btn, 1)
    d.step_time(MINIMUM_SWITCH_TIME_MS + DEBOUNCE_MS)
    d.zcl_cover_set_open_time(COVER_EP, 100)
    d.zcl_cover_set_close_time(COVER_EP, 100)
    return p, d


@pytest.fixture
def loratap() -> Device:
    p, d = make_device(LED_CONFIG)
    try:
        yield d
    finally:
        p.stop()


def leds(d: Device, open_led: str = OPEN_LED, close_led: str = CLOSE_LED) -> tuple[int, int]:
    return (int(d.get_gpio(open_led, refresh=True)), int(d.get_gpio(close_led, refresh=True)))


def test_leds_off_at_boot(loratap: Device):
    assert leds(loratap) == (0, 0)


def test_open_lights_open_led_until_stop(loratap: Device):
    d = loratap
    d.zcl_cover_open(COVER_EP)
    assert leds(d) == (1, 0)
    d.zcl_cover_stop(COVER_EP)
    d.step_time(MINIMUM_SWITCH_TIME_MS)
    assert leds(d) == (0, 0)


def test_close_lights_close_led_until_stop(loratap: Device):
    d = loratap
    d.zcl_cover_close(COVER_EP)
    assert leds(d) == (0, 1)
    d.zcl_cover_stop(COVER_EP)
    d.step_time(MINIMUM_SWITCH_TIME_MS)
    assert leds(d) == (0, 0)


def test_led_follows_direction_change(loratap: Device):
    d = loratap
    d.zcl_cover_open(COVER_EP)
    d.step_time(1000)
    d.zcl_cover_close(COVER_EP)
    for _ in range(10):
        d.step_time(100)
    assert leds(d) == (0, 1)


def test_led_off_after_auto_stop(loratap: Device):
    d = loratap
    d.zcl_cover_goto_position(COVER_EP, 60)
    assert leds(d) == (1, 0)
    for _ in range(40):
        d.step_time(500)
    assert d.zcl_cover_get_position(COVER_EP) == 60
    assert leds(d) == (0, 0)


def test_wall_buttons_drive_leds(loratap: Device):
    d = loratap
    d.click_button(CLOSE_BTN)
    d.step_time(DEBOUNCE_MS)
    assert leds(d) == (0, 1)
    d.click_button(STOP_BTN)
    d.step_time(MINIMUM_SWITCH_TIME_MS + DEBOUNCE_MS)
    assert leds(d) == (0, 0)


def test_leds_follow_logical_direction_with_motor_reversal(loratap: Device):
    d = loratap
    d.zcl_cover_motor_reversal_set(COVER_EP, 1)
    d.step_time(MINIMUM_SWITCH_TIME_MS)
    d.zcl_cover_open(COVER_EP)
    assert leds(d) == (1, 0)


def test_inverted_leds():
    p, d = make_device("cet6ch1r;TS130F-LT7;LC2i;XC4C0fB5f;CD7D2D4iA0i;")
    try:
        assert leds(d) == (1, 1)
        d.zcl_cover_close(COVER_EP)
        assert leds(d) == (1, 0)
    finally:
        p.stop()


@pytest.mark.parametrize("cfg", ["X;Y;CD7D2;", "X;Y;CD7D2D4;"])
def test_without_leds_cover_still_works(cfg: str):
    p = StubProc(device_config=cfg).start()
    try:
        d = Device(p)
        d.step_time(MINIMUM_SWITCH_TIME_MS)
        d.zcl_cover_open(1)
        assert d.zcl_cover_get_moving(1) != 0
    finally:
        p.stop()
