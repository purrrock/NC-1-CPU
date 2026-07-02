# NC-1 CPU

**NC-1** is a minimalist 4-bit RISC microprocessor designed for education, FPGA experiments, digital logic implementation, and emulator development.

The architecture focuses on simplicity, orthogonality, and a very small hardware footprint while remaining expressive enough to support a tiny operating system, user applications, and memory-mapped peripherals.

---

## Highlights

- 4-bit RISC architecture
- 8-bit address space (256 nibbles per bank)
- Modified Harvard architecture
- Separate ROM and RAM memory banks
- Orthogonal register file
- Hardware stack
- Memory-mapped I/O
- System/User execution modes
- Software interrupt support
- Minimal instruction set

---

# Architecture Overview

```
             +----------------------+
             |        NC-1 CPU      |
             +----------------------+
                     |
        +------------+------------+
        |                         |
   System ROM                User RAM
      (OS)                  (Programs)
        |                         |
        +------------+------------+
                     |
                 MMIO Devices
```

The processor always sees a single address space (`0x00–0xFF`).

The currently visible memory bank depends on the **Mode (M)** flag:

- **System Mode** → ROM
- **User Mode** → RAM

Reads are bank-dependent, while writes always target RAM.

---

# CPU Specifications

| Property | Value |
|----------|-------|
| Data width | 4 bits |
| Address width | 8 bits |
| Address space | 256 nibbles |
| Architecture | Modified Harvard |
| Registers | 8 |
| Stack | Hardware |
| Instruction length | 1–3 nibbles |
| ALU width | 4 bits |

---

# Register File

| Register | Description |
|----------|-------------|
| A | Accumulator |
| B | General-purpose register |
| X | Address high nibble |
| Y | Address low nibble |
| SP | Stack Pointer |
| FL | Flags Register |
| PCH | Program Counter High |
| PCL | Program Counter Low |

Unlike many small CPUs, the program counter, stack pointer and flags are directly accessible as ordinary registers.

---

# Flags Register

| Bit | Name | Description |
|-----|------|-------------|
| 3 | R | Reset latch |
| 2 | M | System/User mode |
| 1 | C | Carry |
| 0 | Z | Zero |

---

# Memory Layout

| Address | Purpose |
|----------|---------|
| `00–0F` | Reset vector / Zero page |
| `10–CF` | Program memory |
| `D0–EF` | Stack / Data |
| `F0–FF` | MMIO |

---

# Memory Banking

NC-1 uses two memory banks:

## System Bank (ROM)

Contains:

- Operating System
- Monitor
- Drivers

The ROM is read-only from the CPU perspective.

## User Bank (RAM)

Contains:

- User programs
- Variables
- Stack

### Shadow Write

One distinctive feature of NC-1 is **Shadow Write**:

- **Read** → current memory bank
- **Write** → always RAM

This allows the operating system to load user programs while executing from ROM.

---

# Instruction Set

| Opcode | Instruction |
|---------|-------------|
| 0 | NOP |
| 1 | LDI |
| 2 | MOV |
| 3 | LDR |
| 4 | STR |
| 5 | ADD |
| 6 | SUB |
| 7 | AND |
| 8 | XOR |
| 9 | INC |
| A | DEC |
| B | JZ |
| C | JC |
| D | JMP |
| E | CAL |
| F | SYS |

Instructions occupy from **1 to 3 nibbles**, minimizing code size while preserving functionality.

---

# System Calls

The `SYS` instruction provides privileged operations.

Implemented functions include:

| Code | Function |
|------|----------|
| F0 | HLT |
| F1 | RET |
| F4 | SWI |
| F5 | RETU |

The operating system is entered through a unified entry point at address `0x00`.

---

# Memory-Mapped I/O

| Address | Device |
|----------|--------|
| F0–F3 | Hex Displays |
| F4 | Keyboard Status |
| F5 | Keyboard Code |
| F6 | Speaker |
| F7 | Random Number Generator |
| FE | Shadow PC Low |
| FF | Shadow PC High |

---

# Design Goals

The NC-1 architecture was designed around the following principles:

- extremely small hardware implementation
- easy FPGA implementation
- educational value
- orthogonal instruction set
- simple compiler backend
- operating system support
- deterministic execution

---

# Intended Applications

- CPU architecture education
- FPGA projects
- Digital logic experiments
- Emulator development
- Assembly programming
- Embedded systems research

---

# Documentation

The complete processor specification is available in:

```
docs/NC-1_Technical_Specification.md
```

---

# License

MIT License.
