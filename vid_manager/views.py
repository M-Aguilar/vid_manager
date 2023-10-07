from django.shortcuts import render, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.http import HttpResponseRedirect, Http404, HttpRequest, HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages 
from django.core import serializers #ajax
from django.core.paginator import Paginator
from django.db.models import Count, Sum, Max
import json
from django.conf import settings

import random

from PIL import Image as im

from django.db.models import Q
from django.views.generic import ListView

from django.utils.datastructures import MultiValueDict
from django.views.generic.edit import FormView

#for Ajax rendering. ?
from django.template.loader import render_to_string

from itertools import chain
#import math

import time

#Graph generator in index.html
import plotly.graph_objects as go

from pymediainfo import MediaInfo
import subprocess

from .thumbnail import capture
from .models import Video, Tag, Actor, Event, Image, Alias, PosterColor, VideoSource, Star, VIDEO_SORT_OPTIONS
from .forms import VideoForm, TagForm, ActorForm, EventForm, ImageForm, AliasForm, VideoSourceForm

#Image Form that allows for multiple image upload
class ImageFormView(FormView):
	form_class = ImageForm
	template_name = 'vid_manager/new_image.html'
	success_url = reverse_lazy('images')

	def post(self, request, *args, **kwargs):
		form_class = self.get_form_class()
		form = self.get_form(form_class)
		files = request.FILES.getlist('image')
		if form.is_valid():
			for f in files:
				image = ImageForm(data=request.POST, files=MultiValueDict({'image':[f]}))
				image.save(commit=False)
				img = image.save()
				check_poster(img)
			if request.POST.get('video'):
				self.success_url = reverse('video', args=[request.POST.get('video')])
			return self.form_valid(form)
		else:
			return self.form_invalid(form)

#Associates a ImageColor model with a horizontal Image objects. Updates color if association exists
def check_poster(instance):
	if hasattr(instance, 'image_color'):
		rbg = pull_colors(instance)
		poster = instance.image_color
		poster.red = rbg[0]
		poster.green = rbg[1]
		poster.blue = rbg[2]
		poster.save()
	elif instance.image.width >= instance.image.height:
		instance.is_poster = True
		rbg = pull_colors(instance)
		poster_color = PosterColor(image=instance, red=rbg[0], green=rbg[1],blue=rbg[2])
		poster_color.save()
		instance.save()

#Returns search results of a given query
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
				o_list = o_list.distinct()
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


#Populates the search bar with results before submitting form
@login_required
def quick_search_results(request):
	is_ajax = request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
	if is_ajax and request.user.projector.admin:
		q = request.GET.get('q')
		results = fltr(q)
		html = render_to_string(template_name='vid_manager/quick_search_results.html', context={'results':results})
		data = {"quick_search_results_view":html}
		return JsonResponse(data=data, safe=False)
	return JsonResponse({"error":""}, status=400)

def fltr(q):
	if len(q.split()) > 1:
		results = Actor.objects.filter(first_name__icontains=q.split()[0], last_name__icontains=q.split()[1:])
		if results.count() == 1:
			return results
	else:
		tag_results = Tag.objects.filter(tag_name__icontains=q)
		actor_results = Actor.objects.filter(first_name__icontains=q)
		video_results = Video.objects.filter(title__icontains=q)
	results = {}
	if tag_results.count() > 3:
		results =  chain(results, tag_results[:3])
	elif tag_results.count() > 0:
		results = chain(results, tag_results)
	if actor_results.count() > 3:
		actor_results = actor_results[:3]
	elif actor_results.count() > 0:
		results = chain(results, actor_results)
	if video_results.count() > 3:
		video_results = video_results[:3]
	elif video_results.count() > 0:
		results = chain(results, video_results)
	return results

#Alias Form Handler. Only found in actor.html
def new_alias(request):
	is_ajax = request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
	if is_ajax and request.method == "POST":
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
		data={'first_name': ' '.join(i[0:len(i)-1]), 'last_name': i[-1]}
	form = ActorForm(data=data)
	new_actor = form.save()
	return new_actor.id

#Returns number of Actors not created based on dir tree.
def new_actor_count():
	exceptions = settings.EXCEPTIONS
	form=VideoSourceForm()
	choices = form.fields['file_path'].choices
	actors = []
	for x in Actor.objects.all():
		actors = actors + x.all_names
	new_actors = [x[0].split('/')[-2] for x in choices if x[0].split('/')[-2] not in exceptions and x[0].split('/')[-2] not in actors]
	act_list = []
	for i in new_actors:
		if i not in act_list:
			act_list.append(i)
	return act_list

