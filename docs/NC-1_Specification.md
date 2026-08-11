# NC-1 MICROPROCESSOR TECHNICAL SPECIFICATION

**Version:** 4.2 (Page-Locked Stack & Extended MMIO Specification)  
**Architecture:** 4-bit RISC / Modified Harvard  
**Date:** 2026

---

## 1. General Description

The **NC-1** is a 4-bit microprocessor with an 8-bit addressing space, designed for embedded systems, hardware emulation, and educational computer engineering projects. The architecture minimizes logic gate count while delivering high programming flexibility, featuring privilege separation, cross-bank memory access, and a hardware-assisted stack.

### Key Features
* **Orthogonal Register File:** Direct access to Program Counter (`PC`), Stack Pointer (`SP`), and Status Flags (`FL`) as standard registers.
* **Dual-Bank Memory Architecture:** Separate System (ROM) and User (RAM) banks with hardware-enforced privilege protection.
* **Page-Locked Hardware Stack:** 4-bit physical Stack Pointer mapped to a dedicated 16-nibble RAM page (`0xE0`..`0xEF`).
* **Symmetric Cross-Bank Access (`LDRA`):** High-speed 2-cycle data fetching across memory banks without mode-switching overhead.
* **Extended MMIO Subsystem:** Read/Write display registers, 3-bit General Purpose Input (GPI), and 3-bit General Purpose Output (GPO) integration.
* **Single Entry Point Vector:** Simplified reset and software interrupt handling via hardware status latching.

---

## 2. Hardware Architecture

### 2.1. Buses and Bit Widths
* **Data Bus:** 4-bit (Nibble). Value range: `0..15` (`0x0`..`0xF`).
* **Address Bus:** 8-bit. Addressable space: 256 nibbles per bank (512 nibbles total across ROM and RAM).

---

### 2.2. Register Map
The CPU features 8 internal registers addressed by a 3-bit identifier (`000`b..`111`b).

| ID (Bin) | Mnemonic | Purpose | Width | Access & Hardware Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **000** | **A** | Accumulator | 4-bit | Primary register for ALU, I/O, and data transfer operations. |
| **001** | **B** | Aux / General | 4-bit | General-purpose auxiliary register. |
| **010** | **X** | Index High | 4-bit | High nibble of address pointer for indirect memory access (`X:Y`). |
| **011** | **Y** | Index Low | 4-bit | Low nibble of address pointer for indirect memory access (`X:Y`). |
| **100** | **SP** | Stack Pointer | **4-bit** | Holds the low nibble of the stack address. High nibble is hardware-fixed to `0xE`. |
| **101** | **FL** | Flags | 4-bit | Status and control register (`R`, `M`, `C`, `Z`). |
| **110** | **PCH** | PC High | 4-bit | High nibble of Program Counter. |
| **111** | **PCL** | PC Low | 4-bit | **Write:** Triggers an immediate execution branch to `PCH:NewPCL`. |

*Note on PCL:* Writing to `PCL` updates the low nibble of the Program Counter and immediately redirects pipeline fetch to `PCH:NewPCL`. Reading `PCL` returns the current instruction execution address offset.

---

### 2.3. Flag Register (FLAGS / FL)
Width: 4 bits.

| Bit 3 (MSB) | Bit 2 | Bit 1 | Bit 0 (LSB) |
| :---: | :---: | :---: | :---: |
| **R** (Reset) | **M** (Mode) | **C** (Carry) | **Z** (Zero) |

* **R (Reset Latch):** Set to `1` by hardware upon power-on or hard reset. Cleared strictly via software (by writing `0` to Bit 3). Used by the OS entry point to distinguish cold boot from software syscalls.
* **M (System Mode):** `1` = System Bank (ROM / Kernel) active. `0` = User Bank (RAM) active.
* **C (Carry):** Arithmetic carry/borrow flag.
* **Z (Zero):** Arithmetic zero flag.

---

### 2.4. Flag Update Rules (ALU Flags Behavior)

