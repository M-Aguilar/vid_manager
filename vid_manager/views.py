from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.http import HttpResponseRedirect, Http404, HttpRequest, HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages 
from django.core import serializers #ajax
from os import stat #video bitrate, length, and size
from django.core.paginator import Paginator
from django.db.models import Count
import json
from django.conf import settings

from django.db.models import Q
from django.views.generic import ListView

#for Ajax rendering. ?
from django.template.loader import render_to_string
#NOT USED CURRENTLY
#from itertools import chain
#from django.core.files.images import get_image_dimensions
#import math
#from decimal import Decimal 
#from datetime import datetime as dt
#from datetime import timedelta

import subprocess
import mutagen.mp4

from .thumbnail import capture
from .models import Video, Tag, Actor, Event, Image, Alias
from .forms import VideoForm, TagForm, ActorForm, EventForm, ImageForm, AliasForm

#The Goal is to have narrow results when necessary
#Usually the longer the query the more sepcific the result desired
class SearchResultsView(ListView):
	model = Video
	template_name = 'vid_manager/search_results.html'

	def get_queryset(self):
    	#searches for query
		query = self.request.GET.get('q').strip()
		actors = self.checkActor(query)
		tags = self.checkTag(query)
		if self.request.user.is_authenticated and query not in ['', None]:
			o_list = Video.objects.filter(Q(title__iexact=query))
			if len(o_list) != 1:
				o_list = Video.objects.filter(Q(title__icontains=query), Q(owner=self.request.user))
				if actors and tags:
					o_list = o_list | Video.objects.exclude(id__in=[x.id for x in o_list]).filter(actors__in=[x for x in actors], tags__in=[x for x in tags])
				else:
					if actors:
						temp = []
						for actor in actors:
							new_list = Video.objects.exclude(id__in=[x.id for x in o_list if x not in temp and x not in o_list]).filter(actors=actor)
							temp.append(new_list)
							o_list = o_list | new_list
					if tags:
						temp=[]
						for tag in tags:
							new_list = Video.objects.exclude(id__in=[x.id for x in o_list if x not in temp and x not in o_list]).filter(tags=tag)
							temp.append(new_list)
							o_list = o_list | new_list
		else:
			o_list = Video.objects.filter(Q(title__icontains=query), Q(public=True))
		total = o_list.count() + len(tags) + len(actors)
		paginator = Paginator(o_list, 24)
		page_num = self.request.GET.get('page')
		page_o = paginator.get_page(page_num)
		object_list = {'object_list': page_o, 'q': query, 'total': total, 'actors': actors,'tags':tags}
		return object_list

	#Returns a list of actors/aliases the query is found in. 
	def checkActor(self, q):
		actors = [x for x in Actor.objects.all() if self.closeEnough(q, x.full_name)]
		aliases = [x.actor for x in Alias.objects.all() if x not in actors and self.closeEnough(q,x.full_name)]
		return actors + aliases

	#Returns a list of tags the query is found in
	def checkTag(self, q):
		tags = [x for x in Tag.objects.all() if self.closeEnough(q, x.tag_name)]
		return tags

	#Truthy checks name against query.
	def closeEnough(self, q, name):
		#Meant to allow for multiple names separated by commas
		if ',' in q:
			check = False
			for n in q.split(','):
				if self.closeEnough(n,name):
					check = True
			return check
		#Checks each input word individually
		#TODO. If a full name is found the query should move on to the next pair of names.
		if ' ' in q:
			check = False
			for n in q.split(' '):
				if self.closeEnough(n,name):
					check = True
			return check
		else:
			if q.lower() in name.lower() or name.lower() in q.lower():
				return True
			else:
				return False

#Alias Form Handler. Only found in actor.html
def new_alias(request):
	if request.is_ajax and request.method == "POST":
		form = AliasForm(request.POST)
		if form.is_valid():
			first_in = form['first_name'].value()
			last_in = form['last_name'].value()
			actor = Actor.objects.get(id=request.POST.get('actor'))
			aliases = actor.aliases
			if (first_in not in [x.first_name for x in aliases] and (first_in != actor.first_name)) or (last_in not in [x.last_name for x in aliases] and last_in != actor.last_name):
				instance = form.save(commit=False)
				instance.save()
				serialized = serializers.serialize('json', [ instance, ])
				return JsonResponse({"instance":serialized},status=200)

			else:
				return JsonResponse({"error": "That name already exists for this actor"}, status=400)
		else:
			return JsonResponse({"error": "Something went wrong"}, status=400)
	return JsonResponse({"error":""}, status=400)

