import io
from contextlib import redirect_stdout

class RobotAPI:
    def _setPos_(self,x:int,y:int,to:str):
        line = self.map[y]
        line = line[:x]+to+line[x+1:]
        self.map[y] = line
    def __init__(self,mapIn:list[str],width:int,height:int):
        self.map = mapIn
        self.width = width
        self.height= height
        # Csak megnézi hogy ezen a koordinátákon van e a robot
        self.isPlayer = lambda x,y : self.map[y][x] == '<' or self.map[y][x] == '^' or self.map[y][x] == '>' or self.map[y][x] == 'v'
        # Átkonvertálja a karaktert egy iránnyá
        self.getFaceFromIcon = lambda icon : 0 if icon == '^' else 1 if icon == '<' else 2 if icon == 'v' else 3
        for y in range(len(self.map)):
            for x in range(len(self.map[y])):
                if self.isPlayer(x,y):
                    self.pos = [x,y]
        self._setPos_(self.pos[0],self.pos[1],'.')
        # 0 fel, 1 bal, 2 le, 3 jobb
        self.facing = self.getFaceFromIcon(self.map[self.pos[1]][self.pos[0]])
    # itt már be lesz állítva hogy ne legyen negatív.
    # most jöttem rá hogy nem is lehet negatív mivel a turn-by-hoz csak egy számot lehet írni és nincsenek negatív számok az egészbe
    def turnBy(self,count:int):
        self.facing = (self.facing+count)%4
    def stepForward(self,count:int):
        nextPos = self.pos
        for i in range(count):
            nextPos = [ nextPos[0]-1 if self.facing == 1 else nextPos[0]+1 if self.facing == 3 else nextPos[0],\
                        nextPos[1]-1 if self.facing == 0 else nextPos[1]+1 if self.facing == 2 else nextPos[1]]
            if nextPos[0] < 0 or nextPos[0] >= self.width:
                raise ValueError("E_BEDROCK_HIT")
            if nextPos[1] < 0 or nextPos[1] >= self.height:
                raise ValueError("E_BEDROCK_HIT")
            if self.map[nextPos[1]][nextPos[0]] == '#':
                raise ValueError("E_BEDROCK_HIT")
        self.pos = nextPos
    def mine(self):
        if self.map[self.pos[1]][self.pos[0]] != '@':
            raise ValueError("E_NO_GOLD")

        self._setPos_(self.pos[0],self.pos[1],'.')
    def isThere(self,toCheck:int)->bool:
        checkFor = ''
        if toCheck == 0:
            checkFor = '.'
        elif toCheck == 1:
            checkFor = '#'
        elif toCheck == 2:
            checkFor = '@'

        checkAgainst = ''

        inFront = [ self.pos[0]-1 if self.facing == 1 else self.pos[0]+1 if self.facing == 3 else self.pos[0],\
                    self.pos[1]-1 if self.facing == 0 else self.pos[1]+1 if self.facing == 2 else self.pos[1]]

        if inFront[0] < 0 or inFront[0] >= self.width:
            checkAgainst = '#'
        elif inFront[1] < 0 or inFront[1] >= self.height:
            checkAgainst = '#'
        else:
            checkAgainst = self.map[inFront[1]][inFront[0]]

        #print(inFront,self.width,self.height,checkFor,checkAgainst)
        #print('\n'.join(self.map),self.pos)

        return checkFor == checkAgainst




