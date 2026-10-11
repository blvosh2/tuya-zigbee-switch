#include "hal/system.h"
#pragma pack(push, 1)
#include "tl_common.h"
#include "zb_api.h"
#pragma pack(pop)
#include <stdbool.h>
#include <stdint.h>

static uint16_t reset_info;

// DEEP_ANA_REG1 keeps its value through watchdog and software resets and is
// cleared only by a power cycle, so a marker left there tells the cause of
// the last reset apart.
#define RESET_MARKER_REG         DEEP_ANA_REG1
#define RESET_MARKER_RUNNING     0xA5 // Set at boot; still there after a watchdog or SDK reset
#define RESET_MARKER_SOFTWARE    0x5A // Set by hal_system_reset right before resetting

// Called once at startup, before anything can clear the status.
// Low byte: analog reg 0x44 wakeup status (bit 6 = watchdog reset).
// High byte: the marker found at boot (0x00 = power cycle,
// 0x5A = hal_system_reset, 0xA5 = any other reset).
void telink_capture_reset_info(void) {
    reset_info = analog_read(0x44) | ((uint16_t)analog_read(RESET_MARKER_REG) << 8);
    analog_write(RESET_MARKER_REG, RESET_MARKER_RUNNING);
}

uint16_t hal_system_reset_info(void) {
    return reset_info;
}

void hal_system_reset(void) {
    analog_write(RESET_MARKER_REG, RESET_MARKER_SOFTWARE);
    // Telink 8258 system reset
    mcu_reset();
}

void hal_factory_reset(void) {
    zb_factoryReset();
}
