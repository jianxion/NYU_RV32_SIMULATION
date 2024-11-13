import os
import argparse

MemSize = 1000  # Memory size, though still 32-bit addressable

class InsMem(object):
    def __init__(self, name, ioDir):
        self.id = name
        with open(ioDir + "/input/imem.txt") as im:
            # Read the instruction memory file and store it as 8-bit binary strings
            self.IMem = [data.strip() for data in im.readlines()]

    def readInstr(self, ReadAddress):
        # Convert the byte address to an index for 32-bit instruction (4 bytes per instruction)
        index = ReadAddress // 4 * 4  # Ensure the address is aligned to 4 bytes

        # Check if the address is within bounds
        if index + 3 < len(self.IMem):
            # Concatenate four 8-bit lines to create a 32-bit instruction
            instruction = self.IMem[index] + self.IMem[index + 1] + self.IMem[index + 2] + self.IMem[index + 3]
            # Convert the 32-bit binary string to a hexadecimal value
            return hex(int(instruction, 2))
        else:
            return None  # Return None if the address is out of range

        
# ioDir = "/Users/jianxiongshen/Downloads/ECE6913ComputerArchitecture/project_related"  # Replace with the actual path to the folder containing 'input/imem.txt'
# instruction_memory = InsMem("IMem_Instance", ioDir)

# # Address is a multiple of 4 (e.g., 0, 4, 8, etc.)
# print(instruction_memory.readInstr(8) )
# instruction_memory.readInstr(16) 

class DataMem(object):
    def __init__(self, name, ioDir):
        self.id = name
        self.ioDir = ioDir
        with open(ioDir + "/input/dmem.txt") as dm:
            # Read the data memory file and store each line as an 8-bit binary string
            self.DMem = [data.strip() for data in dm.readlines()]

    def readInstr(self, ReadAddress):
        # Convert the byte address to an index for 32-bit word access (each word is 4 bytes)
        index = ReadAddress // 4 * 4  # Ensure the address is aligned to 4 bytes

        # Check if the address is within bounds
        if index + 3 < len(self.DMem):
            # Concatenate four 8-bit lines to create a 32-bit data word
            data_word = self.DMem[index] + self.DMem[index + 1] + self.DMem[index + 2] + self.DMem[index + 3]
            # Convert the 32-bit binary string to a hexadecimal value
            return hex(int(data_word, 2))
        else:
            return None  # Return None if the address is out of range

    def writeDataMem(self, Address, WriteData):
        # Convert the byte address to an index for word access (each word is 4 bytes)
        index = Address // 4 * 4  # Ensure the address is aligned to 4 bytes

        if index + 3 < len(self.DMem):
            # Convert WriteData to a 32-bit binary string with leading zeros
            data_word = format(WriteData, '032b')

            # Split the 32-bit binary data into four 8-bit segments
            self.DMem[index] = data_word[0:8]
            self.DMem[index + 1] = data_word[8:16]
            self.DMem[index + 2] = data_word[16:24]
            self.DMem[index + 3] = data_word[24:32]
        else:
            raise IndexError("Address out of memory range")

    def outputDataMem(self):
        # Write the content of the data memory to the output file
        resPath = self.ioDir + "/" + self.id + "_DMEMResult.txt"
        with open(resPath, "w") as rp:
            rp.writelines([str(data) + "\n" for data in self.DMem])

ioDir = "/Users/jianxiongshen/Downloads/ECE6913ComputerArchitecture/project_related"  # Replace with the actual path to the folder containing 'input/imem.txt' # Your project directory
dmem = DataMem("Data", ioDir)


# Read first word (4 bytes starting at address 0)
word0 = dmem.readInstr(0)
print(f"Word at address 0: {word0}")  # Output: 0x1020304

# Read second word (4 bytes starting at address 4)
word1 = dmem.readInstr(4)
print(f"Word at address 4: {word1}")  # Output: 0xaaf0ff

# Example 2: Writing data
# Write value 0x12345678 to address 0
dmem.writeDataMem(0, 0x12345678)

# Read back the written value
updated_word = dmem.readInstr(0)
print(f"Updated word at address 0: {updated_word}")  # Output: 0x12345678

# Example 3: Output memory contents to file
dmem.outputDataMem()  # Creates Data_DMEMResult.txt with the current memory contents






class RegisterFile(object):
    def __init__(self, ioDir):
        self.outputFile = ioDir + "\\RFResult.txt"
        self.Registers = [0x0 for i in range(32)]

    def readRF(self, Reg_addr):
        # Return the value at the register address if within range
        if 0 <= Reg_addr < 32:
            return self.Registers[Reg_addr]
        else:
            raise IndexError("Register address out of range")

    def writeRF(self, Reg_addr, Wrt_reg_data):
        # Write the data to the register address if it's within range and not x0
        if 0 < Reg_addr < 32:
            self.Registers[Reg_addr] = Wrt_reg_data

    def outputRF(self, cycle):
        op = ["-"*70 + "\n", "State of RF after executing cycle:" + str(cycle) + "\n"]
        op.extend([str(val) + "\n" for val in self.Registers])
        perm = "w" if cycle == 0 else "a"
        with open(self.outputFile, perm) as file:
            file.writelines(op)

