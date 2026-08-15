ORG 0x00
ENTRY:
    JMP WAIT_CMD          ; Вход после аппаратного сброса
CLOSE_FILE:
    LDP 0xF9              ; STORAGE_CMD
    LDI 0x0               ; MOTOR=0: закрыть файл
    STR
    BOOT                  ; Возврат в монитор
ORG 0x0E
RUN_XBNK:
    XBNK                  ; M=0, следующий fetch из RAM[0x10]
ORG 0x10
WAIT_CMD:
    CAL GETKEY            ; A/B = код команды
    DEC A                 ; 0 -> F,C=1; 1 -> 0,Z=1
    JC RUN                ; 0 = RUN
    JZ TAPE_INIT         ; 1 = TAPE
    DEC A                 ; 2 -> 1
    JZ DUMP_INIT          ; 2 = DUMP
    BOOT                  ; Остальные клавиши игнорируются
RUN:
    JMP RUN_XBNK          ; Переход к трамплину
TAPE_INIT:
    MOV A,B               ; A = 1
    LDP 0xF9              ; STORAGE_CMD
    STR                   ; MOTOR=1, MODE=0
WAIT_TAPE_READY:
    LDR                   ; READY/EOF
    DEC A                 ; READY=0 -> C=1
    JCR WAIT_TAPE_READY
    CAL INIT_PTR          ; Начальный адрес 0x10
TAPE_LOOP:
    LDP 0xF9              ; STORAGE_CMD
    LDR                   ; A = READY/EOF
    DEC A
    DEC A
    JCR TAPE_READ         ; F9=1: READY, читать
    JMP CLOSE_FILE        ; F9=3: READY+EOF, завершить
TAPE_READ:
    DEX                   ; F9 -> F8, STORAGE_DAT
    LDR                   ; A = следующий nibble файла
    CAL WRITE_RAM         ; Записать в RAM и продвинуть адрес
    JMP TAPE_LOOP
DUMP_INIT:
    MOV A,B               ; A = 2
    LDP 0xF0              ; DISP_0
    STR                   ; Показать режим DUMP
    INC A                 ; A = 3
    LDP 0xF9              ; STORAGE_CMD
    STR                   ; MOTOR=1, MODE=1
WAIT_DUMP_READY:
    LDR                   ; READY/EOF
    DEC A                 ; READY=0 -> C=1
    JCR WAIT_DUMP_READY
    CAL INIT_PTR          ; Начальный адрес 0x10
    JMP INPUT_LOOP
INPUT_LOOP:
    CAL GETKEY            ; A/B = введённый nibble
    INC A                 ; F -> 0
    JZ ESCAPE             ; F начинает escape
    MOV A,B               ; Восстановить введённый nibble
STORE_INPUT:
    LDP 0xF8              ; STORAGE_DAT
    STR                   ; Записать nibble на накопитель
    CAL WRITE_RAM         ; Записать тот же nibble в RAM
    JMP INPUT_LOOP
ESCAPE:
    CAL GETKEY            ; Получить второй nibble
    DEC A                 ; 0 -> F,C=1
    JC CLOSE_FILE         ; F0: завершить ввод
    MOV A,B               ; FF/Fx: сохранить второй nibble
    JMP STORE_INPUT
INIT_PTR:
    LDP 0xF3              ; DISP_3
    INC A                 ; 0 -> 1
    STR                   ; Старший nibble адреса = 1
    DEX                   ; F3 -> F2
    DEC A                 ; 1 -> 0
    STR                   ; Младший nibble адреса = 0
    RET
WRITE_RAM:
    PHA                   ; Сохранить данные
    CAL SET_PTR           ; X:Y = DISP_3:DISP_2
    PLA
    STR                   ; RAM[X:Y] = данные
    CAL ADVANCE           ; Перейти к следующему адресу
    RET
SET_PTR:
    LDP 0xF3              ; DISP_3
    LDR                   ; A = старший nibble
    PHA                   ; Сохранить high
    DEX                   ; F3 -> F2
    LDR                   ; A = младший nibble
    MOV Y,A
    PLA
    MOV X,A               ; X:Y = DISP_3:DISP_2
    RET
ADVANCE:
    LDP 0xF2              ; DISP_2
    LDR                   ; A = low address
    INC A
    STR                   ; Сохранить low address
    JCR ADV_HIGH          ; FF -> 00
    RET
ADV_HIGH:
    INX                   ; F2 -> F3
    LDR                   ; A = high address
    INC A
    STR                   ; Увеличить high address
    MOV B,A
    LDI 0xE
    SUB B
    JZ CLOSE_FILE         ; Достигнут адрес 0xE0
    RET
GETKEY:
    LDP 0xF4              ; GPI_KBD
    LDI 0x1               ; Маска KBD
    MOV B,A
WAIT_P:
    LDR                   ; Статус клавиши
    AND B
    JZR WAIT_P            ; Ждать нажатия
    INX                   ; F4 -> F5
    LDR                   ; Код клавиши
    PHA                   ; Сохранить код
    LDP 0xF1              ; DISP_1
    STR                   ; Показать код клавиши
    INX                   ; F1 -> F2
    INX                   ; F2 -> F3
    INX                   ; F3 -> F4
WAIT_R:
    LDR                   ; Статус клавиши
    AND B
    SUB B
    JZR WAIT_R            ; Ждать отпускания
    PLA                   ; Восстановить код
    MOV B,A               ; A/B = код клавиши
    RET