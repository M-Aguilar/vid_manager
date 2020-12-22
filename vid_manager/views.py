from django.shortcuts import render
from django.urls import reverse
from django.http import HttpResponseRedirect, Http404, HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from os import stat
from decimal import Decimal
import mutagen.mp4

from .models import Video, Tag, Actor, ActorImage
from .forms import VideoForm, TagForm, ActorForm, ActorImageForm

# Create your views here.
def index(request):
	return render(request, 'vid_manager/index.html')

def video(request, video_id):
	print(request.headers)
	#2 cases: public videos and nonpublic: Solved
	video = Video.objects.get(id=video_id)
	#this calculates the length of the video
	try:
		v = mutagen.mp4.Open(video.file_path)
		mili = v.info.length
		b_rate = v.info.bitrate
		print(b_rate)
		v_len = '{0:.3g}'.format(mili/60) + ':' + '{0:.2g}'.format(mili%60)
	except mutagen.mp4.MP4StreamInfoError:
		v_len=0
		messages.error(request, 'The file provided is not a video')
	statinfo = stat(video.file_path)
	if video.owner != request.user and not video.public:
		raise Http404

	#list of actors and tags in videos
	actors = video.actors.all()
	tags = video.tags.all()

	in_bytes = statinfo.st_size * 0.000001
	output = round(in_bytes, 2)
	size = str(output) + "MB"
	context = {'video': video, 'size': size, 'actors': actors, 'tags': tags, 'v_len': v_len}
	return render(request, 'vid_manager/video.html', context)

@login_required
def videos(request, user_id='public'):
	if user_id != 'public' and request.user.is_authenticated:
		videos = Video.objects.filter(owner_id=user_id)
	else:
		videos = Video.objects.filter(public=True)
	context = {'videos': videos}
	return render(request, 'vid_manager/videos.html', context)

@login_required
def new_video(request):
	if not request.user.projector.admin:
		raise Http404	
	"""Add a new topic"""
	if request.method != 'POST':
		#no data submitted; create a blank form.
		form = VideoForm()
	else:
		#POST data submitted; process data.
		form = VideoForm(data=request.POST)
		if form.is_valid():
			new_video = form.save(commit=False)
			new_video.owner = request.user
			new_video.save()
			form.save_m2m()
			return HttpResponseRedirect(reverse('video', args=[new_video.id]))
	new_tag_form = TagForm()
	new_actor_form = ActorForm()
	context = {'form': form, 'new_actor_form': new_actor_form, 'new_tag_form': new_tag_form}
	return render(request, 'vid_manager/new_video.html', context)

@login_required
def edit_video(request, video_id):
	video = Video.objects.get(id=video_id)
	if video.owner != request.user and video.public:
		raise Http404

	if request.method != 'POST':
		# initial request; pre-fill form with the current entry.
		form = VideoForm(instance=video)
	else:
		#Post data submitted; process data
		form = VideoForm(instance=video, data=request.POST)
		if form.is_valid():
			form.save()
			return HttpResponseRedirect(reverse('video', args=[video.id]))
	context = {'video': video,'form': form}
	return render(request, 'vid_manager/edit_video.html', context)

@login_required
def delete_video(request, video_id):
	v = Video.objects.get(id=video_id)
	if request.method == 'POST':
		context = {'video_id': v.id, 'video': v.title}
		v.delete()
		return render(request, 'vid_manager/delete_video.html', context)
	else:
		messages.error(request, 'Something wet wrong')
		return HttpResponseRedirect(reverse('my_videos', args=[request.user.id]))

def tags(request):
	tags = Tag.objects.order_by('tag_name')
	new_tag_form = TagForm()
	context = {'tags': tags, 'new_tag_form': new_tag_form}
	return render(request, 'vid_manager/tags.html', context)

def tag(request, tag_id):
	tag = Tag.objects.get(id=tag_id)
	if request.user == 'anonymous':
		videos= Video.objects.filter(tags=tag_id).filter(public=True)
	else:
		videos= Video.objects.filter(tags=tag_id)
	context = {'tag' : tag, 'videos': videos}
	return render(request, 'vid_manager/tag.html', context)	

@login_required
def delete_tag(request, tag_id):
	if request.method == 'POST':
		t =Tag.objects.get(id=tag_id)
		context = {'tag_id': t.id, 'tag_name': t.tag_name}
		t.delete()
		return render(request, 'vid_manager/delete_tag.html', context)
	else:
		return render(request, 'vid_manager/tags.html')

def new_tag(request):
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

@login_required
def actor(request, actor_id):
	actor = Actor.objects.get(id=actor_id)
	if request.user == 'anonymous':
		videos= Video.objects.filter(actors=actor_id).filter(public=True)
		images = {}
	else:
		images = ActorImage.objects.filter(actor=actor)
		videos= Video.objects.filter(actors=actor_id)
	context={'actor':actor, 'videos': videos, 'images':images}
	return render(request, 'vid_manager/actor.html', context)

def actors(request):
	actors = Actor.objects.all().order_by('first_name')
	form = ActorForm()
	context = {'actors': actors, 'form': form}
	return render(request, 'vid_manager/actors.html', context)

def new_actor(request):
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

@login_required
def add_actor_image(request, actor_id):
	actor = Actor.objects.get(id=actor_id)
	if request.method != 'POST':
		data = {'actor':actor}
		form = ActorImageForm(initial=data)
	else:
		form = ActorImageForm(data=request.POST, files=request.FILES)
		if form.is_valid():
			new_actor_image = form.save(commit=False)
			new_actor_image.actor = actor
			new_actor_image.save()
			messages.success(request, 'The Image has been added')
		else:
			messages.error(request, 'Something went wrong. Form invalid')
		return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
	context = {'form':form, 'actor':actor}
	return render(request, 'vid_manager/add_actor_image.html', context)


@login_required
def edit_actor_image(request, image_id):
	image = ActorImage.objects.get(id=image_id)
	if not request.user.projector.admin:
		raise Http404

	if request.method != 'POST':
		# initial request; pre-fill form with the current entry.
		form = ActorImageForm(instance=image)
	else:
		#Post data submitted; process data
		form = ActorImageForm(data=request.POST, files=request.FILES)
		if form.is_valid():
			form.save()
			return HttpResponseRedirect(reverse('actors'))
	context = {'image': image,'form': form}
	return render(request, 'vid_manager/edit_actor_image.html', context)

