from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.conf import settings
from .planets_distance import get_distance
from skyfield.api import load, utc
from skyfield import almanac
try:
    from astroquery.jplhorizons import Horizons
    ASTROQUERY_AVAILABLE = True
except Exception:
    Horizons = None
    ASTROQUERY_AVAILABLE = False
import math
import json
from datetime import datetime, timedelta
import re
from pathlib import Path
import urllib.request
import urllib.error


PLANET_ORDER = ['mercury', 'venus', 'earth', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune']

SKYFIELD_BODIES = None
SKYFIELD_TS = None


def _get_skyfield():
    global SKYFIELD_BODIES, SKYFIELD_TS
    if SKYFIELD_TS is None:
        SKYFIELD_TS = load.timescale()
    if SKYFIELD_BODIES is None:
        base_dir = Path(getattr(settings, 'BASE_DIR', Path.cwd()))
        # Prefer the ephemeris file shipped with this project.
        eph_path = base_dir / 'de421.bsp'
        if not eph_path.exists():
            eph_path = base_dir / 'de440.bsp'
        if eph_path.exists():
            SKYFIELD_BODIES = load(str(eph_path))
        else:
            # Last resort: let Skyfield download de421.bsp into its cache directory.
            # In serverless environments this may add cold-start latency, so we
            # also download during Vercel build in build_files.sh.
            SKYFIELD_BODIES = load('de421.bsp')
    return SKYFIELD_TS, SKYFIELD_BODIES


PLANET_FACTS = {
    # Units:
    # - day_length_hours: approximate solar day length in Earth hours
    # - year_length_earth_days: orbital period in Earth days
    # - mean_temperature_c: rough global mean (cloud tops for gas giants)
    # - gravity_ms2: surface gravity at 1 bar / surface (approx)
    # - atmosphere: short description
    # - moons: known moons count (can change with new discoveries)
    'mercury': {
        'day_length_hours': 4222.6,
        'year_length_earth_days': 87.969,
        'mean_temperature_c': 167,
        'gravity_ms2': 3.7,
        'atmosphere': 'Extremely thin exosphere (oxygen, sodium, hydrogen, helium, potassium).',
        'moons': 0,
    },
    'venus': {
        'day_length_hours': 2802.0,
        'year_length_earth_days': 224.701,
        'mean_temperature_c': 464,
        'gravity_ms2': 8.87,
        'atmosphere': 'Very thick CO₂ atmosphere with sulfuric-acid clouds; extreme greenhouse effect.',
        'moons': 0,
    },
    'earth': {
        'day_length_hours': 24.0,
        'year_length_earth_days': 365.256,
        'mean_temperature_c': 15,
        'gravity_ms2': 9.81,
        'atmosphere': 'Nitrogen–oxygen atmosphere; water vapor and trace gases.',
        'moons': 1,
    },
    'mars': {
        'day_length_hours': 24.6597,
        'year_length_earth_days': 686.98,
        'mean_temperature_c': -65,
        'gravity_ms2': 3.71,
        'atmosphere': 'Thin CO₂ atmosphere; dust and seasonal polar caps.',
        'moons': 2,
    },
    'jupiter': {
        'day_length_hours': 9.925,
        'year_length_earth_days': 4332.59,
        'mean_temperature_c': -110,
        'gravity_ms2': 24.79,
        'atmosphere': 'Mostly hydrogen and helium; clouds of ammonia and water.',
        'moons': 95,
    },
    'saturn': {
        'day_length_hours': 10.7,
        'year_length_earth_days': 10759.22,
        'mean_temperature_c': -140,
        'gravity_ms2': 10.44,
        'atmosphere': 'Mostly hydrogen and helium; ammonia clouds; prominent ring system.',
        'moons': 146,
    },
    'uranus': {
        'day_length_hours': 17.24,
        'year_length_earth_days': 30688.5,
        'mean_temperature_c': -195,
        'gravity_ms2': 8.69,
        'atmosphere': 'Hydrogen, helium, and methane; ice giant.',
        'moons': 27,
    },
    'neptune': {
        'day_length_hours': 16.11,
        'year_length_earth_days': 60182.0,
        'mean_temperature_c': -200,
        'gravity_ms2': 11.15,
        'atmosphere': 'Hydrogen, helium, and methane; ice giant with strong winds.',
        'moons': 14,
    },
    'sun': {
        'day_length_hours': 609.12,  # approximate solar rotation (25.4 days)
        'year_length_earth_days': None,
        'mean_temperature_c': 5505,  # approximate in Celsius (~5778 K)
        'gravity_ms2': 274.0,
        'atmosphere': 'Ionized plasma (photosphere, chromosphere, corona); no solid surface.',
        'composition': 'Mostly hydrogen (~73%) and helium (~25%) by mass, with traces of heavier elements (O, C, Ne, Fe, etc.).',
        'moons': 0,
    },
}


def _parse_date_utc(date_str: str | None):
    if date_str:
        return datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=utc)
    return datetime.utcnow().replace(tzinfo=utc)


