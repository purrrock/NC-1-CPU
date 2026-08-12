ORG 0x00
ENTRY:
    ; Проверка бита 3 (флаг R) в регистре FL
    LDI 0x8         ; Маска 1000b
    MOV B, A
    MOV A, FL       ; Чтение статуса
    AND B           ; A = A & 8
    JZ CMD_LOOP     ; Если Z=1 (R=0) -> это Software Interrupt, идем в цикл

    ; Холодный старт (R=1). Сброс триггера R, сохраняем M=1 (System Mode)
    LDI 0x4         ; 0100b
    MOV FL, A

CMD_LOOP:
    ; Ожидание команды (A или B)
    CAL GETKEY
    LDI 0xA
    SUB B
    JZ LOAD
    LDI 0xB
    SUB B
    JZ RUN
    JMP CMD_LOOP

LOAD:
    ; Ввод старшего полубайта адреса -> DISP_3
    CAL GETKEY      ; После возврата X гарантированно равен 0xF
    LDI 0x3
    MOV Y, A        ; Указатель на 0xF3
    MOV A, B        ; Восстановление кода клавиши
    STR             ; Запись в DISP_3
    
    ; Ввод младшего полубайта адреса -> DISP_2
    CAL GETKEY      ; X снова 0xF
    LDI 0x2
    MOV Y, A        ; Указатель на 0xF2
    MOV A, B
    STR             ; Запись в DISP_2

LOAD_LOOP:
    CAL GETKEY
    ; Проверка на терминатор/escape (код F)
    LDI 0xF
    SUB B
    JZ ESCAPE

WRITE_NIBBLE:
    ; Общая ветка записи ниббла в память
    CAL SET_PTR     ; Установка X:Y из дисплеев
    MOV A, B        ; A = целевой ниббл
    STR             ; RAM[X:Y] = A
    CAL ADVANCE     ; Инкремент адреса в дисплеях
    JMP LOAD_LOOP

ESCAPE:
    CAL GETKEY
    LDI 0x0
    SUB B
    JZ CMD_LOOP     ; Ввод F -> 0: Возврат в командный цикл
    
    ; Ввод F -> F (или любой другой): Запись литерального F
    LDI 0xF
    MOV B, A        ; Подготовка F для записи
    JMP WRITE_NIBBLE; Прыжок на общую логику сохранения

RUN:
    CAL GETKEY      ; Ввод PCH
    MOV PCH, A
    CAL GETKEY      ; Ввод PCL
    LDI 0x0
    MOV FL, A       ; Сброс M=0 (переход в User Mode)
    MOV A, B
    MOV PCL, A      ; Аппаратный прыжок на PCH:PCL в банке RAM

SET_PTR:
    ; Считывает текущий адрес из MMIO и настраивает X:Y
    LDI 0xF
    MOV X, A
    LDI 0x3
    MOV Y, A
    LDR             ; Чтение DISP_3
    MOV B, A        ; Сохранение PCH в B
    LDI 0x2
    MOV Y, A
    LDR             ; Чтение DISP_2 (теперь A = PCL)
    MOV Y, A        ; Установка младшего индекса
    MOV A, B
    MOV X, A        ; Установка старшего индекса
    RET

ADVANCE:
    ; Инкремент значения в DISP_2
    LDI 0xF
    MOV X, A
    LDI 0x2
    MOV Y, A
    LDR
    MOV B, A
    INC B           ; Флаг C установится при переполнении (0xF + 1)
    MOV A, B
    STR             ; Обновление DISP_2
    JC ADV_HIGH     ; Если переполнение -> инкремент DISP_3
    RET

ADV_HIGH:
    ; Инкремент значения в DISP_3 (X уже равен 0xF)
    LDI 0x3
    MOV Y, A
    LDR
    MOV B, A
    INC B
    MOV A, B
    STR             ; Обновление DISP_3
    RET

GETKEY:
    ; Настройка X:Y на порт статуса клавиатуры (0xF4)
    LDI 0xF
    MOV X, A
    LDI 0x4
    MOV Y, A
    LDI 0x1
    MOV B, A            ; B = 0x1 (маска для проверки бита 0)
    
KEY_WAIT_PRESS:
    LDR                 ; Чтение статуса (0xF4)
    AND B               ; Изоляция нулевого бита
    JZ KEY_WAIT_PRESS   ; Ожидание перехода бита 0 в единицу (нажатие)
    
KEY_WAIT_RELEASE:
    LDR                 ; Повторное чтение статуса (0xF4)
    AND B
    SUB B               ; Вычитание маски. Если бит установлен (1 - 1 = 0), флаг Z=1
    JZ KEY_WAIT_RELEASE ; Ожидание перехода бита 0 в ноль (отпускание)
    
    ; Клавиша отпущена. Чтение защелкнутого кода из 0xF5
    LDI 0x5
    MOV Y, A
    LDR
    MOV B, A            ; Сохранение целевого кода в B
    
    ; Вывод считанного кода на индикатор 0xF1
    LDI 0x1
    MOV Y, A
    MOV A, B
    STR
    RET