#Assumes videos are organized into actor dirs. Creates Actor for each.
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

#Takes actor_name and creates Actor.
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

#Returns number of Actors not created based on dir tree.
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

#Add all Videos in actor subdir or contain actor name
@login_required
def auto_add(request, actor_id):
	if not request.user.is_authenticated:
		raise Http404
	actor = Actor.objects.get(id=actor_id)
	new_vidss = scan(actor)
	for new_vids in new_vidss:
		new_vids = new_vids[0]
		title = new_vids.split('/')[-1]
		data = {'title': title[:title.index('.')],'actors': [actor],'file_path':new_vids}
		form = VideoForm(data=data)
		if form.is_valid():
			new_video = form.save(commit=False)
			new_video.owner = request.user
			update_vid(new_video)
			form.save_m2m()	
		else:
			messages.error(request,form.errors)
			return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
	return HttpResponseRedirect(reverse('video', args=[new_video.id]))

#Returns videos found in actor subdir or contain actor name
def scan(actor):
	form = VideoForm()
	choices = form.fields['file_path'].choices
	actor_videos = [x.file_path for x in Video.objects.filter(actors__isnull=False)]
	found = [x for x in choices if (("/{0}/".format(actor.full_name) in x[0]) or (actor.full_name.replace(" ","") in x[0])) and x[0] not in actor_videos]
	return found

#Empty Home page
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

#Paginated videos. Allows for sorting. filtering by resolution, tag, and actor.
@login_required
def videos(request):
	tags = request.GET.get('tag')
	actors = request.GET.get('actor')
	sort = request.GET.get('sort')
	res = request.GET.get('res')
	video_sort = ['release_date','date_added','title','length','resolution','size','actor_num','tag_num','bitrate']
	if not sort or sort.replace('-','').lower() not in video_sort:
		sort = '-date_added'
	if request.user.is_authenticated and request.user.projector.admin:
		if 'actor_num' in sort:
			videos = Video.objects.annotate(actor_num=Count('actors')).order_by(sort)
		elif 'tag_num' in sort:
			videos = Video.objects.annotate(tag_num=Count('tags')).order_by(sort)
		else:
			videos = fine_filter(request.user, sort, tags, actors, res)
	else:
		if 'actor_num' in sort:
			videos = Video.objects.annotate(actor_num=Count('actors')).filter(public=True).order_by(sort)
		else:
			videos = Video.objects.filter(public=True).order_by(sort)
	paginator = Paginator(videos, 24)
	page_num = request.GET.get('page')
	if page_num and '&' in page_num:
		page_num = page_num[:page_num.index('&')]
	page_o = paginator.get_page(page_num)
	context = {'videos':page_o, 'sort': sort, 'sort_options': video_sort, 'actors': actors,'tags': tags, 'res':res}
	return render(request, 'vid_manager/videos.html', context)

#Handles multiple filter inputs and returns a filtered and sorted list. 
def fine_filter(user, sort, tag=None, actor=None,res=None):
	reses = {'ALL':0 , 'HD':720, '1080P':1080,'4K':2160,'UHD':2160,'2K':1440,'1440p':1440,'2160p':2160,'2k':1440,'4k':2160, '1080p':1080}
	if 'resolution' in sort:
		sort = sort.replace('resolution','height')
	if not res or res not in reses.keys():
		res = 'ALL'
	if tag and actor:
		videos = Video.objects.filter(Q(tags__tag_name__icontains=tag) & Q(actors__first_name__icontains=actor) & Q(height=reses[res]),owner=user).order_by(sort)
	elif tag:
		videos = Video.objects.filter(Q(tags__tag_name__icontains=tag) & Q(height=reses[res]), owner=user).order_by(sort)
	elif actor:
		first_name, last_name = actor.split()[0], ' '.join(actor.split()[1:])
		if last_name:
			videos = Video.objects.filter(Q(actors__first_name__icontains=first_name) & Q(actors__last_name__icontains=last_name) & Q(height=reses[res]), owner=user).order_by(sort)
		else:
			videos = Video.objects.filter(Q(actors__first_name__icontains=first_name) & Q(height=reses[res]), owner=user).order_by(sort)
	else:
		videos = Video.objects.filter(height__gte=reses[res],owner=user).order_by(sort)
	return videos

