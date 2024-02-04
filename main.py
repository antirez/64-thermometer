import dht, machine, time, random
from machine import Pin, SPI
import st7789_base, st7789_ext, dht

display = st7789_ext.ST7789(
    SPI(1, baudrate=40000000, phase=0, polarity=0),
    160, 128,
    reset=machine.Pin(2, machine.Pin.OUT),
    dc=machine.Pin(4, machine.Pin.OUT),
    cs=machine.Pin(10, machine.Pin.OUT),
    inversion = False,
)

display.init(landscape=True,mirror_y=True)
backlight = Pin(5,Pin.OUT)
backlight.on()

bg_color = display.color(0x00,0x00,0xff) # Inner screen
fg_color = display.color(0x00,0x88,0xff) # Border + text

# Show the commodor 64 border/background colors on the screen.
# If show_banner is true also writes some C64 startup text.
# in the center-upper part.
#
# If type_text is given, the provided text is typed on the
# screen, line by line (type_text must be an array of strings).
def c64_screen(show_banner=False, type_text=False):
    banner = "** C64 BASIC **"
    display.fill(fg_color)
    bw = display.width//10 # Border width
    display.rect(bw,bw,display.width-bw*2,display.height-bw*2,bg_color,True)
    y = bw+2 # Where to type the next text
    if show_banner:
        spacing = (display.width-bw*2-(len(banner)*8))//2
        display.text(bw+spacing,y,banner,fg_color,bg_color)
        y += 16
        display.text(bw+2,y,"READY.",fg_color,bg_color)
        y += 8
    if type_text:
        for line in type_text:
            c64_type_text(bw+2,y,line,hide_cursor=True)
            y += 8

# Simulates typing the provided text at x,y.
# The function is blocking for all the time needed for the
# final text to appear.
# This is used by c64_screen().
def c64_type_text(x,y,text,hide_cursor=False):
    for i in range(len(text)+1):
        typed = text[:i]
        if len(typed): display.text(x,y,typed,fg_color,bg_color)
        # Don't erase the previous cursor as it was partially
        # replaced (almost... just 1 colum left, so we end with 9x8 cursor)
        # by the text itself.
        display.rect(x+8*len(typed)+1,y,8,8,fg_color,fill=True)
        time.sleep_ms(random.getrandbits(8))
    if hide_cursor:
        # Erase a bit more than 8x8 because of the artifact above.
        display.rect(x+8*len(text),y,9,8,bg_color,fill=True)

c64_screen(show_banner=True,type_text=["LOAD *,8,1","RUN"])
while True:
    d = dht.DHT22(Pin(16))
    d.measure()
    print(d.temperature(), d.humidity())
    time.sleep(1)
