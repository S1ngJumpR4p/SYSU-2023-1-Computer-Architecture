
# instruction类: 对input1.txt和input2.txt的指令进行处理，提取指令的各个部分
class instruction:
    def __init__(self,Line: str,id: int):
        elements = Line.split(" ")
        self.ID = id    # 第几条指令
        self.text = Line    # 保留指令原文
        self.inst = elements[0] # 指令类型
        self.dest = elements[1] # 目的操作数
        self.src1 = elements[2] # 源操作数1
        self.src2 = elements[3] # 源操作数2

# inputProcessing: 对输入进行处理，读取txt文件，注意去除尾部的换行符，然后处理成instruction类型并记录下指令顺序(ID)
def inputProcessing(path: str):
    processed = []
    with open(path, 'r', encoding='utf-8') as f:
        Instructions = f.readlines()
        for i in range(len(Instructions)):
            instr = Instructions[i].replace("\n","")
            processed.append(instruction(instr,i+1))
        return processed