#Add all Videos in actor subdir or contain actor name
@login_required
def auto_add(request, actor_id):
	if not request.user.is_authenticated:
		raise Http404
	is_ajax = request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
	actor = Actor.objects.get(id=actor_id)
	new_vids = scan(actor)
	if is_ajax:
		data = {"actor": actor.id, "new_vids":len(new_vids)}
		return JsonResponse(data=data, safe=False)
	else:
		for new_vid in new_vids:
			new_vid = new_vid[0]
			title = new_vid.split('/')[-1]
			title = title[:title.index('.mp4')]
			if len(title) > 75:
				title = title[:74]
			data = {'title': title,'actors': [actor]}
			form = VideoForm(data=data)
			if form.is_valid():
				new_video = form.save(commit=False)
				new_video.owner = request.user
				new_video.save()
				sc = VideoSource(video=new_video, file_path=new_vid)
				nv = update_vid(sc)
				if nv:
					nv.save()
				form.save_m2m()
			else:
				messages.error(request,form.errors)
				return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
		return HttpResponseRedirect(reverse('video', args=[new_video.id]))

#Returns videos found in actor subdir or contain actor name
def scan(actor):
	form = VideoSourceForm()
	choices = form.fields['file_path'].choices
	actor_videos = [x.file_path for x in VideoSource.objects.all()]
	found = [x for x in choices if (("/{0}/".format(actor.full_name) in x[0]) or (actor.full_name.replace(" ","") in x[0])) and x[0] not in actor_videos]
	return found

#Empty Home page
def index(request):
	total, count, tot_length, image_count, actor_count, graphs = 0, 0, 0, 0, 0, {}
	if request.user.is_authenticated and request.user.projector.admin and Video.objects.filter(owner_id=request.user.id).count() > 0:
		vids = Video.objects.filter(owner=request.user)
		vid_source = VideoSource.objects.filter(video__owner=request.user)
		total = str(round((vid_source.aggregate(Sum('size'))['size__sum'] * 0.000000001),2)) + "GB" 
		count, image_count, actor_count = vid_source.count(), Image.objects.all().count(), Actor.objects.all().count()
		tot_length = vid_source.aggregate(Sum('length'))['length__sum']
		res_labels, res_values, res_size_labels, res_size_values = [], [], [], []
		colors = ['cyan', 'teal', 'royalblue','darkblue', 'grey']
		
		#Res Pie Graph
		reses = vid_source.order_by('height').values('height').distinct()
		for i in reses:
			res_labels.append("<a href='videos?res={0}'>{0}p</a>".format(i['height']))
			res_values.append(vid_source.filter(height=i['height']).count())
			res_size_labels.append("<a href='videos?res={0}'>{0}p</a>".format(i['height']))
			res_size_values.append(round((vid_source.filter(height=i['height']).aggregate(Sum('size'))['size__sum'] * 0.000000001),2))
		fig = go.Figure(
			data=[go.Pie(labels=res_labels, 
						values=res_values, 
						textinfo='label+percent', 
						insidetextorientation='radial',
						marker=dict(colors=colors, line=dict(color='#000000', width=2)))])
		fig.update_layout(
		title={
			'text': "Video Totals by Resolution",
			'y':0.9,
			'x':0.5,
			'xanchor': 'center',
			'yanchor': 'top'})
		res_graph = fig.to_html(full_html=False, default_height=500)
		graphs['res_graph'] = res_graph
		
		#Res Total Storage Graph
		fig1 = go.Figure(
			data=[go.Pie(labels=res_size_labels, 
						values=res_size_values, 
						textinfo='label+percent', 
						insidetextorientation='radial',
						marker=dict(colors=colors, line=dict(color='#000000', width=2)))])
		fig1.update_layout(
		title={
			'text': "Video Resolution Storage Totals in GB",
			'y':0.9,
			'x':0.5,
			'xanchor': 'center',
			'yanchor': 'top'})
		res_graph_1 = fig1.to_html(full_html=False, default_height=500, include_plotlyjs=False)
		graphs['res_graph_1'] = res_graph_1
		
		#Actor Bar Graph
		actor_labels, v_720, v_1080, v_1440, v_2160, max_bar_values = [], [], [], [], [], 10
		actors = Actor.objects.filter(videos__in=vids).annotate(video_num=Count('videos')).filter(video_num__gt=0).order_by('-video_num')[:max_bar_values]
		for a in actors:
			if len(actor_labels) < max_bar_values:
				actor_labels.append("<a href='actor/{1}'>{0}</a>".format(a.full_name, a.id))
				v_720.append(a.videos.filter(videosource__height=720).count())
				v_1440.append(a.videos.filter(videosource__height=1440).count())
				v_1080.append(a.videos.filter(videosource__height=1080).count())
				v_2160.append(a.videos.filter(videosource__height=2160).count())
			else:
				break
		fig2 = go.Figure(data=[
			go.Bar(name="720p", x=actor_labels, y=v_720, marker=dict(color=colors[0], line=dict(color='#000000', width=2))),
			go.Bar(name="1080p", x=actor_labels, y=v_1080, marker=dict(color=colors[1], line=dict(color='#000000', width=2))),
			go.Bar(name="1440p", x=actor_labels, y=v_1440, marker=dict(color=colors[2], line=dict(color='#000000', width=2))),
			go.Bar(name="2160p", x=actor_labels, y=v_2160, marker=dict(color=colors[3], line=dict(color='#000000', width=2)))
			])
		fig2.update_layout(
		barmode = "stack",
		title={
			'text': "Top {0} Actor Video Count".format(max_bar_values),
			'y':0.9,
			'x':0.5,
			'xanchor': 'center',
			'yanchor': 'top'})
		act_graph = fig2.to_html(full_html=False, default_height=500,include_plotlyjs=False)
		graphs['act_graph'] = act_graph

		#Tag Bar Graph
		tag_labels, tag_values = [], []
		tags = Tag.objects.filter(videos__in=vids).annotate(video_num=Count('videos')).filter(video_num__gt=0).order_by('-video_num')[:max_bar_values]
		for tag in tags:
			tag_labels.append("<a href='tag/{0}'>{1}</a>".format(tag.id, tag))
			tag_values.append(tag.videos.count())
		fig3 = go.Figure(data=[go.Bar(x=tag_labels, y=tag_values, marker=dict(color=colors, line=dict(color='#000000', width=2)))])
		fig3.update_layout(
		title={
			'text': "Top {0} Tag Video Count".format(max_bar_values),
			'y':0.9,
			'x':0.5,
			'xanchor': 'center',
			'yanchor': 'top'})
		tag_graph = fig3.to_html(full_html=False, default_height=500, include_plotlyjs=False)
		graphs['tag_graph'] = tag_graph
	context = {'total':total, 'count': count, 'tot_length': tot_length, 'image_count': image_count,
	 			'actor_count': actor_count, 'graphs': graphs}
	return render(request, 'vid_manager/index.html', context)

