const ui = $("#id_tag_name");
const tag_list = $("#tag_results");
var is_local = '';

if ($(location).attr('href').includes('local_site')) {
	is_local = '/local_site';
}

const endpoint = is_local.concat('/tag_results');
const d_lay = 700;
let scheduled = false;
let sub = true;

let tag_search = function(endpoint, tag_in) {
	$.getJSON(endpoint, tag_in)
		.done(response => {
			tag_list.html(response['tag_results_view'])
			tag_list.focus()
		})
};

function submit() {
	$('#tag_form').submit();
};

function sched_submit() {
	if (sub) {
		sub = false;
		sub = setTimeout(submit(),500);
		sub = true;
	} else {
		sub = true;
	}
};

$(".s_content").off();

ui.on('keyup', function () {
	const tag_in = {
		q: $(this).val()
	}

	if (scheduled) {
		clearTimeout(scheduled)
	}

	if (tag_in.q.length > 0){
		scheduled = setTimeout(tag_search, d_lay, endpoint, tag_in)
	}
});

ui.on('change', function() {
	let options = $(".results");
	for (let i = 0; i < options.length; i++) {
		if (options[i].value == $(this).val()) {
			submit();
			break;
		}
	}
});

ui.on('select', function() {
	sched_submit();
});