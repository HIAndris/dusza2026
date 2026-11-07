import customtkinter as Ctk
from PIL import Image
from external.ctk_xyframe import *

class Map():

    #Futtatás példa:
    #from mapui import *
    #testui = Map(nev="Teszt")
    #testui.update(rover_x = 10, rover_y= 2, rover_point=">", map=["....@..........", ".#############.", ".......@......."])
    #testui.main.mainloop()

    def __init__(self, nev:str):
        '''
            Megnyitja a szimulációt egy külön lapon.
        '''
        
        Ctk.set_appearance_mode("dark")

        self.main = Ctk.CTk()
        self.main.title(nev)
        self.main.resizable(False, False)

        self.frame = CTkXYFrame(self.main)
        self.frame.pack(fill="both", expand=True)
        
        self.timer = None
        
        self.oldmap = []
        self.oldroverpos = []

        self.img_size = (50,50) # Képek mérete

        self.gold = Ctk.CTkImage(light_image=Image.open('img/gold.png'), dark_image=Image.open("img/gold.png"), size=self.img_size) # Arany érc képének betöltése

        self.rover_img = "img/rover.png"

        self.wall = Ctk.CTkImage(light_image=Image.open('img/wall.png'), dark_image=Image.open("img/wall.png"), size=self.img_size) # Kövek képének betöltése

        self.nothing = Ctk.CTkImage(light_image=Image.open('img/nothing.png'), dark_image=Image.open("img/nothing.png"), size=self.img_size)


    def update(self, rover_x:int, rover_y:int, rover_point:str, map:list):
        '''
            Frissíti a térképet.
        '''

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


                if item == "@":
                    Ctk.CTkLabel(self.frame, text="", image=self.gold).grid(row=row, column=col)
                elif item == "#":
                    Ctk.CTkLabel(self.frame, text="", image=self.wall).grid(row=row, column=col)
                else:
                    Ctk.CTkLabel(self.frame, text="", image=self.nothing).grid(row=row, column=col)

                    
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