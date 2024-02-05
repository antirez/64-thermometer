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

# Hardware initialization.
display.init(landscape=True,mirror_y=True)
backlight = Pin(5,Pin.OUT)
backlight.on()

# Colors hand picked to be kinda credible in my cheap TFT display,
# in the hope that the gamma is broken in similar ways.
c64colors = {
    'black': [0,0,0],
    'white': [255,255,255],
    'red': [125,0,0],
    'cyan': [50,199,207],
    'violet': [189,0,189],
    'green': [0,125,0],
    'blue': [3,3,80],
    'yellow': [211,223,0],
    'orange': [180,30,5],
    'brown': [80,20,0],
    'light_red': [200,30,30],
    'grey1': [96,96,96],
    'grey2': [138,138,138],
    'light_green': [40,195,40],
    'light_blue': [20,20,125],
    'grey3': [179,179,179],
}

for k,v in c64colors.items():
    c64colors[k] = display.color(v[0],v[1],v[2])

bg_color = c64colors['blue']         # Screen background
fg_color = c64colors['light_blue']         # Screen border
graph_color1 = c64colors['violet'] # Temp graph 1
graph_color2 = c64colors['orange'] # Temp graph 2

def show_palette():
    j = 0
    for colorname in ['black','white','red','cyan','violet','green','blue','yellow','orange','brown','light_red','grey1','grey2','light_green','light_blue','grey3']:
        xstep = display.width//4
        ystep = display.height//4
        display.rect(j%4*xstep,j//4*ystep,xstep,ystep,c64colors[colorname],fill=True)
        j += 1

# This is only useful to debug the palette in your display.
if False:
    show_palette()
    time.sleep(3600)

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
    display.fill(c64colors['black'])
    upscaling = 2
    big_centered_text(2,2,display.width-2,display.height-2,str(temp),
            c64colors['white'],2,
            x_align=ALIGN_LEFT,
            y_align=ALIGN_TOP)
    big_centered_text(2,2,display.width-2,display.height-2,str(humidity),
            c64colors['white'],2,
            x_align=ALIGN_RIGHT,
            y_align=ALIGN_TOP)
    big_centered_text(2,18,display.width-2,display.height-18,"temp",
            c64colors['grey2'],1,
            x_align=ALIGN_LEFT,
            y_align=ALIGN_TOP)
    big_centered_text(2,18,display.width-2,display.height-18,"igro",
            c64colors['grey2'],1,
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
        big_centered_text(0,display.height-8,display.width,display.height,f"min:%.1f" % mintemp,c64colors['cyan'],1,x_align=ALIGN_LEFT,y_align=ALIGN_TOP)
        big_centered_text(0,display.height-8,display.width,display.height,f"max:%.1f" % maxtemp,c64colors['light_red'],1,x_align=ALIGN_RIGHT,y_align=ALIGN_TOP)

        # Draw the title of the graph
        big_centered_text(0,display.height//2,display.width,display.height//2,
                          title,c64colors['grey3'],1,
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

        # Sometimes DHT11/22 sensors randomly timeout.
        try:
            d.measure()
        except:
            print("Sensor reading failed: check cables and pin configuration")
            time.sleep(1)
            continue

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
