document.addEventListener('DOMContentLoaded', function() {
     
    // Skjul begge divs
    document.getElementById('login-div').style.display = 'none';
    document.getElementById('logged-in-div').style.display = 'none';
    
    function sanitizeInput(input) {
        // Regular expression to match only the allowed characters
        var regex = /^[a-zA-Z0-9!?.,@ ]+$/;
        var sanitizedInput = '';
    
        // Iterate through each character in the input
        for (var i = 0; i < input.length; i++) {
            if (regex.test(input[i])) {
                sanitizedInput += input[i];
            }
        }
        
        return sanitizedInput;
    }
    
    
    // Hent cookie
    function getSessionCookie() {
        let cookieArray = document.cookie.split(';');
        for (let cookie of cookieArray) {
            let [cookieName, cookieValue] = cookie.split('=');
            if (cookieName.trim() === 'session') {
                return cookieValue ? cookieValue.trim() : null;
            }
        }
        return null;
    }    
    
    // Function to check login status
    function checkLoginStatus() {
        let cookie = getSessionCookie(); 
        if (cookie) {
            var xhr = new XMLHttpRequest();
            xhr.open('POST', 'http://localhost:8180/Diktdatabase/Sesjon/', true);
            xhr.setRequestHeader('accept', 'text/xml');
            
            xhr.onload = function() {
                var responseText = xhr.responseText;
                if (responseText.includes("<message><text> Gyldig cookie! </text></message>")) {
                    document.getElementById('login-status').innerHTML = "Du er logget inn!";
                    document.getElementById('login-div').style.display = 'none';
                    document.getElementById('logged-in-div').style.display = 'block';
                    
                } else {
                    document.getElementById('login-status').innerHTML = "";
                    document.getElementById('login-div').style.display = 'block';
                    document.getElementById('logged-in-div').style.display = 'none';
                }
            };
            
            xhr.send();
        } 
        else {
            document.getElementById('login-status').innerHTML = "";
            document.getElementById('login-div').style.display = 'block';
            document.getElementById('logged-in-div').style.display = 'none';
        }  
    }
    
    // Sjekker om service worker er støttet
    function serviceWorkerSjekk() {
        if( ! ( 'serviceWorker' in navigator) ) 

            alert ('"ServiceWorker" er ikke stoettet');

        else {

            navigator.serviceWorker.register('serviceArbeider.js').then  (
                function (reg)     { alert ('Installasjon fullført')     } ).catch (
                function (err)     { alert ('Innstallasjon feilet:'+err) }
                );
        }
    }

    // Sjekker login status og service worker støtte
    checkLoginStatus()
    serviceWorkerSjekk()
    
    
    // Vis spesifisert dikt
    document.getElementById('search-form').addEventListener('submit', function(e) {
        e.preventDefault();
        
        var diktTittel = document.getElementById('dikt_tittel').value;
        
        var xhr = new XMLHttpRequest();
        xhr.open('GET', 'http://localhost:8180/Diktdatabase/Diktsamling/' + encodeURIComponent(diktTittel), true);
        
        xhr.onload = function() {
            document.getElementById('result-display').innerHTML = xhr.responseText;
        };
        
        xhr.send();
    });
    
    // Vis alle dikt
    document.getElementById('show_all-form').addEventListener('submit', function(e) {
        e.preventDefault();
        
        var xhr = new XMLHttpRequest();
        xhr.open('GET', 'http://localhost:8180/Diktdatabase/Diktsamling/', true);
        
        xhr.onload = function() {
            document.getElementById('result-display').innerHTML = xhr.responseText;
        };
        
        xhr.send();
    });
    
    
    // Logg inn
    document.getElementById('login-form').addEventListener('submit', function(e) {
        e.preventDefault();
        
        var email = document.getElementById('epost').value;
        var password = document.getElementById('password').value;
        
        // Constructing XML request
        var xmlRequest = "<Autorisering><Login><Epost>" + email + "</Epost><Passord>" + password + "</Passord></Login></Autorisering>";
        
        var xhr = new XMLHttpRequest();
        xhr.open('POST', 'http://localhost:8180/Diktdatabase/Bruker/', true);
        xhr.setRequestHeader('Content-Type', 'text/xml');
        xhr.setRequestHeader('accept', 'text/xml');
        
        xhr.onload = function() {
            document.getElementById('result-display').innerHTML = xhr.responseText;
            
            // Vis ny innlogget side
            document.getElementById('login-status').innerHTML = "Du er logget inn!";
            document.getElementById('login-div').style.display = 'none';
            document.getElementById('logged-in-div').style.display = 'block';
        };
        
        xhr.send(xmlRequest);
    });
    
    // Send inn nytt dikt
    document.getElementById('send_dikt-form').addEventListener('submit', function(e) {
        e.preventDefault();
        
        var tittel = document.getElementById('tittel').value;
        var tekst = document.getElementById('tekst').value;
        
        tittel = sanitizeInput(tittel);
        tekst = sanitizeInput(tekst);
        
        // Constructing XML request
        var xmlRequest = "<Diktsamling><Dikt><Tittel>" + tittel + "</Tittel><Tekst>" + tekst + "</Tekst></Dikt></Diktsamling>";
        
        var xhr = new XMLHttpRequest();
        xhr.open('POST', 'http://localhost:8180/Diktdatabase/Diktsamling/' + encodeURIComponent(tittel), true);
        xhr.setRequestHeader('Content-Type', 'text/xml');
        xhr.setRequestHeader('accept', 'text/xml');
        
        xhr.onload = function() {
            document.getElementById('result-display').innerHTML = xhr.responseText;
        };
        
        xhr.send(xmlRequest);
    });
    
    
    // Slette dikt
    document.getElementById('delete-dikt-form').addEventListener('submit', function(e) {
        e.preventDefault();
        
        var poemTitle = document.getElementById('del_tittel').value;
        
        // Sanitize the input
        poemTitle = sanitizeInput(poemTitle);
        
        var xhr = new XMLHttpRequest();
        xhr.open('DELETE', 'http://localhost:8180/Diktdatabase/Diktsamling/' + encodeURIComponent(poemTitle), true);
        xhr.setRequestHeader('accept', 'text/xml');
        
        xhr.onload = function() {
            document.getElementById('result-display').innerHTML = xhr.responseText;
        };
        
        xhr.send();
    });
    
    
    // Slett alle dikt
    document.getElementById('delete-all-dikt-form').addEventListener('submit', function(e) {
        e.preventDefault();
        
        var xhr = new XMLHttpRequest();
        xhr.open('DELETE', 'http://localhost:8180/Diktdatabase/Diktsamling/', true);
        xhr.setRequestHeader('accept', 'text/xml');
        
        xhr.onload = function() {
            document.getElementById('result-display').innerHTML = xhr.responseText;
        };
        
        xhr.send();
    });
    
    
    // Oppdater dikt
    document.getElementById('update-dikt-form').addEventListener('submit', function(e) {
        e.preventDefault();
        
        var oldTitle = document.getElementById('old_tittel').value;
        var newTitle = document.getElementById('new_tittel').value;
        var newText = document.getElementById('new_tekst').value;
        
        // Sanitize the inputs
        oldTitle = sanitizeInput(oldTitle);
        newTitle = sanitizeInput(newTitle);
        newText = sanitizeInput(newText);
        
        // Constructing XML request
        var xmlRequest = "<Diktsamling><Dikt><Tittel>" + newTitle + "</Tittel><Tekst>" + newText + "</Tekst></Dikt></Diktsamling>";
        
        var xhr = new XMLHttpRequest();
        xhr.open('PUT', 'http://localhost:8180/Diktdatabase/Diktsamling/' + encodeURIComponent(oldTitle), true);
        xhr.setRequestHeader('Content-Type', 'text/xml');
        xhr.setRequestHeader('accept', 'text/xml');
        
        xhr.onload = function() {
            document.getElementById('result-display').innerHTML = xhr.responseText;
        };
        
        xhr.send(xmlRequest);
    });
    
    
    // Logg ut
    document.getElementById('logout-form').addEventListener('submit', function(e) {
        e.preventDefault();
        
        var xhr = new XMLHttpRequest();
        xhr.open('DELETE', 'http://localhost:8180/Diktdatabase/Sesjon/', true);
        xhr.setRequestHeader('accept', 'text/xml');
        
        xhr.onload = function() {
            document.getElementById('result-display').innerHTML = xhr.responseText;

            // Vis ny ut-logget side
            document.getElementById('login-status').innerHTML = "";
            document.getElementById('login-div').style.display = 'block';
            document.getElementById('logged-in-div').style.display = 'none';
        };
        
        xhr.send();
    });

    
   
});
