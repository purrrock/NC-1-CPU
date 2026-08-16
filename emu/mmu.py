import random
import time

class StorageDrive:
    """Контроллер потокового накопителя (Synchronous Mass Storage)"""
    def __init__(self):
        self.eof = 0
        self.ready = 0
        self.motor_on = False
        self.file_buffer = bytearray()
        self.filename = None
        
        # Состояние режима (0=Read, 1=Write), зафиксированное при открытии сессии
        self.active_mode = 0 

        # Коллбэки для GUI
        self.on_motor_on_read = None
        self.on_motor_on_write = None

    def write_cmd(self, val):
        val &= 0xF
        motor = val & 0b0001        # Bit 0
        mode = (val & 0b0010) >> 1  # Bit 1

        # Открытие / Закрытие сессии (Мотор)
        if motor == 1 and not self.motor_on:
            self.motor_on = True
            self.active_mode = mode
            
            if self.active_mode == 1:
                # Включили мотор на ЗАПИСЬ
                if self.on_motor_on_write:
                    self.filename = self.on_motor_on_write()
                
                if self.filename:
                    self.file_buffer = bytearray()
                    self.ready = 1 
                    self.eof = 0
                else:
                    self.motor_on = False 
            else:
                # Включили мотор на ЧТЕНИЕ
                if self.on_motor_on_read:
                    self.filename = self.on_motor_on_read()

                if self.filename:
                    with open(self.filename, 'rb') as f:
                        self.file_buffer = bytearray(f.read())
                    self.ready = 1
                    self.eof = 0
                else:
                    self.motor_on = False

        elif motor == 0 and self.motor_on:
            # Остановка и сброс на диск
            self.motor_on = False
            self.ready = 0
            
            if self.active_mode == 1 and self.filename:
                with open(self.filename, 'wb') as f:
                    f.write(self.file_buffer)
            
            # Сброс имени файла должен происходить независимо от режима
            self.filename = None

    def read_cmd(self):
        # Bit 1 = EOF, Bit 0 = READY
        return (self.eof << 1) | self.ready

    def write_data(self, val):
        # Hardware Streaming Write: Мгновенное добавление в буфер
        if self.ready == 1 and self.active_mode == 1:
            self.file_buffer.append(val & 0x0F)

    def read_data(self, is_debug=False):
        # Hardware Streaming Read с защитой от побочных эффектов GUI
        if self.ready == 1 and self.active_mode == 0:
            if len(self.file_buffer) > 0:
                if is_debug:
                    # Безопасное чтение для DataGrid без сдвига указателя
                    return self.file_buffer[0] & 0x0F
                
                val = self.file_buffer.pop(0) & 0x0F
                if len(self.file_buffer) == 0:
                    self.eof = 1
                return val
            else:
                self.eof = 1
                return 0
        return 0