@login_required
def manager(request):
	if not request.user.projector.admin or not request.user.is_authenticated:
		raise Http404
	else:
		videos = Video.objects.filter(owner=request.user, videosource__isnull=True)
		context = {'videos': videos}
		return render(request, 'vid_manager/manager.html', context)


def video(request, video_id):
	video = get_object_or_404(Video, id=video_id)
	if not request.user.is_authenticated:
		print(('login?{0}').format(request.path))
		return HttpResponseRedirect(reverse('login') + '?next={0}'.format(request.path))
	if video.owner != request.user and not video.public:
		raise Http404
	rel_vid = related_videos(video, 8)
	eventform = EventForm(initial={'video':video})
	context = {'video': video, 'eventform': eventform, 'tagform': TagForm(), 'related_vids': rel_vid}
	return render(request, 'vid_manager/video.html', context)

@login_required
def add_star(request, video_id):
	video = Video.objects.get(id=video_id)
	is_ajax = request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
	if video.owner == request.user and is_ajax:
		star = Star(owner=request.user, video=video)
		star.save()
		return HttpResponse(video.star_set.count())
	else:
		return JsonResponse({"error": "User/Request Error"}, status=400)

@login_required
def new_video_info(request):
	new_video = VideoSourceForm()
	new_video.save(commit=False)
	new_video.file_path = list(request.GET.keys())[0]
	nv = update_vid(new_video)
	is_ajax = request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
	if is_ajax:
		context = {'source': nv}
		return render(request, 'vid_manager/video_info.html', context)
	else:
		return JsonResponse({"error": "User/Request Error"}, status=400)

@login_required
def video_info(request, source_id):
	sc = VideoSource.objects.get(id=source_id)
	is_ajax = request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
	if request.user == sc.video.owner and is_ajax:
		context = {'source': sc}
		return render(request, 'vid_manager/video_info.html', context)
	else:
		return JsonResponse({"error": "User/Request Error"}, status=400)

def related_videos(video, total):
	videos = Video.objects.none()
	actors = video.actors.all()
	for actor in actors:
		videos = videos | actor.videos.filter(tags__in=video.tags.all()).exclude(id=video.id)
	videos = videos.distinct()
	if len(videos) <= total:
		for tag in video.tags.all():
			videos = videos | tag.videos.filter(tags__in=video.tags.all()).distinct().exclude(id=video.id)
	videos = videos.distinct()
	return videos[:total]

#Paginated videos. Allows for sorting. filtering by resolution, tag, and actor.
def videos(request):
	#Check for valid filter queries
	tags = list(dict.fromkeys(request.GET.getlist('tag')))
	actors = list(dict.fromkeys(request.GET.getlist('actor')))
	sort = request.GET.get('sort')
	res = request.GET.get('res')

	#check against valid sort options and set a default if invalid
	video_sort = VIDEO_SORT_OPTIONS
	if not sort or sort.replace('-','').lower() not in video_sort:
		sort = '-date_added'
	
	#if user is logged in filter through own videos, otherwise only consider public videos
	if request.user.is_authenticated and request.user.projector.admin:
		videos = fine_filter(request.user, sort, tags, actors, res)
	else:
		videos = fine_filter(None, sort, tags, actors, res)
	
	#return top 20 tags found in video list
	tt = top_tags(videos, 20)

	#pagination
	paginator = Paginator(videos, 24)
	page_num = request.GET.get('page')
	page_o = paginator.get_page(page_num)
	context = {'videos':page_o, 'sort': sort, 'sort_options': video_sort, 'actors': actors,'tags': tags, 'res':res, 'top_tags': tt}
	return render(request, 'vid_manager/videos.html', context)

