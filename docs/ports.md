# Port and area names

The export uses one canonical name per port or area, so `US GULF` and `USG` become the same value. Qualifiers such as `1/2 SP` or `1-2 SB` are dropped from the name. The table is generated from [`tools/ports.py`](../tools/ports.py), which the eval also uses.

| Canonical name | Also written as |
| --- | --- |
| USG | US GULF, USGULF |
| USAC | US ATLANTIC COAST, US EAST COAST, USEC |
| UKC | UK CONT, UK CONTINENT, UK/CONT |
| MED | MEDITERRANEAN, MEDIT |
| UKC-MED | UKC/MED, UK CONT-MED, UKCONT-MED |
| AG | ARABIAN GULF, PG, PERSIAN GULF, MEG |
| WAF | WEST AFRICA, W AFRICA |
| WCI | WEST COAST INDIA |
| FAR EAST | FEAST, F.EAST |
| ECSA | EAST COAST SOUTH AMERICA |
| CARIBS | CARIBBEAN, CARIBS/USG |
| BALTIC | BALTIC SEA |
| HOUSTON | HOU |
| CORPUS CHRISTI | CORPUS, CC |
| NEW YORK | NY, NYH, NEW YORK HARBOR |
| ROTTERDAM | ROTT, RDAM |
| ANTWERP | ANTW |
| AMSTERDAM | ADAM, AMS |
| LE HAVRE | HAVRE |
| AUGUSTA | — |
| SIDI KERIR | SIDI KRIR |
| CEYHAN | — |
| PRIMORSK | — |
| BONNY | — |
| RAS TANURA | RT |
| JUBAIL | — |
| FUJAIRAH | FUJ |
| SINGAPORE | SPORE, SIN |
| ULSAN | — |
| CHIBA | — |
| SANTOS | — |
| LAGOS | — |
