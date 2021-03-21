const ui_in = $("#search");
const result_list = $("#quick_search_results");
var is_local = '';

if ($(location).attr('href').includes('local_site')) {
	is_local = '/local_site'
}

const search_ep = is_local.concat('/quick_search_results');
const d_la = 700;
let sched = false;

function hde() {
	$("#quick_search_results .dropdown-menu").hide()
}

let search_result = function(search_ep, q_in) {
	$.getJSON(search_ep, q_in)
		.done(response => {
			result_list.html(response['quick_search_results_view'])
			if ($(".qsr").length > 0) {
				$("#quick_search_results .dropdown-menu").show()
			} else {
				hde()
			}
		})
};

ui_in.on('focusout', function() {
	window.setTimeout(function() {hde()}, 100)
});

ui_in.on('click', function() {
	if ($(".qsr").length > 0) {
		$("#quick_search_results .dropdown-menu").toggle()
	}
});

//Generates search results by checking input shortly after input seizes
ui_in.on('keyup', function () {
	const q_in = {
		q: $(this).val()
	}

	if (sched) {
		clearTimeout(sched)
	}

	if (q_in.q.length > 0){
		sched = setTimeout(search_result, d_la, search_ep, q_in)
	} else {
		$(".qsr").remove()
		hde()
	}
});
