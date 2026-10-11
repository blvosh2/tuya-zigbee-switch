#ifndef _HAL_SYSTEM_H_
#define _HAL_SYSTEM_H_

#include <stdint.h>

/**
 * Reset the system/microcontroller
 */
void __attribute__((noreturn)) hal_system_reset(void);

void hal_factory_reset(void);

/**
 * Platform specific reason of the last reset, captured at startup.
 * 0 when unknown. Used for diagnostics only.
 */
uint16_t hal_system_reset_info(void);

#endif /* _HAL_SYSTEM_H_ */
