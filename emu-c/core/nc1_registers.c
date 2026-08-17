#include "nc1_registers.h"
#include <stddef.h>

/* --------------------------------------------------------------------------
 * Internal helper
 * -------------------------------------------------------------------------- */

/*
 * Все архитектурные регистры NC-1 являются 4-битными.
 *
 * Поэтому любое значение, записанное в регистр, должно быть
 * ограничено младшими четырьмя битами.
 */
static uint8_t nibble(uint8_t value)
{
    return value & NC1_NIBBLE_MASK;
}


/* --------------------------------------------------------------------------
 * Lifecycle
 * -------------------------------------------------------------------------- */

void nc1_registers_reset(nc1_register_file_t *rf)
{
    /*
     * Python:
     *
     *     self.regs = [0] * 8
     *     self.sp = 0x0F
     *     self.set_flag_m(1)
     */
    for (uint8_t i = 0; i < NC1_REGISTER_COUNT; ++i)
    {
        rf->regs[i] = 0;
    }

    rf->regs[NC1_REG_SP] = 0x0F;

    /*
     * M = 1 после аппаратного reset:
     * System Bank / ROM.
     */
    rf->regs[NC1_REG_FL] |= NC1_FLAG_M;
}


/* --------------------------------------------------------------------------
 * Generic register access
 * -------------------------------------------------------------------------- */

uint8_t nc1_register_read(
    const nc1_register_file_t *rf,
    nc1_reg_id_t reg_id)
{
    /*
     * Python:
     *
     *     reg_id &= 0x07
     */
    uint8_t id = ((uint8_t)reg_id) & 0x07;

    if (id == NC1_REG_FL)
    {
        /*
         * В Python read():
         *
         *     if reg_id == REG_FL:
         *         return self.fl & 0x07
         *
         * Поэтому Reserved bit 3 здесь намеренно отбрасывается.
         */
        return rf->regs[NC1_REG_FL] & 0x07;
    }

    return nibble(rf->regs[id]);
}


void nc1_register_write(
    nc1_register_file_t *rf,
    uint8_t reg_id,
    uint8_t value)
{
    /*
     * Python:
     *
     *     reg_id &= 0x07
     *     val &= 0x0F
     */
    uint8_t id = reg_id & 0x07;
    uint8_t val = nibble(value);

    if (id == NC1_REG_PCL)
    {
        /*
         * Используем setter, поскольку запись PCL должна вызвать
         * on_pcl_write callback.
         */
        nc1_set_pcl(rf, val);
    }
    else if (id == NC1_REG_FL)
    {
        /*
         * Python write() вызывает self.fl = val.
         * Setter FL маскирует значение до 4 бит.
         */
        rf->regs[NC1_REG_FL] = val;
    }
    else
    {
        rf->regs[id] = val;
    }
}


/* --------------------------------------------------------------------------
 * Individual registers
 * -------------------------------------------------------------------------- */

uint8_t nc1_get_a(const nc1_register_file_t *rf)
{
    return rf->regs[NC1_REG_A];
}

void nc1_set_a(nc1_register_file_t *rf, uint8_t value)
{
    rf->regs[NC1_REG_A] = nibble(value);
}


uint8_t nc1_get_b(const nc1_register_file_t *rf)
{
    return rf->regs[NC1_REG_B];
}

void nc1_set_b(nc1_register_file_t *rf, uint8_t value)
{
    rf->regs[NC1_REG_B] = nibble(value);
}


uint8_t nc1_get_x(const nc1_register_file_t *rf)
{
    return rf->regs[NC1_REG_X];
}

void nc1_set_x(nc1_register_file_t *rf, uint8_t value)
{
    rf->regs[NC1_REG_X] = nibble(value);
}


uint8_t nc1_get_y(const nc1_register_file_t *rf)
{
    return rf->regs[NC1_REG_Y];
}

void nc1_set_y(nc1_register_file_t *rf, uint8_t value)
{
    rf->regs[NC1_REG_Y] = nibble(value);
}


uint8_t nc1_get_sp(const nc1_register_file_t *rf)
{
    return rf->regs[NC1_REG_SP];
}

void nc1_set_sp(nc1_register_file_t *rf, uint8_t value)
{
    rf->regs[NC1_REG_SP] = nibble(value);
}


uint8_t nc1_get_fl(const nc1_register_file_t *rf)
{
    /*
     * Python property fl:
     *
     *     return self.regs[self.REG_FL] & 0x0F
     */
    return rf->regs[NC1_REG_FL] & NC1_NIBBLE_MASK;
}

