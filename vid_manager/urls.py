from django.urls import path

from . import views

urlpatterns = [
	#Home Page
	path('',views.index, name='index'),

	#Search
	path('search/', views.SearchResultsView.as_view(), name='search_results'),
	
	#Videos
	path('videos', views.videos, name='videos'),
	path('random_video', views.random_video, name='random_video'),
	path('video/<video_id>', views.video, name='video'),
	path('new_video/', views.new_video, name='new_video'),
	path('new_video/<actor_id>', views.new_video, name='new_video'),
	path('edit_video/<video_id>', views.edit_video, name='edit_video'),
	path('delete_video/<video_id>', views.delete_video, name='delete_video'),

	#Tags
	path('tag/<tag_id>', views.tag, name='tag'),
	path('tags', views.tags, name='tags'),
	path('new_tag', views.new_tag, name='new_tag'),
	path('delete_tag/<tag_id>', views.delete_tag, name='delete_tag'),
	path('remove_tag/<tag_id>', views.remove_tag, name='remove_tag'),
	path('<video_id>/new_tag',views.new_tag, name="new_video_tag"),

	#Actor
	path('actor/<actor_id>', views.actor, name='actor'),
	path('new_actor', views.new_actor, name='new_actor'),
	path('actors', views.actors, name='actors'),
	path('<actor_id>/delete', views.delete_actor, name='delete_actor'),
	path('new_alias', views.new_alias, name='new_alias'),

	#Auto Add Actor Videos
	path('<actor_id>/auto_add', views.auto_add, name='auto_add'),

	#Auto add actors
	path('auto_actor_add', views.auto_actor_add, name='auto_actor_add'),

	#Actor Images
	path('<actor_id>/images',views.actor_images, name='actor_images'),

	#Tag Images
	path('images/<tag_id>', views.tag_images, name='tag_images'),

	#Images
	path('image/<image_id>', views.image, name='image'),
	path('images',views.images, name='images'),
	path('new_image',views.new_image,name='new_image'),
	path('<image_id>/edit_image', views.edit_image,name='edit_image'),
	path('delete/<image_id>', views.delete_image, name='delete_image'),
	path('<actor_id>/new_actor_image',views.new_actor_image, name='new_actor_image'),
	path('<video_id>/new_video_image',views.new_video_image, name='new_video_image'),

	#Events
	path('new_event/<video_id>',views.new_event,name='new_event'),

	#TODO: Delete Event.
]