class State(object):
    def __init__(self):
        self.IF = {"nop": False, "PC": 0}
        self.ID = {"nop": False, "Instr": 0}
        self.EX = {"nop": False, "Read_data1": 0, "Read_data2": 0, "Imm": 0, "Rs": 0, "Rt": 0, "Wrt_reg_addr": 0, "is_I_type": False, "rd_mem": 0, 
                   "wrt_mem": 0, "alu_op": 0, "wrt_enable": 0}
        self.MEM = {"nop": False, "ALUresult": 0, "Store_data": 0, "Rs": 0, "Rt": 0, "Wrt_reg_addr": 0, "rd_mem": 0, 
                   "wrt_mem": 0, "wrt_enable": 0}
        self.WB = {"nop": False, "Wrt_data": 0, "Rs": 0, "Rt": 0, "Wrt_reg_addr": 0, "wrt_enable": 0}

class Core(object):
    def __init__(self, ioDir, imem, dmem):
        self.myRF = RegisterFile(ioDir)
        self.cycle = 0
        self.halted = False
        self.ioDir = ioDir
        self.state = State()
        self.nextState = State()
        self.ext_imem = imem
        self.ext_dmem = dmem

class SingleStageCore(Core):
    def __init__(self, ioDir, imem, dmem):
        super(SingleStageCore, self).__init__(ioDir + "\\SS_", imem, dmem)
        self.opFilePath = ioDir + "\\StateResult_SS.txt"

    def step(self):
        # For the SingleStageCore implementation, execute one cycle
        self.halted = True
        if self.state.IF["nop"]:
            self.halted = True
            
        self.myRF.outputRF(self.cycle)  # dump RF
        self.printState(self.nextState, self.cycle)  # print states after executing cycle
        
        self.state = self.nextState  # Update the current state
        self.cycle += 1

    def printState(self, state, cycle):
        printstate = ["-"*70 + "\n", "State after executing cycle: " + str(cycle) + "\n"]
        printstate.append("IF.PC: " + str(state.IF["PC"]) + "\n")
        printstate.append("IF.nop: " + str(state.IF["nop"]) + "\n")
        
        perm = "w" if cycle == 0 else "a"
        with open(self.opFilePath, perm) as wf:
            wf.writelines(printstate)


# class FiveStageCore(Core):
#     def __init__(self, ioDir, imem, dmem):
#         super(FiveStageCore, self).__init__(ioDir + "\\FS_", imem, dmem)
#         self.opFilePath = ioDir + "\\StateResult_FS.txt"

#     def step(self):
#         # Your implementation
#         # --------------------- WB stage ---------------------
        
        
        
#         # --------------------- MEM stage --------------------
        
        
        
#         # --------------------- EX stage ---------------------
        
        
        
#         # --------------------- ID stage ---------------------
        
        
        
#         # --------------------- IF stage ---------------------
        
#         self.halted = True
#         if self.state.IF["nop"] and self.state.ID["nop"] and self.state.EX["nop"] and self.state.MEM["nop"] and self.state.WB["nop"]:
#             self.halted = True
        
#         self.myRF.outputRF(self.cycle) # dump RF
#         self.printState(self.nextState, self.cycle) # print states after executing cycle 0, cycle 1, cycle 2 ... 
        
#         self.state = self.nextState #The end of the cycle and updates the current state with the values calculated in this cycle
#         self.cycle += 1

#     def printState(self, state, cycle):
#         printstate = ["-"*70+"\n", "State after executing cycle: " + str(cycle) + "\n"]
#         printstate.extend(["IF." + key + ": " + str(val) + "\n" for key, val in state.IF.items()])
#         printstate.extend(["ID." + key + ": " + str(val) + "\n" for key, val in state.ID.items()])
#         printstate.extend(["EX." + key + ": " + str(val) + "\n" for key, val in state.EX.items()])
#         printstate.extend(["MEM." + key + ": " + str(val) + "\n" for key, val in state.MEM.items()])
#         printstate.extend(["WB." + key + ": " + str(val) + "\n" for key, val in state.WB.items()])

#         if(cycle == 0): perm = "w"
#         else: perm = "a"
#         with open(self.opFilePath, perm) as wf:
#             wf.writelines(printstate)

# if __name__ == "__main__":
     
#     #parse arguments for input file location
#     parser = argparse.ArgumentParser(description='RV32I processor')
#     parser.add_argument('--iodir', default="", type=str, help='Directory containing the input files.')
#     args = parser.parse_args()

#     ioDir = os.path.abspath(args.iodir)
#     print("IO Directory:", ioDir)

#     imem = InsMem("Imem", ioDir)
#     dmem_ss = DataMem("SS", ioDir)
#     dmem_fs = DataMem("FS", ioDir)
    
#     ssCore = SingleStageCore(ioDir, imem, dmem_ss)
#     fsCore = FiveStageCore(ioDir, imem, dmem_fs)

#     while(True):
#         if not ssCore.halted:
#             ssCore.step()
        
#         if not fsCore.halted:
#             fsCore.step()

#         if ssCore.halted and fsCore.halted:
#             break
    
#     # dump SS and FS data mem.
#     dmem_ss.outputDataMem()
#     dmem_fs.outputDataMem()