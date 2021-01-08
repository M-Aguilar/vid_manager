from django.urls import path

from . import views

urlpatterns = [
	path('',views.index, name='index'),

	#User Page
	path('<user_id>/videos', views.videos, name='videos'),

	path('videos/<video_id>', views.video, name='video'),
	#Add a new Video
	path('new_video/', views.new_video, name='new_video'),
	path('new_video/<actor_id>', views.new_video, name='new_video'),
	#Edit Videos
	path('edit_video/<video_id>', views.edit_video, name='edit_video'),
	#Edit Videos
	path('delete_video/<video_id>', views.delete_video, name='delete_video'),

	#delete tag
	path('delete_tag/<tag_id>', views.delete_tag, name='delete_tag'),
	#Add a new Tag
	path('new_tag', views.new_tag, name='new_tag'),
	#Tags page
	path('tags', views.tags, name='tags'),
	#Tag Page
	path('tags/<tag_id>', views.tag, name='tag'),

	#ACTOR PAGES
	path('actor/<actor_id>', views.actor, name='actor'),
	path('new_actor/', views.new_actor, name='new_actor'),
	path('actors/', views.actors, name='actors'),

	#ACTOR IMAGE PAGES
	path('images',views.images, name='images'),
	path('<actor_id>/images',views.images, name='images'),
	
	path('new_image',views.new_image,name='new_image'),

	path('image/<image_id>', views.image, name='image'),
	path('<image_id>/edit_image', views.edit_image,name='edit_image'),
	path('delete/<image_id>', views.delete_image, name='delete_image'),

	path('new_event/<video_id>',views.new_event,name='new_event'),
]
