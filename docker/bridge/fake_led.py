#!/usr/bin/env python3
import rospy
from led_msgs.msg import LEDState, LEDStateArray
from led_msgs.srv import SetLED, SetLEDResponse, SetLEDs, SetLEDsResponse

LED_COUNT = 58

state = [LEDState(index=i, r=0, g=0, b=0) for i in range(LED_COUNT)]
pub = None


def publish():
    pub.publish(LEDStateArray(leds=state))


def set_led(req):
    if req.index >= LED_COUNT:
        return SetLEDResponse(success=False, message='index out of range')
    state[req.index] = LEDState(index=req.index, r=req.r, g=req.g, b=req.b)
    publish()
    return SetLEDResponse(success=True)


def set_leds(req):
    for l in req.leds:
        if l.index >= LED_COUNT:
            return SetLEDsResponse(success=False, message='index %d out of range' % l.index)
    for l in req.leds:
        state[l.index] = LEDState(index=l.index, r=l.r, g=l.g, b=l.b)
    publish()
    return SetLEDsResponse(success=True)


if __name__ == '__main__':
    rospy.init_node('led')
    pub = rospy.Publisher('~state', LEDStateArray, queue_size=1, latch=True)
    rospy.Service('~set_led', SetLED, set_led)
    rospy.Service('~set_leds', SetLEDs, set_leds)
    publish()
    rospy.spin()
