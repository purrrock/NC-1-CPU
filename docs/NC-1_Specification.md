# NC-1 MICROPROCESSOR TECHNICAL SPECIFICATION

**Version:** 4.5 (Variable-Length ISA & Refactored Core, added NOP and HLT)  
**Architecture:** 4-bit RISC / Variable-Length Harvard Architecture  
**Date:** 2026  

---

## 1. General Description

The **NC-1** is a 4-bit microprocessor with an 8-bit addressing space, engineered for embedded systems, hardware emulation, and educational computer architecture projects. Version 4.5 refines the frequency-optimized **Variable-Length Instruction Set Architecture (ISA)** to maximize code density in memory-constrained environments. By encoding high-frequency operations (memory accesses, pointer increments, stack pushes/pops, accumulator arithmetic, and register swaps) into single-nibble (4-bit) opcodes and adding short relative branch instructions, NC-1 v4.5 achieves significantly higher execution speed and up to 40% reduction in code size compared to fixed-width 4-bit architectures.

### Key Features
* **Frequency-Optimized Variable-Length ISA:** 1-nibble, 2-nibble, 3-nibble, and 4-nibble instruction encodings optimized based on real-world assembly profiling.
* **Single-Nibble Core Operations:** High-speed 1-nibble opcodes for memory loads/stores (`LDR`, `STR`), hardware pointer operations (`INX`, `DEX`), stack management (`PHA`, `PLA`), accumulator operations (`INC A`, `DEC A`), register transfers (`MOV A,B`, `MOV B,A`), and subroutine returns (`RET`).
* **Compact Relative Branching (`JZR`, `JCR`, `JR`):** 2-nibble conditional and unconditional relative jumps using a signed 4-bit displacement (`-8` to `+7` nibble offset).
* **Extended Instruction Prefix (`EXT` / Opcode `F`):** Dedicated prefix unleashing 2-nibble register arithmetic (`ADD B`, `SUB B`, `AND B`, `XOR B`), 4-nibble pointer loading (`LDP addr8`), 3-nibble general moves (`MOV Reg`), and 4-nibble absolute branching (`JMP`, `CAL`, `JZ`, `JC`).
* **Orthogonal Register File:** Direct register-mapped access to Accumulator (`A`), Auxiliary (`B`), Index High/Low (`X:Y`), Stack Pointer (`SP`), Status Flags (`FL`), and Program Counter (`PCH:PCL`).
* **Dual-Bank Harvard Memory Architecture:** 256 nibbles of System ROM and 256 nibbles of User RAM sharing an 8-bit addressing space.
* **Page-Locked Hardware Stack:** 4-bit physical Stack Pointer (`SP`) mapped to a dedicated 16-nibble RAM page (`0xE0`..`0xEF`) for subroutines and context pushes/pops.
* **Hardware Execution Bank Exchange (`XBNK`):** Toggles instruction fetch between System ROM and User RAM without changing PC trajectory or modifying ALU flags.
* **Hardware Return to Monitor (`BOOT`):** Software reset mechanism instantly restoring CPU context to `ROM[0x00]`.
* **Symmetric Cross-Bank Data Access (`LDRA`):** 2-cycle cross-bank data reading without mode-switching state corruption.
* **Extended Memory-Mapped I/O (MMIO):** Read/Write display registers, 3-bit General Purpose Input (GPI), and 3-bit General Purpose Output (GPO) integration (`0xF0`..`0xFD`).
* **Mass Storage Interface:** Interface mapped to MMIO for persistent data storage.

---

## 2. Hardware Architecture

### 2.1. Buses and Bit Widths
* **Data Bus:** 4-bit (Nibble). Value range: `0..15` (`0x0`..`0xF`).
* **Address Bus:** 8-bit. Addressable space: 256 nibbles per memory bank (512 nibbles total across ROM and RAM).

---

### 2.2. Register Map
The CPU features eight 4-bit registers addressed by a 3-bit register identifier (`000`b..`111`b).

