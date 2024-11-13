import os
import argparse

MemSize = 1000  # Memory size, though still 32-bit addressable

class InsMem(object):
    def __init__(self, name, ioDir):
        self.id = name
        with open(ioDir + "/Sample_Testcases_SS/input/testcase1/imem.txt") as im:
            self.IMem = [data.strip() for data in im.readlines()]

    def readInstr(self, ReadAddress):
        index = ReadAddress // 4 * 4  
        if index + 3 < len(self.IMem):
            instruction = self.IMem[index] + self.IMem[index + 1] + self.IMem[index + 2] + self.IMem[index + 3]
            return hex(int(instruction, 2))
        else:
            return None 
        

class DataMem(object):
    def __init__(self, name, ioDir):
        self.id = name
        self.ioDir = ioDir
        with open(ioDir + "/Sample_Testcases_SS/input/testcase1/dmem.txt") as dm:
            self.DMem = [data.strip() for data in dm.readlines()]

    def ensure_memory_size(self, min_size):
        if min_size > len(self.DMem):
            self.DMem.extend(['00000000'] * (min_size - len(self.DMem)))

    def readInstr(self, ReadAddress):
        index = ReadAddress // 4 * 4  
        self.ensure_memory_size(index + 4)  
        data_word = self.DMem[index] + self.DMem[index + 1] + self.DMem[index + 2] + self.DMem[index + 3]
        return hex(int(data_word, 2))

    def writeDataMem(self, Address, WriteData):
        index = Address // 4 * 4  
        self.ensure_memory_size(index + 4)  # Ensure memory is large enough
        data_word = format(WriteData, '032b')
        self.DMem[index] = data_word[0:8]
        self.DMem[index + 1] = data_word[8:16]
        self.DMem[index + 2] = data_word[16:24]
        self.DMem[index + 3] = data_word[24:32]

    def outputDataMem(self):
        resPath = self.ioDir + "/" + self.id + "_DMEMResult.txt"
        with open(resPath, "w") as rp:
            rp.writelines([str(data) + "\n" for data in self.DMem])


class RegisterFile(object):
    def __init__(self, ioDir):
        self.outputFile = ioDir + "/RFResult.txt"
        self.Registers = [0x0 for i in range(32)]  
    
    def readRF(self, Reg_addr):
        if 0 <= Reg_addr < 32:
            return self.Registers[Reg_addr]
        else:
            raise IndexError("Register address out of bounds")

    def writeRF(self, Reg_addr, Wrt_reg_data):
        if 1 <= Reg_addr < 32:  # Register x0 must always remain 0
            self.Registers[Reg_addr] = Wrt_reg_data
    
    def outputRF(self, cycle):
        op = ["-" * 70 + "\n", "State of RF after executing cycle:" + str(cycle) + "\n"]
        op.extend([f"{val & 0xFFFFFFFF:032b}\n" for val in self.Registers])  # Mask and format each register value as a 32-bit binary string
        perm = "w" if cycle == 0 else "a"
        with open(self.outputFile, perm) as file:
            file.writelines(op)


class State(object):
    def __init__(self):
        self.IF = {"nop": False, "PC": 0}
        self.ID = {"nop": False, "Instr": 0}
        self.EX = {"nop": False, "Read_data1": 0, "Read_data2": 0, "Imm": 0, "Rs": 0, "Rt": 0, "Wrt_reg_addr": 0, "is_I_type": False, "rd_mem": 0, 
                   "wrt_mem": 0, "alu_op": 0, "wrt_enable": 0, "branch": False}
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
        self.instructionCount = 0