class Interpreter:
    def __init__(self,inFile:str)->None:
        self.file = inFile.split('\n')
        if self.file[-1] == '':
            self.file = self.file[:-1]

        # Robot API dolgok
        height,width = self.file[0].split(' ')
        width = int(width)
        height = int(height)
        roverMap = self.file[1:height+1]
        self.rover = RobotAPI(roverMap,width,height)

        # Ténylegesen az interpreter dolgai
        self.vars:dict[str,int] = {}
        self.varVals = {}
        self.types = {}
        self.functions = {
                # név : függvény ami kezeli
                "isThere":self._handleIsThere
                }
        self.operators = {
                "+":   (lambda a,b: a + b),
                "-":   (lambda a,b: a - b),
                "*":   (lambda a,b: a * b),
                "=":   (lambda a,b: a == b),
                "<>":  (lambda a,b: a != b),
                "<":   (lambda a,b: a < b),
                "<=":  (lambda a,b: a <= b),
                ">":   (lambda a,b: a > b),
                ">=":  (lambda a,b: a >= b),
                "and": (lambda a,b: a and b),
                "or" : (lambda a,b: a or b),
                "not": (lambda a:   not a)
            }
        self.lineNum = height+1
        self.depth = 0
        self.spacecount = [0]    # Az előző soron minden rétegben a space-ek száma
        self.indentStart = []   # A sornak az indexe ahol a beljebb kezdés kezdődik (lista mivel több loop is lehet)
                                # Ha negatív akkor az if blokk kezdetét jelzi
        self.shouldRunindent:bool = True
    def printVars(self):
        for var in self.vars:
            num = self.vars[var]
            print(f"{var}:{self.types[num]} = {self.varVals[num]}")
    def _handleIsThere(self,simpleVal:list)->bool:
        if simpleVal[0] != int or simpleVal[1] > 2 or simpleVal[1] < 0:
            raise ValueError("E_BAD_ARG")
        else:
            return self.rover.isThere(simpleVal[1])

    def _readSimpleVal_(self,var:str)->tuple[type,bool|int]:
        # identifier | number | boolean-lit
        toRet = [None,0]

        if var.isdecimal():
            toRet[0] = int
            toRet[1] = int(var)

        elif var == "true" or var == "false":
            toRet[0] = bool
            toRet[1] = var == "true"
        else:
            # 100% hogy identifier szóval ha nincs a listába akkor errort kell dobni
            if not var in self.vars:
                raise ValueError("E_UNINITIALIZED")
            else:
                toRet[0] = self.types[self.vars[var]]
                toRet[1] = self.varVals[self.vars[var]]
        return (toRet[0],toRet[1])

    def _handleSet_(self,tokenized:list[str]):  # Ez elég egyszerű mivel lehetetlen komplikált egyenletet ide írni
        #  0  1  2   3..
        # set x to ertek
        name:str = tokenized[1]
        value = 0
        expression:list[str] = tokenized[3:]


        isUsed:bool = name in self.vars
        varType = self.types[self.vars[name]] if isUsed else None

        # "ertek" lehet simpleval | function | binop | unop
        match len(expression):
            # Csak simpleval lehet mert a function meg a binop, unop az több tokenből áll
            case 1:
                returned = self._readSimpleVal_(expression[0])

                if varType == None:
                    varType = returned[0]
                elif varType != returned[0]:
                    raise ValueError("E_TYPE_MISMATCH")
                value = returned[1]

            # csak az unop tartozik ide
            case 2:
                # Itt vagy unop lesz vagy function
                if expression[0] == "not":
                    returned = self._readSimpleVal_(expression[1])
                    # muszály hogy bool legyen hogy a "not" működjön
                    if returned[0] != bool:
                        raise ValueError("E_BAD_OPERAND")

                    if varType == None:
                        varType = bool
                    elif varType != bool:
                        raise ValueError("E_TYPE_MISMATCH")

                    value = self.operators["not"](returned[1])
                else:
                    # Itt is 100% hogy a jó function lesz mivel ilyen szempontból hiba mentes lesz a kód
                    typeof, simpVal = self._readSimpleVal_(expression[1])
                    # az isThere függvény igaz-hamist ad vissza, szóval a változónak anak kell lennie
                    value = self.functions[expression[0]]([typeof,simpVal])

                    if varType == None:
                        varType = bool
                    elif varType != bool:
                        raise ValueError("E_TYPE_MISMATCH")

            case 3:
                var1type, var1val = self._readSimpleVal_(expression[0])
                var2type, var2val = self._readSimpleVal_(expression[2])

                operator = expression[1]
                retType = None
                if (operator == "+" or operator == "-" or operator == "*"):
                    if (var1type != int or var2type != int):
                        raise ValueError("E_BAD_OPERAND")
                    retType = int
                if (operator == "<" or operator == "<=" or operator == ">" or operator == ">="):
                    if (var1type != int or var2type != int):
                        raise ValueError("E_BAD_OPERAND")
                    retType = bool
                if (operator == "and" or operator == "or"):
                    if (var1type != bool or var2type != bool):
                        raise ValueError("E_BAD_OPERAND")
                    retType = bool
                if (operator == "=" or operator == "<>"):
                    if (var1type != var2type):
                        raise ValueError("E_BAD_OPERAND")
                    retType = bool

                value = self.operators[operator](var1val,var2val)
                if varType == None:
                    varType = retType
                elif varType!=retType:
                    raise ValueError("E_TYPE_MISMATCH")

        if isUsed:
            self.varVals[self.vars[name]] = value
        else:
            self.vars[name] = len(self.varVals)
            self.varVals[self.vars[name]] = value
            self.types[self.vars[name]] = varType

    def _handlePrint_(self,tokenized:list):
        simpleval = self._readSimpleVal_(tokenized[1])
        if simpleval[0] == bool:
            print(str(simpleval[1]).lower())
        else:
            print(simpleval[1])

    def _handleWhile_(self,tokenized:list):
        simpleval = self._readSimpleVal_(tokenized[1])
        if simpleval[0] != bool:
            raise ValueError("E_NON_BOOL_CONDITION")
        if simpleval[1] == True:
            self.shouldRunindent = True
            self.indentStart.append(self.lineNum)
            self.depth += 1
        else:
            self.shouldRunindent = False

    def _cropLine_(self,lineIn:str)->tuple[str,list[int]]:
        # vissza adja a sort space-ek nélkül és egy listát amibe benne van hogy mennyi space-t használt fel / indentation
        lineOut:str = lineIn[:-1] if lineIn[-1] == '\n' else lineIn
        spaces = 0
        while spaces < len(lineOut) and lineOut[spaces] == ' ':
            spaces += 1
        toRetSpaces = []
        if spaces == 0:
            return (lineOut[spaces:],[0])
        for i in self.spacecount:
            if sum(toRetSpaces) < spaces:
                toRetSpaces.append(i)
            else:
                break
        if spaces > sum(self.spacecount):
            toRetSpaces.append(spaces-sum(self.spacecount))
        #print("toRetSpaces =",toRetSpaces)
        return (lineOut[spaces:],toRetSpaces)

    def _handleTurn_(self,tokenized:list):
        #   0   1 2
        # turn by n
        typeof,simpleval = self._readSimpleVal_(tokenized[2])
        if typeof != int:
            raise ValueError("E_BAD_ARG")
        self.rover.turnBy(simpleval)

    def _handleStep_(self,tokenized:list):
        #   0     1    2
        # step forward n
        typeof,simpleval = self._readSimpleVal_(tokenized[2])
        if typeof != int:
            raise ValueError("E_BAD_ARG")
        self.rover.stepForward(simpleval)

    def _handleMine_(self,tokenized:list):
        #   0    1 
        # mine here
        self.rover.mine()

    def _handleIf_(self,tokenized:list):
        #  0 1
        # if n
        typeof,simpleval = self._readSimpleVal_(tokenized[1])
        if typeof != bool:
            raise ValueError("E_NON_BOOL_CONDITION")
        if simpleval == True:
            self.shouldRunindent = True
            self.indentStart.append(-self.lineNum)
            self.depth += 1
        else:
            self.shouldRunindent = False

    def _handleElse_(self,tokenized:list):
        #   0 
        # else
        # Meg kell keresni az if-et amihez tartozott
        # Egy oszlopba kell lennie az if-nek meg az else-nek
        rawLine = self.file[self.lineNum]
        col = 0
        while col < len(rawLine) and rawLine[col] == ' ':
            col += 1
        assert col < len(rawLine) # Mivel nincs üres sor biztos hogy nem végtelen space lesz

        line = self.lineNum
        # Elvileg mindegyik sornak hosszabbnak kellene lennie az if szó kezdetétől, mivel az if után következik egy indented block
        while line >= 0 and self.file[line][col:col+2] != "if":
            line-=1
        assert line > 0 # Mivel ugye nem lehet úgy else hogy nincsen előtte if

        ifLine = self._cropLine_(self.file[line])[0].split(' ')
        #  0 1
        # if n

        typeof,simpleval = self._readSimpleVal_(ifLine[1])
        if typeof != bool:
            raise ValueError("E_NON_BOOL_CONDITION")
        if simpleval == True:
            # Nem kell lefutni az else-nek
            self.shouldRunindent = False
        else:
            # Le kell futni az else-nek
            self.indentStart.append(-self.lineNum)
            self.shouldRunindent = True
            self.depth += 1

    def _handleDepthChange_(self):
        # Eldönti hogy skippelje-e ezt a réteget (ha például if-else-blockba hamis az állítás
        # -2 = break
        # -1 = exit
        # 1 = norm
        self.spacecount.pop()
        self.depth-=1
        #print("-depth")
        # Nem kell foglalkozni azzal hogy nem lesz elkülönítve a 0. sorba az if és a while mivel a nulladik sorba úgyis a térkép van
        #print(self.indentStart)
        if self.indentStart[self.depth] >= 0:
            self.lineNum = self.indentStart[self.depth]
            self.indentStart.pop()
            line = self.file[self.lineNum]
            line,self.spacecount = self._cropLine_(line)
            return line
        else:
            self.indentStart.pop()
        return 1

    def _handleEOF_(self)->int:
        # ha vége lenne a file-nak és még loop-ba lennénk
        if self.lineNum >= len(self.file):
            if self.depth <=0:
                return -1
            while self.depth > 0:
                ret = self._handleDepthChange_()

                if ret == -1:
                    return -1
                elif ret == 1 and len(self.indentStart) <= 0:
                    return -1
                elif ret != 1:
                    break

            if self.depth < 0:
                return -1
        return 1

    def runLine(self):
        if self._handleEOF_() < 0:
            return -1

        line = self.file[self.lineNum]
        # Eldönti hogy skippelje-e ezt a réteget (ha például if-else-blockba hamis az állítás
        while self.shouldRunindent == False:
            # A szóközöket megszámolja
            spaces = 0
            while line[spaces] == ' ':
                spaces+=1
            # Addig megy végig a sorokon amíg nem talál egy olyat ami ugyan annyira van beljebb kezdve mint ő maga, vagy nincs annyira behúzva mint ő maga, vagy eléri a file végét
            if spaces > sum(self.spacecount):
                self.lineNum += 1
                if self._handleEOF_() < 0:
                    return -1
                line = self.file[self.lineNum]
            else:
                self.shouldRunindent = True
                # Ilyenkor lehet az is hogy most már kevesebb a behúzás mint eddig de ezt elvileg a következő pár kódsor kezeli

        line,spaces = self._cropLine_(line)

        # Ha kiértünk egy beljebb kezdett blokkból akkor ugorjon vissza a loop elejére, ha van
        while sum(spaces) < sum(self.spacecount):
            ret = self._handleDepthChange_()
            if ret == -1:
                return -1
            elif ret != 1:
                line = ret
                break


        if sum(spaces) > sum(self.spacecount):
            self.spacecount.append(sum(spaces)-sum(self.spacecount))

        tokenized:list[str] = line.split(' ')   # Ez elég egyszerű mivel minden space-el el van választva

        match tokenized[0]:
            case "step":
                self._handleStep_(tokenized)
            case "turn":
                self._handleTurn_(tokenized)
            case "mine":
                self._handleMine_(tokenized)
            case "print":
                # Kiírás a konzolba
                self._handlePrint_(tokenized)
            case "set":
                # Változó létrehozás/szerkesztés
                self._handleSet_(tokenized)
            case "if":
                self._handleIf_(tokenized)
            case "else":
                self._handleElse_(tokenized)
            case "while":
                # Ciklusok
                self._handleWhile_(tokenized)
            case _:
                # Itt nyugodtan kiléphet a program mivel a feladat alapján ez úgy se fog megtörténni (2.1)
                print("Hiba az input file-al")
                exit(-1)
        self.lineNum+=1


