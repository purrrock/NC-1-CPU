ORG 0x00
ENTRY:
    JMP WAIT_CMD        ; [0x00..0x03] Вектор аппаратного сброса

CLOSE_FILE:
    ; Размещение в "мертвой зоне" ПЗУ (Ровно 9 нибблов)
    LDP 0xF9            ; [0x04..0x07] Указатель на STORAGE_CMD
    LDI 0x0             ; [0x08..0x09]
    STR                 ; [0x0A] MOTOR = 0 (Сброс буферов на флеш/диск)
    BOOT                ; [0x0B..0x0C] Аппаратный возврат в монитор

ORG 0x0E
RUN_XBNK:
    XBNK                ; [0x0E..0x0F] Трамплин переключения банков памяти

ORG 0x10
WAIT_CMD:
    CAL GETKEY
    
    ; Арифметический парсинг последовательных команд A, B, C, D (Экономия 19 нибблов!)
    LDI 0xA
    SUB B
    JZ LOAD_INIT        ; Кнопка A (0xA) -> Ручной ввод
    
    INC A               ; A = (10 - B) + 1
    JZ RUN_XBNK         ; Кнопка B (0xB) -> Запуск программы из RAM
    
    INC A
    JZ TAPE_LOAD_INIT   ; Кнопка C (0xC) -> Загрузка файла с флешки в RAM
    
    INC A
    JZ DUMP_INIT        ; Кнопка D (0xD) -> Ввод с дублированием на флешку
    
    BOOT                ; Любая другая кнопка -> Сброс

TAPE_LOAD_INIT:
    LDP 0xF9
    LDI 0x1             ; MOTOR=1, MODE=0 (Открытие на чтение)
    STR
    JZR WAIT_STORAGE_READY

DUMP_INIT:
    LDP 0xF9
    LDI 0x3             ; MOTOR=1, MODE=1 (Открытие на запись)
    STR

WAIT_STORAGE_READY:
    LDI 0x1             ; Маска бита READY (Bit 0)
    MOV B, A
WAIT_RDY_LOOP:
    LDR
    AND B
    JZR WAIT_RDY_LOOP   ; Ожидание готовности накопителя (READY=1)

LOAD_INIT:
    ; Единая инициализация базового адреса 0x10
    LDP 0xF3
    LDI 0x1
    STR                 ; PCH = 1
    DEX                 ; X:Y = 0xF2
    LDI 0x0
    STR                 ; PCL = 0
    
    ; Проверка режима: если сессия открыта на ЧТЕНИЕ, переходим к авто-потоку
    LDP 0xF9
    LDR
    LDI 0x1
    MOV B, A
    AND B
    SUB B               ; Если READY=1, A & 1 = 1. 1 - 1 = 0 (Z=1)
    JZ TL_LOOP

LOAD_LOOP:
    ; Интерактивный цикл ввода
    CAL SET_PTR
    LDP 0xF1            
    STR                 ; Отрисовка RAM[X:Y] на DISP_1
    
    CAL GETKEY
    LDI 0xF
    SUB B
    JZ ESCAPE           ; Если нажат F, уходим в автомат

WRITE_B:
    CAL SET_PTR
    MOV A, B
    STR                 ; Запись ниббла в User RAM
    
    ; Проверка активности режима DUMP (Эхо на флешку)
    PHA                 ; Сохраняем введённый код в стек
    LDP 0xF9
    LDI 0x1
    MOV B, A
    LDR
    AND B
    SUB B               ; Если READY == 1, прыгаем на запись потока
    JZ IS_ECHO
    PLA                 ; Если ручной LOAD, восстанавливаем стек
ADV_LOOP:
    CAL ADVANCE
    JMP LOAD_LOOP

IS_ECHO:
    DEX                 ; X:Y = 0xF8 (STORAGE_DAT)
    PLA                 ; Извлекаем ниббл из стека
    STR                 ; Синхронная запись в поток
    JMP ADV_LOOP

TL_LOOP:
    LDP 0xF9            ; STORAGE_CMD
    LDR
    LDI 0x2             ; Маска бита EOF (Bit 1)
    MOV B, A
    AND B
    SUB B               ; Если EOF == 1, (2 & 2) - 2 = 0 (Z=1)
    JZ CLOSE_FILE       ; Достигнут конец файла
    
    DEX                 ; X:Y = 0xF8 (STORAGE_DAT)
    LDR                 ; Чтение с накопителя
    MOV B, A            ; Буферизация в B
    
    CAL SET_PTR         ; X:Y = адрес записи (A перезаписан)
    MOV A, B            ; Восстановление данных из B в A (Опкод A)
    STR                 ; Корректная запись в User RAM
    
    CAL ADVANCE
    JMP TL_LOOP

ESCAPE:
    CAL GETKEY
    LDI 0x0
    SUB B
    JZ CLOSE_FILE       ; Ввод F0 -> закрыть файл и выйти
    JMP WRITE_B         ; Ввод FX -> записать X в память

SET_PTR:
    ; Безопасное формирование X:Y без затирания регистров
    LDP 0xF3
    LDR
    PHA
    DEX
    LDR
    MOV Y, A
    PLA
    MOV X, A
    LDRA
    RET

ADVANCE:
    LDP 0xF2
    LDR
    INC A
    STR
    JCR ADV_HIGH        ; Короткий переход при переполнении PCL
    RET

ADV_HIGH:
    INX                 ; X:Y = 0xF3
    LDR
    INC A
    STR
    MOV B, A
    LDI 0xE
    SUB B
    JZ CLOSE_FILE       ; Защита от затирания аппаратного стека (0xE0)
    RET

GETKEY:
    ; Поллинг клавиатуры с защитой от дребезга контактов
    LDP 0xF4
    LDI 0x1
    MOV B, A
WAIT_P:
    LDR
    AND B
    JZR WAIT_P          ; Ожидание фронта нажатия
    
    INX                 ; X:Y = 0xF5 (KBD_CODE)
    LDR
    PHA
    
    DEX
    DEX
    DEX
    DEX                 ; X:Y = 0xF1 (DISP_1)
    STR                 ; Оверлей нажатой клавиши
    
    INX
    INX
    INX                 ; X:Y = 0xF4 (GPI_KBD)
WAIT_R:
    LDR
    AND B
    SUB B
    JZR WAIT_R          ; Ожидание спада сигнала (отпускание)
    
    PLA
    MOV B, A
    RET