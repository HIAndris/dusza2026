import customtkinter as Ctk
from PIL import Image
class Map():

    #Futtatás példa:
    #main = Ctk.Ctk()
    #testui = Map(main = main, nev="Teszt")
    #testui.update(["....@..........", ".#############.", ".......@...<..."])
    #main.mainloop()

    def __init__(self, main:Ctk.CTk, nev:str):
        '''
            Megnyitja a szimulációt egy külön lapon.
        '''
        
        Ctk.set_appearance_mode("dark")

        self.main = main
        self.main.title(nev)
        self.main.resizable(False, False)

        self.frame = Ctk.CTkScrollableFrame(self.main)
        self.frame.pack(fill="both", expand=True)
        self.timer = None


    def update(self, map:list):
        '''
            Frissíti a térképet.
        '''

        if self.timer != None: #Timer reset
            self.main.after_cancel(self.timer)

        for widget in self.frame.winfo_children(): #Teljes tisztítás
            widget.destroy()

        img_size = (50,50) # Képek mérete

        frame_size = (img_size[0]*len(map[1]),300) #Teljes ablak mérete (dinamikus = img_size[0]*len(map[1]),img_size[1]*len(map)+15, statikus = 300,300)
        
        self.main.geometry(f"{frame_size[0]}x{frame_size[1]}")

        gold = Ctk.CTkImage(light_image=Image.open('img/gold.png'), dark_image=Image.open("img/gold.png"), size=img_size) # Arany érc képének betöltése

        rover_img = "img/rover.png"

        wall = Ctk.CTkImage(light_image=Image.open('img/wall.png'), dark_image=Image.open("img/wall.png"), size=img_size) # Kövek képének betöltése

        nothing = Ctk.CTkImage(light_image=Image.open('img/nothing.png'), dark_image=Image.open("img/nothing.png"), size=img_size)

        def cropimg(row:int, col:int):
            '''
                Egy adot sorban lévő db-ig lévő objetumot jeleníti meg
            '''

            original = Image.open(rover_img)

            width, height = original.size
            left = (col - 2 )* width/12 # right - 1
            top = (row - 1 )* width/12
            right = (col-1)* width/12 # Amit szeretnén db-1
            bottom = row * width/12
            cropped_img = original.crop((left, top, right, bottom))

            return cropped_img

        rover = {
            ">": lambda x: Ctk.CTkImage(light_image=cropimg(1, x), dark_image=cropimg(1, x), size=img_size),
            "<": lambda x: Ctk.CTkImage(light_image=cropimg(3, x), dark_image=cropimg(3, x), size=img_size),
            "v": lambda x: Ctk.CTkImage(light_image=cropimg(4, x), dark_image=cropimg(4, x), size=img_size),
            "^": lambda x: Ctk.CTkImage(light_image=cropimg(2, x), dark_image=cropimg(2, x), size=img_size)
        }


        def rover_anim(pos:str, rover_img:Ctk.CTkLabel, timer:int=3):
            rover_img.configure(image=pos(timer))
            timer = 3 if timer >= 13 else timer + 1
            self.timer = self.main.after(1000, lambda: rover_anim(pos, rover_img, timer))

        for row in range(len(map)):
            for col in range(len(map[row])):
                item = map[row][col]
                
                self.frame.grid_rowconfigure(row, weight=1)
                self.frame.grid_columnconfigure(col, weight=1)

                if item == "@":
                    Ctk.CTkLabel(self.frame, text="", image=gold).grid(row=row, column=col)
                elif item == ">" or item == "<" or item == "^" or item == "v":
                    rover_lb = Ctk.CTkLabel(self.frame, text="", image=rover[item](3))
                    rover_lb.grid(row=row, column=col)

                    if self.timer != None:
                        self.main.after_cancel(self.timer)
                    
                    sitem = item

                    self.timer = self.main.after(1000, lambda: rover_anim(rover[sitem], rover_lb))
                elif item == "#":
                    Ctk.CTkLabel(self.frame, text="", image=wall).grid(row=row, column=col)
                else:
                    Ctk.CTkLabel(self.frame, text="", image=nothing).grid(row=row, column=col)

        
    