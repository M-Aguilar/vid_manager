from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

from math import floor

def user_directory_path(instance, filename):
	try:
		return '{0}/{1}/{2}'.format('Images', instance.video.id, filename)
	except AttributeError:
		print("Attribute Error: user_directory_path 1")
		pass
	try:
		return '{0}/{1}/{2}'.format('Images', instance.actor.full_name, filename)
	except AttributeError:
		print("Attribute Error: user_directory_path 2")
		pass
	try:
		return '{0}/{1}/{2}'.format('Images', instance.pk, filename)
	except AttributeError:
		print("Attribute Error: user_directory_path 3")
		pass

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
			return '{0} {1}'.format(self.first_name, self.last_name)
		else:
			return self.first_name

#tracking view count would be ideal
class Video(models.Model):
	title = models.CharField(max_length=50)
	date_added = models.DateTimeField(auto_now_add=True)
	release_date = models.DateField(blank=True,null=True)
	owner = models.ForeignKey(User, on_delete=models.CASCADE)
	tags = models.ManyToManyField('Tag', blank=True, related_name='videos')
	actors = models.ManyToManyField('Actor', blank=True, related_name='videos')
	public = models.BooleanField(default=False)
	file_path = models.FilePathField(path='{0}/videos/'.format(settings.MEDIA_ROOT), match="^\w.*\.mp4$", recursive=True,unique=True)
	poster = models.ImageField(upload_to=user_directory_path, blank=True, null=True)
	length = models.PositiveIntegerField()
	size = models.PositiveBigIntegerField()

	height = models.PositiveSmallIntegerField(null=True)
	width = models.PositiveSmallIntegerField(null=True)

	class Meta:
		verbose_name_plural = 'videos'

	def __str__(self):
		return self.title

	def size_neat(self):
		return str(round((self.size * 0.000001), 2)) + "MB"

	def time(self):
		return '{0:.2g}'.format(floor(self.length/60)) + ':' + '{:02.0f}'.format(self.length%60)

	def has_events(self):
		if len(Event.objects.filter(video=self.id)) > 0:
			return True
		return False

	def event(self):
		event = Event.objects.filter(video=self.id)[0]
		return event

	def path(self):
		return self.file_path[self.file_path.index('videos'):]

class ImagePath(models.Model):
	file_path = models.FilePathField(path='{0}/videos/'.format(settings.MEDIA_ROOT), match="^[^\.]+.*\.jpg$|^[^\.]+.*\.png$|^[^\.]+.*\.jpeg$|^[^\.]+.*\.gif$", recursive=True)

	class Meta:
		abstract=True

	def url(self):
		return self.file_path[self.file_path.index('/media'):]

'''Potentially just make this into the image class with optional video foreign key ....'''
class Image(models.Model):
	image = models.ImageField(upload_to=user_directory_path)
	
	class Meta:
		abstract=True
''' No need to a restricted number on these, but however there may be a restrictions at some point to allow for better viewing of images. Will see
I need to decide on what it is I want in terms of functionality in the site. I want videos thumbnails to lead to the videos. i however would also like to allow
for images tied to a video.
Images cant already be tied to an actor. And a onetoone which is for the video thumbnail cover. HTML poster attribute. 
'''

class VideoImage(Image):
	video = models.ForeignKey(Video, on_delete=models.CASCADE)
	tags = models.ManyToManyField('Tag', blank=True, related_name='video_image_tags')

	def ref(self):
		return 'video_image'

class ActorImage(Image):
	actors = models.ManyToManyField('Actor', related_name='actors')
	tags = models.ManyToManyField('Tag', blank=True, related_name='actor_image_tags')

	def ref(self):
		return 'actor_image'

'''This does not need to be implemented right away. These are going to primarily used when hovering over video thumbnails as a preview
	Eventually I want to restrict this to a certai number of Images. I want for the most partfor the maipulation of this to be automatic
	Users will be able to djust the image frame as desired once I find a way to omplement that. by allowing for users to copy the video time
	and use that to select preview images.
	Might need to adjust on_delete values
'''

class Event(ImagePath):
	name = models.CharField(max_length=50)
	video = models.ForeignKey(Video, on_delete=models.CASCADE)
	seconds = models.PositiveIntegerField()

	def time(self):
		return '{0:.2g}'.format(floor(self.seconds/60)) + ':' + '{:02.0f}'.format(self.seconds%60)

	class Meta:
		verbose_name_plural = 'events'