#Handles multiple filter inputs and returns a filtered and sorted list. 
def fine_filter(user, sort, tags=None, actors=None, res=None):

	#filter videos by username or public depending on call
	if user:
		videos = Video.objects.filter(owner=user)
	else:
		videos = Video.objects.filter(public=True)
	
	#the values in reses are valid sorting options for resolutions. They keys are checked against video height
	reses = {720: ['HD'], 1080: ['FHD'], 2160: ['4K', 'UHD'], 1440: ['2K', 'QHD']}
	
	#resolution is currently guaged by video height.
	if 'resolution' in sort:
		sort = sort.replace('resolution','height')

	#Filters videos by actor names provided
	if actors:
		for a in actors:
			name = a.split()
			if len(name) > 1:
				videos = videos.filter(Q(actors__first_name__icontains=name[0]) & Q(actors__last_name__icontains=name[-1]))
			else:
				videos = videos.filter(Q(actors__first_name__icontains=name[0]))

	#Filters videos by tag names provided
	if tags:
		for t in tags:
			videos = videos.filter(Q(tags__tag_name=t))

	#Filters by resolution(height). Inputs ending in p (e.g. 1080p) are valid.
	#> < => =< are valid. = is the default
	if res:
		sym,r = None, 0
		if 'p' in res or 'P' in res:
			res = res.lower().split('p')[0]
		if '<=' in res:
			sym = '<='
		elif '>=' in res:
			sym = '>='
		elif '<' in res:
			sym = "<"	
		elif '>' in res:
			sym = '>'
		if sym:
			#helper for handling other valid inputs
			r = res_helper(sym, res, reses)
		try:
			r = int(res)
		except ValueError:
			pass

		#if input is not valid after striping of 'P' and conditionals then return all valid video regardless of resolution
		if not isinstance(r, int):
			videos = videos.filter(Q(videosource__height__gte=0))
		elif sym == '<=':
			videos = videos.filter(Q(videosource__height__lte=r))
		elif sym == '>=':
			videos = videos.filter(Q(videosource__height__gte=r))
		elif sym == '<':
			videos = videos.filter(Q(videosource__height__lt=r))		
		elif sym == '>':
			videos = videos.filter(Q(videosource__height__gt=r))
		else:
			videos = videos.filter(Q(videosource__height=res))

	#Order By
	if 'actor_num' in sort:
		videos = videos.annotate(actor_num=Count('actors'))
	elif 'tag_num' in sort:
		videos = videos.annotate(tag_num=Count('tags'))
	elif 'image_num' in sort:
		videos = videos.annotate(image_num=Count('images'))
	elif 'poster_num' in sort:
		videos = videos.annotate(poster_num=Count('images', filter=Q(images__is_poster=True)))
	elif 'source_num' in sort:
		videos = videos.annotate(source_num=Count('videosource'))
	elif 'length' in sort:
		videos = videos.annotate(length=Max('videosource__length'))
	elif 'size' in sort:
		videos = videos.annotate(size=Max('videosource__size'))
	elif 'bitrate' in sort:
		videos = videos.annotate(bitrate=Max('videosource__bitrate'))
	elif 'height' in sort:
		videos = videos.annotate(height=Max('videosource__height'))
	videos = videos.order_by(sort)
	if sort.replace('-','') in ['title', 'release_date','actor_num','tag_num','image_num', 'source_num','length','size', 'bitrate','height']:
		videos = videos.reverse()
	return videos

#Checks for valid keywords such as "FHD" or "UHD"
def res_helper(sym, res, reses):
	r = res.split(sym)[1]
	found = [True for x in reses.values() if r.upper() in x]
	if found:
		r = get_keys_from_value(reses, r.upper())
		return r[0]
	return r

#returns key value in dict: d for provided value: val
def get_keys_from_value(d, val):
	return [k for k, v in d.items() if val in v]

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
			vs_form = available_fp()
			vs_form.fields['file_path'].choices = scan(actor)
		else:
			form = VideoForm()
			vs_form = available_fp()
	else:
		form = VideoForm(data=request.POST)
		if form.is_valid():
			new_video = form.save(commit=False)
			new_video.owner = request.user
			new_video.save()
			form.save_m2m()
			for sc in request.POST.getlist('file_path'):	
				if VideoSource.objects.filter(file_path=sc).count() == 0:
					v_path = VideoSource(video=new_video,file_path=sc)
					uv = update_vid(v_path)
					if uv:
						uv.save()
					if not uv:
						messages.error(request, "Invalid filename: {0}".format(sc))
						new_video.delete()
						return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
				else:
					messages.error(request, "{0} is already in use".format(sc))
			#return HttpResponseRedirect(reverse('new_video'))
			return HttpResponseRedirect(reverse('video', args=[new_video.id]))
	new_tag_form = TagForm()
	new_actor_form = ActorForm()
	context = {'form': form, 'new_actor_form': new_actor_form, 'new_tag_form': new_tag_form, 'video_source_form': vs_form}
	return render(request, 'vid_manager/new_video.html', context)

