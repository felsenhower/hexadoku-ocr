#!/usr/bin/env python3

import sys
import subprocess
import os
import re

def usage():
    print(("Usage: {} <riddle file> <solution file> " +
           "<riddle output> <solution output>").format(sys.argv[0]))
    sys.exit(0)

def run(command, arguments=[], stdin=None):
    if stdin == None:
        stdin_pipe = open(os.devnull)
    else:
        stdin_pipe = subprocess.PIPE
    stdout, stderr = subprocess.Popen([command] + arguments,
                                      stdin=stdin_pipe,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE).communicate(stdin)
    return stdout, stderr

def is_installed(name):
    try:
        run(name)
    except:
        return False
    return True

def check_dependencies():
    ok = True
    if not is_installed("tesseract"):
        print("tesseract could not be found!")
        ok = False
    if not is_installed("convert"):
        print("convert (ImageMagick) could not be found!")
        ok = False
    if not ok:
        sys.exit(1)

def display(bytes):
    run("display", arguments=["-"], stdin=bytes)

def convert(bytes, arguments, repage=True):
    if repage:
        arguments = ["+repage"] + arguments
    return run("convert", arguments=arguments, stdin=bytes)

def identify(bytes, arguments):
    return run("identify", arguments=arguments, stdin=bytes)

def get_dimensions(bytes):
    width = int(identify(bytes, arguments=["-format", "%w", "-"])[0].decode("utf-8"))
    height = int(identify(bytes, arguments=["-format", "%h", "-"])[0].decode("utf-8"))
    return width, height

def autocrop(bytes, cutoff=3, fuzziness="20%"):
    width, height = get_dimensions(bytes)
    final_width = width - 2 * cutoff
    final_height = height - 2 * cutoff
    return convert(bytes, [
        "-crop", "{0}x{1}+{2}+{2}".format(final_width, final_height, cutoff),
        "-fuzz", str(fuzziness),
        "-trim", "-trim",
        "-", "-"
    ])

def autoscale(bytes, size=750):
    return convert(bytes, [
        "-resize", "{0}x{0}!".format(size),
        "-", "-"
    ])

def autosharpen(bytes, sigma=3.0):
    return convert(bytes, [
        "-sharpen", "0x{0:0.1f}".format(sigma),
        "-", "-"
    ])

def autopad(bytes, border_width=10):
    return convert(bytes, [
        "-bordercolor", "white",
        "-border", str(border_width),
        "-", "-"
    ])

def get_image_part(bytes, y, x):
    width, height = get_dimensions(bytes)
    final_width = width / 4
    final_height = height / 4
    offset_x = int(x * final_width)
    offset_y = int(y * final_height)
    final_width = int(final_width)
    final_height = int(final_height)
    return convert(bytes, [
        "-crop", "{0}x{1}+{2}+{3}".format(final_width, final_height,
                                          offset_x, offset_y),
        "-", "-"
    ])

def tesseract(bytes, psm=10):
    return run("tesseract", [
        "--psm", str(psm),
        "stdin", "-"
    ], stdin=bytes)

sanitize_regex = re.compile(r"[^a-f0-9]")
def sanitize(text):
    return sanitize_regex.sub("", text, re.M)

def ocr(bytes, psm):
    stdout, stderr = tesseract(bytes, psm)
    digit =  stdout.decode("utf-8")
    digit = digit.lower()
    digit = sanitize(digit)
    return digit

def print_matrix(matrix):
    print("[", matrix[0], ",", sep="")
    for line in matrix[1:-1]:
        print(" ", line, ",", sep="")
    print(" ", matrix[-1], "]", sep="")

def do_ocr_cell(bytes):
    width, height = get_dimensions(bytes)
    if (width * height > 1):
        padded, _ = autopad(bytes)
        digit = ocr(padded, psm=10)
        if len(digit) > 1:
            digit = ocr(padded, psm=8)
        if len(digit) > 1:
            digit = digit[0]
    else:
        digit = ""
    if digit == "":
        digit = " "
    return digit

def print_matrix_line(solution, riddle, both, y):
    print("\r | ", "".join(riddle[y]), "  |  ",
                   "".join(solution[y]), "  |  ",
                   "".join(both[y]), "  |",
                   end="", flush=True)

def prepare_image(filename):
    with open(filename, mode='rb') as file:
        bytes = file.read()
    cropped, _ = autocrop(bytes)
    scaled, _ = autoscale(cropped)
    sharp, _ = autosharpen(scaled)
    return sharp

def get_block(image, block_array, y, x):
    if block_array[y][x] == None:
        block, _ = get_image_part(image, y, x)
        block_cropped, _ = autocrop(block)
        block_array[y][x] = block_cropped
        return block_cropped
    else:
        return block_array[y][x]

def extract_row(arr, y):
    return arr[y]

def extract_column(arr, x):
    return [row[x] for row in arr]

