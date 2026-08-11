class RegisterFile:
    """
    Register File for NC-1 CPU.
    Contains 8 orthogonal registers. Handles specific behaviors like
    flags mapping and JUMP-on-PCL-write logic.
    """
    def __init__(self):
        # 8 registers, 4 bits each
        self.regs = [0] * 8

        # ID Constants
        self.REG_A = 0
        self.REG_B = 1
        self.REG_X = 2
        self.REG_Y = 3
        self.REG_SP = 4
        self.REG_FL = 5
        self.REG_PCH = 6
        self.REG_PCL = 7

        # Callback for when PCL is written to (to flush pipeline/jump)
        self.on_pcl_write = None

    def read(self, reg_id: int) -> int:
        """Reads a nibble from a register."""
        reg_id &= 0x07
        return self.regs[reg_id]

    def write(self, reg_id: int, value: int):
        """
        Writes a nibble to a register.
        Handles JUMP-on-PCL-write logic.
        """
        reg_id &= 0x07
        value &= 0x0F

        self.regs[reg_id] = value

        # JUMP-on-PCL-write:
        # When PCL is updated by a register write (e.g., MOV PCL, A),
        # it causes an immediate jump to PCH:NewPCL.
        # The CPU needs to know this happened to adjust its instruction flow.
        if reg_id == self.REG_PCL and self.on_pcl_write is not None:
            self.on_pcl_write()

    # --- Properties for easy access by CPU ---

    @property
    def a(self): return self.regs[self.REG_A]
    @a.setter
    def a(self, val): self.regs[self.REG_A] = val & 0x0F

    @property
    def b(self): return self.regs[self.REG_B]
    @b.setter
    def b(self, val): self.regs[self.REG_B] = val & 0x0F

    @property
    def x(self): return self.regs[self.REG_X]
    @x.setter
    def x(self, val): self.regs[self.REG_X] = val & 0x0F

    @property
    def y(self): return self.regs[self.REG_Y]
    @y.setter
    def y(self, val): self.regs[self.REG_Y] = val & 0x0F

    @property
    def sp(self): return self.regs[self.REG_SP]
    @sp.setter
    def sp(self, val): self.regs[self.REG_SP] = val & 0x0F

    @property
    def pch(self): return self.regs[self.REG_PCH]
    @pch.setter
    def pch(self, val): self.regs[self.REG_PCH] = val & 0x0F

    @property
    def pcl(self): return self.regs[self.REG_PCL]
    @pcl.setter
    def pcl(self, val):
        self.regs[self.REG_PCL] = val & 0x0F
        # Note: Direct assignment to property does NOT trigger on_pcl_write.
        # This is used by CPU for normal PC incrementing.
        # on_pcl_write is only for EXPLICIT writes via write() method (instructions).

    # PC abstraction (8-bit)
    @property
    def pc(self):
        return (self.pch << 4) | self.pcl
    @pc.setter
    def pc(self, val):
        val &= 0xFF
        self.pch = (val >> 4) & 0x0F
        self.pcl = val & 0x0F

    # Address abstraction (X:Y)
    @property
    def addr(self):
        return (self.x << 4) | self.y

    # --- Flags Abstraction ---
    # Bit 3: R (Reset), Bit 2: M (Mode), Bit 1: C (Carry), Bit 0: Z (Zero)

    @property
    def fl(self): return self.regs[self.REG_FL]
    @fl.setter
    def fl(self, val): self.regs[self.REG_FL] = val & 0x0F

    def get_flag_r(self): return (self.fl >> 3) & 1
    def set_flag_r(self, val):
        if val: self.fl |= 0b1000
        else:   self.fl &= 0b0111

    def get_flag_m(self): return (self.fl >> 2) & 1
    def set_flag_m(self, val):
        if val: self.fl |= 0b0100
        else:   self.fl &= 0b1011

    def get_flag_c(self): return (self.fl >> 1) & 1
    def set_flag_c(self, val):
        if val: self.fl |= 0b0010
        else:   self.fl &= 0b1101

    def get_flag_z(self): return self.fl & 1
    def set_flag_z(self, val):
        if val: self.fl |= 0b0001
        else:   self.fl &= 0b1110

    def reset(self):
        """Hardware reset initialization."""
        self.pc = 0x00
        self.sp = 0x0F
        # FL: R=1, M=1, C=0, Z=0 -> 1100b = 0xC
        self.fl = 0xC