| ID (Bin) | Mnemonic | Purpose | Width | Access & Hardware Behavior |
| :---: | :--- | :--- | :---: | :--- |
| **000** | **A** | Accumulator | 4-bit | Primary 4-bit register for ALU, I/O, and data transfer operations. |
| **001** | **B** | Auxiliary | 4-bit | Secondary 4-bit register used for two-operand ALU instructions and temporary data. |
| **010** | **X** | Index High | 4-bit | High nibble of address pointer for indirect memory access (`X:Y`). |
| **011** | **Y** | Index Low | 4-bit | Low nibble of address pointer for indirect memory access (`X:Y`). |
| **100** | **SP** | Stack Pointer | **4-bit** | Holds the low nibble of the stack address. High nibble is hardware-fixed to `0xE`. |
| **101** | **FL** | Flags | 4-bit | Status and mode control register (`Reserved`, `M`, `C`, `Z`). |
| **110** | **PCH** | PC High | 4-bit | High nibble of Program Counter. |
| **111** | **PCL** | PC Low | 4-bit | **Write:** Triggers an immediate execution branch to `PCH:NewPCL`. |

*Note on PCL:* Writing to `PCL` updates the low nibble of the Program Counter and immediately redirects pipeline fetch to `PCH:NewPCL`. Reading `PCL` returns the low nibble of the current instruction execution address.

---

### 2.3. Flag Register (`FLAGS` / `FL`)
Width: 4 bits. Executing `F0` (`MOV FL, A`) writes all 4 bits of `FL` directly from register `A`.

| Bit 3 (MSB) | Bit 2 | Bit 1 | Bit 0 (LSB) |
| :---: | :---: | :---: | :---: |
| **Reserved** | **M** (Execution Bank) | **C** (Carry) | **Z** (Zero) |

* **Bit 3 (Reserved):** Reserved for future hardware expansion. Reads as `0`; writing to Bit 3 has no effect on control logic.
* **M (Execution Bank):** `1` = System Bank (ROM / Nano-Monitor) active for instruction fetch. `0` = User Bank (RAM) active.
* **C (Carry):** Arithmetic carry/borrow flag.
* **Z (Zero):** Arithmetic zero flag.

---

### 2.4. Flag Update Rules (ALU Flags Behavior)

Status flags **Z** (Zero, Bit 0) and **C** (Carry, Bit 1) in the `FL` register are updated by arithmetic, logic, and pointer instructions. Non-ALU instructions do not alter **Z** and **C** unless `FL` is explicitly written as a destination register.

| Instruction | Operation | Carry Flag (C) Behavior | Zero Flag (Z) Behavior |
| :--- | :--- | :--- | :--- |
| **`INC A`** | `A = A + 1` | `1` on unsigned 4-bit overflow (`0xF` $\rightarrow$ `0x0`), else `0`. | `1` if new `A == 0`, else `0`. |
| **`DEC A`** | `A = A - 1` | `1` on unsigned 4-bit underflow (`0x0` $\rightarrow$ `0xF`), else `0`. | `1` if new `A == 0`, else `0`. |
| **`INX`** | `X:Y = X:Y + 1` | `1` on 16-bit wrap (`0xFF` $\rightarrow$ `0x00`), else `0`. | `1` if new `X:Y == 0x0000`, else `0`. |
| **`DEX`** | `X:Y = X:Y - 1` | `1` on 16-bit wrap (`0x0000` $\rightarrow$ `0x00FF`), else `0`. | `1` if new `X:Y == 0x0000`, else `0`. |
| **`F2 ADD B`** | `A = A + B` | `1` if result $> 15$ (4-bit unsigned overflow), else `0`. | `1` if `(A + B) & 0xF == 0`, else `0`. |
| **`F3 SUB B`** | `A = A - B` | `1` if borrow occurred ($A < B$), else `0`. | `1` if `A == B` (result $= 0$), else `0`. |
| **`F4 AND B`** | `A = A & B` | Always cleared to `0`. | `1` if result $= 0$, else `0`. |
| **`F5 XOR B`** | `A = A ^ B` | Always cleared to `0`. | `1` if result $= 0$, else `0`. |