class SingleStageCore(Core):
    def __init__(self, ioDir, imem, dmem):
        super(SingleStageCore, self).__init__(ioDir, imem, dmem)
        self.opFilePath = os.path.join(ioDir,  "StateResult_SS.txt")
        self.instructionCount = 0

    def IF(self):
        self.state.ID["Instr"] = self.ext_imem.readInstr(self.state.IF["PC"])
        if self.state.ID["Instr"] is not None:
            opcode = self.state.ID["Instr"][-7:]  
            
            if opcode == "1111111":  # nop instruction
                self.nextState.IF["PC"] = self.state.IF["PC"]
                self.nextState.IF["nop"] = True

            else:
                self.nextState.IF["nop"] = False
                self.nextState.IF["PC"] = self.state.IF["PC"] + 4;
                self.state.ID["nop"] = False  
                self.instructionCount += 1 

        else:
            self.state.IF["nop"] = True  

            
    def ID(self):
        instruction = self.state.ID["Instr"]
        if instruction is None:
            self.halted = True
            return
        
        instruction = int(instruction, 16) if isinstance(instruction, str) else instruction
        opcode = instruction & 0x7F
        self.state.ID["Instr"] = instruction  

        # rs --> rs1, rt --> rs2
        if opcode == 0x33:  
            funct3 = (instruction >> 12) & 0x7
            funct7 = (instruction >> 25) & 0x7F
            rd = (instruction >> 7) & 0x1F
            rs1 = (instruction >> 15) & 0x1F
            rs2 = (instruction >> 20) & 0x1F
            self.state.EX["Read_data1"] = self.myRF.readRF(rs1)  
            self.state.EX["Read_data2"] = self.myRF.readRF(rs2)  
            self.state.EX["Imm"] = 0  
            self.state.EX["Rs"] = rs1
            self.state.EX["Rt"] = rs2
            self.state.EX["Wrt_reg_addr"] = rd  
            self.state.EX["rd_mem"] = False
            self.state.EX["wrt_mem"] = False
            self.state.EX["is_I_type"] = False 

            ALUmapping = {
                0: "0010",  # ADD
                4: "0011",  # XOR
                6: "0001",  # OR
                7: "0000",  # AND
            }

            if funct3 == 0: 
                if funct7 == 0x00:
                    self.state.EX["alu_op"] = "0010"  # ADD
                elif funct7 == 0x20:
                    self.state.EX["alu_op"] = "0110"  # SUB
            else:
                self.state.EX["alu_op"] = ALUmapping[funct3]  

            self.state.EX["wrt_enable"] = True
       
            
        
        elif opcode == 0x13:  # I-type instructions (e.g., ADDI, XORI, ORI, ANDI)
            funct3 = (instruction >> 12) & 0x7
            rd = (instruction >> 7) & 0x1F
            rs1 = (instruction >> 15) & 0x1F
            imm = (instruction >> 20) & 0xFFF  

            # Sign-extend the immediate value
            if imm & 0x800:  
                imm |= 0xFFFFF000  

            self.state.EX["Wrt_reg_addr"] = rd
            self.state.EX["Rs"] = rs1
            self.state.EX["Read_data1"] = self.myRF.readRF(rs1)  
            self.state.EX["Read_data2"] = 0
            self.state.EX["Rt"] = 0
            self.state.EX["Imm"] = imm  
            self.state.EX["rd_mem"] = False
            self.state.EX["wrt_mem"] = False
            self.state.EX["is_I_type"] = True  
            self.state.EX["wrt_enable"] = True

            ALUmapping = {
                0x0: "0010",  # ADDI
                0x4: "0011",  # XORI
                0x6: "0001",  # ORI
                0x7: "0000",  # ANDI
            }

            self.state.EX["alu_op"] = ALUmapping[funct3]  

      
        elif opcode == 0x03:  # LOAD instructions (I-type)
            funct3 = (instruction >> 12) & 0x7 
            rd = (instruction >> 7) & 0x1F  
            rs1 = (instruction >> 15) & 0x1F  
            imm = (instruction >> 20) & 0xFFF  

            if imm & 0x800:  
                imm |= 0xFFFFF000  

            self.state.EX["Wrt_reg_addr"] = rd
            self.state.EX["Rs"] = rs1
            self.state.EX["Read_data1"] = self.myRF.readRF(rs1)  
            self.state.EX["Read_data2"] = 0
            self.state.EX["Rt"] = 0
            self.state.EX["Imm"] = imm  
            self.state.EX["rd_mem"] = True  
            self.state.EX["wrt_mem"] = False
            self.state.EX["is_I_type"] = True 
            
            ALUmapping = {
                "0000": "0010",  # ADD
                "0001": "0110",  # SUB
                "1110": "0000",  # AND
                "1100": "0001",  # OR
                "1000": "0011",  # XOR
            }
            
            self.state.EX["wrt_enable"] = True
            self.state.EX["alu_op"] = ALUmapping[format(funct3, '04b')]  

        
        elif opcode == 0x6F:  # JAL instruction
            rd = (instruction >> 7) & 0x1F
            imm = ((instruction & 0x80000000) >> 11) | \
                ((instruction & 0x7E000000) >> 20) | \
                ((instruction & 0x100000) >> 9) | \
                ((instruction & 0xFF000))
            #
            if imm & 0x80000:  
                imm |= 0xFFF00000        
         
            self.instructionCount += 1
            self.state.EX["funct3"] = "111"
            self.state.EX["Wrt_reg_addr"] = rd
            self.state.EX["Read_data1"] = 0
            self.state.EX["Read_data2"] = 0
            self.state.EX["Imm"] = imm
            self.state.EX["rd_mem"] = False
            self.state.EX["wrt_mem"] = False
            self.state.EX["is_I_type"] = False
            self.state.EX["wrt_enable"] = True
            self.state.EX["branch"] = True
            self.state.EX["alu_op"] = "0010"  
        

        elif opcode == 0x63:  # B-type instructions
            funct3 = (instruction >> 12) & 0x7
            rs1 = (instruction >> 15) & 0x1F
            rs2 = (instruction >> 20) & 0x1F
            
            imm = ((instruction & 0x80000000) >> 19) | \
                ((instruction & 0x80) << 4) | \
                ((instruction & 0x7E000000) >> 20) | \
                ((instruction & 0xF00) >> 7)
            # Sign-extend the immediate value
            if imm & 0x1000:  
                imm |= 0xFFFFE000  

            read_data1 = self.myRF.readRF(rs1)
            read_data2 = self.myRF.readRF(rs2)

            self.state.EX["funct3"] = funct3
            self.state.EX["Wrt_reg_addr"] = 0
            self.state.EX["Rs"] = rs1
            self.state.EX["Read_data1"] = read_data1
            self.state.EX["Rt"] = rs2
            self.state.EX["Read_data2"] = read_data2
            self.state.EX["Imm"] = imm
            self.state.EX["rd_mem"] = False
            self.state.EX["wrt_mem"] = False
            self.state.EX["is_I_type"] = False
            self.state.EX["wrt_enable"] = False
            self.state.EX["branch"] = True
            self.state.EX["alu_op"] = "0110"  

        elif opcode == 0x23:  
            funct3 = (instruction >> 12) & 0x7
            rs1 = (instruction >> 15) & 0x1F
            rs2 = (instruction >> 20) & 0x1F
       
            imm = ((instruction & 0xFE000000) >> 20) | \
                ((instruction & 0xF80) >> 7)
           
            if imm & 0x800: 
                imm |= 0xFFFFF000  

            read_data1 = self.myRF.readRF(rs1)
            read_data2 = self.myRF.readRF(rs2)

            self.state.EX["funct3"] = funct3
            self.state.EX["Wrt_reg_addr"] = 0
            self.state.EX["Rs"] = rs1
            self.state.EX["Read_data1"] = read_data1
            self.state.EX["Rt"] = rs2
            self.state.EX["Read_data2"] = read_data2
            self.state.EX["Imm"] = imm
            self.state.EX["rd_mem"] = False
            self.state.EX["wrt_mem"] = True
            self.state.EX["is_I_type"] = True
            self.state.EX["wrt_enable"] = False
            self.state.EX["alu_op"] = "0010" 


    def EX(self):
        if not self.state.EX["nop"]:
            if self.state.EX["is_I_type"]:
                ALU2 = self.state.EX["Imm"] if self.state.EX["Imm"] < 0x8000 else self.state.EX["Imm"] - 0x10000
            else:
                ALU2 = self.state.EX["Read_data2"]
            
            if self.state.EX["alu_op"] == "0010":  # ADD or ADDI
                self.state.MEM["ALUresult"] = self.state.EX["Read_data1"] + ALU2
            elif self.state.EX["alu_op"] == "0110":  # SUB
                self.state.MEM["ALUresult"] = self.state.EX["Read_data1"] - ALU2
            elif self.state.EX["alu_op"] == "0000":  # AND or ANDI
                self.state.MEM["ALUresult"] = self.state.EX["Read_data1"] & ALU2
            elif self.state.EX["alu_op"] == "0001":  # OR or ORI
                self.state.MEM["ALUresult"] = self.state.EX["Read_data1"] | ALU2
            elif self.state.EX["alu_op"] == "0011":  # XOR or XORI
                self.state.MEM["ALUresult"] = self.state.EX["Read_data1"] ^ ALU2

            if self.state.EX["branch"]:
                if self.state.EX["funct3"] == 0x0 and self.state.MEM["ALUresult"] == 0:  # beq
                    self.nextState.IF["PC"] = self.state.IF["PC"] + self.state.EX["Imm"]
                    self.nextState.IF["nop"] = False
                    self.state.MEM["nop"] = True
                elif self.state.EX["funct3"] == 0x1 and self.state.MEM["ALUresult"] != 0:  # bne
                    self.nextState.IF["PC"] = self.state.IF["PC"] + self.state.EX["Imm"]
                    self.nextState.IF["nop"] = False
                    self.state.MEM["nop"] = True
                elif self.state.EX["funct3"] == 0x7: 
                    self.nextState.IF["nop"] = False
                    self.state.MEM["ALUresult"] = self.state.IF["PC"] + 4
                    self.nextState.IF["PC"] = self.state.IF["PC"] + self.state.EX["Imm"]


            self.state.MEM["rd_mem"] = self.state.EX["rd_mem"]
            self.state.MEM["wrt_mem"] = self.state.EX["wrt_mem"]

    
    def MEM(self):
        self.state.WB["nop"] = self.state.MEM["nop"]
        if not self.state.MEM["nop"]:
            if self.state.MEM["rd_mem"]:
                self.state.MEM["Store_data"] = self.ext_dmem.readInstr(self.state.MEM["ALUresult"])
            
            if self.state.MEM["wrt_mem"]:
                self.ext_dmem.writeDataMem(self.state.MEM["ALUresult"], self.state.EX["Read_data2"])

            self.state.WB["ALUresult"] = self.state.MEM["ALUresult"]  # Ensure ALU result is passed to WB stage

            self.state.MEM["Wrt_reg_addr"] = self.state.EX["Wrt_reg_addr"]
            self.state.WB["Wrt_reg_addr"] = self.state.MEM["Wrt_reg_addr"]
            self.state.WB["wrt_enable"] = self.state.EX["wrt_enable"]
        else:
            self.state.WB["nop"] = True



    def WB(self):
        if not self.state.WB["nop"] and self.state.WB["wrt_enable"]:
            if self.state.EX["rd_mem"]:
               
                store_data_value = int(self.state.MEM["Store_data"], 16)
                self.myRF.writeRF(self.state.WB["Wrt_reg_addr"], store_data_value)
            else:
                self.myRF.writeRF(self.state.WB["Wrt_reg_addr"], self.state.MEM["ALUresult"])


    def step(self):
        self.IF()
        self.ID()
        self.EX()
        self.MEM()
        self.WB()


        if self.state.IF["nop"]:
            self.halted = True
            self.report_performance_metrics()
    
        # Dump RF and print state
        self.myRF.outputRF(self.cycle)  # Dump Register File
        self.printState(self.nextState, self.cycle)  # Print states after executing the cycle
        
        # Prepare for the next cycle
        self.state = self.nextState  # Update the current state
        self.cycle += 1

    def report_performance_metrics(self):
        total_cycles = self.cycle
        total_instructions = self.instructionCount
        average_cpi = total_cycles / total_instructions if total_instructions > 0 else 0
        ipc = total_instructions / total_cycles if total_cycles > 0 else 0

        print(f"Total Execution Cycles: {total_cycles}")
        print(f"Total Instructions Executed: {total_instructions}")
        print(f"Average CPI: {average_cpi:.2f}")
        print(f"Instructions Per Cycle (IPC): {ipc:.2f}")


    def printState(self, state, cycle):
        printstate = ["-"*70 + "\n", "State after executing cycle: " + str(cycle) + "\n"]
        printstate.append("IF.PC: " + str(state.IF["PC"]) + "\n")
        printstate.append("IF.nop: " + str(state.IF["nop"]) + "\n")
        
        perm = "w" if cycle == 0 else "a"
        with open(self.opFilePath, perm) as wf:
            wf.writelines(printstate)

        

if __name__ == "__main__":
     
    #parse arguments for input file location
    parser = argparse.ArgumentParser(description='RV32I processor')
    parser.add_argument('--iodir', default="", type=str, help='Directory containing the input files.')
    args = parser.parse_args()

    ioDir = os.path.abspath(args.iodir)
    print("IO Directory:", ioDir)

    imem = InsMem("Imem", ioDir)
    dmem_ss = DataMem("SS", ioDir)
    dmem_fs = DataMem("FS", ioDir)
    
    ssCore = SingleStageCore(ioDir, imem, dmem_ss)
    # fsCore = FiveStageCore(ioDir, imem, dmem_fs)


    while(True):
        if not ssCore.halted:
            ssCore.step()
        
        # if not fsCore.halted:
        #     fsCore.step()

        # if ssCore.halted and fsCore.halted:
        #     break

        if ssCore.halted:
            break
    
    # dump SS and FS data mem.
    dmem_ss.outputDataMem()
    # dmem_fs.outputDataMem()




