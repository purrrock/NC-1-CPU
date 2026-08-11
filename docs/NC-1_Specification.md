# NC-1 MICROPROCESSOR TECHNICAL SPECIFICATION

**Version:** 4.1 (Cross-bank Access Update)
**Architecture:** 4-bit RISC / Modified Harvard
**Date:** 2026

## 1. General Description
The **NC-1** is a 4-bit microprocessor with 8-bit addressing, designed for embedded systems and educational hardware projects. The architecture is optimized for minimal logic gate count while maintaining high programming flexibility.

Key Features:
* **Orthogonal Register File:** Direct access to Program Counter (PC), Stack Pointer (SP), and Status Flags as standard registers.
* **Dual-Bank Memory Architecture:** Separate System (ROM) and User (RAM) banks with hardware privilege protection.
* **Symmetric Cross-Bank Access (`LDRA`):** High-speed 2-cycle data fetching across memory banks without mode switching overhead.
* **Single Entry Point Vector:** Simplified reset and interrupt handling via status flags.
* **Hardware Stack Support:** Hardware-assisted subroutine call/return flow (`CAL` / `RET`).

## 2. Hardware Architecture

### 2.1. Buses and Bit Widths
* **Data Bus:** 4-bit (Nibble). Value range: `0..15` (`0x0..0xF`).
* **Address Bus:** 8-bit. Addressable space: 256 nibbles per bank (512 nibbles total).

### 2.2. Register Map
The CPU features 8 internal registers addressed by a 3-bit identifier (`000`..`111`).

| ID (Bin) | Mnemonic | Purpose | Access Notes |
| :--- | :--- | :--- | :--- |
| **000** | **A** | Accumulator | Primary register for ALU and I/O operations. |
| **001** | **B** | Aux / General | General-purpose auxiliary register. |
| **010** | **X** | Index High | High nibble of address for indirect access. |
| **011** | **Y** | Index Low | Low nibble of address for indirect access. |
| **100** | **SP** | Stack Pointer | Stack pointer. Decrements on `PUSH`/`CAL`. |
| **101** | **FL** | Flags | Status register (see Section 2.3). |
| **110** | **PCH** | PC High | High nibble of Program Counter. |
| **111** | **PCL** | PC Low | **Write:** Triggers immediate jump to `PCH:NewPCL`. |

*Note:* Writing to `PCL` updates the low nibble of the PC and triggers an immediate branch. Reading `PCL` returns the current instruction address offset.

### 2.3. Flag Register (FLAGS / FL)
Width: 4 bits.

| Bit 3 (MSB) | Bit 2 | Bit 1 | Bit 0 (LSB) |
| :--- | :--- | :--- | :--- |
| **R** (Reset) | **M** (Mode) | **C** (Carry) | **Z** (Zero) |

* **R (Reset Latch):** Hardware set to `1` on power-on or hard reset. Cleared only via software (writing `0` to bit 3). Used to distinguish cold boot from software syscalls.
* **M (System Mode):** `1` = System Bank (ROM / OS) active. `0` = User Bank (RAM) active.
* **C (Carry):** Arithmetic carry/borrow flag.
* **Z (Zero):** Arithmetic zero flag.

## 3. Memory Organization & Cross-Bank Logic

### 3.1. Memory Banks
The CPU addresses a 256-nibble window (`00..FF`), switched according to the **M** flag and instruction context.

1. **System Bank (ROM):** Active when `M=1`. Contains OS code, monitor firmware, and system drivers.
2. **User Bank (RAM):** Active when `M=0`. Contains user program code and runtime data.

### 3.2. Access Logic & Cross-Bank Read (`LDRA`)
* **Write Operations (`STR`):** Always target **RAM** (User Bank) regardless of mode ("Shadow Write").
* **Read Operations (`LDR` vs `LDRA`):** Selected hardware target bank for reads is determined by a XOR operation:
  
  $$\text{Target\_Bank\_Read} = M \oplus \text{Is\_SYS\_6}$$

  where `Is_SYS_6` is `1` when executing `SYS 6` (`LDRA`), and `0` otherwise.

