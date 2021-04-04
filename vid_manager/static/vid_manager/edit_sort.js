
var s_tags = $('#id_tags option:selected').detach();
var tag_options = $('#id_tags option').detach();
s_tags.appendTo('#id_tags');
tag_options.appendTo('#id_tags');

var s_actors = $('#id_actors option:selected').detach();
var a_o = $('#id_actors option').detach();
s_actors.appendTo('#id_actors');
a_o.appendTo('#id_actors');