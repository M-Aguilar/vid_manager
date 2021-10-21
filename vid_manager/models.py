from django.db import models
from django.db.models import Max
from django.contrib.auth.models import User
from django.conf import settings
from math import floor
import random
from django.core.validators import MaxValueValidator

from django.db.models.fields import PositiveIntegerField

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
		imgs = list(Image.objects.filter(tags=self.id, image__isnull=False).exclude(is_poster=True))
		if len(imgs) > 0:
			img = random.choice(imgs)
			return img
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
		imgs = list(Image.objects.filter(actors=self.id, image__isnull=False).exclude(is_poster=True))
		if len(imgs) > 0:
			img = random.choice(imgs)
			img = img
		else:
			img = False
		return img

	@property
	def all_names(self):
		name = self.full_name
		aliases = [x.full_name for x in self.aliases]
		return [name] + aliases

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

VIDEO_SORT_OPTIONS = ['release_date' ,'date_added' ,'title', 'length', 'resolution','poster_num', 'size', 'actor_num', 'tag_num', 'bitrate', 'image_num']

class Video(models.Model):
	title = models.CharField(max_length=75)
	date_added = models.DateTimeField(auto_now_add=True)
	release_date = models.DateField(blank=True,null=True)
	owner = models.ForeignKey(User, on_delete=models.CASCADE)
	tags = models.ManyToManyField('Tag', blank=True, related_name='videos')
	actors = models.ManyToManyField('Actor', blank=True, related_name='videos')
	public = models.BooleanField(default=False)

	class Meta:
		verbose_name_plural = 'videos'
		ordering = ['title']

	def __str__(self):
		return self.title

	@property
	def rand_color(self):
		cl = list(random.choices(range(256), k=3))
		clr = []
		for i in cl:
			clr.append(str(i))
		return ','.join(clr)

	@property
	def type(self):
		return 'video'

	@property
	def postr(self):
		imgs = list(self.images.filter(is_poster=True))
		if len(imgs) > 0:
			img = random.choice(imgs)
		else:
			img = None
		return img

	@property
	def vlen(self):
		leng = self.videosource_set.all()
		leng.aggregate(Max('length'))
		leng.order_by('-length')
		leng = leng.first()
		return leng.length

	@property
	def min_res(self):
		mr = self.videosource_set.all()
		mr.aggregate(Max('height'))
		mr = mr.order_by('height')
		mr = mr.first()
		return mr.height
	@property
	def max_res(self):
		mr = self.videosource_set.all()
		mr.aggregate(Max('height'))
		mr = mr.order_by('-height')
		mr = mr.first()
		return mr.height

	@property
	def min_size(self):
		ms = self.videosource_set.all()
		ms.aggregate(Max('size'))
		ms.order_by('size')
		ms = ms.first()
		return ms.size

	@property
	def max_size(self):
		ms = self.videosource_set.all()
		ms.aggregate(Max('size'))
		ms.order_by('-size')
		ms = ms.first()
		return ms.size

class VideoSource(models.Model):
	video = models.ForeignKey(Video, on_delete=models.CASCADE)
	file_path = models.FilePathField(path='{0}/videos/'.format(settings.MEDIA_ROOT), match="^\w.*\.mp4$", recursive=True,unique=True)
	length = models.PositiveIntegerField()
	size = models.PositiveBigIntegerField()
	bitrate = models.PositiveIntegerField()
	height = models.PositiveSmallIntegerField(null=True)
	width = models.PositiveSmallIntegerField(null=True)

	def path(self):
		return settings.MEDIA_SERVER + self.file_path[self.file_path.index('videos'):]

	class Meta:
		ordering = ['-width']

class Image(models.Model):
	image = models.ImageField(upload_to=user_directory_path,blank=True)
	actors = models.ManyToManyField('Actor', related_name='actor_images',blank=True)
	video = models.ForeignKey(Video, on_delete=models.CASCADE, blank=True,null=True, related_name='images')
	tags = models.ManyToManyField('Tag', blank=True, related_name='tag_images')
	is_poster = models.BooleanField(default=False)

	def path(self):
		if settings.DEBUG:
			return self.image.url
		else:
			return settings.MEDIA_SERVER + "videos/"  + self.image.path[self.image.path.index('Images'):]
	
	@property
	def first_actor(self):
		return self.actors.first().full_name

	class Meta:
		verbose_name_plural = 'images'

class PosterColor(models.Model):
	image = models.OneToOneField(Image, on_delete=models.CASCADE, related_name='image_color')
	red = PositiveIntegerField(default=0, validators=[MaxValueValidator(256)])
	green = PositiveIntegerField(default=0, validators=[MaxValueValidator(256)])
	blue = PositiveIntegerField(default=0, validators=[MaxValueValidator(256)])

	@property
	def color(self):
		return ','.join([str(self.red), str(self.green), str(self.blue)])

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

	def __str__(self):
		return self.name

	class Meta:
		verbose_name_plural = 'events'