#### Read Target Truth Table:
| Current Mode (M) | Instruction | Is_SYS_6 | Selected Read Bank | Usage Scenario |
| :--- | :--- | :--- | :--- | :--- |
| `1` (ROM / Kernel) | `LDR` | `0` | **ROM (`1`)** | OS reads kernel code/constants |
| `1` (ROM / Kernel) | `LDRA` | `1` | **RAM (`0`)** | OS reads user buffers / zero-page variables |
| `0` (RAM / User) | `LDR` | `0` | **RAM (`0`)** | User reads local variables |
| `0` (RAM / User) | `LDRA` | `1` | **ROM (`1`)** | User reads OS fonts/math lookup tables |

### 3.3. Memory Map
Unified layout across both banks (`00`..`FF`).

| Address (HEX) | Region | Description |
| :--- | :--- | :--- |
| **00 - 0F** | **Vectors / Zero Page** | `00`: Unified Entry Point (Reset & Syscall). `01-0F`: OS zero-page variables. |
| **10 - CF** | **Program Space** | Primary user/kernel code space (192 nibbles). |
| **D0 - EF** | **Stack / Data** | Hardware stack space (grows down from EF) and buffers. |
| **F0 - FF** | **MMIO Ports** | Memory-mapped I/O peripherals (see Section 5). |

## 4. Instruction Set Architecture (ISA)

All instructions have variable length (1, 2, or 3 nibbles).

### Master Opcode Table

| Op | Mnemonic | Arguments | Size (Nibbles) | Action Description |
| :--- | :--- | :--- | :--- | :--- |
| **0** | `NOP` | - | 1 | No operation. |
| **1** | `LDI` | Imm (4b) | 2 | `A = Imm` |
| **2** | `MOV` | Mode+Reg | 2 | Register transfer (see Section 4.1). |
| **3** | `LDR` | - | 1 | `A = CurrentBank[X:Y]` (Indirect load from active bank) |
| **4** | `STR` | - | 1 | `RAM[X:Y] = A` (Shadow write to RAM) |
| **5** | `ADD` | Reg (3b) | 2 | `A = A + Reg` |
| **6** | `SUB` | Reg (3b) | 2 | `A = A - Reg` |
| **7** | `AND` | Reg (3b) | 2 | `A = A & Reg` |
| **8** | `XOR` | Reg (3b) | 2 | `A = A ^ Reg` |
| **9** | `INC` | Reg (3b) | 2 | `Reg = Reg + 1` |
| **A** | `DEC` | Reg (3b) | 2 | `Reg = Reg - 1` |
| **B** | `JZ` | Addr (8b) | 3 | If `Z=1`, `PC = Addr` |
| **C** | `JC` | Addr (8b) | 3 | If `C=1`, `PC = Addr` |
| **D** | `JMP` | Addr (8b) | 3 | `PC = Addr` (Unconditional Jump) |
| **E** | `CAL` | Addr (8b) | 3 | `PUSH PCH`, `PUSH PCL`, `PC = Addr` |
| **F** | `SYS` | Func (4b) | 2 | System functions (see Section 4.2). |

### 4.1. MOV Format (Opcode 2)
Argument (2nd nibble) structure: `D R R R`.
* **D (Direction):**
  * `0`: `MOV A, Reg` (Read Reg into A).
  * `1`: `MOV Reg, A` (Write A into Reg).
* **RRR:** Register ID (`000`..`111`).

### 4.2. SYS Functions (Opcode F)
* `F0`: **HLT** (Halt CPU until hardware reset).
* `F1`: **RET** (Subroutine return: `POP PCL`, `POP PCH`).
* `F4`: **SWI** (Software Interrupt / Syscall).
  * Action: `SPC = PC` (save return address), `M = 1` (kernel mode), `PC = 0` (jump to entry point).
* `F5`: **RETU** (Return to User mode).
  * Action: `PC = SPC`, `M = 0`.
* `F6`: **LDRA** (Load Alternate Bank).
  * Action: `A = AlternateBank[X:Y]`. Reads from opposite bank using `Target_Bank = M ⊕ 1`.

