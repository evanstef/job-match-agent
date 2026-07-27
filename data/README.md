# data/

Berisi contoh data mentah hasil panggilan API pihak ketiga, dipakai untuk
mengembangkan pipeline secara offline tanpa menghabiskan kuota API.

Isinya **sengaja tidak ikut ke repo** (`data/*.json` ada di `.gitignore`) karena
itu data milik penyedia sumber, bukan milik project ini.

Cara membuat ulang:

```bash
curl -s -X POST "https://id.jooble.org/api/$JOOBLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"keywords":"developer","location":"Jakarta","ResultOnPage":"100"}' \
  > data/jooble-sample-developer-jakarta.json
```
