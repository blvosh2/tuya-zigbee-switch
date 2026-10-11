#include "hal/system.h"
#pragma pack(push, 1)
#include "tl_common.h"
#include "zb_api.h"
#pragma pack(pop)
#include <stdbool.h>
#include <stdint.h>

static uint16_t reset_info;

// Called once at startup, before anything can clear the status.
// Low byte: analog reg 0x44 wakeup status (bit 6 = watchdog reset).
// High byte: pm mcu status (0 = boot, 1 = deep retention, 2 = deep sleep).
void telink_capture_reset_info(void) {
    reset_info = analog_read(0x44) | ((uint16_t)pm_get_mcu_status() << 8);
}

uint16_t hal_system_reset_info(void) {
    return reset_info;
}

void hal_system_reset(void) {
    // Telink 8258 system reset
    mcu_reset();
}

void hal_factory_reset(void) {
    zb_factoryReset();
}
