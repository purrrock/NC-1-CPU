; NC-1 v4.5 TAPE DRIVE TEST PROGRAM
; Запись нибблов 0..F -> Останов -> Ожидание 'C' -> Чтение 0..F -> Сверка

ORG 0x00

INIT:
    LDP 0xF0     ; Очистка индикатора DISP_0
    LDI 0x0
    STR

; =========================================================
; 1. ФАЗА ЗАПИСИ (WRITE NIBBLES 0x0 .. 0xF)
; =========================================================

START_WRITE:
    ; Включаем мотор на запись: MOTOR=1, MODE=1, STRB=0 -> 0b0110 = 6
    LDP 0xF9
    LDI 0x6
    STR

    ; Ожидаем готовности ленты (READY == 1)
    LDI 0x4
    MOV B, A
WAIT_W_READY:
    LDR
    AND B
    JZR WAIT_W_READY

    ; Инициализируем начальное значение V = 0
    LDI 0x0
    PHA          ; Сохраняем V в стек

WRITE_LOOP:
    ; 1. Записываем ниббл V в TAPE_DAT (0xF8)
    LDP 0xF8
    PLA          ; A = V
    PHA          ; Сохраняем обратно
    STR          ; RAM[0xF8] = V

    ; 2. Выставляем строб: MOTOR=1, MODE=1, STRB=1 -> 0b0111 = 7
    LDP 0xF9
    LDI 0x7
    STR

    ; 3. Ожидаем ACK == 1
    LDI 0x1
    MOV B, A
WAIT_W_ACK1:
    LDR
    AND B
    JZR WAIT_W_ACK1

    ; 4. Снимаем строб: MOTOR=1, MODE=1, STRB=0 -> 0b0110 = 6
    LDP 0xF9
    LDI 0x6
    STR

    ; 5. Ожидаем ACK == 0
WAIT_W_ACK0:
    LDR
    AND B
    SUB B        ; (ACK-1): 0 - 1 = F (Z=0, выход). 1 - 1 = 0 (Z=1, ждем).
    JZR WAIT_W_ACK0

    ; 6. Увеличиваем ниббл V
    PLA          ; A = V
    INC A        ; V = V + 1 (Если было F, станет 0 и C=1)
    PHA          ; Сохраняем новое V
    JCR WRITE_DONE ; Проверяем флаг ПЕРЕНОСА (Carry). Если C=1, прошли от 0 до F!
    JMP WRITE_LOOP

WRITE_DONE:
    PLA          ; Очищаем стек
    ; Выключаем мотор магнитофона (сохранение файла)
    LDP 0xF9
    LDI 0x0
    STR

; =========================================================
; 2. ПАУЗА: ОЖИДАНИЕ КЛАВИШИ 'C'
; =========================================================

    ; Выводим 'C' на индикатор, чтобы показать пользователю, чего ждем
    LDP 0xF0
    LDI 0xC
    STR

WAIT_KEY_C:
    ; Читаем статус клавиатуры (0xF4, нулевой бит = 1, если нажата)
    LDP 0xF4
    LDR
    MOV B, A
    LDI 0x1
    AND B
    JZ WAIT_KEY_C ; Ждем пока нажмут любую кнопку

    ; Читаем код нажатой кнопки (0xF5)
    LDP 0xF5
    LDR
    MOV B, A
    LDI 0xC        ; Ожидаем код 0xC
    SUB B          ; Если нажали 'C', то 0xC - 0xC = 0 (Z=1)
    JZR START_READ ; Если это 'C', идем дальше
    JMP WAIT_KEY_C ; Иначе продолжаем ждать

; =========================================================
; 3. ФАЗА ЧТЕНИЯ И СВЕРКИ (READ & VERIFY 0x0 .. 0xF)
; =========================================================

START_READ:
    ; Очищаем дисплей перед чтением
    LDP 0xF0
    LDI 0x0
    STR

    ; Включаем мотор на чтение: MOTOR=1, MODE=0, STRB=0 -> 0b0100 = 4
    LDP 0xF9
    LDI 0x4
    STR

    ; Ожидаем готовности ленты (READY == 1)
    LDI 0x4
    MOV B, A
WAIT_R_READY:
    LDR
    AND B
    JZR WAIT_R_READY

    ; Инициализируем ожидаемое значение V = 0
    LDI 0x0
    PHA          

READ_LOOP:
    ; 1. Запрашиваем ниббл: MOTOR=1, MODE=0, STRB=1 -> 0b0101 = 5
    LDP 0xF9
    LDI 0x5
    STR

    ; 2. Ожидаем ACK == 1
    LDI 0x1
    MOV B, A
WAIT_R_ACK1:
    LDR
    AND B
    JZR WAIT_R_ACK1

    ; 3. Читаем ниббл из TAPE_DAT (0xF8)
    LDP 0xF8
    LDR
    MOV B, A     ; B = прочитанное значение

    ; 4. Сравниваем с ожидаемым значением V
    PLA          ; A = V
    PHA
    SUB B        ; A = V - B
    JZR MATCH_OK ; Если совпадают, идем дальше
    JMP ERROR    ; ОШИБКА ДАННЫХ

MATCH_OK:
    ; 5. Снимаем строб: MOTOR=1, MODE=0, STRB=0 -> 0b0100 = 4
    LDP 0xF9
    LDI 0x4
    STR

    ; 6. Ожидаем ACK == 0
    LDI 0x1
    MOV B, A
WAIT_R_ACK0:
    LDR
    AND B
    SUB B
    JZR WAIT_R_ACK0

    ; 7. Увеличиваем ожидаемое значение V
    PLA
    INC A
    PHA
    JCR READ_DONE ; Если C=1 (переход от F к 0), мы успешно прочитали все 16 нибблов!
    JMP READ_LOOP

READ_DONE:
    PLA          ; Очищаем стек
    LDP 0xF9
    LDI 0x0
    STR          ; Выключаем мотор
    JMP SUCCESS

; =========================================================
; 4. ЗАВЕРШЕНИЕ (SUCCESS / ERROR)
; =========================================================

SUCCESS:
    LDP 0xF0     ; DISP_0
    LDI 0xF      ; Выводим 'F'
    STR
HALT_OK:
    JMP HALT_OK

ERROR:
    LDP 0xF9     ; Выключаем мотор
    LDI 0x0
    STR
    LDP 0xF3     ; DISP_3
    LDI 0xE      ; Выводим 'E'
    STR
HALT_ERR:
    JMP HALT_ERR