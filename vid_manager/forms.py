from django import forms

from .models import Video, Actor, Tag, ActorImage

class VideoForm(forms.ModelForm):
	class Meta:
		model = Video
		fields = ['title', 'tags','actors','public', 'file_path']

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
		fields = ['actor','image']