import sys
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QGroupBox,
                             QPlainTextEdit, QPushButton, QLabel, QSpinBox,
                             QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
                             QFileDialog, QMessageBox, QGridLayout)
from PyQt6.QtGui import QFontDatabase, QFont
from PyQt6.QtCore import QTimer, Qt
from .cpu import CPU
from .assembler import Assembler, AssemblerError

class GUI(QWidget):
    def __init__(self, cpu: CPU):
        super().__init__()
        self.setWindowTitle("NC-1 Debug Board")
        self.cpu = cpu
        self.assembler = Assembler()

        self.is_running = False

        # Таймер для Event Model
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.run_loop)

        self.setup_ui()
        self.update_ui()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        self.setStyleSheet("""
            QPushButton {
                border: 2px outset gray;
                background-color: lightgray;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:pressed {
                border: 2px inset gray;
                background-color: darkgray;
            }
        """)

        # -------------------------------------------------------------
        # Left Panel: Инструменты разработки (Редактор, Управление)
        # -------------------------------------------------------------
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        editor_group = QGroupBox("Code Editor")
        editor_layout = QVBoxLayout(editor_group)

        self.editor = QPlainTextEdit()
        mono_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self.editor.setFont(mono_font)
        self.editor.setMinimumSize(250, 400)
        editor_layout.addWidget(self.editor)

        editor_ctrl_layout = QGridLayout()

        btn_load = QPushButton("Load")
        btn_load.clicked.connect(self.load_code)
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.save_code)
        editor_ctrl_layout.addWidget(btn_load, 0, 0)
        editor_ctrl_layout.addWidget(btn_save, 0, 1)

        btn_asm_rom = QPushButton("Assemble to ROM")
        btn_asm_rom.clicked.connect(self.assemble_to_rom)
        btn_asm_ram = QPushButton("Assemble to RAM")
        btn_asm_ram.clicked.connect(self.assemble_to_ram)
        editor_ctrl_layout.addWidget(btn_asm_rom, 1, 0)
        editor_ctrl_layout.addWidget(btn_asm_ram, 1, 1)

        editor_layout.addLayout(editor_ctrl_layout)
        left_layout.addWidget(editor_group)

        exec_group = QGroupBox("Execution")
        exec_layout = QGridLayout(exec_group)

        btn_step = QPushButton("Step")
        btn_step.clicked.connect(self.step)
        btn_run = QPushButton("Run")
        btn_run.clicked.connect(self.run)
        btn_pause = QPushButton("Pause")
        btn_pause.clicked.connect(self.pause)

        exec_layout.addWidget(btn_step, 0, 0)
        exec_layout.addWidget(btn_run, 0, 1)
        exec_layout.addWidget(btn_pause, 0, 2)

        btn_reset = QPushButton("Reset")
        btn_reset.clicked.connect(self.reset)
        exec_layout.addWidget(btn_reset, 1, 0)

        delay_label = QLabel("Delay (ms):")
        exec_layout.addWidget(delay_label, 1, 1, alignment=Qt.AlignmentFlag.AlignRight)
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(1, 1000)
        self.delay_spin.setValue(50)
        exec_layout.addWidget(self.delay_spin, 1, 2)

        left_layout.addWidget(exec_group)
        main_layout.addWidget(left_panel)

        # -------------------------------------------------------------
        # Right Panel: Аппаратный контекст и Память
        # -------------------------------------------------------------
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # --- Группа 1: Ядро (Регистры и Флаги) ---
        top_hw_layout = QHBoxLayout()

        reg_group = QGroupBox("Registers (Hex)")
        reg_layout = QGridLayout(reg_group)

        self.reg_labels = {}
        for i, reg in enumerate(["A", "B", "X", "Y", "SP", "FL", "PCH", "PCL", "PC"]):
            lbl_name = QLabel(f"{reg}:")
            lbl_val = QLabel("0")
            lbl_val.setFont(mono_font)
            lbl_val.setStyleSheet("color: red; background-color: black; font-weight: bold; padding: 2px;")
            lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_val.setMinimumWidth(30)

            reg_layout.addWidget(lbl_name, i // 3, (i % 3) * 2, alignment=Qt.AlignmentFlag.AlignRight)
            reg_layout.addWidget(lbl_val, i // 3, (i % 3) * 2 + 1)
            self.reg_labels[reg] = lbl_val

        top_hw_layout.addWidget(reg_group)

        flags_group = QGroupBox("Flags")
        flags_layout = QHBoxLayout(flags_group)
        self.flag_leds = {}
        for flag in ["R", "M", "C", "Z"]:
            flag_vbox = QVBoxLayout()
            lbl_name = QLabel(flag)
            lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            led = QLabel()
            led.setFixedSize(16, 16)
            led.setStyleSheet("background-color: gray; border-radius: 8px;")

            # Allow flag toggling via mouse click
            def make_toggle(f):
                return lambda event: self.toggle_flag(f)
            led.mousePressEvent = make_toggle(flag)

            flag_vbox.addWidget(lbl_name)
            flag_vbox.addWidget(led, alignment=Qt.AlignmentFlag.AlignCenter)
            flags_layout.addLayout(flag_vbox)
            self.flag_leds[flag] = led

        top_hw_layout.addWidget(flags_group)
        right_layout.addLayout(top_hw_layout)

        # --- Группа 2: Периферия (Дисплеи, Клавиатура, Аудио) ---
        mid_hw_layout = QHBoxLayout()
        
        font_id = QFontDatabase.addApplicationFont("assets/Segment7Standard.otf")
        if font_id != -1:
            family = QFontDatabase.applicationFontFamilies(font_id)[0]
            seg_font = QFont(family, 27)
        else:
            seg_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
            seg_font.setPointSize(27)

        mmio_group = QGroupBox("MMIO Displays (F3-F0)")
        mmio_layout = QHBoxLayout(mmio_group)
        self.mmio_labels = []
        for i in range(4):
            disp_vbox = QVBoxLayout()
            lbl_val = QLabel("0")
            lbl_val.setFont(seg_font)
            lbl_val.setStyleSheet("color: red; background-color: black; padding: 5px;")
            lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_name = QLabel(f"F{3-i}")
            lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)

            disp_vbox.addWidget(lbl_val)
            disp_vbox.addWidget(lbl_name)
            mmio_layout.addLayout(disp_vbox)
            self.mmio_labels.append(lbl_val)

        mid_hw_layout.addWidget(mmio_group)

        audio_group = QGroupBox("Audio (F6)")
        audio_layout = QVBoxLayout(audio_group)
        self.audio_led = QLabel()
        self.audio_led.setFixedSize(30, 30)
        self.audio_led.setStyleSheet("background-color: gray; border-radius: 15px;")
        audio_layout.addWidget(self.audio_led, alignment=Qt.AlignmentFlag.AlignCenter)
        mid_hw_layout.addWidget(audio_group)

        keypad_group = QGroupBox("Keypad (F4-F5)")
        keypad_layout = QGridLayout(keypad_group)
        self.keys = {}

        # Подменяем методы в соответствии с требованиями, чтобы не трогать mmu.py, но интерфейс был нужным
        if hasattr(self.cpu.mmu, 'hardware_inject_key') and not hasattr(self.cpu.mmu, 'hardware_inject_key_press'):
            self.cpu.mmu.hardware_inject_key_press = self.cpu.mmu.hardware_inject_key
        if hasattr(self.cpu.mmu, 'hardware_release_key') and not hasattr(self.cpu.mmu, 'hardware_inject_key_release'):
            self.cpu.mmu.hardware_inject_key_release = self.cpu.mmu.hardware_release_key

        for r in range(4):
            for c in range(4):
                val = r * 4 + c
                btn = QPushButton(f"{val:X}")
                btn.setFixedSize(40, 30)
                # Матричная клавиатура (F4-F5): сигналы pressed и released -> hardware_inject_key_press/release
                btn.pressed.connect(lambda v=val: self.cpu.mmu.hardware_inject_key_press(v))
                btn.released.connect(lambda: self.cpu.mmu.hardware_inject_key_release())
                keypad_layout.addWidget(btn, r, c)
                self.keys[val] = btn

        mid_hw_layout.addWidget(keypad_group)
        right_layout.addLayout(mid_hw_layout)

        # --- Блок Памяти ---
        mem_group = QGroupBox("Memory Viewer")
        mem_layout = QVBoxLayout(mem_group)

        self.disasm_label = QLabel("00: NOP")
        self.disasm_label.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.disasm_label.setStyleSheet("color: blue; font-weight: bold;")
        self.disasm_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        mem_layout.addWidget(self.disasm_label)

        self.notebook = QTabWidget()

        self.rom_tree = self.create_mem_tree()
        self.ram_tree = self.create_mem_tree()

        self.notebook.addTab(self.rom_tree, "ROM (System)")
        self.notebook.addTab(self.ram_tree, "RAM (User)")

        mem_layout.addWidget(self.notebook)
        right_layout.addWidget(mem_group)

        main_layout.addWidget(right_panel)

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

        # Настраиваем размеры ячеек
        header = tree.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        header.setDefaultSectionSize(22)
        header.setMinimumSectionSize(22)

        vheader = tree.verticalHeader()
        vheader.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        vheader.setDefaultSectionSize(20)
        vheader.setMinimumSectionSize(20)

        return tree

    def toggle_flag(self, flag):
        regs = self.cpu.regs
        if flag == "R":
            regs.set_flag_r(not regs.get_flag_r())
        elif flag == "M":
            regs.set_flag_m(not regs.get_flag_m())
        elif flag == "C":
            regs.set_flag_c(not regs.get_flag_c())
        elif flag == "Z":
            regs.set_flag_z(not regs.get_flag_z())
        self.update_ui()

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
            if d == 0:
                return f"MOV A, {reg_name}"
            else:
                return f"MOV {reg_name}, A"
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
            else: return f"SYS 0x{func:X}"
        return f"UNK 0x{opcode:X}"

    def update_ui(self):
        regs = self.cpu.regs
        self.reg_labels["A"].setText(f"{regs.a:X}")
        self.reg_labels["B"].setText(f"{regs.b:X}")
        self.reg_labels["X"].setText(f"{regs.x:X}")
        self.reg_labels["Y"].setText(f"{regs.y:X}")
        self.reg_labels["SP"].setText(f"{regs.sp:X}")
        self.reg_labels["FL"].setText(f"{regs.fl:X}")
        self.reg_labels["PCH"].setText(f"{regs.pch:X}")
        self.reg_labels["PCL"].setText(f"{regs.pcl:X}")
        self.reg_labels["PC"].setText(f"{regs.pc:02X}")

        def update_led(flag, state):
            color = "red" if state else "gray"
            self.flag_leds[flag].setStyleSheet(f"background-color: {color}; border-radius: 8px;")

        update_led("R", regs.get_flag_r())
        update_led("M", regs.get_flag_m())
        update_led("C", regs.get_flag_c())
        update_led("Z", regs.get_flag_z())

        for i in range(4):
            self.mmio_labels[i].setText(f"{self.cpu.mmu.displays[3-i]:X}")

        audio_color = "red" if self.cpu.mmu.audio else "gray"
        self.audio_led.setStyleSheet(f"background-color: {audio_color}; border-radius: 15px;")

        pc = regs.pc
        m_flag = regs.get_flag_m()

        self.update_mem_tree(self.rom_tree, 1, pc if m_flag == 1 else -1)
        self.update_mem_tree(self.ram_tree, 0, pc if m_flag == 0 else -1)

        if m_flag == 1:
            self.notebook.setCurrentIndex(0)
        else:
            self.notebook.setCurrentIndex(1)

        disasm_text = self.disassemble_current_instruction()
        self.disasm_label.setText(f"[{pc:02X}] {disasm_text}")

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

    def load_code(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Open Assembly", "", "Assembly (*.asm);;All Files (*.*)")
        if filepath:
            with open(filepath, "r") as f:
                self.editor.setPlainText(f.read())

    def save_code(self):
        filepath, _ = QFileDialog.getSaveFileName(self, "Save Assembly", "", "Assembly (*.asm);;All Files (*.*)")
        if filepath:
            with open(filepath, "w") as f:
                f.write(self.editor.toPlainText())

    def assemble_to_rom(self):
        code = self.editor.toPlainText()
        try:
            prog = self.assembler.assemble(code)
            self.cpu.mmu.load_rom(prog)
            self.update_ui()
            QMessageBox.information(self, "Success", f"Assembled {len(prog)} nibbles to ROM.")
        except AssemblerError as e:
            QMessageBox.critical(self, "Assembler Error", str(e))

    def assemble_to_ram(self):
        code = self.editor.toPlainText()
        try:
            prog = self.assembler.assemble(code)
            self.cpu.mmu.load_ram(prog)
            self.update_ui()
            QMessageBox.information(self, "Success", f"Assembled {len(prog)} nibbles to RAM.")
        except AssemblerError as e:
            QMessageBox.critical(self, "Assembler Error", str(e))

    def step(self):
        if not self.cpu.halted:
            self.cpu.step()
            self.update_ui()
        else:
            QMessageBox.information(self, "Halted", "CPU is halted. Reset to continue.")

    def run(self):
        if not self.is_running:
            self.is_running = True
            delay = self.delay_spin.value()
            self.timer.start(delay)

    def run_loop(self):
        if self.is_running and not self.cpu.halted:
            self.cpu.step()
            self.update_ui()
        else:
            self.is_running = False
            self.timer.stop()

    def pause(self):
        self.is_running = False
        self.timer.stop()
        self.update_ui()

    def reset(self):
        self.pause()
        self.cpu.reset()
        self.update_ui()
