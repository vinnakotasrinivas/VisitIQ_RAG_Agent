# T02 - Sample data generator

**Goal**: production-like Hyderabad documents in all four formats, plus files that exercise every rejection path.

## Files
- `scripts/generate_sample_docs.py`
- Output: `sample_data/valid/*`, `sample_data/invalid/*`

## Content
| File | Content |
|------|---------|
| `hyderabad_visitor_guide.pdf` (3 pages) | Overview, areas, best season, food, shopping, getting around, emergency numbers |
| `heritage_sites_guide.pdf` (3 pages) | Charminar, Golconda Fort, Qutb Shahi Tombs, Chowmahalla Palace: history, hours, tickets, tips |
| `safety_etiquette_advisory.pdf` (2 pages) | Scams, night travel, women travellers, dress code at religious sites, photography, emergency numbers |
| `visitor_faqs.txt` | Visas, SIM cards, currency, ATMs, weather, tipping |
| `getting_around.txt` | Metro lines, autos, ride apps, buses, airport, last-mile to Golconda |
| `attractions.csv` (~60 rows) | Real closed days (e.g. Salar Jung Museum and Chowmahalla closed Friday, Zoo closed Monday) |
| `restaurants.csv` (~150 rows) | Cuisine, area, price band, veg options, rating, hours |
| `events_calendar.xlsx` (~3 months from the generation date) | Weekly recurring and one-off events with `day_of_week` and `recurring` |
| `transport_timetable.xlsx` | Sheets: metro_lines, metro_fares, airport_bus, day_passes, local_fares |
| Invalid | `sample.jpg`, `archive.zip`, `fake_pdf.pdf`, `pharmacy_invoice.pdf`, `bengaluru_guide.pdf`, `empty.csv`, `injection_doc.txt` |

The oversize test file (20 MB) is created by `python scripts/generate_sample_docs.py --oversize` so it is not committed.

## Verify
```powershell
python scripts/generate_sample_docs.py
Get-ChildItem sample_data -Recurse
```

## Done when
- [ ] 9 valid files and 7 invalid files exist.
- [ ] The CSVs have fewer than 500 rows and the PDFs have 2-3 pages.