#Returns a blank or existing VideoForm containing filtered file_path choices. Only non-claimed file_paths allowed
#Provide current video to exclude.
def available_fp(cur=None):
	if cur:
		form = VideoSourceForm(instance=cur)
	else:
		form = VideoSourceForm()
	all_fps = [x.file_path for x in VideoSource.objects.all()]
	form.fields['file_path'].choices  = [x for x in form.fields['file_path'].choices if ((cur) and cur.file_path in x[0]) or x[0] not in all_fps]
	return form

#Takes a video objects. scans and creates/updates video attributes. Video dimmensions/length/size/bitrate
def update_vid(new_video):
	try:
		v = MediaInfo.parse(new_video.file_path)
		info = v.tracks[1]
		new_video.height = info.height
		new_video.width = info.width
		new_video.length = round(float(info.duration/1000),0)
		new_video.bitrate = v.tracks[0].overall_bit_rate
		new_video.size = v.tracks[0].file_size
		#new_video.framerate = info.frame_rate
		return new_video
	except FileNotFoundError:
		return False

#Takes video id and returns VideoForm instance or varifies and applies POST changes.
@login_required
def edit_video(request, video_id):
	video = get_object_or_404(Video, id=video_id)
	if video.owner != request.user and video.public:
		raise Http404
	if request.method != 'POST':
		form = VideoForm(instance=video)
		vs_forms = []
		for vs in video.videosource_set.all():
			vs_forms.append(available_fp(vs))
	else:
		form = VideoForm(instance=video, data=request.POST)
		if form.is_valid():
			sources = video.videosource_set.all()
			s_list = list(sources.values_list('file_path', flat=True))
			post_source = request.POST.getlist('file_path')
			for sc in sources:
				if sc.file_path not in post_source:
					sc.delete()
			for ns in post_source:
				if ns not in s_list:
					if VideoSource.objects.filter(file_path=ns).count() == 0:
						source = VideoSource(video=video, file_path=ns)
						new_video = update_vid(source)
						if new_video:
							new_video.save()
					else:
						messages.error(request, "{0} is already in use".format(ns))
			new_video = form.save(commit=False)
			form.save_m2m()
			new_video = form.save()
			return HttpResponseRedirect(reverse('video', args=[video.id]))
	context = {'video': video,'form': form, 'vs_forms': vs_forms}
	return render(request, 'vid_manager/edit_video.html', context)

#Returns full page for adding videosource or just the form when in new_video page allowing for multiple source during video creation
@login_required
def new_video_source(request, video_id=None):
	#Checks if video exists.
	if video_id:
		video = get_object_or_404(Video, id=video_id)
		if video.owner != request.user or not request.user.projector.admin:
			raise Http404
	#Check not POST
	if request.method != 'POST':
		#Checks if ajax request is made and returns form to be rendered in new_video page
		is_ajax = request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
		if is_ajax:
			try:
				form = available_fp()
				return HttpResponse(form)
			except Exception as e:
				return JsonResponse({"error":e}, status=400)
		#Form = basic page
		form = available_fp()
	else:
		#Submit new video object.
		form = VideoSourceForm(data=request.POST)
		new_source = form.save(commit=False)
		new_source.video = video
		new_video = update_vid(new_source)
		if new_video:
			new_video.save()
		#return page and new object id
		return HttpResponseRedirect(reverse('video', args=[video.id]))
	context = {'video': video, 'form': form}
	return render(request, 'vid_manager/new_video_source.html', context)

#Takes video id and verifies ownerships before deleting video. deletes corresponding poster file. 
@login_required
def delete_video(request, video_id):
	v = get_object_or_404(Video, id=video_id)
	if request.user.is_authenticated and request.user.projector.admin:
		events = Event.objects.filter(video=v)
		if events.count() >0:
			for e in events:
				subprocess.Popen(['sudo','rm', e.file_path])
		for vs in v.videosource_set.all():
			vs.delete()
		for i in v.images.all():
			i.image.delete()
			i.delete()
		v.delete()
		messages.success(request, "Video {0} Succesfully Deleted".format(video_id))
	else:
		messages.error(request, 'Something wet wrong')
	return HttpResponseRedirect(reverse('videos'))

