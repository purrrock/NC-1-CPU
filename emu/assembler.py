class AssemblerError(Exception):
    pass

class Assembler:
    """
    Two-pass assembler for NC-1 CPU.
    """
    def __init__(self):
        self.regs = {
            "A": 0, "B": 1, "X": 2, "Y": 3,
            "SP": 4, "FL": 5, "PCH": 6, "PCL": 7
        }

        self.opcodes = {
            "NOP": 0x0,
            "LDI": 0x1,
            "MOV": 0x2,
            "LDR": 0x3,
            "STR": 0x4,
            "ADD": 0x5,
            "SUB": 0x6,
            "AND": 0x7,
            "XOR": 0x8,
            "INC": 0x9,
            "DEC": 0xA,
            "JZ":  0xB,
            "JC":  0xC,
            "JMP": 0xD,
            "CAL": 0xE,
            "SYS": 0xF,
        }

    def assemble(self, source_code: str) -> list[int]:
        lines = source_code.split('\n')
        labels = {}
        program = []

        # Pass 1: Resolve Labels
        pc = 0
        parsed_lines = []
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

            if opcode not in self.opcodes:
                raise AssemblerError(f"Unknown instruction '{opcode}' on line {line_num+1}")

            parsed_lines.append((line_num, opcode, parts[1:]))

            # Calculate instruction size
            if opcode in ["NOP", "LDR", "STR"]:
                pc += 1
            elif opcode in ["LDI", "MOV", "ADD", "SUB", "AND", "XOR", "INC", "DEC", "SYS"]:
                pc += 2
            elif opcode in ["JZ", "JC", "JMP", "CAL"]:
                pc += 3

        # Pass 2: Generate Code
        pc = 0
        for line_num, opcode, args in parsed_lines:
            program.append(self.opcodes[opcode])

            if opcode == "LDI":
                if len(args) != 1: raise AssemblerError(f"LDI expects 1 argument (line {line_num+1})")
                val = self._parse_val(args[0], labels)
                program.append(val & 0x0F)

            elif opcode == "MOV":
                if len(args) != 2: raise AssemblerError(f"MOV expects 2 arguments (line {line_num+1})")
                dest, src = args[0].upper(), args[1].upper()

                if dest == "A" and src in self.regs:
                    # Read from Reg to A
                    program.append((0 << 3) | self.regs[src])
                elif src == "A" and dest in self.regs:
                    # Write A to Reg
                    program.append((1 << 3) | self.regs[dest])
                else:
                    raise AssemblerError(f"MOV must use A as source or destination (line {line_num+1})")

            elif opcode in ["ADD", "SUB", "AND", "XOR", "INC", "DEC"]:
                if len(args) != 1: raise AssemblerError(f"{opcode} expects 1 argument (line {line_num+1})")
                reg = args[0].upper()
                if reg not in self.regs: raise AssemblerError(f"Invalid register '{reg}' (line {line_num+1})")
                program.append(self.regs[reg])

            elif opcode in ["JZ", "JC", "JMP", "CAL"]:
                if len(args) != 1: raise AssemblerError(f"{opcode} expects 1 argument (line {line_num+1})")
                addr = self._parse_val(args[0], labels)
                program.append((addr >> 4) & 0x0F)
                program.append(addr & 0x0F)

            elif opcode == "SYS":
                if len(args) != 1: raise AssemblerError(f"SYS expects 1 argument (line {line_num+1})")
                func = self._parse_val(args[0], labels)
                program.append(func & 0x0F)

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
