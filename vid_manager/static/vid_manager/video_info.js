var appleWebKit = navigator.userAgent.includes("AppleWebKit/6")
var vid = document.querySelector('video')

var observerOptions = {
        attributes: true
};


if (appleWebKit == true) {
    var observer = new WebKitMutationObserver(callback);
} else {
    var observer = new MutationObserver(callback);
}

function callback(mutationList, observer) {
    mutationList.forEach( (mutation) => {
        switch(mutation.type) {
            case 'attributes':
                if (mutation.attributeName === 'src') {
                    get_info(mutation.target.src)
                }
                break;
        }
    })
};

observer.observe(vid, observerOptions);