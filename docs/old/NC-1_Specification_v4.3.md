# NC-1 MICROPROCESSOR TECHNICAL SPECIFICATION

**Version:** 4.3 (Lite / Refactored ISA)  
**Architecture:** 4-bit RISC / Modified Harvard  
**Date:** 2026  
**Status:** Reference specification

## 1. General Description

The **NC-1** is a 4-bit microprocessor with an 8-bit addressing space, designed for embedded systems, hardware emulation, and educational computer engineering projects.

Version 4.3 (Lite) refactors the execution model to a streamlined **ROM Monitor + User RAM** architecture. The legacy software-interrupt path has been removed. The CPU instead provides direct MMIO access, hardware execution-bank exchange (`XBNK`), a software return to the ROM Monitor (`BOOT`), and a small set of stack and address-pointer extensions.

### Key Features

* **Orthogonal Register File:** Direct access to Program Counter (`PC`), Stack Pointer (`SP`), and Status Flags (`FL`) as standard registers.
* **Dual-Bank Memory Architecture:** 256 nibbles of System ROM and 256 nibbles of User RAM sharing the same 8-bit address space.
* **Page-Locked Hardware Stack:** 4-bit `SP` mapped to the dedicated RAM page `0xE0..0xEF` for `CAL`/`RET` and `PHA`/`PLA`.
* **Hardware Execution Bank Exchange (`XBNK`):** Toggles the execution bank without changing the program-flow trajectory or arithmetic flags.
* **Hardware Return to Monitor (`BOOT`):** Restores `PC=0x00`, `SP=0xF`, `M=1` and resumes execution from ROM.
* **Symmetric Cross-Bank Data Access (`LDRA`):** Reads data from the opposite memory bank without changing execution mode.
* **Enhanced Address Pointer Operations (`INX` / `DEX`):** Hardware 8-bit increment/decrement of the `X:Y` pointer.
* **Extended MMIO:** Hex displays, keyboard input, audio/GPO, RNG, and reserved expansion addresses.

## 2. Hardware Architecture

### 2.1. Buses and Bit Widths

* **Data Bus:** 4-bit nibble. Value range: `0..15` (`0x0..0xF`).
* **Address Bus:** 8-bit. Address range: `0x00..0xFF` (256 nibbles per bank).
* **Physical Memory:** 256 nibbles ROM + 256 nibbles RAM.

### 2.2. Register Map

The CPU has 8 internal 4-bit registers addressed by a 3-bit identifier.

| ID | Mnemonic | Purpose | Width | Access / Hardware Behavior |
| :---: | :--- | :--- | :---: | :--- |
| `000` | `A` | Accumulator | 4-bit | Primary ALU, data-transfer and I/O register. |
| `001` | `B` | Auxiliary | 4-bit | General-purpose register. |
| `010` | `X` | Index High | 4-bit | High nibble of the indirect address `X:Y`. |
| `011` | `Y` | Index Low | 4-bit | Low nibble of the indirect address `X:Y`. |
| `100` | `SP` | Stack Pointer | 4-bit | Low nibble of stack address. High nibble is fixed to `0xE`. |
| `101` | `FL` | Flags / Mode | 4-bit | `Reserved, M, C, Z`. |
| `110` | `PCH` | PC High | 4-bit | High nibble of program counter. |
| `111` | `PCL` | PC Low | 4-bit | Write triggers an immediate branch to `PCH:NewPCL`. |

Writing `PCL` updates the low nibble of `PC` and immediately redirects instruction fetch to the resulting `PCH:PCL` address.

### 2.3. Flag Register (`FL`)

`FL` is 4 bits wide:

| Bit | Name | Meaning |
| :---: | :--- | :--- |
| 3 | Reserved | No defined CPU control function in v4.3. |
| 2 | `M` | Execution bank: `1=System ROM`, `0=User RAM`. |
| 1 | `C` | Carry / borrow flag. |
| 0 | `Z` | Zero flag. |

`MOV FL,A` writes all four bits of `FL` exactly as present in `A`. The reserved bit is stored but has no defined effect on control logic.

### 2.4. Reset State

Hardware Reset establishes:

```text
PC = 0x00
SP = 0x0F
FL = 0x04
```

