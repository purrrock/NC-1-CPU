from mmu import MMU
from registers import RegisterFile

class CPU:
    """
    NC-1 Central Processing Unit (v4.4 Variable-Length ISA).
    Combines Register File and MMU. Implements instruction decoding,
    ALU operations, hardware stack, and system calls.
    """
    def __init__(self, mmu: MMU, regs: RegisterFile):
        self.mmu = mmu
        self.regs = regs

        # Connect PCL write callback
        self.regs.on_pcl_write = self._handle_pcl_write

        self.halted = False
        self.jumped_this_cycle = False

    def reset(self):
        """Hardware reset of the CPU. Restores context to ROM[0x00]."""
        self.regs.reset()
        self.mmu.reset()
        self.halted = False
        self.jumped_this_cycle = False

    def _handle_pcl_write(self):
        """Callback for when PCL is written to directly."""
        self.jumped_this_cycle = True

    def fetch(self) -> int:
        """Fetches the next nibble from memory and increments PC."""
        pc = self.regs.pc
        val = self.mmu.read(pc, self.regs.get_flag_m())
        self.regs.pc = (pc + 1) & 0xFF
        return val

    def push(self, val: int):
        """Pushes a nibble to the hardware stack (Page-Locked 0xE0-0xEF)."""
        addr = 0xE0 | self.regs.sp
        self.mmu.write(addr, val)
        self.regs.sp = (self.regs.sp - 1) & 0x0F

    def pop(self) -> int:
        """Pops a nibble from the hardware stack."""
        self.regs.sp = (self.regs.sp + 1) & 0x0F
        addr = 0xE0 | self.regs.sp
        # Hardware constraint: stack is always in RAM (bank 0)
        return self.mmu.read(addr, 0)
        
    def _calc_relative_branch(self, disp4: int):
        """Calculates signed 4-bit relative branch."""
        # Convert 4-bit unsigned to signed [-8, +7]
        if disp4 >= 8:
            disp4 -= 16
        # The offset is applied to the NEXT instruction's PC (already incremented by fetch)
        self.regs.pc = (self.regs.pc + disp4) & 0xFF

    def step(self):
        """Executes a single variable-length instruction."""
        if self.halted:
            return

        self.jumped_this_cycle = False
        opcode = self.fetch()

        # --- Base Instructions (Opcodes 0..E) ---
        if opcode == 0x0:
            # LDI imm4 (2 nibbles)
            imm = self.fetch()
            self.regs.a = imm

        elif opcode == 0x1:
            # LDR (1 nibble)
            addr = self.regs.addr
            self.regs.a = self.mmu.read(addr, self.regs.get_flag_m())

        elif opcode == 0x2:
            # STR (1 nibble)
            addr = self.regs.addr
            self.mmu.write(addr, self.regs.a)

        elif opcode == 0x3:
            # RET (1 nibble)
            pcl = self.pop()
            pch = self.pop()
            self.regs.pc = (pch << 4) | pcl

        elif opcode == 0x4:
            # PHA (1 nibble)
            self.push(self.regs.a)

        elif opcode == 0x5:
            # PLA (1 nibble)
            self.regs.a = self.pop()

        elif opcode == 0x6:
            # INX (1 nibble) - 16-bit increment
            val = self.regs.addr
            res = (val + 1) & 0xFF
            self.regs.addr = res
            self.regs.set_flag_c(1 if val == 0xFF else 0)
            self.regs.set_flag_z(1 if res == 0 else 0)

        elif opcode == 0x7:
            # DEX (1 nibble) - 16-bit decrement
            val = self.regs.addr
            res = (val - 1) & 0xFF
            self.regs.addr = res
            self.regs.set_flag_c(1 if val == 0x00 else 0) # Underflow generates Carry
            self.regs.set_flag_z(1 if res == 0 else 0)

        elif opcode == 0x8:
            # INC A (1 nibble)
            val = self.regs.a
            res = (val + 1) & 0x0F
            self.regs.a = res
            self.regs.set_flag_c(1 if val == 0x0F else 0)
            self.regs.set_flag_z(1 if res == 0 else 0)

        elif opcode == 0x9:
            # DEC A (1 nibble)
            val = self.regs.a
            res = (val - 1) & 0x0F
            self.regs.a = res
            self.regs.set_flag_c(1 if val == 0x00 else 0)
            self.regs.set_flag_z(1 if res == 0 else 0)

        elif opcode == 0xA:
            # MOV A, B (1 nibble)
            self.regs.a = self.regs.b

        elif opcode == 0xB:
            # MOV B, A (1 nibble)
            self.regs.b = self.regs.a

        elif opcode == 0xC:
            # JZR disp4 (2 nibbles)
            disp4 = self.fetch()
            if self.regs.get_flag_z() == 1:
                self._calc_relative_branch(disp4)

        elif opcode == 0xD:
            # JCR disp4 (2 nibbles)
            disp4 = self.fetch()
            if self.regs.get_flag_c() == 1:
                self._calc_relative_branch(disp4)

        elif opcode == 0xE:
            # JR disp4 (2 nibbles)
            disp4 = self.fetch()
            self._calc_relative_branch(disp4)

        # --- Extended Instructions (Prefix F) ---
        elif opcode == 0xF:
            subop = self.fetch()

            if subop == 0x0:
                # F0 MOV Reg [D RRR] (3 nibbles)
                operand = self.fetch()
                d = (operand >> 3) & 1
                r = operand & 0x07
                if d == 0:
                    self.regs.a = self.regs.read(r)
                else:
                    self.regs.write(r, self.regs.a)

            elif subop == 0x1:
                # F1 XCHG (2 nibbles)
                temp = self.regs.a
                self.regs.a = self.regs.b
                self.regs.b = temp

            elif subop == 0x2:
                # F2 ADD B (2 nibbles)
                res = self.regs.a + self.regs.b
                self.regs.a = res & 0x0F
                self.regs.set_flag_c(1 if res > 0x0F else 0)
                self.regs.set_flag_z(1 if (res & 0x0F) == 0 else 0)

            elif subop == 0x3:
                # F3 SUB B (2 nibbles)
                val1 = self.regs.a
                val2 = self.regs.b
                res = val1 - val2
                self.regs.a = res & 0x0F
                self.regs.set_flag_c(1 if val1 >= val2 else 0) # Borrow logic
                self.regs.set_flag_z(1 if (res & 0x0F) == 0 else 0)

            elif subop == 0x4:
                # F4 AND B (2 nibbles)
                res = self.regs.a & self.regs.b
                self.regs.a = res
                self.regs.set_flag_c(0)
                self.regs.set_flag_z(1 if res == 0 else 0)

            elif subop == 0x5:
                # F5 XOR B (2 nibbles)
                res = self.regs.a ^ self.regs.b
                self.regs.a = res
                self.regs.set_flag_c(0)
                self.regs.set_flag_z(1 if res == 0 else 0)

            elif subop == 0x6:
                # F6 LDRA (2 nibbles)
                alt_m = self.regs.get_flag_m() ^ 1
                addr = self.regs.addr
                self.regs.a = self.mmu.read(addr, alt_m)

            elif subop == 0x7:
                # F7 XBNK (2 nibbles)
                current_m = self.regs.get_flag_m()
                self.regs.set_flag_m(current_m ^ 1)

            elif subop == 0x8:
                # F8 LDP Hi Lo (3 nibbles)
                addr_h = self.fetch()
                addr_l = self.fetch()
                self.regs.x = addr_h
                self.regs.y = addr_l

            elif subop == 0x9:
                # F9 BOOT (2 nibbles)
                self.regs.pc = 0x00
                self.regs.sp = 0x0F
                self.regs.set_flag_m(1)

            elif subop == 0xA:
                # FA JZ Hi Lo (4 nibbles)
                addr_h = self.fetch()
                addr_l = self.fetch()
                if self.regs.get_flag_z() == 1:
                    self.regs.pc = (addr_h << 4) | addr_l

            elif subop == 0xB:
                # FB JC Hi Lo (4 nibbles)
                addr_h = self.fetch()
                addr_l = self.fetch()
                if self.regs.get_flag_c() == 1:
                    self.regs.pc = (addr_h << 4) | addr_l

            elif subop == 0xC:
                # FC JMP Hi Lo (4 nibbles)
                addr_h = self.fetch()
                addr_l = self.fetch()
                self.regs.pc = (addr_h << 4) | addr_l

            elif subop == 0xD:
                # FD CAL Hi Lo (4 nibbles)
                addr_h = self.fetch()
                addr_l = self.fetch()
                ret_pc = self.regs.pc
                self.push((ret_pc >> 4) & 0x0F) # Push PCH
                self.push(ret_pc & 0x0F)        # Push PCL
                self.regs.pc = (addr_h << 4) | addr_l

            elif subop == 0xE or subop == 0xF:
                # Reserved -> Acts as NOP (2 nibbles)
                pass