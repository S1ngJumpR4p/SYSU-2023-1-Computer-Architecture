import Process
import Hardware_Structure

# 识别指令应该进入保留站的哪一个功能单元如load1、add2、mult1以及源操作数是寄存器类型还是常量
def Recognize(instr: Process.instruction):
    # 源操作数如果是常量，首个字符是数字，若是寄存器则首个字符是英文(即非数字)
    Src1Type = "constant" if instr.src1[0].isdigit() else "register"
    Src2Type = "constant" if instr.src2[0].isdigit() else "register"
    Itype = str()   # 划分到的功能单元
    Ioperation = str()  # 具体的浮点汇编指令操作如fld(load)、fstp(store)、fadd.d(add)等
    if instr.inst == "LD":    
        Itype = "Load"  # LD和会使用保留站中的"Load"功能单元
        Ioperation = "fld"
    elif instr.inst == "SD":
        Itype = "Store" # SD会使用保留站中的"Store"功能单元
        Ioperation = "fstp"
    elif instr.inst == "ADDD" or instr.inst == "SUBD":  
        Itype = "Add"   # ADDD和SUBD会使用保留站中的"Add"功能单元
        Ioperation = "fadd.d" if instr.inst == "ADDD" else "fsub.d"
    elif instr.inst == "MULTD" or instr.inst == "DIVD": 
        Itype = "Mult"  # MULTD和DIVD会使用保留站中的"Mult"功能单元
        Ioperation = "fmul.d" if instr.inst == "MULTD" else "fdiv.d"
    
    return Itype, Ioperation, Src1Type, Src2Type

# 判断指令是否可以发射: 
# 指令发送阶段，需要ROB和RS中都有空位且当前指令的目的寄存器与先前指令的目的寄存器相同但是先前指令已经提交时才能发射指令
def issue_available(instr: Process.instruction, rs: Hardware_Structure.RS, rob: Hardware_Structure.ROB,fprs:Hardware_Structure.FPRS):
    rob_available, rs_available, fprs_available = False, False , False 
    for i in range(rob.Number):
        if rob.Instruction[i] == "":
            rob_available = True
            break
    fpid = fprs.Names.index(instr.dest)
    if fprs.Status[0][fpid] == "":  # 第一次放入fprs中，"大胆放"
        fprs_available = True
    else:   # 与此前的指令有相同的目的寄存器，若该此前指令已经提交，"大胆放"
        if fprs.Status[1][fpid] == "No":
            fprs_available = True
    Itype, _, _, _ = Recognize(instr)
    if Itype == "Load":
        start = rs.Name.index("Load1")
        
        for i in range(start, start + 3):   # 在Load1到Load3里面寻找可用的功能单元
            if rs.Busy[i] == "No" and rs.Op[i] == "":
                rs_available = True
                break
    elif Itype == "Store":
        start = rs.Name.index("Store1")
        for i in range(start, start + 3):   # 在Store1到Store3里面寻找可用的功能单元
            if rs.Busy[i] == "No" and rs.Op[i] == "":
                rs_available = True
                break
    elif Itype == "Add":
        start = rs.Name.index("Add1")
        for i in range(start, start + 3):   # 在Add1到Add3里面寻找可用的功能单元
            if rs.Busy[i] == "No" and rs.Op[i] == "":
                rs_available = True
                break
    else:   # Itype: Mult
        start = rs.Name.index("Mult1")
        for i in range(start, start + 2):   # 在Mult1到Mult2里面寻找可用的功能单元
            if rs.Busy[i] == "No" and rs.Op[i] == "":
                rs_available = True
                break
    return rob_available and rs_available and fprs_available  # 只有在ROB、FPRS还有RS中都满足可发射条件时才可以发射

