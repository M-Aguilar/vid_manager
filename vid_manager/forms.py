from django import forms

from .models import Video, Actor, Tag, Image, Event, Alias

class VideoForm(forms.ModelForm):
	class Meta:
		model = Video
		fields = ['title', 'tags','actors','public', 'file_path', 'poster', 'release_date']
		labels = {'title':''}
		widgets = {
		'title': forms.TextInput(attrs={'placeholder':'Title','autofocus':'autofocus'}),
		'release_date': forms.DateInput(attrs={'placeholder':'MM-DD-YYYY','format':'%m/%d/%Y'}),
		}

class AliasForm(forms.ModelForm):
	class Meta:
		model = Alias
		fields = ['first_name','last_name','actor']

class ActorForm(forms.ModelForm):
	class Meta:
		model = Actor
		fields = ['first_name', 'last_name']

class TagForm(forms.ModelForm):
	class Meta:
		model = Tag
		fields = ['tag_name']
		widgets = {
			'tag_name': forms.TextInput(attrs={'list':'tag_results', 'autocomplete': 'off'})
		}

class ImageForm(forms.ModelForm):
	class Meta:
		model = Image
		fields = ['actors','video','image','tags']

class EventForm(forms.ModelForm):
	class Meta:
		model = Event
		fields = ['name','seconds']