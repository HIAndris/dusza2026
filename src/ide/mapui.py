import customtkinter as Ctk
from PIL import Image
from external.ctk_xyframe import *

class Map():

    #Futtatás példa:
    #from mapui import *
    #testui = Map(nev="Teszt",parentwindow=<Ctk.Ctk object>)
    #testui.update(rover_x = 10, rover_y= 2, rover_point=">", map=["....@..........", ".#############.", ".......@......."])

    def _setCols_(self):
        if self.mode:
            # program alapján fut
            self.stepBtn.configure(state="disabled",fg_color="#373737",hover_color="#373737",border_color="#373737",text_color="#777777")
            self.turnLBtn.configure(state="disabled",fg_color="#373737",hover_color="#373737",border_color="#373737",text_color="#777777")
            self.turnRBtn.configure(state="disabled",fg_color="#373737",hover_color="#373737",border_color="#373737",text_color="#777777")
            self.mineBtn.configure(state="disabled",fg_color="#373737",hover_color="#373737",border_color="#373737",text_color="#777777")
            self.simBtn.configure(state="disabled",fg_color="#373737",hover_color="#373737",border_color="#373737",text_color="#777777")
            #ez be lesz kapcsolva
            self.manualBtn.configure(state="normal",fg_color="#373737",hover_color="#474747",border_color="#ffffff",text_color="#ffffff")
        else:
            # kézi irányítás
            self.stepBtn.configure(state="normal",fg_color="#373737",hover_color="#474747",border_color="#ffffff",text_color="#ffffff")
            self.turnLBtn.configure(state="normal",fg_color="#373737",hover_color="#474747",border_color="#ffffff",text_color="#ffffff")
            self.turnRBtn.configure(state="normal",fg_color="#373737",hover_color="#474747",border_color="#ffffff",text_color="#ffffff")
            self.mineBtn.configure(state="normal",fg_color="#373737",hover_color="#474747",border_color="#ffffff",text_color="#ffffff")
            self.simBtn.configure(state="normal",fg_color="#373737",hover_color="#474747",border_color="#ffffff",text_color="#ffffff")
            #ez ki lesz kapcsolva
            self.manualBtn.configure(state="disabled",fg_color="#373737",hover_color="#373737",border_color="#373737",text_color="#777777")

    def _switchMode_(self):
        self.mode = not self.mode
        self._setCols_()

    def _handleMine_(self):
        print("MINE")
    def _handleTurn_(self,isLeft:bool):
        print("TURN " + "LEFT!" if isLeft else "RIGHT!")
    def _handleStep_(self):
        print("STEP")


    def __init__(self, nev:str, parentwindow,isSim):
        '''
            Megnyitja a szimulációt egy külön lapon.
        '''

        self.mode = isSim
        self.main = Ctk.CTkToplevel(parentwindow)
        self.main.focus()
        self.main.title(nev)
        self.main.resizable(False, False)

        self.frame = CTkXYFrame(self.main)
        self.frame.pack(fill="both", expand=True)


        self.timer = None
        
        self.oldmap = []
        self.oldroverpos = []

        self.img_size = (50,50) # Képek mérete

        self.goldOG = Image.open('img/gold.png').convert('RGBA')
        self.gold = Ctk.CTkImage(light_image=self.goldOG, dark_image=self.goldOG, size=self.img_size) # Arany érc képének betöltése

        self.rover_img = "img/rover.png"

        self.wallOG = Image.open('img/wall.png').convert('RGBA')
        self.wall = Ctk.CTkImage(light_image=self.wallOG, dark_image=self.wallOG, size=self.img_size) # Kövek képének betöltése

        self.nothing = Ctk.CTkImage(light_image=Image.open('img/nothing.png'), dark_image=Image.open("img/nothing.png"), size=self.img_size)

        # Azok amik ahoz kellenek hogy megjelenítse melyik helyeken járt meg ilyenek:
        self.visited = [[5,1],[3,1]]
        self.saw = [[9,2],[10,2]]
        self.visitedImg = Image.open("img/visited.png")
        self.visitedImg = self.visitedImg.resize(self.img_size)
        self.sawImg = Image.open("img/saw.png")
        self.sawImg = self.sawImg.resize(self.img_size)

        # A GUI
        self.buttonFrame = Ctk.CTkFrame(self.main,height=100,fg_color="#575757")
        self.buttonFrame.pack(side="bottom",fill="x")
        self.goldBox = Ctk.CTkFrame(self.buttonFrame,width=200,fg_color="#676767")
        self.goldBox.pack(side="right",fill="y")
        self.goldFrame = Ctk.CTkFrame(self.goldBox,height=self.img_size[1],fg_color="#676767")
        self.goldFrame.place(anchor="center",relx=0.5,rely=0.5)
        img = Image.open('img/gold.png')
        gold2 = Ctk.CTkImage(light_image=img,dark_image=img,size=(int(img.width*1.5),int(img.height*1.5)))
        self.goldIMG = Ctk.CTkLabel(self.goldFrame,text="",image=gold2)
        self.goldIMG.pack(side="left")
        self.goldText = Ctk.CTkLabel(self.goldFrame,text=" = 67",font=('Arial',28))
        self.goldText.pack(side="right")

        # Turn-by, step-forward, mine-here
        # Az elképzelt layout:
        #                                 ______________
        #          [step]                 |    mine    |
        # [turn-left]  [turn-right]       |    here    |
        #                                 L____________J

        self.controls = Ctk.CTkFrame(self.buttonFrame,fg_color="#575757")
        self.controls.pack(side="left",fill="both",expand=True)

        self.centeredCtrls = Ctk.CTkFrame(self.controls,fg_color="#575757")
        self.centeredCtrls.place(anchor="center",relx=0.5,rely=0.5)
        self.dPadFrameOuter = Ctk.CTkFrame(self.centeredCtrls,fg_color="#575757")
        self.dPadFrameOuter.pack(side="left",fill="both",expand=True)
        self.dPadFrame = Ctk.CTkFrame(self.dPadFrameOuter,fg_color="#575757")
        self.dPadFrame.pack(side="left",pady=20,padx=20)
        # A gombok:
        self.stepBtn = Ctk.CTkButton(self.dPadFrame,
                                     text="⇪",width=30,height=60,border_width=3,
                                     corner_radius=50,font=('Arial',24,"bold"),command=self._handleStep_)
        self.stepBtn.place(anchor="n",relx=0.5,rely=0.1)
        self.turnLBtn = Ctk.CTkButton(self.dPadFrame,
                                     text="↰",width=30,height=60,border_width=3,
                                      corner_radius=50,font=('Arial',24,"bold"),command=lambda:self._handleTurn_(True))
        self.turnLBtn.place(anchor="w",relx=0.0,rely=0.6)
        self.turnRBtn = Ctk.CTkButton(self.dPadFrame,
                                     text="↱",width=30,height=60,border_width=3,
                                      corner_radius=50,font=('Arial',24,"bold"),command=lambda:self._handleTurn_(False))
        self.turnRBtn.place(anchor="e",relx=1.0,rely=0.6)

        # A jobb oldal
        self.RBtnWrapper = Ctk.CTkFrame(self.centeredCtrls,fg_color="#575757")
        self.RBtnWrapper.pack(side="right",fill="both",expand=True,padx=30)
        self.mineBtn = Ctk.CTkButton(self.RBtnWrapper,
                                     text="⛏",width=100,height=100,border_width=3,
                                     corner_radius=50,font=('Arial',24,"bold"),command=self._handleMine_)
        self.mineBtn.place(rely=0.5,relx=0.5,anchor="center")


        # A mód váltás:
        self.switchSwitch = Ctk.CTkFrame(self.main,fg_color="transparent",corner_radius=100)
        self.switchSwitch.place(x=5,y=5)

        self.simBtn = Ctk.CTkButton(self.switchSwitch,text="Sim",font=('Arial',11,"bold"),width=60,corner_radius=4,border_width=1,command=self._switchMode_)
        self.simBtn.pack(side="left",expand=True,fill="both")
        self.manualBtn = Ctk.CTkButton(self.switchSwitch,text="Manual",font=('Arial',11,"bold"),width=60,corner_radius=4,border_width=1,command=self._switchMode_)
        self.manualBtn.pack(side="right",expand=True,fill="both")

        self._setCols_()

    def update(self, rover_x:int, rover_y:int, rover_point:str, map:list):
        '''
            Frissíti a térképet.
        '''

        if not [rover_x,rover_y] in self.visited:
            self.visited.append([rover_x,rover_y])



        if self.timer != None and self.oldmap == []: #Timer reset
            self.main.after_cancel(self.timer)

        if self.oldmap == []:
            for widget in self.frame.winfo_children(): #Teljes tisztítás
                widget.destroy()

            frame_size = (700,600) #Teljes ablak mérete (dinamikus = img_size[0]*len(map[1]),img_size[1]*len(map)+15, statikus = 700,600)
            self.main.geometry(f"{frame_size[0]}x{frame_size[1]}")

        def cropimg(row:int, col:int, img):
            '''
                Egy adot sorban lévő db-ig lévő objetumot jeleníti meg
            '''

            original = Image.open(img)

            width, height = original.size
            left = (col - 2 )* width/12 # right - 1
            top = (row - 1 )* width/12
            right = (col-1)* width/12 # Amit szeretnén db-1
            bottom = row * width/12
            cropped_img = original.crop((left, top, right, bottom))

            return cropped_img

        rover = {
            ">": lambda x: Ctk.CTkImage(light_image=cropimg(1, x, self.rover_img), dark_image=cropimg(1, x, self.rover_img), size=self.img_size),
            "<": lambda x: Ctk.CTkImage(light_image=cropimg(3, x, self.rover_img), dark_image=cropimg(3, x, self.rover_img), size=self.img_size),
            "v": lambda x: Ctk.CTkImage(light_image=cropimg(4, x, self.rover_img), dark_image=cropimg(4, x, self.rover_img), size=self.img_size),
            "^": lambda x: Ctk.CTkImage(light_image=cropimg(2, x, self.rover_img), dark_image=cropimg(2, x, self.rover_img), size=self.img_size)
        }


        def rover_anim(pos:str, rover_img:Ctk.CTkLabel, timer:int=3):
            rover_img.configure(image=pos(timer))
            timer = 3 if timer >= 13 else timer + 1
            self.timer = self.main.after(1000, lambda: rover_anim(pos, rover_img, timer))

        for row in range(len(map)):
            for col in range(len(map[row])):
                item = map[row][col]
                if self.oldmap != [] and item == self.oldmap[row][col] and row != rover_y and col != rover_x:
                    continue
                
                self.frame.grid_rowconfigure(row, weight=1)
                self.frame.grid_columnconfigure(col, weight=1)


                imgLabel = None
                currImg = None
                if item == "@":
                    imgLabel = Ctk.CTkLabel(self.frame, text="", image=self.gold)
                    imgLabel.grid(row=row, column=col)
                    currImg = self.goldOG
                elif item == "#":
                    imgLabel = Ctk.CTkLabel(self.frame, text="", image=self.wall)
                    imgLabel.grid(row=row, column=col)
                    currImg = self.wallOG
                else:
                    imgLabel = Ctk.CTkLabel(self.frame, text="", image=self.nothing)
                    imgLabel.grid(row=row, column=col)

                toUse = None
                if [col,row] in self.visited and imgLabel != None:
                    toUse = self.visitedImg
                elif [col,row] in self.saw and imgLabel != None:
                    toUse = self.sawImg

                if toUse != None:
                    img = None
                    if currImg == None:
                        img = Ctk.CTkImage(light_image=toUse,dark_image=toUse,size=toUse.size)
                    else:
                        combined = toUse.copy()
                        combined.alpha_composite(currImg)
                        img = Ctk.CTkImage(light_image=combined,dark_image=combined,size=combined.size)
                    overlay = Ctk.CTkLabel(self.frame,text="",image=img,fg_color="transparent")
                    overlay.grid(row=row,column=col)
                    
                if row == rover_y and col == rover_x:
                    if self.oldroverpos != [] and (self.oldroverpos[0] != rover_y or self.oldroverpos[1] != rover_x):
                        Ctk.CTkLabel(self.frame, text="", image=self.nothing).grid(row=self.oldroverpos[0], column=self.oldroverpos[1])

                    self.oldroverpos = [rover_y, rover_x]
                    rover_lb = Ctk.CTkLabel(self.frame, text="", image=rover[rover_point](3))
                    rover_lb.grid(row=row, column=col)

                    if self.timer != None:
                        self.main.after_cancel(self.timer)
                    

                    self.timer = self.main.after(1000, lambda: rover_anim(rover[rover_point], rover_lb))

        self.oldmap = map