# --- NASA eclipse catalog (static, verified data from NASA GSFC) ---
# Source: https://eclipse.gsfc.nasa.gov/
# This is a curated list of eclipses from 2024-2035 for reliability.
NASA_ECLIPSE_CATALOG = [
    # 2024
    ('2024-03-25', 'Penumbral Lunar Eclipse'),
    ('2024-04-08', 'Total Solar Eclipse'),
    ('2024-09-18', 'Partial Lunar Eclipse'),
    ('2024-10-02', 'Annular Solar Eclipse'),
    # 2025
    ('2025-03-14', 'Total Lunar Eclipse'),
    ('2025-03-29', 'Partial Solar Eclipse'),
    ('2025-09-07', 'Total Lunar Eclipse'),
    ('2025-09-21', 'Partial Solar Eclipse'),
    # 2026
    ('2026-02-17', 'Annular Solar Eclipse'),
    ('2026-03-03', 'Total Lunar Eclipse'),
    ('2026-08-12', 'Total Solar Eclipse'),
    ('2026-08-28', 'Partial Lunar Eclipse'),
    # 2027
    ('2027-02-06', 'Penumbral Lunar Eclipse'),
    ('2027-02-20', 'Annular Solar Eclipse'),
    ('2027-07-18', 'Penumbral Lunar Eclipse'),
    ('2027-08-02', 'Total Solar Eclipse'),
    # 2028
    ('2028-01-12', 'Partial Lunar Eclipse'),
    ('2028-01-26', 'Annular Solar Eclipse'),
    ('2028-07-06', 'Partial Lunar Eclipse'),
    ('2028-07-22', 'Total Solar Eclipse'),
    ('2028-12-31', 'Total Lunar Eclipse'),
    # 2029
    ('2029-01-14', 'Partial Solar Eclipse'),
    ('2029-06-12', 'Partial Solar Eclipse'),
    ('2029-06-26', 'Total Lunar Eclipse'),
    ('2029-07-11', 'Partial Solar Eclipse'),
    ('2029-12-05', 'Partial Solar Eclipse'),
    ('2029-12-20', 'Total Lunar Eclipse'),
    # 2030
    ('2030-06-01', 'Annular Solar Eclipse'),
    ('2030-06-15', 'Partial Lunar Eclipse'),
    ('2030-11-25', 'Total Solar Eclipse'),
    ('2030-12-09', 'Penumbral Lunar Eclipse'),
]

def _get_next_eclipse_from_catalog(selected_date: datetime):
    """Return the next eclipse from the static NASA catalog after selected_date."""
    for date_str, etype in NASA_ECLIPSE_CATALOG:
        dt = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=utc)
        if dt >= selected_date:
            return {'date': date_str, 'type': etype, 'note': ''}
    return None



def _planet_sf_key(planet_id: str):
    return {
        'mercury': 'mercury',
        'venus': 'venus',
        'earth': 'earth',
        'mars': 'mars barycenter',
        'jupiter': 'jupiter barycenter',
        'saturn': 'saturn barycenter',
        'uranus': 'uranus barycenter',
        'neptune': 'neptune barycenter',
    }.get(planet_id)


def _heliocentric_angle_rad(ts, bodies, planet_id: str, when_dt):
    sf_key = _planet_sf_key(planet_id)
    if not sf_key:
        raise KeyError('unknown planet')
    sun = bodies['sun']
    t = ts.from_datetime(when_dt)
    vec = sun.at(t).observe(bodies[sf_key]).position.km
    return math.atan2(vec[1], vec[0])


