from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.http import HttpResponseRedirect, Http404, HttpRequest, HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages 
from django.core import serializers #ajax
from os import stat #video bitrate, length, and size
from django.core.paginator import Paginator
import json
from django.conf import settings
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

def auto_actor_add(request):
	if request.user.projector.admin:
		form = VideoForm()
		actors = [x.full_name for x in Actor.objects.all()]
		choices = form.fields['file_path'].choices
		new_actors = [x[0].split('/')[-2] for x in choices if x[0].split('/')[-2] not in settings.EXCEPTIONS and x[0].split('/')[-2] not in actors]
		added_list = []
		for i in new_actors:
			if i not in added_list:
				added_list.append(i)
				add_actor(i)		
	return HttpResponseRedirect(reverse('actors'))

def add_actor(actor_name):
	i = actor_name.split(' ')
	if len(i) == 1:
		data={'first_name': i[0]}
	elif len(i) == 2:
		data={'first_name': i[0], 'last_name': i[1]}
	else:
		data={'first_name': i[0], 'last_name': ' '.join(i[1:])}
	form = ActorForm(data=data)
	new_actor = form.save()

def new_actor_count():
	exceptions = settings.EXCEPTIONS
	form=VideoForm()
	choices = form.fields['file_path'].choices
	actors = [x.full_name for x in Actor.objects.all()]
	new_actors = [x[0].split('/')[-2] for x in choices if x[0].split('/')[-2] not in exceptions and x[0].split('/')[-2] not in actors]
	act_list = []
	for i in new_actors:
		if i not in act_list:
			act_list.append(i)
	return len(act_list)

@login_required
def auto_add(request, actor_id):
	actor = Actor.objects.get(id=actor_id)
	new_vidss = scan(actor)
	for new_vids in new_vidss:
		title = new_vids.split('/')[-1]
		data = {'title': title[:title.index('.')],'actors': [actor],'file_path':new_vids}
		form = VideoForm(data=data)
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
			form.save_m2m()	
		else:
			messages.error(request,form.errors)
			return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
	return HttpResponseRedirect(reverse('video', args=[new_video.id]))

def scan(actor):
	form = VideoForm()
	choices = form.fields['file_path'].choices
	actor_videos = [x.file_path for x in Video.objects.filter(actors__isnull=False)]
	found = [x for x in choices if (("/{0}/".format(actor.full_name) in x[0]) or (actor.full_name.replace(" ","") in x[0])) and x[0] not in actor_videos]
	return found

def index(request):
	return render(request, 'vid_manager/index.html')

'''########################    ACTOR     #########################'''

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
	if request.user.is_authenticated and request.user.projector.admin:
		videos = Video.objects.filter(owner=request.user).order_by('-date_added')
	else:
		videos = Video.objects.filter(public=True)
	total = videos.count()
	paginator = Paginator(videos, 24)
	page_num = request.GET.get('page')
	page_o = paginator.get_page(page_num)
	context = {'videos':page_o, 'total':total}
	return render(request, 'vid_manager/videos.html', context)

@login_required
def tag_videos(request, tag_id):
	tag = get_object_or_404(Tag, id=tag_id)
	if request.user.is_authenticated and request.user.projector.admin:
		videos = Video.objects.filter(tags=tag)
		total = videos.count()
	paginator = Paginator(videos, 24)
	page_num = request.GET.get('page')
	page_o = paginator.get_page(page_num)
	context = {'videos':page_o, 'tag':tag, 'total':total}
	return render(request, 'vid_manager/videos.html', context)

@login_required
def actor_videos(request, actor_id):
	actor = get_object_or_404(Actor, id=actor_id)
	if request.user.is_authenticated and request.user.projector.admin:
		videos = Video.objects.filter(actors=actor)
		total = videos.count()
	paginator = Paginator(videos, 24)
	page_num = request.GET.get('page')
	page_o = paginator.get_page(page_num)
	context = {'videos':page_o, 'actor': actor, 'total':total}
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
			form.fields['file_path'].choices = scan(actor)
		else:
			all_fps = [x.file_path for x in Video.objects.filter(actors__isnull=False)]
			form = VideoForm()
			choices = [x for x in form.fields['file_path'].choices if x[0] not in all_fps]
			form.fields['file_path'].choices = choices
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
		if (request.FILES.get('poster', False) and request.FILES.get('poster') != video.poster):
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
	total = tags.count()
	paginator = Paginator(tags, 24)
	page_num = request.GET.get('page')
	page_o = paginator.get_page(page_num)
	new_tag_form = TagForm()
	context = {'tags': page_o, 'new_tag_form': new_tag_form, 'total':total}
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
def remove_tag(request, tag_id):
	t = request.META.get('HTTP_REFERER')
	print(t)
	if request.is_ajax and request.user.projector.admin:
		tag = Tag.objects.get(id=tag_id)
		print(tag)
		if 'video' in t:
			video = Video.objects.get(id=t[t.index('video')+6:])
			video.tags.remove(tag)
		if 'image' in t:
			image = Image.objects.get(id=t[t.index('image')+6:])
			image.tags.remove(tag)
		instance = tag
		return JsonResponse({'instance':serializers.serialize('json',[instance,])}, status=200)
	else:
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
					image.tags.add(tag)
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
		new_videos = scan(actor)
		images = Image.objects.filter(actors=actor)
		videos= Video.objects.filter(actors=actor)
	context={'actor':actor, 'videos': videos[:6], 'images':images[:12], 'total_vids': videos.count(), 'total_images': images.count(), 'new_videos': len(new_videos)}
	return render(request, 'vid_manager/actor.html', context)

@login_required
def actors(request):
	if not request.user.projector.admin:
		raise Http404
	actors = Actor.objects.all().order_by('first_name')
	form = ActorForm()
	context = {'actors': actors, 'form': form, 'new_actors':new_actor_count()}
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

'''########################    IMAGES     #########################'''

#All Images
@login_required
def images(request):
	if request.user.is_authenticated and request.user.projector.admin:
		images = Image.objects.all()
		total = images.count()
	else:
		raise Http404
	paginator = Paginator(images, 24)
	page_num = request.GET.get('page')
	page_o = paginator.get_page(page_num)
	context = {'images': page_o, 'total':total}
	return render(request,'vid_manager/images.html',context)

#Tag Images
@login_required
def tag_images(request, tag_id):
	tag = get_object_or_404(Tag, id=tag_id)
	if request.user.is_authenticated and request.user.projector.admin:
		images = Image.objects.filter(tags=tag)
	else:
		raise Http404
	paginator = Paginator(images, 24)
	page_num = request.GET.get('page')
	page_o = paginator.get_page(page_num)
	context = {'images':page_o, 'tag': tag}
	return render(request, 'vid_manager/images.html', context)

#Actor Images
@login_required
def actor_images(request, actor_id):
	actor = get_object_or_404(Actor, id=actor_id)
	if request.user.is_authenticated and request.user.projector.admin:
		images = Image.objects.filter(actors=actor)
	else:
		raise Http404
	paginator = Paginator(images, 24)
	page_num = request.GET.get('page')
	page_o = paginator.get_page(page_num)
	context = {'images': page_o, 'actor': actor}
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
	context = {'image':image,'actors':actors, 'tagform': tag_form}
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


'''########################    EVENTS     #########################'''
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

