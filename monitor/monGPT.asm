ORG 0x00
ENTRY:
    JMP WAIT_CMD

CLOSE_FILE:
    LDP 0xF9
    LDI 0x0
    STR
    BOOT

ORG 0x0E
RUN_XBNK:
    XBNK

ORG 0x10
WAIT_CMD:
    CAL GETKEY
    DEC A
    JC 0x0E
    JZR TAPE_INIT
    DEC A
    JZ DUMP_INIT
    BOOT

TAPE_INIT:
    MOV A,B
    LDP 0xF9
    STR

WAIT_TAPE_READY:
    LDR
    DEC A
    JCR WAIT_TAPE_READY

    CAL INIT_PTR
    JMP TAPE_LOOP

TAPE_LOOP:
    LDP 0xF9
    LDR
    DEC A
    JZR TAPE_READ
    DEC A
    DEC A
    JZ 0x04

TAPE_READ:
    DEX
    LDR
    CAL WRITE_RAM
    JMP TAPE_LOOP

DUMP_INIT:
    MOV A,B
    LDP 0xF0
    STR
    INC A
    LDP 0xF9
    STR

WAIT_DUMP_READY:
    LDR
    DEC A
    JCR WAIT_DUMP_READY

    CAL INIT_PTR
    JMP INPUT_LOOP

INPUT_LOOP:
    CAL GETKEY
    INC A
    JZ ESCAPE
    MOV A,B

STORE_INPUT:
    LDP 0xF8
    STR
    CAL WRITE_RAM
    JMP INPUT_LOOP

ESCAPE:
    CAL GETKEY
    DEC A
    JC 0x04
    MOV A,B
    JMP STORE_INPUT

INIT_PTR:
    LDP 0xF3
    INC A
    STR
    DEX
    DEC A
    STR
    RET

WRITE_RAM:
    PHA
    CAL SET_PTR
    PLA
    STR
    CAL ADVANCE
    RET

SET_PTR:
    LDP 0xF3
    LDR
    PHA             ; сохранить high nibble адреса
    DEX             ; F3 -> F2, пока X:Y всё ещё = F3
    LDR             ; A = low nibble адреса
    MOV Y,A
    PLA             ; A = high nibble адреса
    MOV X,A
    RET

ADVANCE:
    LDP 0xF2
    LDR
    INC A
    STR
    JCR ADV_HIGH
    RET

ADV_HIGH:
    INX
    LDR
    INC A
    STR
    MOV B,A
    LDI 0xE
    SUB B
    JZ 0x04
    RET

GETKEY:
    LDP 0xF4
    LDI 0x1
    MOV B,A

WAIT_P:
    LDR
    AND B
    JZR WAIT_P

    INX
    LDR
    PHA

    LDP 0xF1
    STR

    INX
    INX
    INX

WAIT_R:
    LDR
    AND B
    SUB B
    JZR WAIT_R

    PLA
    MOV B,A
    RET