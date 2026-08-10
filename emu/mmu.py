import random

class MMU:
    """
    Memory Management Unit for NC-1 CPU.
    Handles dual-bank memory (ROM and RAM), memory-mapped I/O (MMIO),
    and Shadow Write logic.
    """
    def __init__(self):
        # 256 nibbles per bank
        self.rom = [0] * 256
        self.ram = [0] * 256

        # MMIO State
        self.displays = [0, 0, 0, 0]  # F0 - F3
        self.kbd_stat = 0             # F4
        self.kbd_code = 0             # F5
        self.audio = 0                # F6
        self.spc_l = 0                # FE
        self.spc_h = 0                # FF

        # Random number generator logic
        self.rng_func = lambda: random.randint(0, 15)

    def read(self, address: int, m_flag: int) -> int:
        """
        Reads a nibble from memory or MMIO.
        Active memory bank depends on the M flag:
        1 = System (ROM)
        0 = User (RAM)
        """
        address &= 0xFF

        if address >= 0xF0:
            return self._mmio_read(address)

        if m_flag == 1:
            return self.rom[address]
        else:
            return self.ram[address]

    def write(self, address: int, value: int):
        """
        Writes a nibble to memory or MMIO.
        SHADOW WRITE LOGIC:
        Writes are ALWAYS performed to RAM, regardless of the M flag.
        This allows the OS to load programs into RAM while executing from ROM.
        """
        address &= 0xFF
        value &= 0x0F

        if address >= 0xF0:
            self._mmio_write(address, value)
        else:
            # Shadow write: always to RAM
            self.ram[address] = value

    def _mmio_read(self, address: int) -> int:
        """Handles reading from Memory-Mapped I/O."""
        if address == 0xF4:
            return self.kbd_stat & 0x01
        elif address == 0xF5:
            return self.kbd_code & 0x0F
        elif address == 0xF7:
            return self.rng_func() & 0x0F
        elif address == 0xFE:
            return self.spc_l & 0x0F
        elif address == 0xFF:
            return self.spc_h & 0x0F
        # Other addresses (like displays, audio) might not be explicitly readable in hardware,
        # but returning 0 is safe for undefined behavior.
        return 0

    def _mmio_write(self, address: int, value: int):
        """Handles writing to Memory-Mapped I/O."""
        if 0xF0 <= address <= 0xF3:
            self.displays[address - 0xF0] = value
        elif address == 0xF6:
            self.audio = value & 0x01
        elif address == 0xFE:
            self.spc_l = value
        elif address == 0xFF:
            self.spc_h = value
        # Writes to KBD_STAT, KBD_CODE, RNG are ignored as they are read-only from CPU's perspective.

    def load_rom(self, program: list[int]):
        """Helper to load a program into ROM."""
        for i, val in enumerate(program):
            if i < 256:
                self.rom[i] = val & 0x0F

    def load_ram(self, program: list[int]):
        """Helper to load a program into RAM."""
        for i, val in enumerate(program):
            if i < 256:
                self.ram[i] = val & 0x0F

    def reset(self):
        """Resets MMIO state."""
        self.displays = [0, 0, 0, 0]
        self.kbd_stat = 0
        self.kbd_code = 0
        self.audio = 0
        self.spc_l = 0
        self.spc_h = 0
        # ROM and RAM contents are usually preserved across resets in hardware,
        # but zeroing RAM might be useful. For now, keep them intact like real memory.
