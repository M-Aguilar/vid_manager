from django.urls import path

from . import views

urlpatterns = [
	path('',views.index, name='index'),

	#Actor Video
	#path('<actor_id>/videos', views.videos, name='videos'),

	#All Videos
	path('videos', views.videos, name='videos'),

	#Tag Videos
	path('videos/<tag_id>', views.tag_videos, name='tag_videos'),

	#Actor Videos
	path('<actor_id>/videos', views.actor_videos, name='actor_videos'),

	#Individual Video
	path('video/<video_id>', views.video, name='video'),

	#New Video
	path('new_video/', views.new_video, name='new_video'),

	#New actor Video
	path('new_video/<actor_id>', views.new_video, name='new_video'),

	#Edit Video
	path('edit_video/<video_id>', views.edit_video, name='edit_video'),

	#Delete Video
	path('delete_video/<video_id>', views.delete_video, name='delete_video'),

	#Delete Tag
	path('delete_tag/<tag_id>', views.delete_tag, name='delete_tag'),

	path('remove_tag/<tag_id>', views.remove_tag, name='remove_tag'),

	path('remove_tag', views.remove_tag, name='remove_tag'),

	#New Tag
	path('new_tag', views.new_tag, name='new_tag'),

	#New Video Tag
	path('<video_id>/new_tag',views.new_tag, name="new_video_tag"),

	#All Tags
	path('tags', views.tags, name='tags'),

	#Individual Tag
	path('tag/<tag_id>', views.tag, name='tag'),

	#Actor
	path('actor/<actor_id>', views.actor, name='actor'),

	#New Actor
	path('new_actor', views.new_actor, name='new_actor'),

	#All Actors
	path('actors', views.actors, name='actors'),

	path('<actor_id>/delete', views.delete_actor, name='delete_actor'),
	#ACTOR IMAGE PAGES
#	path('<actor_id>/images/#=<page_num>',views.images, name='images'),
	
	#Actor Images
	path('<actor_id>/images',views.actor_images, name='actor_images'),
#	path('images/<tag_id>/#=<page_num>',views.images, name='images'),

	#Tag Images
	path('images/<tag_id>', views.tag_images, name='tag_images'),
	#path('images/#=<page_num>',views.images, name='images'),

	#All Images
	path('images',views.images, name='images'),

	#New Actor Image
	path('<actor_id>/new_actor_image',views.new_actor_image, name='new_actor_image'),	

	#New Video Image
	path('<video_id>/new_video_image',views.new_video_image, name='new_video_image'),

	#New Image
	path('new_image',views.new_image,name='new_image'),

	#Individual Image
	path('image/<image_id>', views.image, name='image'),

	#Edit Image
	path('<image_id>/edit_image', views.edit_image,name='edit_image'),

	#Delete Image
	path('delete/<image_id>', views.delete_image, name='delete_image'),

	#New Event
	path('new_event/<video_id>',views.new_event,name='new_event'),

	#TODO: Delete Event. Page Numbers (Tags Actors Images Videos)
]
