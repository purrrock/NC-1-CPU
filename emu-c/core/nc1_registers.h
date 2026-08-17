#ifndef NC1_REGISTERS_H
#define NC1_REGISTERS_H

#include <stdint.h>
#include <stdbool.h>

/*
 * NC-1 Register File
 *
 * The NC-1 architecture has eight 4-bit registers:
 *
 *   0: A
 *   1: B
 *   2: X
 *   3: Y
 *   4: SP
 *   5: FL
 *   6: PCH
 *   7: PCL
 *
 * Registers are stored in uint8_t, but only the low nibble is
 * architecturally significant.
 */

#define NC1_REGISTER_COUNT 8u
#define NC1_NIBBLE_MASK    0x0Fu


/* --------------------------------------------------------------------------
 * Register identifiers
 * -------------------------------------------------------------------------- */

typedef enum
{
    NC1_REG_A   = 0,
    NC1_REG_B   = 1,
    NC1_REG_X   = 2,
    NC1_REG_Y   = 3,
    NC1_REG_SP  = 4,
    NC1_REG_FL  = 5,
    NC1_REG_PCH = 6,
    NC1_REG_PCL = 7

} nc1_reg_id_t;


/* --------------------------------------------------------------------------
 * FL bit assignments
 * -------------------------------------------------------------------------- */

/*
 * FL:
 *
 *   bit 0 = Z — Zero
 *   bit 1 = C — Carry
 *   bit 2 = M — Memory bank
 *   bit 3 = R — Reserved
 */

#define NC1_FLAG_Z 0x01u
#define NC1_FLAG_C 0x02u
#define NC1_FLAG_M 0x04u
#define NC1_FLAG_R 0x08u


/* --------------------------------------------------------------------------
 * PCL write callback
 * -------------------------------------------------------------------------- */

/*
 * Called after PCL is written.
 *
 * The callback is used by the CPU core to reproduce the behavior of the
 * Python implementation, where a direct PCL write marks that a jump
 * occurred during the current instruction cycle.
 */
typedef void (*nc1_pcl_write_callback_t)(void *context);


/* --------------------------------------------------------------------------
 * Register File
 * -------------------------------------------------------------------------- */

typedef struct
{
    /*
     * Eight architectural 4-bit registers.
     *
     * Stored as uint8_t because C has no native 4-bit integer type.
     * Register-writing functions enforce the 0x0F mask.
     */
    uint8_t regs[NC1_REGISTER_COUNT];

    /*
     * Optional callback invoked after PCL is written.
     */
    nc1_pcl_write_callback_t on_pcl_write;

    /*
     * Opaque user-defined callback context.
     *
     * The Register File does not need to know what owns the callback.
     */
    void *callback_context;

} nc1_register_file_t;


/* --------------------------------------------------------------------------
 * Lifecycle
 * -------------------------------------------------------------------------- */

/*
 * Reset the register file.
 *
 * According to the current Python implementation:
 *
 *   all registers = 0
 *   SP = 0x0F
 *   M  = 1
 */
void nc1_registers_reset(nc1_register_file_t *rf);


/* --------------------------------------------------------------------------
 * Generic register access
 * -------------------------------------------------------------------------- */

/*
 * Read a register by register ID.
 *
 * The register ID is limited to 3 bits.
 *
 * For FL, this function reproduces RegisterFile.read():
 * only bits Z/C/M (bits 0..2) are returned.
 */
uint8_t nc1_register_read(
    const nc1_register_file_t *rf,
    nc1_reg_id_t reg_id
);


/*
 * Write a register by register ID.
 *
 * Register ID is limited to 3 bits.
 * Value is limited to 4 bits.
 *
 * Writing PCL invokes the configured PCL callback.
 */
void nc1_register_write(
    nc1_register_file_t *rf,
    uint8_t reg_id,
    uint8_t value
);


/* --------------------------------------------------------------------------
 * Individual registers
 * -------------------------------------------------------------------------- */

uint8_t nc1_get_a(const nc1_register_file_t *rf);
void nc1_set_a(nc1_register_file_t *rf, uint8_t value);

uint8_t nc1_get_b(const nc1_register_file_t *rf);
void nc1_set_b(nc1_register_file_t *rf, uint8_t value);

uint8_t nc1_get_x(const nc1_register_file_t *rf);
void nc1_set_x(nc1_register_file_t *rf, uint8_t value);

uint8_t nc1_get_y(const nc1_register_file_t *rf);
void nc1_set_y(nc1_register_file_t *rf, uint8_t value);

uint8_t nc1_get_sp(const nc1_register_file_t *rf);
void nc1_set_sp(nc1_register_file_t *rf, uint8_t value);

uint8_t nc1_get_fl(const nc1_register_file_t *rf);
void nc1_set_fl(nc1_register_file_t *rf, uint8_t value);

uint8_t nc1_get_pch(const nc1_register_file_t *rf);
void nc1_set_pch(nc1_register_file_t *rf, uint8_t value);

uint8_t nc1_get_pcl(const nc1_register_file_t *rf);
void nc1_set_pcl(nc1_register_file_t *rf, uint8_t value);


/* --------------------------------------------------------------------------
 * Combined registers
 * -------------------------------------------------------------------------- */

/*
 * PC = PCH:PCL
 */
uint8_t nc1_get_pc(const nc1_register_file_t *rf);
void nc1_set_pc(nc1_register_file_t *rf, uint8_t value);


/*
 * ADDR = X:Y
 */
uint8_t nc1_get_addr(const nc1_register_file_t *rf);
void nc1_set_addr(nc1_register_file_t *rf, uint8_t value);


/* --------------------------------------------------------------------------
 * Flags
 * -------------------------------------------------------------------------- */

bool nc1_get_flag_z(const nc1_register_file_t *rf);
void nc1_set_flag_z(nc1_register_file_t *rf, bool value);

bool nc1_get_flag_c(const nc1_register_file_t *rf);
void nc1_set_flag_c(nc1_register_file_t *rf, bool value);

bool nc1_get_flag_m(const nc1_register_file_t *rf);
void nc1_set_flag_m(nc1_register_file_t *rf, bool value);

bool nc1_get_flag_r(const nc1_register_file_t *rf);
void nc1_set_flag_r(nc1_register_file_t *rf, bool value);


/* --------------------------------------------------------------------------
 * PCL callback configuration
 * -------------------------------------------------------------------------- */

void nc1_registers_set_pcl_callback(
    nc1_register_file_t *rf,
    nc1_pcl_write_callback_t callback,
    void *context
);


#endif /* NC1_REGISTERS_H */