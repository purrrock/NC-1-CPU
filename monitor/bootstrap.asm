ORG 0xD0
    LDP 0xF9
    LDI 0x4
    STR             ; MOT=1, MOD=0 (Чтение, STRB=0)
    
    ; Инициализация указателя записи в RAM (0x10)
    LDI 0x1
    MOV X, A
    LDI 0x0
    MOV Y, A        ; X:Y = 0x10

READ_LOOP:
    ; 1. Сохраняем RAM-указатель X:Y в стек
    MOV A, X
    PHA
    MOV A, Y
    PHA
    
    ; 2. Запрос байта (STRB=1)
    LDP 0xF9
    LDI 0x5
    STR
    LDI 0x1
    MOV B, A
WAIT_1: 
    LDR
    AND B
    JZR WAIT_1      ; Ожидание ACK=1
    
    ; 3. Проверка EOF (бит 1)
    LDR
    MOV B, A
    LDI 0x2
    AND B
    JZ NOT_EOF      ; Если Z=0, то EOF=1. 
    LDI 0x0
    STR             ; Выключаем мотор
    BOOT              ; BOOT (Возврат в Nano-Monitor!)
    
NOT_EOF:
    ; 4. Чтение данных
    DEX             ; TAPE_DAT (0xF8)
    LDR
    PHA             ; Сохраняем считанный ниббл в стек
    
    ; 5. Снятие строба (STRB=0)
    INX             ; TAPE_CMD (0xF9)
    LDI 0x4
    STR
    LDI 0x1
    MOV B, A
WAIT_0: 
    LDR
    AND B
    SUB B
    JZR WAIT_0      ; Ожидание ACK=0
    
    ; 6. Восстановление X:Y из стека и запись
    PLA
    MOV B, A        ; Достаем данные -> B
    PLA
    MOV Y, A            ; Достаем Y -> MOV Y, A
    PLA
    MOV X, A            ; Достаем X -> MOV X, A
    
    MOV A, B
    STR             ; RAM[X:Y] = Данные с ленты
    INX             ; Инкремент адреса RAM
    JMP READ_LOOP