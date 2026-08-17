#ifndef NC1_CORE_H
#define NC1_CORE_H

#include <stdint.h>

/* * Идентификаторы регистров (ISA v4.4/v4.5)
 * Архитектура содержит 8 ортогональных 4-битных регистров.
 */
typedef enum {
    REG_A   = 0, // Accumulator
    REG_B   = 1, // Auxiliary
    REG_X   = 2, // Index High
    REG_Y   = 3, // Index Low
    REG_SP  = 4, // Stack Pointer (младший ниббл, аппаратно фиксирован префикс 0xE)
    REG_FL  = 5, // Flags
    REG_PCH = 6, // PC High
    REG_PCL = 7  // PC Low
} nc1_reg_id_t;

/* * Битовые маски для регистра флагов (REG_FL)
 * Биты 7..4 игнорируются (маскируются при записи).
 * Бит 3 - Reserved (аппаратно читается как 0).
 */
#define NC1_FLAG_Z (1U << 0) // Бит 0: Zero flag
#define NC1_FLAG_C (1U << 1) // Бит 1: Carry flag
#define NC1_FLAG_M (1U << 2) // Бит 2: Execution Bank (1 = ROM, 0 = RAM)

/*
 * Абстракция Memory-Mapped I/O (MMIO).
 * Сигнатуры функций (коллбэков) для платформозависимой обработки
 * периферии по адресам 0xF0-0xFD.
 */
typedef uint8_t (*nc1_mmio_read_cb_t)(uint8_t address);
typedef void (*nc1_mmio_write_cb_t)(uint8_t address, uint8_t data);

/*
 * Глобальный контекст состояния процессора NC-1.
 * Структура не имеет платформозависимых зависимостей.
 */
typedef struct {
    /* * Регистровый файл.
     * Используется тип uint8_t для хранения 4-битных значений.
     * Все операции записи в массив regs должны сопровождаться 
     * побитовым И с маской 0x0F (ниббл) для предотвращения переполнения.
     */
    uint8_t regs[8];

    /* * Указатели на банки памяти (Гарвардская архитектура, 8-битная адресация).
     * Физическое выделение памяти делегируется уровню платформы.
     */
    uint8_t *rom; // System Bank (256 байт)
    uint8_t *ram; // User Bank (256 байт)

    /*
     * Обработчики платформозависимого ввода-вывода.
     */
    nc1_mmio_read_cb_t mmio_read;
    nc1_mmio_write_cb_t mmio_write;

} nc1_cpu_t;

#endif // NC1_CORE_H