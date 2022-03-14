from django import template
from django.conf import settings

register = template.Library()

@register.filter
def media_server(word):
	return settings.MEDIA_SERVER
