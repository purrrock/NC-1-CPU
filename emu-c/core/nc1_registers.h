#ifndef NC1_REGISTERS_H
#define NC1_REGISTERS_H

#include <stdint.h>
#include <stdbool.h>

/*
 * NC-1 Register File
 *
 * В архитектуре NC-1 восемь 4-битных регистров:
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
 * В C регистры хранятся в uint8_t, однако их архитектурное
 * значение ограничено младшими четырьмя битами.
 */

#define NC1_REGISTER_COUNT  8
#define NC1_NIBBLE_MASK     0x0F
#define NC1_BYTE_MASK       0xFF


/* --------------------------------------------------------------------------
 * Register IDs
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
 * Flag masks
 * -------------------------------------------------------------------------- */

/*
 * FL:
 *
 *   bit 0 = Z — Zero
 *   bit 1 = C — Carry
 *   bit 2 = M — Execution Bank
 *   bit 3 = R — Reserved
 */

#define NC1_FLAG_Z  0x01
#define NC1_FLAG_C  0x02
#define NC1_FLAG_M  0x04
#define NC1_FLAG_R  0x08


/* --------------------------------------------------------------------------
 * PCL write callback
 * -------------------------------------------------------------------------- */

/*
 * В Python RegisterFile запись PCL может вызвать callback
 * on_pcl_write().
 *
 * Callback нужен, в частности, для сохранения семантики текущего
 * Python-эмулятора, где изменение PCL может инициировать действие
 * внешнего компонента.
 *
 * Пока callback не получает дополнительных аргументов.
 */
typedef void (*nc1_pcl_write_callback_t)(void *context);


/* --------------------------------------------------------------------------
 * Register File
 * -------------------------------------------------------------------------- */

typedef struct
{
    /*
     * Восемь архитектурных 4-битных регистров.
     *
     * Каждый элемент хранится в uint8_t, но функции записи
     * обеспечивают маскирование до младшего nibble.
     */
    uint8_t regs[NC1_REGISTER_COUNT];

    /*
     * Вызывается после записи PCL.
     *
     * Может быть NULL.
     */
    nc1_pcl_write_callback_t on_pcl_write;

    /*
     * Произвольный контекст callback.
     *
     * Register File не знает, кто именно обрабатывает событие.
     */
    void *callback_context;

} nc1_register_file_t;


/* --------------------------------------------------------------------------
 * Lifecycle
 * -------------------------------------------------------------------------- */

/*
 * Инициализация Register File.
 *
 * Поведение соответствует RegisterFile.reset() в Python:
 *
 *   все регистры = 0
 *   SP = 0x0F
 *   M = 1
 */
void nc1_registers_reset(nc1_register_file_t *rf);


/* --------------------------------------------------------------------------
 * Individual register access
 * -------------------------------------------------------------------------- */

/*
 * Прямое чтение регистра.
 *
 * Значение возвращается в диапазоне 0..15.
 *
 * Для FL функция эквивалентна Python read():
 * bit 3 (Reserved) в результате не возвращается.
 */
uint8_t nc1_register_read(
    const nc1_register_file_t *rf,
    nc1_reg_id_t reg_id
);


/*
 * Запись регистра по ID.
 *
 * reg_id ограничивается тремя младшими битами.
 * value ограничивается четырьмя младшими битами.
 *
 * Запись PCL вызывает зарегистрированный callback.
 */
void nc1_register_write(
    nc1_register_file_t *rf,
    uint8_t reg_id,
    uint8_t value
);


/* --------------------------------------------------------------------------
 * Individual register properties
 * -------------------------------------------------------------------------- */

uint8_t nc1_get_a(const nc1_register_file_t *rf);
void    nc1_set_a(nc1_register_file_t *rf, uint8_t value);

uint8_t nc1_get_b(const nc1_register_file_t *rf);
void    nc1_set_b(nc1_register_file_t *rf, uint8_t value);

uint8_t nc1_get_x(const nc1_register_file_t *rf);
void    nc1_set_x(nc1_register_file_t *rf, uint8_t value);

uint8_t nc1_get_y(const nc1_register_file_t *rf);
void    nc1_set_y(nc1_register_file_t *rf, uint8_t value);

uint8_t nc1_get_sp(const nc1_register_file_t *rf);
void    nc1_set_sp(nc1_register_file_t *rf, uint8_t value);

uint8_t nc1_get_fl(const nc1_register_file_t *rf);
void    nc1_set_fl(nc1_register_file_t *rf, uint8_t value);

uint8_t nc1_get_pch(const nc1_register_file_t *rf);
void    nc1_set_pch(nc1_register_file_t *rf, uint8_t value);

uint8_t nc1_get_pcl(const nc1_register_file_t *rf);
void    nc1_set_pcl(nc1_register_file_t *rf, uint8_t value);


/* --------------------------------------------------------------------------
 * Combined registers
 * -------------------------------------------------------------------------- */

/*
 * PC = PCH:PCL
 */
uint8_t nc1_get_pc(const nc1_register_file_t *rf);
void    nc1_set_pc(nc1_register_file_t *rf, uint8_t value);


/*
 * ADDR = X:Y
 */
uint8_t nc1_get_addr(const nc1_register_file_t *rf);
void    nc1_set_addr(nc1_register_file_t *rf, uint8_t value);


/* --------------------------------------------------------------------------
 * Flags
 * -------------------------------------------------------------------------- */

uint8_t nc1_get_flag_z(const nc1_register_file_t *rf);
void    nc1_set_flag_z(nc1_register_file_t *rf, bool value);

uint8_t nc1_get_flag_c(const nc1_register_file_t *rf);
void    nc1_set_flag_c(nc1_register_file_t *rf, bool value);

uint8_t nc1_get_flag_m(const nc1_register_file_t *rf);
void    nc1_set_flag_m(nc1_register_file_t *rf, bool value);

uint8_t nc1_get_flag_r(const nc1_register_file_t *rf);
void    nc1_set_flag_r(nc1_register_file_t *rf, bool value);


/* --------------------------------------------------------------------------
 * Callback configuration
 * -------------------------------------------------------------------------- */

void nc1_registers_set_pcl_callback(
    nc1_register_file_t *rf,
    nc1_pcl_write_callback_t callback,
    void *context
);


#endif /* NC1_REGISTERS_H */