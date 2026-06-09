from machine import Pin, PWM

class Servo:
        def __init__(self, port, angle=93):
            self.port = port
            self.servo_pwm = PWM(Pin(port,Pin.OUT), freq=50)
            self.set_angle(angle)

        def set_angle(self, angle):
            if angle < 0:
                angle = 0
            if angle > 180:
                angle = 180
            t = int(24+(99*angle/180))
            self.servo_pwm.duty(t)
            self.angle = angle