def issue(instr: Process.instruction, rs: Hardware_Structure.RS, rob: Hardware_Structure.ROB, fprs: Hardware_Structure.FPRS):
    """
    input:
        instr: 处理好的指令
        rs: 保留站
        rob: 重排序缓存
        fprs: 寄存器状态
    output:
        指令ID(成功) 或 -1(发射失败)
        所在功能单元区
    """
    Itype, Ioperation, _, _ = Recognize(instr)
    if Itype == "Load": # Load指令
        start = rs.Name.index("Load1")  # 记录第一个Load功能单元的索引
        for i in range(start, start+3): # 寻找可用的Load功能单元
            if rs.Busy[i] == "No" and rs.Op[i] == "":
                # 写RS
                rs.Busy[i] = "Yes"
                rs.Op[i] = Ioperation
                rs.Vj[i] = instr.src1.replace("+","")
                rs.Vk[i] = "Regs["+instr.src2+"]"
                rs.Dest[i] = "#"+str(instr.ID)
                
                # 写ROB
                rob.Busy[instr.ID-1] = "Yes"
                rob.Instruction[instr.ID-1] = instr.text
                rob.State[instr.ID-1] = "Issue"
                rob.Dest[instr.ID-1] = instr.dest
                rob.Value[instr.ID-1] = "Mem["
                rob.Value[instr.ID-1] += "" if instr.src1=="0" else instr.src1
                rob.Value[instr.ID-1] += rs.Vk[i] + "]"

                # 写FP RS
                fp_id = fprs.Names.index(instr.dest)
                fprs.Status[0][fp_id] = str(instr.ID)
                fprs.Status[1][fp_id] = "Yes"
                return instr.ID, rs.Name[i]
            
    elif Itype == "Add":    # Add或Sub指令
        start = rs.Name.index("Add1")   # 记录第一个Add功能单元的索引
        for i in range(start,start+3):  # 寻找可用的Add功能单元
            if rs.Busy[i] == "No" and rs.Op[i] == "":
                # 写RS
                rs.Busy[i] = "Yes"
                rs.Op[i] = Ioperation
                rs.Dest[i] = "#"+str(instr.ID)

                # 对于Add/Sub指令的源操作数，要注意对应的寄存器是否已经写回即其值是否被修改过
                fp_id1, fp_id2 = fprs.Names.index(instr.src1), fprs.Names.index(instr.src2) # 两个源操作数在fprs中的索引
                if fprs.Status[1][fp_id1] == "Yes":  # fprs中对应busy项为"Yes"，说明还未写回
                    rs.Qj[i] = "#"+fprs.Status[0][fp_id1]   # 将其赋值为:"#"+该寄存器的reorder值，注意对Q赋值而不是V
                else:   
                    # fprs中对应的busy项为"No"
                    rs.Vj[i] = "Regs["+instr.src1+"]"
                
                # 另一个操作数同理
                if fprs.Status[1][fp_id2] == "Yes":
                    rs.Qk[i] = "#"+fprs.Status[0][fp_id2]
                else:   
                    # fprs中对应的busy项为"No"
                    rs.Vk[i] = "Regs["+instr.src1+"]"
               
                # 写ROB
                rob.Busy[instr.ID-1] = "Yes"
                rob.Instruction[instr.ID-1] = instr.text
                rob.State[instr.ID-1] = "Issue"
                rob.Dest[instr.ID-1] = instr.dest
                ele1, ele2 = "", "" # ROB的Value项涉及到的两个操作数
                for j in range(instr.ID-1): # 遍历前面已经发射的指令，看看这两个源操作数是不是前面的指令的结果
                    # 如果是，则记为"#"+指令编号
                    if rob.Dest[j] == instr.src1:
                        ele1 = "#"+str(j+1) # 这里不能直接break，因为有些寄存器在前面可能不止被写过一次
                    if rob.Dest[j] == instr.src2:
                        ele2 = "#"+str(j+1) # 同理
                if ele1 == "":  # 还为""说明前面没有指令会动它，则直接Regs[寄存器]读取它的值即可
                    ele1 = "Regs["+instr.src1+"]"
                if ele2 == "":  # 另一个操作数同理
                    ele2 = "Regs["+instr.src2+"]"
                if Ioperation == "fadd.d":  # 注意是add还是sub
                    rob.Value[instr.ID-1] = ele1+"+"+ele2
                else:   # Ioperation: "fsub.d"
                    rob.Value[instr.ID-1] = ele1+"-"+ele2

                # 写FPRS
                fp_id = fprs.Names.index(instr.dest)
                fprs.Status[0][fp_id] = str(instr.ID)
                fprs.Status[1][fp_id] = "Yes"
                return instr.ID, rs.Name[i]

    elif Itype == "Mult":
        start = rs.Name.index("Mult1")
        for i in range(start,start+2):
            if rs.Busy[i] == "No" and rs.Op[i] == "":
                # 写RS
                rs.Busy[i] = "Yes"
                rs.Op[i] = Ioperation
                rs.Dest[i] = "#"+str(instr.ID)

                # 对于Mult/Div指令的源操作数，要注意对应的寄存器是否已经写回即其值是否被修改过
                fp_id1, fp_id2 = fprs.Names.index(instr.src1), fprs.Names.index(instr.src2) # 两个源操作数在fprs中的索引
                if fprs.Status[1][fp_id1] == "Yes":  # fprs中对应busy项为"Yes"，说明还未写回
                    rs.Qj[i] = "#"+fprs.Status[0][fp_id1]   # 将其赋值为:"#"+该寄存器的reorder值，注意对Q赋值而不是V
                else:   
                    # fprs中对应的busy项为"No"
                    rs.Vj[i] = "Regs["+instr.src1+"]"
                
                # 另一个操作数同理
                if fprs.Status[1][fp_id2] == "Yes":
                    rs.Qk[i] = "#"+fprs.Status[0][fp_id2]
                else:   
                    # fprs中对应的busy项为"No"
                    rs.Vk[i] = "Regs["+instr.src1+"]"
                

                # 写ROB
                rob.Busy[instr.ID-1] = "Yes"
                rob.Instruction[instr.ID-1] = instr.text
                rob.State[instr.ID-1] = "Issue"
                rob.Dest[instr.ID-1] = instr.dest
                ele1, ele2 = "", "" # ROB的Value项涉及到的两个操作数
                for j in range(instr.ID-1): # 遍历前面已经发射的指令，看看这两个源操作数是不是前面的指令的结果
                    # 如果是，则记为"#"+指令编号
                    if rob.Dest[j] == instr.src1:
                        ele1 = "#"+str(j+1) # 这里不能直接break，因为有些寄存器在前面可能不止被写过一次
                    if rob.Dest[j] == instr.src2:
                        ele2 = "#"+str(j+1) # 同理
                if ele1 == "":  # 还为""说明前面没有指令会动它，则直接Regs[寄存器]读取它的值即可
                    ele1 = "Regs["+instr.src1+"]"
                if ele2 == "":  # 另一个操作数同理
                    ele2 = "Regs["+instr.src2+"]"
                if Ioperation == "fmul.d":  # 注意是mult还是div
                    rob.Value[instr.ID-1] = ele1+"*"+ele2
                else:   # Ioperation: "fdiv.d"
                    rob.Value[instr.ID-1] = ele1+"/"+ele2
                # 写FPRS
                fp_id = fprs.Names.index(instr.dest)
                fprs.Status[0][fp_id] = str(instr.ID)
                fprs.Status[1][fp_id] = "Yes"
                return instr.ID, rs.Name[i]

    else:   # Itype: "Store"
        start = rs.Name.index("Store1")
        for i in range(start,start+3):
            if rs.Busy[i] == "No" and rs.Op[i] == "":
                # 写RS
                rs.Busy[i] = "Yes"
                rs.Op[i] = Ioperation
                rs.Dest[i] = "#"+str(instr.ID)
                # 注意 store指令的格式，指令instr的dest对应的是要写入存储器的值，src1和src2分别对应偏移和基地址
                rs.Vj[i] = instr.src1.replace("+","") 
                rs.Vk[i] = "Regs["+instr.src2+"]"
                
                # 写ROB
                rob.Busy[instr.ID-1] = "Yes"
                rob.Instruction[instr.ID-1] = instr.text
                rob.State[instr.ID-1] = "Issue"

                # store指令的rob就不记录目的寄存器和值了
                # store指令不用动FPRS
                return instr.ID, rs.Name[i]
    return -1, ""
                
