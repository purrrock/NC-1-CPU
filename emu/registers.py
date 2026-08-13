class RegisterFile:
    """
    Register File for NC-1 CPU (ISA v4.4).
    Contains 8 4-bit registers:
    0: A   (Accumulator)
    1: B   (Auxiliary)
    2: X   (Index High)
    3: Y   (Index Low)
    4: SP  (Stack Pointer)
    5: FL  (Flags: Bit 3 Reserved, Bit 2 M, Bit 1 C, Bit 0 Z)
    6: PCH (PC High)
    7: PCL (PC Low)
    """
    REG_A = 0
    REG_B = 1
    REG_X = 2
    REG_Y = 3
    REG_SP = 4
    REG_FL = 5
    REG_PCH = 6
    REG_PCL = 7

    def __init__(self):
        self.regs = [0] * 8
        self.on_pcl_write = None
        self.reset()

    def reset(self):
        """Resets registers to hardware reset state (PC=0x00, SP=0x0F, M=1)."""
        self.regs = [0] * 8
        self.sp = 0x0F
        self.set_flag_m(1)  # M=1 (System Bank / ROM) on reset

    # --- Individual Register Properties ---
    @property
    def a(self) -> int:
        return self.regs[self.REG_A]

    @a.setter
    def a(self, val: int):
        self.regs[self.REG_A] = val & 0x0F

    @property
    def b(self) -> int:
        return self.regs[self.REG_B]

    @b.setter
    def b(self, val: int):
        self.regs[self.REG_B] = val & 0x0F

    @property
    def x(self) -> int:
        return self.regs[self.REG_X]

    @x.setter
    def x(self, val: int):
        self.regs[self.REG_X] = val & 0x0F

    @property
    def y(self) -> int:
        return self.regs[self.REG_Y]

    @y.setter
    def y(self, val: int):
        self.regs[self.REG_Y] = val & 0x0F

    @property
    def sp(self) -> int:
        return self.regs[self.REG_SP]

    @sp.setter
    def sp(self, val: int):
        self.regs[self.REG_SP] = val & 0x0F

    @property
    def fl(self) -> int:
        return self.regs[self.REG_FL] & 0x0F

    @fl.setter
    def fl(self, val: int):
        self.regs[self.REG_FL] = val & 0x0F

    @property
    def pch(self) -> int:
        return self.regs[self.REG_PCH]

    @pch.setter
    def pch(self, val: int):
        self.regs[self.REG_PCH] = val & 0x0F

    @property
    def pcl(self) -> int:
        return self.regs[self.REG_PCL]

    @pcl.setter
    def pcl(self, val: int):
        self.regs[self.REG_PCL] = val & 0x0F
        if self.on_pcl_write:
            self.on_pcl_write()

    # --- Abstract Combined Properties ---
    @property
    def pc(self) -> int:
        """8-bit Program Counter (PCH:PCL)."""
        return (self.pch << 4) | self.pcl

    @pc.setter
    def pc(self, val: int):
        val &= 0xFF
        self.pch = (val >> 4) & 0x0F
        self.pcl = val & 0x0F

    @property
    def addr(self) -> int:
        """8-bit Memory Address Pointer (X:Y)."""
        return (self.x << 4) | self.y

    @addr.setter
    def addr(self, val: int):
        val &= 0xFF
        self.x = (val >> 4) & 0x0F
        self.y = val & 0x0F

    # --- Flag Helpers ---
    def get_flag_z(self) -> int:
        """Bit 0: Zero Flag."""
        return self.fl & 1

    def set_flag_z(self, val: int | bool):
        if val:
            self.fl |= 0b0001
        else:
            self.fl &= 0b1110

    def get_flag_c(self) -> int:
        """Bit 1: Carry Flag."""
        return (self.fl >> 1) & 1

    def set_flag_c(self, val: int | bool):
        if val:
            self.fl |= 0b0010
        else:
            self.fl &= 0b1101

    def get_flag_m(self) -> int:
        """Bit 2: Execution Bank Flag (1=System/ROM, 0=User/RAM)."""
        return (self.fl >> 2) & 1

    def set_flag_m(self, val: int | bool):
        if val:
            self.fl |= 0b0100
        else:
            self.fl &= 0b1011

    def get_flag_r(self) -> int:
        """Bit 3: Reserved (kept for GUI compatibility)."""
        return (self.fl >> 3) & 1

    def set_flag_r(self, val: int | bool):
        if val:
            self.fl |= 0b1000
        else:
            self.fl &= 0b0111

    # --- Generic Read/Write by 3-bit Register ID ---
    def read(self, reg_id: int) -> int:
        """Reads 4-bit value from register by 3-bit ID (0..7)."""
        reg_id &= 0x07
        if reg_id == self.REG_FL:
            return self.fl & 0x07  # Bit 3 reads as 0
        return self.regs[reg_id] & 0x0F

    def write(self, reg_id: int, val: int):
        """Writes 4-bit value to register by 3-bit ID (0..7)."""
        reg_id &= 0x07
        val &= 0x0F
        if reg_id == self.REG_PCL:
            self.pcl = val  # Triggers on_pcl_write callback
        elif reg_id == self.REG_FL:
            self.fl = val
        else:
            self.regs[reg_id] = val