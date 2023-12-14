# Dikt_webapp
Prosjekt repo for emnet VE3260, *Utvikling av sikre webtjenester med prosjekt*.

Div:

For å at root i docker skal være uprivligert i værtssystemet ble daemon.json konfigurert sånn her:
/etc/docker/daemon.json
{
  "userns-remap": "default"
}

Dette lager en ny bruker "dockremap" på værtssystemet som gir muligheten å "mappe" tilgang mellom docker og vært.
Eks. Diktdatabase.db, som er et volum for konteiner-2. 
Uten riktig "remappet" fil-eierskap på databasefilen, vil dette volumet være utilgjengelig å endre/aksessere for alt i docker konteiner.


**Arkitekturskisse for fullført prosjekt:**
![Skjermbilde 2023-10-27 205458](https://github.com/Fleischrr/Dikt_webapp/assets/96070187/3ba244d4-976f-48fd-a2ff-a5bb41ac6d75)

