import tkinter as tk
from .mmu import MMU
from .registers import RegisterFile
from .cpu import CPU
from .gui import GUI

def main():
    mmu = MMU()
    regs = RegisterFile()
    cpu = CPU(mmu, regs)

    # Do initial reset
    cpu.reset()

    root = tk.Tk()
    app = GUI(root, cpu)

    root.mainloop()

if __name__ == "__main__":
    main()
