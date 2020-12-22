from django.db import models
from django.contrib.auth.models import User
from django.conf import settings


def user_directory_path(instance, filename):
    return '{0}/{1}/{2}'.format('Images', instance.actor.full_name, filename)

class Projector(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE)
	admin = models.BooleanField(default=False)

# Create your models here.
class Tag(models.Model):
	tag_name = models.CharField(max_length=20)

	class Meta:
		verbose_name_plural = 'tags'

	def __str__(self):
		return self.tag_name

class Actor(models.Model):
	first_name = models.CharField(max_length=15)
	last_name = models.CharField(max_length=15,blank=True)

	class Meta:
		verbose_name_plural = 'actors'

	def __str__(self):
		return self.full_name
	
	@property
	def full_name(self):
		"Returns the person's full name."
		if self.last_name:
			return '{0}{1}'.format(self.first_name, self.last_name)
		else:
			return self.first_name

#tracking view count would be ideal
class Video(models.Model):
	title = models.CharField(max_length=50)
	date_added = models.DateTimeField(auto_now_add=True)
	owner = models.ForeignKey(User, on_delete=models.CASCADE)
	tags = models.ManyToManyField('Tag', blank=True, related_name='videos')
	actors = models.ManyToManyField('Actor', blank=True, related_name='videos')
	public = models.BooleanField(default=False)
	#date_added = models.DateTimeField(auto_now_add=True)
	#release_date = models.DateTimeField(blank=True)
	file_path = models.FilePathField(path='{0}/videos/'.format(settings.MEDIA_ROOT), match="^\w.*\.mp4$", recursive=True)

	class Meta:
		verbose_name_plural = 'videos'

	def __str__(self):
		return self.title

	def path(self):
		return self.file_path[self.file_path.index('videos'):]

class ImagePath(models.Model):
	file_path = models.FilePathField(path='{0}/videos/'.format(settings.MEDIA_ROOT), match="^[^\.]+.*\.jpg$|^[^\.]+.*\.png$|^[^\.]+.*\.jpeg$|^[^\.]+.*\.gif$", recursive=True)

	class Meta:
		abstract=True

class Image(models.Model):
	image = models.ImageField(upload_to=user_directory_path,blank=True)

	class Meta:
		abstract=True
''' No need to a restricted number on these, but however there may be a restrictions at some point to allow for better viewing of images. Will see
'''
class ActorImage(Image):
	actor = models.ForeignKey(Actor, on_delete=models.CASCADE)

#Image purely used as display image on the frozen starting frame of the video.
class Poster(Image):
	video = models.OneToOneField(Video, on_delete=models.CASCADE, unique=True)

'''This does not need to be implemented right away. These are going to primarily used when hovering over video thumbnails as a preview
	Eventually I want to restrict this to a certai number of Images. I want for the most partfor the maipulation of this to be automatic
	Users will be able to djust the image frame as desired once I find a way to omplement that. by allowing for users to copy the video time
	and use that to select preview images.
	Might need to adjust on_delete values
'''
class PreviewImage(ImagePath):
	video = models.ForeignKey(Video, on_delete=models.CASCADE)
	seconds = models.PositiveIntegerField()
	tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
