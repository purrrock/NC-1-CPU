import sys
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QGroupBox,
                             QPushButton, QLabel, QSpinBox, QFileDialog, 
                             QMessageBox, QGridLayout)
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtCore import QTimer, Qt

from cpu import CPU
from assembler import Assembler, AssemblerError
from editor import CodeEditor
from panels import HardwarePanel, MemoryPanel

class GUI(QWidget):
    def __init__(self, cpu: CPU):
        super().__init__()
        self.setWindowTitle("NC-1 Debug Board v4.5")
        self.cpu = cpu
        self.assembler = Assembler()
        self.is_running = False
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.run_loop)

        self.cpu.mmu.storage_drive.on_motor_on_read = self.handle_storage_read
        self.cpu.mmu.storage_drive.on_motor_on_write = self.handle_storage_write

        self.setup_ui()
        self.update_ui()
        
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def handle_storage_read(self):
        was_running = self.is_running
        if was_running:
            self.timer.stop() 

        filename, _ = QFileDialog.getOpenFileName(self, "Load from Storage", "", "Data Files (*.bin);;All Files (*.*)")
        
        if was_running:
            self.timer.start() 
        return filename

    def handle_storage_write(self):
        was_running = self.is_running
        if was_running:
            self.timer.stop()

        filename, _ = QFileDialog.getSaveFileName(self, "Save to Storage", "", "Data Files (*.bin);;All Files (*.*)")
        
        if was_running:
            self.timer.start()
        return filename

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        self.setStyleSheet("""
            QPushButton {
                border: 2px outset gray;
                background-color: lightgray;
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton:pressed {
                border: 2px inset gray;
                background-color: darkgray;
            }
            QPushButton#runButton:checked {
                background-color: red;
                color: white;
                border: 2px inset darkred;
            }
            QTabWidget::pane {
                border-top: 2px solid #8F8F91;
            }
            QTabBar::tab {
                background: lightgray;
                border: 2px solid #8F8F91;
                border-bottom-color: #8F8F91;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                color: black;
                padding: 3px 8px;
            }
            QTabBar::tab:selected {
                background: #F0F0F0;
                border-color: #8F8F91;
                border-bottom-color: #F0F0F0;
                font-weight: bold;
                color: darkblue;
                margin-top: -2px;
            }
            QTabBar::tab:!selected {
                margin-top: 2px;
            }
        """)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        editor_group = QGroupBox("Code Editor")
        editor_layout = QVBoxLayout(editor_group)

        self.editor = CodeEditor()
        mono_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self.editor.setFont(mono_font)
        self.editor.setMinimumSize(220, 200) 
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

        btn_clear_rom = QPushButton("Clear ROM")
        btn_clear_rom.clicked.connect(self.clear_rom)
        btn_clear_ram = QPushButton("Clear RAM")
        btn_clear_ram.clicked.connect(self.clear_ram)
        editor_ctrl_layout.addWidget(btn_clear_rom, 2, 0)
        editor_ctrl_layout.addWidget(btn_clear_ram, 2, 1)

        editor_layout.addLayout(editor_ctrl_layout)
        left_layout.addWidget(editor_group)

        exec_group = QGroupBox("Execution")
        exec_layout = QGridLayout(exec_group)

        btn_step = QPushButton("Step")
        btn_step.clicked.connect(self.step)
        
        self.btn_run = QPushButton("Run")
        self.btn_run.setObjectName("runButton")
        self.btn_run.setCheckable(True)
        self.btn_run.clicked.connect(self.run)

        exec_layout.addWidget(btn_step, 0, 0)
        exec_layout.addWidget(self.btn_run, 0, 1, 1, 2)

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

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.hw_panel = HardwarePanel(self.cpu, self.update_ui)
        right_layout.addWidget(self.hw_panel)

        self.mem_panel = MemoryPanel(self.cpu)
        right_layout.addWidget(self.mem_panel)

        main_layout.addWidget(right_panel)

    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return super().keyPressEvent(event)
        
        if self.editor.hasFocus():
            return super().keyPressEvent(event)
            
        val = self.hw_panel.key_map.get(event.key())
        if val is not None:
            self.cpu.mmu.hardware_inject_key_press(val)
            if val in self.hw_panel.keys:
                self.hw_panel.keys[val].setDown(True)  
            self.update_ui()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return super().keyReleaseEvent(event)
            
        if self.editor.hasFocus():
            return super().keyReleaseEvent(event)
            
        val = self.hw_panel.key_map.get(event.key())
        if val is not None:
            self.cpu.mmu.hardware_inject_key_release()
            if val in self.hw_panel.keys:
                self.hw_panel.keys[val].setDown(False) 
            self.update_ui()
        else:
            super().keyReleaseEvent(event)

    def update_ui(self):
        self.hw_panel.update_ui()
        self.mem_panel.update_ui()

    def load_code(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Open Assembly", "", "Assembly (*.asm);;All Files (*.*)")
        if filepath:
            with open(filepath, "r", encoding="utf-8") as f:
                self.editor.setPlainText(f.read())

    def save_code(self):
        filepath, _ = QFileDialog.getSaveFileName(self, "Save Assembly", "", "Assembly (*.asm);;All Files (*.*)")
        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())

    def assemble_to_rom(self):
        code = self.editor.toPlainText()
        try:
            prog = self.assembler.assemble(code)
            self.cpu.mmu.load_rom(prog)
            self.update_ui()
            QMessageBox.information(self, "Success", f"Assembled {len(prog)} nibbles to ROM.")
        except (AssemblerError, ValueError) as e:
            print(f"[ASSEMBLER ERROR] {str(e)}")
            QMessageBox.critical(self, "Assembler Error", str(e))

    def assemble_to_ram(self):
        code = self.editor.toPlainText()
        try:
            prog = self.assembler.assemble(code)
            self.cpu.mmu.load_ram(prog)
            self.update_ui()
            QMessageBox.information(self, "Success", f"Assembled {len(prog)} nibbles to RAM.")
        except (AssemblerError, ValueError) as e:
            print(f"[ASSEMBLER ERROR] {str(e)}")
            QMessageBox.critical(self, "Assembler Error", str(e))

    def clear_rom(self):
        if hasattr(self.cpu.mmu, 'clear_rom'):
            self.cpu.mmu.clear_rom()
        else:
            self.cpu.mmu.rom = [0] * 256
        self.update_ui()

    def clear_ram(self):
        if hasattr(self.cpu.mmu, 'clear_ram'):
            self.cpu.mmu.clear_ram()
        else:
            self.cpu.mmu.ram = [0] * 256
        self.update_ui()

    def step(self):
        if not self.cpu.halted:
            self.cpu.step()
            self.update_ui()
            if self.cpu.halted and self.is_running:
                self.pause()
        else:
            QMessageBox.information(self, "Halted", "CPU is halted. Reset to continue.")

    def run(self, checked=False):
        if self.btn_run.isChecked():
            if self.cpu.halted:
                self.btn_run.setChecked(False)
                QMessageBox.information(self, "Halted", "CPU is halted. Reset to continue.")
            else:
                self.is_running = True
                delay = self.delay_spin.value()
                self.timer.start(delay)
        else:
            self.pause()

    def run_loop(self):
        if self.is_running and not self.cpu.halted:
            self.cpu.step()
            self.update_ui()
            if self.cpu.halted:
                self.pause()
        else:
            self.pause()

    def pause(self):
        self.is_running = False
        self.timer.stop()
        self.btn_run.setChecked(False)
        self.update_ui()

    def reset(self):
        self.pause()
        self.cpu.reset()
        self.cpu.mmu.storage_drive.on_motor_on_read = self.handle_storage_read
        self.cpu.mmu.storage_drive.on_motor_on_write = self.handle_storage_write
        self.update_ui()