#### Non-ALU Instruction Flag Preservations:
* **Immediate, Data Transfer & Pointer Loads (`0 LDI`, `1 LDR`, `2 STR`, `A MOV A,B`, `B MOV B,A`, `F0 MOV Reg`, `F1 XCHG`, `F6 LDRA`, `F8 LDP`):** Preserve existing **Z** and **C** flags.
* **Control Flow & Bank Logic (`C JZR`, `D JCR`, `E JR`, `F7 XBNK`, `F9 BOOT`, `FA JZ`, `FB JC`, `FC JMP`, `FD CAL`, `FE Reserved`):** Preserve existing **Z** and **C** flags.
* **Stack Operations (`3 RET`, `4 PHA`, `5 PLA`):** Preserve existing **Z** and **C** flags.
* **Direct Register Write (`F0 MOV FL, A`):** Overwrites all 4 bits of `FL` (`Reserved`, `M`, `C`, `Z`) with the value of register `A`.

---

## 3. Memory Organization & Cross-Bank Architecture

### 3.1. Memory Banks
The CPU addresses a 256-nibble window (`0x00`..`0xFF`), mapped dynamically depending on execution flag **M** and instruction context.

1. **System Bank (ROM):** Active when `M=1`. Contains the Nano-Monitor firmware, system lookup tables, and initialization routines. Read-only for instruction fetch and data reads.
2. **User Bank (RAM):** Active when `M=0`. Contains user code, runtime variables, hardware stack, and MMIO ports. Writable in all execution modes.

---

### 3.2. Memory Access & Shadow Write

* **Write Operations (`STR`, `PHA`, `CAL`):** All memory write operations are unconditionally routed to **RAM** (User Bank) regardless of the state of flag **M** ("Shadow Write"). This allows ROM routines to write data into RAM without toggling execution banks.
* **Stack Space Code Execution (ROM Overlap):** Because all stack-related read and write operations (`PHA`, `PLA`, `CAL`, `RET`) are physically routed to the RAM bank, the corresponding address range in the System Bank (`ROM[0xE0..0xEF]`) is isolated from stack bus conflicts. Executable system code, jump tables, or constants can safely reside in this ROM region while the CPU concurrently manipulates the hardware stack in the identical RAM address window.
* **Read Operations (`LDR` vs `LDRA`):** The target memory bank for data reads is evaluated using hardware XOR logic:
$$\text{Target\_Bank\_Read} = M \oplus \text{Is\_SYS\_6}$$

where `Is_SYS_6` is `1` during execution of `F6` (`LDRA`), and `0` during standard `1` (`LDR`) operations.

#### Memory Read Truth Table:
| Mode (M) | Instruction | Is_SYS_6 | Read Target Bank | Application |
| :---: | :---: | :---: | :---: | :--- |
| `1` (ROM) | `LDR` | `0` | **ROM (`1`)** | Nano-Monitor reads ROM code/constants |
| `1` (ROM) | `LDRA` | `1` | **RAM (`0`)** | Nano-Monitor reads user buffers in RAM |
| `0` (RAM) | `LDR` | `0` | **RAM (`0`)** | User program reads local RAM variables |
| `0` (RAM) | `LDRA` | `1` | **ROM (`1`)** | User program reads OS fonts / math tables in ROM |

---

### 3.3. Memory Map Layout
Unified address space layout across both banks (`0x00`..`0xFF`).

| Address (HEX) | Region | Access Privilege | Description & Usage |
| :---: | :---: | :---: | :--- |
| **`00`** | **Reset Entry** | Hardware | Entry point upon Hardware Reset (`PC=0x00`, `SP=0xF`, `M=1`). |
| **`01` - `DF`** | **Program Space** | User / ROM | Primary program code execution space. |
| **`E0` - `EF`** | **Hardware Stack / ROM Code Space** | Hardware / Stack (RAM) / Read-Only (ROM) | Dedicated 16-nibble Page-Locked Stack space in RAM (`0xE0`..`0xEF`). The identical address range in ROM (`ROM[0xE0..0xEF]`) can safely store executable system code due to independent hardware routing. |
| **`F0` - `FD`** | **MMIO Ports** | Memory-Mapped I/O | Peripheral device control and registers (see Section 5). |
| **`FE` - `FF`** | **Reserved** | Reserved | Unmapped / Reserved addresses. |