void nc1_set_fl(nc1_register_file_t *rf, uint8_t value)
{
    rf->regs[NC1_REG_FL] = nibble(value);
}


uint8_t nc1_get_pch(const nc1_register_file_t *rf)
{
    return rf->regs[NC1_REG_PCH];
}

void nc1_set_pch(nc1_register_file_t *rf, uint8_t value)
{
    rf->regs[NC1_REG_PCH] = nibble(value);
}


uint8_t nc1_get_pcl(const nc1_register_file_t *rf)
{
    return rf->regs[NC1_REG_PCL];
}

void nc1_set_pcl(nc1_register_file_t *rf, uint8_t value)
{
    rf->regs[NC1_REG_PCL] = nibble(value);

    /*
     * В Python callback вызывается ПОСЛЕ записи PCL.
     *
     * Проверяем NULL, поскольку callback является необязательным.
     */
    if (rf->on_pcl_write != NULL)
    {
        rf->on_pcl_write(rf->callback_context);
    }
}


/* --------------------------------------------------------------------------
 * Combined registers
 * -------------------------------------------------------------------------- */

uint8_t nc1_get_pc(const nc1_register_file_t *rf)
{
    /*
     * PC = PCH:PCL
     *
     * PCH занимает старший nibble,
     * PCL — младший.
     */
    return (uint8_t)(
        (nc1_get_pch(rf) << 4) |
        nc1_get_pcl(rf)
    );
}


void nc1_set_pc(nc1_register_file_t *rf, uint8_t value)
{
    /*
     * Аналог Python:
     *
     *     self.pch = (val >> 4) & 0x0F
     *     self.pcl = val & 0x0F
     *
     * Поэтому установка PC вызывает callback PCL.
     */
    nc1_set_pch(rf, (value >> 4) & 0x0F);
    nc1_set_pcl(rf, value & 0x0F);
}


uint8_t nc1_get_addr(const nc1_register_file_t *rf)
{
    /*
     * ADDR = X:Y
     */
    return (uint8_t)(
        (nc1_get_x(rf) << 4) |
        nc1_get_y(rf)
    );
}


void nc1_set_addr(nc1_register_file_t *rf, uint8_t value)
{
    nc1_set_x(rf, (value >> 4) & 0x0F);
    nc1_set_y(rf, value & 0x0F);
}


/* --------------------------------------------------------------------------
 * Flags
 * -------------------------------------------------------------------------- */

bool nc1_get_flag_z(const nc1_register_file_t *rf)
{
    return (nc1_get_fl(rf) & NC1_FLAG_Z) ? true : false;
}


void nc1_set_flag_z(nc1_register_file_t *rf, bool value)
{
    if (value)
    {
        rf->regs[NC1_REG_FL] |= NC1_FLAG_Z;
    }
    else
    {
        rf->regs[NC1_REG_FL] &= (uint8_t)~NC1_FLAG_Z;
    }
}


bool nc1_get_flag_c(const nc1_register_file_t *rf)
{
    return (nc1_get_fl(rf) & NC1_FLAG_C) ? true : false;
}


void nc1_set_flag_c(nc1_register_file_t *rf, bool value)
{
    if (value)
    {
        rf->regs[NC1_REG_FL] |= NC1_FLAG_C;
    }
    else
    {
        rf->regs[NC1_REG_FL] &= (uint8_t)~NC1_FLAG_C;
    }
}


bool nc1_get_flag_m(const nc1_register_file_t *rf)
{
    return (nc1_get_fl(rf) & NC1_FLAG_M) ? true : false;
}


void nc1_set_flag_m(nc1_register_file_t *rf, bool value)
{
    if (value)
    {
        rf->regs[NC1_REG_FL] |= NC1_FLAG_M;
    }
    else
    {
        rf->regs[NC1_REG_FL] &= (uint8_t)~NC1_FLAG_M;
    }
}


bool nc1_get_flag_r(const nc1_register_file_t *rf)
{
    return (nc1_get_fl(rf) & NC1_FLAG_R) ? true : false;
}


void nc1_set_flag_r(nc1_register_file_t *rf, bool value)
{
    if (value)
    {
        rf->regs[NC1_REG_FL] |= NC1_FLAG_R;
    }
    else
    {
        rf->regs[NC1_REG_FL] &= (uint8_t)~NC1_FLAG_R;
    }
}


/* --------------------------------------------------------------------------
 * PCL callback
 * -------------------------------------------------------------------------- */

void nc1_registers_set_pcl_callback(
    nc1_register_file_t *rf,
    nc1_pcl_write_callback_t callback,
    void *context)
{
    rf->on_pcl_write = callback;
    rf->callback_context = context;
}