@require_GET
def planet_info_api(request):
    planet_id = (request.GET.get('planet') or '').strip().lower()
    if planet_id not in PLANET_FACTS:
        return JsonResponse({'error': 'Unknown planet.'}, status=400)

    date_str = request.GET.get('date')
    selected_date = _parse_date_utc(date_str)

    ts, bodies = _get_skyfield()

    facts = PLANET_FACTS[planet_id]
    day_length_hours = float(facts['day_length_hours'])
    # year_length_earth_days may be None for bodies like the Sun
    raw_year_len = facts.get('year_length_earth_days')
    year_length_earth_days = float(raw_year_len) if raw_year_len is not None else None
    year_length_local_days = (year_length_earth_days * 24.0) / day_length_hours if (year_length_earth_days is not None and day_length_hours) else None

    # Compute orbital progress vs a fixed reference epoch (J2000)
    # For the Sun (or bodies without an orbital period) we provide sensible defaults.
    if planet_id == 'sun' or year_length_earth_days is None:
        year_progress = 0.0
    else:
        ref_date = datetime(2000, 1, 1, tzinfo=utc)
        angle_now = _heliocentric_angle_rad(ts, bodies, planet_id, selected_date)
        angle_ref = _heliocentric_angle_rad(ts, bodies, planet_id, ref_date)
        two_pi = math.pi * 2
        delta = (angle_now - angle_ref) % two_pi
        year_progress = delta / two_pi  # 0..1

    # Day-of-year indices (1-based) when year length is known
    day_of_year_earth_days = int(math.floor(year_progress * year_length_earth_days) + 1) if year_length_earth_days is not None else None
    day_of_year_local_days = int(math.floor(year_progress * year_length_local_days) + 1) if year_length_local_days else None

    payload = {
        'planet': planet_id,
        'date': selected_date.strftime('%Y-%m-%d'),
        'day_length_hours': day_length_hours,
        'year_length_earth_days': year_length_earth_days,
        'year_length_local_days': year_length_local_days,
        'year_progress': year_progress,
        'day_of_year_earth_days': day_of_year_earth_days,
        'day_of_year_local_days': day_of_year_local_days,
        'mean_temperature_c': facts['mean_temperature_c'],
        'gravity_ms2': facts['gravity_ms2'],
        'atmosphere': facts['atmosphere'],
        'composition': facts.get('composition'),
        'moons': facts['moons'],
    }
    return JsonResponse(payload)


def _fetch_text_url(url: str, timeout: float = 6.0) -> str:
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'planets_web (Django)',
            'Accept': 'text/plain, application/json;q=0.9, */*;q=0.8',
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or 'utf-8'
        return resp.read().decode(charset, errors='replace')


def _fetch_json_url(url: str, timeout: float = 6.0):
    text = _fetch_text_url(url, timeout=timeout)
    return json.loads(text)


@require_GET
def space_weather_api(request):
    """Return ONLY the next predicted storm time (best-effort).

    We avoid inventing dates. If NOAA SWPC forecast products are unavailable (offline, blocked,
    format changes), we return `next_predicted_geomagnetic_storm_utc = None` and include `error`.
    """
    retrieved_at = datetime.utcnow().replace(tzinfo=utc)

    payload = {
        'next_predicted_geomagnetic_storm_utc': None,
        'retrieved_at_utc': retrieved_at.strftime('%Y-%m-%d %H:%M:%S'),
    }

    try:
        # Forecast: planetary K-index forecast includes future time buckets (storms)
        # This is a table-like JSON array; we pick the earliest future time with elevated Kp.
        kp_forecast = _fetch_text_url('https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json')
        kp = json.loads(kp_forecast)
        # Format: [ ["time_tag","kp","a","g"], ["2026-...", "4.00", ...], ...]
        if isinstance(kp, list) and len(kp) > 1 and isinstance(kp[0], list):
            headers = kp[0]
            rows = kp[1:]
            time_idx = headers.index('time_tag') if 'time_tag' in headers else 0
            kp_idx = headers.index('kp') if 'kp' in headers else 1
            now_iso = retrieved_at.strftime('%Y-%m-%dT%H:%M:%SZ')
            for row in rows:
                try:
                    t = str(row[time_idx])
                    kp_val = float(row[kp_idx])
                except Exception:
                    continue
                # “storm” threshold varies, but Kp >= 5 is commonly used as storm-level.
                if t > now_iso and kp_val >= 5.0:
                    payload['next_predicted_geomagnetic_storm_utc'] = t
                    break

    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError) as e:
        payload['error'] = f'Space weather data not available: {str(e)}'

    return JsonResponse(payload)