#random video
@login_required
def random_video(request):
	tag = request.GET.get('tag')
	actor = request.GET.get('actor')
	video = None
	if actor:
		name = actor.split()
		if len(name) > 1:
			videos = list(Video.objects.filter(Q(owner=request.user),Q(actors__first_name=name[0]) & Q(actors__last_name=' '.join(name[1:]))))
			video = random.choice(videos)
		else:
			videos = list(Video.objects.filter(Q(actors__first_name=name[0]) & Q(owner=request.user)))
			video = random.choice(videos)
	elif tag:
		videos = list(Video.objects.filter(Q(tags__tag_name=tag) & Q(owner=request.user)))
		video = random.choice(videos)
	if not video:
		videos = list(Video.objects.filter(owner=request.user))
		video = random.choice(videos)
	if not video:
		messages.error('You have no videos')
		return HttpResponseRedirect('videos')
	return HttpResponseRedirect(reverse('video', args=[video.id]))

#========================    TAGS     ==========================

#Takes tag id and returns <=6 images and videos and total of each.
@login_required
def tag(request, tag_id=None):
	if not tag_id:
		tag_id = request.GET.get('pk')
	tag = get_object_or_404(Tag, id=tag_id)
	if not request.user.projector.admin:
		raise Http404
	else:
		videos = Video.objects.filter(tags=tag_id)[:6]
		images = Image.objects.filter(tags=tag_id)[:6]
	context = {'tag' : tag, 'videos': videos, 'images': images, 'v_tot':videos.count(), 'i_tot':images.count()}
	return render(request, 'vid_manager/tag.html', context)	

#Returns Paginated list of all Tags and empty TagForm
@login_required
def tags(request):
	sort_options = ['tag_name', 'id', 'video_num','image_num']
	sort = request.GET.get('sort')
	video = request.GET.get('video')
	vid = None
	if not sort or sort.replace('-','') not in sort_options:
		sort = 'tag_name'
	if not request.user.projector.admin:
		raise Http404
	if video:
		try:
			vid = Video.objects.get(id=video)
			tags=vid.tags.all()
		except Video.DoesNotExist:
			tags = Tag.objects.all()
	else:
		tags = Tag.objects.all()
	if sort and sort.replace('-','') == 'video_num':
		tags = Tag.objects.annotate(video_num=Count('videos'))
	elif sort and sort.replace('-','') == 'image_num':
		tags = Tag.objects.annotate(image_num=Count('tag_images'))
	tags = tags.order_by(sort)
	paginator = Paginator(tags, 24)
	page_num = request.GET.get('page')
	page_o = paginator.get_page(page_num)
	context = {'tags': page_o, 'new_tag_form': TagForm(),'sort_options':sort_options,'sort':sort}
	if vid:
		context['video'] = vid
	return render(request, 'vid_manager/tags.html', context)

#takes videos and returns the top tags limited by total.
def top_tags(videos, total=None):
	top_tags = Tag.objects.annotate(video_num=Count('videos')).filter(videos__in=videos).order_by('-video_num')
	if total and isinstance(total, int):
		return top_tags[:total]
	else: 
		return top_tags

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
		messages.error(request, "Something went wrong")
	return HttpResponseRedirect(reverse('tags'))

#Removes the tag from video or image without deleting the tag.
@login_required
def remove_tag(request, tag_id):
	t = request.META.get('HTTP_REFERER')
	is_ajax = request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
	if is_ajax and request.user.projector.admin:
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

#creates a new tag if requested tag does not exists.
#otherwise tag is ammended to the referring objects tag list
@login_required
def new_tag(request):
	t = request.META.get('HTTP_REFERER')
	is_ajax = request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
	if is_ajax and request.method == "POST":
		form = TagForm(request.POST)
		try:
			tag = Tag.objects.get(tag_name=form.data['tag_name'])
			if tag:
				instance = tag
				if 'video' in t:
					video = Video.objects.get(id=t[t.index('video')+6:])
					if tag not in video.tags.all():
						video.tags.add(instance)
				elif 'image' in t:
					image = Image.objects.get(id=t[t.index('image')+6:])
					if tag not in image.tags.all():
						image.tags.add(instance)
				serialized = serializers.serialize('json', [ instance, ])
				return JsonResponse({"instance":serialized},status=200)
		except Tag.DoesNotExist:
			if form.is_valid():
				instance = form.save()
				if 'video' in t:
					video = Video.objects.get(id=t[t.index('video')+6:])
					instance.videos.add(video)
				elif 'image' in t:
					image = Image.objects.get(id=t[t.index('image')+6:])
					instance.tag_images.add(image)
				serialized = serializers.serialize('json', [ instance, ])
				return JsonResponse({"instance":serialized},status=200)
			else:
				return JsonResponse(form.error, status=400)
	return JsonResponse({"error":""}, status=400)

#returns JSON list of tags matching q
@login_required
def tag_results(request):
	q = request.GET.get('q')
	t = request.META.get('HTTP_REFERER')
	is_ajax = request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
	if request.user.projector.admin and q and is_ajax:
		tags = None
		if 'video' in t:
			video = Video.objects.get(id=t[t.index('video')+6:])
			tags = Tag.objects.filter(tag_name__icontains=q).exclude(id__in=video.tags.all())
		if 'image' in t:
			image = Image.objects.get(id=t[t.index('image')+6:])
			tags = Tag.objects.filter(tag_name__icontains=q).exclude(id__in=image.tags.all())
		if is_ajax:
			html = render_to_string(template_name='vid_manager/tag_results.html', context={'tags':tags})
			data = {"tag_results_view":html}
			return JsonResponse(data=data, safe=False)
		else:
			return JsonResponse({"error":""}, status=400)

