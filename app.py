from flask import Flask, render_template, jsonify, request
import pandas as pd
import requests, re
from pathlib import Path
from datetime import datetime, timezone
from functools import lru_cache

app = Flask(__name__)
BASE = Path(__file__).parent
PROFILE_FILE = BASE / 'data' / 'rocket_profiles.csv'
FALLBACK_FILE = BASE / 'data' / 'launches.csv'
LL2 = 'https://ll.thespacedevs.com/2.3.0/launches/upcoming/'


def profiles():
    return pd.read_csv(PROFILE_FILE).where(pd.notnull, None).to_dict('records')


def match_profile(rocket_name):
    name = (rocket_name or '').lower()
    matches = [p for p in profiles() if str(p['match_key']).lower() in name]
    return max(matches, key=lambda p: len(str(p['match_key']))) if matches else None


def configuration(profile, rocket_name):
    """Adjust mass/motor count when the live rocket name encodes a configuration."""
    if not profile:
        return None
    p = dict(profile)
    n = (rocket_name or '').lower()
    if 'vulcan' in n:
        m = re.search(r'vc([0246])', n)
        count = int(m.group(1)) if m else 6
        p['solid_propellant_t'] = round(count * 47.853, 3)
        p['solid_motors'] = f'{count} × GEM 63XL' if count else 'No GEM 63XL boosters'
    elif 'h3-' in n:
        m = re.search(r'h3-(\d)(\d)', n)
        count = int(m.group(2)) if m else 4
        p['solid_propellant_t'] = round(count * 66.8, 3)
        p['solid_motors'] = f'{count} × SRB-3' if count else 'No SRB-3 boosters'
    elif 'ariane 64' in n:
        p['solid_propellant_t'] = 624.0; p['solid_motors'] = '4 × P160C/P120-family boosters'
    elif 'ariane 62' in n:
        p['solid_propellant_t'] = 312.0; p['solid_motors'] = '2 × P160C/P120-family boosters'
    return p


def emissions(profile):
    if not profile:
        return {k: None for k in ['tracked_propellant_t','aluminum_t','alumina_t','submicron_alumina_t','black_carbon_t']}
    mass = float(profile.get('solid_propellant_t') or profile.get('tracked_propellant_t') or 0)
    al_frac = float(profile.get('aluminum_fraction') or 0)
    alumina_factor = float(profile.get('alumina_factor_kg_per_kg') or 0)
    bc_factor = float(profile.get('bc_factor_kg_per_kg') or 0)
    return {
        'tracked_propellant_t': round(mass, 3),
        'aluminum_t': round(mass * al_frac, 3),
        'alumina_t': round(mass * alumina_factor, 3),
        'submicron_alumina_t': round(mass * float(profile.get('submicron_alumina_factor') or 0), 3),
        'black_carbon_t': round(mass * bc_factor, 3),
    }


def parse_launch(x):
    cfg = (((x.get('rocket') or {}).get('configuration')) or {})
    rocket = cfg.get('full_name') or cfg.get('name') or 'Unknown rocket'
    profile = configuration(match_profile(rocket), rocket)
    pad = x.get('pad') or {}; loc = pad.get('location') or {}; lsp = x.get('launch_service_provider') or {}
    mission = x.get('mission') or {}; status = x.get('status') or {}; calc = emissions(profile)
    alumina_candidate = bool(profile and calc['alumina_t'] and calc['alumina_t'] > 0)
    bc_candidate = bool(profile and calc['black_carbon_t'] and calc['black_carbon_t'] > 0)
    return {
        'id': x.get('id'), 'mission': x.get('name') or mission.get('name') or 'Unnamed launch',
        'net': x.get('net'), 'window_start': x.get('window_start'), 'window_end': x.get('window_end'),
        'status': status.get('name') or status.get('abbrev') or 'Unknown', 'rocket': rocket,
        'operator': lsp.get('name') or (cfg.get('manufacturer') or {}).get('name') or 'Unknown',
        'site': pad.get('name') or 'Unknown pad', 'location': loc.get('name') or 'Unknown location',
        'lat': pad.get('latitude'), 'lon': pad.get('longitude'), 'mission_type': mission.get('type'),
        'orbit': (mission.get('orbit') or {}).get('name'), 'description': mission.get('description'),
        'profile_matched': bool(profile), 'alumina_candidate': alumina_candidate, 'bc_candidate': bc_candidate,
        'pollution_candidate': alumina_candidate or bc_candidate,
        'motors': profile.get('solid_motors') if profile else 'No curated emissions profile yet',
        'propellant_type': profile.get('propellant_type') if profile else 'Unclassified',
        'aluminum_fraction_pct': round(float(profile.get('aluminum_fraction') or 0)*100, 1) if profile else None,
        'aluminum_basis': profile.get('aluminum_basis') if profile else 'Not modeled',
        'confidence': profile.get('confidence') if profile else 'Unclassified',
        'chemistry_note': profile.get('chemistry_note') if profile else 'Live launch found, but no curated propulsion-emissions profile has been matched yet.',
        'source_label': profile.get('source_label') if profile else None, 'source_url': profile.get('source_url') if profile else None,
        **calc,
    }


@lru_cache(maxsize=1)
def fetch_live_cached():
    params = {'limit': 100, 'mode': 'normal', 'ordering': 'net', 'format': 'json'}
    r = requests.get(LL2, params=params, timeout=18, headers={'User-Agent':'AluminaWatch/3.0 educational research'})
    r.raise_for_status()
    return {'launches':[parse_launch(x) for x in r.json().get('results',[])], 'fetched_at':datetime.now(timezone.utc).isoformat(), 'source':'Launch Library 2 (live)', 'error':None}


def live_data(force=False):
    if force: fetch_live_cached.cache_clear()
    try: return fetch_live_cached()
    except Exception as e:
        # Keep the app usable offline; fallback rows are parsed from the bundled research table.
        df = pd.read_csv(FALLBACK_FILE)
        rows=[]
        for _,x in df.iterrows():
            p=configuration(match_profile(str(x.rocket)),str(x.rocket)); calc=emissions(p)
            rows.append({'id':None,'mission':x.mission,'net':x.date_status,'status':'Offline fallback','rocket':x.rocket,'operator':x.operator,
              'site':x.site,'location':x.country,'lat':x.lat,'lon':x.lon,'mission_type':None,'orbit':None,'description':None,
              'profile_matched':True,'alumina_candidate':bool(calc['alumina_t']),'bc_candidate':bool(calc['black_carbon_t']),
              'pollution_candidate':bool(calc['alumina_t'] or calc['black_carbon_t']),'motors':p.get('solid_motors'),'propellant_type':p.get('propellant_type'),
              'aluminum_fraction_pct':round(float(p.get('aluminum_fraction') or 0)*100,1),'aluminum_basis':p.get('aluminum_basis'),'confidence':p.get('confidence'),
              'chemistry_note':p.get('chemistry_note'),'source_label':p.get('source_label'),'source_url':p.get('source_url'),**calc})
        return {'launches':rows,'fetched_at':datetime.now(timezone.utc).isoformat(),'source':'Local fallback dataset','error':str(e)}

@app.route('/')
def index():
    data=live_data(); return render_template('index.html',launches=data['launches'],meta=data)
@app.route('/api/launches')
def api_launches(): return jsonify(live_data(force=request.args.get('refresh')=='1'))
@app.route('/api/profiles')
def api_profiles(): return jsonify(profiles())
@app.route('/health')
def health(): return jsonify({'ok':True,'version':'3.1'})

if __name__=='__main__': app.run(debug=True)
