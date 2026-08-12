from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QGroupBox,
                             QLabel, QPushButton, QTabWidget, QTableWidget,
                             QTableWidgetItem, QHeaderView, QGridLayout)
from PyQt6.QtGui import QFontDatabase, QFont
from PyQt6.QtCore import Qt

class HardwarePanel(QWidget):
    def __init__(self, cpu, update_callback):
        super().__init__()
        self.cpu = cpu
        self.update_callback = update_callback
        self.reg_labels = {}
        self.flag_leds = {}
        self.mmio_labels = []
        self.keys = {}
        
        # Маппинг клавиш физической клавиатуры на Hex-значения (0-F)
        self.key_map = {
            Qt.Key.Key_0: 0x0, Qt.Key.Key_1: 0x1, Qt.Key.Key_2: 0x2, Qt.Key.Key_3: 0x3,
            Qt.Key.Key_4: 0x4, Qt.Key.Key_5: 0x5, Qt.Key.Key_6: 0x6, Qt.Key.Key_7: 0x7,
            Qt.Key.Key_8: 0x8, Qt.Key.Key_9: 0x9, Qt.Key.Key_A: 0xA, Qt.Key.Key_B: 0xB,
            Qt.Key.Key_C: 0xC, Qt.Key.Key_D: 0xD, Qt.Key.Key_E: 0xE, Qt.Key.Key_F: 0xF
        }
        
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Верхний ряд: Слева (Регистры + Флаги), Справа (Клавиатура)
        top_hw_layout = QHBoxLayout()
        top_hw_layout.setSpacing(6)

        # Левый блок: Регистры сверху, Флаги снизу
        left_top_vbox = QVBoxLayout()
        left_top_vbox.setContentsMargins(0, 0, 0, 0)
        left_top_vbox.setSpacing(4)

        reg_group = QGroupBox("Registers (Hex)")
        reg_layout = QGridLayout(reg_group)
        reg_layout.setContentsMargins(6, 6, 6, 6)
        reg_layout.setSpacing(4)
        
        reg_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        reg_font.setPointSize(13)
        
        reg_positions = [
            ("A",   0, 0), ("B",   0, 2), ("SP", 0, 4), ("FL", 0, 6),
            ("X",   1, 0), ("Y",   1, 2), ("XY", 1, 4),
            ("PCH", 2, 0), ("PCL", 2, 2), ("PC", 2, 4)
        ]

        for reg, row, col in reg_positions:
            lbl_name = QLabel(f"{reg}:")
            lbl_val = QLabel("0")
            lbl_val.setFont(reg_font)
            lbl_val.setStyleSheet("color: red; background-color: black; font-weight: bold; padding: 1px 3px;")
            lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_val.setMinimumWidth(32)
            reg_layout.addWidget(lbl_name, row, col, alignment=Qt.AlignmentFlag.AlignRight)
            reg_layout.addWidget(lbl_val, row, col + 1)
            self.reg_labels[reg] = lbl_val

        # Индикатор AUDIO (F6) в регистровой панели
        lbl_audio = QLabel("AUDIO:")
        self.audio_led = QLabel()
        self.audio_led.setFixedSize(12, 12)
        self.audio_led.setStyleSheet("background-color: gray; border-radius: 6px;")
        reg_layout.addWidget(lbl_audio, 1, 6, alignment=Qt.AlignmentFlag.AlignRight)
        reg_layout.addWidget(self.audio_led, 1, 7, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        left_top_vbox.addWidget(reg_group)

        # Флаги ПОД регистрами
        flags_group = QGroupBox("Flags")
        flags_layout = QHBoxLayout(flags_group)
        flags_layout.setContentsMargins(6, 4, 6, 4)
        for flag in ["R", "M", "C", "Z"]:
            flag_vbox = QVBoxLayout()
            lbl_name = QLabel(flag)
            lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            led = QLabel()
            led.setFixedSize(14, 14)
            led.setStyleSheet("background-color: gray; border-radius: 7px;")
            led.mousePressEvent = lambda event, f=flag: self.toggle_flag(f)
            flag_vbox.addWidget(lbl_name)
            flag_vbox.addWidget(led, alignment=Qt.AlignmentFlag.AlignCenter)
            flags_layout.addLayout(flag_vbox)
            self.flag_leds[flag] = led

        left_top_vbox.addWidget(flags_group)
        top_hw_layout.addLayout(left_top_vbox)

        # Правый верхний угол: Keypad (F4-F5)
        keypad_group = QGroupBox("Keypad (F4-F5)")
        keypad_layout = QGridLayout(keypad_group)
        keypad_layout.setContentsMargins(6, 6, 6, 6)
        keypad_layout.setSpacing(3)

        if hasattr(self.cpu.mmu, 'hardware_inject_key') and not hasattr(self.cpu.mmu, 'hardware_inject_key_press'):
            self.cpu.mmu.hardware_inject_key_press = self.cpu.mmu.hardware_inject_key
        if hasattr(self.cpu.mmu, 'hardware_release_key') and not hasattr(self.cpu.mmu, 'hardware_inject_key_release'):
            self.cpu.mmu.hardware_inject_key_release = self.cpu.mmu.hardware_release_key

        for r in range(4):
            for c in range(4):
                val = r * 4 + c
                btn = QPushButton(f"{val:X}")
                btn.setFixedSize(36, 26)
                btn.pressed.connect(lambda v=val: self.cpu.mmu.hardware_inject_key_press(v))
                btn.released.connect(lambda: self.cpu.mmu.hardware_inject_key_release())
                keypad_layout.addWidget(btn, r, c)
                self.keys[val] = btn

        top_hw_layout.addWidget(keypad_group)
        layout.addLayout(top_hw_layout)

        # Компактные 7-сегментные дисплеи MMIO (F3-F0)
        font_id = QFontDatabase.addApplicationFont("emu/assets/Segment7Standard.otf")
        if font_id != -1:
            family = QFontDatabase.applicationFontFamilies(font_id)[0]
            seg_font = QFont(family, 26)
        else:
            seg_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
            seg_font.setPointSize(22)

        mmio_group = QGroupBox("MMIO Displays (F3-F0)")
        mmio_layout = QHBoxLayout(mmio_group)
        mmio_layout.setContentsMargins(6, 4, 6, 4)
        mmio_layout.setSpacing(6)
        
        for i in range(4):
            disp_vbox = QVBoxLayout()
            disp_vbox.setSpacing(1)
            lbl_val = QLabel("0")
            lbl_val.setFont(seg_font)
            lbl_val.setStyleSheet("color: red; background-color: black; padding: 2px 8px;")
            lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_name = QLabel(f"F{3-i}")
            lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            disp_vbox.addWidget(lbl_val)
            disp_vbox.addWidget(lbl_name)
            mmio_layout.addLayout(disp_vbox)
            self.mmio_labels.append(lbl_val)

        layout.addWidget(mmio_group)

    def toggle_flag(self, flag):
        regs = self.cpu.regs
        if flag == "R": regs.set_flag_r(not regs.get_flag_r())
        elif flag == "M": regs.set_flag_m(not regs.get_flag_m())
        elif flag == "C": regs.set_flag_c(not regs.get_flag_c())
        elif flag == "Z": regs.set_flag_z(not regs.get_flag_z())
        self.update_callback()

    def update_ui(self):
        regs = self.cpu.regs
        self.reg_labels["A"].setText(f"{regs.a:X}")
        self.reg_labels["B"].setText(f"{regs.b:X}")
        self.reg_labels["X"].setText(f"{regs.x:X}")
        self.reg_labels["Y"].setText(f"{regs.y:X}")
        self.reg_labels["XY"].setText(f"{(regs.x << 4) | regs.y:02X}")
        self.reg_labels["SP"].setText(f"{0xE0 | regs.sp:02X}")
        self.reg_labels["FL"].setText(f"{regs.fl:X}")
        self.reg_labels["PCH"].setText(f"{regs.pch:X}")
        self.reg_labels["PCL"].setText(f"{regs.pcl:X}")
        self.reg_labels["PC"].setText(f"{regs.pc:02X}")

        def update_led(f_key, state):
            color = "red" if state else "gray"
            self.flag_leds[f_key].setStyleSheet(f"background-color: {color}; border-radius: 7px;")

        update_led("R", regs.get_flag_r())
        update_led("M", regs.get_flag_m())
        update_led("C", regs.get_flag_c())
        update_led("Z", regs.get_flag_z())

        for i in range(4):
            self.mmio_labels[i].setText(f"{self.cpu.mmu.displays[3-i]:X}")

        audio_color = "red" if self.cpu.mmu.audio else "gray"
        self.audio_led.setStyleSheet(f"background-color: {audio_color}; border-radius: 6px;")


class MemoryPanel(QWidget):
    def __init__(self, cpu):
        super().__init__()
        self.cpu = cpu
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        mem_group = QGroupBox("Memory Viewer")
        mem_layout = QVBoxLayout(mem_group)
        mem_layout.setContentsMargins(6, 6, 6, 6)

        self.notebook = QTabWidget()
        
        self.rom_tree = self.create_mem_tree()
        self.ram_tree = self.create_mem_tree()
        self.notebook.addTab(self.rom_tree, "ROM (System)")
        self.notebook.addTab(self.ram_tree, "RAM (User)")

        self.disasm_label = QLabel(" 00: NOP ")
        self.disasm_label.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.disasm_label.setStyleSheet("color: blue; font-weight: bold; padding: 0px 8px;")
        self.disasm_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.notebook.setCornerWidget(self.disasm_label, Qt.Corner.TopRightCorner)

        mem_layout.addWidget(self.notebook)
        layout.addWidget(mem_group)

    def create_mem_tree(self):
        tree = QTableWidget(16, 16)
        tree.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        tree.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        headers = [f"{i:X}" for i in range(16)]
        tree.setHorizontalHeaderLabels(headers)
        row_headers = [f"{i:X}0" for i in range(16)]
        tree.setVerticalHeaderLabels(row_headers)

        for r in range(16):
            for c in range(16):
                item = QTableWidgetItem("0")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                tree.setItem(r, c, item)

        header = tree.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setDefaultSectionSize(20)
        header.setMinimumSectionSize(18)

        vheader = tree.verticalHeader()
        vheader.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        vheader.setDefaultSectionSize(18)
        vheader.setMinimumSectionSize(16)
        return tree

    def disassemble_current_instruction(self):
        regs = self.cpu.regs
        pc = regs.pc
        m_flag = regs.get_flag_m()
        read = lambda addr: self.cpu.mmu.read(addr, m_flag)
        REG_MAP = {0: "A", 1: "B", 2: "X", 3: "Y", 4: "SP", 5: "FL", 6: "PCH", 7: "PCL"}

        opcode = read(pc)
        if opcode == 0x0: return "NOP"
        elif opcode == 0x3: return "LDR"
        elif opcode == 0x4: return "STR"
        elif opcode == 0x1:
            imm = read((pc + 1) & 0xFF)
            return f"LDI 0x{imm:X}"
        elif opcode == 0x2:
            op = read((pc + 1) & 0xFF)
            d = (op >> 3) & 1
            r = op & 0x07
            reg_name = REG_MAP.get(r, f"R{r}")
            if d == 0: return f"MOV A, {reg_name}"
            else: return f"MOV {reg_name}, A"
        elif opcode in (0x5, 0x6, 0x7, 0x8, 0x9, 0xA):
            mnemonics = {0x5: "ADD", 0x6: "SUB", 0x7: "AND", 0x8: "XOR", 0x9: "INC", 0xA: "DEC"}
            op = read((pc + 1) & 0xFF)
            r = op & 0x07
            reg_name = REG_MAP.get(r, f"R{r}")
            return f"{mnemonics[opcode]} {reg_name}"
        elif opcode in (0xB, 0xC, 0xD, 0xE):
            mnemonics = {0xB: "JZ", 0xC: "JC", 0xD: "JMP", 0xE: "CAL"}
            h = read((pc + 1) & 0xFF)
            l = read((pc + 2) & 0xFF)
            addr = (h << 4) | l
            return f"{mnemonics[opcode]} 0x{addr:02X}"
        elif opcode == 0xF:
            func = read((pc + 1) & 0xFF)
            if func == 0x0: return "HLT"
            elif func == 0x1: return "RET"
            elif func == 0x4: return "SWI"
            elif func == 0x5: return "RETU"
            elif func == 0x6: return "LDRA"
            else: return f"SYS 0x{func:X}"
        return f"UNK 0x{opcode:X}"

    def update_mem_tree(self, tree, bank_flag, highlight_pc):
        for r in range(16):
            for c in range(16):
                idx = r * 16 + c
                val = self.cpu.mmu.read(idx, bank_flag)
                val_str = f"{val:X}"
                is_highlighted = (idx == highlight_pc)
                if is_highlighted:
                    val_str = f"[{val_str}]"
                item = tree.item(r, c)
                if item:
                    item.setText(val_str)
                    font = item.font()
                    font.setBold(is_highlighted)
                    item.setFont(font)

    def update_ui(self):
        pc = self.cpu.regs.pc
        m_flag = self.cpu.regs.get_flag_m()

        self.update_mem_tree(self.rom_tree, 1, pc if m_flag == 1 else -1)
        self.update_mem_tree(self.ram_tree, 0, pc if m_flag == 0 else -1)

        if m_flag == 1:
            self.notebook.setCurrentIndex(0)
        else:
            self.notebook.setCurrentIndex(1)

        disasm_text = self.disassemble_current_instruction()
        self.disasm_label.setText(f"[{pc:02X}] {disasm_text}")