The status flags **Z** (Zero, Bit 0) and **C** (Carry, Bit 1) in the `FL` register are updated by arithmetic and logic operations. Non-ALU instructions do not alter **Z** and **C** unless `FL` is explicitly written as a destination register.

| Instruction | Operation | Carry Flag (C) | Zero Flag (Z) |
| :--- | :--- | :--- | :--- |
| **`ADD Reg`** | `A = A + Reg` | `1` if result $> 15$ (4-bit unsigned overflow), else `0`. | `1` if `(A + Reg) & 0xF == 0`, else `0`. |
| **`SUB Reg`** | `A = A - Reg` | `1` if borrow occurred ($A < \text{Reg}$), else `0`. | `1` if `A == Reg` (result $= 0$), else `0`. |
| **`AND Reg`** | `A = A & Reg` | Always cleared to `0`. | `1` if result $= 0$, else `0`. |
| **`XOR Reg`** | `A = A ^ Reg` | Always cleared to `0`. | `1` if result $= 0$, else `0`. |
| **`INC Reg`** | `Reg = Reg + 1` | `1` if overflow occurred (`0xF + 1`), else `0`. | `1` if new `Reg == 0`, else `0`. |
| **`DEC Reg`** | `Reg = Reg - 1` | `1` if underflow occurred (`0x0 - 1`), else `0`. | `1` if new `Reg == 0`, else `0`. |

#### Non-ALU Flag Behavior:
* **Data Transfer (`LDI`, `MOV` [except destination `FL`], `LDR`, `STR`, `LDRA`):** Preserve existing **Z** and **C** flags.
* **Control Flow (`NOP`, `JZ`, `JC`, `JMP`, `CAL`, `RET`, `HLT`, `SWI`, `RETU`):** Preserve existing **Z** and **C** flags.
* **Direct Register Write (`MOV FL, A`):** Overwrites all 4 bits of `FL` (`R`, `M`, `C`, `Z`) with the contents of register `A`.

---

## 3. Memory Organization & Cross-Bank Logic

### 3.1. Memory Banks
The CPU addresses a 256-nibble window (`00`..`FF`), mapped dynamically depending on privilege flag **M** and instruction context.

1. **System Bank (ROM):** Active when `M=1`. Houses OS kernel code, monitor firmware, system call handlers, and system lookup tables.
2. **User Bank (RAM):** Active when `M=0`. Houses user code, runtime data, zero-page variables, hardware stack, and MMIO ports.

---

### 3.2. Access Logic & Cross-Bank Read (`LDRA`)
* **Write Operations (`STR`):** All memory writes are unconditionally directed to **RAM** (User Bank) regardless of mode ("Shadow Write" mechanism). This enables the OS in ROM to write data into RAM without mode switching.
* **Read Operations (`LDR` vs `LDRA`):** The target memory bank for data reads is evaluated using hardware XOR logic:

$$\text{Target\_Bank\_Read} = M \oplus \text{Is\_SYS\_6}$$

where `Is_SYS_6` is `1` during execution of `SYS 6` (`LDRA`), and `0` during standard `LDR` operations.

#### Memory Read Truth Table:
| Mode (M) | Instruction | Is_SYS_6 | Read Target Bank | Application |
| :---: | :---: | :---: | :---: | :--- |
| `1` (Kernel) | `LDR` | `0` | **ROM (`1`)** | OS reads kernel code/ROM constants |
| `1` (Kernel) | `LDRA` | `1` | **RAM (`0`)** | OS reads user buffers / zero-page state |
| `0` (User) | `LDR` | `0` | **RAM (`0`)** | User program reads local data/RAM |
| `0` (User) | `LDRA` | `1` | **ROM (`1`)** | User program reads OS fonts / math tables |

---

### 3.3. Memory Map & ABI Allocation
Unified address space layout across both banks (`00`..`FF`).

