import time
import board
import pwmio
import os
import socketpool
import wifi
import rtc
import adafruit_ntp
from adafruit_motor import servo

# Settings
MILITARY_TIME = False
RESYNC_HOURS = 4
TZ_OFFSET = -4
DEBUG = False

# PWM Outputs from board to servos
PIN_LIST = [board.IO4, board.IO3, board.IO1, board.IO0]

# Servo settings.
MIN_PULSE = 500
MAX_PULSE = 2500
FREQUENCY = 50
DUTY_CYCLE = 2**15

# Create stop points
STOPS_LIST = [
    [166, 150, 135, 112, 94, 77, 59, 42, 24, 7],
    [166, 150, 135, 112, 94, 77, 59, 42, 24, 7],
    [166, 150, 135, 112, 94, 77, 59, 42, 24, 7],
    [166, 150, 135, 112, 94, 77, 59, 42, 24, 7]
]

LAST_POSITION = [
    STOPS_LIST[0][0],
    STOPS_LIST[1][0],
    STOPS_LIST[2][0],
    STOPS_LIST[3][0]
]

# Connect to wifi. Done this way to provide socketpool for NTP use.
def wifiConnect():
    try:
        ssid = os.getenv("CIRCUITPY_WIFI_SSID")
        password = os.getenv("CIRCUITPY_WIFI_PASSWORD")
        print("Connecting to", ssid)
        wifi.radio.connect(ssid, password)
        print("Connected to", ssid, " IP: ", wifi.radio.ipv4_address)
    except:
        print("Failed to connect to wifi.")

    return(socketpool.SocketPool(wifi.radio))

# Sync time via NTP and set board internal clock accordingly
def syncTime():
    try:
        # Get current time from NTP
        pool = wifiConnect();
        ntp = adafruit_ntp.NTP(pool, tz_offset=TZ_OFFSET)
        rtc.RTC().datetime = ntp.datetime
        print("Time syncronized.")
    except:
        print("Failed to sync time.")

    return(time.time())

# Create servo list
def getServoList():
    servo_list = []
    for pin in PIN_LIST:
        servo_list.append(
            servo.Servo(
            pwmio.PWMOut(
                pin,
                duty_cycle=DUTY_CYCLE,
                frequency=FREQUENCY
            ),
            min_pulse = MIN_PULSE,
            max_pulse = MAX_PULSE
        )
    )
    return(servo_list)

# return a 4 digit number with the current time (eg: 11:42am -> 1142)
def getFourDigitTime(t):
    hour = t.tm_hour
    minute = t.tm_min

    # Logic for 12hr time
    if not MILITARY_TIME:
        if hour > 12:
            hour = hour-12

    return(hour * 100 + minute)

# Return the single digit at the nth position of a number
def getDigit(number, n):
    x = number // 10**n % 10
    return(x)

# Take a single digit and display it on the clock at a specified position
def displayDigit(digit, position, servos):

    # Get positions
    old_pos = LAST_POSITION[position]
    new_pos = STOPS_LIST[position][digit]

    print("Moving servo from",old_pos,"to",new_pos)

    # Determine the direction the servo will spin
    increment = 1
    if (old_pos > new_pos):
        increment = -1
        
    # Do degree incremental steps to slow the transition (and reduce noise)
    for i in range(old_pos,new_pos + increment, increment):
        servos[position].angle = i
        print(i,"", end='')
        time.sleep(0.02)  

    # Release servo
    servos[position].angle = None    
    print("Digit Done")

    # Record the new position
    LAST_POSITION[position] = new_pos  
        
    return
    
# Display the passed 4 digit number on the clock
def displayTime(t, servos):
    for i in range(4):
        digit = getDigit(t, i)
        print("Displaying digit", digit, "at position ", 3-i)
        displayDigit(digit, 3-i, servos)
    
    print("Done update")
    return

# Main program
if __name__ == "__main__":        
            
    # Set up an array of the 4 digit servos
    servos = getServoList()
    
    # Continuous Counter on all digits for testing
    if DEBUG:
        while True:
            for j in range(10):
                for i in range(3):
                    displayDigit(j, i, servos)
                    print(j,"at position",i)
            print("loop")
                 
    # Sync the board clock via ntp and record current time
    sync_time = syncTime()
    
    # Get an initial 4 digit int for time
    last_time = getFourDigitTime(time.localtime())
    
    # Display the initial time
    displayTime(last_time, servos)

    # Start the clock update loop
    while True:

        # check if time needs to be resynced
        if(time.time() - sync_time > RESYNC_HOURS * 3600):
            sync_time = syncTime()

        # Get the current time
        new_time = getFourDigitTime(time.localtime())

        # Check if the time has changed
        if(last_time != new_time):
            # Time has changed, update the clock
            print("Updating time to: ", new_time) 
            displayTime(new_time, servos)
            # New time now becomes old time
            last_time = new_time

        time.sleep(1)