Therefore:

```text
Reserved = 0
M        = 1
C        = 0
Z        = 0
```

Execution starts with an instruction fetch from `ROM[0x00]`.

There is no reset-latch flag and there is no Shadow PC register in v4.3.

### 2.5. Flag Update Rules

`Z` and `C` are updated by arithmetic, logic, and pointer instructions. Non-ALU instructions preserve `Z` and `C` unless `FL` is explicitly written.

| Instruction | Operation | Carry `C` | Zero `Z` |
| :--- | :--- | :--- | :--- |
| `ADD Reg` | `A=A+Reg` | `1` if unsigned overflow > `0xF`, else `0` | `1` if result nibble is `0` |
| `SUB Reg` | `A=A-Reg` | `1` if borrow (`A<Reg`), else `0` | `1` if operands were equal |
| `AND Reg` | `A=A&Reg` | Always `0` | `1` if result is `0` |
| `XOR Reg` | `A=A^Reg` | Always `0` | `1` if result is `0` |
| `INC Reg` | `Reg=Reg+1` | `1` on `0xF->0x0`, else `0` | `1` if new register value is `0` |
| `DEC Reg` | `Reg=Reg-1` | `1` on `0x0->0xF`, else `0` | `1` if new register value is `0` |
| `INX` | `X:Y=X:Y+1` | `1` on `0xFF->0x00`, else `0` | `1` if new `X:Y=0x0000` |
| `DEX` | `X:Y=X:Y-1` | `1` on `0x0000->0x00FF`, else `0` | `1` if new `X:Y=0x0000` |

The following instructions preserve `Z` and `C`:

* `NOP`
* `LDI`
* `MOV` unless destination is `FL`
* `LDR`
* `STR`
* `JZ`, `JC`, `JMP`
* `CAL`, `RET`
* `HLT`
* `XBNK`
* `BOOT`
* `PHA`, `PLA`
* `LDRA`

`MOV FL,A` overwrites `Reserved`, `M`, `C`, and `Z`.

## 3. Memory Organization

### 3.1. Memory Banks

The CPU exposes two banks sharing the same 8-bit addresses:

1. **System Bank (ROM):** Active for instruction fetch when `M=1`. Contains the Nano-Monitor and system ROM data.
2. **User Bank (RAM):** Active for instruction fetch when `M=0`. Contains the user COM image, runtime data, stack, and MMIO.

### 3.2. Memory Map

The address map is:

| Address | Region | Purpose |
| :---: | :--- | :--- |
| `0x00` | Reset Entry | ROM Monitor entry point after Hardware Reset or `BOOT`. |
| `0x01..0x0F` | Monitor Reserved / Scratch | Reserved for Nano-Monitor state and temporary trampolines. |
| `0x10..0xDF` | User COM Space | Unified user code/data image. No code/data distinction is enforced by hardware. |
| `0xE0..0xEF` | Hardware Stack | Dedicated 16-nibble stack page. Not available to the user image. |
| `0xF0..0xF7` | Defined MMIO | Display, keyboard, audio/GPO, RNG. |
| `0xF8..0xFD` | Reserved MMIO | Reserved for future peripherals. |
| `0xFE..0xFF` | Reserved | Unmapped / reserved. |

The user COM image is therefore a single code/data area from `0x10` through `0xDF`. The user is responsible for deciding which cells contain executable code and which contain data.

The hardware stack is not part of the user image even though it lies immediately after the COM area.

### 3.3. Data Read Bank Selection

Standard `LDR` reads from the current execution bank. `LDRA` reads from the opposite bank.

Formally:

```text
LDR:  TargetBank = M
LDRA: TargetBank = M XOR 1
```

Therefore:

| `M` | `LDR` | `LDRA` |
| :---: | :--- | :--- |
| `1` | ROM | RAM |
| `0` | RAM | ROM |

`LDRA` changes only `A`; it does not change `M`, `Z`, or `C`.

### 3.4. Shadow Writes

All normal memory writes are directed to User RAM, regardless of `M`:

```text
STR
PHA
CAL stack writes
```

This allows ROM Monitor code to populate User RAM while remaining in System Mode.