#Takes POST and creates Video or provides empty VideoForm
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
			form = available_fp()
	else:
		form = VideoForm(data=request.POST)
		if form.is_valid():
			new_video = form.save(commit=False)
			new_video.owner = request.user
			update_vid(new_video)
			if request.FILES:
				new_video.poster = request.FILES['poster']
				new_video.save()
			form.save_m2m()
			return HttpResponseRedirect(reverse('video', args=[new_video.id]))
	new_tag_form = TagForm()
	new_actor_form = ActorForm()
	context = {'form': form, 'new_actor_form': new_actor_form, 'new_tag_form': new_tag_form}
	return render(request, 'vid_manager/new_video.html', context)

#Returns a blank or existing VideoForm containing filtered file_path choices. Only non-claimed file_paths allowed
def available_fp(cur=None):
	if cur:
		form = VideoForm(instance=cur)
	else:
		form = VideoForm()
	all_fps = [x.file_path for x in Video.objects.all()]
	form.fields['file_path'].choices  = [x for x in form.fields['file_path'].choices if ((cur) and cur.file_path in x[0]) or x[0] not in all_fps]
	return form

#Takes a video objects. scans and creates/updates video attributes. Video dimmensions/length/size/bitrate
def update_vid(new_video):
	try:
		v = mutagen.mp4.Open(new_video.file_path)
		seconds = v.info.length
		b_rate = v.info.bitrate
	except mutagen.mp4.MP4StreamInfoError:
		seconds=0
		b_rate=0
	fp = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'stream=width,height', '-of', 'csv=p=0:s=x', new_video.file_path])
	fp = fp.decode('ascii').rstrip()
	dim = {'width':fp.split('x')[0],'height':fp.split('x')[1]}
	try:
		new_video.height = int(dim['height'])
	except ValueError:
		new_video.height = int(dim['height'][:dim['height'].index('\n')])
		print(new_video.height)
	new_video.width = int(dim['width'])
	statinfo = stat(new_video.file_path)
	new_video.length = seconds
	new_video.bitrate = b_rate
	new_video.size = statinfo.st_size
	new_video.save()

#Takes video id and returns VideoForm instance or varifies and applies POST changes.
@login_required
def edit_video(request, video_id):
	video = get_object_or_404(Video, id=video_id)
	f_path = video.file_path
	if video.owner != request.user and video.public:
		raise Http404
	if request.method != 'POST':
		form = available_fp(video)
	else:
		form = VideoForm(instance=video, data=request.POST, files=request.FILES)
		new_video = form.save(commit=False)
		if f_path != new_video.file_path:
			update_vid(new_video)
		if (request.FILES.get('poster', False) and request.FILES.get('poster') != video.poster):
			video.poster.delete()
		if form.is_valid():
			form.save()
			return HttpResponseRedirect(reverse('video', args=[video.id]))
	context = {'video': video,'form': form}
	return render(request, 'vid_manager/edit_video.html', context)

#Takes video id and verifies ownerships before deleting video. deletes corresponding poster file. 
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

@login_required
def random_video(request):
    video = Video.objects.all().order_by("?").first()
    return HttpResponseRedirect(reverse('video', args=[video.id]))

#========================    TAGS     ==========================

@login_required
def tag_results(request):
	q = request.GET.get('q')
	tags = None
	if q:
		tags = Tag.objects.filter(tag_name__icontains=q)
	if request.is_ajax():
		html = render_to_string(template_name='vid_manager/tag_results.html', context={'tags':tags})
		data = {"tag_results_view":html}
		return JsonResponse(data=data, safe=False)
	else:
		return JsonResponse({"error":""}, status=400)

#Returns Paginated list of all Tags and empty TagForm
@login_required
def tags(request):
	if not request.user.projector.admin:
		raise Http404
	tags = Tag.objects.order_by('tag_name')
	paginator = Paginator(tags, 24)
	page_num = request.GET.get('page')
	page_o = paginator.get_page(page_num)
	context = {'tags': page_o, 'new_tag_form': TagForm()}
	return render(request, 'vid_manager/tags.html', context)

