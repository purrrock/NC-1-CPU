ORG 0x00
ENTRY:
    ; Единая точка входа после RESET и SWI
CMD_LOOP:
    ; A/B получают код команды
    CAL GETKEY
    LDI 0xA
    SUB B
    JZ LOAD
    LDI 0xB
    SUB B
    JZ RUN
    JMP CMD_LOOP
LOAD:
    ; Первый ниббл стартового адреса -> DISP_3
    CAL GETKEY
    LDI 0xF
    MOV X,A
    LDI 0x3
    MOV Y,A
    STR
    ; Второй ниббл стартового адреса -> DISP_2
    CAL GETKEY
    LDI 0xF
    MOV X,A
    LDI 0x2
    MOV Y,A
    MOV A,B
    STR
LOAD_LOOP:
    ; Получить очередной машинный ниббл
    CAL GETKEY
    ; F -> escape/терминатор
    LDI 0xF
    SUB B
    JZ ESCAPE
    ; Обычный ниббл
    CAL SET_PTR
    MOV A,B
    STR
    CAL ADVANCE
    JMP LOAD_LOOP
ESCAPE:
    ; F0 = конец загрузки
    CAL GETKEY
    LDI 0x0
    SUB B
    JZ CMD_LOOP
    ; FF + N = записать литеральный F, N будет обработан
    ; следующей итерацией
    LDI 0xF
    MOV B,A
    CAL SET_PTR
    MOV A,B
    STR
    CAL ADVANCE
    JMP LOAD_LOOP
RUN:
    ; Первый ниббл адреса -> PCH
    CAL GETKEY
    MOV PCH,A
    ; Второй ниббл адреса
    CAL GETKEY
    MOV A,B
    ; User Mode: M=0
    LDI 0x0
    MOV FL,A
    ; Запись PCL запускает пользовательский код
    MOV PCL,A
SET_PTR:
    ; D3:D2 хранят текущий адрес записи
    ; D0:D1 временно используются внутри подпрограммы
    LDI 0xF
    MOV X,A
    LDI 0x3
    MOV Y,A
    LDRA
    DEC Y
    DEC Y
    DEC Y
    STR
    LDI 0x2
    MOV Y,A
    LDRA
    DEC Y
    STR
    LDI 0x0
    MOV Y,A
    LDRA
    MOV X,A
    LDI 0x1
    MOV Y,A
    LDRA
    MOV Y,A
    RET
ADVANCE:
    ; B содержит последний введённый ниббл
    INC Y
    JC ADV_HIGH
    ; Следующий адрес в той же странице
    MOV A,Y
    LDI 0xF
    MOV X,A
    LDI 0x2
    MOV Y,A
    STR
    ; Восстановить отображение последнего ниббла
    MOV A,B
    LDI 0x1
    MOV Y,A
    STR
    RET
ADV_HIGH:
    ; Переход FF -> 00
    INC X
    MOV A,X
    MOV B,A
    ; Обновить старшую часть адреса
    LDI 0xF
    MOV X,A
    LDI 0x3
    MOV Y,A
    STR
    ; Обновить младшую часть адреса
    LDI 0x2
    MOV Y,A
    LDI 0x0
    STR
    ; Восстановить отображение последнего ниббла
    LDI 0x1
    MOV Y,A
    MOV A,B
    STR
    RET
GETKEY:
    ; Ожидание нажатия клавиши
    LDI 0xF
    MOV X,A
    LDI 0x4
    MOV Y,A
    LDI 0x1
    MOV B,A
KEY_WAIT:
    LDRA
    AND B
    JZ KEY_WAIT
    ; Чтение кода клавиши
    LDI 0x5
    MOV Y,A
    LDRA
    MOV B,A
    ; Показать введённый ниббл на DISP_1
    LDI 0x1
    MOV Y,A
    MOV A,B
    STR
    RET