---

## 4. Instruction Set Architecture (ISA v4.5)

NC-1 v4.5 implements a variable-length instruction encoding scheme consisting of 1-nibble, 2-nibble, 3-nibble, and 4-nibble instructions.

### 4.1. Primary Opcode Table (`0`..`F`)

| Opcode (Hex) | Mnemonic | Arguments | Size (Nibbles) | Operation Description |
| :---: | :--- | :--- | :---: | :--- |
| **`0`** | `LDI` | `imm4` | 2 | Load Immediate: `A = imm4`. |
| **`1`** | `LDR` | - | 1 | Load Indirect: `A = ActiveBank[X:Y]`. |
| **`2`** | `STR` | - | 1 | Store Indirect: `RAM[X:Y] = A` (Shadow write to RAM). |
| **`3`** | `RET` | - | 1 | Return from Subroutine: `POP PCL`, `POP PCH`. |
| **`4`** | `PHA` | - | 1 | Push Accumulator: `RAM[0xE0\|SP] = A`, `SP = (SP - 1) & 0xF`. |
| **`5`** | `PLA` | - | 1 | Pop Accumulator: `SP = (SP + 1) & 0xF`, `A = RAM[0xE0\|SP]`. |
| **`6`** | `INX` | - | 1 | Increment Index Pair: `X:Y = (X:Y + 1) & 0xFF`. Updates Z & C. |
| **`7`** | `DEX` | - | 1 | Decrement Index Pair: `X:Y = (X:Y - 1) & 0xFF`. Updates Z & C. |
| **`8`** | `INC A` | - | 1 | Increment Accumulator: `A = (A + 1) & 0xF`. Updates Z & C. |
| **`9`** | `DEC A` | - | 1 | Decrement Accumulator: `A = (A - 1) & 0xF`. Updates Z & C. |
| **`A`** | `MOV A, B` | - | 1 | Move Auxiliary to Accumulator: `A = B`. |
| **`B`** | `MOV B, A` | - | 1 | Move Accumulator to Auxiliary: `B = A`. |
| **`C`** | `JZR` | `disp4` | 2 | Relative Jump if `Z==1`: `PC = PC_next + signed(disp4)`. |
| **`D`** | `JCR` | `disp4` | 2 | Relative Jump if `C==1`: `PC = PC_next + signed(disp4)`. |
| **`E`** | `JR` | `disp4` | 2 | Unconditional Relative Jump: `PC = PC_next + signed(disp4)`. |
| **`F`** | `EXT` | `subop` | 2–4 | Extended Instruction Prefix (see Section 4.2). |

---

### 4.2. Extended Instruction Table (`EXT`, Prefix `F`)

Instructions beginning with Opcode `F` decode the second nibble as a subopcode.

