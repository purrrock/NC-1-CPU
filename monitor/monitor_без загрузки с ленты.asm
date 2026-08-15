ORG 0x00
ENTRY:
    JMP WAIT_CMD        ; [0x00..0x03] Вектор аппаратного сброса

CLOSE_FILE:
    ; Размещение в "мертвой зоне" ПЗУ
    LDP 0xF9            ; [0x04..0x07] Указатель на STORAGE_CMD
    LDI 0x0             ; [0x08..0x09]
    STR                 ; [0x0A] MOTOR = 0 (Безопасное закрытие и сброс буферов на флеш/диск)
    BOOT                ; [0x0B..0x0C] Аппаратный возврат в монитор

ORG 0x0E
RUN_XBNK:
    XBNK                ; [0x0E..0x0F] Трамплин переключения банков памяти

ORG 0x10
WAIT_CMD:
    CAL GETKEY
    
    ; Эхо нажатой команды на DISP_0
    LDP 0xF0
    MOV A, B
    STR
    
    ; Парсинг команд
    LDI 0xB
    SUB B
    JZ RUN_XBNK         ; B -> Абсолютный прыжок на трамплин
    
    LDI 0xA
    SUB B
    JZ LOAD_INIT        ; A -> Абсолютный прыжок на загрузку
    
    LDI 0xD
    SUB B
    JZR DUMP_INIT       ; D -> Короткий прыжок (смещение +2)
    
    BOOT                ; Любая другая кнопка -> программный сброс

DUMP_INIT:
    ; Инициализация записи на внешний носитель
    LDP 0xF9
    LDI 0x3             ; MOTOR=1 (бит 0), MODE=1 (Write, бит 1) -> 0x3
    STR
    
    LDI 0x1             ; Маска бита 0 (READY)
    MOV B, A
WAIT_RDY:
    LDR
    AND B
    JZR WAIT_RDY        ; Ожидание готовности накопителя (READY=1)
    
    ; Проваливаемся в LOAD_INIT (Fall-through)

LOAD_INIT:
    ; Инициализация целевого адреса 0x10
    LDP 0xF3
    LDI 0x1
    STR                 ; PCH = 1
    DEX                 ; X:Y = 0xF2
    LDI 0x0
    STR                 ; PCL = 0

LOAD_LOOP:
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
    STR                 ; 1. Запись в User RAM
    
    ; 2. Проверка аппаратного состояния мотора флеш-контроллера
    PHA                 ; Спасаем введенный код B в стек
    LDP 0xF9            ; Указатель на STORAGE_CMD
    LDI 0x1
    MOV B, A            ; B = 1 (маска READY - сессия активна)
    LDR
    AND B
    SUB B               ; Если READY=1, то 1 - 1 = 0 (Z=1)
    JZ IS_ECHO          ; Абсолютный прыжок к записи потока
    
    PLA                 ; Если сессия закрыта: восстанавливаем баланс стека
ADV_LOOP:
    ; Инкремент младшего адреса
    LDP 0xF2
    LDR
    INC A
    STR
    JCR ADV_HIGH        ; Короткий переход при переполнении (+4 ниббла)
    JMP LOAD_LOOP       ; Возврат в начало цикла ввода

ADV_HIGH:
    ; Инкремент старшего адреса
    INX                 ; X:Y = 0xF3
    LDR
    INC A
    STR
    
    ; Защита аппаратного стека от затирания
    MOV B, A
    LDI 0xE
    SUB B
    JZ CLOSE_FILE       ; Если PCH == 0xE, экстренно закрываем файл
    JMP LOAD_LOOP

IS_ECHO:
    ; ЭКСТРЕМАЛЬНАЯ ОПТИМИЗАЦИЯ v4.5: Указатель X:Y уже на 0xF9! 
    DEX                 ; X:Y = 0xF8 (STORAGE_DAT)
    PLA                 ; Извлекаем введенный ниббл из стека обратно в A
    STR                 ; Синхронная запись! Аппаратура сама инкрементирует адрес на флешке.
    JMP ADV_LOOP        ; Возврат к инкременту адреса RAM

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

GETKEY:
    LDP 0xF4
    LDI 0x1
    MOV B, A
WAIT_P:
    LDR
    AND B
    JZR WAIT_P          ; Ожидание нажатия
    
    INX
    LDR
    PHA
    
    ; Визуальный оверлей нажатия на DISP_1
    DEX
    DEX
    DEX
    DEX
    STR                 
    
    INX
    INX
    INX
WAIT_R:
    LDR
    AND B
    SUB B
    JZR WAIT_R          ; Ожидание отпускания
    
    PLA
    MOV B, A
    RET