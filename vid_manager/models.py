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
		return '{0}/{1}'.format('Images', filename)
	except AttributeError:
		print("Attribute Error: user_directory_path 4")
		pass

class Projector(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE)
	admin = models.BooleanField(default=False)

#Tag Model
class Tag(models.Model):
	tag_name = models.CharField(max_length=50, unique=True)

	#returns a random image related to the tag. Returns False if non exist
	def img(self):
		img = Image.objects.filter(tags=self.id, image__isnull=False).order_by('?').first()
		if img:
			return img.image
		else:
			return False

	class Meta:
		verbose_name_plural = 'tags'
		ordering = ['tag_name']

	@property
	def type(self):
		return 'tag'

	def __str__(self):
		return self.tag_name

class ActorBase(models.Model):
	first_name = models.CharField(max_length=15)
	last_name = models.CharField(max_length=15,blank=True)

	class Meta:
		abstract = True

	def __str__(self):
		return self.full_name
	
	@property
	def full_name(self):
		"Returns the person's full name."
		if self.last_name:
			return '{0} {1}'.format(self.first_name, self.last_name)
		else:
			return self.first_name

class Actor(ActorBase):
	class Meta:
		verbose_name_plural = 'actors'
		ordering = ['first_name']

	def img(self):
		img = Image.objects.filter(actors=self.id, image__isnull=False).order_by("?").first()
		if img:
			return img.image
		else:
			return False

	@property
	def aliases(self):
		return Alias.objects.filter(actor=self.id)
	
	@property
	def type(self):
		return 'actor'

class Alias(ActorBase):
	actor = models.ForeignKey(Actor, on_delete=models.CASCADE, related_name='alias')

	class Meta:
		verbose_name_plural = 'aliases'

VIDEO_SORT_OPTIONS = ['release_date' ,'date_added' ,'title' , 'poster', 'length', 'resolution', 'size', 'actor_num', 'tag_num', 'bitrate', 'image_num']

class Video(models.Model):
	title = models.CharField(max_length=75)
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
	bitrate = models.PositiveIntegerField()

	height = models.PositiveSmallIntegerField(null=True)
	width = models.PositiveSmallIntegerField(null=True)

	class Meta:
		verbose_name_plural = 'videos'
		ordering = ['title']

	def __str__(self):
		return self.title

	def path(self):
		return settings.MEDIA_SERVER + self.file_path[self.file_path.index('videos'):]

	@property
	def type(self):
		return 'video'

class Image(models.Model):
	image = models.ImageField(upload_to=user_directory_path,blank=True)
	actors = models.ManyToManyField('Actor', related_name='actor_images')
	video = models.ForeignKey(Video, on_delete=models.CASCADE, blank=True,null=True)
	tags = models.ManyToManyField('Tag', blank=True, related_name='tag_images')

	@property
	def first_actor(self):
		return self.actors.first().full_name

	class Meta:
		verbose_name_plural = 'images'

class Event(models.Model):
	name = models.CharField(max_length=50)
	file_path = models.FilePathField(path='{0}/videos/'.format(settings.MEDIA_ROOT), match="^[^\.]+.*\.jpg$|^[^\.]+.*\.png$|^[^\.]+.*\.jpeg$|^[^\.]+.*\.gif$", recursive=True)
	video = models.ForeignKey(Video, on_delete=models.CASCADE)
	seconds = models.PositiveIntegerField()

	def url(self):
		if settings.DEBUG:
			return self.file_path[self.file_path.index('/media'):]
		else:
			return settings.MEDIA_SERVER + self.file_path[self.file_path.index('videos'):]

	def time(self):
		return '{0:.2g}'.format(floor(self.seconds/60)) + ':' + '{:02.0f}'.format(self.seconds%60)

	class Meta:
		verbose_name_plural = 'events'