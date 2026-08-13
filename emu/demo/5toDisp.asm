LDP 0xF0 ;(Set pointer to Display 0 MMIO)
LDI 5
STR 	;(Output 5 to DISP_0)
BOOT ;(Software Reset back to Nano-Monitor at ROM[0x00])