| Prefix + Subopcode | Mnemonic | Format Structure | Size (Nibbles) | Operation & Description |
| :---: | :--- | :--- | :---: | :--- |
| **`F0`** | **`MOV Reg`** | `F 0 [D RRR]` | 3 | **Universal Move:** Move between Accumulator `A` and Register `RRR` (`D=0`: `A = Reg`, `D=1`: `Reg = A`). |
| **`F1`** | **`XCHG`** | `F 1` | 2 | **Exchange Registers:** Atomic swap of registers `A` and `B` (`Swap(A, B)`). Does not alter Z or C. |
| **`F2`** | **`ADD B`** | `F 2` | 2 | **Add Auxiliary:** `A = (A + B) & 0xF`. Updates Z and C flags. |
| **`F3`** | **`SUB B`** | `F 3` | 2 | **Subtract Auxiliary:** `A = (A - B) & 0xF`. Updates Z and C flags. |
| **`F4`** | **`AND B`** | `F 4` | 2 | **Bitwise AND Auxiliary:** `A = A & B`. Updates Z flag; clears C flag. |
| **`F5`** | **`XOR B`** | `F 5` | 2 | **Bitwise XOR Auxiliary:** `A = A ^ B`. Updates Z flag; clears C flag. |
| **`F6`** | **`LDRA`** | `F 6` | 2 | **Load Alternate Bank:** `A = AlternateBank[X:Y]` where $\text{Target} = M \oplus 1$. Does not alter M, Z, C. |
| **`F7`** | **`XBNK`** | `F 7` | 2 | **Exchange Execution Bank:** `M = M XOR 1`. Toggles execution bank. Does not alter Z, C, or any register. |
| **`F8`** | **`LDP`** | `F 8 Hi Lo` | 4 | **Load Memory Pointer:** Immediate 8-bit pointer assignment: `X = Hi`, `Y = Lo`. |
| **`F9`** | **`BOOT`** | `F 9` | 2 | **Software Reset:** Restores CPU context to Monitor: `PC = 0x00`, `SP = 0xF`, `M = 1`. |
| **`FA`** | **`JZ`** | `F A Hi Lo` | 4 | **Absolute Jump if Zero:** If `Z == 1`, `PC = Hi:Lo`. |
| **`FB`** | **`JC`** | `F B Hi Lo` | 4 | **Absolute Jump if Carry:** If `C == 1`, `PC = Hi:Lo`. |
| **`FC`** | **`JMP`** | `F C Hi Lo` | 4 | **Absolute Unconditional Jump:** `PC = Hi:Lo`. |
| **`FD`** | **`CAL`** | `F D Hi Lo` | 4 | **Call Subroutine:** `PUSH PCH`, `PUSH PCL`, `PC = Hi:Lo`. |
| **`FE`** | **`Reserved`** | `F E` | 2 | **Reserved:** Reserved for future hardware extension. Not recomended use as `NOP`. |
| **`FF`** | **`HLT`** | `F F` | 2 | **Halt:** Stops CPU clock execution. Prevents invalid execution on uninitialized memory (`0xFF`). |

---

### 4.3. Subroutine Call and Hardware Stack Mechanics

Subroutine control flow in NC-1 uses the **Page-Locked Hardware Stack**. The physical 4-bit Stack Pointer (`SP`, Register ID `100`b) is combined with a hardcoded high nibble `0xE` (`1110`b).

This locks the hardware stack to RAM addresses `0xE0` to `0xEF` (16 nibbles capacity, supporting up to 8 nested `CAL` calls or combined data pushes).

* **Hardware Memory Routing:** All stack operations (`CAL`, `RET`, `PHA`, `PLA`) route strictly to **RAM** regardless of execution mode **M**. This architectural decoupling guarantees that the execution of instructions fetched from `ROM[0xE0..0xEF]` will never collide with hardware stack manipulations.
* **Stack Wrap-around:** `SP` wraps modulo 16 (`0x0 - 1 = 0xF`; `0xF + 1 = 0x0`). Stack overflow/underflow wraps smoothly without hardware exceptions.
* **Stack Reset:** Hardware Reset or `BOOT` sets `SP = 0xF` (initial top of stack = `0xEF`).

#### A. Relative Branching (`JZR`, `JCR`, `JR`)
Relative jump instructions use a 4-bit 2's complement displacement (`disp4`) encoded in the second nibble. The displacement represents a signed integer offset in the range `[-8, +7]`.

* **Relative Address Calculation:**
  $$\text{PC}_{\text{target}} = (\text{PC}_{\text{next}} + \text{signed}(\text{disp4})) \pmod{256}$$
  where $\text{PC}_{\text{next}} = \text{PC}_{\text{current}} + 2$ (the address of the instruction immediately following the 2-nibble branch opcode).

* **Signed 4-Bit Encoding Table (`disp4`):**
  * `0x0` $= 0$, `0x1` $= +1$, `0x2` $= +2$, `0x3` $= +3$, `0x4` $= +4$, `0x5` $= +5$, `0x6` $= +6$, `0x7` $= +7$
  * `0x8` $= -8$, `0x9` $= -7$, `0xA` $= -6$, `0xB` $= -5$, `0xC` $= -4$, `0xD` $= -3$, `0xE` $= -2$, `0xF` $= -1$