## 5. Memory-Mapped I/O Subsystem (MMIO)
Peripherals are mapped to addresses `F0`..`FF`. Writes are directed to RAM/Peripherals; reads query device status.

| Address | Name | R/W | Description |
| :--- | :--- | :--- | :--- |
| `F0` | **DISP_0** | W | Rightmost 7-segment hex display. |
| `F1` | **DISP_1** | W | Display 1. |
| `F2` | **DISP_2** | W | Display 2. |
| `F3` | **DISP_3** | W | Leftmost 7-segment hex display. |
| `F4` | **KBD_STAT** | R | `Bit 0`: 1 = Key pressed, 0 = Released. |
| `F5` | **KBD_CODE** | R | Pressed key code (`0x0`..`0xF`). |
| `F6` | **AUDIO** | W | `Bit 0`: Speaker control (1=On, 0=Off). |
| `F7` | **RNG** | R | Random Number Generator. |
| `FE` | **SPC_L** | R/W | Low nibble of Shadow PC (debugging/kernel). |
| `FF` | **SPC_H** | R/W | High nibble of Shadow PC (debugging/kernel). |

## 5. Memory-Mapped I/O Subsystem (MMIO)
Peripherals are mapped to addresses `F0`..`FF`.

| Address | Name | R/W | Bit 3 | Bit 2 | Bit 1 | Bit 0 | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `F0` | **DISP_0** | R/W | D3 | D2 | D1 | D0 | Rightmost 7-segment hex display. |
| `F1` | **DISP_1** | R/W | D3 | D2 | D1 | D0 | Display 1. |
| `F2` | **DISP_2** | R/W | D3 | D2 | D1 | D0 | Display 2. |
| `F3` | **DISP_3** | R/W | D3 | D2 | D1 | D0 | Leftmost 7-segment hex display. |
| `F4` | **GPI_KBD** | R | `GPI_3` | `GPI_2` | `GPI_1` | `KBD` | `Bit 0`: 1 = Key pressed. `Bits 1..3`: General Purpose Input lines. |
| `F5` | **KBD_CODE**| R | K3 | K2 | K1 | K0 | Pressed key code (`0x0`..`0xF`). |
| `F6` | **GPO_AUD** | R/W | `GPO_3` | `GPO_2` | `GPO_1` | `AUD` | `Bit 0`: Speaker (1=On). `Bits 1..3`: General Purpose Output lines. |
| `F7` | **RNG** | R | R3 | R2 | R1 | R0 | Random Number Generator. |
| `FE` | **SPC_L** | R/W | S3 | S2 | S1 | S0 | Low nibble of Shadow PC (debugging/kernel). |
| `FF` | **SPC_H** | R/W | S7 | S6 | S5 | S4 | High nibble of Shadow PC (debugging/kernel). |

## 6. System Reset & Interrupt Logic

### Hardware Reset Sequence
1. Assert `Reset` signal to CPU.
2. Internal registers reset: `PC = 00`, `SP = 00`.
3. Status flags set: **`R = 1`**, `M = 1` (System Mode).
4. Execution starts at address `00` in ROM.

### Entry Point Dispatcher (`0x00`)
Example kernel dispatcher code in ROM:

```asm
00: 2 (MOV) 0 101   ; MOV A, FL (Read flags)
02: 7 (AND) 8       ; Mask bit R (8 = 1000b)
04: B (JZ)  HANDLER ; If R=0, jump to Syscall Handler
06: ...             ; If R=1, execute Cold Boot sequence
```

### Appendix A: Cross-Bank Call & Read Example
**Scenario:** OS kernel (`M=1`) reads user parameters from Zero Page (`RAM[0x05]`) using `LDRA`.

```asm
; Kernel executing in ROM (M=1)
00: 1 (LDI) 0       ; A = 0
02: 2 (MOV) 1 010   ; MOV X, A (X = 0)
04: 1 (LDI) 5       ; A = 5
06: 2 (MOV) 1 011   ; MOV Y, A (Y = 5, address = 0x05)
08: F (SYS) 6       ; LDRA (Opcode F6) -> Reads RAM[0x05] into A
```