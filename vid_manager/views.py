from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.http import HttpResponseRedirect, Http404, HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from os import stat
from decimal import Decimal
from django.core.files.images import get_image_dimensions
import math
from itertools import chain

from django.db.models import Q
#from datetime import datetime as dt
#from datetime import timedelta
import subprocess
import mutagen.mp4

from .thumbnail import capture
from .models import Video, Tag, Actor, Event, Image
from .forms import VideoForm, TagForm, ActorForm, EventForm, ImageForm

# Create your views here.

def index(request):
	return render(request, 'vid_manager/index.html')

'''########################    VIDEOS     #########################'''

@login_required
def video(request, video_id):
	video = get_object_or_404(Video, id=video_id)
	#print(request.headers)
	#2 cases: public videos and nonpublic: Solved
	if video.owner != request.user and not video.public:
		raise Http404
	images = Image.objects.filter(video=video)
	#list of actors and tags in videos
	data={'video':video,'actors':video.actors.all()}
	form = EventForm(initial=data)
	actors = video.actors.all()
	tags = video.tags.all()
	events = Event.objects.filter(video=video)

#	size = str(round((statinfo.st_size * 0.000001), 2)) + "MB"
	context = {'video': video, 'actors': actors, 'tags': tags, 'images':images, 'form':form,'events':events}
	return render(request, 'vid_manager/video.html', context)

@login_required
def videos(request, actor_id=None):
	if request.user.is_authenticated:
		videos = Video.objects.filter(owner=request.user.id).order_by('-date_added')
		if actor_id:
			videos = videos.filter(actors=actor_id).order_by('-date_added')
	else:
		videos = Video.objects.filter(public=True)
	context = {'videos': videos}
	return render(request, 'vid_manager/videos.html', context)

@login_required
def new_video(request, actor_id=None):
	if not request.user.projector.admin:
		raise Http404	
	"""Add a new topic"""
	if request.method != 'POST':
		#no data submitted; create a blank form.
		if actor_id:
			actor = Actor.objects.get(id=actor_id)
			data = {'actors':actor}
			form = VideoForm(initial=data)
		else:
			form = VideoForm()
	else:
		#POST data submitted; process data.
		form = VideoForm(data=request.POST)
		if form.is_valid():
			new_video = form.save(commit=False)
			try:
				v = mutagen.mp4.Open(new_video.file_path)
				seconds = v.info.length
				b_rate = v.info.bitrate
			except mutagen.mp4.MP4StreamInfoError:
				seconds=0
				messages.error(request, 'Something went wrong checking length of video.')
			fp = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'stream=width,height', '-of', 'csv=p=0:s=x', new_video.file_path])
			fp = fp.decode('ascii').rstrip()
			dim = {'width':fp.split('x')[0],'height':fp.split('x')[1]}
			new_video.owner = request.user
			new_video.height = int(dim['height'])
			new_video.width = int(dim['width'])
			statinfo = stat(new_video.file_path)
			new_video.length = seconds
			new_video.bitrate = b_rate
			new_video.size = statinfo.st_size
			new_video.save()
			if request.FILES:
				new_video.poster = request.FILES['poster']
				new_video.save()
			form.save_m2m()
			return HttpResponseRedirect(reverse('video', args=[new_video.id]))
	new_tag_form = TagForm()
	new_actor_form = ActorForm()
	context = {'form': form, 'new_actor_form': new_actor_form, 'new_tag_form': new_tag_form}
	return render(request, 'vid_manager/new_video.html', context)

@login_required
def edit_video(request, video_id):
	video = get_object_or_404(Video, id=video_id)
	if video.owner != request.user and video.public:
		raise Http404

	if request.method != 'POST':
		# initial request; pre-fill form with the current entry.
		form = VideoForm(instance=video)
	else:
		#Post data submitted; process data
		form = VideoForm(instance=video, data=request.POST, files=request.FILES)
		if form.is_valid():
			form.save()
			return HttpResponseRedirect(reverse('video', args=[video.id]))
	context = {'video': video,'form': form}
	return render(request, 'vid_manager/edit_video.html', context)

