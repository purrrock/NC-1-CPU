# NC-1 Microprocessor Technical Specification

**Version:** 4.0 (Final Release)  
**Architecture:** 4-bit RISC / Modified Harvard

---

# 1. General Description

The **NC-1** is a 4-bit microprocessor with an 8-bit address space, designed for embedded systems and educational purposes. The architecture is optimized to minimize logic gate count while maintaining programming flexibility.

## Key Features

- **Orthogonal Register File:** Direct access to the Program Counter (PC), Stack Pointer (SP), and Flags as ordinary registers.
- **Dual-Bank Memory:** Separation of System (ROM) and User (RAM) memory with hardware protection.
- **Unified Entry Vector:** Simplified reset and interrupt handling through a status flag.
- **Hardware Stack:** Supports nested subroutine calls.

---

# 2. Hardware Architecture

## 2.1 Buses and Data Width

- **Data Bus:** 4 bits (Nibble)
  - Value range: `0...15` (`0x0...0xF`)
- **Address Bus:** 8 bits
  - Address space: 256 nibbles per memory bank

---

## 2.2 Register Map

The processor contains eight registers addressed by a 3-bit identifier (`000...111`).

| ID (Bin) | Mnemonic | Description | Access Notes |
|----------|-----------|-------------|--------------|
| 000 | A | Accumulator | Primary register for ALU and I/O operations |
| 001 | B | Auxiliary / General Purpose | General-purpose register |
| 010 | X | Index High | High nibble of indirect address |
| 011 | Y | Index Low | Low nibble of indirect address |
| 100 | SP | Stack Pointer | Decremented by `PUSH` and `CAL` |
| 101 | FL | Flags | Flags register (see Section 2.3) |
| 110 | PCH | PC High | High nibble of Program Counter |
| 111 | PCL | PC Low | Writing causes an immediate jump to `PCH:NewPCL` |

**Note:** Writing to `PCL` updates the low address nibble and immediately flushes the instruction pipeline (jump). Reading `PCL` returns the current address plus the instruction fetch offset.

---

## 2.3 Flags Register (FLAGS)

Width: **4 bits**

| Bit 3 (MSB) | Bit 2 | Bit 1 | Bit 0 (LSB) |
|-------------|--------|--------|-------------|
| R (Reset) | M (Mode) | C (Carry) | Z (Zero) |

### Flag Definitions

- **R (Reset Latch)**
  - Set to `1` by hardware after power-on or reset.
  - Cleared only by software (writing `0`).
  - Used to distinguish between a cold boot and a system call.

- **M (System Mode)**
  - `1` = ROM bank active (Operating System)
  - `0` = RAM bank active (User program)

- **C (Carry)**
  - Carry/Borrow flag.

- **Z (Zero)**
  - Set when the ALU result equals zero.

---

# 3. Memory Model

## 3.1 Memory Banks

The processor always sees a single address window (`00...FF`). The active bank depends on the **M** flag.

### System Bank (ROM)

- Active when `M = 1`
- Contains:
  - Operating System
  - Monitor
  - Drivers
- Read-only for the CPU (except MMIO)

### User Bank (RAM)

- Active when `M = 0`
- Stores user code and data.

---

## 3.2 Memory Access Logic (Shadow Write)

### Read (`LDR`)

Reads from the currently selected bank according to the **M** flag.

### Write (`STR`)

Writes are **always performed to RAM**, regardless of the current mode.

This allows the operating system to load user programs while executing from ROM.

---

## 3.3 Memory Map

The same address map applies to both memory banks.

| Address | Region | Description |
|----------|---------|-------------|
| `00–0F` | Vectors / Zero Page | `00`: Unified entry point (Reset & System Call) |
| `10–CF` | Program Space | Main program area (192 nibbles) |
| `D0–EF` | Stack / Data | Stack (grows downward from `EF`) and data buffers |
| `F0–FF` | MMIO Ports | Memory-mapped I/O (see Section 5) |

---

# 4. Instruction Set Architecture (ISA)

All instructions have variable length:

- 1 nibble
- 2 nibbles
- 3 nibbles

## Opcode Table

