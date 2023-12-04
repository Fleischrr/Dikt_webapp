const CACHE_NAME = 'mellomlagring';
const STATIC_URLS = [
    '/',
    '/index.html',
    'http://localhost:8000/js/form-handler.js',
    'http://localhost:8000/style/dikt.css',
    'http://localhost:8180/Diktdatabase/Diktsamling/'
];

// Event som blir trigget når serviceworker blir registrert
self.addEventListener('install', function(event) {
    
    // Venter til alt i kallet er ferdig før videre kjøring
    event.waitUntil(

        // Åpner cache og henter responser som skal mellomlagres 
        caches.open(CACHE_NAME)
            .then(function(cache) {
                return cache.addAll(STATIC_URLS);
            })
    );
});

// Event som blir trigget når serviceworker blir aktivert
self.addEventListener('fetch', function(event) {
    
    // Responderer med nettverks forespørsel
    event.respondWith(
        fetch(event.request).catch(function() {
            
            // Returnerer fra mellomlagring ved feilet forespøsel
            return caches.match(event.request);
        })
            
    );
});

