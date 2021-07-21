from django import template
from math import floor
register = template.Library()

@register.filter
def bit_size(br):
    if br > 1000000000:
        return str(round((br * 0.000000001),2)) + "GB"
    elif br > 1000000:
        return str(round((br * 0.000001), 2)) + "MB"
    elif br > 1000:
        return str(round((br * 0.001), 2)) + "KB"
    else:
        return str(br) + "bytes"

@register.filter
def hours(time):
    m = time/60
    return "{0} Hours".format(round(m/60, 2))

@register.filter
def time(time):
    return '{0:.2g}'.format(floor(time/60)) + ':' + '{:02.0f}'.format(time%60,4)

@register.filter
def bit_rate(br):
    return str(round((br * 0.000001), 1)) + " mb/s"