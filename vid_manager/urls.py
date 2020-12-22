from django.urls import path

from . import views

urlpatterns = [
	path('',views.index, name='index'),

	#User Page
	path('<user_id>/videos/', views.videos, name='videos'),

	path('videos/<video_id>/', views.video, name='video'),
	#Add a new Video
	path('new_video/', views.new_video, name='new_video'),
	#Edit Videos
	path('edit_video/<video_id>', views.edit_video, name='edit_video'),
	#Edit Videos
	path('delete_video/<video_id>', views.delete_video, name='delete_video'),

	#delete tag
	path('delete_tag/<tag_id>', views.delete_tag, name='delete_tag'),
	#Add a new Tag
	path('new_tag/', views.new_tag, name='new_tag'),
	#Tags page
	path('tags/', views.tags, name='tags'),
	#Tag Page
	path('tags/<tag_id>/', views.tag, name='tag'),

	#ACTOR PAGES
	path('actor/<actor_id>', views.actor, name='actor'),
	path('new_actor/', views.new_actor, name='new_actor'),
	path('actors/', views.actors, name='actors'),

	path('<actor_id>/add_image', views.add_actor_image,name='add_actor_image'),
	path('<image_id>/edit_actor_image', views.edit_actor_image,name='edit_actor_image'),
]
