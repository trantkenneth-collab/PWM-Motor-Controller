import RPi.GPIO as GPIO
import time
import threading

#(match the number assinged with it's corresponding color for the jumper calbe to the pi)
# Hardware Pin Assignments (Basically what the button controls, each color represents a different wire connected to the raspberry pi)

MOTOR_PWM_PIN = 12  # Black   -> L293D Pin 1 (Speed Control)
DIR_A_PIN = 16      # Grey    -> L293D Pin 2 (Direction A)
DIR_B_PIN = 18      # White   -> L293D Pin 7 (Direction B)

# Control Buttons (controles the motor speed and direction)
BTN_FWD = 22        # Blue   -> Button 1 (Forward)
BTN_REV = 24        # Green  -> Button 2 (Reverse)
BTN_STOP = 26       # Yellow -> Button 3 (Stop)
BTN_UP = 32         # Orange -> Button 4 (Speed +)
BTN_DOWN = 36       # Red    -> Button 5 (Speed -)

# Standalone Visual Dashboard Indicator LED
LED_INDICATOR = 38  # BROWN WIRE  -> Row 50j (Resistor Bridge to LED)

# Global Variables
motor_speed_pct = 0   # Active velocity: 0% to 100%
motor_direction = "STOP"
keep_blinking = True


# Initialization and pi pin layout intructions
GPIO.setmode(GPIO.BOARD)  # Instructs the Pi to read physical layout numbers

# Safely declare Output registers
OUTPUT_PINS = [MOTOR_PWM_PIN, DIR_A_PIN, DIR_B_PIN, LED_INDICATOR]
GPIO.setup(OUTPUT_PINS, GPIO.OUT)

# Configure all 5 buttons to utilize internal pull-up registers
# This keeps the lines floating at 3.3V until shorted to the Blue Ground Rail
BUTTONS = [BTN_FWD, BTN_REV, BTN_STOP, BTN_UP, BTN_DOWN]
GPIO.setup(BUTTONS, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Establish (PWM) clock at 100Hz frequency
motor_pwm = GPIO.PWM(MOTOR_PWM_PIN, 100)
motor_pwm.start(0)  # Launch with the system completely stopped


# Visual LED indicator of speed
def led_visualizer_thread():
    """Background Thread: Dynamically calculates visual blink rate based on load"""
    global motor_speed_pct, motor_direction, keep_blinking
    while keep_blinking:
        if motor_direction == "STOP" or motor_speed_pct == 0:
            GPIO.output(LED_INDICATOR, GPIO.LOW)
            time.sleep(0.1)
        elif motor_speed_pct <= 60: 
            # Low Speed Zone: Slow safety flash pulse
            GPIO.output(LED_INDICATOR, GPIO.HIGH)
            time.sleep(0.4)
            GPIO.output(LED_INDICATOR, GPIO.LOW)
            time.sleep(0.4)
        else:
            # High Speed Zone: Keep at solid color
            GPIO.output(LED_INDICATOR, GPIO.HIGH)


# Hardware outputs
def update_hardware_outputs():
    """Translates programmatic state math into physical copper line voltages"""
    global motor_speed_pct, motor_direction
    
    if motor_direction == "FORWARD":
        GPIO.output(DIR_A_PIN, GPIO.HIGH)
        GPIO.output(DIR_B_PIN, GPIO.LOW)
        motor_pwm.ChangeDutyCycle(motor_speed_pct)
    elif motor_direction == "REVERSE":
        GPIO.output(DIR_A_PIN, GPIO.LOW)
        GPIO.output(DIR_B_PIN, GPIO.HIGH)
        motor_pwm.ChangeDutyCycle(motor_speed_pct)
    else: # SYSTEM STOPPED (happens if speed = 0, or the STOP button is pressed)
        GPIO.output(DIR_A_PIN, GPIO.LOW)
        GPIO.output(DIR_B_PIN, GPIO.LOW)
        motor_pwm.ChangeDutyCycle(0)
        
    print(f" Fan State | Direction: {motor_direction:<7} | Speed: {motor_speed_pct}%")

# Spin up our visual tracking worker engine in the background
viz_thread = threading.Thread(target=led_visualizer_thread, daemon=True)
viz_thread.start()

# =====================
# Core loop for buttons
# =====================
try:
    print("===========================================================")
    print("PWM Fan controller is now active, press any button to begin")
    print("===========================================================")
    
    while True:
        # Button 1: Forward Loop Activation (Blue Wire)
        if GPIO.input(BTN_FWD) == GPIO.LOW:
            motor_direction = "FORWARD"
            # if motor_speed_pct == 0: 
            # motor_speed_pct = 50 (kept in tags due to not being needed)
            update_hardware_outputs()
            time.sleep(0.3)  # Physical switch debounce delay
            
        # Button 2: Reverse Loop Activation (Green Wire)
        elif GPIO.input(BTN_REV) == GPIO.LOW:
            motor_direction = "REVERSE"
            # if motor_speed_pct == 0: 
            # motor_speed_pct = 50 (kept in tags due to not being needed)
            update_hardware_outputs()
            time.sleep(0.3)
            
        # Button 3: E-STOP Manual Cutoff (Yellow Wire)
        elif GPIO.input(BTN_STOP) == GPIO.LOW:
            motor_direction = "STOP"
            update_hardware_outputs()
            time.sleep(0.3)
            
        # Check Button 4: Speed Increment (+10%) (Orange Wire)
        elif GPIO.input(BTN_UP) == GPIO.LOW:
            if motor_speed_pct < 100:
                motor_speed_pct += 10
                if motor_speed_pct > 100: motor_speed_pct = 100
                if motor_speed_pct <0: motor_speed_pct = 0
                update_hardware_outputs()
            time.sleep(0.3)  
            
        # Check Button 5: Speed Decrement (-10%) (Red Wire)
        elif GPIO.input(BTN_DOWN) == GPIO.LOW:
            if motor_speed_pct > 0:
                motor_speed_pct -= 10
                if motor_speed_pct <0: motor_speed_pct = 0
                update_hardware_outputs()
            time.sleep(0.3)  


#Other functions (Don't really do anything as im running it remotely, the finally is a just in case)
except KeyboardInterrupt:
    print("\n⚠️ Keyboard Override Detected. Halting system core...")

finally:
    # Clear out all hardware registries to prevent pinned high voltage logic states
    keep_blinking = False
    motor_pwm.stop()
    GPIO.cleanup()
    print("🏁 Hardware clean-up executed. All copper lines set to safe ground states.")
