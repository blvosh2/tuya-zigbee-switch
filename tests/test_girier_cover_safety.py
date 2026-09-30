"""Groups support and relay interlock for cover modules (Girier TS130F layout)."""
import random
import time

import pytest

from client import StubProc
from conftest import Device, DEBOUNCE_MS, MINIMUM_SWITCH_TIME_MS
from zcl_consts import (
    ZCL_ATTR_GROUP_NAME_SUPPORT,
    ZCL_CLUSTER_GROUPS,
    ZCL_COVER_SWITCH_TYPE_TOGGLE,
)

# Real config string of MODULE_GIRIER_TS130F_1GANG from device_db.yaml
GIRIER_CONFIG = "dwytrmda;TS130F-GIR;BD2u;LC2;XB5B4f;CC3C4;"
COVER_SWITCH_EP = 1
COVER_EP = 2
OPEN_BTN, CLOSE_BTN = "B5", "B4"
OPEN_RELAY, CLOSE_RELAY = "C3", "C4"


def pin_num(pin: str) -> int:
    return (ord(pin[0].upper()) - ord("A")) * 16 + int(pin[1:])


@pytest.fixture
def girier() -> Device:
    p = StubProc(device_config=GIRIER_CONFIG).start()
    try:
        d = Device(p)
        # Wall switch released (floating inputs idle high on this module)
        d.set_gpio(OPEN_BTN, 1)
        d.set_gpio(CLOSE_BTN, 1)
        d.step_time(MINIMUM_SWITCH_TIME_MS + DEBOUNCE_MS)
        d.zcl_cover_switch_set_switch_type(COVER_SWITCH_EP, ZCL_COVER_SWITCH_TYPE_TOGGLE)
        yield d
    finally:
        p.stop()


def relay_writes(d: Device) -> list[tuple[str, int]]:
    """Ordered (pin, value) writes to the two motor relays since last clear_events()."""
    time.sleep(0.02)  # let the reader thread drain pending events
    names = {pin_num(OPEN_RELAY): OPEN_RELAY, pin_num(CLOSE_RELAY): CLOSE_RELAY}
    out = []
    for e in list(d._events):
        if e.kind != "gpio":
            continue
        pin = int(e.payload.get("pin", "-1"))
        if pin in names:
            out.append((names[pin], int(e.payload["value"])))
    return out


def assert_never_both_on(writes: list[tuple[str, int]], start: dict[str, int]) -> None:
    state = dict(start)
    for i, (pin, val) in enumerate(writes):
        state[pin] = val
        assert not (state[OPEN_RELAY] and state[CLOSE_RELAY]), (
            f"both relays energized after write #{i} {pin}={val}; writes={writes}"
        )


def relay_state(d: Device) -> dict[str, int]:
    return {p: int(d.get_gpio(p, refresh=True)) for p in (OPEN_RELAY, CLOSE_RELAY)}


# ---------------------------------------------------------------------------
# Groups cluster (upstream issue #522)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cfg,cover_eps", [
    (GIRIER_CONFIG, [COVER_EP]),
    ("X;Y;CA0A1;", [1]),
    ("X;Y;XA0A1u;CB0B1;XC0C1u;CD0D1;", [3, 4]),
])
def test_cover_endpoints_have_groups_cluster(cfg: str, cover_eps: list[int]):
    p = StubProc(device_config=cfg).start()
    try:
        d = Device(p)
        for ep in cover_eps:
            res = d.p.exec(f"zcl_read {ep} 0x{ZCL_CLUSTER_GROUPS:04X} 0x{ZCL_ATTR_GROUP_NAME_SUPPORT:04X}")
            assert res.ok, f"endpoint {ep} has no Groups cluster: {res.payload}"
    finally:
        p.stop()


# ---------------------------------------------------------------------------
# Relay interlock
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cmd,on_pin,off_pin", [
    ("open", OPEN_RELAY, CLOSE_RELAY),
    ("close", CLOSE_RELAY, OPEN_RELAY),
])
def test_opposite_relay_released_before_energizing(girier: Device, cmd: str, on_pin: str, off_pin: str):
    d = girier
    d.clear_events()
    getattr(d, f"zcl_cover_{cmd}")(COVER_EP)
    writes = relay_writes(d)
    on_idx = writes.index((on_pin, 1))
    assert (off_pin, 0) in writes[:on_idx], f"{off_pin} not released before {on_pin} energized: {writes}"


@pytest.mark.parametrize("first,second", [
    ("zigbee_open", "switch_close"),
    ("switch_close", "zigbee_open"),
    ("zigbee_close", "switch_open"),
    ("switch_open", "zigbee_close"),
])
@pytest.mark.parametrize("gap_ms", [0, 1, 5, 50, 150, 199, 200, 250])
def test_zigbee_and_wall_switch_at_same_time(girier: Device, first: str, second: str, gap_ms: int):
    """The reported incident: a Zigbee command and a wall-switch flip arrive together."""
    d = girier
    d.freeze_time()
    start = relay_state(d)
    d.clear_events()

    def do(action: str) -> None:
        if action == "zigbee_open":
            d.zcl_cover_open(COVER_EP)
        elif action == "zigbee_close":
            d.zcl_cover_close(COVER_EP)
        elif action == "switch_open":
            d.set_gpio(CLOSE_BTN, 1)
            d.set_gpio(OPEN_BTN, 0)
        elif action == "switch_close":
            d.set_gpio(OPEN_BTN, 1)
            d.set_gpio(CLOSE_BTN, 0)

    do(first)
    d.step_time(gap_ms)
    do(second)
    for _ in range(20):
        d.step_time(25)

    assert_never_both_on(relay_writes(d), start)
    final = relay_state(d)
    assert not (final[OPEN_RELAY] and final[CLOSE_RELAY])


@pytest.mark.parametrize("seed", range(6))
def test_random_zigbee_and_switch_storm(girier: Device, seed: int):
    d = girier
    d.freeze_time()
    rng = random.Random(seed)
    start = relay_state(d)
    d.clear_events()
    for _ in range(150):
        action = rng.choice(["zo", "zc", "zs", "so", "sc", "s0", "pos"])
        if action == "zo":
            d.zcl_cover_open(COVER_EP)
        elif action == "zc":
            d.zcl_cover_close(COVER_EP)
        elif action == "zs":
            d.zcl_cover_stop(COVER_EP)
        elif action == "so":
            d.set_gpio(CLOSE_BTN, 1)
            d.set_gpio(OPEN_BTN, 0)
        elif action == "sc":
            d.set_gpio(OPEN_BTN, 1)
            d.set_gpio(CLOSE_BTN, 0)
        elif action == "s0":
            d.set_gpio(OPEN_BTN, 1)
            d.set_gpio(CLOSE_BTN, 1)
        else:
            d.zcl_cover_goto_position(COVER_EP, rng.randint(0, 100))
        d.step_time(rng.choice([0, 1, 3, 10, 40, 120, 199, 201, 400]))
    assert_never_both_on(relay_writes(d), start)