#returns tag_tile found in video.html and image.html generated after quick adding a new tag
def tag_tile(request, tag_id):
	tag = get_object_or_404(Tag, id=tag_id)
	return render(request, 'vid_manager/tag_tile.html', {'tag':tag})

#returns tags_tiles that are found in the tags page. Generated after adding a new tag
def tags_tile(request, tag_id):
	tag = get_object_or_404(Tag, id=tag_id)
	is_ajax = request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
	if is_ajax and request.method != "POST" and request.user.projector.admin:
		return render(request, 'vid_manager/tags_tile.html', {'tag':tag})

'''########################    ACTOR     #########################'''

#returns actor_tiles that are found in actors.html. Generated after adding a new actor.
@login_required
def actor_tile(request, actor_id):
	actor = get_object_or_404(Actor, id=actor_id)
	is_ajax = request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
	if is_ajax and request.method != "POST" and request.user.projector.admin:
		return render(request, 'vid_manager/actor_tile.html', {'actor': actor})

#Individual actor page. Shows max 10 images, max 8 videos and top 5 tags in all actor videos.
@login_required
def actor(request, actor_id):
	if not request.user.projector.admin:
		raise Http404
	else:
		actor = get_object_or_404(Actor,id=actor_id)
		new_videos = scan(actor)
		images = Image.objects.filter(actors=actor)[:10]
		videos = actor.videos.order_by('-date_added')
		tt = top_tags(videos, 5)
	data = {'actor':actor}
	alias_form = AliasForm(initial=data)
	context = {'actor':actor, 'videos': videos[:8], 'new_videos': len(new_videos), 'alias_form':alias_form, 'images': images, 'top_tags': tt}
	return render(request, 'vid_manager/actor.html', context)

#page for viewing all actors. By default actors are sorted by first name. 
@login_required
def actors(request):
	sort = request.GET.get('sort')
	actor_sort = ['first_name','last_name','vid_num','image_num']
	if not sort or sort.replace('-','') not in actor_sort:
		sort = 'first_name'
	if not request.user.projector.admin:
		raise Http404
	if sort.replace('-','') == 'vid_num':
		actors = Actor.objects.annotate(vid_num=Count('videos')).order_by(sort)
	elif sort.replace('-','') == 'image_num':
		actors = Actor.objects.annotate(image_num=Count('actor_images')).order_by(sort)
	else:
		actors = Actor.objects.all().order_by(sort)
	total = actors.count()
	form = ActorForm()
	paginator = Paginator(actors, 24)
	page_num = request.GET.get('page')
	page_o = paginator.get_page(page_num)
	context = {'actors': page_o, 'form': form, 'new_actors':len(new_actor_count()),'total':total,'sort':sort,'sort_options': actor_sort}
	return render(request, 'vid_manager/actors.html', context)

#deletes actors as well as all associated images
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

#creates new actors
@login_required
def new_actor(request, actor_name=""):
	is_ajax = request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
	if is_ajax and request.method == "POST":
		form = ActorForm(request.POST)
		if form.is_valid():
			instance = form.save(commit=False)
			instance.save()
			serialized = serializers.serialize('json', [ instance, ])
			return JsonResponse({"instance":serialized},status=200)
		else:
			return JsonResponse({"error": "That name is already in use"}, status=400)
	else:
		aid = add_actor(actor_name)
		return HttpResponseRedirect(reverse('actor', args=[aid]))
	return JsonResponse({"error":""}, status=400)


'''########################    IMAGES     #########################'''

#Returns a single color from the image. The most common color and least grey.
def pull_colors(img_obj):
	i = []
	with im.open(img_obj.image.path) as ifile:
		t_i = ifile.resize((150,150))
		i = im.Image.getcolors(t_i, maxcolors=(150*150))
	i.sort(key=lambda tup: tup[0], reverse=True)
	color = i[0][1][:3]
	limit = len(i)
	if limit > 20:
		limit=20
	for c in i[1:limit]:
		if ((abs(c[1][0]-c[1][1]) + abs(c[1][1]-c[1][2])) > (abs(color[0]-color[1]) + abs(color[1]-color[2]))):
			color = c[1][:3]
	return color

#page for viewing individual an image
@login_required
def image(request, image_id):
	request.session['ref'] = request.META.get('HTTP_REFERER')
	image = Image.objects.get(id=image_id)
	if not request.user.projector.admin or not image:
		raise Http404
	actors = image.actors.all()
	tag_form = TagForm()
	context = {'image':image,'actors':actors, 'tagform': tag_form}
	return render(request, 'vid_manager/image.html', context)

