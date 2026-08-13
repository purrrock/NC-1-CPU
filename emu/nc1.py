import sys
from PyQt6.QtWidgets import QApplication

# Убраны точки перед именами модулей (абсолютный импорт)
from mmu import MMU
from registers import RegisterFile
from cpu import CPU
from gui import GUI

def main():
    app = QApplication(sys.argv)

    mmu = MMU()
    regs = RegisterFile()
    cpu = CPU(mmu, regs)

    # Do initial reset
    cpu.reset()

    # Create and show the GUI
    window = GUI(cpu)
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()