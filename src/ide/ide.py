from asyncio import InvalidStateError

import customtkinter as ctk
from ide.mapui import Map
from PIL import Image
import os
from interpreter.interpreter import *
from external.ctk_xyframe import *
import re

ctk.set_appearance_mode("Dark")

class IDE:
    def __init__(self, input_file:str, output_file:str):
        self.input_file = str(input_file)
        self.output_file = str(output_file)

        self.window = ctk.CTk()
        self.subwindow = Map("Rover",self.window,True,RobotAPI(["....@..........",".#############.",".......@...>..."],15,3,Logger(output_file)))
        self.subwindow.update()

        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()

        window_width = int(screen_width * 0.6)
        window_height = int(screen_height * 0.6)
        self.window.geometry(f"{window_width}x{window_height}")

        self.program = self.read_input_file()

        self.window.title(f"MazsolaÉsTádé MineScript editor...  (loading editor)")
        self.create_env()

        self.window.title(f"MazsolaÉsTádé MineScript editor  <<  {self.input_file}")

    def main(self):
        self.window.mainloop()

    def create_env(self):
        # program betűtípus
        self.mono_font = ctk.CTkFont(family="Consolas", size=14)

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
        self.button1 = ctk.CTkButton(self.top_box, fg_color="green", hover_color="darkgreen", text="Blokk", command=self.action_b1)
        self.button1.grid(row=0, column=0, padx=(5, 2.5), pady=5, sticky="ew")
        # forráskód gomb
        self.button2 = ctk.CTkButton(self.top_box, fg_color="green", hover_color="darkgreen", text="Kód", command=self.action_b2)
        self.button2.grid(row=0, column=1, padx=(2.5, 5), pady=5, sticky="ew")

        # oldalsáv
        self.sidebar = ctk.CTkFrame(self.window, width=38, corner_radius=5)
        self.sidebar.grid(row=1, column=0, sticky="nsw", padx=(5, 2.5), pady=(0, 5))
        self.sidebar.grid_propagate(False)

        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.play_icon = ctk.CTkImage(light_image=Image.open(os.path.join(current_dir, "../img/icons/play.png")), size=(20, 20))
            self.debug_icon = ctk.CTkImage(light_image=Image.open(os.path.join(current_dir, "../img/icons/debug.png")), size=(20, 20))
            self.save_icon = ctk.CTkImage(light_image=Image.open(os.path.join(current_dir, "../img/icons/save.png")), size=(20, 20))
            self.add_icon = ctk.CTkImage(light_image=Image.open(os.path.join(current_dir, "../img/icons/add.png")), size=(20, 20))
            self.remove_icon = ctk.CTkImage(light_image=Image.open(os.path.join(current_dir, "../img/icons/remove.png")), size=(20, 20))
            self.move_up_icon = ctk.CTkImage(light_image=Image.open(os.path.join(current_dir, "../img/icons/move_up.png")), size=(20, 20))
            self.move_down_icon = ctk.CTkImage(light_image=Image.open(os.path.join(current_dir, "../img/icons/move_down.png")), size=(20, 20))
        except FileNotFoundError:
            raise FileNotFoundError("Egy vagy több ikon nem található! Ez az alkalmazáshoz tartozó egyik erőforrás hiányát jelenti, újratelepítés ajánlott.")

        # futtatás gomb
        self.side_btn_run = ctk.CTkButton(self.sidebar, fg_color="#8AE03D", hover_color="#72B339", text="", image=self.play_icon, width=28, height=28, command=self.run)
        self.side_btn_run.pack(pady=5, padx=5)

        # debug gomb
        self.side_btn_debug = ctk.CTkButton(self.sidebar, fg_color="#E6D95A", hover_color="#BFB549", text="", image=self.debug_icon, width=28, height=28, command=self.debug)
        self.side_btn_debug.pack(pady=5, padx=5)

        # mentés gomb
        self.side_btn_save = ctk.CTkButton(self.sidebar, fg_color="#50B7EB", hover_color="#4694BD", text="", image=self.save_icon, width=28, height=28, command=self.save)
        self.side_btn_save.pack(pady=5, padx=5)

        self.side_btn_add = None
        self.side_btn_remove = None

        # fő content tároló
        self.main_container = CTkXYFrame(self.window, fg_color="#1C1C1C")
        self.main_container.grid(row=1, column=1, padx=(2.5, 5), pady=(0, 5), sticky="nsew")

        self.block_editor = None

        self.action_b1() # blokkos nézet gomb alapból megnyomva

    def read_input_file(self):
        try:
            with open(self.input_file, "r") as f:
                return f.readlines()
        except FileNotFoundError:
            raise FileNotFoundError(f"Nem található a bemeneti fájl! Győződj meg róla, hogy a megadott útvonal helyes! ('{self.input_file}') ({os.listdir()})")

    def action_b1(self):
        if self.mode == 1:
            return

        self.mode = 1
        self.load_block_view()

        self.button1.configure(state="disabled")
        self.button2.configure(state="normal")

    def action_b2(self):
        if self.mode == 2:
            return

        self.mode = 2
        self.load_code_view()
        self.unload_block_view()

        self.button2.configure(state="disabled")
        self.button1.configure(state="normal")

    def load_code_view(self):
        self.clear_main_container()
        for i in range(len(self.program)):
            self.add_code_row(i+1, self.program[i].strip())

    def clear_main_container(self):
        for e in self.main_container.pack_slaves():
            e.destroy()

    def add_code_row(self, line_num, code):
        row_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        row_frame.pack(fill="x", anchor="w", pady=1)

        line_num_section = ctk.CTkLabel(
            row_frame,
            text=str(line_num)[:3],
            font=self.mono_font,
            width=35,
            height=22,
            anchor="e",
            fg_color="gray25",
            corner_radius=4
        )
        line_num_section.pack(side="left", padx=(0, 5))

        code_section = ctk.CTkLabel(
            row_frame,
            text=code,
            font=self.mono_font,
            height=22,
            anchor="w",
            justify="left"
        )
        code_section.pack(side="left", fill="x", expand=True)

    def load_block_view(self):
        self.clear_main_container()

        self.block_editor = BlockEditor(self.program, self.main_container, self.window)

        # új elem gomb
        self.side_btn_add = ctk.CTkButton(self.sidebar, fg_color="#84FF78", hover_color="#6FD164", text="", image=self.add_icon, width=28, height=28, command=self.add_block)
        self.side_btn_add.pack(pady=5, padx=5)

        # elem törlése gomb
        self.side_btn_remove = ctk.CTkButton(self.sidebar, fg_color="#FF7A7A", hover_color="#D45B5B", text="", image=self.remove_icon, width=28, height=28, command=self.remove_block)
        self.side_btn_remove.pack(pady=5, padx=5)

        # elem felfele mozgatása gomb
        self.side_btn_move_up = ctk.CTkButton(self.sidebar, fg_color="#D587FF", hover_color="#B983D6", text="", image=self.move_up_icon, width=28, height=28, command=self.move_block_up)
        self.side_btn_move_up.pack(pady=5, padx=5)

        # elem lefele mozgatása gomb
        self.side_btn_move_down = ctk.CTkButton(self.sidebar, fg_color="#FF7DAD", hover_color="#D1668E", text="", image=self.move_down_icon, width=28, height=28, command=self.move_block_down)
        self.side_btn_move_down.pack(pady=5, padx=5)

    def unload_block_view(self):
        if self.side_btn_add:
            self.side_btn_add.destroy()
        if self.side_btn_remove:
            self.side_btn_remove.destroy()
        self.block_editor = None

    def add_block(self):
        self.block_editor.add_block()

    def remove_block(self):
        self.block_editor.delete_block()

    def move_block_up(self):
        self.block_editor.move_block_up()

    def move_block_down(self):
        self.block_editor.move_block_down()

    def run(self):
        print("{" + self.block_editor.reconstruct_program_text(self.main_container) + "}")

    def debug(self):
        pass

    def save(self):
        with open(self.input_file, "w") as f:
            f.writelines(self.program)
        self.window.title(f"MazsolaÉsTádé MineScript editor  <<  {self.input_file}")

