import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from .cpu import CPU
from .assembler import Assembler, AssemblerError

class GUI:
    def __init__(self, root: tk.Tk, cpu: CPU):
        self.root = root
        self.root.title("NC-1 Debug Board")
        self.cpu = cpu
        self.assembler = Assembler()

        self.is_running = False
        self.run_job = None

        self.setup_ui()
        self.update_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left Panel (Editor + Controls)
        left_panel = ttk.Frame(main_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Code Editor
        editor_frame = ttk.LabelFrame(left_panel, text="Code Editor")
        editor_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.editor = tk.Text(editor_frame, width=25, height=20, font=("Courier New", 10))
        self.editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Editor Controls
        editor_ctrl_frame = ttk.Frame(left_panel)
        editor_ctrl_frame.pack(fill=tk.X, pady=5)
        ttk.Button(editor_ctrl_frame, text="Load", command=self.load_code).pack(side=tk.LEFT, padx=2)
        ttk.Button(editor_ctrl_frame, text="Save", command=self.save_code).pack(side=tk.LEFT, padx=2)
        ttk.Button(editor_ctrl_frame, text="Assemble to ROM", command=self.assemble_to_rom).pack(side=tk.RIGHT, padx=2)
        ttk.Button(editor_ctrl_frame, text="Assemble to RAM", command=self.assemble_to_ram).pack(side=tk.RIGHT, padx=2)

        # Execution Controls
        exec_ctrl_frame = ttk.LabelFrame(left_panel, text="Execution")
        exec_ctrl_frame.pack(fill=tk.X, pady=5)
        ttk.Button(exec_ctrl_frame, text="Step", command=self.step).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(exec_ctrl_frame, text="Run", command=self.run).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(exec_ctrl_frame, text="Pause", command=self.pause).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(exec_ctrl_frame, text="Reset", command=self.reset).pack(side=tk.RIGHT, padx=5, pady=5)

        # Delay config
        ttk.Label(exec_ctrl_frame, text="Delay (ms):").pack(side=tk.LEFT, padx=(10,2), pady=5)
        self.delay_var = tk.StringVar(value="50")
        ttk.Entry(exec_ctrl_frame, textvariable=self.delay_var, width=5).pack(side=tk.LEFT, pady=5)

        # Right Panel (Registers, Flags, Memory)
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10,0))

        # Registers (7-segment mockups with labels)
        reg_frame = ttk.LabelFrame(right_panel, text="Registers (Hex)")
        reg_frame.pack(fill=tk.X, pady=5)

        self.reg_labels = {}
        for i, reg in enumerate(["A", "B", "X", "Y", "SP", "FL", "PCH", "PCL", "PC"]):
            ttk.Label(reg_frame, text=f"{reg}:").grid(row=i//3, column=(i%3)*2, padx=5, pady=2, sticky=tk.E)
            lbl = ttk.Label(reg_frame, text="0", font=("Courier New", 14, "bold"), foreground="red", background="black", width=2, anchor=tk.CENTER)
            lbl.grid(row=i//3, column=(i%3)*2+1, padx=5, pady=2)
            self.reg_labels[reg] = lbl

        # Flags (LEDs)
        flags_frame = ttk.LabelFrame(right_panel, text="Flags")
        flags_frame.pack(fill=tk.X, pady=5)

        self.flag_canvas = tk.Canvas(flags_frame, height=30, width=150)
        self.flag_canvas.pack(pady=5)

        self.flag_leds = {}
        for i, flag in enumerate(["R", "M", "C", "Z"]):
            x = 20 + i * 35
            self.flag_canvas.create_text(x, 10, text=flag)
            led = self.flag_canvas.create_oval(x-5, 18, x+5, 28, fill="gray")
            self.flag_leds[flag] = led

        # MMIO Displays (F0-F3)
        mmio_frame = ttk.LabelFrame(right_panel, text="MMIO Displays (F3-F0)")
        mmio_frame.pack(fill=tk.X, pady=5)
        self.mmio_labels = []
        for i in range(4):
            disp_subframe = ttk.Frame(mmio_frame)
            disp_subframe.pack(side=tk.LEFT, padx=10, pady=5)
            lbl = ttk.Label(disp_subframe, text="0", font=("Courier New", 18, "bold"), foreground="red", background="black", width=2, anchor=tk.CENTER)
            lbl.pack()
            ttk.Label(disp_subframe, text=f"F{3-i}").pack()
            self.mmio_labels.append(lbl)

        # Memory Viewer
        mem_frame = ttk.LabelFrame(right_panel, text="Memory Viewer")
        mem_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Notebook for ROM / RAM tabs
        self.notebook = ttk.Notebook(mem_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.rom_tree = self.create_mem_tree(self.notebook, "ROM")
        self.ram_tree = self.create_mem_tree(self.notebook, "RAM")

        self.notebook.add(self.rom_tree, text="ROM (System)")
        self.notebook.add(self.ram_tree, text="RAM (User)")

    def create_mem_tree(self, parent, name):
        columns = [f"{i:X}" for i in range(16)]
        tree = ttk.Treeview(parent, columns=columns, show="tree headings", height=16)

        tree.heading("#0", text="Addr")
        tree.column("#0", width=45, anchor=tk.CENTER)

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=30, anchor=tk.CENTER)

        # Insert 16 rows
        for r in range(16):
            row_id = f"{r:X}0"
            tree.insert("", "end", iid=row_id, text=row_id, values=(["0"]*16))

        return tree

    def update_ui(self):
        # Update Registers
        regs = self.cpu.regs
        self.reg_labels["A"].config(text=f"{regs.a:X}")
        self.reg_labels["B"].config(text=f"{regs.b:X}")
        self.reg_labels["X"].config(text=f"{regs.x:X}")
        self.reg_labels["Y"].config(text=f"{regs.y:X}")
        self.reg_labels["SP"].config(text=f"{regs.sp:X}")
        self.reg_labels["FL"].config(text=f"{regs.fl:X}")
        self.reg_labels["PCH"].config(text=f"{regs.pch:X}")
        self.reg_labels["PCL"].config(text=f"{regs.pcl:X}")
        self.reg_labels["PC"].config(text=f"{regs.pc:02X}")

        # Update Flags
        def update_led(flag, state):
            color = "red" if state else "gray"
            self.flag_canvas.itemconfig(self.flag_leds[flag], fill=color)

        update_led("R", regs.get_flag_r())
        update_led("M", regs.get_flag_m())
        update_led("C", regs.get_flag_c())
        update_led("Z", regs.get_flag_z())

        # Update MMIO Displays (F3 down to F0)
        # displays[3] is F3, displays[0] is F0. So we show them left-to-right as F3, F2, F1, F0
        for i in range(4):
            self.mmio_labels[i].config(text=f"{self.cpu.mmu.displays[3-i]:X}")

        # Update Memory Grids
        pc = regs.pc
        m_flag = regs.get_flag_m()

        self.update_mem_tree(self.rom_tree, self.cpu.mmu.rom, pc if m_flag == 1 else -1)
        self.update_mem_tree(self.ram_tree, self.cpu.mmu.ram, pc if m_flag == 0 else -1)

        # Bank Switching
        if m_flag == 1:
            self.notebook.select(self.rom_tree)
        else:
            self.notebook.select(self.ram_tree)

    def update_mem_tree(self, tree, memory, highlight_pc):
        for r in range(16):
            row_id = f"{r:X}0"
            values = []
            for c in range(16):
                idx = r * 16 + c
                val_str = f"{memory[idx]:X}"
                if idx == highlight_pc:
                    val_str = f"[{val_str}]"
                values.append(val_str)
            tree.item(row_id, values=values)

    def load_code(self):
        filepath = filedialog.askopenfilename(defaultextension=".asm", filetypes=[("Assembly", "*.asm"), ("All Files", "*.*")])
        if filepath:
            with open(filepath, "r") as f:
                self.editor.delete(1.0, tk.END)
                self.editor.insert(tk.END, f.read())

    def save_code(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".asm", filetypes=[("Assembly", "*.asm"), ("All Files", "*.*")])
        if filepath:
            with open(filepath, "w") as f:
                f.write(self.editor.get(1.0, tk.END))

    def assemble_to_rom(self):
        code = self.editor.get(1.0, tk.END)
        try:
            prog = self.assembler.assemble(code)
            self.cpu.mmu.load_rom(prog)
            self.update_ui()
            messagebox.showinfo("Success", f"Assembled {len(prog)} nibbles to ROM.")
        except AssemblerError as e:
            messagebox.showerror("Assembler Error", str(e))

    def assemble_to_ram(self):
        code = self.editor.get(1.0, tk.END)
        try:
            prog = self.assembler.assemble(code)
            self.cpu.mmu.load_ram(prog)
            self.update_ui()
            messagebox.showinfo("Success", f"Assembled {len(prog)} nibbles to RAM.")
        except AssemblerError as e:
            messagebox.showerror("Assembler Error", str(e))

    def step(self):
        if not self.cpu.halted:
            self.cpu.step()
            self.update_ui()
        else:
            messagebox.showinfo("Halted", "CPU is halted. Reset to continue.")

    def run(self):
        if not self.is_running:
            self.is_running = True
            self.run_loop()

    def run_loop(self):
        if self.is_running and not self.cpu.halted:
            self.cpu.step()
            self.update_ui()
            try:
                delay = int(self.delay_var.get())
            except ValueError:
                delay = 50
            self.run_job = self.root.after(delay, self.run_loop)
        else:
            self.is_running = False

    def pause(self):
        self.is_running = False
        if self.run_job:
            self.root.after_cancel(self.run_job)
            self.run_job = None
        self.update_ui()

    def reset(self):
        self.pause()
        self.cpu.reset()
        self.update_ui()
