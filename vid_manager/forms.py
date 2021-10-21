from django import forms

from .models import Video, Actor, Tag, Image, Event, Alias, VideoSource

class VideoSourceForm(forms.ModelForm):
	class Meta:
		model = VideoSource
		fields = ['file_path']
		widgets = {
			'file_path': forms.Select(attrs={'class': 'form-control py-0 col-11'})
		}

class VideoForm(forms.ModelForm):
	class Meta:
		model = Video
		fields = ['title', 'tags','actors','public', 'release_date']
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
		labels = {'tag_name': ''}
		fields = ['tag_name']
		widgets = {
			'tag_name': forms.TextInput(attrs={'list':'tag_results', 'autocomplete': 'off', 'placeholder':'Tag Name'})
		}

class ImageForm(forms.ModelForm):
	class Meta:
		model = Image
		fields = ['actors','video','image','tags']

		widgets = {
			'image' : forms.FileInput(attrs={'multiple':''}),
			'video' : forms.Select(attrs={'class': 'form-control py-0'}),
		}

class EventForm(forms.ModelForm):
	class Meta:
		model = Event
		fields = ['name','seconds']