@login_required
def delete_video(request, video_id):
	v = get_object_or_404(id=video_id)
	if request.user.is_authenticated and request.user.projector.admin:
		events = Event.objects.filter(video=v)
		if len(events)>0:
			for e in events:
				subprocess.Popen(['sudo','rm', e.file_path])
		if v.poster:
			ff = v.poster.open()
			ff.delete()
		v.delete()
		messages.success(request, "Video {0} Succesfully Deleted".format(video_id))
	else:
		messages.error(request, 'Something wet wrong')
	return HttpResponseRedirect(reverse('videos', args=[request.user.id]))


'''########################    TAGS     #########################'''

@login_required
def tags(request):
	if not request.user.projector.admin:
		raise Http404
	tags = Tag.objects.order_by('tag_name')
	new_tag_form = TagForm()
	context = {'tags': tags, 'new_tag_form': new_tag_form}
	return render(request, 'vid_manager/tags.html', context)

@login_required
def tag(request, tag_id):
	tag = get_object_or_404(Tag, id=tag_id)
	if not request.user.projector.admin:
		raise Http404
	else:
		videos= Video.objects.filter(tags=tag_id)
		images = Image.objects.filter(tags=tag_id)
	context = {'tag' : tag, 'videos': videos, 'images': images}
	return render(request, 'vid_manager/tag.html', context)	

@login_required
def delete_tag(request, tag_id):
	if not request.user.projector.admin:
		raise Http404
	if request.method == 'POST':
		t =get_object_or_404(Tag, id=tag_id)
		context = {'tag_id': t.id, 'tag_name': t.tag_name}
		t.delete()
		return render(request, 'vid_manager/delete_tag.html', context)
	else:
		return render(request, 'vid_manager/tags.html')

def new_tag(request):
	if not request.user.projector.admin:
		raise Http404
	if request.method != 'POST':
		#no data submitted; create a blank form.
		form = TagForm()
	else:
		#POST data submitted; process data.
		new_name = Tag.objects.filter(tag_name=request.POST['tag_name']).exists()
		form = TagForm(request.POST)
		if form.is_valid() and not new_name:
			new_tag = form.save(commit=False)
			new_tag.save()
			messages.success(request, 'The tag has been added')
			#i need to see which page they request is coming from
		else:
			messages.warning(request, 'That tag already exists')
		return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
		"""
		if form.is_valid():
			try:
				new_tag = Tag.objects.create(tag_name=request.POST['tag_name'])
				messages.success(request, 'Profile details updated.')
				return render(request, 'v_bank/v_home.html')
			except IntegrityError as e:
				return render_to_response("v_bank/new_tag.html", {"message": e.message})
		"""
	context = {'form': form}
	return render(request, 'vid_manager/new_tag.html', context)

'''########################    ACTOR     #########################'''

@login_required
def actor(request, actor_id):
	if not request.user.projector.admin:
		raise Http404
	else:
		actor = get_object_or_404(Actor,id=actor_id)
		images = Image.objects.filter(actors=actor)[:6]
		videos= Video.objects.filter(actors=actor)
	context={'actor':actor, 'videos': videos, 'images':images}
	return render(request, 'vid_manager/actor.html', context)

@login_required
def actors(request):
	if not request.user.projector.admin:
		raise Http404
	actors = Actor.objects.all().order_by('first_name')
	form = ActorForm()
	context = {'actors': actors, 'form': form}
	return render(request, 'vid_manager/actors.html', context)

@login_required
def new_actor(request):
	if not request.user.projector.admin:
		raise Http404
	if request.method != 'POST':
		#no data submitted; create a blank form.
		form = ActorForm()
	else:
		#POST data submitted; process data.
		first_name = Actor.objects.filter(first_name=request.POST['first_name']).exists()
		last_name = Actor.objects.filter(last_name=request.POST['last_name']).exists()
		if first_name and last_name:
			new_name = False
		else: 
			new_name = True
		form = ActorForm(request.POST)
		if form.is_valid() and new_name:
			new_actor = form.save(commit=False)
			new_actor.save()
			messages.success(request, 'The Actor has been added')
		else:
			messages.error(request, 'That Actor already exists')
		return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
	context = {'form': form}
	return render(request, 'vid_manager/new_actor.html', context)