MMIO devices occupy the RAM address space and therefore are also written through the `STR` path when their addresses are selected.

### 3.5. Instruction Fetch from Reserved/MMIO Space

Instruction fetches are valid only for addresses belonging to the executable ROM/RAM address space.

If execution reaches `0xF0..0xFF`, the CPU enters the same terminal behavior as `HLT`: instruction execution stops until Hardware Reset.

Reserved MMIO and Reserved addresses therefore do not form an alternative code-execution area.

## 4. Instruction Set Architecture

All instructions are 1, 2, or 3 nibbles long.

### 4.1. Master Opcode Table

| Opcode | Mnemonic | Arguments | Size | Operation |
| :---: | :--- | :--- | :---: | :--- |
| `0` | `NOP` | - | 1 | No operation. |
| `1` | `LDI` | Imm | 2 | `A=Imm`. |
| `2` | `MOV` | Mode+Reg | 2 | Register transfer. |
| `3` | `LDR` | - | 1 | `A=ActiveBank[X:Y]`. |
| `4` | `STR` | - | 1 | `RAM[X:Y]=A`. |
| `5` | `ADD` | Reg | 2 | `A=A+Reg`. |
| `6` | `SUB` | Reg | 2 | `A=A-Reg`. |
| `7` | `AND` | Reg | 2 | `A=A&Reg`. |
| `8` | `XOR` | Reg | 2 | `A=A^Reg`. |
| `9` | `INC` | Reg | 2 | `Reg=Reg+1`. |
| `A` | `DEC` | Reg | 2 | `Reg=Reg-1`. |
| `B` | `JZ` | Addr | 3 | Branch if `Z=1`. |
| `C` | `JC` | Addr | 3 | Branch if `C=1`. |
| `D` | `JMP` | Addr | 3 | Unconditional branch. |
| `E` | `CAL` | Addr | 3 | Push return address and branch. |
| `F` | `EXT` | Func | 2 | System and extended instruction group. |

The former `SYS` naming is retired in v4.3. Opcode `F` is the **EXT** instruction group.

### 4.2. `MOV` Format

The second nibble has the format `D R R R`:

* `D=0`: `MOV A,Reg`.
* `D=1`: `MOV Reg,A`.

Register ID values are those listed in Section 2.2.

## 5. Extended Instruction Group (`EXT`, Opcode `F`)

| Subopcode | Mnemonic | Size | Operation |
| :---: | :--- | :---: | :--- |
| `F0` | `HLT` | 2 | Halt CPU until Hardware Reset. |
| `F1` | `RET` | 2 | Pop return address from hardware stack. |
| `F2` | `PHA` | 2 | Push `A` onto hardware stack. |
| `F3` | `PLA` | 2 | Pop one nibble into `A`. |
| `F4` | Reserved | 2 | Reserved. |
| `F5` | Reserved | 2 | Reserved. |
| `F6` | `LDRA` | 2 | Read from opposite bank. |
| `F7` | `INX` | 2 | Increment `X:Y`. |
| `F8` | `DEX` | 2 | Decrement `X:Y`. |
| `F9` | `XBNK` | 2 | Toggle execution bank. |
| `FA` | `BOOT` | 2 | Reset execution state to ROM Monitor entry. |
| `FB`..`FE` | Reserved | 2 | Reserved for future allocation. |
| `FF` | Reserved Prefix | 2+ | Reserved; not implemented in v4.3. |

### 5.1. `XBNK` — Exchange Execution Bank

`XBNK` is a bank-exchange instruction, not a data-read instruction.

Microoperation:

```text
M = M XOR 1
```

No other architectural register is modified.

### Pipeline Semantics

`XBNK` is a 2-nibble instruction. Its execution sequence is:

1. Fetch `F9` and its subopcode from the current execution bank.
2. Decode `XBNK`.
3. Invert `M`.
4. Advance `PC` by 2, exactly as for any other 2-nibble instruction.
5. Fetch the next instruction from the bank selected by the new `M`.

Therefore the address trajectory does not change; only the bank used for the next instruction fetch changes.

Example:

```text
Before XBNK:
PC = 0x50
M  = 1
ROM[0x50] = F9

After XBNK:
PC = 0x52
M  = 0

Next fetch:
RAM[0x52]
```

