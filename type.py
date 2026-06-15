import readchar
import sys
import usb.core
from escpos.printer import Usb

global p
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
style = { 'bold': False, 'underline': False, 'double_width': False }

print("""┌──────────────────────────────┐
│ RECEIPT PRINTER TYPEWRITER   │
│                              │
│ ENTER to print/linefeed.     │
│ Ctrl+B to toggle \033[1mbold\033[0m.       │
│ Ctrl+U to toggle \033[4munderline\033[0m.  │
│ Ctrl+W to toggle w i d t h . │
│                              │
│ ESCAPE twice to quit.        │
└──────────────────────────────┘
""")

def print_line():
    for part in line:
        p._raw(b'\x1b\x40')
        p.set(bold='bold' in part, underline='underline' in part, double_width='double_width' in part)
        p.text(part['text'])
    p.text("\n")
    line.clear()
    line.append({ 'text': "" })
    if style['bold']:
        line[-1]['bold'] = True
    if style['underline']:
        line[-1]['underline'] = True
    if style['double_width']:
        line[-1]['double_width'] = True
    sys.stdout.write("\r\n")
    sys.stdout.flush()

try:
    while True:
        ch = readchar.readkey()
        if ch.isprintable():
            line[-1]['text'] += ch
            sys.stdout.write(ch)
            if 'double_width' in line[-1]:
                sys.stdout.write(" ")
            sys.stdout.flush()
            total_len = 0
            for part in line:
                part_len = len(part['text'])
                total_len += part_len * 2 if 'double_width' in part else part_len
            if total_len % line_limit == 0:
                print_line()
        elif ch == "\x1b\x1b": #escape
            break
        elif ch == readchar.key.ENTER:
            print_line()
        elif ch == readchar.key.BACKSPACE:
            if line[-1]['text'] == "":
                if len(line) > 1:
                    line = line[:-1]
                    line[-1]['text'] = line[-1]['text'][:-1]
                    style['bold'] = 'bold' in line[-1]
                    style['underline'] = 'underline' in line[-1]
                    style['double_width'] = 'double_width' in line[-1]
                    sys.stdout.write('\033[0m') # reset everything
                    sys.stdout.write('\033[1m' if style['bold'] else '')
                    sys.stdout.write('\033[4m' if style['underline'] else '')
                    sys.stdout.flush()
                else:
                    continue
            else:
                line[-1]['text'] = line[-1]['text'][:-1]
            if 'double_width' in line[-1]:
                sys.stdout.write("\b\b  \b\b")
            else:
                sys.stdout.write("\b \b")
            sys.stdout.flush()
        elif ch == readchar.key.UP or ch == readchar.key.DOWN or ch == readchar.key.LEFT or ch == readchar.key.RIGHT:
            pass # ignore arrow keys
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
        elif ch == '\x15': #ctrl+u
            style['underline'] = not style['underline']
            sys.stdout.write('\033[4m' if style['underline'] else '\033[24m')
            sys.stdout.flush()
            if len(line[-1]['text']) > 0 and ('underline' in line[-1]) != style['underline']:
                line.append({ 'text': "" })
            if style['underline']:
                line[-1]['underline'] = True
            elif 'underline' in line[-1]:
                del line[-1]['underline']
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

sys.stdout.write("\r\n")
sys.stdout.flush()