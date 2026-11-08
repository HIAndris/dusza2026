import customtkinter as Ctk
from interpreter.interpreter import RobotAPI
from PIL import Image
from external.ctk_xyframe import *
import os

mapui_current_dir = os.path.dirname(os.path.abspath(__file__))

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

class Map():

    #Futtatás példa:
    #from mapui import *
    #testui = Map(nev="Teszt",parentwindow=<Ctk.Ctk object>,isSim:bool,RobotAPI)
    #testui.update()

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
        if self.mode:
            # program alapján fut
            self.robot.loggingEnabled = False
        self.mode = not self.mode
        self._setCols_()

    def _handleMine_(self):
        try:
            self.robot.mine()
            self.update()
        except:
            pass
    def _handleTurn_(self,isLeft:bool):
        try:
            self.robot.turnBy(1 if isLeft else 3)
            self.update()
        except:
            pass
    def _handleStep_(self):
        try:
            self.robot.stepForward(1)
            self.update()
        except:
            pass


    def __init__(self, nev:str, parentwindow,isSim:bool,robotAPI:RobotAPI):
        '''
            Megnyitja a szimulációt egy külön lapon.
        '''

        self.mode = isSim
        self.main = Ctk.CTkToplevel(parentwindow)
        self.main.focus()
        self.main.title(nev)
        self.main.resizable(False, False)

        self.robot = robotAPI

        self.outerFrame = CTkXYFrame(self.main,fg_color="#333333")
        self.outerFrame.pack(fill="both", expand=True)

        self.frame = None

        self.timer = None
        
        self.oldmap = []
        self.oldroverpos = []

        self.img_size = (61,64) # Képek mérete
        
        goldOG = Image.open(f"{mapui_current_dir}/../img/gold.png").convert('RGBA')
        gold = Ctk.CTkImage(light_image=goldOG, dark_image=goldOG, size=self.img_size) # Arany érc képének betöltése

        self.rover_img = f"{mapui_current_dir}/../img/rover.png"

        wallOG = Image.open(f"{mapui_current_dir}/../img/wall.png").convert('RGBA')
        wall = Ctk.CTkImage(light_image=wallOG, dark_image=wallOG, size=self.img_size) # Kövek képének betöltése

        self.nothing = Ctk.CTkImage(light_image=Image.open(f"{mapui_current_dir}/../img/nothing.png"), dark_image=Image.open(f"{mapui_current_dir}/../img/nothing.png"), size=self.img_size)

        # Azok amik ahoz kellenek hogy megjelenítse melyik helyeken járt meg ilyenek:
        self.visited = [[5,1],[3,1]]
        self.saw = [[9,1],[9,2]]

        sawImg = Image.open(f"{mapui_current_dir}/../img/saw.png")
        sawImg = sawImg.resize(self.img_size)

        didntVisitImg = Image.open(f"{mapui_current_dir}/../img/didntvisit.png")
        didntVisitImg = didntVisitImg.resize(self.img_size)


        combined = goldOG.copy()
        combined.alpha_composite(didntVisitImg)
        goldDidnt = Ctk.CTkImage(light_image=combined,dark_image=combined,size=combined.size)

        combined2 = goldOG.copy()
        combined2.alpha_composite(sawImg)
        goldSaw = Ctk.CTkImage(light_image=combined2,dark_image=combined2,size=combined2.size)

        combined3 = wallOG.copy()
        combined3.alpha_composite(didntVisitImg)
        wallDidnt = Ctk.CTkImage(light_image=combined3,dark_image=combined3,size=combined3.size)

        combined4 = wallOG.copy()
        combined4.alpha_composite(sawImg)
        wallSaw = Ctk.CTkImage(light_image=combined4,dark_image=combined4,size=combined4.size)

        self.images = {
                "@": {
                        0 : goldDidnt,    # Semmi
                        1 : gold,   # Ha már meglett látogatva
                        2 : goldSaw       # Ha az isThere meg lett hívva rajt
                    },
                "#": {
                        0 : wallDidnt,    # Semmi
                        1 : wall,   # Ha már meglett látogatva
                        2 : wallSaw       # Ha az isThere meg lett hívva rajt
                    },
                "": {
                        0 : Ctk.CTkImage(light_image=didntVisitImg,dark_image=didntVisitImg,size=sawImg.size),
                        1 : self.nothing,
                        2 : Ctk.CTkImage(light_image=sawImg,dark_image=sawImg,size=sawImg.size)
                   }
                }

        # A GUI
        self.buttonFrame = Ctk.CTkFrame(self.main,height=100,fg_color="#575757")
        self.buttonFrame.pack(side="bottom",fill="x")
        self.goldBox = Ctk.CTkFrame(self.buttonFrame,width=200,fg_color="#676767")
        self.goldBox.pack(side="right",fill="y")
        self.goldFrame = Ctk.CTkFrame(self.goldBox,height=self.img_size[1],fg_color="#676767")
        self.goldFrame.place(anchor="center",relx=0.5,rely=0.5)
        img = Image.open(f"{mapui_current_dir}/../img/gold.png")
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


    def update(self):
        '''
            Frissíti a térképet.
        '''
        rover_x,rover_y = self.robot.pos
        rover_point = self.robot.getIconFromFace(self.robot.facing)
        map = self.robot.map

        self.goldText.configure(text=" = "+str(self.robot.goldCount))

        if not [rover_x,rover_y] in self.visited:
            self.visited.append([rover_x,rover_y])


        if self.timer != None and self.oldmap == []: #Timer reset
            self.main.after_cancel(self.timer)

        if self.oldmap == []:
            for widget in self.outerFrame.winfo_children(): #Teljes tisztítás
                widget.destroy()

            frame_size = (700,600) #Teljes ablak mérete (dinamikus = img_size[0]*len(map[1]),img_size[1]*len(map)+15, statikus = 700,600)
            self.main.geometry(f"{frame_size[0]}x{frame_size[1]}")


        rover = {
            ">": lambda x: Ctk.CTkImage(light_image=cropimg(1, x, self.rover_img), dark_image=cropimg(1, x, self.rover_img), size=self.img_size),
            "<": lambda x: Ctk.CTkImage(light_image=cropimg(3, x, self.rover_img), dark_image=cropimg(3, x, self.rover_img), size=self.img_size),
            "v": lambda x: Ctk.CTkImage(light_image=cropimg(4, x, self.rover_img), dark_image=cropimg(4, x, self.rover_img), size=self.img_size),
            "^": lambda x: Ctk.CTkImage(light_image=cropimg(2, x, self.rover_img), dark_image=cropimg(2, x, self.rover_img), size=self.img_size)
        }


        def rover_anim(pos:str, rover_img:Ctk.CTkLabel, timer:int=3):
            rover_img.configure(image=pos(timer))
            timer = 3 if timer >= 13 else timer + 1
            self.timer = self.main.after(333, lambda: rover_anim(pos, rover_img, timer))

        if self.frame == None:
            self.frame = Ctk.CTkFrame(self.outerFrame)
            for row in range(len(map)):
                for col in range(len(map[row])):
                    self.frame.grid_rowconfigure(row, weight=1)
                    self.frame.grid_columnconfigure(col, weight=1)
                    self.outerFrame.grid_rowconfigure(row, weight=1)
                    self.outerFrame.grid_columnconfigure(col, weight=1)
            self.frame.grid(row=0,column=0,rowspan=len(map),columnspan=len(map[0]))

        for row in range(len(map)):
            for col in range(len(map[row])):
                item = map[row][col]
                if self.oldmap != [] and item == self.oldmap[row][col] and row != rover_y and col != rover_x:
                    continue


                version = 0
                if [col,row] in self.visited:
                    version = 1
                elif [col,row] in self.saw:
                    version = 2


                if item != "@" and item != "#":
                    imgLabel = Ctk.CTkLabel(self.frame, text="", image=self.images[""][version])
                    imgLabel.grid(row=row, column=col)
                else:
                    imgLabel = Ctk.CTkLabel(self.frame, text="",image=self.images[item][version])
                    imgLabel.grid(row=row,column=col)



                if row == rover_y and col == rover_x:
                    self.oldroverpos = [rover_y, rover_x]
                    rover_lb = Ctk.CTkLabel(self.frame, text="", image=rover[rover_point](3))
                    rover_lb.grid(row=row, column=col)

                    if self.timer != None:
                        self.main.after_cancel(self.timer)
                    

                    self.timer = self.main.after(333, lambda: rover_anim(rover[rover_point], rover_lb))

        self.oldmap = map
