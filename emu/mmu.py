import random

class MMU:
    """
    Memory Management Unit for NC-1 CPU.
    Handles dual-bank memory (ROM and RAM), memory-mapped I/O (MMIO),
    and Shadow Write logic.
    """
    def __init__(self):
        self.rom = [0] * 256
        self.ram = [0] * 256

        # MMIO State
        self.displays = [0, 0, 0, 0]
        self.kbd_stat = 0
        self.kbd_code = 0
        self.audio = 0
        self.spc_l = 0
        self.spc_h = 0

        self.rng_func = lambda: random.randint(0, 15)
        
        # Callbacks для связи аппаратной части с GUI
        self.audio_callback = None
        self.display_callback = None

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
            idx = address - 0xF0
            self.displays[idx] = value
            if self.display_callback:
                self.display_callback(idx, value)
                
        elif address == 0xF6:
            new_audio_state = value & 0x01
            # Вызываем callback только при фактическом изменении состояния
            if self.audio_callback and self.audio != new_audio_state:
                self.audio_callback(new_audio_state)
            self.audio = new_audio_state
            
        elif address == 0xFE:
            self.spc_l = value
        elif address == 0xFF:
            self.spc_h = value

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
    def hardware_inject_key_press(self, scancode: int):
        """Имитация аппаратного прерывания от контроллера клавиатуры (Key Pressed)"""
        self.kbd_code = scancode & 0x0F
        self.kbd_stat = 1

    def hardware_inject_key_release(self):
        """Имитация снятия сигнала удержания клавиши (Key Released)"""
        self.kbd_stat = 0
        
    def clear_rom(self):
        """Fills ROM bank with zeros."""
        self.rom = [0] * 256

    def clear_ram(self):
        """Fills RAM bank with zeros."""
        self.ram = [0] * 256