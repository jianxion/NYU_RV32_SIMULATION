from NYU_RV32I_6913 import DataMem

def test_data_mem():
    # Initialize DataMem object
    ioDir = "/Users/jianxiongshen/Downloads/ECE6913ComputerArchitecture/project_related"
    data_mem = DataMem("TestMem", ioDir)

    # Write data to memory
    print("Writing data to memory:")
    data_mem.writeDataMem(0, 0x56565678)
    data_mem.writeDataMem(4, "0xABCDEF01")
    data_mem.writeDataMem(8, 0x12233456)
    data_mem.writeDataMem(12, 0x00000090)

    print("\nReading data from memory:")
    # Read data from memory
    for address in range(0, 16, 4):
        data = data_mem.readInstr(address)
        print(f"Data at address 0x{address:08X}: {data}")

    # Output the final state of memory to a file
    data_mem.outputDataMem()
    print("\nMemory state has been written to file.")

if __name__ == "__main__":
    test_data_mem()