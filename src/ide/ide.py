import time
from asyncio import InvalidStateError

import customtkinter as ctk
from ide.mapui import Map
from PIL import Image
import os
from interpreter.interpreter import *
from external.ctk_xyframe import *
import re
from dataclasses import dataclass, field
from functools import lru_cache
from tkinter import messagebox

ctk.set_appearance_mode("Dark")


# ----------------------------------------------------------------------
# Blokk-sablonok egy helyen, hogy a blokkválasztó ablakok és a
# szöveg -> blokk átalakítás ugyanazt használja.
# "$" = input mező, "#" = tároló, "@" = blokkgyűjtő tároló
# ----------------------------------------------------------------------
BLOCK_TEMPLATES = {
    "step forward": ("step forward$", "command"),
    "turn by": ("turn by$", "command"),
    "mine here": ("mine here", "command"),
    "print": ("print$", "print"),
    "set": ("set$to#", "set"),
    "if": ("if$@", "if"),
    "if-else": ("if$@else@", "if"),
    "while": ("while$@", "loop"),  # "do:" nélkül, mert a szöveges kódban sincs
}

VALUE_TEMPLATES = {
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
    "isThere": ("isThere$", "value"),
}

# kétoperandusú műveletek kötési erőssége (kisebb = gyengébben köt);
# az érték szövege a leggyengébben kötő műveletnél vágódik két mezőre
BINARY_PRECEDENCE = {"or": 1, "and": 2, "=": 3, "<>": 3, "<": 3, "<=": 3, ">": 3, ">=": 3, "+": 4, "-": 4, "*": 5}


# ----------------------------------------------------------------------
# Szöveg -> blokkszerkezet
#
# 1. lépés: a sorokból a behúzás alapján fa épül (mint a Pythonnál).
# 2. lépés: a fa csomópontjait a BLOCK_TEMPLATES sablonjaihoz illesztjük.
# Itt még nem jön létre widget, így hibás programnál a felület érintetlen marad.
# ----------------------------------------------------------------------

class ProgramParseError(ValueError):
    def __init__(self, line_no, message):
        super().__init__(f"{line_no}. sor: {message}")
        self.line_no = line_no


@dataclass
class ParsedValue:
    template: str   # pl. "$+$"
    fields: list    # a "$" mezők szövege, sorrendben


@dataclass
class ParsedStatement:
    template: str     # pl. "set$to#"
    block_type: str   # pl. "set"
    fields: list      # "$" -> str, "#" -> ParsedValue vagy None, a sablon sorrendjében
    bodies: list      # "@" -> list[ParsedStatement], a sablon sorrendjében
    line_no: int


@dataclass
class _SourceLine:
    text: str
    line_no: int
    indent: int
    children: list = field(default_factory=list)


def parse_program_text(lines):
    """Szöveges program (sorok listája, pl. readlines()) -> list[ParsedStatement].
    Hibás programnál ProgramParseError-t dob, a sor számával."""
    return _parse_statements(_build_line_tree(lines))


def _build_line_tree(lines):
    root = _SourceLine("", 0, -1)
    stack = [root]
    for line_no, raw in enumerate(lines, start=1):
        expanded = raw.rstrip("\r\n").expandtabs(4)
        text = expanded.strip()
        if not text:
            continue  # az üres sorok nem számítanak

        indent = len(expanded) - len(expanded.lstrip())
        while stack[-1].indent >= indent:
            stack.pop()
        parent = stack[-1]

        if parent.children and parent.children[0].indent != indent:
            message = "a behúzás egyik korábbi szinthez sem illeszkedik"
            if _is_continuation_line(parent.text):  # pl. rosszul behúzott "else" okozza
                message += f" (ellenőrizd a {parent.line_no}. sor ('{parent.text}') behúzását is)"
            raise ProgramParseError(line_no, message)

        node = _SourceLine(text, line_no, indent)
        parent.children.append(node)
        stack.append(node)
    return root.children