A common ROM-to-RAM trampoline is:

```text
ROM[0x50] = F9          ; XBNK
RAM[0x52] = D 0x1 0     ; JMP 0x10
```

The first instruction executes in ROM. After `XBNK`, the next instruction is fetched from RAM at `0x52`, and `JMP 0x10` transfers execution to the user COM entry point.

`XBNK` is useful in three contexts:

1. **ROM Monitor -> User RAM transfer:** change execution bank without rewriting PC trajectory.
2. **Flag-preserving bank change:** unlike `MOV FL,A`, `XBNK` changes only `M` and therefore preserves `Z/C`.
3. **Cross-bank ROM libraries:** user RAM code can switch into a ROM-side code path and later use another `XBNK` to return to RAM. Library entry points and register-clobbering rules are an ABI convention, not a hardware feature.

### 5.2. `BOOT` — Software Return to Monitor

`BOOT` returns control from User RAM to the ROM Monitor.

Microoperations:

```text
PC = 0x00
SP = 0x0F
M  = 1
```

`BOOT` immediately redirects the next instruction fetch to `ROM[0x00]`.

`BOOT` preserves:

```text
Z
C
Reserved bit 3
```

Thus `BOOT` is a software reset of the execution context, not an arithmetic flag reset.

### 5.3. `PHA` — Push Accumulator

```text
RAM[0xE0 | SP] = A
SP = (SP - 1) & 0xF
```

`PHA` uses the same stack as `CAL/RET` and does not modify `FL`.

### 5.4. `PLA` — Pop Accumulator

```text
SP = (SP + 1) & 0xF
A = RAM[0xE0 | SP]
```

`PLA` uses the same stack as `CAL/RET` and does not modify `FL`.

### 5.5. `INX` — Increment Address Pair

`X:Y` is treated as one 8-bit unsigned pointer:

```text
X:Y = (X:Y + 1) & 0xFF
```

Flag semantics:

```text
C = 1 only for 0xFF -> 0x00
Z = 1 only when the new X:Y is 0x0000
```

### 5.6. `DEX` — Decrement Address Pair

```text
X:Y = (X:Y - 1) & 0xFF
```

Flag semantics:

```text
C = 1 only for 0x00 -> 0xFF
Z = 1 only when the new X:Y is 0x0000
```

## 6. Subroutine and Stack Mechanics

### 6.1. Stack Organization

The hardware stack is fixed to RAM addresses:

```text
0xE0..0xEF
```

`SP` is a 4-bit register. Hardware prepends the high nibble `0xE` to form the physical stack address.

The stack grows downward.

```text
SP = 0xF  ->  RAM[0xEF]
SP = 0xE  ->  RAM[0xEE]
...
SP = 0x0  ->  RAM[0xE0]
```

`SP` wraps modulo 16. There is no hardware stack overflow/underflow exception.

Stack occupancy is measured in nibbles. A `CAL` consumes two nibbles; `PHA` consumes one nibble.

### 6.2. `CAL`

`CAL Addr` is a 3-nibble instruction:

```text
E Addr_High Addr_Low
```

Return address is `Next_PC = Current_PC + 3`.

Microoperations:

1. Write `PCH` to `RAM[0xE0|SP]`; decrement `SP`.
2. Write `PCL` to `RAM[0xE0|SP]`; decrement `SP`.
3. Set `PCH=Addr_High` and `PCL=Addr_Low`.

### 6.3. `RET`

`RET` is `F1`.

Microoperations:

1. Increment `SP`; read low return nibble into temporary hardware state.
2. Increment `SP`; read high return nibble into temporary hardware state.
3. Restore `PCH` and `PCL` and resume execution.

`RET` does not modify `Z` or `C`.

### 6.4. Mixed CALL/Data Stack Usage

`CAL/RET` and `PHA/PLA` share one physical stack. Software must balance its own stack usage.

Valid pattern:

```asm
CAL FUNCTION
...
FUNCTION:
PHA
...
PLA
RET
```

Invalid pattern:

```asm
CAL FUNCTION
...
FUNCTION:
PHA
...
RET
```