class BlockEditor:
    def __init__(self, program, container, window):
        self.program = program
        self.container = container
        self.window = window

        self.selected_block = None
        self.selected_block_original_color = None

        self.create_env()

    def create_env(self):
        pass

    # "$" = input mező, "#" = tároló, "@" = blokkgyűjtő tároló
    def make_block(self, parent, contents, block_type):
        if block_type == "command":
            block = ctk.CTkFrame(parent, fg_color="#8DF0EA")
        elif block_type == "print":
            block = ctk.CTkFrame(parent, fg_color="#8FEB81")
        elif block_type == "set":
            block = ctk.CTkFrame(parent, fg_color="#8DAEF0")
        elif block_type == "if":
            block = ctk.CTkFrame(parent, fg_color="#EE8DF0")
        elif block_type == "loop":
            block = ctk.CTkFrame(parent, fg_color="#81EBAB")
        elif block_type == "value":
            block = ctk.CTkFrame(parent, fg_color="#F0D28D")
        else:
            raise ValueError(f"Nem létező blokk típus! ('{block_type}') Ez az alkalmazás kódjának korrupcióját jelenti, újratelepítés ajánlott.")

        inner_regular_containers = contents.count("@")
        grid_index = 0
        block.grid_rowconfigure(tuple(range(inner_regular_containers * 2 + 1)), weight=1)
        block.grid_columnconfigure(0, weight=1)
        block.grid_columnconfigure(1, minsize=10)
        block.is_block = "yessir"
        row = ctk.CTkFrame(block, fg_color="transparent", height=0, width=0)
        row.grid(row=grid_index, column=0, padx=(5, 0), pady=5, sticky="w")
        row.bind("<Button-1>", lambda e, b=block: self.select_block(b))
        row.is_row = "yessir"

        sub_containers = []
        parts = re.split(r'([$#@])', contents)
        for part in parts:
            if part == "":
                continue

            if part == "$":
                input_box = ctk.CTkEntry(row, fg_color="white", text_color="black")
                input_box.pack(side="left", padx=5, pady=10)
                sub_containers.append(input_box)

            elif part == "#":
                inline_container = ctk.CTkFrame(row, height=24, fg_color="white")
                inline_container.pack(side="left", padx=5, pady=5, fill="y")
                inline_container.container_type = "#"
                inline_container.bind("<Button-1>", lambda event, container=inline_container: self.add_value_block(container))
                sub_containers.append(inline_container)

            elif part == "@":
                grid_index += 1
                regular_container = ctk.CTkFrame(block, fg_color="#1C1C1C", corner_radius=0, height=30)
                regular_container.grid(row=grid_index, column=0, columnspan=2, padx=(30, 0), pady=5, sticky="new")
                regular_container.container_type = "@"
                sub_containers.append(regular_container)
                grid_index += 1
                row = ctk.CTkFrame(block, fg_color="transparent", height=0, width=0)
                row.grid(row=grid_index, column=0, padx=(5, 0), pady=5, sticky="w")
                row.bind("<Button-1>", lambda e, b=block: self.select_block(b))
                row.is_row = "yessir"

            else:
                text_label = ctk.CTkLabel(row, text=part, fg_color="transparent", text_color="black")
                text_label.pack(side="left", padx=(10, 5), pady=10)
                text_label.bind("<Button-1>", lambda e, b=block: self.select_block(b))
                sub_containers.append(text_label)

        block.bind("<Button-1>", lambda e, b=block: self.select_block(b))
        block.pack(pady=5, padx=5, anchor="w")
        return block, sub_containers

    def reconstruct_program_text(self, container, depth=0, is_inline=False):
        reconstructed_text = ""

        container.update_idletasks()

        children = container.winfo_children()
        children.sort(key=lambda widget: (widget.winfo_y(), widget.winfo_x()))

        for child in children:

            if isinstance(child, ctk.CTkLabel):
                reconstructed_text += child.cget("text") + " "

            elif isinstance(child, ctk.CTkEntry):
                val = child.get()
                reconstructed_text += (val if val else "") + " "

            elif isinstance(child, ctk.CTkFrame):
                ctype = getattr(child, "container_type", None)
                is_block = getattr(child, "is_block", None) == "yessir"

                if is_block:
                    if is_inline:
                        reconstructed_text += self.reconstruct_program_text(child, depth, is_inline=True).strip() + " "
                    else:
                        block_text = self.reconstruct_program_text(child, depth, is_inline=False)
                        reconstructed_text += block_text.rstrip() + "\n"

                elif ctype == "@":
                    inner_text = self.reconstruct_program_text(child, depth + 1, is_inline=False).rstrip()
                    if inner_text:
                        reconstructed_text += "\n" + inner_text + "\n"
                    else:
                        reconstructed_text += "\n"

                elif ctype == "#":
                    reconstructed_text += self.reconstruct_program_text(child, depth, is_inline=True).strip() + " "

                else:
                    row_text = self.reconstruct_program_text(child, depth, is_inline).strip()

                    if row_text:
                        if not is_inline:
                            indent = "    " * depth
                            reconstructed_text += indent + row_text + " "
                        else:
                            reconstructed_text += row_text + " "

        return reconstructed_text

    def select_block(self, selected_block):
        if self.selected_block:
            self.selected_block.configure(fg_color=self.selected_block_original_color)

        if self.selected_block == selected_block:
            self.selected_block = None
            self.selected_block_original_color = None
            return

        self.selected_block = selected_block
        self.selected_block_original_color = self.selected_block.cget("fg_color")
        self.selected_block.configure(fg_color="#FFAA99")

    def delete_block(self):
        if not self.selected_block:
            return

        self.selected_block.destroy()
        self.selected_block = None
        self.selected_block_original_color = None

    def add_block(self):
        contents, block_type = self.block_selector()
        self.make_block(self.container, contents, block_type)

    def add_value_block(self, parent):
        contents, block_type = self.value_block_selector()

        for e in parent.pack_slaves():
            e.destroy()

        self.make_block(parent, contents, block_type)

    def move_block_up(self):
        if not self.selected_block:
            return

        # nincs mozgatás, ha érték-blokk
        if getattr(self.selected_block.pack_info()["in"], "container_type", None) == "#":
            return

        current_parent = self.selected_block.pack_info()["in"]
        siblings = current_parent.pack_slaves()

        try:
            idx = siblings.index(self.selected_block)
        except ValueError:
            raise InvalidStateError("UI hiba! Nem található a mozgatásra kiválasztott blokk.")

        # előtte lévő blokk
        if idx > 0:
            block_above = siblings[idx - 1]

            block_above_siblings = block_above.winfo_children()
            regular_containers = [c for c in block_above_siblings if getattr(c, "container_type", "") == "@"]

            if len(regular_containers) == 0:
                self.selected_block.pack(before=block_above)
            else:
                previous_container = regular_containers[-1]
                self.selected_block.pack(in_=previous_container, pady=5, padx=5, anchor="w")

            self.lift_block(self.selected_block)
            return

        # ne mozduljon, ha a legtetején van
        if current_parent == self.container:
            self.lift_block(self.selected_block)
            return

        # a blokk, amiben van
        outer_block = current_parent.master

        # más konténer ebben a blokkban
        outer_siblings = outer_block.winfo_children()
        regular_containers = [c for c in outer_siblings if getattr(c, "container_type", "") == "@"]

        if current_parent in regular_containers:
            container_idx = regular_containers.index(current_parent)

            # másik konténerbe ugrás
            if container_idx > 0:
                previous_container = regular_containers[container_idx - 1]
                self.selected_block.pack(in_=previous_container, pady=5, padx=5, anchor="w")

            # kiugrás a blokkból
            else:
                outer_parent = outer_block.pack_info()["in"]
                self.selected_block.pack(in_=outer_parent, before=outer_block, pady=5, padx=5, anchor="w")

        self.lift_block(self.selected_block)

    def move_block_down(self):
        if not self.selected_block:
            return

        # nincs mozgatás, ha érték-blokk
        if getattr(self.selected_block.pack_info()["in"], "container_type", None) == "#":
            return

        current_parent = self.selected_block.pack_info()["in"]
        siblings = current_parent.pack_slaves()

        try:
            idx = siblings.index(self.selected_block)
        except ValueError:
            raise InvalidStateError("UI hiba! Nem található a mozgatásra kiválasztott blokk.")

        # utána lévő blokk
        if idx < len(siblings) - 1:
            block_below = siblings[idx + 1]

            block_below_siblings = block_below.winfo_children()
            regular_containers = [c for c in block_below_siblings if getattr(c, "container_type", "") == "@"]

            if len(regular_containers) == 0:
                self.selected_block.pack(after=block_below)
            else:
                next_container = regular_containers[0]
                next_children = next_container.pack_slaves()

                if next_children:
                    self.selected_block.pack(in_=next_container, before=next_children[0], pady=5, padx=5, anchor="w")
                else:
                    self.selected_block.pack(in_=next_container, pady=5, padx=5, anchor="w")

            self.lift_block(self.selected_block)
            return

        # ne mozduljon, ha a legalján van
        if current_parent == self.container:
            self.lift_block(self.selected_block)
            return

        # a blokk, amiben van
        outer_block = current_parent.master

        # más konténer ebben a blokkban
        outer_siblings = outer_block.winfo_children()
        regular_containers = [c for c in outer_siblings if getattr(c, "container_type", "") == "@"]

        if current_parent in regular_containers:
            container_idx = regular_containers.index(current_parent)

            # másik konténerbe ugrás
            if container_idx < len(regular_containers) - 1:
                next_container = regular_containers[container_idx + 1]
                next_children = next_container.pack_slaves()

                if next_children:
                    self.selected_block.pack(in_=next_container, before=next_children[0], pady=5, padx=5, anchor="w")
                else:
                    self.selected_block.pack(in_=next_container, pady=5, padx=5, anchor="w")

            # kiugrás a blokkból
            else:
                outer_parent = outer_block.pack_info()["in"]
                self.selected_block.pack(in_=outer_parent, after=outer_block, pady=5, padx=5, anchor="w")

        self.lift_block(self.selected_block)

    def lift_block(self, block, depth=0):
        block.lift()
        if getattr(block, "is_block", None) == "yessir":
            for child in block.winfo_children():
                self.lift_block(child, depth + 1)
        else:
            for child in block.pack_slaves():
                self.lift_block(child, depth + 1)

    def get_max_internal_at_depth(self, widget):
        """Kiszámolja a mozgatni kívánt blokk saját, belső maximális @ mélységét."""
        max_depth = 0
        for child in widget.winfo_children():
            child_depth = self.get_max_internal_at_depth(child)
            if getattr(child, "container_type", "") == "@":
                child_depth += 1
            if child_depth > max_depth:
                max_depth = child_depth
        return max_depth

    def block_selector(self):
        # kiválasztás ablak
        selector_window = ctk.CTkToplevel(self.window)
        selector_window.title("Válassz blokkot!")
        selector_window.geometry("300x400")
        selector_window.transient(self.window)
        selector_window.wait_visibility()
        selector_window.grab_set()

        selected_data = ("", "")

        block_options = {
            "step forward": ("step forward$", "command"),
            "turn by": ("turn by$", "command"),
            "mine here": ("mine here", "command"),
            "print": ("print$", "print"),
            "set": ("set$to#", "set"),
            "if": ("if$@", "if"),
            "if-else": ("if$@else@", "if"),
            "while": ("while$do:@", "loop")
        }

        # választó lista
        scroll_frame = ctk.CTkScrollableFrame(selector_window, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        def make_selection(values):
            nonlocal selected_data
            selected_data = values
            selector_window.destroy()

        for display_name, values in block_options.items():
            btn = ctk.CTkButton(
                scroll_frame,
                text=display_name,
                anchor="w",
                fg_color="#D9D9D9",
                hover_color="#9C9C9C",
                text_color="black",
                command=lambda a=values: make_selection(a)
            )
            btn.pack(fill="x", padx=5, pady=5)

        # felhasználói bemenetre várás
        self.window.wait_window(selector_window)

        return selected_data

    def value_block_selector(self):
        # kiválasztás ablak
        selector_window = ctk.CTkToplevel(self.window)
        selector_window.title("Válassz érték-blokkot!")
        selector_window.geometry("300x400")
        selector_window.transient(self.window)
        selector_window.wait_visibility()
        selector_window.grab_set()

        selected_data = ("", "")

        block_options = {
            "simpleval": ("$", "value"),
            "+": ("$+$", "value"),
            "-": ("$-$", "value"),
            "*": ("$*$", "value"),
            "=": ("$=$", "value"),
            "<>": ("$<>$", "value"),
            "<": ("$<$", "value"),
            "<=": ("$<=$", "value"),
            ">": ("$>$", "value"),
            ">=": ("$>=$", "value"),
            "and": ("$and$", "value"),
            "or": ("$or$", "value"),
            "not": ("not$", "value"),
            "isThere": ("isThere$", "value")
        }

        # választó lista
        scroll_frame = ctk.CTkScrollableFrame(selector_window, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        def make_selection(values):
            nonlocal selected_data
            selected_data = values
            selector_window.destroy()

        for display_name, values in block_options.items():
            btn = ctk.CTkButton(
                scroll_frame,
                text=display_name,
                anchor="w",
                fg_color="#FFE6B3",
                hover_color="#EBD2A0",
                text_color="black",
                command=lambda a=values: make_selection(a)
            )
            btn.pack(fill="x", padx=5, pady=5)

        # felhasználói bemenetre várás
        self.window.wait_window(selector_window)

        return selected_data
