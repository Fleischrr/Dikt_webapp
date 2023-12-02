self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open('mellomlagring').then(function(cache) {
            return cache.addAll([
                '/',
                '/index.html',
                'http://kans-sndbox/js/form-handler.js',
                'http://kans-sndbox/js/style/dikt.css'
            ]);
        })
    );
});


self.addEventListener('fetch', function(event) {
    event.respondWith(
        caches.match(event.request)
    );
});