#### B. Universal Move (`F0 MOV Reg`)
The `F0` instruction structure is 3 nibbles: `F` `0` `[D RRR]`.
* `D` (Bit 3 of third nibble): Direction bit (`0` = Read register `RRR` into `A`; `1` = Write register `A` into `RRR`).
* `RRR` (Bits 2..0 of third nibble): Register ID (`000`=A, `001`=B, `010`=X, `011`=Y, `100`=SP, `101`=FL, `110`=PCH, `111`=PCL).

*Example:* `F0 2` (`D=0, RRR=010`b) loads `X` into `A`. `F0 A` (`D=1, RRR=010`b) writes `A` into `X`.

#### C. Pointer Load (`F8 LDP addr8`)
The `F8` instruction structure is 3 nibbles: `F` `8` `Hi` `Lo`. It loads an 8-bit immediate memory address directly into the `X:Y` register pair in a single instruction sequence (`X = Hi`, `Y = Lo`).

#### D. Execution Bank Exchange (`F7 XBNK`)
* **Microoperation:** `M = M XOR 1`.
* **Execution Sequence:**
  1. Fetch opcode `F` and subopcode `7` from the current execution bank.
  2. Decode `XBNK`.
  3. Invert execution bank flag **M**.
  4. Advance `PC` by 2 (instruction length).
  5. Fetch the subsequent instruction from the **new memory bank** at the updated `PC`.
* **Register Preservations:** Preserves `PC`, `A`, `B`, `X`, `Y`, `SP`, `Z`, and `C`.

#### E. Software Reset (`F9 BOOT`)
* **Microoperations:** `PC = 0x00`, `SP = 0xF`, `M = 1`.
* Immediately transfers execution to `ROM[0x00]` in System Mode. Preserves flags `Z` and `C`.

#### F. No-Operation (NOP) and Padding
The architecture deliberately omits a dedicated single-byte `NOP` opcode to preserve encoding space. 

* **Recommended NOP:** It is strictly recommended to use the 2-nibble unconditional relative jump **`JR +0` (Opcode `E 0`)** as a standard `NOP` for padding or delay loops.
  * **Microoperation:** `PC = PC + 0`.
  * **Why not `FE`?** Using unmapped/reserved opcodes (like `FE`) as pseudo-NOPs is strongly discouraged to avoid critical instruction collisions with future hardware extensions. `JR +0` is architecturally guaranteed to act as a safe `NOP` with zero side effects on registers, flags, or memory.

---

### 4.4. Subroutine Call and Hardware Stack Mechanics

Subroutine control flow in NC-1 uses the **Page-Locked Hardware Stack**. The physical 4-bit Stack Pointer (`SP`, Register ID `100`b) is combined with a hardcoded high nibble `0xE` (`1110`b).

This locks the hardware stack to RAM addresses `0xE0` to `0xEF` (16 nibbles capacity, supporting up to 8 nested `CAL` calls or combined data pushes).

* **Hardware Memory Routing:** All stack operations (`CAL`, `RET`, `PHA`, `PLA`) route strictly to **RAM** regardless of execution mode **M**.
* **Stack Wrap-around:** `SP` wraps modulo 16 (`0x0 - 1 = 0xF`; `0xF + 1 = 0x0`). Stack overflow/underflow wraps smoothly without hardware exceptions.
* **Stack Reset:** Hardware Reset or `BOOT` sets `SP = 0xF` (initial top of stack = `0xEF`).

#### Subroutine Call (`FD CAL addr8`) — Opcode `FD`
4-nibble instruction (`F D Hi Lo`). Return address: `Next_PC = Current_PC + 4`.

1. Write `PCH` to `RAM[0xE0 | SP]`; `SP = (SP - 1) & 0xF`.
2. Write `PCL` to `RAM[0xE0 | SP]`; `SP = (SP - 1) & 0xF`.
3. `PCH = Hi`; `PCL = Lo` (branches execution to `Hi:Lo`).

#### Subroutine Return (`3 RET`) — Opcode `3`
1-nibble instruction (`3`).

