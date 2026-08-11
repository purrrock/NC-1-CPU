; NC-1 "CAT CATCH THE DIGIT"
; F0 = target
; F1 = score high
; F2 = score middle
; F3 = score low
; F4 = keyboard status
; F5 = keyboard code
; F6 = audio
; F7 = RNG

START:
    LDI 0xF
    MOV X,A
    LDI 0
    MOV Y,A
    LDR
    LDI 1
    MOV Y,A
    STR
    LDI 2
    MOV Y,A
    STR
    LDI 3
    MOV Y,A
    STR
    CAL NEW_TARGET

GAME_LOOP:
    CAL WAIT_KEY
    MOV B,A
    LDI 0
    MOV Y,A
    LDR
    SUB B
    JZ CORRECT
    CAL BEEP
    CAL WAIT_RELEASE
    JMP GAME_LOOP

CORRECT:
    LDI 3
    MOV Y,A
    LDR
    INC A
    STR
    JC SCORE_CARRY_1
    CAL NEW_TARGET
    CAL WAIT_RELEASE
    JMP GAME_LOOP

SCORE_CARRY_1:
    LDI 2
    MOV Y,A
    LDR
    INC A
    STR
    JC SCORE_CARRY_2
    CAL NEW_TARGET
    CAL WAIT_RELEASE
    JMP GAME_LOOP

SCORE_CARRY_2:
    LDI 1
    MOV Y,A
    LDR
    INC A
    STR
    CAL NEW_TARGET
    CAL WAIT_RELEASE
    JMP GAME_LOOP

WAIT_KEY:
WAIT_KEY_LOOP:
    LDI 4
    MOV Y,A
    LDR
    MOV B,A
    LDI 1
    AND B
    JZ WAIT_KEY_LOOP
    LDI 5
    MOV Y,A
    LDR
    RET

WAIT_RELEASE:
WAIT_RELEASE_LOOP:
    LDI 4
    MOV Y,A
    LDR
    MOV B,A
    LDI 1
    AND B
    JZ WAIT_RELEASE_DONE
    JMP WAIT_RELEASE_LOOP

WAIT_RELEASE_DONE:
    RET

NEW_TARGET:
    LDI 7
    MOV Y,A
    LDR
    MOV B,A
    LDI 0
    MOV Y,A
    MOV A,B
    STR
    RET

BEEP:
    LDI 6
    MOV Y,A
    LDI 1
    STR
    LDI 0xF
    MOV B,A

BEEP_DELAY:
    DEC B
    JZ BEEP_OFF
    JMP BEEP_DELAY

BEEP_OFF:
    LDI 0
    STR
    RET