| Op | Mnemonic | Arguments | Size | Operation |
|----|-----------|-----------|------|-----------|
| 0 | NOP | — | 1 | No operation |
| 1 | LDI | Imm (4-bit) | 2 | `A = Imm` |
| 2 | MOV | Mode + Reg | 2 | Register transfer |
| 3 | LDR | — | 1 | `A = Memory[X:Y]` |
| 4 | STR | — | 1 | `Memory[X:Y] = A` |
| 5 | ADD | Reg | 2 | `A = A + Reg` |
| 6 | SUB | Reg | 2 | `A = A - Reg` |
| 7 | AND | Reg | 2 | `A = A & Reg` |
| 8 | XOR | Reg | 2 | `A = A ^ Reg` |
| 9 | INC | Reg | 2 | `Reg = Reg + 1` |
| A | DEC | Reg | 2 | `Reg = Reg - 1` |
| B | JZ | Addr (8-bit) | 3 | If `Z = 1`, `PC = Addr` |
| C | JC | Addr (8-bit) | 3 | If `C = 1`, `PC = Addr` |
| D | JMP | Addr (8-bit) | 3 | Unconditional jump |
| E | CAL | Addr (8-bit) | 3 | `PUSH PCH`, `PUSH PCL`, `PC = Addr` |
| F | SYS | Function | 2 | System functions |

---

## 4.1 MOV Instruction Format

The second nibble has the following layout:

```
D R R R
```

### D — Direction

- `0` → `MOV A, Reg` (Read register into A)
- `1` → `MOV Reg, A` (Write A into register)

### RRR

Register ID (`0...7`)

---

## 4.2 System Functions (`SYS`)

| Opcode | Function | Description |
|---------|----------|-------------|
| F0 | HLT | Halt processor until reset |
| F1 | RET | Return from subroutine (`POP PCL`, `POP PCH`) |
| F4 | SWI | System Call |
| F5 | RETU | Return to User mode |

### SWI (F4)

Operation:

- `SPC = PC`
- `M = 1`
- `PC = 0`

Execution continues from the ROM entry point.

### RETU (F5)

Operation:

- `PC = SPC`
- `M = 0`

Returns execution to the user program.

---

# 5. Memory-Mapped I/O (MMIO)

Devices are mapped to addresses `F0...FF`.

Writes always succeed. Reads depend on device state.

| Address | Name | R/W | Description |
|----------|------|-----|-------------|
| F0 | DISP_0 | W | Right hexadecimal display |
| F1 | DISP_1 | W | Display |
| F2 | DISP_2 | W | Display |
| F3 | DISP_3 | W | Left hexadecimal display |
| F4 | KBD_STAT | R | Bit 0: `1 = Key Pressed`, `0 = Released` |
| F5 | KBD_CODE | R | Key code (`0...F`) |
| F6 | AUDIO | W | Bit 0: Speaker (`1 = On`, `0 = Off`) |
| F7 | RNG | R | Random number generator |
| FE | SPC_L | R/W | Shadow PC Low (OS debugging) |
| FF | SPC_H | R/W | Shadow PC High |

---

# 6. Reset and Initialization Logic

## Hardware Reset

When the CPU Reset signal is asserted:

1. Registers are initialized:
   - `PC = 00`
   - `SP = 00`
2. Flags are initialized:
   - `R = 1`
   - `M = 1` (System Mode)
3. Execution begins at ROM address `00`.

---

## Entry Point (`0x00`)

Example ROM dispatcher:

```asm
00: MOV A, FL        ; Read flags
02: AND 8            ; Test R bit (1000b)
04: JZ HANDLER       ; R=0 -> System Call
06: ...              ; R=1 -> Cold Boot initialization
```

---

# Appendix A — Example System Call Flow

**Task:** A user program calls an operating system function.

1. User program loads arguments into registers and/or memory.
2. User program executes:

   ```
   SYS 4    ; SWI
   ```

   CPU actions:

   - Save return address in `SPC`
   - Enable ROM (`M = 1`)
   - Jump to address `00`

3. Operating System (address `00`)
   - Checks flag `R`
   - Since `R = 0`, branches to `HANDLER`

4. Handler performs the requested service.

5. Operating System executes:

   ```
   SYS 5    ; RETU
   ```

   CPU actions:

   - Restore `PC` from `SPC`
   - Enable RAM (`M = 0`)

6. User program resumes execution.