#Takes tag id and returns <=6 images and videos and total of each.
@login_required
def tag(request, tag_id=None):
	if not tag_id:
		tag_id = request.GET.get('pk')
	tag = get_object_or_404(Tag, id=tag_id)
	if not request.user.projector.admin:
		raise Http404
	else:
		videos = Video.objects.filter(tags=tag_id)
		images = Image.objects.filter(tags=tag_id)
	context = {'tag' : tag, 'videos': videos[:6], 'images': images[:6], 'v_tot':videos.count(), 'i_tot':images.count()}
	return render(request, 'vid_manager/tag.html', context)	

#Checks for permissions and deletes tag
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

#Removes the tag from video or image without deleting the tag.
@login_required
def remove_tag(request, tag_id):
	t = request.META.get('HTTP_REFERER')
	if request.is_ajax and request.user.projector.admin:
		tag = Tag.objects.get(id=tag_id)
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
					if tag not in video.tags.all():
						instance.videos.add(video)
				if 'image' in t:
					image = Image.objects.get(id=t[t.index('image')+6:])
					if tag not in image.tags.all():
						instance.tag_images.add(image)
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
					instance.tag_images.add(image)
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
		videos= Video.objects.filter(actors=actor).order_by('-date_added')
	data = {'actor':actor}
	alias_form = AliasForm(initial=data)
	context = {'actor':actor, 'videos': videos[:6], 'new_videos': len(new_videos), 'alias_form':alias_form}
	if len(images) > 10:
		context['images'] = images[:10]
	else:
		context['images'] = images
	return render(request, 'vid_manager/actor.html', context)

@login_required
def actors(request):
	sort = request.GET.get('sort')
	actor_sort = ['first_name','-first_name','last_name','-last_name']
	vid_ann = ['vid_num', '-vid_num']
	if not sort or sort not in actor_sort and sort not in vid_ann:
		sort = 'first_name'
	if not request.user.projector.admin:
		raise Http404
	if sort in vid_ann:
		actors = Actor.objects.annotate(vid_num=Count('videos')).order_by(sort)
	else:
		actors = Actor.objects.all().order_by(sort)
	total = actors.count()
	form = ActorForm()
	paginator = Paginator(actors, 24)
	page_num = request.GET.get('page')
	page_o = paginator.get_page(page_num)
	context = {'actors': page_o, 'form': form, 'new_actors':new_actor_count(),'total':total,'sort':sort}
	return render(request, 'vid_manager/actors.html', context)

@login_required
def new_actor(request):
	if request.is_ajax and request.method == "POST":
		form = ActorForm(request.POST)
		if form.is_valid():
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
	sort = request.GET.get('sort')
	image_sort = ['actors', 'id', 'image', 'tags', 'video', 'video_id']
	if not sort or sort.replace('-','') not in image_sort:
		sort = '-id'
	if request.user.is_authenticated and request.user.projector.admin:
		images = Image.objects.all().order_by(sort)
		total = images.count()
	else:
		raise Http404
	paginator = Paginator(images, 24)
	page_num = request.GET.get('page')
	page_o = paginator.get_page(page_num)
	context = {'images': page_o, 'total':total, 'sort_options': image_sort, 'sort':sort}
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
	if request.method != 'POST':
		data={}
		video = get_object_or_404(Video, id=video_id)
		data = {'video':video,'actors':video.actors.all(),'tags':video.tags.all()}
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

@login_required
def new_event(request,video_id):
	if not request.user.projector.admin:
		raise Http404
	video = Video.objects.get(id=video_id)
	if request.method != 'POST':
		messages.error(request, 'TRY GET')
	else:
		form = EventForm(data=request.POST)
		if form.is_valid() and int(request.POST.get('seconds')) < video.length:
			new_event = form.save(commit=False)
			new_event.video = video
			image_path = capture(video.file_path,int(request.POST['seconds']))
			new_event.file_path = image_path
			form.save()
			messages.success(request, 'Success! Event Added')
		else:
			messages.error(request, 'Something went wrong. Form invalid')
	return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

