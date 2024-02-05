import dht, machine, time, random
from machine import Pin, SPI
import st7789_base, st7789_ext, dht

########################### GLOBAL STATE AND CONFIG ############################

sampling_period = 10 # Read temperature/humidity every N seconds.
                     # Better if multiple of 60.
# We take temp readings of the last hour in high resolution, and
# historical data of the last couple of days with hourly resolution.
# In both cases, we only take the latest 'display.width' samples as
# anyway this is max data we can should as one-pixel bars.
ts_h = []  # Temperatures sampled every 'sampling_period'. Few hours.
ts_d = []  # Temperatures sampled every 15 min. A couple of days.
sph = 3600//sampling_period # Samples per hour at sampling_period.
spq = sph//4 # Samples per 15 minutes.

# Display and backlight
display = st7789_ext.ST7789(
    SPI(1, baudrate=40000000, phase=0, polarity=0),
    160, 128,
    reset=machine.Pin(2, machine.Pin.OUT),
    dc=machine.Pin(4, machine.Pin.OUT),
    cs=machine.Pin(10, machine.Pin.OUT),
    inversion = False,
)

# Colors (from the C64 color table at https://www.c64-wiki.com/wiki/Color)
# r,g,b sampled from the screenshot provided.
c64color = {
    'black': display.color(0,0,0),
    'white': display.color(255,255,255),
    'red': display.color(157,69,60),
    'cyan': display.color(110,199,207),
    'violet': display.color(157,77,189),
    'green': display.color(92,179,57),
    'blue': display.color(75,57,176),
    'yellow': display.color(211,223,109),
    'orange': display.color(161,102,28),
    'brown': display.color(107,81,0),
    'light_red': display.color(204,125,117),
    'grey1': display.color(96,96,96),
    'grey2': display.color(138,138,138),
    'light_green': display.color(162,238,133),
    'light_blue': display.color(137,121,230),
    'grey3': display.color(179,179,179),
}

bg_color = c64color['blue']         # Screen background
fg_color = c64color['light_blue']   # Screen border
graph_color1 = c64color['violet'] # Temp graph 1
graph_color2 = c64color['orange'] # Temp graph 2

# Hardware initialization.
display.init(landscape=True,mirror_y=True)
backlight = Pin(5,Pin.OUT)
backlight.on()

################################# IMPLEMENTATION ###############################

# How much border to use, compared to screen size?
def get_border_width():
    return display.width//10 # 10% of width

# Show the commodor 64 border/background colors on the screen.
# If show_banner is true also writes some C64 startup text.
# in the center-upper part.
#
# If type_text is given, the provided text is typed on the
# screen, line by line (type_text must be an array of strings).
def c64_screen(show_banner=False, type_text=False):
    banner = "** C64 BASIC **"
    display.fill(fg_color)
    bw = get_border_width()
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

# Show a big centered text. The text is centered in the sub-window
# identified by the rectangle with left corner x,y of size width x height
# pixels. x_align and y_align control how do we want the text to aligned
# in the horizonal and vertical axis.
ALIGN_MID = const(1)        # Both for x_align and y_align
ALIGN_LEFT = const(0)
ALIGN_RIGHT = const(2)
ALIGN_TOP = const(3)
ALIGN_BOTTOM = const(4)
def big_centered_text(x,y,width,height,txt,color,upscaling,*,x_align=ALIGN_MID,y_align=ALIGN_MID):
    char_size = upscaling*8
    rx = 0 # left as default
    ry = 0 # top as default
    if x_align == ALIGN_MID:
        rx = int((width - char_size*len(txt))/2)
    elif x_align == ALIGN_RIGHT:
        rx = width - char_size*len(txt)
    if y_align == ALIGN_MID:
        ry = int((height - char_size)/2)
    elif y_align == ALIGN_BOTTOM:
        ry = height - char_size
    display.upscaled_text(x+rx,y+ry,txt,color,upscaling=upscaling)

