ORG 0x00
ENTRY:
    ; Единая точка входа
    LDI 0x8         
    MOV B, A
    MOV A, FL       
    AND B           
    JZ CMD_LOOP     ; Возврат из SWI (R=0)
    
    LDI 0x4         
    MOV FL, A       ; Холодный старт (R=1, M=1)

CMD_LOOP:
    LDI 0xF
    MOV X, A
    LDI 0x0
    MOV Y, A
    STR             ; DISP_0 = 0x0

WAIT_CMD:
    CAL GETKEY      
    LDI 0xA
    SUB B
    JZ LOAD
    LDI 0xB
    SUB B
    JZ RUN
    JMP WAIT_CMD

LOAD:
    LDI 0x0
    MOV Y, A
    LDI 0xA
    STR             ; DISP_0 = 0xA
    
    CAL GETKEY      ; Возвращает код в A и B. Y остается равным 4 после GETKEY
    DEC Y           ; Y = 3 (Указатель на DISP_3)
    STR             ; DISP_3 = PCH
    
    CAL GETKEY      
    LDI 0x2
    MOV Y, A
    STR             ; DISP_2 = PCL

LOAD_LOOP:
    CAL SET_PTR     ; X=PCH, Y=PCL, A=RAM[X:Y]
    MOV B, A        ; B = RAM[X:Y]
    LDI 0xF
    MOV X, A
    LDI 0x1
    MOV Y, A
    MOV A, B
    STR             ; DISP_1 = RAM[X:Y] (Динамическая индикация)
    
    CAL GETKEY      
    LDI 0xF
    SUB B
    JZ ESCAPE

WRITE_NIBBLE:
    CAL SET_PTR     
    MOV A, B        ; Восстановление кода клавиши в A
    STR             ; RAM[X:Y] = A
    CAL ADVANCE
    JMP LOAD_LOOP

ESCAPE:
    CAL GETKEY
    LDI 0x0
    SUB B
    JZ CMD_LOOP     ; F0 -> Выход
    
    LDI 0xF
    MOV B, A        ; FF -> Литерал F
    JMP WRITE_NIBBLE

RUN:
    LDI 0x0
    MOV Y, A
    LDI 0xB
    STR             ; DISP_0 = 0xB
    
    CAL GETKEY
    MOV PCH, A      ; Прямая загрузка из A
    
    CAL GETKEY
    LDI 0x0
    MOV FL, A       ; M = 0 (User Mode)
    MOV A, B        ; Восстановление кода клавиши
    MOV PCL, A      ; Запуск пользовательского кода

SET_PTR:
    LDI 0xF
    MOV X, A
    LDI 0x3
    MOV Y, A
    LDR
    MOV PCH, A      ; Использование PCH как регистра-скратчпада
    DEC Y           ; Y = 2 (DISP_2)
    LDR
    MOV Y, A        ; Y = PCL
    MOV A, PCH
    MOV X, A        ; X = PCH
    LDRA            ; Чтение RAM[X:Y]
    RET

ADVANCE:
    ; Инкремент младшего полубайта адреса (DISP_2)
    LDI 0xF
    MOV X, A
    LDI 0x2
    MOV Y, A
    LDR
    MOV B, A
    INC B           ; AЛУ: B = B + 1. Аппаратно сбрасывает C=0 или устанавливает C=1 при 0xF->0x0
    MOV A, B        ; Переносим результат обратно в A для записи
    STR             
    JC ADV_HIGH     ; Чистый переход при переполнении страницы памяти
    RET

ADV_HIGH:
    ; Инкремент старшего полубайта адреса (DISP_3)
    LDI 0x3
    MOV Y, A
    LDR
    MOV B, A
    INC B           ; AЛУ: B = B + 1
    MOV A, B
    STR             ; DISP_3 = DISP_3 + 1
    RET

GETKEY:
    ; Инициализация указателя на порт GPI (0xF4)
    LDI 0xF
    MOV X, A
    LDI 0x4
    MOV Y, A
    LDI 0x1
    MOV B, A        ; Резервируем B как маску (0x1) для АЛУ
    
K_WAIT_P:
    LDR             ; Чтение состояния порта в аккумулятор A. Флаги НЕ меняются!
    AND B           ; Пропускаем через АЛУ: A = A & 1. АЛУ обновляет флаг Z!
    JZ K_WAIT_P     ; Теперь Z отражает реальное состояние пина. Если 0 -> ждем.   
    
    LDI 0x5
    MOV Y, A
    LDR
    MOV PCH, A      ; Сохранение кода клавиши
    
    LDI 0x1
    MOV Y, A
    STR             ; DISP_1 = Введенный ниббл
    
    LDI 0x4
    MOV Y, A
    
K_WAIT_R:
    LDR
    SUB B           ; Если кнопка нажата, A=1. 1 - 1 = 0 (Z=1)
    JZ K_WAIT_R     
    
    MOV A, PCH      ; Восстановление кода в A
    MOV B, A        ; Дублирование кода в B для ABI
    RET