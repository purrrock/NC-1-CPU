ORG 0x00
ENTRY:
    ; Unified entry after RESET or SWI
    LDI 0x8
    MOV B,A
    MOV A,FL
    AND B
    JZ MON_INIT
    ; Cold start: clear R, keep M=1
    LDI 0x4
    MOV FL,A
MON_INIT:
    ; Reset display mode and restore MMIO pointer
    LDI 0xF
    MOV X,A
    LDI 0x0
    MOV Y,A
    STR
WAIT_CMD:
    ; Read command: A / B
    CAL GETKEY
    LDI 0xA
    SUB B
    JZ LOAD
    LDI 0xB
    SUB B
    JZ RUN
    JMP WAIT_CMD
LOAD:
    ; DISP_0 = A, current address = 0x10
    LDI 0x0
    MOV Y,A
    LDI 0xA
    STR
    LDI 0x3
    MOV Y,A
    LDI 0x1
    STR
    LDI 0x2
    MOV Y,A
    LDI 0x0
    STR
LOAD_LOOP:
    ; DISP_1 = current RAM value
    CAL SET_PTR
    LDI 0x1
    MOV Y,A
    STR
    ; Read next input nibble
    CAL GETKEY
    LDI 0xF
    SUB B
    JZ ESCAPE
WRITE_NIBBLE:
    ; Write B to current RAM address
    CAL SET_PTR
    MOV A,B
    STR
    ; Increment low address nibble
    LDI 0xF
    MOV X,A
    LDI 0x2
    MOV Y,A
    LDR
    INC A
    STR
    JC ADV_HIGH
    JMP LOAD_LOOP
ESCAPE:
    ; F0 = end of LOAD, FF = literal F
    CAL GETKEY
    LDI 0x0
    SUB B
    JZ MON_INIT
    LDI 0xF
    SUB B
    JZ LITERAL_F
    JMP MON_INIT
LITERAL_F:
    LDI 0xF
    MOV B,A
    JMP WRITE_NIBBLE
RUN:
    ; Run fixed COM entry point 0x10
    LDI 0x0
    MOV Y,A
    MOV A,B
    STR
    LDI 0x1
    MOV PCH,A
    LDI 0x0
    MOV FL,A
    MOV PCL,A
SET_PTR:
    ; X=0xF on entry; DISP_3:DISP_2 = current address
    LDI 0x3
    MOV Y,A
    LDR
    MOV PCH,A
    DEC Y
    LDR
    MOV Y,A
    MOV A,PCH
    MOV X,A
    LDRA
    RET
ADV_HIGH:
    ; Increment high nibble; E0 means end of COM area
    LDI 0x3
    MOV Y,A
    LDR
    INC A
    STR
    MOV B,A
    LDI 0xE
    SUB B
    JZ MON_INIT
    JMP LOAD_LOOP
GETKEY:
    ; X:Y = GPI_KBD, B = status mask
    LDI 0xF
    MOV X,A
    LDI 0x4
    MOV Y,A
    LDI 0x1
    MOV B,A
WAIT_PRESS:
    ; LDR preserves Z, so AND must update it
    LDR
    AND B
    JZ WAIT_PRESS
    ; Read latched key code
    LDI 0x5
    MOV Y,A
    LDR
    MOV PCH,A
    ; Dynamic key overlay on DISP_1
    LDI 0x1
    MOV Y,A
    MOV A,PCH
    STR
    ; Wait until key is released
    LDI 0x4
    MOV Y,A
WAIT_RELEASE:
    LDR
    SUB B
    JZ WAIT_RELEASE
    ; Return code in both A and B
    MOV A,PCH
    MOV B,A
    RET