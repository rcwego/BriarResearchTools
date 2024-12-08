# BriarResearchTools

## Beskrivelse
BriarResearchTools er en samling verktøy utviklet for forskning og dataanalyse knyttet til meldingsapplikasjonen Briar. Repositoriet er best forstått i sammenheng med den tilhørende studien. Koden ble primært utviklet som et arbeidsverktøy og en prototype, og studiens resultater er derfor ikke inkludert i repositoriet.

- Ordlisteangrep: Prototypkode som utfører passordangrep mot Briar
- Ressurser: Felles kode og konfigurasjon som nyttes i øvrige kataloger
- Situasjoner: Datasett og kode for å utføre 7 situasjoner med sending av meldinger i ulike Briar-funksjoner
- TuringLab: Konfigurering og administrasjon av Android-enheter og ssh-forwarding av AVD-porter

`.sh` er iht. skriptpekeren laget for `zsh-shell` (standard Shell på Mac OS X) og `.py` er laget for `Python 3.11.5`

## Filstruktur
```
BriarResearchTools/
├── ordlisteangrep/
│   ├── injiser-passord.js
│   ├── ordliste-angrep.py
│   ├── relevante-resultater-ordlisteangrep.py
│   ├── samle-datasett.py
│   ├── verifiser-passord.py
├── ressurser/
│   ├── briar_verktøy.py
│   ├── bt_liveonthree.sh
│   ├── custom_formatter.py
│   ├── felles.sh
│   └── hjelpe_funksjoner.py
├── situasjoner/
│   ├── datasett/
│   │   ├── datasett_en.csv
│   │   ├── datasett_en_med_uuids.csv
│   │   └── meldinger/
│   │       ├── en/
│   ├── lokallagring/
│   │   ├── analyser-lokallagring.py
│   │   ├── diff.py
│   │   └── relevante-resultater-lokallagring.py
│   ├── nettverkstrafikk/
│       ├── hent-pakkedumper.sh
│       ├── sammenstill-resultater.py
│       └── slett-pakkedumper.sh
├── turinglab/
│   ├── enheter/
│   │   ├── Makefile-briar.mk
│   │   ├── Makefile-felles.mk
│   │   ├── Makefile-frida.mk
│   │   ├── konfigurer-briar.sh
│   │   └── konfigurer-enhet.sh
│   └── infrastruktur/
│       ├── styr-avder.sh
│       ├── styr-ssh-forwarding.sh
│       └── stopp-alle_emulatorer.bat
└── README.md
```