def extract_block(arr, y, x):
    return [row[x*4:(x+1)*4] for row in arr[y*4:(y+1)*4]]

def flatten(matrix):
    return [item for sublist in matrix for item in sublist]

def is_valid_part(row):
    occurences = [0 for i in range(16)]
    for chr in row:
        if len(chr) != 1:
            return False
        try:
            corresponding = int("0x" + chr, 0)
        except:
            return False
        occurences[corresponding] += 1
    for i in occurences:
        if i != 1:
            return False
    return True

def check_hexadoku(both):
    okay = True
    for y in range(16):
        if not is_valid_part(extract_row(both, y)):
            print("Row {} is not valid!".format(y+1))
            okay = False
    for x in range(16):
        if not is_valid_part(extract_column(both, x)):
            print("Column {} is not valid!".format(x+1))
            okay = False
    for y in range(4):
        for x in range(4):
            if not is_valid_part(flatten(extract_block(both, y, x))):
                print("Block ({},{}) is not valid!".format(x+1, y+1))
                okay = False

    print("")
    if okay:
        print("Output seems to be valid!")
    else:
        print("Output is not a valid Hexadoku!")
    print("")

def get_hexadokus(riddle_file, solution_file):
    solution_blocks = [ [None for i in range(4)] for j in range(4) ]
    riddle_blocks = [ [None for i in range(4)] for j in range(4) ]
    solution = [ [" " for i in range(16)] for j in range(16) ]
    riddle = [ [" " for i in range(16)] for j in range(16) ]
    both = [ [" " for i in range(16)] for j in range(16) ]
    print_matrix_line(
        [list("    Solution    ")],
        [list("     Riddle     ")],
        [list("      Both      ")],
        0
    )
    print("")
    print_matrix_line(solution, riddle, both, 0)
    riddle_image = prepare_image(riddle_file)
    solution_image = prepare_image(solution_file)
    # Iterate over all 4 rows (16x4) of blocks (4x4) in the Hexadoku (16x16)
    for y_of_block in range(4):
        # For all 4 rows of blocks, iterate over all 4 rows (16x1) of cells
        for y_in_block in range(4):
            # For all 16 rows of cells, iterate over all 4 sub-rows (4x1) of cells
            for x_of_block in range(4):
                # For all sub-rows, iterate over all 4 cells (1x1)
                for x_in_block in range(4):
                    y_global = y_of_block * 4 + y_in_block
                    x_global = x_of_block * 4 + x_in_block
                    solution[y_global][x_global] = "_"
                    riddle[y_global][x_global] = "_"
                    both[y_global][x_global] = "_"
                    print_matrix_line(solution, riddle, both, y_global)
                    riddle_block = get_block(riddle_image, riddle_blocks, y_of_block, x_of_block)
                    cell, _ = get_image_part(riddle_block, y_in_block, x_in_block)
                    cell_cropped, _ = autocrop(cell)
                    digit = do_ocr_cell(cell_cropped)
                    riddle[y_global][x_global] = digit
                    if digit == " ":
                        solution_block = get_block(solution_image, solution_blocks, y_of_block, x_of_block)
                        cell, _ = get_image_part(solution_block, y_in_block, x_in_block)
                        cell_cropped, _ = autocrop(cell)
                        digit = do_ocr_cell(cell_cropped)
                        solution[y_global][x_global] = digit
                        both[y_global][x_global] = digit
                    else:
                        solution[y_global][x_global] = " "
                        both[y_global][x_global] = digit
                    print_matrix_line(solution, riddle, both, y_global)
            print("")
    return solution, riddle, both

def write_tex(output_filename, text):
    with open("template.tex", "r") as template_file:
        template = template_file.read()
        foo = template.replace("<placeholder>", text)
        with open(output_filename, "w") as output_file:
            output_file.write(foo)

def texify(arr, chr):
    output_lines = ["\\firstrow;"]
    sep = "}\\"+ chr + "{"
    start = "\\" + chr + "{"
    end = "}\\nr"
    for line in arr:
        foo = start + sep.join(line) + end
        output_lines.append(foo)
    output = "\n" + "\n".join(output_lines) + "\n"
    return output

def main():
    check_dependencies()
    if len(sys.argv[1:]) != 4:
        usage()
    riddle_file = sys.argv[1]
    solution_file = sys.argv[2]
    riddle_output = sys.argv[3]
    solution_output = sys.argv[4]
    solution, riddle, both = get_hexadokus(riddle_file, solution_file)
    check_hexadoku(both)
    solution_texified = texify(solution, "s")
    riddle_texified = texify(riddle, "p")
    riddle_tex_src = riddle_texified
    write_tex(riddle_output, riddle_tex_src)
    both_tex_src = riddle_texified + "\n" + solution_texified
    write_tex(solution_output, both_tex_src)

main()
