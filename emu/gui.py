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

        # -------------------------------------------------------------
        # Left Panel: Инструменты разработки (Редактор, Управление)
        # -------------------------------------------------------------
        left_panel = ttk.Frame(main_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, expand=False)

        editor_frame = ttk.LabelFrame(left_panel, text="Code Editor")
        editor_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.editor = tk.Text(editor_frame, width=15, height=20, font=("Courier New", 10))
        self.editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        editor_ctrl_frame = ttk.Frame(left_panel)
        editor_ctrl_frame.pack(fill=tk.X, pady=5)

        row1 = ttk.Frame(editor_ctrl_frame)
        row1.pack(fill=tk.X, pady=2)
        ttk.Button(row1, text="Load", command=self.load_code).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ttk.Button(row1, text="Save", command=self.save_code).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        row2 = ttk.Frame(editor_ctrl_frame)
        row2.pack(fill=tk.X, pady=2)
        ttk.Button(row2, text="Assemble to ROM", command=self.assemble_to_rom).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ttk.Button(row2, text="Assemble to RAM", command=self.assemble_to_ram).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        exec_ctrl_frame = ttk.LabelFrame(left_panel, text="Execution")
        exec_ctrl_frame.pack(fill=tk.X, pady=5)

        exec_row1 = ttk.Frame(exec_ctrl_frame)
        exec_row1.pack(fill=tk.X, pady=2)
        ttk.Button(exec_row1, text="Step", command=self.step).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ttk.Button(exec_row1, text="Run", command=self.run).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ttk.Button(exec_row1, text="Pause", command=self.pause).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        exec_row2 = ttk.Frame(exec_ctrl_frame)
        exec_row2.pack(fill=tk.X, pady=2)
        ttk.Button(exec_row2, text="Reset", command=self.reset).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        ttk.Label(exec_row2, text="Delay (ms):").pack(side=tk.LEFT, padx=(10,2))
        self.delay_var = tk.StringVar(value="50")
        ttk.Entry(exec_row2, textvariable=self.delay_var, width=5).pack(side=tk.LEFT)

        # -------------------------------------------------------------
        # Right Panel: Аппаратный контекст и Память
        # -------------------------------------------------------------
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10,0))

        # --- Группа 1: Ядро (Регистры и Флаги) ---
        # Использование side=tk.LEFT в дочерних фреймах позволяет выстроить их в единую горизонтальную строку
        top_hw_frame = ttk.Frame(right_panel)
        top_hw_frame.pack(fill=tk.X, pady=5)

        reg_frame = ttk.LabelFrame(top_hw_frame, text="Registers (Hex)")
        # fill=tk.Y гарантирует одинаковую высоту фрейма с соседними элементами по горизонтали
        reg_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))

        self.reg_labels = {}
        for i, reg in enumerate(["A", "B", "X", "Y", "SP", "FL", "PCH", "PCL", "PC"]):
            # Расположение 9 регистров матрицей 3x3 через grid-менеджер
            ttk.Label(reg_frame, text=f"{reg}:").grid(row=i//3, column=(i%3)*2, padx=5, pady=2, sticky=tk.E)
            lbl = ttk.Label(reg_frame, text="0", font=("Courier New", 14, "bold"), foreground="red", background="black", width=2, anchor=tk.CENTER)
            lbl.grid(row=i//3, column=(i%3)*2+1, padx=5, pady=2)
            self.reg_labels[reg] = lbl

        flags_frame = ttk.LabelFrame(top_hw_frame, text="Flags")
        flags_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.flag_canvas = tk.Canvas(flags_frame, height=30, width=150)
        # Центрируем Canvas с помощью отступов
        self.flag_canvas.pack(pady=20, padx=10)

        self.flag_leds = {}
        for i, flag in enumerate(["R", "M", "C", "Z"]):
            x = 20 + i * 35
            self.flag_canvas.create_text(x, 10, text=flag)
            led = self.flag_canvas.create_oval(x-5, 18, x+5, 28, fill="gray")
            self.flag_leds[flag] = led

        # --- Группа 2: Периферия (Дисплеи, Клавиатура, Аудио) ---
        mid_hw_frame = ttk.Frame(right_panel)
        mid_hw_frame.pack(fill=tk.X, pady=5)

        mmio_frame = ttk.LabelFrame(mid_hw_frame, text="MMIO Displays (F3-F0)")
        mmio_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        
        self.mmio_labels = []
        for i in range(4):
            disp_subframe = ttk.Frame(mmio_frame)
            disp_subframe.pack(side=tk.LEFT, padx=8, pady=5)
            lbl = ttk.Label(disp_subframe, text="0", font=("Courier New", 18, "bold"), foreground="red", background="black", width=2, anchor=tk.CENTER)
            lbl.pack()
            ttk.Label(disp_subframe, text=f"F{3-i}").pack()
            self.mmio_labels.append(lbl)

        io_frame = ttk.Frame(mid_hw_frame)
        io_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        audio_frame = ttk.LabelFrame(io_frame, text="Audio (F6)")
        audio_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        self.audio_canvas = tk.Canvas(audio_frame, height=50, width=50)
        self.audio_canvas.pack(padx=10, pady=20)
        self.audio_led = self.audio_canvas.create_oval(15, 15, 35, 35, fill="gray")

        keypad_frame = ttk.LabelFrame(io_frame, text="Keypad (F4-F5)")
        keypad_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.keys = {}
        for r in range(4):
            for c in range(4):
                val = r * 4 + c
                btn = ttk.Button(keypad_frame, text=f"{val:X}", width=4)
                btn.grid(row=r, column=c, padx=2, pady=2)
                
                # Биндинг низкоуровневых событий X11/Windows для обработки зажатия клавиши (Имитация регистра-защелки)
                btn.bind("<ButtonPress-1>", lambda e, v=val: self.on_keypad_press(v))
                btn.bind("<ButtonRelease-1>", lambda e, v=val: self.on_keypad_release(v))
                self.keys[val] = btn

        # --- Блок Памяти ---
        mem_frame = ttk.LabelFrame(right_panel, text="Memory Viewer")
        mem_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.notebook = ttk.Notebook(mem_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.rom_tree = self.create_mem_tree(self.notebook, "ROM")
        self.ram_tree = self.create_mem_tree(self.notebook, "RAM")

        self.notebook.add(self.rom_tree, text="ROM (System)")
        self.notebook.add(self.ram_tree, text="RAM (User)")

    def on_keypad_press(self, val):
        self.cpu.mmu.kbd_code = val & 0x0F
        self.cpu.mmu.kbd_stat |= 0x01
        if not self.is_running:
            self.update_ui()

    def on_keypad_release(self, val):
        self.cpu.mmu.kbd_stat &= ~0x01
        if not self.is_running:
            self.update_ui()

    def create_mem_tree(self, parent, name):
        columns = [f"{i:X}" for i in range(16)]
        tree = ttk.Treeview(parent, columns=columns, show="tree headings", height=16)

        tree.heading("#0", text="Addr")
        tree.column("#0", width=45, anchor=tk.CENTER)

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=30, anchor=tk.CENTER)

        for r in range(16):
            row_id = f"{r:X}0"
            tree.insert("", "end", iid=row_id, text=row_id, values=(["0"]*16))

        return tree

    def update_ui(self):
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

        def update_led(flag, state):
            color = "red" if state else "gray"
            self.flag_canvas.itemconfig(self.flag_leds[flag], fill=color)

        update_led("R", regs.get_flag_r())
        update_led("M", regs.get_flag_m())
        update_led("C", regs.get_flag_c())
        update_led("Z", regs.get_flag_z())

        for i in range(4):
            self.mmio_labels[i].config(text=f"{self.cpu.mmu.displays[3-i]:X}")

        audio_color = "red" if self.cpu.mmu.audio else "gray"
        self.audio_canvas.itemconfig(self.audio_led, fill=audio_color)

        pc = regs.pc
        m_flag = regs.get_flag_m()

        # Передаем идентификатор банка (1 - ROM, 0 - RAM) вместо самого массива
        self.update_mem_tree(self.rom_tree, 1, pc if m_flag == 1 else -1)
        self.update_mem_tree(self.ram_tree, 0, pc if m_flag == 0 else -1)

        if m_flag == 1:
            self.notebook.select(self.rom_tree)
        else:
            self.notebook.select(self.ram_tree)

    def update_mem_tree(self, tree, bank_flag, highlight_pc):
        for r in range(16):
            row_id = f"{r:X}0"
            values = []
            for c in range(16):
                idx = r * 16 + c
                
                # Аппаратное чтение через MMU. 
                # Гарантирует корректный поллинг MMIO-устройств в диапазоне F0-FF.
                val = self.cpu.mmu.read(idx, bank_flag)
                val_str = f"{val:X}"
                
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