if __name__ == "__main__":
    header = \
"""\
3 15
....@..........
.#############.
.......@...>...
"""
    tests = ''.join(open("./tests.txt","r",encoding="utf-8").readlines())
    progs = tests.split('---')
    ans = [progs[x] for x in range(len(progs)) if x%2==1]
    ans = [(line[1:] if line[0] == '\n' else line) for line in ans]
    ans = [(line[:-1] if line[-1] == '\n' else line) for line in ans]

    progs = [progs[x] for x in range(len(progs)) if x%2==0]
    progs = [(line[1:] if line[0] == '\n' else line) for line in progs]
    progs = [(line[:-1] if line[-1] == '\n' else line) for line in progs]
    progs = [header+line for line in progs]

    #print(progs[12])
    #inter = Interpreter(progs[12])
    #while -1 != inter.runLine():
    #    pass


    for i in range(len(progs)):
        print(f"Running test:{i}")
        inter = Interpreter(progs[i])
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            while -1 != inter.runLine():
                pass
        output = buffer.getvalue()
        if output == ans[i]+'\n':
            print(f"Test {i} passed!")
        else:
            print(f"Test {i} failed:\n{progs[i]}\nExpected output:\n{ans[i]}\nOutput:\n{output}")
            exit(-1)
    print("Tests done!")
