# 保留站 Reservation Station
class RS:
    """
    Name: 名称，共9种类型，可见于下面初始化函数
    Timer: 执行指令时的计时器
    Busy: 保留站及其相关功能单元是否被占用
    Op: 对源操作数执行的运算
    Vj, Vk: 源操作数的值，Vk字段用于保存偏移量字段
    Qj, Qk: 将产生源寄存器值的保留站
    Dest: 目的寄存器
    inst_exec_time: 存储不同指令的执行时间
    """
    inst_exec_time = {
        "fld": 2 ,
        "fstp": 2 ,
        "fadd.d": 2 ,
        "fsub.d" : 2 ,
        "fmul.d" : 10 ,
        "fdiv.d" : 20
    }
    # 初始化
    def __init__(self):
        self.Name = ["Load1", "Load2", "Load3", "Store1", "Store2", "Store3", "Add1", "Add2", "Add3", "Mult1", "Mult2"]
        self.Timer = [0] * len(self.Name)
        self.Busy = ["No"] * len(self.Name)
        self.Op = [""] * len(self.Name)
        self.Vj, self.Vk = [""] * len(self.Name), [""] * len(self.Name)
        self.Qj, self.Qk = [""] * len(self.Name), [""] * len(self.Name)
        self.Dest = [""] * len(self.Name) 
        return

    # 计时器倒计时，并检查有没有刚好执行完毕的功能单元
    def Countdown(self):
        res = []
        for i in range(len(self.Name)):
            if self.Timer[i] > 0 and self.Busy[i] == "Yes":
                self.Timer[i] -= 1
                if self.Timer[i] == 0:
                    res.append(self.Name[i])
        return res
    
    # 清空指定的功能单元区
    def Clear(self, name:str):
        Index = self.Name.index(name)
        self.Busy[Index] = "No"
        self.Op[Index] = ""
        self.Vj[Index], self.Vk[Index], self.Qj[Index], self.Qk[Index], self.Dest[Index] = "", "", "", "", ""
        return

# 寄存器状态 FP Register Status
class FPRS:
    """
    Name: 名称, recorder or busy 
    Status: 寄存器f0-f10的状态，是一个2*11的二维列表，分别存储reorder和busy的信息
    Values: 寄存器的最终结果值
    """
    # 初始化
    def __init__(self):
        self.Names = ["F"+str(i) for i in range(11)]
        self.Status = [ [""] * 11, ["No"] * 11] 
        self.Values = [""] * 11
        return
     


# 重排序缓存 Reorder Buffer
class ROB:
    """
    Number: 指令数目, 假设ROB容量刚好等于指令集的指令条数
    Busy: 当前项目是否忙
    Instruction: 指令
    State: 指令状态
    Dest: 目的操作数
    Value: 值
    """
    # 初始化
    def __init__(self, N: int):
        # input: 
        #   N: 指令条数
        self.Number = N
        self.Busy = ["No"] * self.Number
        self.Instruction = [""] * self.Number
        self.State = [""] * self.Number
        self.Dest = [""] * self.Number
        self.Value = [""] * self.Number
        return

   