'''########################    ACTOR IMAGE     #########################'''
@login_required
def images(request,actor_id=None):
	context = {'actor':None}
	if not request.user.is_authenticated or not request.user.projector.admin:
		raise Http404
	if actor_id:
		actor = get_object_or_404(Actor, id=actor_id)
		images = Image.objects.filter(actors=actor_id)
		context['actor'] = actor
	else:
		images = Image.objects.all()
		#images = list(chain(ActorImage.objects.all(), VideoImage.objects.all()))
	context['images'] = images
	return render(request,'vid_manager/images.html',context)

#WHERE DID I GO WRONGS?
'''

I need to allow a few type of image additions
1. new_image/ * No variables included
2. new_image/ actor(+actor+...) * Actor/s variable included
3. new_image/ actors / video * Actors/s and Video variable included

'''

@login_required
def new_image(request):
	if request.method == 'GET':
		data={}
		ref = request.META.get('HTTP_REFERER')
		if '/videos/' in ref:
			#video = Video.obejcts.get(id=ref[ref.index('/videos/'+7):])
			start = ref[ref.index('videos')+7:]
			video = Video.objects.get(id=start)
			data = {'video':video,'actors':video.actors.all()}
		if '/actor/' in ref:
			start = ref[ref.index('actor')+6:]
			actors = Actor.objects.get(id=start)
			data = {'actors':actors}
		form = ImageForm(initial=data)
	else:
		form = ImageForm(data=request.POST)
		if request.FILES.get('image',0) == 0:
			messages.error(request, 'No Image attached')
			return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
		if form.is_valid():
			new_image = form.save(commit=False)
			new_image.save()
			new_image.image = request.FILES['image']
			new_image.save()
			form.save_m2m()
			messages.success(request, 'The Image has been added')
			return HttpResponseRedirect(reverse('image', args=[new_image.pk]))
		else:
			messages.error(request, 'Something went wrong. Form invalid')
			return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
	context = {'form':form}
	return render(request, 'vid_manager/new_image.html', context)

@login_required
def image(request, image_id):
	image = Image.objects.get(id=image_id)
	if not request.user.projector.admin or not image:
		raise Http404
	actors = image.actors.all()
	context = {'image':image,'actors':actors}
	return render(request, 'vid_manager/image.html', context)

@login_required
def delete_image(request, image_id):
	image = Image.objects.get(id=image_id)
	if request.user.is_authenticated and request.user.projector.admin:
		context = {'image': image}
		image.image.delete()
		image.delete()
		return render(request, 'vid_manager/delete_image.html', context)
	else:
		messages.error(request, 'Something wet wrong')
		return HttpResponseRedirect(reverse('images'))

#UNECESSARY EVENTUALLY. SHOULD JUST ALLOW TO DELETE. AND VIEW IMAGE.
#ONLY ALLOW TO ADD TAGS
@login_required
def edit_image(request, image_id):
	if not request.user.projector.admin:
		raise Http404
	image = Image.objects.get(id=image_id)
	if request.method != 'POST':
		# initial request; pre-fill form with the current entry.
		form = ImageForm(instance=image)
	else:
		#Post data submitted; process data
		form = ImageForm(instance=image, files=request.FILES, data=request.POST)
		if form.is_valid():
			form.save()
			return HttpResponseRedirect(reverse('images'))
	context = {'image': image,'form': form}
	return render(request, 'vid_manager/edit_image.html', context)

#TODO check for time inside bounds of video length
@login_required
def new_event(request,video_id):
	if not request.user.projector.admin:
		raise Http404
	video = Video.objects.get(id=video_id)
	if request.method != 'POST':
		messages.error(request, 'TRY GET')
	else:
		form = EventForm(data=request.POST)
		if form.is_valid():
			new_event = form.save(commit=False)
			new_event.video = video
			image_path = capture(video.file_path,int(request.POST['seconds']))
			new_event.file_path = image_path
			form.save()
			messages.success(request, 'Success! Event Added')
		else:
			messages.error(request, 'Something went wrong. Form invalid')
	return HttpResponseRedirect(request.META.get('HTTP_REFERER'))		