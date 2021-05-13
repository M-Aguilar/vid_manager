from django import template
from math import floor
register = template.Library()

@register.filter
def bit_size(br):
    mb = round((br * 0.000001), 2)
    if mb > 1000:
        return str(round((mb * 0.001),2)) + "GB"
    else:
        return str(mb) + "MB"
@register.filter
def time(time):
    return '{0:.2g}'.format(round(time/60)) + ':' + '{:02.0f}'.format(time%60,4)

@register.filter
def bit_rate(br):
    return str(round((br * 0.0001), 1)) + "MB/s"