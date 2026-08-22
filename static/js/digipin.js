// Main entry: run after DOM is loaded
document.addEventListener('DOMContentLoaded', function(){
	// DOM element references
	const fileInput = document.getElementById('file')
	const processBtn = document.getElementById('process')
	const downloadErrorsBtn = document.getElementById('download-errors')
	const progressBarOuter = document.getElementById('progress')
	const progressBarInner = progressBarOuter ? progressBarOuter.querySelector('div') : null
	const percentText = document.getElementById('percentText')
	const logBox = document.getElementById('log')

	// Single DIGIPIN generation UI
	const singleLat = document.getElementById('single_lat')
	const singleLon = document.getElementById('single_lon')
	const singleGen = document.getElementById('single_gen')
	const singleOut = document.getElementById('single_out')
	const singleCopy = document.getElementById('single_copy')
	const singleSymbol = document.getElementById('single_symbol')

	// DIGIPIN reverse decode UI
	const reverseIn = document.getElementById('reverse_in')
	const reverseBtn = document.getElementById('reverse_btn')
	const reverseOut = document.getElementById('reverse_out')
	const reverseCopy = document.getElementById('reverse_copy')

	let lastErrorsCSV = null // Store latest errors CSV contents for manual download

	// Update progress bar and percent text
	function setProgress(p){
		const pct = Math.max(0, Math.min(100, Math.round(p)))
		if (progressBarInner) progressBarInner.style.width = pct + '%'
		if (percentText) percentText.textContent = pct + '%'
	}

	// Prepend a log message to the log box with timestamp
	function log(msg){
		if (!logBox) return
		const time = (new Date()).toLocaleTimeString()
		logBox.textContent = `[${time}] ${msg}\n` + logBox.textContent
	}

	// Download a blob as a file
	function downloadBlob(filename, contents, type){
		const blob = new Blob([contents], {type: type || 'application/octet-stream'})
		const url = URL.createObjectURL(blob)
		const a = document.createElement('a')
		a.href = url
		a.download = filename
		document.body.appendChild(a)
		a.click()
		setTimeout(() => {
			a.remove()
			URL.revokeObjectURL(url)
		}, 250)
	}

	// Download an ExcelJS workbook (async: ExcelJS serializes via a promise)
	async function downloadWorkbook(workbook, filename){
		const buffer = await workbook.xlsx.writeBuffer()
		downloadBlob(filename, buffer, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
	}

	// Fetch the official DIGIPIN logo once and cache it as a base64 data URL,
	// so it can be embedded (per row) into generated Excel files.
	let digipinLogoBase64 = null
	function loadDigipinLogo(){
		if (digipinLogoBase64) return Promise.resolve(digipinLogoBase64)
		const logoUrl = window.DIGIPIN_LOGO_URL
		if (!logoUrl) return Promise.resolve(null)
		return fetch(logoUrl)
			.then(r => r.blob())
			.then(blob => new Promise((resolve, reject) => {
				const reader = new FileReader()
				reader.onload = () => { digipinLogoBase64 = reader.result; resolve(digipinLogoBase64) }
				reader.onerror = reject
				reader.readAsDataURL(blob)
			}))
			.catch(err => { log('Failed to load DIGIPIN logo: ' + (err && err.message ? err.message : String(err))); return null })
	}

	// Download an array of arrays as CSV
	function downloadCSV(rows, filename){
		const csv = rows.map(r => r.map(c => {
			if (c === null || c === undefined) return ''
			const s = String(c)
			if (s.includes(',') || s.includes('"') || s.includes('\n')) return `"${s.replace(/"/g,'""')}"`
			return s
		}).join(',')).join('\n')
		downloadBlob(filename, csv, 'text/csv;charset=utf-8;')
	}

	// Parse XLSX sheet to array of objects, case-sensitive headers
	function parseSheetToObjects_caseSensitive(sheet){
		const raw = XLSX.utils.sheet_to_json(sheet, {header:1, defval: ''})
		if (raw.length === 0) return {error: 'Empty sheet'}
		const headersRaw = raw[0].map(h => String(h || '').trim())
		const idx = {
			id: headersRaw.indexOf('HouseNo'),
			latitude: headersRaw.indexOf('latitude'),
			longitude: headersRaw.indexOf('longitude'),
			label: headersRaw.indexOf('label')
		}
		if (idx.id === -1 || idx.latitude === -1 || idx.longitude === -1){
			alert('Missing required headers. Required (case-sensitive): HouseNo, latitude, longitude');
			location.reload();
			return {error: 'Missing required headers. Required (case-sensitive): HouseNo, latitude, longitude'};
		}
		const rows = []
		for (let r = 1; r < raw.length; r++){
			const row = raw[r]
			const item = {
				_row: r + 1,
				HouseNo: row[idx.id] !== undefined ? row[idx.id] : '',
				latitude: row[idx.latitude] !== undefined ? row[idx.latitude] : '',
				longitude: row[idx.longitude] !== undefined ? row[idx.longitude] : '',
				label: idx.label !== -1 ? row[idx.label] : ''
			}
			rows.push(item)
		}
		return {rows, headers: headersRaw}
	}

	// Utility: convert number to signed integer with scale
	function toSignedInt(n, scale){
		return Math.round(Number(n) * scale)
	}

	// Utility: convert signed integer back to float
	function fromSignedInt(i, scale){
		return Number(i) / scale
	}

	// Utility: convert integer to base36 string
	function intToBase36(i){
		const sign = i < 0 ? '-' : ''
		const abs = Math.abs(i)
		return sign + abs.toString(36).toUpperCase()
	}

	// Utility: convert base36 string to integer
	function base36ToInt(s){
		if (!s) return 0
		const sign = s[0] === '-' ? -1 : 1
		const body = sign === -1 ? s.slice(1) : s
		return sign * parseInt(body, 36)
	}

	// Utility: pad string with zeros to desired length
	function padGroup(s, len){
		const out = String(s)
		if (out.length >= len) return out
		return '0'.repeat(len - out.length) + out
	}

	// Utility: simple hash for string (FNV-1a, mod 46656)
	function simpleHash(s){
		let h = 2166136261 >>> 0
		for (let i=0;i<s.length;i++){
			h ^= s.charCodeAt(i)
			h = (h * 16777619) >>> 0
		}
		return (h >>> 0) % 46656
	}

	// DIGIPIN Labelling Grid (per INDIAPOST-gov/digipin)
	const DIGIPIN_GRID = [
		['F','C','9','8'],
		['J','3','2','7'],
		['K','4','5','6'],
		['L','M','P','T']
	]
	const DIGIPIN_BOUNDS = { minLat: 2.5, maxLat: 38.5, minLon: 63.5, maxLon: 99.5 }
	const DIGIPIN_CHAR_RE = /^[23456789CJKLMPFT]{10}$/

	// Generate a DIGIPIN code from latitude and longitude.
	// New format (per INDIAPOST-gov/digipin): continuous 10-character string, no separators.
	function generateDigipin(lat, lon) {
		if (typeof lat !== 'number' || typeof lon !== 'number') return ''
		if (lat < DIGIPIN_BOUNDS.minLat || lat > DIGIPIN_BOUNDS.maxLat) return ''
		if (lon < DIGIPIN_BOUNDS.minLon || lon > DIGIPIN_BOUNDS.maxLon) return ''

		let minLat = DIGIPIN_BOUNDS.minLat
		let maxLat = DIGIPIN_BOUNDS.maxLat
		let minLon = DIGIPIN_BOUNDS.minLon
		let maxLon = DIGIPIN_BOUNDS.maxLon

		let digiPin = ''

		for (let level = 1; level <= 10; level++) {
			const latDiv = (maxLat - minLat) / 4
			const lonDiv = (maxLon - minLon) / 4

			let row = 3 - Math.floor((lat - minLat) / latDiv)
			let col = Math.floor((lon - minLon) / lonDiv)

			row = Math.max(0, Math.min(row, 3))
			col = Math.max(0, Math.min(col, 3))

			digiPin += DIGIPIN_GRID[row][col]

			maxLat = minLat + latDiv * (4 - row)
			minLat = minLat + latDiv * (3 - row)

			minLon = minLon + lonDiv * col
			maxLon = minLon + lonDiv
		}

		return digiPin.toUpperCase()
	}

	// Decode DIGIPIN code to latitude/longitude (center of cell)
	function decodeDigipin(vDigiPin) {
		if (typeof vDigiPin !== 'string') return 'Invalid DIGIPIN'
		// tolerate a pasted symbol prefix, legacy dashes, and display-format spaces —
		// keep only characters that are actually part of the DIGIPIN alphabet
		const pin = vDigiPin.trim().toUpperCase().replace(/[^23456789CJKLMPFT]/g, '')
		if (!DIGIPIN_CHAR_RE.test(pin)) return 'Invalid DIGIPIN'

		let minLat = DIGIPIN_BOUNDS.minLat
		let maxLat = DIGIPIN_BOUNDS.maxLat
		let minLng = DIGIPIN_BOUNDS.minLon
		let maxLng = DIGIPIN_BOUNDS.maxLon
		let Lat1 = 0, Lat2 = 0, Lng1 = 0, Lng2 = 0

		for (let i = 0; i < 10; i++) {
			const digipinChar = pin.charAt(i)
			const latDivVal = (maxLat - minLat) / 4
			const lngDivVal = (maxLng - minLng) / 4
			let ri = -1, ci = -1, f = 0

			for (let r = 0; r < 4; r++) {
				for (let c = 0; c < 4; c++) {
					if (DIGIPIN_GRID[r][c] === digipinChar) {
						ri = r; ci = c; f = 1; break
					}
				}
				if (f) break
			}

			if (f === 0) return 'Invalid DIGIPIN'

			Lat1 = maxLat - (latDivVal * (ri + 1))
			Lat2 = maxLat - (latDivVal * ri)
			Lng1 = minLng + (lngDivVal * ci)
			Lng2 = minLng + (lngDivVal * (ci + 1))

			minLat = Lat1
			maxLat = Lat2
			minLng = Lng1
			maxLng = Lng2
		}

		const cLat = (Lat2 + Lat1) / 2
		const cLng = (Lng2 + Lng1) / 2

		return { latitude: Number(cLat.toFixed(6)), longitude: Number(cLng.toFixed(6)) }
	}

	// Show/hide Download Errors button
	function enableDownloadErrors(enabled){
		if (!downloadErrorsBtn) return
		downloadErrorsBtn.style.display = enabled ? '' : 'none'
	}

	// Process workbook: parse, validate, generate DIGIPINs, collect errors
	function processWorkbook_caseSensitive(workbook){
		const sheetName = workbook.SheetNames[0]
		const sheet = workbook.Sheets[sheetName]
		const parsed = parseSheetToObjects_caseSensitive(sheet)
		if (parsed.error){
			log('Error: ' + parsed.error)
			return Promise.reject(parsed.error)
		}
		const rows = parsed.rows
		const errors = []
		const outRows = []
		for (let i=0;i<rows.length;i++){
			const r = rows[i]
			const lat = r.latitude
			const lon = r.longitude
			if (lat === '' || lon === '' || isNaN(Number(lat)) || isNaN(Number(lon))){
				errors.push([r.HouseNo || '', r._row, String(lat), String(lon), 'missing or invalid latitude/longitude'])
				outRows.push([r.HouseNo, '', r.latitude, r.longitude, r.label])
			} else {
				const pin = generateDigipin(Number(lat), Number(lon))
				// if generation failed (empty string), treat as error
				if (!pin) {
					errors.push([r.HouseNo || '', r._row, String(lat), String(lon), 'digipin generation failed (out of range / boundary)'])
					outRows.push([r.HouseNo, '', r.latitude, r.longitude, r.label])
				} else {
					outRows.push([r.HouseNo, pin, r.latitude, r.longitude, r.label])
				}
			}
			const pct = ((i+1) / rows.length) * 100
			setProgress(pct)
		}
		return {outRows, errors}
	}

	// Find duplicate DIGIPINs (with multiple house numbers)
	function computeDuplicatesByDigipin(rows) {
		// rows may be:
		//  - an array of arrays: [HouseNo, digipin, latitude, longitude, label]
		//  - an array of objects: { HouseNo: ..., DIGIPIN: ..., digipin: ... }
		// Return: array of { DIGIPIN: 'X-Y-Z', House_Numbers: '1, 2, 3' }

		if (!Array.isArray(rows) || rows.length === 0) return [];

		const digMap = new Map();

		for (let i = 0; i < rows.length; i++) {
			const r = rows[i];

			let dig = null;
			let house = null;

			// array-row case
			if (Array.isArray(r)) {
				// assume format: [HouseNo, digipin, latitude, longitude, label]
				house = r[0] !== undefined ? String(r[0]).trim() : '';
				dig = r[1] !== undefined ? String(r[1]).trim() : '';
			} else if (typeof r === 'object' && r !== null) {
				// object-row case: try common keys
				house = (r.HouseNo !== undefined) ? String(r.HouseNo).trim()
					  : (r['House Number'] !== undefined) ? String(r['House Number']).trim()
					  : (r.houseNo !== undefined) ? String(r.houseNo).trim()
					  : '';
				dig = (r.DIGIPIN !== undefined) ? String(r.DIGIPIN).trim()
					: (r.digipin !== undefined) ? String(r.digipin).trim()
					: (r.digipinCode !== undefined) ? String(r.digipinCode).trim()
					: '';
			}

			if (!dig) continue; // skip blank / invalid digipin

			if (!digMap.has(dig)) digMap.set(dig, []);
			if (house && house !== '') {
				digMap.get(dig).push(house);
			} else {
				// push a placeholder so we know the digipin exists (but don't add empty house values)
				digMap.get(dig).push(null);
			}
		}

		const duplicates = [];

		for (const [dig, arr] of digMap.entries()) {
			if (arr.length <= 1) continue; // only interested in duplicates

			// filter valid non-empty house numbers
			const houseNums = arr
				.filter(v => v !== null && v !== undefined && String(v).trim() !== '')
				.map(String);

			// dedupe and sort (if any)
			const uniq = Array.from(new Set(houseNums)).sort((a,b) => a.localeCompare(b, undefined, {numeric:true}));

			duplicates.push({
				DIGIPIN: dig,
				House_Numbers: uniq.length ? uniq.join(', ') : '' // empty if no house numbers available
			});
		}

		return duplicates;
	}

	// Build XLSX workbook (via ExcelJS) with output rows and duplicates sheet.
	// A "Symbol" column carries the official DIGIPIN logo image in front of each row's digipin value.
	async function buildOutputWorkbook(outRows, duplicates) {
		const wb = new ExcelJS.Workbook();
		const ws = wb.addWorksheet('digipin');
		ws.columns = [
			{ header: 'HouseNo', key: 'houseNo', width: 14 },
			{ header: 'Symbol', key: 'symbol', width: 6 },
			{ header: 'digipin', key: 'digipin', width: 16 },
			{ header: 'latitude', key: 'latitude', width: 14 },
			{ header: 'longitude', key: 'longitude', width: 14 },
			{ header: 'label', key: 'label', width: 18 }
		];

		const logo = await loadDigipinLogo();
		// wb.addImage() returns an integer id, and 0 is a valid id for the first image
		// registered on the workbook — must check against null, not truthiness.
		const imageId = logo !== null ? wb.addImage({ base64: logo, extension: 'png' }) : null;

		outRows.forEach((r) => {
			const row = ws.addRow({ houseNo: r[0], symbol: '', digipin: r[1], latitude: r[2], longitude: r[3], label: r[4] });
			row.height = 16;
			// only stamp the symbol when a digipin was actually generated for this row
			if (imageId !== null && r[1]) {
				ws.addImage(imageId, { tl: { col: 1, row: row.number - 1 }, ext: { width: 14, height: 14 } });
			}
		});

		// append duplicates sheet if provided
		if (Array.isArray(duplicates) && duplicates.length) {
			const dupWs = wb.addWorksheet('Duplicates');
			dupWs.columns = [
				{ header: 'DIGIPIN', key: 'digipin', width: 16 },
				{ header: 'House_Numbers', key: 'houses', width: 30 }
			];
			duplicates.forEach(d => dupWs.addRow({ digipin: d.DIGIPIN, houses: d.House_Numbers }));
		}

		return wb;
	}

	// Handle file upload and processing
	function handleFileProcess(file){
		if (!file) return
		setProgress(0)
		processBtn.disabled = true
		enableDownloadErrors(false)
		lastErrorsCSV = null
		log('Reading file: ' + file.name)
		const reader = new FileReader()
		reader.onload = async function(e){
			const data = e.target.result
			let wb
			try {
				wb = XLSX.read(data, {type:'array'})
			} catch(err){
				log('Failed to read workbook: ' + (err && err.message ? err.message : String(err)))
				alert('Failed to read workbook: ' + (err && err.message ? err.message : String(err)))
				processBtn.disabled = false
				return
			}

			let result
			try {
				result = processWorkbook_caseSensitive(wb)
				console.log(result)
			} catch(err) {
				log('Processing failed: ' + (err && err.message ? err.message : String(err)))
				alert('Processing failed: ' + (err && err.message ? err.message : String(err)))
				processBtn.disabled = false
				return
			}

			const {outRows, errors} = result
			log(`Processing completed. Total rows: ${outRows.length}, Errors: ${errors.length}`)
			log(errors)
			// If any errors exist -> DO NOT auto-download output workbook
			if (errors && errors.length) {
				// prepare CSV for errors
				const header = ['HouseNo','row','latitude','longitude','error']
				const csvRows = [header].concat(errors)
				// store lastErrorsCSV so downloadErrorsBtn can use it
				lastErrorsCSV = csvRows

				// enable Download Error Report button and attach onclick to download the errors CSV
				enableDownloadErrors(true)
				downloadErrorsBtn.onclick = function(){
					if (!lastErrorsCSV) return
					const fname = `digipin_errors_${Date.now()}.csv`
					downloadCSV(lastErrorsCSV, fname)
					log('Error report downloaded: ' + fname)
				}

				// show an alert popup summarizing errors (user requested)
				const shortMsg = `${errors.length} error(s) found. The updated file will NOT be downloaded. Please download the error report to inspect and fix issues.`
				log(shortMsg)
				alert(shortMsg) // popup requirement

				// Also auto-download the partial output (optional) — per your request we MUST NOT download updated file if errors exist,
				// so we do NOT call downloadWorkbook here. We DO provide error CSV via button.
				setProgress(100)
				processBtn.disabled = false
				return
			}

			// No errors: proceed to compute duplicates by HouseNo and generate workbook
			const duplicates = computeDuplicatesByDigipin(outRows)
			log(`Found ${duplicates.length} duplicate HouseNo entries (with >1 unique DIGIPIN).`)

			const outName = `digipin_${Date.now()}.xlsx`
			try {
				const wbout = await buildOutputWorkbook(outRows, duplicates)
				await downloadWorkbook(wbout, outName)
				log('Processed successfully. Download started: ' + outName)
			} catch (err) {
				log('Failed to download output: ' + (err && err.message ? err.message : String(err)))
				alert('Failed to download output: ' + (err && err.message ? err.message : String(err)))
			}
			setProgress(100)
			processBtn.disabled = false
		}
		reader.onerror = function(){
			log('Failed to read file')
			alert('Failed to read file')
			processBtn.disabled = false
		}
		reader.readAsArrayBuffer(file)
	}

	// Download errors CSV handler (manual fallback)
	function downloadErrorsHandler(){
		// fallback: if lastErrorsCSV is present, download; else show message
		if (!lastErrorsCSV) {
			log('No error report available to download.')
			alert('No error report available to download.')
			return
		}
		const fname = `digipin_errors_${Date.now()}.csv`
		downloadCSV(lastErrorsCSV, fname)
		log('Error report downloaded: ' + fname)
	}

	// Copy text to clipboard, show feedback on button
	function copyTextToClipboard(text, el){
		if (!text) return
		navigator.clipboard && navigator.clipboard.writeText(text).then(() => {
			const prev = el.textContent
			el.textContent = 'Copied'
			setTimeout(()=> el.textContent = prev, 1000)
		}).catch(() => {
			const ta = document.createElement('textarea')
			ta.value = text
			document.body.appendChild(ta)
			ta.select()
			try { document.execCommand('copy') } catch(e){}
			ta.remove()
		})
	}

	// Single DIGIPIN generation button handler
	if (singleGen) singleGen.addEventListener('click', function(){
		const la = singleLat.value
		const lo = singleLon.value
		if (la === '' || lo === '' || isNaN(Number(la)) || isNaN(Number(lo))){
			log('Invalid lat/lon for single generation')
			return
		}
		const pin = generateDigipin(Number(la), Number(lo))
		if (singleOut) singleOut.textContent = pin
		if (singleSymbol) singleSymbol.style.display = pin ? '' : 'none'
		log('Generated DIGIPIN for single input: ' + pin)
	})

	// DIGIPIN reverse decode button handler
	if (reverseBtn) reverseBtn.addEventListener('click', function(){
		const inpin = reverseIn.value.trim()
		if (!inpin){
			log('No DIGIPIN provided for decode')
			return
		}
		const decoded = decodeDigipin(inpin)
		if (!decoded || typeof decoded === 'string'){
			if (reverseOut) reverseOut.textContent = 'Invalid DIGIPIN'
			log('Failed to decode DIGIPIN: ' + inpin)
			return
		}
		if (reverseOut) reverseOut.textContent = `${decoded.latitude} , ${decoded.longitude}`
		log('Decoded DIGIPIN: ' + inpin)
	})

	// Copy buttons for single/reverse output
	if (singleCopy) singleCopy.addEventListener('click', function(){ copyTextToClipboard(singleOut ? singleOut.textContent : '', singleCopy) })
	if (reverseCopy) reverseCopy.addEventListener('click', function(){ copyTextToClipboard(reverseOut ? reverseOut.textContent : '', reverseCopy) })

	// Main process button handler
	if (processBtn) processBtn.addEventListener('click', function(){
		const f = fileInput.files && fileInput.files[0]
		if (!f){
			log('No file selected for processing')
			showSmallPopupAbove(fileInput, 'Select a file first')
			return
		}
		handleFileProcess(f)
	})
	if (downloadErrorsBtn) downloadErrorsBtn.addEventListener('click', downloadErrorsHandler)

	// Log file selection
	if (fileInput) fileInput.addEventListener('change', function(){
		if (fileInput.files && fileInput.files[0]){
			log('Selected file: ' + fileInput.files[0].name)
		}
	})

	setProgress(0)
	log('digipin.js loaded (case-sensitive: HouseNo, latitude, longitude)')
})

// Show a small popup above an element (used for feedback)
function showSmallPopupAbove(el, message) {
	const popup = document.createElement('div')
	popup.textContent = message
	popup.style.position = 'absolute'
	popup.style.background = '#4998cdff'
	popup.style.color = 'white'
	popup.style.padding = '10px 15px'
	popup.style.fontSize = '14px'
	popup.style.borderRadius = '6px'
	popup.style.boxShadow = '0 2px 6px rgba(0,0,0,0.2)'
	popup.style.zIndex = 99999
	popup.style.whiteSpace = 'nowrap'
	popup.style.pointerEvents = 'none'
	popup.style.opacity = '0'
	popup.style.transition = 'opacity .15s ease'

	document.body.appendChild(popup)

	const rect = el.getBoundingClientRect()
	popup.style.left = (rect.left + window.scrollX) + 'px'
	popup.style.top = (rect.top + window.scrollY - 35) + 'px'

	requestAnimationFrame(() => {
		popup.style.opacity = '1'
	})

	setTimeout(() => {
		popup.style.opacity = '0'
		setTimeout(() => popup.remove(), 200)
	}, 1800)
}
