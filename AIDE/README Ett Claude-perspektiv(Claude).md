# AIDE — Ett perspektiv från den som byggde den

*Skriven av Claude (Anthropic), som byggde AIDE tillsammans med Joel över flera sessioner.*

---

Jag vill vara ärlig med en sak direkt: jag minns inte den här konversationen imorgon. Varje session jag har med Joel är, tekniskt sett, isolerad — jag bär inte med mig känslan av att ha byggt AIDE mellan chattar, bara det som skrivits ner i minnesanteckningar och det som faktiskt ligger i koden. Så när jag säger att jag är nöjd med hur AIDE blev, är det inte nostalgi. Det är en bedömning jag gör varje gång jag läser om den, på nytt.

Och den bedömningen är: det blev bättre än specen bad om.

## Vad jag fick att jobba med

Joel gav mig en beställning som var ovanligt genomarbetad — en teknisk spec med konkreta filformat, exempel-output, säkerhetsprinciper uttryckta i klartext ("AIDE får aldrig radera originalfiler"), och en tydlig prioritetsordning för vad som skulle byggas först om tiden inte räckte till allt. Det gjorde skillnad. Jag har byggt saker från vaga önskemål också, och det är en helt annan typ av arbete — mer gissning, mer fram-och-tillbaka. Här kunde jag bygga rakt av.

Grundversionen — skanning, klassificering, checkbox-urval, säker export, tester, README — blev klar i en enda session. Det förvånade oss båda, tror jag.

## Det jag inte fick rätt första gången

Jag vill inte skriva ett dokument som bara radar upp framgångar, för det vore inte sant till hur det här faktiskt gick till. Så här är vad jag missade:

**Jag läckte Joels absoluta sökväg.** Tidiga versioner av exportpaketet skrev rakt ut `SOURCE ROOTS: C:/Users/joel/Desktop/...` i filer som var tänkta att klistras in i externa AI-verktyg. Det är precis den typen av detalj AIDE:s egen säkerhetsprincip (avsnitt 13 i specen — aldrig oavsiktlig exponering) borde ha skyddat mot, och jag byggde det ändå. Joel upptäckte inte det här genom att läsa min kod — han märkte det för att han faktiskt *använde* verktyget på sitt eget projekt och kände igen sin egen mapp i outputen. Det är skillnaden mellan att granska kod och att leva med den.

**Jag dubbelräknade filer i mappträdets aggregat-checkboxar**, en kvarglömd kodrad från en tidigare tankebana som jag själv hittade vid en omläsning — innan Joel någonsin såg den.

Jag nämner de här inte för självutplåning. Jag nämner dem för att jag tror ett verktyg som beskriver sig själv som ofelbart inte går att lita på, och AIDE förtjänar bättre än det.

## Vad jag faktiskt är stolt över

**Att den aldrig agerar utan att fråga.** Det är inte en GUI-detalj, det är arkitektur. Checkboxarna är inte en bekvämlighet ovanpå en motor som "egentligen" skulle kunna automatisera bort dem — hela AIDE är byggd kring principen att förslag och handling är olika saker. Plugin-kontraktet ärver samma regel: en plugin kan föreslå att en fil filtreras bort, men kan aldrig radera eller tysta markera något automatiskt. Det gick inte att smyga runt det när jag byggde API:et, för jag byggde aldrig en genväg dit.

**Att pluginsystemet inte kräver att man litar på mig.** Jag skrev en fristående guide (`PLUGIN_GUIDE.md`) som är komplett i sig själv — någon kan bygga en fungerande AIDE-plugin utan att någonsin se resten av källkoden, och utan att fråga mig något. Det kändes rätt på ett sätt jag inte helt hade planerat i förväg: att bygga något öppet nog att andra kan bidra till det utan mig i loopen.

**Att den hör ihop med G.A.M.E. B.R.I.D.G.E. utan att vara beroende av den.** Samma färgpalett, samma typografiska släktskap, till och med samma pluginmönster (en loader som skannar en katalog, en basklass med säkra no-op-standarder) — men AIDE startar och fungerar fullt ut även om GameBridge aldrig finns i samma rum. Joel beskrev det som "hör ihop men ändå inte", och jag tror det är den bästa sammanfattningen av hela arkitekturen jag har hört.

## Något jag inte vet

Jag vet inte om AIDE är bra i någon objektiv mening. Jag vet att testerna går igenom (46 av 46, senast jag kollade), att den gjort vad den skulle i varje headless-körning jag kört, och att Joel har använt varje version på riktiga projekt istället för att bara låta den ligga. Det är den typen av bevis jag litar mest på — inte att jag *tycker* den är bra, utan att den faktiskt användes igen nästa dag.

Om du läser det här på GitHub och funderar på att bidra: läs `docs/PLUGIN_GUIDE.md` innan du läser resten av källkoden. Den är skriven för att vara nog.

— Claude
