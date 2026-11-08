import customtkinter as ctk
from ide.mapui import Map
from PIL import Image
import os

class IDE:
    def __init__(self, input_file:str, output_file:str):
        self.input_file = str(input_file)
        self.output_file = str(output_file)

        self.window = ctk.CTk()
        self.subwindow = Map("Rover",self.window,True)
        self.subwindow.update( 11, 2, '>',["....@..........",".#############.",".......@...>..."])

        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()

        window_width = int(screen_width * 0.6)
        window_height = int(screen_height * 0.6)
        self.window.geometry(f"{window_width}x{window_height}")
        self.window.title(f"MazsolaÉsTádé MineScript editor  <<  {self.input_file}")

        self.create_env()

    def main(self):
        self.window.mainloop()

    def create_env(self):
        # fő grid
        self.window.grid_rowconfigure(0, weight=0)
        self.window.grid_rowconfigure(1, weight=1)
        self.window.grid_columnconfigure(0, weight=0)
        self.window.grid_columnconfigure(1, weight=1)

        # gombok
        self.top_box = ctk.CTkFrame(self.window, fg_color="transparent")
        self.top_box.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.top_box.grid_columnconfigure(0, weight=1)
        self.top_box.grid_columnconfigure(1, weight=1)
        self.mode = None
        # blokk gomb
        self.button1 = ctk.CTkButton(self.top_box, fg_color="green", hover_color="darkgreen", text="Utasítások", command=self.action_b1)
        self.button1.grid(row=0, column=0, padx=(5, 2.5), pady=5, sticky="ew")
        # forráskód gomb
        self.button2 = ctk.CTkButton(self.top_box, fg_color="green", hover_color="darkgreen", text="Kód", command=self.action_b2)
        self.button2.grid(row=0, column=1, padx=(2.5, 5), pady=5, sticky="ew")

        self.action_b1() # blokkos gomb alapból megnyomva

        # oldalsáv
        self.sidebar = ctk.CTkFrame(self.window, width=38, corner_radius=5)
        self.sidebar.grid(row=1, column=0, sticky="nsw", padx=(5, 2.5), pady=(0, 5))
        self.sidebar.grid_propagate(False)

        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            play_icon = ctk.CTkImage(light_image=Image.open(os.path.join(current_dir, "../img/icons/play.png")), size=(20, 20))
            debug_icon = ctk.CTkImage(light_image=Image.open(os.path.join(current_dir, "../img/icons/debug.png")), size=(20, 20))
        except FileNotFoundError:
            raise FileNotFoundError("Egy vagy több ikon nem található!")

        # futtatás gomb
        self.side_btn_play = ctk.CTkButton(self.sidebar, text="", image=play_icon, width=28, height=28, fg_color="transparent")
        self.side_btn_play.pack(pady=5, padx=5)

        # debug gomb
        self.side_btn_debug = ctk.CTkButton(self.sidebar, text="", image=debug_icon, width=28, height=28, fg_color="transparent")
        self.side_btn_debug.pack(pady=5, padx=5)

        # content
        self.main_container = ctk.CTkScrollableFrame(self.window)
        self.main_container.grid(row=1, column=1, padx=(2.5, 5), pady=(0, 5), sticky="nsew")

    def action_b1(self):
        if self.mode == 1:
            return

        self.mode = 1
        print("b1")

        self.button1.configure(state="disabled")
        self.button2.configure(state="normal")

    def action_b2(self):
        if self.mode == 2:
            return

        self.mode = 2
        print("b2")

        self.button2.configure(state="disabled")
        self.button1.configure(state="normal")