| Address (HEX) | Region | Access Privilege | Description & ABI Usage |
| :---: | :---: | :---: | :--- |
| **`00`** | **Entry Vector** | Hardware | Unified entry point for Reset (`R=1`) and SWI (`R=0`). |
| **`01` - `0F`** | **Zero Page** | Kernel / Reserved | Reserved for OS state preservation (user register saves during `SWI`). |
| **`10` - `CF`** | **Program Space** | User / Kernel | Primary code execution space (192 nibbles). |
| **`D0` - `DF`** | **Buffer Space** | User / Kernel | General-purpose data workspace. |
| **`E0` - `EF`** | **Hardware Stack** | Hardware / Stack | Dedicated 16-nibble Page-Locked Stack space (`0xE0`..`0xEF`). |
| **`F0` - `FF`** | **MMIO Ports** | Memory-Mapped I/O | Peripheral device control and registers (see Section 5). |

*Hardware vs. ABI Note:* The RAM hardware is uniform. Executing code from `0x00` in User Mode (`M=0`) is physically valid. However, the OS ABI reserves `0x01`..`0x0F` as Zero Page workspace. User programs allocating data in `0x01`..`0x0F` risk state corruption during system calls.

---

## 4. Instruction Set Architecture (ISA)

All instructions have variable length (1, 2, or 3 nibbles).

### 4.1. Master Opcode Table

| Opcode | Mnemonic | Arguments | Size (Nibbles) | Operation Description |
| :---: | :--- | :--- | :---: | :--- |
| **`0`** | `NOP` | - | 1 | No operation. |
| **`1`** | `LDI` | Imm (4b) | 2 | `A = Imm` |
| **`2`** | `MOV` | Mode+Reg | 2 | Register transfer (see Section 4.2). |
| **`3`** | `LDR` | - | 1 | `A = CurrentBank[X:Y]` (Indirect load from active bank) |
| **`4`** | `STR` | - | 1 | `RAM[X:Y] = A` (Shadow write to RAM) |
| **`5`** | `ADD` | Reg (3b) | 2 | `A = A + Reg` |
| **`6`** | `SUB` | Reg (3b) | 2 | `A = A - Reg` |
| **`7`** | `AND` | Reg (3b) | 2 | `A = A & Reg` |
| **`8`** | `XOR` | Reg (3b) | 2 | `A = A ^ Reg` |
| **`9`** | `INC` | Reg (3b) | 2 | `Reg = Reg + 1` |
| **`A`** | `DEC` | Reg (3b) | 2 | `Reg = Reg - 1` |
| **`B`** | `JZ` | Addr (8b) | 3 | If `Z == 1`, `PC = Addr` |
| **`C`** | `JC` | Addr (8b) | 3 | If `C == 1`, `PC = Addr` |
| **`D`** | `JMP` | Addr (8b) | 3 | `PC = Addr` (Unconditional Jump) |
| **`E`** | `CAL` | Addr (8b) | 3 | `PUSH PCH`, `PUSH PCL`, `PC = Addr` |
| **`F`** | `SYS` | Func (4b) | 2 | System functions (see Section 4.3). |

---

### 4.2. MOV Format (Opcode 2)
Argument (2nd nibble) structure: `D R R R` (4 bits).
* **D (Direction Bit):**
  * `0`: `MOV A, Reg` (Read Register `RRR` into Accumulator `A`).
  * `1`: `MOV Reg, A` (Write Accumulator `A` into Register `RRR`).
* **RRR (Register ID):** 3-bit Register Identifier (`000`b..`111`b).

---

### 4.3. SYS Functions (Opcode F)
* **`F0` (`HLT`):** Halt CPU until hardware reset.
* **`F1` (`RET`):** Subroutine return (`POP PCL`, `POP PCH`).
* **`F4` (`SWI`):** Software Interrupt / Syscall.
  * Action: `SPC = PC` (save return address), `M = 1` (kernel mode), `PC = 0` (jump to entry point).