class MMU:
    """
    Memory Management Unit for NC-1 CPU (ISA v4.5).
    Handles dual-bank memory (ROM and RAM), memory-mapped I/O (MMIO),
    and Shadow Write logic.
    """
    def __init__(self):
        self.rom = [0] * 256
        self.ram = [0] * 256

        # MMIO State
        self.displays = [0, 0, 0, 0]  # F0-F3
        self.kbd_stat = 0             # F4
        self.kbd_code = 0             # F5
        self.audio = 0                # F6 (GPO_AUD)
        
        # Hardware Timer State (FA)
        self.timer_value = 0
        self.timer_last_tick = time.time()
        
        # Интеграция накопителя
        self.storage_drive = StorageDrive()

        self.rng_func = lambda: random.randint(0, 15)
        
        # Callbacks для связи аппаратной части с GUI
        self.audio_callback = None
        self.display_callback = None

    def read(self, address: int, m_flag: int, is_debug: bool = False) -> int:
        """
        Reads a nibble from memory or MMIO.
        Active memory bank depends on the M flag:
        1 = System (ROM)
        0 = User (RAM)
        is_debug: Флаг безопасного чтения для GUI (предотвращает побочные эффекты)
        """
        address &= 0xFF
        if address >= 0xF0:
            return self._mmio_read(address, is_debug)
        if m_flag == 1:
            return self.rom[address]
        else:
            return self.ram[address]
 
    def write(self, address: int, value: int):
        address &= 0xFF
        value &= 0x0F

        if address >= 0xF0:
            self._mmio_write(address, value)
        else:
            self.ram[address] = value

    def _mmio_read(self, address: int, is_debug: bool = False) -> int:
        if 0xF0 <= address <= 0xF3:
            return self.displays[address - 0xF0]
        elif address == 0xF4:
            return self.kbd_stat & 0x01
        elif address == 0xF5:
            return self.kbd_code & 0x0F
        elif address == 0xF6:
            return self.audio & 0x0F
        elif address == 0xF7:
            return self.rng_func() & 0x0F
        elif address == 0xF8:
            return self.storage_drive.read_data(is_debug)
        elif address == 0xF9:
            return self.storage_drive.read_cmd()
        elif address == 0xFA:
            # Ленивое вычисление состояния таймера
            if self.timer_value > 0 and not is_debug:
                current_time = time.time()
                elapsed = current_time - self.timer_last_tick
                
                # Таймер отсчитывает 4 такта в секунду (250 мс на квант)
                ticks_passed = int(elapsed / 0.25)
                
                if ticks_passed > 0:
                    self.timer_value -= ticks_passed
                    if self.timer_value < 0:
                        self.timer_value = 0
                    
                    # Сдвигаем метку времени на количество полных прошедших квантов,
                    # сохраняя дробный остаток для предотвращения рассинхронизации (дрейфа таймера)
                    self.timer_last_tick += (ticks_passed * 0.25)
                    
            return self.timer_value & 0x0F
            
        return 0

    def _mmio_write(self, address: int, value: int):
        if 0xF0 <= address <= 0xF3:
            idx = address - 0xF0
            self.displays[idx] = value
            if self.display_callback:
                self.display_callback(idx, value)
        elif address == 0xF6:
            new_audio_state = value & 0x01
            if self.audio_callback and (self.audio & 0x01) != new_audio_state:
                self.audio_callback(new_audio_state)
            self.audio = value
        elif address == 0xF8:
            self.storage_drive.write_data(value)
        elif address == 0xF9:
            self.storage_drive.write_cmd(value)
        elif address == 0xFA:
            # Непосредственная запись переопределяет текущее значение и сбрасывает базу времени
            self.timer_value = value & 0x0F
            self.timer_last_tick = time.time()

    def load_rom(self, program: list[int]):
        if len(program) > 240:
            raise ValueError(f"Program size ({len(program)} nibbles) exceeds available ROM space.")
        for i, val in enumerate(program):
            self.rom[i] = val & 0x0F

    def load_ram(self, program: list[int]):
        if len(program) > 224:
            raise ValueError(f"Program size ({len(program)} nibbles) exceeds available RAM space.")
        for i, val in enumerate(program):
            self.ram[i] = val & 0x0F

    def clear_rom(self):
        self.rom = [0] * 256

    def clear_ram(self):
        self.ram = [0] * 256

    def hardware_inject_key_press(self, scancode: int):
        self.kbd_code = scancode & 0x0F
        self.kbd_stat = 1

    def hardware_inject_key_release(self):
        self.kbd_stat = 0

    def reset(self):
        self.displays = [0, 0, 0, 0]
        self.kbd_stat = 0
        self.kbd_code = 0
        self.audio = 0
        
        # Сброс аппаратного таймера
        self.timer_value = 0
        self.timer_last_tick = time.time()
        
        # Сохраняем коллбэки при сбросе
        read_cb = self.storage_drive.on_motor_on_read
        write_cb = self.storage_drive.on_motor_on_write
        
        self.storage_drive = StorageDrive()
        
        self.storage_drive.on_motor_on_read = read_cb
        self.storage_drive.on_motor_on_write = write_cb