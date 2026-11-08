import re

def parse_indentation(lines):
    def parse_block(index, base_indent):
        result = []

        while index < len(lines):
            line = lines[index]
            stripped = line.lstrip()
            indent = len(line) - len(stripped)

            if not stripped:
                index += 1
                continue

            if indent < base_indent:
                break

            if indent > base_indent:
                nested, index = parse_block(index, indent)
                result.append(nested)
            else:
                result.append(stripped)
                index += 1

        return result, index

    if not lines:
        return []

    first_indent = min(
        len(line) - len(line.lstrip())
        for line in lines if line.strip()
    )

    result, _ = parse_block(0, first_indent)
    return result





def translate(program):
    def process(items):
        output = []

        for item in items:
            if isinstance(item, list):
                output.append("@" + process(item) + "@")
                continue

            line = item.strip()

            # Variable assignment
            match = re.match(r"set\s+(\w+)\s+to\s+(.+)", line)

            if match:
                variable, expression = match.groups()

                # Wrap every word/number except keywords
                expression = re.sub(
                    r"\b[a-zA-Z_]\w*\b|\b\d+\b",
                    lambda m: m.group()
                    if m.group() in ("isThere", "not")
                    else f"${m.group()}$",
                    expression
                )

                output.append(
                    f"set ${variable}$ to #{expression}#"
                )

            # step forward
            elif match := re.match(r"step forward\s+(.+)", line):
                output.append(f"step forward ${match.group(1)}$")

            # turn by
            elif match := re.match(r"turn by\s+(.+)", line):
                output.append(f"turn by ${match.group(1)}$")

            # print
            elif match := re.match(r"print\s+(.+)", line):
                output.append(f"print ${match.group(1)}$")

            else:
                output.append(line)

        return "\n".join(output)

    return process(program)


if __name__ == "__main__":
    prog = """\
set count to 0
set fal to isThere 1
set megy to not fal
while megy
  set arany to isThere 2
  if arany
    step forward 1
    mine here
    set count to count + 1
  else
    step forward 1
  set fal to isThere 1
  set megy to not fal
print count\
"""
    prog = [line for line in prog.split('\n')]
    print(parsed:=parse_indentation(prog))
    print(translate(parsed))