* **`F5` (`RETU`):** Return to User mode.
  * Action: `PC = SPC`, `M = 0`.
* **`F6` (`LDRA`):** Load Alternate Bank.
  * Action: `A = AlternateBank[X:Y]`. Reads from opposite bank using $\text{Target\_Bank} = M \oplus 1$.

---

## 4.4. Subroutine Call and Return Mechanics (Page-Locked Stack)

Subroutine control flow in NC-1 uses a **Page-Locked Hardware Stack**. 
To match the 4-bit register file, the physical Stack Pointer (`SP`, Register ID `100`b) is a 4-bit register. The Memory Management Unit (MMU) automatically prepends a hardcoded high nibble of `0xE` (`1110`b) to all stack memory cycles.

This fixes the stack in RAM across addresses `0xE0` to `0xEF` (16 nibbles capacity, supporting up to 8 nested subroutine calls). The stack grows downward.

* **Hardware Memory Routing:** All stack read and write micro-operations (`CAL`, `RET`, `PUSH`, `POP`) route strictly to the **RAM bank** regardless of the privilege mode bit **M**.
* **Stack Overflow/Underflow Behavior:** The 4-bit `SP` register wraps around modulo 16 (`0x0 - 1 = 0xF`; `0xF + 1 = 0x0`). There is no hardware trap or exception for stack overflow/underflow.
* **Stack Reset:** Hardware Reset sets `SP = 0xF` (initial top of stack = `0xEF`). Software can reset `SP` by executing `LDI F` followed by `MOV SP, A`.

```text
Stack Memory Map (RAM Page 0xE)
      +-----------------+
0xF0  | MMIO Boundary   |
      +-----------------+
      |  PCL (Low)      |  <- SP points to top of stack (last pushed nibble)
      +-----------------+
      |  PCH (High)     |
      +-----------------+
      | Previous Data   |
      +-----------------+  Address 0xEF (Initial SP state)
```

### Hardware Subroutine Call (`CAL Addr`) — Opcode `E`
Instruction layout: 3 nibbles (`E Addr_High Addr_Low`).  
Return address: `Next_PC = Current_PC + 3`.

1. **Push High Nibble (`PCH`):**
   * Write `PCH` to `RAM[0xE0 | SP]`.
   * Decrement Stack Pointer: `SP = (SP - 1) & 0xF`.
2. **Push Low Nibble (`PCL`):**
   * Write `PCL` to `RAM[0xE0 | SP]`.
   * Decrement Stack Pointer: `SP = (SP - 1) & 0xF`.
3. **Execute Branch:**
   * `PCH = Addr_High`
   * `PCL = Addr_Low` (triggers pipeline fetch at target address).

---

### Subroutine Return (`RET`) — Opcode `F1` (`SYS 1`)
Pops the 8-bit return address from the hardware stack.

1. **Pop Low Nibble (`PCL`):**
   * Increment Stack Pointer: `SP = (SP + 1) & 0xF`.
   * Read low nibble: `Temp_PCL = RAM[0xE0 | SP]`.
2. **Pop High Nibble (`PCH`):**
   * Increment Stack Pointer: `SP = (SP + 1) & 0xF`.
   * Read high nibble: `Temp_PCH = RAM[0xE0 | SP]`.
3. **Restore Execution:**
   * `PCH = Temp_PCH`
   * `PCL = Temp_PCL` (triggers execution resume at saved `Next_PC`).

---

## 5. Memory-Mapped I/O Subsystem (MMIO)

Peripherals are mapped to addresses `F0`..`FF` in RAM space. Display registers `F0`..`F3` and audio/GPO register `F6` support Read/Write (R/W) access, allowing them to serve as auxiliary storage nibbles if display/output flickering is acceptable.

