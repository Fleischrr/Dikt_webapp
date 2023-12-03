self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open('mellomlagring').then(function(cache) {
            return cache.addAll([
                '/',
                '/index.html',
                'http://localhost:8000/js/form-handler.js',
                'http://localhost:8000/js/style/dikt.css'
            ]);
        })
    );
});


self.addEventListener('fetch', function(event) {
    event.respondWith(
        caches.match(event.request)
    );
});