1. `SP = (SP + 1) & 0xF`; `Temp_PCL = RAM[0xE0 | SP]`.
2. `SP = (SP + 1) & 0xF`; `Temp_PCH = RAM[0xE0 | SP]`.
3. `PCH = Temp_PCH`; `PCL = Temp_PCL` (resumes execution at saved return address).

---
## 5. Memory-Mapped I/O Subsystem (MMIO)

Peripherals are mapped to addresses `0xF0`..`0xFD` in RAM space. Display registers `F0`..`F3` and audio/GPO register `F6` support Read/Write (R/W) access.

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
| **`F8`** | **STORAGE_DAT**| R/W | D3 | D2 | D1 | D0 | Synchronous stream data buffer (Auto-incrementing). |
| **`F9`** | **STORAGE_CMD**| R/W | - | - | `MOD`/`EOF`| `MOT`/`RDY`| Mass storage control and status register (See 5.1). |
| **`FA`-`FD`**| **Reserved**| - | - | - | - | - | Peripheral expansion bus. |
| **`FE`-`FF`**| **Reserved**| - | - | - | - | - | Reserved / Unmapped memory addresses. |

### 5.1. Synchronous Mass Storage Protocol
The mass storage subsystem uses ports `0xF8` (Data) and `0xF9` (Command/Status) to provide high-speed, synchronous stream data transfer between the CPU and the storage medium (Emulator File or SPI Flash). Hardware wait-states (Clock Stretching) are handled transparently by the FPGA or emulator, eliminating the need for software handshake loops.

**Port `0xF9` Write (CPU $\rightarrow$ Controller):**
* **Bit 0 (`MOTOR`):** Session Control. `1` = Open session (prompt user or prepare medium). `0` = Close session (flush to disk).
* **Bit 1 (`MODE`):** Data Direction. `1` = Save/Write to medium, `0` = Load/Read from medium.

**Port `0xF9` Read (Controller $\rightarrow$ CPU):**
* **Bit 0 (`READY`):** Drive Ready. `1` = Session is open and ready for stream I/O. `0` = Session closed or aborted.
* **Bit 1 (`EOF`):** End of File. `1` = Reached the end of the file during Load mode.

**Port `0xF8` Read/Write (Stream Data):**
* **Write (`STR`):** Instantly appends the nibble to the open file. Hardware auto-increments the internal pointer.
* **Read (`LDR`):** Instantly fetches the next nibble from the file. Hardware auto-increments the internal pointer.

**Synchronous I/O Sequence:**
1. CPU sets `MOTOR=1` and `MODE=x`. Polls `READY` until it becomes `1`.
2. CPU executes a loop of consecutive `STR` or `LDR` instructions to `0xF8` to stream the data.
3. CPU sets `MOTOR=0` to close the file.

---

## 6. Execution Model (ROM Monitor / User RAM)

NC-1 v4.5 operates under a hardware-controlled **ROM Monitor / User RAM Execution Cycle**.

```text
       Hardware Reset
             │
             ▼
      ROM[0x00] (M=1)
             │
      Nano-Monitor
             │
      XBNK / Trampoline
             │
             ▼
      User RAM (M=0)
             │
      BOOT Instruction (F9)
             │
             └──────────────► ROM[0x00] (M=1)
```			 
Execution Flow:
Hardware Reset Sequence:

Assert Reset signal.

Internal state reset: PC = 0x00, SP = 0xF, M = 1.

Execution starts at ROM[0x00].

Nano-Monitor Execution:

Reads user inputs from keyboard (0xF4 / 0xF5) and writes application nibbles into User RAM space (0x10..0xCF).

ROM → RAM Execution Transfer (Trampoline Pattern):

Nano-Monitor writes a jump instruction into a temporary RAM address (e.g., RAM[0x0E] = FC 1 0 -> JMP 0x10).

Nano-Monitor aligns PC in ROM to execute XBNK (F7).

Upon XBNK execution, M becomes 0. The next instruction is fetched from RAM[0x0E] (JMP 0x10), smoothly launching user execution in RAM.

RAM → ROM Application Return:

When the user program completes, it executes BOOT (F9).

