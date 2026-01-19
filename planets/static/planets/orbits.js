// Obtener posiciones desde Django y covertirlos en objeto usable para javascript
// .parse convierte el string en objeto
// .textContent devuelve el texto dentro del html
const positions = JSON.parse(document.getElementById('positions-data').textContent);

/* esto da como resultado

positions = {
  earth: { radius: 300, angle: 1.57 },
  mars: { radius: 350, angle: 0.9 }
}

*/

// declaramos el centro del lienzo SVG
const center = 1600 / 2;

//llamamos a la API para pedir informacion y si da error devolvemos null para que no la lie
//si try funciona devuelve el texto convertido a objeto y si falla va a catch y devuelve null
function safeParseJson(text) {
    try {
        return JSON.parse(text);
    } catch {
        return null;
    }
}

// si el  id es por ejemplo mars, devuelve Mars y si es null devuelve Planet
// "sun" → "Sun", "" → "Planet"
// id.slice(1) devuelve el String desde el segundo caracter (el 0 cuenta jeje)
function titleFromId(id) {
    if (!id) return 'Planet';
    return id.charAt(0).toUpperCase() + id.slice(1);
}


// bloque para que la ejecucion de todo el codigo se retrase hasta que el html este cargado
// estructura de window.addEventListener (type,listener,options(options es opcional))
// Cuando el DOMContentLoaded este listo se ejecuta el listener, en este caso todo el script
// () => {} funcion flecha
window.addEventListener('DOMContentLoaded', () => {

    //constante para orden de los planetas
    const planetOrder = ['mercury','venus','earth','mars','jupiter','saturn','uranus','neptune'];

    // const para botones clicables, empezando en el sol y seguido por la const planetOrder
    // ... desempaqueta los elementos de un array dentro de otro array
    const clickableBodies = ['sun', ...planetOrder];


    // orbitEls contiene los elementos de .orbit
    const orbitEls = document.querySelectorAll('.orbit');

    // cont radiusMap = {} crea un objeto vacio para guardar radios por planeta
    const radiusMap = {};

    // p(planeta), i (indice)
    // bucle, la constante orbitEl cambia cada vuelta por el planeta del array en orden (orbitsEls[i])
    planetOrder.forEach((p, i) => {
        const orbitEl = orbitEls[i];

        //Aseguramos que los planetas coincidan con la orbita
        if (orbitEl && orbitEl.getAttribute('r')) radiusMap[p] = parseFloat(orbitEl.getAttribute('r'));

        //si no hay planeta la orbita sale igual porque si, no se, chatgpt me dijo que pusiera esto aqui 
        else if (positions[p] && positions[p].radius) radiusMap[p] = positions[p].radius;
    });


    // informacion de los planetas en el pop up
    const modalOverlay = document.getElementById('planet-modal-overlay');
    const modal = document.getElementById('planet-modal');
    const modalTitle = document.getElementById('planet-modal-title');
    const modalBody = document.getElementById('planet-modal-body');
    const modalClose = document.getElementById('planet-modal-close');

    const planetInfoEl = document.getElementById('planet-info-data');
    // Optional user notes per planet (editable in HTML)
    const planetInfo = planetInfoEl ? (safeParseJson(planetInfoEl.textContent) || {}) : {};

    const dateInput = document.getElementById('date');

    function formatNumber(n, digits = 2) {
        if (n === null || n === undefined) return '—';
        const x = Number(n);
        if (Number.isNaN(x)) return '—';
        return x.toFixed(digits);
    }

    function formatMaybeInt(n) {
        if (n === null || n === undefined) return '—';
        const x = Number(n);
        if (Number.isNaN(x)) return '—';
        return String(Math.round(x));
    }

    function buildPlanetText(apiData, notes) {
        const lines = [];
        const planetKey = (apiData.planet || '').toLowerCase();
        
        // Helper to format a line with label:value coloring
        const labelVal = (label, value) => `<span class="modal-label">${label}:</span> <span class="modal-value">${value}</span>`;
        
        lines.push(labelVal('Day length', `${formatNumber(apiData.day_length_hours, 2)} hours`));
        // Omitir la longitud del año en días terrestres para la Tierra (redundante)
        // y para el Sol (no aplica / no queremos mostrarlo).
        if (planetKey !== 'earth' && planetKey !== 'sun') {
            lines.push(labelVal('Year length', `${formatNumber(apiData.year_length_earth_days, 2)} Earth days`));
        }
        // Para el Sol, ocultar también el "year length" en días locales.
        if (planetKey !== 'sun' && apiData.year_length_local_days !== null && apiData.year_length_local_days !== undefined) {
            lines.push(labelVal('Year length', `${formatNumber(apiData.year_length_local_days, 2)} local days`));
        }
        lines.push(labelVal('Gravity', `${formatNumber(apiData.gravity_ms2, 2)} m/s²`));
        lines.push(labelVal('Mean temperature', `${formatMaybeInt(apiData.mean_temperature_c)} °C`));
        lines.push(labelVal('Atmosphere', apiData.atmosphere || '—'));
        if (apiData.composition) {
            lines.push(labelVal('Composition', apiData.composition));
        }
        // Para el Sol, no mostrar número de lunas.
        if (planetKey !== 'sun') {
            lines.push(labelVal('Moons', apiData.moons ?? '—'));
        }
        lines.push('');

        // Para el Sol, ocultar: orbit progress y day-of-year.
        if (planetKey !== 'sun') {
            lines.push(labelVal(`Orbit progress on ${noWrap(apiData.date)}`, `${(Number(apiData.year_progress) * 100).toFixed(1)}%`));
            // Omitir "Day of year" en escala de días terrestres para la Tierra (redundante)
            if (planetKey !== 'earth') {
                lines.push(labelVal('Day of year (Earth-day scale)', `${apiData.day_of_year_earth_days} / ${formatNumber(apiData.year_length_earth_days, 0)}`));
            }
            if (apiData.day_of_year_local_days !== null && apiData.day_of_year_local_days !== undefined) {
                lines.push(labelVal('Day of year (local-day scale)', `${apiData.day_of_year_local_days} / ${formatNumber(apiData.year_length_local_days, 0)}`));
            }
        }
        const notesText = String(notes ?? '').trim();
        const isPlaceholderNotes = /^write your notes\b/i.test(notesText);
        if (notesText && !isPlaceholderNotes) {
            lines.push('');
            lines.push(`<span class="modal-label">Notes:</span>`);
            lines.push(`<span class="modal-value">${escapeHtml(notesText)}</span>`);
        }
        return lines.join('\n');
    }

    // Escape text for safe HTML insertion
    function escapeHtml(s) {
        return String(s || '').replace(/[&<>"']/g, (c) => {
            return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c];
        });
    }

    function noWrap(value) {
        return `<span class="no-wrap">${escapeHtml(value)}</span>`;
    }

    // Get a usable image src for a planet: prefer the existing SVG image element's
    // href/xlink:href attribute; fallback to the static path.
    function getPlanetImageSrc(planetId) {
        try {
            const el = document.getElementById(planetId);
            if (el) {
                return el.getAttribute('href') || el.getAttribute('xlink:href') || el.getAttribute('src') || (`/static/planets/gifs/${planetId}.gif`);
            }
        } catch (e) {
            // ignore
        }
        return `/static/planets/gifs/${planetId}.gif`;
    }

    function positionModalNearPoint(point) {
        if (!modal) return;
        const margin = 12;
        const offset = 14;

        // Ensure we can measure it
        modal.style.visibility = 'hidden';
        modal.style.left = `${Math.round(margin)}px`;
        modal.style.top = `${Math.round(margin)}px`;

        requestAnimationFrame(() => {
            const rect = modal.getBoundingClientRect();
            const w = rect.width || 320;
            const h = rect.height || 180;

            const spaceRight = window.innerWidth - margin - (point.x + offset);
            const spaceLeft = (point.x - offset) - margin;
            const spaceBelow = window.innerHeight - margin - (point.y + offset);
            const spaceAbove = (point.y - offset) - margin;

            // Prefer placing to the right/bottom, but flip when there isn't room.
            let left = point.x + offset;
            if (spaceRight < w && spaceLeft > spaceRight) {
                left = point.x - offset - w;
            }

            let top = point.y + offset;
            if (spaceBelow < h && spaceAbove > spaceBelow) {
                top = point.y - offset - h;
            }

            left = Math.min(Math.max(margin, left), window.innerWidth - margin - w);
            top = Math.min(Math.max(margin, top), window.innerHeight - margin - h);

            modal.style.left = `${Math.round(left)}px`;
            modal.style.top = `${Math.round(top)}px`;
            modal.style.visibility = 'visible';
        });
    }

    async function openPlanetModal(planetId, point) {
        if (!modalOverlay || !modalTitle || !modalBody) return;
        const info = planetInfo[planetId] || {};
        const title = info.title || titleFromId(planetId);
        modalTitle.textContent = title;
        modalBody.textContent = 'Loading...';
        modalOverlay.hidden = false;
        if (point) positionModalNearPoint(point);
        if (modalClose) modalClose.focus();
        document.addEventListener('keydown', escCloseHandler);

        const selected = dateInput && dateInput.value ? dateInput.value : '';
        const url = `/api/planet-info/?planet=${encodeURIComponent(planetId)}&date=${encodeURIComponent(selected)}`;
        try {
            const res = await fetch(url, { headers: { 'Accept': 'application/json' } });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            if (data && data.error) throw new Error(data.error);
            const notes = info.notes || '';

            let text = buildPlanetText(data, notes);

            // Prepare planet image info for later rendering in the modal
            const imgSrc = getPlanetImageSrc(planetId);
            // Use Jupiter's SVG width as base but DOUBLE it for the popup image
            // so the modal image is larger while SVG orbit images remain unchanged.
            let imgWidth = 90;
            try {
                const jupEl = document.getElementById('jupiter');
                if (jupEl) {
                    const base = parseFloat(jupEl.getAttribute('width')) || imgWidth;
                    imgWidth = base * 2;
                } else {
                    const srcEl = document.getElementById(planetId);
                    const base = srcEl ? (parseFloat(srcEl.getAttribute('width')) || imgWidth) : imgWidth;
                    imgWidth = base * 2;
                }
            } catch (e) {
                // ignore
            }
            const imgHtml = `<img src="${escapeHtml(imgSrc)}" alt="${escapeHtml(title)}" style="width:${Math.round(imgWidth)}px;height:auto;border-radius:8px;flex:0 0 auto">`;

            // Extra info for the Sun: show ONLY the next predicted storm time.
            if (planetId === 'sun') {
                try {
                    const swUrl = `/api/space-weather/?date=${encodeURIComponent(selected)}`;
                    const swRes = await fetch(swUrl, { headers: { 'Accept': 'application/json' } });
                    if (swRes.ok) {
                        const sw = await swRes.json();
                        const nextStorm = sw.next_predicted_geomagnetic_storm_utc || '—';
                        text += `\n\n<span class="modal-label">Next predicted solar storm (UTC):</span> <span class="modal-value">${noWrap(nextStorm)}</span>`;
                    }
                } catch {
                    // ignore, we keep the base Sun info
                }
            }

            // Render modal with image + text (text contains HTML for label/value colors)
            modalBody.innerHTML = `<div style="display:flex;align-items:flex-start;gap:12px">${imgHtml}<pre style="margin:0;white-space:pre-wrap;font-family:inherit">${text}</pre></div>`;

            // Content can change modal size; reposition to avoid clipping.
            if (point) requestAnimationFrame(() => positionModalNearPoint(point));
        } catch (err) {
            modalBody.textContent = `Could not load data. ${String(err && err.message ? err.message : err)}`;
        }
    }

    function closePlanetModal() {
        if (!modalOverlay) return;
        modalOverlay.hidden = true;
        document.removeEventListener('keydown', escCloseHandler);
    }

    function escCloseHandler(e) {
        if (e.key === 'Escape') closePlanetModal();
    }

    if (modalClose) modalClose.addEventListener('click', closePlanetModal);
    if (modalOverlay) {
        modalOverlay.addEventListener('click', (e) => {
            // Close when clicking outside the window
            if (e.target === modalOverlay) closePlanetModal();
        });
    }
    if (modal) {
        modal.addEventListener('click', (e) => e.stopPropagation());
    }

    // Posicionar planetas en el SVG (reutilizable para updates sin recargar)
    function applyPositions(posMap) {
        if (!posMap) return;
        for (let planet in posMap) {
            const el = document.getElementById(planet);
            if (!el) continue;

            const pos = posMap[planet];
            const r = (radiusMap[planet] !== undefined) ? radiusMap[planet] : pos.radius;
            const cx = center + r * Math.cos(pos.angle);
            const cy = center - r * Math.sin(pos.angle);

            // Support both <circle> (cx/cy) and <image> (x/y)
            const tag = (el.tagName || '').toLowerCase();
            if (tag === 'image') {
                const w = parseFloat(el.getAttribute('width')) || 24;
                const h = parseFloat(el.getAttribute('height')) || 24;
                el.setAttribute('x', cx - (w / 2));
                el.setAttribute('y', cy - (h / 2));
            } else {
                el.setAttribute('cx', cx);
                el.setAttribute('cy', cy);
            }
        }
    }

    // initial placement from server-rendered JSON
    applyPositions(positions);

    // === Cambiar fecha SIN recargar (fetch a /api/orbit-positions/) ===
    const dateForm = document.getElementById('date-form');
    let lastRequestToken = 0;

    function setUrlDateParam(dateStr, push = true) {
        try {
            const url = new URL(window.location.href);
            if (dateStr) url.searchParams.set('date', dateStr);
            if (push) history.pushState({ date: dateStr }, '', url);
            else history.replaceState({ date: dateStr }, '', url);
        } catch {
            // ignore
        }
    }

    async function updateOrbitsForDate(dateStr, opts = {}) {
        const options = { pushHistory: true, ...opts };
        if (!dateStr) return;
        const token = ++lastRequestToken;

        try {
            const url = `/api/orbit-positions/?date=${encodeURIComponent(dateStr)}`;
            const res = await fetch(url, { headers: { 'Accept': 'application/json' } });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            if (data && data.error) throw new Error(data.error);
            if (token !== lastRequestToken) return; // respuesta vieja

            const normalized = data.date || dateStr;
            if (dateInput) dateInput.value = normalized;
            applyPositions(data.positions || {});

            // update moon panel
            try { updateMoonPanel(new Date(normalized)); } catch (err) {}

            if (options.pushHistory) setUrlDateParam(normalized, true);
            else setUrlDateParam(normalized, false);
        } catch (err) {
            // Fallback a recarga completa si algo falla
            if (dateForm) {
                dateForm.submit();
            } else {
                setUrlDateParam(dateStr, true);
                window.location.reload();
            }
        }
    }
    
    // Planet tooltip that follows cursor
    const tooltip = document.getElementById('planet-tooltip');
    if (tooltip) {
        // IMPORTANT: the solar system is inside a transformed container.
        // A transformed ancestor can make `position: fixed` behave like `absolute`.
        // Move the tooltip to <body> so clientX/clientY map correctly to the viewport.
        if (tooltip.parentElement !== document.body) {
            document.body.appendChild(tooltip);
        }

        const planetsWithNames = document.querySelectorAll('.solar-system image[data-name]');
        planetsWithNames.forEach((planet) => {
            planet.addEventListener('mouseenter', (e) => {
                tooltip.textContent = planet.getAttribute('data-name');
                tooltip.classList.add('visible');
            });
            
            planet.addEventListener('mousemove', (e) => {
                // Cerca del puntero, pero sin taparlo
                tooltip.style.left = (e.clientX + 25) + 'px';
                tooltip.style.top = (e.clientY + 25) + 'px';
            });
            
            planet.addEventListener('mouseleave', () => {
                tooltip.classList.remove('visible');
            });
        });
    }

    // Register clicks on planets (only the expected ones)
    clickableBodies.forEach((planetId) => {
        const el = document.getElementById(planetId);
        if (!el) return;
        // accesibilidad básica
        el.setAttribute('tabindex', '0');
        el.setAttribute('role', 'button');
        el.setAttribute('aria-label', `View information about ${titleFromId(planetId)}`);

        el.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            openPlanetModal(planetId, { x: e.clientX, y: e.clientY });
        });
        el.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                const r = el.getBoundingClientRect();
                openPlanetModal(planetId, { x: r.right, y: r.top });
            }
        });
    });

    // Generar cinturón de asteroides entre Marte y Júpiter
    function generateAsteroidBelt(count = 250, gap = 40) {
        const beltGroup = document.getElementById('asteroid-belt');
        if (!beltGroup) return;
        while (beltGroup.firstChild) beltGroup.removeChild(beltGroup.firstChild);

        // Prefer fixed orbit radii from SVG so belt is independent of the date
        const orbitEls = document.querySelectorAll('.orbit');
        let marsR = null, jupiterR = null;
        if (orbitEls && orbitEls.length >= 5) {
            // order: mercury, venus, earth, mars, jupiter, ... (0-based)
            marsR = parseFloat(orbitEls[3].getAttribute('r'));
            jupiterR = parseFloat(orbitEls[4].getAttribute('r'));
        }
        // fallback to fixed radii if SVG not present. Avoid using `positions` here
        // because `positions` changes with the selected date and would make the
        // belt move between reloads. Prefer SVG orbit radii; otherwise use
        // stable defaults.
        if (!marsR || !jupiterR) {
            const defaultMarsR = 288;
            const defaultJupiterR = 360;
            marsR = marsR || defaultMarsR;
            jupiterR = jupiterR || defaultJupiterR;
        }

        // Increase separation between belt and planet orbits.
        // `extraPadding` widens the gap beyond the caller-provided `gap`.
        const extraPadding = 30; // px of additional separation
        const effectiveGap = gap + extraPadding;
        let minR = Math.min(marsR, jupiterR) + effectiveGap;
        let maxR = Math.max(marsR, jupiterR) - effectiveGap;
        if (minR >= maxR) {
            const fallbackGap = Math.max(10, Math.floor(effectiveGap / 2));
            minR = Math.min(marsR, jupiterR) + fallbackGap;
            maxR = Math.max(marsR, jupiterR) - fallbackGap;
        }

        // Deterministic placement using index-based sequence (golden ratio spacing)
        // This avoids any use of Math.random() or time-varying data so positions
        // remain identical between reloads and date changes.
        const SVG_NS = 'http://www.w3.org/2000/svg';
        const phi = 0.618033988749895; // 1/phi
        function fract(x) { return x - Math.floor(x); }
        for (let i = 0; i < count; i++) {
            // angle spaced by irrational multiplier to avoid clustering
            const angle = fract(i * phi) * Math.PI * 2;
            // radius distributed across band; add a small deterministic jitter
            const bandPos = i / count;
            const baseR = minR + bandPos * Math.max(0, (maxR - minR));
            const jitter = (fract(Math.sin(i * 12.9898) * 43758.5453) - 0.5) * 8; // +/-4px
            const r = Math.max(minR, Math.min(maxR, baseR + jitter));
            const cx = center + r * Math.cos(angle);
            const cy = center - r * Math.sin(angle);
            const dot = document.createElementNS(SVG_NS, 'circle');
            dot.setAttribute('cx', cx);
            dot.setAttribute('cy', cy);
            const rr = 0.8 + fract(Math.cos(i * 7.123) * 10000) * 1.8; // size 0.8-2.6
            dot.setAttribute('r', rr);
            dot.setAttribute('fill', '#9e9e9e');
            dot.setAttribute('opacity', '0.95');
            beltGroup.appendChild(dot);
        }
    }

    generateAsteroidBelt(250, 40);

    // Button to set today's date
    const todayBtn = document.getElementById('today-btn');
    const calendarBtn = document.getElementById('calendar-btn');
    const customPicker = document.getElementById('custom-datepicker');

    if (todayBtn && dateInput) {
        todayBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const today = new Date().toISOString().split('T')[0];
            dateInput.value = today;
            // update moon panel immediately, then submit
            try { updateMoonPanel(new Date(today)); } catch (err) {}
            updateOrbitsForDate(today);
        });
    }

    function formatDateYMD(d) {
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const dd = String(d.getDate()).padStart(2, '0');
        return `${d.getFullYear()}-${mm}-${dd}`;
    }

    function renderDatepicker(monthDate) {
        const year = monthDate.getFullYear();
        const month = monthDate.getMonth();
        const first = new Date(year, month, 1);
        const daysInMonth = new Date(year, month + 1, 0).getDate();

        const monthNames = ['January','February','March','April','May','June','July','August','September','October','November','December'];

        let html = `
          <div class="dp-header">
            <button type="button" class="dp-nav-btn" data-action="prev">◀</button>
            <div class="dp-title">${monthNames[month]} ${year}</div>
            <button type="button" class="dp-nav-btn" data-action="next">▶</button>
          </div>
          <div class="dp-weekdays"><div>M</div><div>T</div><div>W</div><div>T</div><div>F</div><div>S</div><div>S</div></div>
          <div class="dp-grid">
        `;

        const firstWeekday = (first.getDay() + 6) % 7;
        for (let i = 0; i < firstWeekday; i++) html += `<div></div>`;

        for (let d = 1; d <= daysInMonth; d++) {
            const cur = new Date(year, month, d);
            const isToday = dateInput.value === formatDateYMD(cur);
            html += `<button type="button" class="dp-day" data-day="${d}" ${isToday? 'aria-current="date"':''}>${d}</button>`;
        }

        html += `</div>`;
        customPicker.innerHTML = html;

        // nav buttons: change month
        customPicker.querySelectorAll('.dp-nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const action = btn.getAttribute('data-action');
                const newMonthDate = new Date(year, month + (action === 'next' ? 1 : -1), 1);
                renderDatepicker(newMonthDate);
            });
        });

        customPicker.querySelectorAll('.dp-day').forEach(btn => {
            btn.addEventListener('click', () => {
                const day = Number(btn.getAttribute('data-day'));
                const chosen = new Date(year, month, day);
                const chosenStr = formatDateYMD(chosen);
                dateInput.value = chosenStr;
                hideDatepicker();
                // update moon panel immediately so user sees phase before navigation
                try { updateMoonPanel(chosen); } catch (err) {}
                updateOrbitsForDate(chosenStr);
            });
        });
    }

    function showDatepicker() {
        if (!customPicker) return;
        const base = dateInput && dateInput.value ? new Date(dateInput.value) : new Date();
        renderDatepicker(base);
        customPicker.classList.add('open');
        customPicker.setAttribute('aria-hidden', 'false');
        try { if (typeof placeMoonPanel === 'function') placeMoonPanel(); } catch (e) {}
        document.addEventListener('click', outsideClickHandler);
    }

    function hideDatepicker() {
        if (!customPicker) return;
        customPicker.classList.remove('open');
        customPicker.setAttribute('aria-hidden', 'true');
        try { if (typeof placeMoonPanel === 'function') placeMoonPanel(); } catch (e) {}
        document.removeEventListener('click', outsideClickHandler);
    }

    function outsideClickHandler(e) {
        if (!customPicker) return;
        if (customPicker.contains(e.target) || (calendarBtn && calendarBtn.contains(e.target)) || (dateInput && dateInput.contains(e.target))) return;
        hideDatepicker();
    }

    if (calendarBtn) {
        calendarBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (customPicker && customPicker.classList.contains('open')) hideDatepicker(); else showDatepicker();
        });
    }

    // --- Moon phase helper functions ---
    function _julianDate(d) {
        return d.getTime() / 86400000 + 2440587.5;
    }

    function moonAgeDays(date) {
        // approximate using known new moon reference (2000-01-06 18:14 UTC)
        const ref = new Date(Date.UTC(2000, 0, 6, 18, 14, 0));
        const synodic = 29.53058867; // days
        const diff = Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()) - ref.getTime();
        const days = diff / 86400000;
        const age = (days % synodic + synodic) % synodic; // 0..synodic
        return age;
    }

    function moonPhaseNameAndFile(date) {
        const age = moonAgeDays(date);
        // boundaries for 8 phases (approx)
        if (age < 1.84566) return { name: 'New Moon', file: 'new_moon.png' };
        if (age < 5.53699) return { name: 'Waxing Crescent', file: 'waxig_crescent.png' };
        if (age < 9.22831) return { name: 'First Quarter', file: 'first_quarter.png' };
        if (age < 12.91963) return { name: 'Waxing Gibbous', file: 'waxing_gibbous.png' };
        if (age < 16.61096) return { name: 'Full Moon', file: 'full_moon.png' };
        if (age < 20.30228) return { name: 'Waning Gibbous', file: 'waning_gibbous.png' };
        if (age < 23.99361) return { name: 'Last Quarter', file: 'last_quarter.png' };
        if (age < 27.68493) return { name: 'Waning Crescent', file: 'waning_crescent.png' };
        return { name: 'New Moon', file: 'new_moon.png' };
    }

    function updateMoonPanel(date) {
        if (!date) return;
        const el = document.getElementById('moon-phase-img');
        const label = document.getElementById('moon-phase-label');
        if (!el) return;
        const d = (date instanceof Date) ? date : new Date(date);
        if (isNaN(d.getTime())) return;
        const info = moonPhaseNameAndFile(d);
        el.src = `/static/planets/imgs/moon/${info.file}`;
        el.alt = info.name;
        if (label) label.textContent = info.name;
    }

    // initialize moon panel from current input value or today
    try {
        const initial = dateInput && dateInput.value ? new Date(dateInput.value) : new Date();
        updateMoonPanel(initial);
        // position the moon panel under the date panel (to the right of the solar system)
        function placeMoonPanel() {
            const panel = document.getElementById('moon-panel');
            const datePanel = document.querySelector('.date-control-panel');
            if (!panel || !datePanel) return;
            const rect = datePanel.getBoundingClientRect();
            // place just below date panel and centered horizontally relative to it
            panel.style.position = 'absolute';
            const panelW = panel.offsetWidth || panel.getBoundingClientRect().width || 200;
            const left = rect.left + window.scrollX + Math.round((rect.width - panelW) / 2);
            // nudge panel slightly left so it's a bit offset from perfect center
            const nudgeLeft = -30; // pixels, negative moves left
            panel.style.left = (left + nudgeLeft) + 'px';
            panel.style.top = (rect.bottom + window.scrollY + 20) + 'px';
        }
        placeMoonPanel();
        window.addEventListener('resize', placeMoonPanel);
        window.addEventListener('scroll', placeMoonPanel);
    } catch (err) {}

    function normalizeAndValidateDate() {
        if (!dateInput) return false;
        const v = dateInput.value.trim();
        if (!v) return false;
        // Try to parse user input into a Date
        const parsed = new Date(v);
        if (isNaN(parsed.getTime())) {
            return false;
        }
        dateInput.value = formatDateYMD(parsed);
        return true;
    }

    if (dateInput) {
        dateInput.addEventListener('change', () => {
            if (normalizeAndValidateDate()) {
                updateOrbitsForDate(dateInput.value);
            } else {
                // leave value for user to correct
            }
        });
        if (dateForm) {
            dateForm.addEventListener('submit', (e) => {
                e.preventDefault();
                if (!normalizeAndValidateDate()) {
                    alert('Invalid date. Use YYYY-MM-DD or a recognizable date.');
                    return;
                }
                updateOrbitsForDate(dateInput.value);
            });
        }
    }

    // Botones de navegación de fecha: anterior / hoy / siguiente
    const prevBtn = document.getElementById('prev-day-btn');
    const nextBtn = document.getElementById('next-day-btn');

    function changeDateBy(days) {
        if (!dateInput) return;
        const base = dateInput.value ? new Date(dateInput.value) : new Date();
        base.setDate(base.getDate() + days);
        const next = base.toISOString().split('T')[0];
        dateInput.value = next;
        updateOrbitsForDate(next);
    }

    if (prevBtn) prevBtn.addEventListener('click', (e) => { e.preventDefault(); changeDateBy(-1); });
    if (nextBtn) nextBtn.addEventListener('click', (e) => { e.preventDefault(); changeDateBy(1); });

    // back/forward: actualizar planetas según la URL
    window.addEventListener('popstate', () => {
        try {
            const url = new URL(window.location.href);
            const d = url.searchParams.get('date');
            if (d && dateInput) {
                dateInput.value = d;
                if (normalizeAndValidateDate()) {
                    updateOrbitsForDate(dateInput.value, { pushHistory: false });
                }
            }
        } catch {
            // ignore
        }
    });
});
