import re

class AssemblerError(Exception):
    pass

class Assembler:
    """
    Two-pass assembler for NC-1 CPU (ISA v4.5 Variable-Length).
    Includes ORG, DN, DB directives, bound checks, relative jumps, and syntax synonyms.
    """
    def __init__(self):
        self.regs = {
            "A": 0, "B": 1, "X": 2, "Y": 3,
            "SP": 4, "FL": 5, "PCH": 6, "PCL": 7
        }

    def assemble(self, source_code: str) -> list[int]:
        lines = source_code.split('\n')
        labels = {}
        program = []
        parsed_lines = []

        # Pass 1: Resolve Labels and Calculate PC based on variable instruction sizes
        pc = 0
        for line_num, line in enumerate(lines):
            line = line.split(';')[0].strip()
            if not line:
                continue

            if ':' in line:
                parts = line.split(':', 1)
                label = parts[0].strip()
                labels[label] = pc
                line = parts[1].strip()
                if not line:
                    continue

            # Разделяем строку по пробелам и запятым
            tokens = [t.strip().upper() for t in re.split(r'[,\s]+', line) if t.strip()]
            if not tokens:
                continue

            opcode = tokens[0]
            args = tokens[1:]

            # --- Directives ---
            if opcode == "ORG":
                if len(args) != 1:
                    raise AssemblerError(f"ORG expects 1 argument (line {line_num+1})")
                pc = self._parse_val(args[0], {})
                parsed_lines.append((line_num, "ORG", args, 0))
                continue
            elif opcode == "DN":
                if not args:
                    raise AssemblerError(f"DN expects at least 1 argument (line {line_num+1})")
                parsed_lines.append((line_num, "DN", args, pc))
                pc += len(args)
                continue
            elif opcode == "DB":
                if not args:
                    raise AssemblerError(f"DB expects at least 1 argument (line {line_num+1})")
                parsed_lines.append((line_num, "DB", args, pc))
                pc += len(args) * 2
                continue

            # --- Instructions ---
            size = 0
            std_opcode = opcode

            # 1-Nibble Instructions
            if opcode in ("LDR", "STR", "RET", "INX", "DEX"):
                size = 1
            elif opcode in ("PHA", "PUSH"):
                std_opcode = "PHA"; size = 1
            elif opcode in ("PLA", "POP"):
                std_opcode = "PLA"; size = 1
            elif opcode == "INC":
                std_opcode = "INC"; size = 1
            elif opcode == "DEC":
                std_opcode = "DEC"; size = 1
            elif opcode == "MOV":
                if len(args) != 2:
                    raise AssemblerError(f"MOV expects 2 arguments (line {line_num+1})")
                if args[0] == "A" and args[1] == "B":
                    std_opcode = "MOV_A_B"; size = 1
                elif args[0] == "B" and args[1] == "A":
                    std_opcode = "MOV_B_A"; size = 1
                else:
                    std_opcode = "MOV_REG"; size = 3 # F0 MOV Reg

            # 2-Nibble Instructions
            elif opcode in ("LDI", "JZR", "JCR", "JR", "XCHG", "ADD", "SUB", "AND", "XOR", "LDRA", "XBNK", "BOOT", "HLT"):
                size = 2
            elif opcode == "NOP":
                # В v4.5 NOP транслируется в JR +0 (E 0)
                std_opcode = "NOP"; size = 2 

            # 4-Nibble Instructions
            elif opcode in ("JZ", "JC", "JMP", "CAL", "LDP"):
                size = 4
            else:
                raise AssemblerError(f"Unknown instruction '{opcode}' on line {line_num+1}")

            parsed_lines.append((line_num, std_opcode, args, pc))
            pc += size

        # Pass 2: Generate Machine Code
        pc = 0
        for line_num, opcode, args, instr_pc in parsed_lines:
            if opcode == "ORG":
                target_pc = self._parse_val(args[0], {})
                if target_pc < pc:
                    raise AssemblerError(f"ORG overlaps or jumps backward (line {line_num+1})")
                program.extend([0x0] * (target_pc - pc))
                pc = target_pc
                continue

            # --- Processing Data Directives ---
            if opcode == "DN":
                for arg in args:
                    val = self._parse_val(arg, labels)
                    if not (0 <= val <= 15): 
                        raise AssemblerError(f"DN value out of 4-bit range: {val} (line {line_num+1})")
                    program.append(val)
                pc += len(args)
                continue
            elif opcode == "DB":
                for arg in args:
                    val = self._parse_val(arg, labels)
                    if not (0 <= val <= 255): 
                        raise AssemblerError(f"DB value out of 8-bit range: {val} (line {line_num+1})")
                    program.extend([(val >> 4) & 0x0F, val & 0x0F])
                pc += len(args) * 2
                continue

            # --- Base Opcodes (0-E) ---
            if opcode == "NOP":
                # NOP = JR +0 (E 0)
                program.extend([0xE, 0x0])
                pc += 2
            elif opcode == "LDI":
                if len(args) != 1: raise AssemblerError(f"LDI expects 1 argument (line {line_num+1})")
                val = self._parse_val(args[0], labels)
                if not (0 <= val <= 15): raise AssemblerError(f"Value out of 4-bit range (line {line_num+1})")
                program.extend([0x0, val])
                pc += 2
            elif opcode == "LDR":
                program.append(0x1)
                pc += 1
            elif opcode == "STR":
                program.append(0x2)
                pc += 1
            elif opcode == "RET":
                program.append(0x3)
                pc += 1
            elif opcode == "PHA":
                if args and args[0] != "A": raise AssemblerError(f"PUSH/PHA expects 'A' or no args (line {line_num+1})")
                program.append(0x4)
                pc += 1
            elif opcode == "PLA":
                if args and args[0] != "A": raise AssemblerError(f"POP/PLA expects 'A' or no args (line {line_num+1})")
                program.append(0x5)
                pc += 1
            elif opcode == "INX":
                program.append(0x6)
                pc += 1
            elif opcode == "DEX":
                program.append(0x7)
                pc += 1
            elif opcode == "INC":
                if args and args[0] != "A": raise AssemblerError(f"INC expects 'A' or no args (line {line_num+1})")
                program.append(0x8)
                pc += 1
            elif opcode == "DEC":
                if args and args[0] != "A": raise AssemblerError(f"DEC expects 'A' or no args (line {line_num+1})")
                program.append(0x9)
                pc += 1
            elif opcode == "MOV_A_B":
                program.append(0xA)
                pc += 1
            elif opcode == "MOV_B_A":
                program.append(0xB)
                pc += 1
            elif opcode in ("JZR", "JCR", "JR"):
                if len(args) != 1: raise AssemblerError(f"{opcode} expects 1 arg (line {line_num+1})")
                target = self._parse_val(args[0], labels)
                
                offset = target - (instr_pc + 2)
                if not (-8 <= offset <= 7):
                    raise AssemblerError(f"Relative jump '{opcode}' out of bounds [-8, +7]. Offset is {offset} (line {line_num+1})")
                
                disp4 = offset & 0x0F
                if opcode == "JZR": program.extend([0xC, disp4])
                elif opcode == "JCR": program.extend([0xD, disp4])
                elif opcode == "JR": program.extend([0xE, disp4])
                pc += 2

            # --- Extended Opcodes (Prefix F) ---
            elif opcode == "MOV_REG":
                dest, src = args[0], args[1]
                if dest == "A" and src in self.regs:
                    d, r = 0, self.regs[src]
                elif src == "A" and dest in self.regs:
                    d, r = 1, self.regs[dest]
                else:
                    raise AssemblerError(f"MOV must use A as source or dest (line {line_num+1})")
                program.extend([0xF, 0x0, (d << 3) | r])
                pc += 3
            elif opcode == "XCHG":
                program.extend([0xF, 0x1])
                pc += 2
            elif opcode in ("ADD", "SUB", "AND", "XOR"):
                if args and args[0] != "B": raise AssemblerError(f"{opcode} expects 'B' or no args (line {line_num+1})")
                subops = {"ADD": 0x2, "SUB": 0x3, "AND": 0x4, "XOR": 0x5}
                program.extend([0xF, subops[opcode]])
                pc += 2
            elif opcode == "LDRA":
                program.extend([0xF, 0x6])
                pc += 2
            elif opcode == "XBNK":
                program.extend([0xF, 0x7])
                pc += 2
            elif opcode == "LDP":
                if len(args) != 1: raise AssemblerError(f"LDP expects 1 arg (line {line_num+1})")
                addr = self._parse_val(args[0], labels)
                if not (0 <= addr <= 255): raise AssemblerError(f"Address out of 8-bit range (line {line_num+1})")
                program.extend([0xF, 0x8, (addr >> 4) & 0x0F, addr & 0x0F])
                pc += 4
            elif opcode == "BOOT":
                program.extend([0xF, 0x9])
                pc += 2
            elif opcode in ("JZ", "JC", "JMP", "CAL"):
                if len(args) != 1: raise AssemblerError(f"{opcode} expects 1 arg (line {line_num+1})")
                addr = self._parse_val(args[0], labels)
                if not (0 <= addr <= 255): raise AssemblerError(f"Address out of 8-bit range (line {line_num+1})")
                subops = {"JZ": 0xA, "JC": 0xB, "JMP": 0xC, "CAL": 0xD}
                program.extend([0xF, subops[opcode], (addr >> 4) & 0x0F, addr & 0x0F])
                pc += 4
            elif opcode == "HLT":
                program.extend([0xF, 0xF])
                pc += 2

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