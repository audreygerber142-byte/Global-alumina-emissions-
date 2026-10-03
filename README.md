# Alumina Watch Live V3.1

# Alumina Watch V3

Live Flask research dashboard that combines Launch Library 2 upcoming-launch data with a curated rocket-propulsion emissions model.

## V3 changes
- No `NaN` aluminum boxes: every matched solid profile has a numerical aluminum estimate.
- Evidence labels distinguish documented fractions from engineering estimates.
- Tracks aluminum, total alumina, submicron alumina, and black carbon.
- RP-1/LOX vehicles such as Falcon 9 can be tracked for black carbon even though their alumina model is zero.
- Live filters/search and a shorter default 12-card dashboard.
- Configuration-aware Vulcan and H3 booster counts when encoded in the live rocket name.

## Scientific model
Brown et al. (2024), *Worldwide Rocket Launch Emissions 2019*, gives HTPB-solid emission indices of 380 g/kg total alumina and 20 g/kg black carbon; it discusses 10–120 g/kg for submicron alumina and a likely 60 g/kg value. It also reports 20 g/kg black carbon for RP-1/LOX. These are emission-model estimates, not direct measurements of a future individual launch.

Aluminum fractions are documented where possible (e.g. GEM 63XL 19% from Northrop Grumman). Where a current motor formulation is not publicly specified, V3 uses a central engineering estimate and labels it explicitly in the UI and CSV.

## Run on Windows / VS Code
If you already have V2's `.venv`, you can use it with V3. Otherwise:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

## Libraries
- Flask — web server/routes
- requests — Launch Library 2 HTTP calls
- pandas — curated CSV database
- Plotly — browser map and emissions chart (loaded in page)
- NumPy / SciPy — installed for next-stage uncertainty/statistical analysis
- Skyfield / SGP4 — installed for future post-launch orbit tracking
- Folium — installed for alternative geospatial work

## Main sources
- Launch Library 2: https://ll.thespacedevs.com/2.3.0/launches/upcoming/
- Brown et al. 2024: https://doi.org/10.1029/2024EA003668
- Northrop Grumman Propulsion Products Catalog: https://cdn.northropgrumman.com/-/media/wp-content/uploads/NG-Propulsion-Products-Catalog.pdf
- NASA solid rocket booster reference: https://www.nasa.gov/reference/the-space-shuttle/
