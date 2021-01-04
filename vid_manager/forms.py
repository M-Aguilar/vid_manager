from django import forms

from .models import Video, Actor, Tag, ActorImage, VideoImage, Event

class VideoForm(forms.ModelForm):
	class Meta:
		model = Video
		fields = ['title', 'tags','actors','public', 'file_path', 'poster', 'release_date']
		labels = {'title':''}
		widgets = {
		'title': forms.TextInput(attrs={'placeholder':'Title','autofocus':'autofocus'}),
		'release_date': forms.DateInput(attrs={'placeholder':'MM-DD-YYYY'}),
		}

class ActorForm(forms.ModelForm):
	class Meta:
		model = Actor
		fields = ['first_name', 'last_name']

class TagForm(forms.ModelForm):
	class Meta:
		model = Tag
		fields = ['tag_name']

class ActorImageForm(forms.ModelForm):
	class Meta:
		model = ActorImage
		fields = ['actors','image','tags']

class VideoImageForm(forms.ModelForm):
	class Meta:
		model = VideoImage
		fields = ['video','image','tags']

class EventForm(forms.ModelForm):
	class Meta:
		model = Event
		fields = ['name','seconds']