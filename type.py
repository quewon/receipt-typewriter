import sys
import os
import termios
import tty
import select
import usb.core
from escpos.printer import Usb

line_limit = 32 # 58mm printer default

def find_usb_printer():
    for device in usb.core.find(find_all=True):
        for cfg in device:
            for intf in cfg:
                if intf.bInterfaceClass == 7: # printer class
                    in_ep = out_ep = None
                    for ep in intf:
                        if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN:
                            in_ep = ep.bEndpointAddress
                        else:
                            out_ep = ep.bEndpointAddress
                    return device.idVendor, device.idProduct, in_ep, out_ep

try:
    vendor, product, in_ep, out_ep = find_usb_printer()
    p = Usb(vendor, product, in_ep=in_ep, out_ep=out_ep)
except Exception:
    sys.exit("printer not found.")

line = [{ 'text': "" }]
style = { 'bold': False, 'double_width': False }
fd = sys.stdin.fileno()

print("""┌------------------------------┐
│ RECEIPT PRINTER TYPEWRITER   │
│                              │
│ ENTER to print/linefeed.     │
│ Ctrl+B to toggle \033[1mbold\033[0m.       │
│ Ctrl+W to toggle w i d t h . │
│                              │
│ ESCAPE twice to quit.        │
└------------------------------┘
""")

def read_key():
    ch = os.read(fd, 1).decode("utf-8", "replace")
    if ch != "\x1b":
        return ch
    if select.select([fd], [], [], 0.01)[0]:
        seq = os.read(fd, 1).decode("utf-8", "replace")
        if seq in ("[", "O"):
            if select.select([fd], [], [], 0.01)[0]:
                return "\x1b" + seq + os.read(fd, 1).decode("utf-8", "replace")
            return "\x1b" + seq
        return "\x1b" + seq
    return "\x1b"

def print_line():
    for part in line:
        p._raw(b'\x1b\x40')
        p.set(bold='bold' in part, double_width='double_width' in part)
        p.text(part['text'])
    p.text("\n")
    line.clear()
    line.append({ 'text': "" })
    if style['bold']:
        line[-1]['bold'] = True
    #if style['underline']:
    #    line[-1]['underline'] = True
    if style['double_width']:
        line[-1]['double_width'] = True
    sys.stdout.write("\r\n")
    sys.stdout.flush()

def total_len(line):
    l = 0
    for part in line:
        part_len = len(part['text'])
        l += part_len * 2 if 'double_width' in part else part_len
    return l

old_settings = termios.tcgetattr(fd)
try:
    tty.setcbreak(fd)
    esc_pending = False

    while True:
        ch = read_key()
        if ch == "\x1b": # escape
            if esc_pending:
                break  # ESC twice -> quit
            esc_pending = True
            continue
        esc_pending = False

        if ch.startswith("\x1b["): # arrow keys and other csi sequences
            pass
        elif ch.isprintable():
            if 'double_width' in line[-1] and total_len(line) >= line_limit - 1:
                print_line()
            line[-1]['text'] += ch
            sys.stdout.write(ch)
            if 'double_width' in line[-1]:
                sys.stdout.write(" ")
            sys.stdout.flush()
            if total_len(line) >= line_limit:
                print_line()
        elif ch in ("\r", "\n"):
            print_line()
        elif ch == "\x7f": # backspace
            if line[-1]['text'] == "":
                if len(line) > 1:
                    line = line[:-1]
                    line[-1]['text'] = line[-1]['text'][:-1]
                    style['bold'] = 'bold' in line[-1]
                    #style['underline'] = 'underline' in line[-1]
                    style['double_width'] = 'double_width' in line[-1]
                    sys.stdout.write('\033[0m') # reset everything
                    sys.stdout.write('\033[1m' if style['bold'] else '')
                    sys.stdout.write('\033[4m' if style['underline'] else '')
                    sys.stdout.flush()
                else:
                    line[0] = { 'text': "" }
                    style['bold'] = False
                    #style['underline'] = False
                    style['double_width'] = False
                    sys.stdout.write('\033[0m') # reset everything
                    sys.stdout.flush()
                    continue
            else:
                line[-1]['text'] = line[-1]['text'][:-1]
            if 'double_width' in line[-1]:
                sys.stdout.write("\b\b  \b\b")
            else:
                sys.stdout.write("\b \b")
            sys.stdout.flush()
        elif ch == '\x02': #ctrl+b
            style['bold'] = not style['bold']
            sys.stdout.write('\033[1m' if style['bold'] else '\033[22m')
            sys.stdout.flush()
            if len(line[-1]['text']) > 0 and ('bold' in line[-1]) != style['bold']:
                line.append({ 'text': "" })
            if style['bold']:
                line[-1]['bold'] = True
            elif 'bold' in line[-1]:
                del line[-1]['bold']
        #elif ch == '\x15': #ctrl+u
        #    style['underline'] = not style['underline']
        #    sys.stdout.write('\033[4m' if style['underline'] else '\033[24m')
        #    sys.stdout.flush()
        #    if len(line[-1]['text']) > 0 and ('underline' in line[-1]) != style['underline']:
        #        line.append({ 'text': "" })
        #    if style['underline']:
        #        line[-1]['underline'] = True
        #    elif 'underline' in line[-1]:
        #        del line[-1]['underline']
        elif ch == '\x17': #ctrl+w
            style['double_width'] = not style['double_width']
            if len(line[-1]['text']) > 0 and ('double_width' in line[-1]) != style['double_width']:
                line.append({ 'text': "" })
            if style['double_width']:
                line[-1]['double_width'] = True
            elif 'double_width' in line[-1]:
                del line[-1]['double_width']
except KeyboardInterrupt:
    pass

termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
sys.stdout.write("\r\n")
sys.stdout.flush()