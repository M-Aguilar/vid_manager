from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.http import HttpResponseRedirect, Http404, HttpRequest, HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages 
from django.core import serializers #ajax
from os import stat #video bitrate, length, and size

#NOT USED CURRENTLY
#from itertools import chain
#from django.core.files.images import get_image_dimensions
#import math
#from django.db.models import Q
#from decimal import Decimal 
#from datetime import datetime as dt
#from datetime import timedelta

import subprocess
import mutagen.mp4

from .thumbnail import capture
from .models import Video, Tag, Actor, Event, Image
from .forms import VideoForm, TagForm, ActorForm, EventForm, ImageForm

def index(request):
	return render(request, 'vid_manager/index.html')

@login_required
def video(request, video_id):
	video = get_object_or_404(Video, id=video_id)
	if video.owner != request.user and not video.public:
		raise Http404
	images = Image.objects.filter(video=video)
	data={'video':video}
	eventform = EventForm(initial=data)
	tagform = TagForm()
	actorform = ActorForm()
	actors = video.actors.all()
	video.actors.all()
	tags = video.tags.all()
	events = Event.objects.filter(video=video)
	context = {'video': video, 'actors': actors, 'tags': tags, 'images':images, 'eventform':eventform, 'actorform': actorform, 'tagform': tagform, 'events':events}
	return render(request, 'vid_manager/video.html', context)

@login_required
def videos(request):
	context = {}
	if request.user.is_authenticated and request.user.projector.admin:
		videos = Video.objects.filter(owner=request.user).order_by('-date_added')
	else:
		videos = Video.objects.filter(public=True)
	context['videos'] = videos
	return render(request, 'vid_manager/videos.html', context)


@login_required
def tag_videos(request, tag_id):
	tag = get_object_or_404(Tag, id=tag_id)
	if request.user.is_authenticated and request.user.projector.admin:
		videos = Video.objects.filter(tags=tag)
	context = {'videos':videos, 'tag':tag}
	return render(request, 'vid_manager/videos.html', context)

@login_required
def actor_videos(request, actor_id):
	actor = get_object_or_404(Actor, id=actor_id)
	if request.user.is_authenticated and request.user.projector.admin:
		videos = Video.objects.filter(actors=actor)
	context = {'videos':videos, 'actor': actor}
	return render(request, 'vid_manager/videos.html', context)

@login_required
def new_video(request, actor_id=None):
	if not request.user.projector.admin:
		raise Http404	
	if request.method != 'POST':
		if actor_id:
			actor = Actor.objects.get(id=actor_id)
			data = {'actors':actor}
			form = VideoForm(initial=data)
		else:
			form = VideoForm()
	else:
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
		form = VideoForm(instance=video)
	else:
		form = VideoForm(instance=video, data=request.POST, files=request.FILES)
		if (request.FILES.get('poster', False) and request.FILES['poster'] != video.poster) or (request.FILES.get('poster', True) and video.poster):
			video.poster.delete()
		if form.is_valid():
			form.save()
			return HttpResponseRedirect(reverse('video', args=[video.id]))
	context = {'video': video,'form': form}
	return render(request, 'vid_manager/edit_video.html', context)

@login_required
def delete_video(request, video_id):
	v = get_object_or_404(Video, id=video_id)
	if request.user.is_authenticated and request.user.projector.admin:
		events = Event.objects.filter(video=v)
		if events.count() >0:
			for e in events:
				subprocess.Popen(['sudo','rm', e.file_path])
		if v.poster:
			ff = v.poster.open()
			ff.delete()
		v.delete()
		messages.success(request, "Video {0} Succesfully Deleted".format(video_id))
	else:
		messages.error(request, 'Something wet wrong')
	return HttpResponseRedirect(reverse('videos'))

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
def tag(request, tag_id=None):
	if not tag_id:
		tag_id = request.GET.get('pk')
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
	if request.user.is_authenticated:
		t = get_object_or_404(Tag, id=tag_id)
		context = {'tag_id': t.id, 'tag_name': t.tag_name}
		t_copy=t
		t.delete()
		messages.success(request, "Tag {0} Succesfully Deleted".format(t_copy))
	else:
		message.error(request, "Something went wrong")
	return HttpResponseRedirect(reverse('tags'))

@login_required
def remove_tag(request, tag_id=None):
	print(tag_id)
	print("Type: {0}".format(type(tag_id)))
	t = request.META.get('HTTP_REFERER')
	if request.is_ajax and request.user.projector.admin and tag_id:
		tag = Tag.objects.get(id=tag_id)
		print(tag)
		if 'video' in t:
			video = Video.objects.get(id=t[t.index('video')+6:])
			video.tags.remove(tag)
			video.save()
			instance = tag
			serialized = serializers.serialize('json', [ instance, ])
			return JsonResponse({"tag":instance},status=200)
	return JsonResponse({"error":""}, status=400)

