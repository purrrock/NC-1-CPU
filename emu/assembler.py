class AssemblerError(Exception):
    pass

class Assembler:
    """
    Two-pass assembler for NC-1 CPU (ISA v4.0).
    Includes ORG directive, bound checks, and SYS aliases.
    """
    def __init__(self):
        self.regs = {
            "A": 0, "B": 1, "X": 2, "Y": 3,
            "SP": 4, "FL": 5, "PCH": 6, "PCL": 7
        }

        self.opcodes = {
            "NOP": 0x0, "LDI": 0x1, "MOV": 0x2, "LDR": 0x3,
            "STR": 0x4, "ADD": 0x5, "SUB": 0x6, "AND": 0x7,
            "XOR": 0x8, "INC": 0x9, "DEC": 0xA, "JZ":  0xB,
            "JC":  0xC, "JMP": 0xD, "CAL": 0xE, "SYS": 0xF,
        }

        # Аппаратные алиасы для прерываний и системных вызовов
        self.sys_aliases = {
            "HLT": 0x0, "RET": 0x1, "SWI": 0x4, "RETU": 0x5, "LDRA": 0x6
        }
    def assemble(self, source_code: str) -> list[int]:
        lines = source_code.split('\n')
        labels = {}
        program = []
        parsed_lines = []
        
        # Pass 1: Распознавание меток, директивы ORG и вычисление абсолютных адресов (PC)
        pc = 0
        for line_num, line in enumerate(lines):
            line = line.split(';')[0].strip()
            if not line:
                continue

            if ':' in line:
                parts = line.split(':')
                label = parts[0].strip()
                labels[label] = pc
                line = parts[1].strip()
                if not line:
                    continue

            parts = line.replace(',', ' ').split()
            opcode = parts[0].upper()
            args = parts[1:]

            if opcode == "ORG":
                if len(args) != 1:
                    raise AssemblerError(f"ORG expects 1 argument (line {line_num+1})")
                pc = self._parse_val(args[0], {})  # Разрешение значения без словаря меток
                parsed_lines.append((line_num, opcode, args))
                continue

            if opcode not in self.opcodes and opcode not in self.sys_aliases:
                raise AssemblerError(f"Unknown instruction '{opcode}' on line {line_num+1}")

            parsed_lines.append((line_num, opcode, args))

            # Расчет аппаратного сдвига PC
            if opcode in ["NOP", "LDR", "STR"]:
                pc += 1
            elif opcode in ["LDI", "MOV", "ADD", "SUB", "AND", "XOR", "INC", "DEC", "SYS"]:
                pc += 2
            elif opcode in ["JZ", "JC", "JMP", "CAL"]:
                pc += 3
            elif opcode in self.sys_aliases:
                pc += 2  # Алиасы транслируются в двухниббловую команду SYS

        # Pass 2: Кодогенерация с проверкой границ операндов
        pc = 0
        for line_num, opcode, args in parsed_lines:
            if opcode == "ORG":
                target_pc = self._parse_val(args[0], {})
                if target_pc < pc:
                    raise AssemblerError(f"ORG overlaps or jumps backward (line {line_num+1})")
                
                # Заполнение неиспользуемой памяти между блоками NOP-инструкциями (0x0)
                # для сохранения консистентности плоского массива памяти эмулятора.
                program.extend([0x0] * (target_pc - pc))
                pc = target_pc
                continue

            if opcode in self.sys_aliases:
                program.append(self.opcodes["SYS"])
                program.append(self.sys_aliases[opcode])
                pc += 2
                continue

            program.append(self.opcodes[opcode])

            if opcode == "LDI":
                if len(args) != 1: raise AssemblerError(f"LDI expects 1 argument (line {line_num+1})")
                val = self._parse_val(args[0], labels)
                if not (0 <= val <= 15): 
                    raise AssemblerError(f"Value 0x{val:X} out of 4-bit range (line {line_num+1})")
                program.append(val)
                pc += 2

            elif opcode == "MOV":
                if len(args) != 2: raise AssemblerError(f"MOV expects 2 arguments (line {line_num+1})")
                dest, src = args[0].upper(), args[1].upper()

                if dest == "A" and src in self.regs:
                    # Чтение из регистра в Аккумулятор (Бит D = 0)
                    program.append((0 << 3) | self.regs[src])
                elif src == "A" and dest in self.regs:
                    # Запись Аккумулятора в регистр (Бит D = 1)
                    program.append((1 << 3) | self.regs[dest])
                else:
                    raise AssemblerError(f"MOV must use A as source or destination (line {line_num+1})")
                pc += 2

            elif opcode in ["ADD", "SUB", "AND", "XOR", "INC", "DEC"]:
                if len(args) != 1: raise AssemblerError(f"{opcode} expects 1 argument (line {line_num+1})")
                reg = args[0].upper()
                if reg not in self.regs: raise AssemblerError(f"Invalid register '{reg}' (line {line_num+1})")
                program.append(self.regs[reg])
                pc += 2

            elif opcode in ["JZ", "JC", "JMP", "CAL"]:
                if len(args) != 1: raise AssemblerError(f"{opcode} expects 1 argument (line {line_num+1})")
                addr = self._parse_val(args[0], labels)
                if not (0 <= addr <= 255): 
                    raise AssemblerError(f"Address 0x{addr:X} out of 8-bit range (line {line_num+1})")
                
                # Извлечение High и Low нибблов из 8-битного адреса
                program.append((addr >> 4) & 0x0F)
                program.append(addr & 0x0F)
                pc += 3

            elif opcode == "SYS":
                if len(args) != 1: raise AssemblerError(f"SYS expects 1 argument (line {line_num+1})")
                func = self._parse_val(args[0], labels)
                if not (0 <= func <= 15):
                    raise AssemblerError(f"SYS parameter 0x{func:X} out of 4-bit range (line {line_num+1})")
                program.append(func)
                pc += 2
            
            elif opcode in ["NOP", "LDR", "STR"]:
                pc += 1

        return program

    def _parse_val(self, val_str: str, labels: dict) -> int:
        if val_str in labels:
            return labels[val_str]

        try:
            if val_str.startswith("0x") or val_str.startswith("0X"):
                return int(val_str, 16)
            elif val_str.endswith("h") or val_str.endswith("H"):
                return int(val_str[:-1], 16)
            elif val_str.endswith("b") or val_str.endswith("B"):
                return int(val_str[:-1], 2)
            else:
                return int(val_str)
        except ValueError:
            raise AssemblerError(f"Invalid value or unknown label: '{val_str}'")