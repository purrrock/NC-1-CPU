ORG 0x00
ENTRY:
    ; Единая точка входа для Reset (M=1, R=1) и BOOT (M=1, PC=0)
    JMP MON_INIT

ORG 0x0E
RUN_XBNK:
    ; Trampoline pattern: переключение банков (ROM -> RAM)
    ; Следующая выборка инструкции произойдет из RAM[0x10]
    XBNK

ORG 0x10
MON_INIT:
    ; DISP_0 = 0x0 (Command Mode)
    LDP 0xF0
    LDI 0x0
    STR

WAIT_CMD:
    ; Ожидание команды оператора
    CAL GETKEY
    LDI 0xA
    SUB B
    JZ LOAD
    LDI 0xB
    SUB B
    JZ RUN
    JMP WAIT_CMD

LOAD:
    ; DISP_0 = 0xA (LOAD Mode)
    LDP 0xF0
    LDI 0xA
    STR
    
    ; Инициализация PCH:PCL адресом 0x10
    LDP 0xF3
    LDI 0x1
    STR             ; DISP_3 = 1
    DEX
    LDI 0x0
    STR             ; DISP_2 = 0

LOAD_LOOP:
    ; Динамическая индикация памяти на DISP_1
    CAL SET_PTR
    LDP 0xF1
    STR
    
    CAL GETKEY
    LDI 0xF
    SUB B
    JZ ESCAPE

WRITE_B:
    CAL SET_PTR
    MOV A,B         ; Восстановление кода клавиши в A
    STR
    CAL ADVANCE
    JMP LOAD_LOOP

ESCAPE:
    ; Ожидание подтверждающего символа (0 или F)
    CAL GETKEY
    
    ; Проверка на F0 (выход)
    LDI 0x0
    SUB B
    JZ MON_INIT
    
    ; Проверка на FF (литерал F)
    LDI 0xF
    SUB B
    JZ WRITE_B      ; Абсолютный прыжок на штатную процедуру записи (B = 0xF)
    
    ; Обработка невалидной комбинации (например, FC)
    ; Сброс escape-состояния: возвращаемся в цикл ввода без записи и сдвига адреса
    JMP LOAD_LOOP

RUN:
    ; DISP_0 = 0xB (RUN Mode)
    LDP 0xF0
    LDI 0xB
    STR
    ; Прыжок на трамплин
    JMP RUN_XBNK

SET_PTR:
    ; Настройка X:Y из дисплейных регистров без разрушения указателя
    LDP 0xF3
    LDR
    PHA             ; ИСПРАВЛЕНИЕ: Сохранение PCH в стек (не в X)
    DEX             ; X:Y корректно смещается на 0xF2
    LDR
    MOV Y,A         ; Y = PCL
    PLA             ; Извлечение PCH
    MOV X,A         ; X = PCH
    LDRA            ; A = RAM[X:Y] (Кросс-чтение)
    RET

ADVANCE:
    ; Инкремент PCL
    LDP 0xF2
    LDR
    INC A           ; Строго обновляет Z и C (ISA v4.4)
    STR
    JCR ADV_HIGH    ; 2-ниббловый относительный переход при C=1 (+1 ниббл)
    RET

ADV_HIGH:
    ; Инкремент PCH
    INX             ; X:Y = 0xF3
    LDR
    INC A
    STR
    
    ; Защита аппаратного стека (0xE0)
    MOV B,A
    LDI 0xE
    SUB B
    JZ MON_INIT
    RET

GETKEY:
    ; Инициализация указателя и маски
    LDP 0xF4
    LDI 0x1
    MOV B,A         ; B = 1
    
WAIT_PRESS:
    LDR             ; Чтение GPI_KBD
    AND B
    JZR WAIT_PRESS  ; Относительный прыжок (-5 нибблов), ждем 1
    
    ; Чтение защелкнутого кода клавиши (KBD_CODE)
    INX
    LDR
    PHA
    
    ; Оверлей нажатия на DISP_1
    DEX
    DEX
    DEX
    DEX             ; X:Y = 0xF1
    STR
    
    ; Возврат к порту статуса (0xF4)
    INX
    INX
    INX
    
WAIT_RELEASE:
    LDR
    AND B
    SUB B           ; ИСПРАВЛЕНИЕ: Вычитание маски (1 - 1 = 0 -> Z=1)
    JZR WAIT_RELEASE; Относительный прыжок (-7 нибблов), ждем 0
    
    ; Извлечение кода клавиши и возврат
    PLA
    MOV B,A
    RET