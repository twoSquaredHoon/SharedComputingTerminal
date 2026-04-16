import shutil
import os

RED   = "\033[38;2;180;50;50m"
DIM   = "\033[2m"
BOLD  = "\033[1m"
RESET = "\033[0m"

def draw_splash():
    w = shutil.get_terminal_size().columns

    # inner_w = everything between the two │ chars
    inner_w = w - 2

    top    = "╭" + "─" * inner_w + "╮"
    bottom = "╰" + "─" * inner_w + "╯"

    def row(text=""):
        # Strip ANSI from text to get visible length
        import re
        visible = re.sub(r'\033\[[^m]*m', '', text)
        pad = " " * (inner_w - len(visible))
        print(f"{RED}{BOLD}│{RESET}{text}{pad}{RED}{BOLD}│{RESET}")

    print()
    print(f"{RED}{BOLD}{top}{RESET}")
    row()
    row(f"  {RED}{BOLD}SharedComputing{RESET}")
    row(f"  {DIM}v0.1.0{RESET}")
    row()
    row(f"  {DIM}Distributed ML training — local & simple{RESET}")
    row(f"  {DIM}Made by YSL, SHJ, SHL{RESET}")
    row()
    print(f"{RED}{BOLD}{bottom}{RESET}")
    print()

if __name__ == "__main__":
    draw_splash()
    input(f"  {DIM}Press Enter to continue...{RESET}\n")
