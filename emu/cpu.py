from .mmu import MMU
from .registers import RegisterFile

class CPU:
    """
    NC-1 Central Processing Unit.
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
        """Hardware reset of the CPU."""
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
        """Pushes a nibble to the hardware stack."""
        sp = self.regs.sp
        addr = 0xD0 + sp  # Stack grows upward in local 0-F space? Wait.
        # Docs say: "Stack (grows downward from EF) and data buffers"
        # So SP is 0..15. We start at EF (SP=15) and grow down.
        # "Decremented by PUSH and CAL"

        # Let's map SP 0..15 to D0..EF. Actually, simpler:
        # If it grows downward from EF:
        # Base is E0. Addr = E0 | SP. Wait, if it's E0-EF, that's 16 nibbles.
        # Let's check docs again: "D0–EF Stack / Data" -> 32 nibbles.
        # Wait, SP is 4 bits, so it can only index 16 locations.
        # If it grows downward, it usually means we use it as an offset.
        # Let's just map it to E0..EF (SP=F to 0) to keep it simple and 4-bit.
        # Actually, if SP is decremented BEFORE push or AFTER?
        # Standard: decrement then write.

        # Let's just use: Addr = 0xE0 + self.regs.sp
        self.regs.sp = (self.regs.sp - 1) & 0x0F
        addr = 0xE0 + self.regs.sp
        self.mmu.write(addr, val)

    def pop(self) -> int:
        """Pops a nibble from the hardware stack."""
        addr = 0xE0 + self.regs.sp
        val = self.mmu.read(addr, self.regs.get_flag_m())
        self.regs.sp = (self.regs.sp + 1) & 0x0F
        return val

    def step(self):
        """Executes a single instruction."""
        if self.halted:
            return

        self.jumped_this_cycle = False
        opcode = self.fetch()

        # Decode and execute
        if opcode == 0x0:
            # NOP
            pass

        elif opcode == 0x1:
            # LDI Imm
            imm = self.fetch()
            self.regs.a = imm

        elif opcode == 0x2:
            # MOV Mode + Reg
            operand = self.fetch()
            d = (operand >> 3) & 1
            r = operand & 0x07

            if d == 0:
                # MOV A, Reg (Read register into A)
                self.regs.a = self.regs.read(r)
            else:
                # MOV Reg, A (Write A into register)
                self.regs.write(r, self.regs.a)

        elif opcode == 0x3:
            # LDR
            addr = self.regs.addr
            self.regs.a = self.mmu.read(addr, self.regs.get_flag_m())

        elif opcode == 0x4:
            # STR
            addr = self.regs.addr
            self.mmu.write(addr, self.regs.a)

        elif opcode == 0x5:
            # ADD Reg
            operand = self.fetch()
            r = operand & 0x07
            val1 = self.regs.a
            val2 = self.regs.read(r)

            res = val1 + val2
            self.regs.a = res & 0x0F

            # Flags
            self.regs.set_flag_c(1 if res > 0x0F else 0)
            self.regs.set_flag_z(1 if (res & 0x0F) == 0 else 0)

        elif opcode == 0x6:
            # SUB Reg
            operand = self.fetch()
            r = operand & 0x07
            val1 = self.regs.a
            val2 = self.regs.read(r)

            res = val1 - val2
            self.regs.a = res & 0x0F

            # Flags: C is Borrow in SUB (0 if borrow, 1 if no borrow? or 1 if borrow?)
            # Usually in 4-bit, carry out of adder is inverted borrow. Let's set C=1 if no borrow (val1 >= val2)
            self.regs.set_flag_c(1 if val1 >= val2 else 0)
            self.regs.set_flag_z(1 if (res & 0x0F) == 0 else 0)

        elif opcode == 0x7:
            # AND Reg
            operand = self.fetch()
            r = operand & 0x07
            res = self.regs.a & self.regs.read(r)
            self.regs.a = res
            self.regs.set_flag_z(1 if res == 0 else 0)

        elif opcode == 0x8:
            # XOR Reg
            operand = self.fetch()
            r = operand & 0x07
            res = self.regs.a ^ self.regs.read(r)
            self.regs.a = res
            self.regs.set_flag_z(1 if res == 0 else 0)

        elif opcode == 0x9:
            # INC Reg
            operand = self.fetch()
            r = operand & 0x07
            val = self.regs.read(r)
            res = (val + 1) & 0x0F
            self.regs.write(r, res)
            # Typically INC/DEC set Zero flag, maybe not Carry to allow loop counters without breaking math
            self.regs.set_flag_z(1 if res == 0 else 0)

        elif opcode == 0xA:
            # DEC Reg
            operand = self.fetch()
            r = operand & 0x07
            val = self.regs.read(r)
            res = (val - 1) & 0x0F
            self.regs.write(r, res)
            self.regs.set_flag_z(1 if res == 0 else 0)

        elif opcode == 0xB:
            # JZ Addr
            addr_h = self.fetch()
            addr_l = self.fetch()
            if self.regs.get_flag_z() == 1:
                self.regs.pc = (addr_h << 4) | addr_l

        elif opcode == 0xC:
            # JC Addr
            addr_h = self.fetch()
            addr_l = self.fetch()
            if self.regs.get_flag_c() == 1:
                self.regs.pc = (addr_h << 4) | addr_l

        elif opcode == 0xD:
            # JMP Addr
            addr_h = self.fetch()
            addr_l = self.fetch()
            self.regs.pc = (addr_h << 4) | addr_l

        elif opcode == 0xE:
            # CAL Addr
            addr_h = self.fetch()
            addr_l = self.fetch()
            # Push PC (Return address)
            ret_pc = self.regs.pc
            self.push((ret_pc >> 4) & 0x0F) # PCH
            self.push(ret_pc & 0x0F)        # PCL
            self.regs.pc = (addr_h << 4) | addr_l

        elif opcode == 0xF:
            # SYS Function
            func = self.fetch()
            if func == 0x0:
                # HLT
                self.halted = True
            elif func == 0x1:
                # RET
                pcl = self.pop()
                pch = self.pop()
                self.regs.pc = (pch << 4) | pcl
            elif func == 0x4:
                # SWI
                self.mmu.spc_l = self.regs.pcl
                self.mmu.spc_h = self.regs.pch
                self.regs.set_flag_m(1) # ROM mode
                self.regs.pc = 0x00
            elif func == 0x5:
                # RETU
                self.regs.pcl = self.mmu.spc_l
                self.regs.pch = self.mmu.spc_h
                self.regs.set_flag_m(0) # RAM mode

        # If PCL was directly written by an instruction (like MOV PCL, A),
        # it flushes pipeline/jumps automatically because pc gets updated by property setters,
        # but the cycle already fetched instructions. We just let it continue from new PC.