def execReady(rsName: str, rs: Hardware_Structure.RS):  # 指令在其所用的RS里面的两个源操作数都准备完毕且Qj和Qk均为空时可以执行
    rsID = rs.Name.index(rsName)
    return (rs.Vj[rsID]!="") and (rs.Vk[rsID]!="") and (rs.Qj[rsID] == "") and (rs.Qk[rsID] == "")


# 算法模拟器
def Speculative_Tomasulo(inPath: str, outPath: str):
    processedInstr = Process.inputProcessing(inPath)  # 获取处理后的指令
    N = len(processedInstr)     # 记录指令总条数
    FinalTable = [[""]*5 for _ in range(N+1)]   # 最终执行情况表，一个(N+1)*5的二维列表(N+1：包括列名)
    FinalTable[0] = ["Instruction".ljust(16," "),
                     "Issue cycle".ljust(15," "),
                     "Exec comp cycle".ljust(17," "),
                     "Write result cycle".ljust(22," "),
                     "Commit cycle"]
    
    # 初始化保留站、ROB、FPRS
    rs = Hardware_Structure.RS()
    rob = Hardware_Structure.ROB(N)
    fprs = Hardware_Structure.FPRS()
    Cycles = 1  # 当前周期
    IssNum = 0  # 当前已发射的指令数
    CommNum = 0 # 当前已提交的指令数
    Inst2RS = {}    # 每条指令使用的功能单元
    RS2Inst = {}    # 每个功能单元对应的指令
    outFile = open(outPath,"w") # 输出文件

    while CommNum < N:  # 终止条件：所有指令都提交
        countdownRes = rs.Countdown()   # 进行倒计时，记录下有没有刚好可以执行的，如果有，待会进入执行态
        # 1) 先找能提交的，能交要尽快交
        if CommNum == 0:    # 对首条进行特殊处理
            if rob.State[0] == "Write Result":
                # 修改ROB: 状态:Write Result -> Commit  Busy:Yes->No
                rob.State[0] = "Commit"
                rob.Busy[0] = "No"
                
                # 修改RS: 对应的功能单元: 调用RS的clear函数 
                rs.Clear(Inst2RS[1])    # 注意此处对应的是第一条指令(id=1)

                # 修改fprs: 对应的busy: Yes -> No(由于Store指令没有改动fprs，因此这里只对非Store指令进行修改)
                if processedInstr[0].inst != "SD":
                    fpid = fprs.Status[0].index("1")  # 找到对应的reorder项的索引
                    fprs.Status[1][fpid] = "No"

                # 修改Inst2RS,RS2Inst
                RS2Inst[Inst2RS[1]] = ""
                Inst2RS[1] = ""

                # 记录其提交时间
                FinalTable[1][4] = str(Cycles)

                # 发射指令数+1
                CommNum += 1
        else:
            if rob.State[CommNum] == "Write Result" and rob.State[CommNum-1] == "Commit":
                # 修改ROB: 状态:Write Result -> Commit  Busy:Yes->No
                rob.State[CommNum] = "Commit"
                rob.Busy[CommNum] = "No"

                # 修改RS: 对应的功能单元: 调用RS的clear函数 
                rs.Clear(Inst2RS[CommNum+1])    # 注意此处对应的是第CommNum+1条指令

                # 修改fprs: 对应的busy: Yes -> No(由于Store指令没有改动fprs，因此这里只对非Store指令进行修改)
                if processedInstr[CommNum].inst != "SD":
                    fpid = fprs.Status[0].index(str(CommNum+1))  # 找到对应的reorder项的索引
                    fprs.Status[1][fpid] = "No"

                # 修改Inst2RS,RS2Inst
                RS2Inst[Inst2RS[CommNum+1]] = ""
                Inst2RS[CommNum+1] = ""

                # 记录其提交时间
                FinalTable[CommNum+1][4] = str(Cycles)

                # 发射指令数+1
                CommNum += 1
        
        # 2) 找能发射的
        # 发射条件: 还有指令未发送且满足issue_available条件(见issue_available函数)
        if IssNum < N and issue_available(processedInstr[IssNum],rs,rob,fprs):   
            instrID, rsName = issue(processedInstr[IssNum],rs,rob,fprs)
            if instrID != -1:
                FinalTable[instrID][0] = processedInstr[IssNum].text # 最终执行情况表中导入指令
                FinalTable[instrID][1] = str(Cycles) # 记录发射周期
                
                # 建立起指令ID和对应功能单元的映射
                Inst2RS[instrID] = rsName   
                RS2Inst[rsName] = instrID
                
                IssNum += 1 # 已发射指令数+1
        

        # 3) 找能写回的
        if len(countdownRes) != 0:  # 倒计时后记录执行完毕的结果列表不为空的话说明有指令可以在当前周期进行写回
            for rsItem in countdownRes:
                id = RS2Inst[rsItem]
                if rob.State[id-1] == "Execute":
                    # 修改ROB
                    rob.State[id-1] = "Write Result"

                    # 修改RS: 将Qj/Qk中涉及到的相关操作数都改了，注意Vj/Vk也要赋值(此处直接赋值为ROB中对应的Regs[Dest])
                    rs.Busy[rs.Name.index(rsItem)] = "No"
                    for i in range(len(rs.Name)):
                        if rs.Qj[i] == "#"+str(id):
                            if rob.Dest[id-1] != "":
                                rs.Vj[i] = "Regs["+rob.Dest[id-1]+"]"
                                rs.Qj[i] = ""
                        if rs.Qk[i] == "#"+str(id):
                            if rob.Dest[id-1] != "":
                                rs.Vk[i] = "Regs["+rob.Dest[id-1]+"]"
                                rs.Qk[i] = ""
                    # fprs不用改
                    
                    # 记录其写回时间
                    FinalTable[id][3] = str(Cycles)
        
        # 4) 找能执行的
        for instid in Inst2RS.keys():
            if Inst2RS[instid]!="" and execReady(Inst2RS[instid],rs) and rob.State[instid-1] == "Issue" and FinalTable[instid][1] != str(Cycles):
                # 修改ROB
                rob.State[instid-1] = "Execute"

                # 修改RS: 设置计时器
                rsid = rs.Name.index(Inst2RS[instid])
                rsop = rs.Op[rsid]
                rs.Timer[rsid] = rs.inst_exec_time[rsop]

                # 记录执行周期
                FinalTable[instid][2] = str(Cycles)
        
        # 输出
        outStr = "Cycle_"+str(Cycles)+";\n"
        outFile.write(outStr)
        print(outStr)

        # 输出ROB信息
        for i in range(N):
            outStr = "Entry"+str(i+1)+": "+rob.Busy[i]+","+rob.Instruction[i]+","+rob.State[i]+","
            outStr += rob.Dest[i] + "," + rob.Value[i] + ";\n"
            outFile.write(outStr)
            print(outStr)
        
        # 输出RS信息
        for i in range(len(rs.Name)):
            outStr = rs.Name[i]+": "+rs.Busy[i]+","+rs.Op[i]+","+rs.Vj[i]+","+rs.Vk[i]+","+rs.Qj[i]+","+rs.Qk[i]+","
            outStr += rs.Dest[i]+";\n"
            outFile.write(outStr)
            print(outStr)
        
        # 输出FPRS信息
        # 1.reorder信息
        outStr = "Reorder#: "
        for i in range(len(fprs.Names)):
            outStr += fprs.Names[i]+":"
            outStr += "" if fprs.Status[1][i] == "No" else fprs.Status[0][i]
            outStr += ";"
        outStr += "\n"
        outFile.write(outStr)
        print(outStr)

        # 2.busy信息
        outStr = "Busy: "
        for i in range(len(fprs.Names)):
            outStr += fprs.Names[i]+":"+fprs.Status[1][i]+";"
        outStr += "\n\n"
        outFile.write(outStr)
        print(outStr)
        Cycles += 1
    outStr = "Final execution table: \n"
    outFile.write(outStr)
    print(outStr)
    for i in range(N+1):
        outStr = ""
        if i == 0:  # 输出列名
            for j in range(5):  
                outStr += FinalTable[i][j]
            outStr += "\n"
            outFile.write(outStr)
            print(outStr)
        else:   # 对齐并输出各条指令及其对应的发射周期、执行周期、写回周期、提交周期(这里指的是进入某一阶段的周期)
            outStr += FinalTable[i][0].ljust(16," ")
            outStr += FinalTable[i][1].ljust(15," ")
            outStr += FinalTable[i][2].ljust(17," ")
            outStr += FinalTable[i][3].ljust(22," ")
            outStr += FinalTable[i][4] + "\n"
            outFile.write(outStr)
            print(outStr)
    