@login_required
def new_tag(request):
	t = request.META.get('HTTP_REFERER')
	if request.is_ajax and request.method == "POST":
		form = TagForm(request.POST)
		try:
			tag = Tag.objects.get(tag_name=form.data['tag_name'])
			if tag:
				instance = tag
				if 'video' in t:
					video = Video.objects.get(id=t[t.index('video')+6:])
					tag.videos.add(video)
				if 'image' in t:
					image = Image.objects.get(id=t[t.index('image')+6:])
					tag.images.add(image)
				serialized = serializers.serialize('json', [ instance, ])
				return JsonResponse({"instance":serialized},status=200)
		except Tag.DoesNotExist:
			if form.is_valid():
				instance = form.save()
				if 'video' in t:
					video = Video.objects.get(id=t[t.index('video')+6:])
					instance.videos.add(video)
				if 'image' in t:
					image = Image.objects.get(id=t[t.index('image')+6:])
					instance.images.add(image)
				serialized = serializers.serialize('json', [ instance, ])
				return JsonResponse({"instance":serialized},status=200)
			else:
				return JsonResponse(form.error, status=400)
	return JsonResponse({"error":""}, status=400)

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
	if request.is_ajax and request.method == "POST":
		first_name = Actor.objects.filter(first_name=request.POST['first_name']).exists()
		last_name = Actor.objects.filter(last_name=request.POST['last_name']).exists()
		if first_name and last_name:
			new_name = False
		else: 
			new_name = True
		form = ActorForm(request.POST)
		if form.is_valid() and new_name:
			instance = form.save(commit=False)
			instance.save()
			serialized = serializers.serialize('json', [ instance, ])
			return JsonResponse({"instance":serialized},status=200)
		else:
			return JsonResponse({"error": "That name is already in use"}, status=400)
	return JsonResponse({"error":""}, status=400)

@login_required
def delete_actor(request, actor_id):
	if request.method == "POST" and request.user.projector.admin:
		actor = get_object_or_404(Actor, id=actor_id)
		images = Image.objects.filter(actors=actor)
		for image in images:
			image.delete()
		actor.delete()
		messages.success(request, "Actor deleted.")
		return HttpResponseRedirect(reverse('actors'))
	messages.error(request, "An error occured.")
	return HttpResponseRedirect(request.META.get("HTTP_REFERER"))

#All Images
@login_required
def images(request):
	if request.user.is_authenticated and request.user.projector.admin:
		images = Image.objects.all()
	else:
		raise Http404
	context = {'images': images}
	return render(request,'vid_manager/images.html',context)

#Tag Images
@login_required
def tag_images(request, tag_id):
	tag = get_object_or_404(Tag, id=tag_id)
	if request.user.is_authenticated and request.user.projector.admin:
		images = Image.objects.filter(tags=tag)
	else:
		raise Http404
	context = {'images':images, 'tag': tag}
	return render(request, 'vid_manager/images.html', context)

#Actor Images
@login_required
def actor_images(request, actor_id):
	actor = get_object_or_404(Actor, id=actor_id)
	if request.user.is_authenticated and request.user.projector.admin:
		images = Image.objects.filter(actors=actor)
	else:
		raise Http404
	context = {'images': images, 'actor': actor}
	return render(request, 'vid_manager/images.html', context)

#New Video Image
@login_required
def new_video_image(request, video_id):
	if request.method == 'GET':
		data={}
		video = get_object_or_404(Video, id=video_id)
		data = {'video':video,'actors':video.actors.all()}
	else:
		new_image(request)
	form = ImageForm(initial=data)
	context = {'form':form}
	return render(request, 'vid_manager/new_image.html', context)

#New Actor Image
@login_required
def new_actor_image(request, actor_id):
	if request.method == 'GET':
		data={}
		actors = get_object_or_404(Actor, id=actor_id)
		data = {'actors':actors}
	else:
		new_image(request)
	form = ImageForm(initial=data)
	context = {'form':form}
	return render(request, 'vid_manager/new_image.html', context)

@login_required
def new_image(request):
	if request.method == 'GET':
		form = ImageForm()
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
	tag_form = TagForm()
	context = {'image':image,'actors':actors}
	return render(request, 'vid_manager/image.html', context)

@login_required
def delete_image(request, image_id):
	image = Image.objects.get(id=image_id)
	if request.user.is_authenticated and request.user.projector.admin and request.method == "POST":
		context = {'image': image}
		i_id = image.id
		i_i = image.image.name
		image.image.delete()
		image.delete()
		messages.success(request, "Image ID: {0} Filename: {1} has been deleted.".format(i_id,i_i))
		return HttpResponseRedirect(reverse('images'))
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
		if form.is_valid() and request.POST.get('seconds') < video.length:
			new_event = form.save(commit=False)
			new_event.video = video
			image_path = capture(video.file_path,int(request.POST['seconds']))
			new_event.file_path = image_path
			form.save()
			messages.success(request, 'Success! Event Added')
		else:
			messages.error(request, 'Something went wrong. Form invalid')
	return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