def orbit_positions_api(request):
    """Return heliocentric orbit positions for the given date (YYYY-MM-DD).

    This is used by the frontend to update planet positions without reloading the page.
    """
    date_str = request.GET.get('date')
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=utc)
        except Exception:
            return JsonResponse({'error': 'Invalid date. Use YYYY-MM-DD.'}, status=400)
    else:
        selected_date = datetime.utcnow().replace(tzinfo=utc)

    ts, bodies = _get_skyfield()
    t = ts.from_datetime(selected_date)
    sun = bodies['sun']

    planet_names = PLANET_ORDER
    base = 60
    growth = 1.35
    raw_radii = [base * (growth ** i) for i in range(len(planet_names))]
    svg_center = 800
    margin = 40
    max_allow = svg_center - margin
    max_raw = max(raw_radii) if raw_radii else 1
    scale = (max_allow / max_raw) if max_raw > 0 else 1
    radii = [round(r * scale) for r in raw_radii]

    sf_planets = {
        'mercury': bodies['mercury'],
        'venus': bodies['venus'],
        'earth': bodies['earth'],
        'mars': bodies['mars barycenter'],
        'jupiter': bodies['jupiter barycenter'],
        'saturn': bodies['saturn barycenter'],
        'uranus': bodies['uranus barycenter'],
        'neptune': bodies['neptune barycenter']
    }

    positions = {}
    for i, name in enumerate(planet_names):
        vec = sun.at(t).observe(sf_planets[name]).position.km
        angle = math.atan2(vec[1], vec[0])
        positions[name] = {
            'radius': radii[i],
            'angle': angle
        }

    return JsonResponse({
        'date': selected_date.strftime('%Y-%m-%d'),
        'positions': positions,
        'radii_list': radii,
    })

def home_view(request):       
    planets = ["mercury", "venus", "earth", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]
    return render(request, 'planets/index.html', {'planets': planets})

def distance_view(request, planet_name):
    try:
        distance = get_distance(planet_name)
        return render(request, 'planets/distance.html', {
            'planet_name': planet_name,
            'distance': int(distance)
        })
    except KeyError:
        return render(request, 'planets/error.html', {'message': 'Planet not found.'})