| Address | Name | Access | Bit 3 | Bit 2 | Bit 1 | Bit 0 | Description & Hardware Function |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`F0`** | **DISP_0** | R/W | D3 | D2 | D1 | D0 | Rightmost 7-segment display (Hex digit `0`..`F`). |
| **`F1`** | **DISP_1** | R/W | D3 | D2 | D1 | D0 | Display digit 1. |
| **`F2`** | **DISP_2** | R/W | D3 | D2 | D1 | D0 | Display digit 2. |
| **`F3`** | **DISP_3** | R/W | D3 | D2 | D1 | D0 | Leftmost 7-segment display (Hex digit `0`..`F`). |
| **`F4`** | **GPI_KBD**| R | `GPI_3` | `GPI_2` | `GPI_1` | `KBD` | **Bit 0:** Key status (1=Pressed, 0=Released).<br>**Bits 1..3:** General Purpose Input lines. |
| **`F5`** | **KBD_CODE**| R | K3 | K2 | K1 | K0 | Key code of pressed button (`0x0`..`0xF`). |
| **`F6`** | **GPO_AUD** | R/W | `GPO_3` | `GPO_2` | `GPO_1` | `AUD` | **Bit 0:** Speaker toggle (1=On, 0=Off).<br>**Bits 1..3:** General Purpose Output lines. |
| **`F7`** | **RNG** | R | R3 | R2 | R1 | R0 | Pseudo-random number generator output (`0x0`..`0xF`). |
| **`FE`** | **SPC_L** | R/W | S3 | S2 | S1 | S0 | Low nibble of Shadow PC (Syscall return address). |
| **`FF`** | **SPC_H** | R/W | S7 | S6 | S5 | S4 | High nibble of Shadow PC (Syscall return address). |

---

## 6. System Reset & Interrupt Logic

### 6.1. Hardware Reset Sequence
1. Assert `Reset` signal to CPU.
2. Internal registers reset: `PC = 0x00`, `SP = 0xF`.
3. Flags set: **`R = 1`**, `M = 1` (System Mode).
4. Execution begins at ROM address `0x00`.

---

### 6.2. Entry Point Dispatcher (`0x00`)
Both Cold Boot (`Reset`) and Software Interrupts (`SWI`) jump to ROM address `0x00`. The OS kernel inspects the `R` flag to determine execution context.

```asm
; --- ROM Entry Point 0x00 ---
00: 2 (MOV) 0 101   ; MOV A, FL (Read FLAGS register)
02: 7 (AND) 8       ; Mask Bit 3 (R flag: 1000b)
04: B (JZ)  HANDLER ; If R == 0 -> Branch to Syscall Handler
06: 1 (LDI) 0       ; If R == 1 -> Cold Boot: Clear Accumulator
08: 2 (MOV) 1 101   ; MOV FL, A (Clear R flag to 0 for future syscalls)
0A: ...             ; Initialize stack, Zero Page, and launch Shell
```

---

## Appendix A — Full System Call Execution Timeline

**Scenario:** A user program in RAM (`M=0`) invokes OS Function 1 (e.g., Print Character) via system call.

1. **User Setup:** User program writes arguments to Zero Page (`RAM[0x01]`) and executes `SYS 4` (`SWI`) at address `0x25`.
2. **Hardware Transition (`SWI`):**
   * Hardware saves return address (`0x27`) into Shadow PC registers (`SPC_H = 2`, `SPC_L = 7`).
   * Hardware sets mode flag `M = 1` (Kernel Mode).
   * Hardware forces `PC = 0x00`.
3. **Kernel Dispatch (`0x00`):**
   * Kernel checks `FL.R`. Since `R == 0`, it branches to `HANDLER`.
   * Kernel reads arguments from `RAM[0x01]` using `LDR` or `LDRA`.
   * Kernel executes requested driver operation (e.g., writes to `DISP_0` at `0xF0`).
4. **Kernel Return (`SYS 5` / `RETU`):**
   * Kernel executes `SYS 5`.
   * Hardware restores `PC = SPC` (`0x27`).
   * Hardware sets mode flag `M = 0` (User Mode).
5. **User Resume:** User program continues execution seamlessly at `0x27`.