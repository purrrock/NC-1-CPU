; ============================================================
; NC-1 GAME: "CAT CATCH THE DIGIT"
;
; User RAM program
;
; DISP_0 = target digit
; DISP_1..3 = score
;
; Keyboard:
;   F4 = KBD_STAT
;   F5 = KBD_CODE
;
; RNG:
;   F7 = RNG
;
; AUDIO:
;   F6 = speaker
;
; RAM:
;   10 = TARGET
;   11 = SCORE_L
;   12 = SCORE_M
;   13 = SCORE_H
;   14 = KEY
;   15 = TEMP
;   16 = ONE
;   17 = ZERO
;
; ============================================================


; ------------------------------------------------------------
; START
; ------------------------------------------------------------

START:
        ; ONE = 1
        LDI 1
        MOV B,A

        ; TARGET = random digit
        CALL_RANDOM

        ; SCORE = 000
        LDI 0
        MOV X,A
        LDI 11
        MOV Y,A
        STR

        LDI 0
        LDI 12
        MOV Y,A
        STR

        LDI 0
        LDI 13
        MOV Y,A
        STR

        ; Display initial score
        CALL_DISPLAY_SCORE


; ------------------------------------------------------------
; MAIN GAME LOOP
; ------------------------------------------------------------

GAME_LOOP:

        ; ----------------------------------------
        ; Wait until a key is pressed
        ; ----------------------------------------

WAIT_KEY:

        ; X:Y = F4 (KBD_STAT)
        LDI 0
        MOV X,A

        LDI 4
        MOV Y,A

        LDR                 ; A = KBD_STAT

        ; B = 1
        MOV A,B

        ; Test bit 0
        ; We need A = KBD_STAT again
        LDI 0
        MOV X,A
        LDI 4
        MOV Y,A
        LDR

        AND B               ; A & 1

        JZ WAIT_KEY         ; no key


        ; ----------------------------------------
        ; Read key code
        ; ----------------------------------------

        LDI 0
        MOV X,A

        LDI 5
        MOV Y,A

        LDR                 ; A = KBD_CODE

        ; Save KEY
        MOV X,A
        LDI 14
        MOV Y,A

        ; A currently contains key code


        ; ----------------------------------------
        ; Load TARGET
        ; ----------------------------------------

        LDI 0
        MOV X,A

        LDI 10
        MOV Y,A

        LDR                 ; A = TARGET

        ; Save TARGET in TEMP
        MOV X,A
        LDI 15
        MOV Y,A
        STR


        ; ----------------------------------------
        ; Compare KEY with TARGET
        ; ----------------------------------------

        ; Load KEY
        LDI 0
        MOV X,A
        LDI 14
        MOV Y,A
        LDR                 ; A = KEY

        ; B = TARGET
        MOV X,A
        LDI 15
        MOV Y,A
        LDR

        MOV B,A

        ; Reload KEY
        LDI 0
        MOV X,A
        LDI 14
        MOV Y,A
        LDR

        SUB B               ; KEY - TARGET

        JZ CORRECT


; ------------------------------------------------------------
; WRONG ANSWER
; ------------------------------------------------------------

WRONG:

        CALL_BEEP

        JMP WAIT_KEY


; ------------------------------------------------------------
; CORRECT ANSWER
; ------------------------------------------------------------

CORRECT:

        ; Increment SCORE_L
        LDI 0
        MOV X,A
        LDI 11
        MOV Y,A
        LDR

        INC A               ; A = SCORE_L + 1

        ; Did it overflow?
        ; Expected C = 1 on 0xF -> 0x0

        MOV X,A
        LDI 11
        MOV Y,A
        STR

        JC SCORE_CARRY_1

        CALL_DISPLAY_SCORE
        CALL_RANDOM
        JMP GAME_LOOP


; ------------------------------------------------------------
; SCORE carry: low -> middle
; ------------------------------------------------------------

SCORE_CARRY_1:

        LDI 0
        MOV X,A
        LDI 12
        MOV Y,A
        LDR

        INC A

        MOV X,A
        LDI 12
        MOV Y,A
        STR

        JC SCORE_CARRY_2

        CALL_DISPLAY_SCORE
        CALL_RANDOM
        JMP GAME_LOOP


; ------------------------------------------------------------
; SCORE carry: middle -> high
; ------------------------------------------------------------

SCORE_CARRY_2:

        LDI 0
        MOV X,A
        LDI 13
        MOV Y,A
        LDR

        INC A

        MOV X,A
        LDI 13
        MOV Y,A
        STR

        CALL_DISPLAY_SCORE
        CALL_RANDOM
        JMP GAME_LOOP


; ============================================================
; RANDOM
;
; Generates a new target from RNG.
;
; RNG returns a 4-bit value, so it already gives us exactly
; one hexadecimal digit: 0..F.
;
; TARGET = RNG
; DISP_0 = TARGET
; ============================================================

CALL_RANDOM:

        ; X:Y = F7
        LDI 0
        MOV X,A

        LDI 7
        MOV Y,A

        LDR                 ; A = RNG

        ; Save TARGET
        MOV B,A

        MOV X,A
        LDI 10
        MOV Y,A
        STR

        ; Display target
        MOV A,B

        LDI 0
        MOV X,A

        LDI 0
        MOV Y,A

        STR                 ; DISP_0

        RET


; ============================================================
; DISPLAY_SCORE
;
; DISP_1 = SCORE_H
; DISP_2 = SCORE_M
; DISP_3 = SCORE_L
; ============================================================

CALL_DISPLAY_SCORE:

        ; ----------------------------------------
        ; DISP_3 = SCORE_L
        ; ----------------------------------------

        LDI 0
        MOV X,A

        LDI 11
        MOV Y,A
        LDR

        LDI 0
        MOV X,A

        LDI 3
        MOV Y,A

        STR


        ; ----------------------------------------
        ; DISP_2 = SCORE_M
        ; ----------------------------------------

        LDI 0
        MOV X,A

        LDI 12
        MOV Y,A
        LDR

        LDI 0
        MOV X,A

        LDI 2
        MOV Y,A

        STR


        ; ----------------------------------------
        ; DISP_1 = SCORE_H
        ; ----------------------------------------

        LDI 0
        MOV X,A

        LDI 13
        MOV Y,A
        LDR

        LDI 0
        MOV X,A

        LDI 1
        MOV Y,A

        STR

        RET


; ============================================================
; BEEP
;
; Simple software-generated pulse.
; ============================================================

CALL_BEEP:

        ; AUDIO = 1
        LDI 1

        LDI 0
        MOV X,A

        LDI 6
        MOV Y,A

        LDI 1
        STR


        ; crude delay
        LDI F
        MOV B,A

BEEP_DELAY:
        DEC B
        JZ BEEP_OFF
        JMP BEEP_DELAY


BEEP_OFF:

        ; AUDIO = 0
        LDI 0

        LDI 0
        MOV X,A

        LDI 6
        MOV Y,A

        STR

        RET