@lru_cache(maxsize=None)
def _line_regex(line_template):
    """Egy sablonsor (pl. "set$to#") mintája; a mezők üresek is lehetnek,
    hogy a kitöltetlen blokkokból kapott szöveg is visszaalakítható legyen."""
    pattern = ""
    for part in re.split(r"([$#])", line_template):
        if not part.strip():
            continue
        if part in ("$", "#"):
            pattern += r"(?:\s+(.*?))?" if pattern else r"(.*?)"
        else:
            literal = r"\s+".join(re.escape(word) for word in part.split())
            pattern += (r"\s+" + literal) if pattern else literal
    return re.compile(pattern + r"\s*")


def _match_line(line_template, text):
    """[(mezőfajta, szöveg), ...] a sablonsor mezőire, vagy None, ha nem illeszkedik."""
    match = _line_regex(line_template).fullmatch(text)
    if match is None:
        return None
    kinds = [p for p in re.split(r"([$#])", line_template) if p in ("$", "#")]
    return [(kind, (value or "").strip()) for kind, value in zip(kinds, match.groups())]


def _parse_statements(nodes):
    statements = []
    i = 0
    while i < len(nodes):
        statement, used_lines = _parse_statement(nodes, i)
        statements.append(statement)
        i += used_lines
    return statements


def _parse_statement(nodes, i):
    best = None
    indent_error = None

    for template, block_type in BLOCK_TEMPLATES.values():
        segments = template.split("@")                # "if$@else@" -> ["if$", "else", ""]
        line_templates = [s for s in segments if s]   # ["if$", "else"]: egy-egy szövegsor
        n_bodies = len(segments) - 1
        if i + len(line_templates) > len(nodes):
            continue

        fields, bodies, matches = [], [], True
        for j, line_template in enumerate(line_templates):
            node = nodes[i + j]
            line_fields = _match_line(line_template, node.text)
            if line_fields is None:
                matches = False
                break
            if j < n_bodies:
                bodies.append(node.children)   # a beljebb kezdett sorok = a "@" tartalma
            elif node.children:
                matches = False
                indent_error = node.children[0]
                break
            fields.extend(line_fields)

        # több illeszkedő sablonból a több sort lefedő nyer (if-else az if előtt)
        if matches and (best is None or len(line_templates) > best[0]):
            best = (len(line_templates), template, block_type, fields, bodies)

    if best is None:
        node = nodes[i]
        if indent_error is not None:
            raise ProgramParseError(indent_error.line_no, "váratlan behúzás: az előző utasításnak nem lehet belső része")
        if _is_continuation_line(node.text):
            raise ProgramParseError(node.line_no, f"a(z) '{node.text}' sor előtt nincs vele azonos behúzású, hozzá tartozó blokk")
        raise ProgramParseError(node.line_no, f"ismeretlen utasítás: '{node.text}'")

    used_lines, template, block_type, fields, bodies = best
    statement = ParsedStatement(
        template=template,
        block_type=block_type,
        fields=[_parse_value(text) if kind == "#" else text for kind, text in fields],
        bodies=[_parse_statements(body) for body in bodies],
        line_no=nodes[i].line_no,
    )
    return statement, used_lines


def _is_continuation_line(text):
    """Olyan sor-e, ami csak egy blokk folytatása lehet (pl. "else")."""
    for template, _ in BLOCK_TEMPLATES.values():
        for segment in template.split("@")[1:]:
            if segment and _match_line(segment, text) is not None:
                return True
    return False


def _value_operators():
    binary, prefix = [], []
    for template, _ in VALUE_TEMPLATES.values():
        if len(template) > 2 and template[0] == template[-1] == "$" and "$" not in template[1:-1]:
            binary.append(template[1:-1])      # "$+$" -> "+"
        elif len(template) > 1 and template.endswith("$") and "$" not in template[:-1]:
            prefix.append(template[:-1])       # "not$" -> "not"
    return binary, prefix


def _operator_pattern(operators):
    return "|".join(
        rf"\b{re.escape(op)}\b" if op.isalnum() else re.escape(op)
        for op in sorted(operators, key=len, reverse=True)  # "<=" előbb, mint "<"
    )


