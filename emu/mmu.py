import random

class TapeDrive:
    """Контроллер ленточного накопителя (Mass Storage Interface)"""
    def __init__(self):
        self.data_reg = 0
        self.cmd_reg = 0
        self.ack = 0
        self.eof = 0
        self.ready = 0
        self.motor_on = False
        self.file_buffer = bytearray()
        self.filename = None

        # Коллбэки для GUI (чтобы mmu не зависел от PyQt6 напрямую)
        self.on_motor_on_read = None
        self.on_motor_on_write = None

    def write_cmd(self, val):
        self.cmd_reg = val & 0xF
        strb = self.cmd_reg & 0b0001
        mode = (self.cmd_reg & 0b0010) >> 1
        motor = (self.cmd_reg & 0b0100) >> 2

        # 1. ОБРАБОТКА МОТОРА (Открытие / Закрытие файла)
        if motor == 1 and not self.motor_on:
            self.motor_on = True
            if mode == 1:
                # Включили мотор на ЗАПИСЬ
                if self.on_motor_on_write:
                    self.filename = self.on_motor_on_write()
                
                if self.filename:
                    self.file_buffer = bytearray()
                    self.ready = 1 # Магнитофон готов к приему данных
                else:
                    self.motor_on = False # Отмена выбора файла
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
                    self.motor_on = False # Отмена выбора файла

        elif motor == 0 and self.motor_on:
            # ВЫКЛЮЧИЛИ МОТОР (Остановка и сохранение)
            self.motor_on = False
            self.ready = 0
            if mode == 1 and self.filename:
                # Сбрасываем буфер на диск
                with open(self.filename, 'wb') as f:
                    f.write(self.file_buffer)
                self.filename = None

        # 2. ОБРАБОТКА ДАННЫХ (Handshake) только если мотор включен
        if self.ready == 1:
            if strb == 1 and self.ack == 0:
                if mode == 1:
                    # Сохраняем ниббл в буфер
                    self.file_buffer.append(self.data_reg & 0x0F)
                else:
                    # Читаем ниббл из буфера (если не конец файла)
                    if len(self.file_buffer) > 0:
                        self.data_reg = self.file_buffer.pop(0) & 0x0F
                    else:
                        self.eof = 1
                self.ack = 1 # Сигнал процессору: операция выполнена
                
            elif strb == 0 and self.ack == 1:
                self.ack = 0 # Сброс ACK вслед за сбросом STRB

    def read_cmd(self):
        # Формируем байт статуса для CPU
        return (self.ready << 2) | (self.eof << 1) | self.ack


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
        
        # Интеграция ленточного накопителя
        self.tape_drive = TapeDrive()

        self.rng_func = lambda: random.randint(0, 15)
        
        # Callbacks для связи аппаратной части с GUI
        self.audio_callback = None
        self.display_callback = None

    def read(self, address: int, bank_flag: int) -> int:
        address &= 0xFF

        if address >= 0xF0:
            return self._mmio_read(address)

        if bank_flag == 1:
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

    def _mmio_read(self, address: int) -> int:
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
            return self.tape_drive.data_reg
        elif address == 0xF9:
            return self.tape_drive.read_cmd()
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
            self.tape_drive.data_reg = value
        elif address == 0xF9:
            self.tape_drive.write_cmd(value)

    def load_rom(self, program: list[int]):
        if len(program) > 240:
            raise ValueError(f"Program size ({len(program)} nibbles) exceeds available ROM space (max 240 nibbles before MMIO space).")
        for i, val in enumerate(program):
            self.rom[i] = val & 0x0F

    def load_ram(self, program: list[int]):
        if len(program) > 224:
            raise ValueError(f"Program size ({len(program)} nibbles) exceeds available RAM space (max 224 nibbles before Stack/MMIO space).")
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
        self.tape_drive = TapeDrive() # Сброс состояния накопителя