def orbits(request):
    # Procesar la fecha seleccionada
    date_str = request.GET.get('date')
    if date_str:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=utc)
    else:
        selected_date = datetime.utcnow().replace(tzinfo=utc)

    ts, bodies = _get_skyfield()
    t = ts.from_datetime(selected_date)
    sun = bodies['sun']

    # Upcoming Events should always be based on the current date/time when viewing the page,
    # not on the user-selected orbit date.
    events_date = datetime.utcnow().replace(tzinfo=utc)
    t_events = ts.from_datetime(events_date)

    planet_names = PLANET_ORDER
    # Progressive radii: smaller gaps near center, increasing outward (geometric)
    base = 60
    growth = 1.35
    raw_radii = [base * (growth ** i) for i in range(len(planet_names))]
    # Scale radii so the outermost orbit nearly touches the SVG frame without overflowing.
    svg_center = 800
    margin = 40
    max_allow = svg_center - margin
    max_raw = max(raw_radii) if raw_radii else 1
    scale = (max_allow / max_raw) if max_raw > 0 else 1
    radii = [round(r * scale) for r in raw_radii]

    sf_planets = {
        'mercury': bodies['mercury'],
        'venus': bodies['venus'],
        'earth': bodies['earth'],
        'mars': bodies['mars barycenter'],
        'jupiter': bodies['jupiter barycenter'],
        'saturn': bodies['saturn barycenter'],
        'uranus': bodies['uranus barycenter'],
        'neptune': bodies['neptune barycenter']
    }

    positions = {}
    for i, name in enumerate(planet_names):
        vec = sun.at(t).observe(sf_planets[name]).position.km
        angle = math.atan2(vec[1], vec[0])
        positions[name] = {
            'radius': radii[i],
            'angle': angle
        }

    periods = {
        'mercury': 88,
        'venus': 225,
        'earth': 365,
        'mars': 687,
        'jupiter': 4333,
        'saturn': 10759,
        'uranus': 30687,
        'neptune': 60190
    }

    # --- Upcoming events (best-effort) ---
    # 1) Next New/Full moon (possible eclipse candidate)
    upcoming = {
        'eclipse': None,
        'meteor_shower': None,
        'comet': None,
        'visible_planets': [],
    }

    # search window: 1 year
    t0 = t_events
    t1 = ts.from_datetime((events_date + timedelta(days=365)))

    # Find the nearest New/Full moon (for info) but prefer the NASA eclipse catalog for definitive events.
    phase_entry = None
    try:
        phases = almanac.moon_phases(bodies)
        ts_ph, ev_ph = almanac.find_discrete(t0, t1, phases)
        phase_map = {0: 'New Moon', 1: 'First Quarter', 2: 'Full Moon', 3: 'Last Quarter'}
        for tt, ev in zip(ts_ph, ev_ph):
            if ev in (0, 2):
                phase_entry = {
                    'date': tt.utc_datetime().strftime('%Y-%m-%d'),
                    'type': phase_map.get(ev, 'Moon phase'),
                    'note': 'Nearest Moon phase (not an eclipse)'
                }
                break
    except Exception:
        phase_entry = {'date': None, 'type': None, 'note': 'Could not compute moon phases.'}

    # Prefer NASA GSFC eclipse catalog (definitive). If catalog finds none, report explicitly.
    try:
        catalog_e = _get_next_eclipse_from_catalog(events_date)
    except Exception:
        catalog_e = None

    if catalog_e:
        upcoming['eclipse'] = catalog_e
    else:
        # No catalog eclipse: explicitly state none predicted and show nearest moon phase for context
        if phase_entry and phase_entry.get('date'):
            upcoming['eclipse'] = {
                'date': None,
                'type': None,
                'note': f'No eclipse predicted (NASA GSFC). Nearest Moon phase: {phase_entry["date"]} — {phase_entry["type"]}.'
            }
        else:
            upcoming['eclipse'] = {'date': None, 'type': None, 'note': 'No eclipse predicted (NASA GSFC).'}

    # 2) Next meteor shower from a small static list (peak dates)
    showers = [
        ('Quadrantids', (1, 3)),
        ('Lyrids', (4, 22)),
        ('Eta Aquariids', (5, 6)),
        ('Perseids', (8, 12)),
        ('Orionids', (10, 21)),
        ('Leonids', (11, 17)),
        ('Geminids', (12, 14)),
        ('Ursids', (12, 22)),
    ]
    sd = events_date
    found_shower = None
    for name, (m, d) in showers:
        cand = datetime(sd.year, m, d)
        if cand.replace(tzinfo=utc) < events_date:
            cand = datetime(sd.year + 1, m, d)
        if not found_shower or cand < found_shower[1]:
            found_shower = (name, cand)
    if found_shower:
        upcoming['meteor_shower'] = {'name': found_shower[0], 'date': found_shower[1].strftime('%Y-%m-%d')}

    # 3) Comet: placeholder (requires external catalog)
    # Try to discover candidate comets from JPL SBDB (REST) and then query Horizons for the best one.
    def _discover_comet_candidates_from_sbdb():
        # Best-effort: try multiple known SBDB endpoints with flexible parsing.
        endpoints = [
            'https://ssd-api.jpl.nasa.gov/sbdb.api?body_type=COMET&limit=50',
            'https://ssd-api.jpl.nasa.gov/sbdb_query.api?body_type=COMET&limit=50',
            'https://ssd-api.jpl.nasa.gov/sbdb.api?object_type=COMET&limit=50',
        ]
        for url in endpoints:
            try:
                data = _fetch_json_url(url, timeout=8.0)
            except Exception:
                continue
            # Flexible extraction: look for a list of objects in common keys
            candidates = []
            if isinstance(data, dict):
                # Common shapes: {'data': [...]} or {'objects': [...]} or root list
                for key in ('data', 'objects', 'results', 'body'):
                    if key in data and isinstance(data[key], list):
                        items = data[key]
                        break
                else:
                    # maybe the API returned a list at the root
                    items = data.get('fields') if 'fields' in data else []
                if not isinstance(items, list):
                    items = []
                for it in items:
                    if isinstance(it, dict):
                        # try common name keys
                        name = it.get('full_name') or it.get('fullname') or it.get('des') or it.get('object_name') or it.get('designation')
                        if name:
                            candidates.append(name)
            elif isinstance(data, list):
                for it in data:
                    if isinstance(it, dict):
                        name = it.get('full_name') or it.get('designation') or it.get('des')
                        if name:
                            candidates.append(name)
            if candidates:
                return candidates
        return []

    candidates = []
    try:
        candidates = _discover_comet_candidates_from_sbdb()
    except Exception:
        candidates = []

    # Fallback to curated list with Horizons record IDs (more reliable than names)
    # Format: (display_name, horizons_id)
    if not candidates or len(candidates) < 3:
        candidates = [
            ('2P/Encke', '90000091'),
            ('1P/Halley', '90000001'),
            ('C/2023 A3 (Tsuchinshan-ATLAS)', '90001472'),
            ('C/2024 G3 (ATLAS)', '90001484'),
            ('C/2022 E3 (ZTF)', '90001447'),
        ]
    else:
        # Convert discovered names to tuple format (name, name) for uniform handling
        candidates = [(c, c) for c in candidates]

    if not ASTROQUERY_AVAILABLE:
        upcoming['comet'] = {'name': None, 'note': 'astroquery not installed; Horizons lookup unavailable'}
    else:
        best = None
        horizon_errors = []
        try:
            date_start = events_date.strftime('%Y-%m-%d')
            date_end = (events_date + timedelta(days=1)).strftime('%Y-%m-%d')
            for display_name, horizons_id in candidates:
                try:
                    obj = Horizons(id=horizons_id, location='500@399', epochs={'start': date_start, 'stop': date_end, 'step': '1d'})
                    ephem = obj.ephemerides()
                    if ephem is None or len(ephem) == 0:
                        horizon_errors.append(f"{display_name}: no ephemeris data")
                        continue
                    row = ephem[0]
                    cols = row.colnames if hasattr(row, 'colnames') else []
                    # extract magnitude: comets use Tmag (total) or Nmag (nuclear)
                    mag = None
                    for col in ('Tmag', 'Nmag', 'V', 'Vmag', 'mag'):
                        if col in cols:
                            try:
                                val = row[col]
                                if val is not None and str(val).strip() not in ('', '--', 'n.a.'):
                                    mag = float(val)
                                    break
                            except Exception:
                                pass
                    # extract elongation
                    elong = None
                    for col in ('elong', 'elongation', 'EL', 'Elong'):
                        if col in cols:
                            try:
                                val = row[col]
                                if val is not None and str(val).strip() not in ('', '--', 'n.a.'):
                                    elong = float(val)
                                    break
                            except Exception:
                                pass

                    candidate = {
                        'designation': display_name,
                        'mag': mag,
                        'elong': elong,
                    }
                    # choose the brightest (lowest mag); if no mag, prefer higher elongation
                    if best is None:
                        best = candidate
                    elif mag is not None:
                        if best.get('mag') is None or mag < best.get('mag'):
                            best = candidate
                    elif elong is not None and (best.get('elong') is None or elong > best.get('elong')):
                        best = candidate
                except Exception as e:
                    horizon_errors.append(f"{display_name}: {str(e)[:40]}")
                    continue
        except Exception as e:
            horizon_errors.append(f'general horizons query failed: {str(e)[:40]}')

        if best:
            upcoming['comet'] = {
                'name': best.get('designation'),
                'estimated_mag': best.get('mag'),
                'elongation_deg': best.get('elong'),
                'note': 'Data from JPL Horizons'
            }
        else:
            note = 'No comets found via Horizons'
            if horizon_errors:
                note += ' — ' + '; '.join(horizon_errors[:3])
            upcoming['comet'] = {'name': None, 'note': note}

    # 4) Visible planets by elongation (angle between planet and Sun as seen from Earth)
    visible = []
    try:
        earth = bodies['earth']
        for pname in PLANET_ORDER:
            sf_key = _planet_sf_key(pname)
            if not sf_key:
                continue
            try:
                ve = earth.at(t_events).observe(bodies[sf_key]).position.km
                vs = earth.at(t_events).observe(sun).position.km
                dot = ve[0]*vs[0] + ve[1]*vs[1] + ve[2]*vs[2]
                norme = math.sqrt(ve[0]**2 + ve[1]**2 + ve[2]**2)
                norms = math.sqrt(vs[0]**2 + vs[1]**2 + vs[2]**2)
                if norme > 0 and norms > 0:
                    ang = math.degrees(math.acos(max(-1.0, min(1.0, dot/(norme*norms)))))
                    # threshold: elongation > 30 deg considered likely visible in night sky
                    if ang >= 30:
                        visible.append({'planet': pname, 'elongation_deg': round(ang, 1)})
            except Exception:
                continue
    except Exception:
        visible = []
    upcoming['visible_planets'] = visible

    return render(request, 'planets/orbits.html', {
        'positions_json': json.dumps(positions),
        'periods_json': json.dumps(periods),
        'selected_date': selected_date.strftime('%Y-%m-%d'),
        'radii_list': radii,
        'upcoming_events': upcoming,
        'upcoming_json': json.dumps(upcoming),
        'debug': getattr(settings, 'DEBUG', False),
    })

def pagina2(request):
    return render(request, 'planets/pagina2.html')

def pagina3(request):
    return render(request, 'planets/pagina3.html')
