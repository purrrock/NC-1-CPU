; NC-1 v4.4 DIAGNOSTIC TEST ROM
; Проверка АЛУ, Флагов, Памяти, Стека и Подпрограмм

ORG 0x00

INIT:
    LDP 0xF0     ; X=F, Y=0 (Указатель на DISP_0)
    LDI 0        ; A = 0
    STR          ; Очистка DISP_0 перед началом тестов

TEST_1_CARRY:
    LDI 0        ; A = 0
    DEC A        ; A = 0 - 1. Ожидаем: A=0xF, C=1, Z=0
    JCR TEST_2_ZERO ; Если C=1 (Успех), идем к следующему тесту
    JMP ERROR    ; ОШИБКА

TEST_2_ZERO:
    LDI 0xF      ; A = 0xF (Исправлено с F)
    INC A        ; A = 0xF + 1. Ожидаем: A=0, C=1, Z=1
    JZR TEST_3_ALU  ; Если Z=1 (Успех), идем к следующему тесту
    JMP ERROR    ; ОШИБКА

TEST_3_ALU:
    LDI 5        ; A = 5
    MOV B, A     ; B = 5
    LDI 7        ; A = 7
    ADD B        ; A = 7 + 5 = 12 (0xC). Z=0, C=0
    SUB B        ; A = 12 - 5 = 7.
    MOV B, A     ; B = 7
    LDI 7        ; A = 7
    SUB B        ; A = 7 - 7 = 0. Ожидаем Z=1
    JZR TEST_4_MEM  ; Проверяем флаг Z
    JMP ERROR    ; ОШИБКА

TEST_4_MEM:
    LDP 0x50     ; Указатель на RAM 0x50
    LDI 0xA      ; A = 0xA (Исправлено с A)
    STR          ; RAM[0x50] = 0xA (Shadow Write в RAM)
    LDI 0        ; Сбрасываем A
    LDRA         ; A = RAM[0x50] (Кросс-чтение из RAM)
    MOV B, A     ; B = 0xA
    LDI 0xA      ; A = 0xA
    SUB B        ; A = 0xA - 0xA = 0. Z=1
    JZR TEST_5_STACK; Проверяем
    JMP ERROR    ; ОШИБКА

TEST_5_STACK:
    LDI 3        ; A = 3
    PHA          ; Push A в стек
    LDI 0        ; Портим A
    PLA          ; Pop A из стека (ожидаем A=3)
    MOV B, A     ; B = 3
    LDI 3        ; A = 3
    SUB B        ; A - B = 0. Z=1
    JZR TEST_6_CALL ; Проверка
    JMP ERROR    ; ОШИБКА

TEST_6_CALL:
    CAL SUB_TEST ; Вызов подпрограммы
    MOV B, A     ; Подпрограмма записала 9 в A. B=9
    LDI 9        ; A = 9
    SUB B        ; Сравниваем
    JZR SUCCESS  ; Успех?
    JMP ERROR    ; ОШИБКА

; --- Блоки подпрограмм и останова ---

ORG 0x80
SUB_TEST:
    LDI 9        ; A = 9
    RET          ; Возврат из подпрограммы

ORG 0xC0
SUCCESS:
    LDP 0xF0     ; X:Y = 0xF0 (DISP_0)
    LDI 0xF      ; A = 0xF (Исправлено с F)
    STR          ; Выводим 'F' на индикатор
HALT_OK:
    JMP HALT_OK  ; Бесконечный цикл

ORG 0xE0
ERROR:
    LDP 0xF3     ; X:Y = 0xF3 (DISP_3)
    LDI 0xE      ; A = 0xE (Исправлено с E)
    STR          ; Выводим 'E' на индикатор
HALT_ERR:
    JMP HALT_ERR ; Бесконечный цикл