#Returns all images sorted by -date_added or checks for filters/sorting inputs
@login_required
def images(request):
	sort = request.GET.get('sort')
	image_sort = ['actors', 'id', 'tags', 'video', 'video_id', 'tag_num', 'actor_num','is_poster']
	tags = request.GET.getlist('tag')
	actors = request.GET.getlist('actor')
	video = request.GET.get('video')
	if not sort or sort.replace('-','') not in image_sort:
		sort = '-id'
	if request.user.is_authenticated and request.user.projector.admin:
		vid = Video.objects.none
		if video:
			vid = Video.objects.get(id=video)
			if vid.owner != request.user:
				raise Http404
			else:
				images = vid.images.all()
		else:
			images = Image.objects.filter(Q(video__owner=request.user))
			if actors:
				for actor in actors:
					a = actor.split()
					if len(a) > 1:
						images = images.filter(Q(actors__first_name=a[0]) & Q(actors__last_name=''.join(a[1:])))
					else:
						images = images.filter(Q(actors__first_name__icontains=a[0]))
			if tags:
				for tag in tags:
					images = images.filter(tags__tag_name__icontains=tag)
	else:
		raise Http404
	if sort.replace('-','') == 'tag_num':
		images = images.annotate(tag_num=Count('tags'))
	elif sort.replace('-','') == 'actor_num':
		images = images.annotate(actor_num=Count('actors'))
	images = images.order_by(sort)
	if sort.replace('-','') in ['tag_num','actor_num', 'is_poster']:
		images = images.reverse()
	paginator = Paginator(images, 24)
	page_num = request.GET.get('page')
	page_o = paginator.get_page(page_num)
	context = {'images': page_o,'sort_options': image_sort, 'sort':sort,'actors':actors,'tags':tags}
	if vid:
		context['video'] = vid
	return render(request,'vid_manager/images.html',context)

#function for deleting all images related to a specified video
@login_required
def delete_images(request, video_id):
	if request.user.is_authenticated and request.user.projector.admin:
		video = get_object_or_404(Video, id=video_id)
		if request.user == video.owner:
			tot = video.images.all().count()
			for image in video.images.all():
				image.image.delete()
				image.delete()
			messages.success(request, "All images for {0} have been deleted. Total: {1}".format(video, tot))
			return HttpResponseRedirect(reverse('video', args=[video.id]))
	messages.error(request, 'Permission denied. 🔒')
	return HttpResponseRedirect(request.META.get('HTTP_REFERRER'))

#function for deleting an individual image
@login_required
def delete_image(request, image_id):
	image = Image.objects.get(id=image_id)
	if request.user.is_authenticated and request.user.projector.admin and request.method == "POST":
		i_id = image.id
		i_i = image.image.name
		image.image.delete()
		image.delete()
		messages.success(request, "Image ID: {0} Filename: {1} has been deleted.".format(i_id,i_i))
		ref = request.session.get('ref')
		request.session['ref'] = None
		if '/actor/' in ref:
			return HttpResponseRedirect(reverse('actor', args=[ref.split('/')[-1]]))
		if '/video/' in ref:
			return HttpResponseRedirect(reverse('video', args=[ref.split('/')[-1]]))
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
		form = ImageForm(instance=image)
	else:
		#Post data submitted; process data
		form = ImageForm(instance=image, files=request.FILES, data=request.POST)
		if form.is_valid():
			img = form.save()
			check_poster(img) #questionable
			ref = request.session.get('ref')
			request.session['ref'] = None
			if ref and 'actor' in ref:
				return HttpResponseRedirect(reverse('actor', args=[ref.split('/')[-1]]))
			if ref and 'video' in ref:
				return HttpResponseRedirect(reverse('video', args=[ref.split('/')[-1]]))
			return HttpResponseRedirect(reverse('images'))
	context = {'image': image,'form': form}
	return render(request, 'vid_manager/edit_image.html', context)

#form page for adding adding video images. Could be combined with ImageView
@login_required
def new_video_image(request, video_id):
	if request.method != 'POST':
		video = get_object_or_404(Video, id=video_id)
		data = {'video':video,'actors':video.actors.all(),'tags':video.tags.all()}
		form = ImageForm(initial=data)
		context = {'form':form}
		return render(request, 'vid_manager/new_image.html', context)

#form page for adding actor images
@login_required
def new_actor_image(request, actor_id):
	if request.method == 'GET':
		actors = get_object_or_404(Actor, id=actor_id)
		data = {'actors':actors}
		form = ImageForm(initial=data)
		context = {'form':form}
		return render(request, 'vid_manager/new_image.html', context)

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

def delete_event(request, event_id):
	event = get_object_or_404(Event, id=event_id)
	is_ajax = request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
	if is_ajax and request.user.projector.admin and event.video.owner == request.user:
		temp_event = event
		pk = event.id
		event.delete()
		instance = temp_event
		instance.pk = pk
		return JsonResponse({'instance':serializers.serialize('json',[instance,])}, status=200)
	else:
		return JsonResponse({"error":""}, status=400)