# Main view where temp and humidity are shown.
# If the temperatures time series 'ts' is given, a graph
# of the history is displayed as well. 'color_step' represents
# after how many data samples to change color, alternating between
# two colors, so that different hours/minutes are marked in this way.
def main_view(title,temp,humidity,ts,color):
    display.fill(display.color(0,0,0))
    upscaling = 2
    big_centered_text(2,2,display.width-2,display.height-2,str(temp),
            display.color(255,255,255),2,
            x_align=ALIGN_LEFT,
            y_align=ALIGN_TOP)
    big_centered_text(2,2,display.width-2,display.height-2,str(humidity),
            display.color(255,255,255),2,
            x_align=ALIGN_RIGHT,
            y_align=ALIGN_TOP)
    big_centered_text(2,18,display.width-2,display.height-18,"temp",
            display.color(50,50,50),1,
            x_align=ALIGN_LEFT,
            y_align=ALIGN_TOP)
    big_centered_text(2,18,display.width-2,display.height-18,"igro",
            display.color(50,50,50),1,
            x_align=ALIGN_RIGHT,
            y_align=ALIGN_TOP)
    
    if ts and len(ts):
        # Graph drawing.
        bottom_margin = 10
        ybase = display.height-bottom_margin-1 # y coordiante of bars start
        maxlen = display.height - (16+8+5) # header text + padding.
        maxlen -= bottom_margin # Space at the bottom for min/max/info.

        maxtemp = max(ts)
        mintemp = min(ts)
        delta = maxtemp-mintemp
        for i in range(len(ts)):
            # 75% of space is the dynamic range, 25% if fixed.
            thisdelta = ts[i]-mintemp
            thislen = maxlen*0.25
            if delta: thislen += thisdelta/delta*maxlen*0.75
            display.vline(ybase,ybase-int(thislen),i,color)

        # Draw the footer with min/max/info
        big_centered_text(0,display.height-8,display.width,display.height,f"min:%.1f" % mintemp,display.color(0,0xcc,0x55),1,x_align=ALIGN_LEFT,y_align=ALIGN_TOP)
        big_centered_text(0,display.height-8,display.width,display.height,f"max:%.1f" % maxtemp,display.color(0x88,0,0),1,x_align=ALIGN_RIGHT,y_align=ALIGN_TOP)

        # Draw the title of the graph
        big_centered_text(0,display.height//2,display.width,display.height//2,
                          title,display.color(0xcc,0xcc,0xcc),1,
                          x_align=ALIGN_MID,y_align=ALIGN_MID)

# Persist hourly/daily time series on the device flash.
def save_state():
    f = open("history.txt","wb")
    f.write("ts_h = %s\n" % repr(ts_h))
    f.write("ts_d = %s\n" % repr(ts_d))
    f.close()

# Load state at startup. So when the device powers up again the graphs
# don't start from scratch.
def load_state():
    try:
        f = open("history.txt","rb")
    except:
        return # ENOENT, likely
    try:
        content = f.read()
        f.close()
        global ts_h, ts_d
        exec(content)
    except Exception as e:
        print("Loading settings: "+str(e))
        pass # Corrupted data?

# Creates a unique fingerprint of the current readings, to update
# the view only if sensor data changes. Our readings are so easy
# that is more memory efficient to just contatenate the strings.
def hash_sensor_data(*args):
    return "_".join([str(x) for x in args])

def main():
    global ts_h, ts_d
    data_hash = None    # Hashing of last data rendered. As long as both
                        # temperature and humidity are the same we don't
                        # refresh them.
    daily_graph = False # Used to alternate between hourly and daily graph.
    # Let's start the show.
    c64_screen(show_banner=True,type_text=["LOAD *,8,1","RUN"])
    loop_count = 1
    load_state()        # Load past data

    while True:
        loop_start = time.ticks_ms()
        d = dht.DHT22(Pin(16))
        d.measure()

        # Print / store the data
        cur_hash = hash_sensor_data(d.temperature(),d.humidity())
        ts_h.append(d.temperature())
        ts_h = ts_h[-display.width:]
        if loop_count % spq == 0 and len(ts_h) >= spq:
            # Every 15 minutes we populate the last days time series.
            ts_d.append(sum(ts_h[-spq:])/spq)
            ts_d = ts_d[-display.width:]
        print("readings",d.temperature(), d.humidity())
        print("ts_h",ts_h)
        print("ts_d",ts_d)

        # From time to time show again the loading screen.
        if loop_count > 1 and random.getrandbits(5) == 0:
            c64_screen(show_banner=True,type_text=["LOAD *,8,1","RUN"])
            data_hash = None # Force refresh of view

        # Display current view
        if cur_hash != data_hash:
            if daily_graph:
                main_view("hourly",d.temperature(),d.humidity(),ts_h,graph_color1)
            else:
                main_view("daily",d.temperature(),d.humidity(),ts_d,graph_color2)
            data_hash = cur_hash
            daily_graph = not daily_graph

        # Wait 10 seconds from the last sensor reading.
        while time.ticks_diff(time.ticks_ms(),loop_start) < sampling_period*1000:
            time.sleep_ms(100)

        loop_count += 1
        if loop_count % 10 == 0: save_state()

# Entry point.
main()
