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

# Create your models here.
class Tag(models.Model):
	tag_name = models.CharField(max_length=20, unique=True)

	def img(self):
		img = Image.objects.filter(tags=self.id, image__isnull=False).order_by('?').first()
		if img:
			return img.image
		else:
			return False

	class Meta:
		verbose_name_plural = 'tags'

	def __str__(self):
		return self.tag_name

class Actor(models.Model):
	first_name = models.CharField(max_length=15)
	last_name = models.CharField(max_length=15,blank=True)

	class Meta:
		verbose_name_plural = 'actors'

	def img(self):
		img = Image.objects.filter(actors=self.id, image__isnull=False).order_by("?").first()
		if img:
			return img.image
		else:
			return False

	@property
	def video_count(self):
		return Video.objects.filter(actors=self.id).count()

	@property
	def images_count(self):
		return Image.objects.filter(actors=self.id).count()
	

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

	def __str__(self):
		return self.title

	def size_neat(self):
		mb = round((self.size * 0.000001), 2)
		if mb > 1000:
			return str(round((mb * 0.001),2)) + "GB"
		else:
			return str(mb) + "MB"

	def time(self):
		return '{0:.2g}'.format(floor(self.length/60)) + ':' + '{:02.0f}'.format(self.length%60)

	def has_events(self):
		if len(Event.objects.filter(video=self.id)) > 0:
			return True
		return False

	def event(self):
		event = Event.objects.filter(video=self.id)[0]
		return event

	def b_rate(self):
		return str(round((self.bitrate * 0.0001), 1)) + "MB/s"

	def path(self):
		return "http://10.15.69.69:8800/media/{0}".format(self.file_path[self.file_path.index('videos'):])

	def actor_list_url(self):
		actor_list = None
		for i in self.actors.all():
			if not actor_list:
				actor_list = str(i)
			else:
				actor_list = '{0}+{1}'.format(actor_list, str(i))
		return actor_list

'''Potentially just make this into the image class with optional video foreign key ....'''
class Image(models.Model):
	image = models.ImageField(upload_to=user_directory_path,blank=True)
	actors = models.ManyToManyField('Actor', related_name='actors')
	video = models.ForeignKey(Video, on_delete=models.CASCADE, blank=True,null=True)
	tags = models.ManyToManyField('Tag', blank=True, related_name='tags')

	@property
	def first_actor(self):
		return self.actors.first().full_name

class Event(models.Model):
	name = models.CharField(max_length=50)
	file_path = models.FilePathField(path='{0}/videos/'.format(settings.MEDIA_ROOT), match="^[^\.]+.*\.jpg$|^[^\.]+.*\.png$|^[^\.]+.*\.jpeg$|^[^\.]+.*\.gif$", recursive=True)
	video = models.ForeignKey(Video, on_delete=models.CASCADE)
	seconds = models.PositiveIntegerField()

	def url(self):
		return self.file_path[self.file_path.index('/media'):]

	def time(self):
		return '{0:.2g}'.format(floor(self.seconds/60)) + ':' + '{:02.0f}'.format(self.seconds%60)

	class Meta:
		verbose_name_plural = 'events'