_BINARY_OPERATORS, _PREFIX_OPERATORS = _value_operators()
_BINARY_OPERATOR_RE = re.compile(_operator_pattern(_BINARY_OPERATORS))
_ENDS_WITH_OPERATOR_RE = re.compile(rf"(?:{_operator_pattern(_BINARY_OPERATORS + _PREFIX_OPERATORS)})\s*$")


def _parse_value(text):
    """Érték szövege -> ParsedValue (vagy None, ha üres). A mezők szabad szövegek,
    így pl. "a + b + c" az ("a + b", "c") vágással is pontosan visszaalakítható."""
    text = text.strip()
    if not text:
        return None

    best = None
    for match in _BINARY_OPERATOR_RE.finditer(text):
        left, right = text[:match.start()].strip(), text[match.end():].strip()
        if not left or not right or _ENDS_WITH_OPERATOR_RE.search(left):
            continue  # nem kétoperandusú használat, pl. előjel: "x * -1", "isThere -1"
        precedence = BINARY_PRECEDENCE.get(match.group(), 3)
        if best is None or precedence <= best[0]:  # azonos erősségnél a jobb szélső (balra kötés)
            best = (precedence, match.group(), left, right)

    if best is not None:
        _, operator, left, right = best
        return ParsedValue(f"${operator}$", [left, right])

    for operator in _PREFIX_OPERATORS:
        match = re.fullmatch(rf"{re.escape(operator)}\s+(.+)", text)
        if match:
            return ParsedValue(f"{operator}$", [match.group(1).strip()])

    return ParsedValue("$", [text])