Hardware resets PC = 0x00, SP = 0xF, M = 1, transferring control back to the Nano-Monitor in ROM.

---

## Appendix A — Assembly Code Examples

### A.1. Memory Block Copy Loop in ISA v4.5
Copy a 16-nibble block from ROM (0x80..0x8F) to User RAM (0x20..0x2F) using LDP, LDRA, STR, INX, and JCR:

Code snippet
; NC-1 v4.5 Optimized Block Copy
; Source: ROM 0x80, Destination: RAM 0x20, Counter: 16 nibbles

; 1. Load source pointer X:Y = 0x80 (3 nibbles)
F 8 8 0         ; LDP 0x80 (X=8, Y=0)

; 2. Initialize loop counter in B = 16 (0x0 = 16 modulo 16 wrap check)
0 0             ; LDI 0
B               ; MOV B, A (B = 0)

COPY_LOOP:
F 6             ; LDRA (A = ROM[X:Y] cross-bank read)
2               ; STR  (RAM[X:Y] = A -> Note: Shadow Write targets RAM address X:Y)
                ; Wait: To copy to separate RAM buffer 0x20, set pointer to 0x20:

; Optimized Dual-Pointer Copy using LDP, INX, and Relative Branch:
F 8 8 0         ; LDP 0x80 (X:Y = ROM source)
F 6             ; LDRA (A = ROM[0x80])
F 8 2 0         ; LDP 0x20 (X:Y = RAM destination)
2               ; STR  (RAM[0x20] = A)
6               ; INX  (X:Y = 0x21, updates Z/C)
; ... Loop continues using 2-nibble relative branch JR:
E F 0           ; JR -16 (Jumps relative -16 nibbles back to COPY_LOOP)

### A.2. Subroutine Context Preservation (PHA / PLA / RET)
Code snippet
; Subroutine preserving Accumulator A across computations
MATH_SUBROUTINE:
4               ; PHA (Push A to hardware stack, 1 nibble)
A               ; MOV A, B
8               ; INC A
B               ; MOV B, A
5               ; PLA (Pop A from hardware stack, 1 nibble)
3               ; RET (Return to caller, 1 nibble)

### A.3. Application Entry and Monitor Return (BOOT)
Code snippet
; User Program Entry Point in RAM (0x10)
USER_START:
F 8 F 0         ; LDP 0xF0 (Set pointer to Display 0 MMIO)
0 5             ; LDI 5
2               ; STR (Output 5 to DISP_0)
F 9             ; BOOT (Software Reset back to Nano-Monitor at ROM[0x00])

### A.4. Synchronous Storage I/O (Writing Data)

Thanks to the synchronous stream interface, writing a block of data to storage requires no software handshakes or delays. Wait states are handled transparently by the hardware.

```asm
; NC-1 v4.5 Synchronous Storage Write Example
; Writes nibbles 0x0 through 0xF to the storage drive

ORG 0x00
INIT_STORAGE:
    ; 1. Open File for Writing (MOTOR=1, MODE=1 -> 0b0011 = 3)
    LDP 0xF9     
    LDI 0x3      
    STR          

    ; 2. Wait for READY == 1 (Bit 0)
    LDI 0x1
    MOV B, A     
WAIT_READY:
    LDR
    AND B
    JZR WAIT_READY 

    ; 3. Initialize Loop Counter
    LDI 0x0      
    PHA          

WRITE_LOOP:
    ; 4. Stream Write (Instant Hardware Execution)
    LDP 0xF8     
    PLA          ; A = Current Value
    PHA          ; Save back to stack
    STR          ; Write to Disk (Hardware handles timing transparently)

    ; 5. Increment and loop
    PLA
    INC A
    PHA
    JCR CLOSE_FILE ; If C=1 (wrapped from F to 0), we are done
    JMP WRITE_LOOP

CLOSE_FILE:
    PLA          ; Clean up stack
    
    ; 6. Close file (MOTOR=0)
    LDP 0xF9
    LDI 0x0
    STR
    
HALT_END:
    FF           ; HLT (Opcode 0xFF) - safely halt execution
```