The second example leaves the stack pointer misaligned for the caller's `RET`.

## 7. Memory-Mapped I/O

Defined MMIO addresses are in RAM space:

| Address | Name | Access | Description |
| :---: | :--- | :---: | :--- |
| `0xF0` | `DISP_0` | R/W | Rightmost 7-segment hex display. |
| `0xF1` | `DISP_1` | R/W | Display digit 1. |
| `0xF2` | `DISP_2` | R/W | Display digit 2. |
| `0xF3` | `DISP_3` | R/W | Leftmost 7-segment hex display. |
| `0xF4` | `GPI_KBD` | R | Bit 0 = key status; bits 1..3 = GPI. |
| `0xF5` | `KBD_CODE` | R | Latched 4-bit key code. |
| `0xF6` | `GPO_AUD` | R/W | Bit 0 = audio; bits 1..3 = GPO. |
| `0xF7` | `RNG` | R | 4-bit pseudo-random value. |
| `0xF8..0xFD` | Reserved MMIO | Reserved | Peripheral expansion. |
| `0xFE..0xFF` | Reserved | Reserved | Unmapped. |

`KBD_CODE` is latched on the keyboard strobe and retains the last key code after the key is released.

Recommended polling sequence:

```asm
WAIT_PRESS:
    LDR
    AND B
    JZ WAIT_PRESS
```

After the key status becomes active, read `KBD_CODE`, then poll until the key status is released. This avoids interpreting a held key as repeated key presses.

Reserved MMIO reads return `0x0` in the reference implementation. Reserved MMIO writes are ignored. These values are implementation-defined only if a future peripheral extension overrides them.

## 8. ROM Monitor / User RAM Execution Model

The intended system model is:

```text
             Hardware Reset
                    |
                    v
             ROM[0x00]
                    |
                    v
             Nano-Monitor
                    |
              XBNK trampoline
                    |
                    v
              User RAM
                    |
                  BOOT
                    |
                    v
             ROM[0x00]
```

### 8.1. Loading a COM Image

Nano-Monitor loads the user image starting at `0x10`.

The user image is a single contiguous code/data area through `0xDF`. The monitor does not distinguish code from data.

The range is:

```text
0x10..0xDF = 208 nibbles = 104 bytes
```

The hardware stack at `0xE0..0xEF` is not part of the user image.

### 8.2. Running the User Program

A minimal ROM-to-RAM transfer can use:

```text
ROM: XBNK
RAM: JMP 0x10
```

The `XBNK` instruction transfers the next fetch into RAM without modifying the PC trajectory. The RAM-side `JMP` then moves execution to the fixed COM entry at `0x10`.

### 8.3. Returning to the Monitor

The user program terminates with:

```asm
BOOT
```

This restores:

```text
PC = 0x00
SP = 0x0F
M  = 1
```

and resumes Nano-Monitor execution from ROM.

## 9. Cross-Bank Library ABI

`XBNK` provides a hardware mechanism for crossing between executable ROM and RAM banks, but v4.3 does not define a mandatory system-library calling convention.

A library ABI may specify:

* entry address;
* required `X` and `Y` values;
* argument registers;
* return values;
* registers preserved by the callee;
* whether the library returns by `XBNK`, `JMP`, or another documented mechanism.

A ROM library invoked from RAM must arrange its entry point so that the bank exchange occurs at a known PC trajectory. Likewise, a ROM library returning to RAM must execute an `XBNK` at a compatible address or use a documented trampoline.

## 10. Assembler Requirements

The reference assembler should support the following v4.3 syntax:

```asm
ORG 0x10
LDI 0x5
MOV B,A
INX
LDRA
PHA
PLA
XBNK
BOOT
HLT
```

The assembler should treat `F` as an extended opcode group rather than the legacy `SYS` mnemonic.

Recommended aliases:

```text
F0 = HLT
F1 = RET
F2 = PHA
F3 = PLA
F6 = LDRA
F7 = INX
F8 = DEX
F9 = XBNK
FA = BOOT
```

`F4`, `F5`, `FB`, `FC`, `FD`, `FE`, and `FF` are reserved in v4.3 and should not assemble as executable instructions except where the assembler intentionally supports a raw opcode/data mode.