class IDE:
    def __init__(self, input_file:str, output_file:str):
        self.input_file = str(input_file)
        self.output_file = str(output_file)

        self.program = self.read_input_file()

        self.window = ctk.CTk()

        self.interpreter = Interpreter("".join(self.program), self.output_file)
        x, y = self.program[0].split(" ")
        for i in range(int(x) + 1):
            self.program.pop(0)

        self.subwindow = Map("Rover",self.window,True, self.interpreter.rover)
        self.subwindow.update()

        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()

        window_width = int(screen_width * 0.6)
        window_height = int(screen_height * 0.6)
        self.window.geometry(f"{window_width}x{window_height}")

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

        # a blokknézet gombjai (a blokknézet hozza létre és törli őket)
        self.side_btn_add = None
        self.side_btn_remove = None
        self.side_btn_move_up = None
        self.side_btn_move_down = None

        # fő content tároló
        self.main_container = CTkXYFrame(self.window, fg_color="#1C1C1C")
        self.main_container.grid(row=1, column=1, padx=(2.5, 5), pady=(0, 5), sticky="nsew")

        self.block_editor = None

        self.action_b1() # blokkos nézet gomb alapból megnyomva

    def read_input_file(self):
        try:
            with open(self.input_file, "r", encoding="utf-8") as f:
                return f.readlines()
        except FileNotFoundError:
            raise FileNotFoundError(f"Nem található a bemeneti fájl! Győződj meg róla, hogy a megadott útvonal helyes! ('{self.input_file}') ({os.listdir()})")

    def show_error(self, title, message):
        # after(): induláskor a főablak még nem látszik; így a hibaablak a mainloop indulása után jön fel
        self.window.after(100, lambda: messagebox.showerror(title, message, parent=self.window))

    def action_b1(self):
        if self.mode == 1:
            return

        # előbb csak értelmezzük a szöveget: ha hibás, a felület érintetlen marad
        try:
            statements = parse_program_text(self.program)
        except ProgramParseError as error:
            self.show_error("A program nem alakítható blokkokká", str(error))
            if self.mode is None:  # induláskor: a hibás program kódnézetben nyílik meg
                self.action_b2()
            return

        self.mode = 1
        self.load_block_view(statements)

        self.button1.configure(state="disabled")
        self.button2.configure(state="normal")

    def action_b2(self):
        if self.mode == 2:
            return

        if self.mode == 1:
            self.sync_program_from_blocks()  # a blokkos szerkesztések ne vesszenek el
        self.unload_block_view()

        self.mode = 2
        self.load_code_view()

        self.button2.configure(state="disabled")
        self.button1.configure(state="normal")

    def sync_program_from_blocks(self):
        if self.block_editor is not None:
            self.program = self.block_editor.get_program_lines()

    def load_code_view(self):
        self.clear_main_container()
        for i in range(len(self.program)):
            self.add_code_row(i+1, self.program[i].rstrip())  # a behúzás (bal oldal) megmarad

    def clear_main_container(self):
        for e in self.main_container.pack_slaves():
            if getattr(e, "is_block", None) == "yessir":
                BlockEditor.destroy_block_tree(e)  # a beágyazott blokkokkal együtt
            else:
                e.destroy()

    def add_code_row(self, line_num, code):
        row_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        row_frame.pack(fill="x", anchor="w", pady=1)

        line_num_section = ctk.CTkLabel(
            row_frame,
            text=str(line_num),
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

    def load_block_view(self, statements):
        self.clear_main_container()

        self.block_editor = BlockEditor(self.main_container, self.window)
        self.block_editor.build_program(statements)

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
        for button in (self.side_btn_add, self.side_btn_remove, self.side_btn_move_up, self.side_btn_move_down):
            if button is not None:
                button.destroy()
        self.side_btn_add = None
        self.side_btn_remove = None
        self.side_btn_move_up = None
        self.side_btn_move_down = None

        self.clear_main_container()
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
        i=0
        while self.interpreter.runLine() != -1:
            self.subwindow.update()
            i += 1
            print(i)
            time.sleep(1)

    def debug(self):
        pass

    def save(self):
        if self.mode == 1:
            self.sync_program_from_blocks()
        with open(self.input_file, "w", encoding="utf-8") as f:
            f.writelines(self.program)
        self.window.title(f"MazsolaÉsTádé MineScript editor  <<  {self.input_file}")

class BlockEditor:
    INDENT = "  "  # behúzás szintenként a visszaalakított szövegben

    def __init__(self, container, window):
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

    # ------------------------------------------------------------------
    # Szöveg -> blokkok (a parse_program_text() eredményéből)
    # ------------------------------------------------------------------

    def build_program(self, statements):
        for statement in statements:
            self._build_statement(statement, self.container)

    def _build_statement(self, statement, target_container):
        # Minden utasításblokk a fő tároló gyereke (ugyanúgy, mint az add_block-nál),
        # a beágyazást a pack(in_=...) adja: így a mozgatás és a visszaalakítás is működik.
        # A külső blokk előbb jön létre, mint a belsők, így a belsők alapból fölötte vannak.
        block, sub_containers = self.make_block(self.container, statement.template, statement.block_type)
        if target_container is not self.container:
            block.pack(in_=target_container, pady=5, padx=5, anchor="w")

        fields = iter(statement.fields)
        bodies = iter(statement.bodies)
        for widget in sub_containers:
            if isinstance(widget, ctk.CTkEntry):
                widget.insert(0, next(fields))
            elif getattr(widget, "container_type", None) == "#":
                value = next(fields)
                if value is not None:
                    self._build_value(value, widget)
            elif getattr(widget, "container_type", None) == "@":
                for inner_statement in next(bodies):
                    self._build_statement(inner_statement, widget)
        return block

    def _build_value(self, value, slot):
        _, sub_containers = self.make_block(slot, value.template, "value")
        entries = [w for w in sub_containers if isinstance(w, ctk.CTkEntry)]
        for entry, text in zip(entries, value.fields):
            entry.insert(0, text)

    # ------------------------------------------------------------------
    # Blokkok -> szöveg
    #
    # A geometriakezelők (pack / grid) szerint járjuk be a felületet,
    # NEM winfo_children() és NEM képernyő-koordináták alapján: a beágyazott
    # utasításblokkok a fő tároló gyerekei, a beágyazást csak a pack(in_=...)
    # adja. Ezt a pack_slaves() látja, pakolási sorrendben.
    # ------------------------------------------------------------------

    def reconstruct_program_text(self, container=None, depth=0):
        """A tárolóban (alapból a fő tárolóban) lévő program szövege."""
        if container is None:
            container = self.container
        return "\n".join(self._statement_lines(container, depth))

    def get_program_lines(self):
        """A program a beolvasott fájllal azonos alakban (sorok, sorvégi \\n-nel)."""
        return [line + "\n" for line in self.reconstruct_program_text().splitlines()]

    def _statement_lines(self, container, depth):
        lines = []
        for block in container.pack_slaves():  # a pack(in_=...)-nel bepakoltak is
            if getattr(block, "is_block", None) == "yessir":
                lines.extend(self._block_lines(block, depth))
        return lines

    def _block_lines(self, block, depth):
        lines = []
        for part in self._block_parts(block):
            if getattr(part, "container_type", None) == "@":
                lines.extend(self._statement_lines(part, depth + 1))
            elif getattr(part, "is_row", None) == "yessir":
                text = self._row_text(part)
                if text:  # az utolsó '@' utáni üres sort kihagyjuk
                    lines.append(self.INDENT * depth + text)
        return lines

    @staticmethod
    def _block_parts(block):
        """A blokk sorai és '@' tárolói fentről lefelé.
        A grid_slaves() a legutoljára elhelyezettel kezd, ezért sorszám szerint rendezünk."""
        return sorted(block.grid_slaves(), key=lambda w: int(w.grid_info()["row"]))

    def _row_text(self, row):
        tokens = []
        for child in row.pack_slaves():
            if isinstance(child, ctk.CTkLabel):
                tokens.append(child.cget("text").strip())
            elif isinstance(child, ctk.CTkEntry):
                tokens.append(child.get().strip())
            elif getattr(child, "container_type", None) == "#":
                for value_block in child.pack_slaves():
                    if getattr(value_block, "is_block", None) == "yessir":
                        tokens.append(self._value_text(value_block))
        return " ".join(t for t in tokens if t)

    def _value_text(self, value_block):
        rows = [p for p in self._block_parts(value_block) if getattr(p, "is_row", None) == "yessir"]
        return " ".join(t for t in (self._row_text(r) for r in rows) if t)

    # ------------------------------------------------------------------

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

        self.destroy_block_tree(self.selected_block)
        self.selected_block = None
        self.selected_block_original_color = None

    @staticmethod
    def destroy_block_tree(block):
        # A beágyazott utasításblokkok a fő tároló gyerekei, csak bele vannak pakolva
        # a '@' tárolókba, ezért a block.destroy() nem viszi magával őket.
        for part in block.grid_slaves():
            if getattr(part, "container_type", None) == "@":
                for inner in part.pack_slaves():
                    BlockEditor.destroy_block_tree(inner)
        block.destroy()

    def add_block(self):
        contents, block_type = self.block_selector()
        if not contents:  # a választóablakot választás nélkül zárták be
            return
        self.make_block(self.container, contents, block_type)

    def add_value_block(self, parent):
        contents, block_type = self.value_block_selector()
        if not contents:  # a választóablakot választás nélkül zárták be
            return

        for e in parent.pack_slaves():
            if e is self.selected_block:
                self.selected_block = None
                self.selected_block_original_color = None
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

    def lift_block(self, block):
        # Csak utasításblokkokat emelünk: a beágyazott blokkok a fő tároló gyerekei,
        # ezért a külső blokk fölé kell kerülniük. (A régi változat minden gyereket
        # emelt, köztük a CTk widgetek belső CTkCanvas-át is; tkinter.Canvas-on a
        # lift() a tag_raise()-t hívja, ami argumentum nélkül TclError-t dob.)
        block.lift()
        for part in self._block_parts(block):
            if getattr(part, "container_type", None) == "@":
                for inner in part.pack_slaves():
                    self.lift_block(inner)

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

        # választó lista
        scroll_frame = ctk.CTkScrollableFrame(selector_window, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        def make_selection(values):
            nonlocal selected_data
            selected_data = values
            selector_window.destroy()

        for display_name, values in BLOCK_TEMPLATES.items():
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

        # választó lista
        scroll_frame = ctk.CTkScrollableFrame(selector_window, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        def make_selection(values):
            nonlocal selected_data
            selected_data = values
            selector_window.destroy()

        for display_name, values in VALUE_TEMPLATES.items():
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