## 11. Implementation Requirements for CPU / Emulator

The CPU implementation should include the following mandatory tests.

### 11.1. Reset

After Hardware Reset:

```text
PC = 0x00
SP = 0x0F
FL = 0x04
M = 1
```

### 11.2. XBNK

Verify:

```text
ROM[0x50] = F9
RAM[0x52] = D 0x1 0
```

After executing `ROM[0x50]`:

```text
PC = 0x52
M = 0
```

and the next instruction fetch must come from `RAM[0x52]`.

Also verify that `A`, `B`, `X`, `Y`, `SP`, `Z`, and `C` are unchanged.

### 11.3. BOOT

With arbitrary `PC`, `SP`, and `M`:

```text
BOOT
```

must produce:

```text
PC = 0x00
SP = 0x0F
M = 1
```

and fetch the next instruction from ROM.

### 11.4. PHA / PLA

Verify:

```text
A = 0xA
PHA
A = 0x3
PLA
```

After `PLA`:

```text
A = 0xA
```

and `SP` must return to its original value. `Z/C` must remain unchanged.

### 11.5. INX

Verify:

```text
0x0000 -> 0x0001
0x000F -> 0x0010
0x00FF -> 0x0100
0xFFFF -> 0x0000
```

with `C=1` only for the last transition and `Z=1` only when the new pointer is zero.

### 11.6. DEX

Verify:

```text
0x0001 -> 0x0000
0x0010 -> 0x000F
0x0100 -> 0x00FF
0x0000 -> 0x00FF
```

with `C=1` only for the final underflow transition and `Z=1` only when the new pointer is zero.

### 11.7. Stack Mixing

Verify that a sequence such as:

```text
CAL -> PHA -> PLA -> RET
```

returns to the original caller with the original `SP`.

### 11.8. Reserved / MMIO Fetch

Verify that instruction fetch from `0xF0..0xFF` enters the terminal halt behavior defined in Section 3.5.

## 12. Design Rationale

NC-1 v4.3 intentionally does not implement a general-purpose interrupt or syscall subsystem. The intended software model is a small ROM Monitor controlling a single User RAM execution environment.

The removed mechanisms were:

```text
R flag
SWI
SPC_H
SPC_L
RETU
```

The replacement mechanisms are:

```text
XBNK  -- execution bank transfer
BOOT  -- return to ROM Monitor
PHA   -- register preservation
PLA   -- register restoration
INX   -- 8-bit pointer increment
DEX   -- 8-bit pointer decrement
```

This keeps the control unit small while moving common software patterns into compact hardware primitives.

## Appendix A — Example: ROM-to-RAM Trampoline

ROM code:

```asm
TRAMPOLINE:
    XBNK
```

User RAM at the next address:

```asm
    JMP 0x10
```

If `TRAMPOLINE` is located at `0x50`, the sequence is:

```text
ROM[0x50] = F9          ; XBNK
RAM[0x52] = D0 10       ; JMP 0x10
```

Execution:

```text
ROM[0x50] -> XBNK
M: 1 -> 0
PC: 0x50 -> 0x52
RAM[0x52] -> JMP 0x10
RAM[0x10] -> user program
```

## Appendix B — Example: PHA / PLA

```asm
MY_SUBROUTINE:
    PHA
    ; Modify A freely
    LDI 0x5
    PLA
    RET
```

After `PLA`, the original accumulator value is restored.

## Appendix C — Example: INX Loop

```asm
    LDI 0x2
    MOV X,A
    LDI 0x0
    MOV Y,A
LOOP:
    ; process memory at X:Y
    INX
    JZ DONE
    JMP LOOP
DONE:
    BOOT
```

## Appendix D — Loading and Running a COM Image

Nano-Monitor uses the fixed COM entry address `0x10`.

A user program is assembled as:

```asm
ORG 0x10
START:
    ; user code
    BOOT
```

The monitor writes the assembled nibble stream into RAM starting at `0x10`. It does not interpret the image as instructions or data.

The complete runtime cycle is:

```text
LOAD -> User RAM[0x10..0xDF] -> XBNK trampoline -> User program -> BOOT -> ROM Monitor
```
