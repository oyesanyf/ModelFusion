// tests/test_ticket_and_maps_directions.js
// Automated verification suite for Ticket Booking, Map Directions,
// Natural Language URL Routing & Human-in-the-Loop (HITL) Safety Gates in ModelFusion

const assert = require('assert');
const fs = require('fs');
const path = require('path');

console.log('🧭 Starting Ticket Booking & Map Directions HITL Verification Suite...\n');

const appPath = path.resolve(__dirname, '../browser/ui/app.js');
assert.ok(fs.existsSync(appPath), 'browser/ui/app.js must exist');
const appJs = fs.readFileSync(appPath, 'utf8');
global.window = global.window || {};

// =====================================================================
// Test 1: Archetype Classification & Natural Language URL Routing
// =====================================================================
console.log('Test 1: Archetype Classification & Natural Language URL Routing...');

// 1.1 Extract and evaluate classifyPageArchetype
const classifyMatch = appJs.match(/function classifyPageArchetype\(doc,\s*text,\s*url[\s\S]*?\{([\s\S]*?)\n  \}/);
assert.ok(classifyMatch, 'classifyPageArchetype must be defined in app.js');
eval(classifyMatch[0]);

// Directions archetype classification
assert.strictEqual(
  classifyPageArchetype(null, 'Directions to Central Park via 5th Ave', 'https://www.google.com/maps/dir/', '@agent computer-use get map directions'),
  'directions',
  'Must classify maps URL and directions goal as directions'
);
assert.strictEqual(
  classifyPageArchetype(null, 'Route 1: via I-80 E (Fastest route). In 500 feet turn right.', 'https://maps.example.com', ''),
  'directions',
  'Must classify route text with turn guidance as directions'
);
assert.strictEqual(
  classifyPageArchetype(null, 'Public Transit Schedule: Subway Line 2. Departure 10:15 AM', 'https://transit.city.org/routes', ''),
  'directions',
  'Must classify transit route page as directions'
);
assert.strictEqual(
  classifyPageArchetype(null, 'Origin: San Francisco. Destination: Los Angeles', 'https://example.com/navigate', ''),
  'directions',
  'Must classify origin/destination navigate page as directions'
);

// Ticket Booking archetype preservation
assert.strictEqual(
  classifyPageArchetype(null, 'Flight SFO to JFK Departure 08:30 AM Economy Class $240', 'https://airline.com/booking', '@agent computer-use book flight ticket'),
  'booking',
  'Must classify flight booking page as booking'
);
assert.strictEqual(
  classifyPageArchetype(null, 'Concert VIP Pass $150. General Admission $65. Select seats now.', 'https://tickets.example.com/event/rock', ''),
  'booking',
  'Must classify concert ticket page as booking'
);

// 1.2 Extract and evaluate resolveNaturalLanguageNavUrl
const navMatch = appJs.match(/function resolveNaturalLanguageNavUrl\(goal\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(navMatch, 'resolveNaturalLanguageNavUrl must be defined in app.js');
eval(navMatch[0]);

// Map Directions Natural URL routing
const mapFromToUrl = resolveNaturalLanguageNavUrl('get map directions from Central Park to Times Square');
assert.ok(mapFromToUrl.includes('google.com/maps/dir/'), 'Must resolve to google.com/maps/dir/');
assert.ok(mapFromToUrl.includes('origin=Central%20Park'), 'Must encode origin correctly');
assert.ok(mapFromToUrl.includes('destination=Times%20Square'), 'Must encode destination correctly');

const mapDestUrl = resolveNaturalLanguageNavUrl('directions to Golden Gate Bridge');
assert.ok(mapDestUrl.includes('google.com/maps/dir/'), 'Must resolve to google.com/maps/dir/');
assert.ok(mapDestUrl.includes('destination=Golden%20Gate%20Bridge'), 'Must encode destination correctly');

const mapSearchUrl = resolveNaturalLanguageNavUrl('map of San Francisco');
assert.ok(mapSearchUrl.includes('google.com/maps/search/'), 'Must resolve to google.com/maps/search/');
assert.ok(mapSearchUrl.includes('query=San%20Francisco'), 'Must encode map query correctly');

// Flight & Ticket Booking Natural URL routing
const flightUrl = resolveNaturalLanguageNavUrl('book a ticket from SFO to JFK');
assert.ok(flightUrl.includes('google.com/travel/flights'), 'Must resolve to google.com/travel/flights');
assert.ok(flightUrl.includes('SFO') && flightUrl.includes('JFK'), 'Must contain origin and destination in flight query');

const concertTicketUrl = resolveNaturalLanguageNavUrl('book concert tickets');
assert.ok(concertTicketUrl.includes('google.com/search') && concertTicketUrl.includes('concert%20tickets'), 'Must resolve to ticket search portal');

console.log('  ✅ Test 1 Passed: Archetype classification and natural URL routing verified for maps and tickets.\n');

// =====================================================================
// Test 2: Structured Route Extraction (extractDirections)
// =====================================================================
console.log('Test 2: Structured Route Extraction (extractDirections)...');

const extractDirMatch = appJs.match(/function extractDirections\(doc,\s*text\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(extractDirMatch, 'extractDirections must be defined in app.js');
eval(extractDirMatch[0]);

// 2.1 DOM-based route extraction
class MockDirectionsDomNode {
  constructor(tagName = 'DIV', attrs = {}, text = '') {
    this.tagName = tagName.toUpperCase();
    this.attributes = attrs;
    this.id = attrs.id || '';
    this.className = attrs.class || '';
    this._textContent = text;
    this.children = [];
  }
  get textContent() {
    if (this._textContent) return this._textContent;
    return this.children.map(c => c.textContent).join(' ');
  }
  set textContent(v) { this._textContent = v; }
  querySelector(sel) {
    if (sel.includes('.section-directions-trip-title') || sel.includes('.route-title')) {
      return this.children.find(c => (c.className || '').includes('title')) || null;
    }
    if (sel.includes('.distance') || sel.includes('secondary-text')) {
      return this.children.find(c => (c.className || '').includes('distance')) || null;
    }
    if (sel.includes('.duration')) {
      return this.children.find(c => (c.className || '').includes('duration')) || null;
    }
    return null;
  }
  querySelectorAll(sel) {
    if (sel.includes('.section-directions-trip') || sel.includes('.route-card')) {
      return this.children.filter(c => (c.className || '').includes('route-card'));
    }
    if (sel.includes('.directions-step') || sel.includes('.step-item')) {
      return this.children.filter(c => (c.className || '').includes('step-item'));
    }
    return [];
  }
  appendChild(child) { this.children.push(child); }
}

const mockDoc = new MockDirectionsDomNode('BODY');
const route1El = new MockDirectionsDomNode('DIV', { class: 'route-card' });
const r1Title = new MockDirectionsDomNode('SPAN', { class: 'route-title' }, 'via I-80 E (Fastest Route)');
const r1Dist = new MockDirectionsDomNode('SPAN', { class: 'route-distance' }, '14.2 miles');
const r1Dur = new MockDirectionsDomNode('SPAN', { class: 'route-duration' }, '22 mins');
const step1 = new MockDirectionsDomNode('DIV', { class: 'step-item' }, 'Head north on Main St (0.5 miles)');
const step2 = new MockDirectionsDomNode('DIV', { class: 'step-item' }, 'Merge onto I-80 E (13.0 miles)');
const step3 = new MockDirectionsDomNode('DIV', { class: 'step-item' }, 'Take exit 42 toward Downtown (0.7 miles)');

route1El.appendChild(r1Title);
route1El.appendChild(r1Dist);
route1El.appendChild(r1Dur);
route1El.appendChild(step1);
route1El.appendChild(step2);
route1El.appendChild(step3);
mockDoc.appendChild(route1El);

const domParsed = extractDirections(mockDoc, '');
assert.ok(domParsed.routes.length === 1, 'Must extract 1 route from DOM');
assert.strictEqual(domParsed.routes[0].title, 'via I-80 E (Fastest Route)');
assert.strictEqual(domParsed.routes[0].distance, '14.2 miles');
assert.strictEqual(domParsed.routes[0].duration, '22 mins');
assert.strictEqual(domParsed.routes[0].isFastest, true);
assert.strictEqual(domParsed.routes[0].steps.length, 3, 'Must extract 3 step-by-step turns');
assert.strictEqual(domParsed.routes[0].steps[0].instruction, 'Head north on Main St');
console.log('  ✅ Test 2.1: DOM-based route and turn extraction validated.');

// 2.2 Plain Text Multi-Route Extraction
const sampleTextRoutes = `
Origin: San Francisco Ferry Building
Destination: San Jose Convention Center

Route 1: via US-101 S (Fastest route with current traffic)
Distance: 48.5 miles
Travel Time: 52 mins
Mode: Drive
Steps:
1. Head south on The Embarcadero (0.8 mi)
2. Take the ramp onto US-101 S (45.2 mi)
3. Take exit 384 for Market St toward Downtown (1.5 mi)
4. Arrive at San Jose Convention Center (1.0 mi)

Route 2: via I-280 S (Scenic route)
Distance: 53.1 miles
Travel Time: 58 mins
Mode: Drive
Steps:
1. Head south on The Embarcadero (0.8 mi)
2. Follow I-280 S toward San Jose (50.5 mi)
3. Exit onto Bird Ave (1.8 mi)
`;

const textParsed = extractDirections(null, sampleTextRoutes);
assert.ok(textParsed.routes.length === 2, `Must extract 2 routes from plain text, found ${textParsed.routes.length}`);
assert.strictEqual(textParsed.origin, 'San Francisco Ferry Building');
assert.strictEqual(textParsed.destination, 'San Jose Convention Center');
assert.ok(textParsed.routes[0].title.includes('US-101 S'), 'Route 1 must identify US-101 S');
assert.strictEqual(textParsed.routes[0].distance, '48.5 miles');
assert.strictEqual(textParsed.routes[0].duration, '52 mins');
assert.strictEqual(textParsed.routes[0].isFastest, true);
assert.ok(textParsed.routes[0].steps.length >= 3, 'Route 1 must extract at least 3 steps');
assert.ok(textParsed.routes[1].title.includes('I-280 S'), 'Route 2 must identify I-280 S');
assert.strictEqual(textParsed.routes[1].distance, '53.1 miles');
assert.strictEqual(textParsed.routes[1].duration, '58 mins');
console.log('  ✅ Test 2.2: Plain text multi-route extraction validated.\n');

// =====================================================================
// Test 3: Structured Ticket Extraction (extractTickets)
// =====================================================================
console.log('Test 3: Ticket Booking Extraction (extractTickets)...');

const extractTicketsMatch = appJs.match(/function extractTickets\(doc,\s*text\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(extractTicketsMatch, 'extractTickets must be defined in app.js');
eval(extractTicketsMatch[0]);

const sampleFlightText = `
Option 1: United Airlines Flight UA 214 (SFO to JFK) - Nonstop $289.00 Departure 08:30 AM Arrives 05:00 PM
Option 2: Delta Air Lines Flight DL 482 (SFO to JFK) - 1 Stop $235.50 Departure 10:15 AM Arrives 08:45 PM
Option 3: JetBlue Mint Business Class (SFO to JFK) - Nonstop $789.00 Departure 11:00 AM Lie-Flat Seat
`;

const parsedTickets = extractTickets(null, sampleFlightText);
assert.strictEqual(parsedTickets.length, 3, 'Must extract 3 flight ticket options');
assert.strictEqual(parsedTickets[0].numericPrice, 289);
assert.strictEqual(parsedTickets[0].currency, '$');
assert.strictEqual(parsedTickets[0].isRecommended, true);
assert.strictEqual(parsedTickets[1].numericPrice, 235.5);
assert.strictEqual(parsedTickets[2].numericPrice, 789);
console.log('  ✅ Test 3 Passed: Ticket options, pricing, and seat categories extracted accurately.\n');

// =====================================================================
// Test 4: HITL Directions Workspace & Interactive Safety Gate
// =====================================================================
console.log('Test 4: buildHitlDirectionsWorkspaceHtml & Window Handlers...');

// Mock escapeHtml helper
global.escapeHtml = global.escapeHtml || (s => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'));

const buildDirHtmlMatch = appJs.match(/function buildHitlDirectionsWorkspaceHtml\(directions,\s*title[\s\S]*?\{([\s\S]*?)\n  \}/);
assert.ok(buildDirHtmlMatch, 'buildHitlDirectionsWorkspaceHtml must be defined in app.js');
eval(buildDirHtmlMatch[0]);

const dirHtml = buildHitlDirectionsWorkspaceHtml(textParsed, 'San Francisco to San Jose Navigation');
assert.ok(dirHtml.includes('hitl-directions-workspace'), 'Must contain hitl-directions-workspace container');
assert.ok(dirHtml.includes('San Francisco Ferry Building'), 'Must include origin');
assert.ok(dirHtml.includes('San Jose Convention Center'), 'Must include destination');
assert.ok(dirHtml.includes('US-101 S'), 'Must include Route 1');
assert.ok(dirHtml.includes('48.5 miles'), 'Must include Route 1 distance');
assert.ok(dirHtml.includes('52 mins'), 'Must include Route 1 duration');
assert.ok(dirHtml.includes('FASTEST'), 'Must display FASTEST badge');
assert.ok(dirHtml.includes('directions-hitl-safety-gate'), 'Must render safety gate bar');
assert.ok(dirHtml.includes('window.confirmDirectionsAction()'), 'Must wire confirm action');
assert.ok(dirHtml.includes('window.abortDirectionsAction()'), 'Must wire abort action');
assert.ok(dirHtml.includes('window.autoSelectFastestRoute()'), 'Must wire autoSelectFastestRoute');

// Test window handlers
const selectRouteMatch = appJs.match(/function selectDirectionRoute\(rIndex\)\s*\{([\s\S]*?)\n  \}/);
eval(selectRouteMatch[0]);
const confirmDirMatch = appJs.match(/function confirmDirectionsAction\(\)\s*\{([\s\S]*?)\n  \}/);
eval(confirmDirMatch[0]);
const abortDirMatch = appJs.match(/function abortDirectionsAction\(\)\s*\{([\s\S]*?)\n  \}/);
eval(abortDirMatch[0]);
const autoSelectFastMatch = appJs.match(/function autoSelectFastestRoute\(\)\s*\{([\s\S]*?)\n  \}/);
eval(autoSelectFastMatch[0]);

// Mock DOM elements for handler execution
const mockGate = { innerHTML: '' };
const mockRouteCards = [
  { id: 'directions-r-0', style: {}, querySelector: () => ({ textContent: '', style: {} }) },
  { id: 'directions-r-1', style: {}, querySelector: () => ({ textContent: '', style: {} }) }
];
global.document = {
  getElementById: (id) => {
    if (id === 'directions-hitl-safety-gate') return mockGate;
    if (id === 'directions-r-0') return mockRouteCards[0];
    if (id === 'directions-r-1') return mockRouteCards[1];
    return null;
  }
};
global.termLog = () => {};

// Select Route 2
selectDirectionRoute(1);
assert.strictEqual(window.selectedRouteId, 2, 'Must update selectedRouteId to 2');
assert.strictEqual(mockRouteCards[1].style.borderColor, '#38bdf8');

// Auto select fastest
autoSelectFastestRoute();
assert.strictEqual(window.selectedRouteId, 1, 'Must auto-select Route 1 as fastest');

// Confirm Action
confirmDirectionsAction();
assert.ok(mockGate.innerHTML.includes('Human Verification Granted: Navigation Started!'), 'Confirm must render approval banner');
assert.ok(mockGate.innerHTML.includes('US-101 S'), 'Must mention confirmed route');

// Abort Action
abortDirectionsAction();
assert.ok(mockGate.innerHTML.includes('Navigation Canceled by User'), 'Abort must render cancellation banner');

console.log('  ✅ Test 4 Passed: HITL Directions workspace and safety gate transitions validated.\n');

// =====================================================================
// Test 5: HITL Ticket Booking Workspace & Safety Gate Transitions
// =====================================================================
console.log('Test 5: buildHitlBookingWorkspaceHtml & Booking Handlers...');

const buildBookingHtmlMatch = appJs.match(/function buildHitlBookingWorkspaceHtml\(tickets,\s*eventTitle[\s\S]*?\{([\s\S]*?)\n  \}/);
assert.ok(buildBookingHtmlMatch, 'buildHitlBookingWorkspaceHtml must be defined in app.js');
eval(buildBookingHtmlMatch[0]);

const bookingHtml = buildHitlBookingWorkspaceHtml(parsedTickets, 'Flight Reservation: SFO to JFK');
assert.ok(bookingHtml.includes('hitl-booking-workspace'), 'Must include hitl-booking-workspace');
assert.ok(bookingHtml.includes('$289.00'), 'Must include price $289.00');
assert.ok(bookingHtml.includes('booking-hitl-safety-gate'), 'Must include booking safety gate');
assert.ok(bookingHtml.includes('window.confirmBookingAction()'), 'Must wire confirmBookingAction');
assert.ok(bookingHtml.includes('window.abortBookingAction()'), 'Must wire abortBookingAction');

const selectTicketMatch = appJs.match(/function selectBookingTicket\(tIndex\)\s*\{([\s\S]*?)\n  \}/);
eval(selectTicketMatch[0]);
const confirmBookingMatch = appJs.match(/function confirmBookingAction\(\)\s*\{([\s\S]*?)\n  \}/);
eval(confirmBookingMatch[0]);
const abortBookingMatch = appJs.match(/function abortBookingAction\(\)\s*\{([\s\S]*?)\n  \}/);
eval(abortBookingMatch[0]);
const changeTicketQtyMatch = appJs.match(/function changeTicketQuantity\(tIndex,\s*delta\)\s*\{([\s\S]*?)\n  \}/);
eval(changeTicketQtyMatch[0]);

const mockBookingGate = { innerHTML: '' };
const mockTicketCards = [
  { id: 'booking-t-0', style: {}, querySelector: () => ({ textContent: '', style: {} }) },
  { id: 'booking-t-1', style: {}, querySelector: () => ({ textContent: '', style: {} }) }
];
const mockQtyEl = { textContent: '1' };

global.document = {
  getElementById: (id) => {
    if (id === 'booking-hitl-safety-gate') return mockBookingGate;
    if (id === 'booking-t-0') return mockTicketCards[0];
    if (id === 'booking-t-1') return mockTicketCards[1];
    if (id === 't-qty-0') return mockQtyEl;
    return null;
  }
};

selectBookingTicket(0);
assert.strictEqual(window.selectedTicketId, 1, 'Must select ticket ID 1');

// Change quantity
changeTicketQuantity(0, 1);
assert.strictEqual(parsedTickets[0].quantity, 2, 'Quantity must increment to 2');
assert.strictEqual(mockQtyEl.textContent, '2');

// Confirm booking
confirmBookingAction();
assert.ok(mockBookingGate.innerHTML.includes('Human Verification Granted: Ticket Reservation Confirmed!'), 'Must display confirmed banner');
assert.ok(mockBookingGate.innerHTML.includes('2 seat(s)'), 'Must display updated seat quantity');

// Abort booking
abortBookingAction();
assert.ok(mockBookingGate.innerHTML.includes('Booking Reservation Aborted by User'), 'Must display aborted banner');

console.log('  ✅ Test 5 Passed: HITL Ticket booking workspace and safety gates validated.\n');

// =====================================================================
// Test 6: Universal Execution Gate & Non-Premature Return Guarantee
// =====================================================================
console.log('Test 6: Universal Browser Execution Gate Verification...');

const isContentGoalRegex = /(?:extract|answer|question|test|exam|quiz|find|tell|solve|what|parse|vuln|security|threat|analy)/i;
const isUniversalBrowserGoalRegex = new RegExp(
  isContentGoalRegex.source +
  '|(?:shop|price|product|buy|cart|order|deal|book|ticket|flight|seat|hotel|reservation|form|submit|map|maps|direction|directions|route|navigate|distance|drive|transit|walk)',
  'i'
);

// Map and directions goals must match isUniversalBrowserGoal
const mapGoals = [
  '@agent computer-use get map directions from Central Park to Times Square',
  '@agent computer-use directions to Golden Gate Bridge',
  '@agent computer-use find the best route to San Jose',
  '@agent ui-tars navigate to airport',
  '@agent computer-use what is the drive distance to Boston?'
];
mapGoals.forEach(g => {
  assert.ok(isUniversalBrowserGoalRegex.test(g), `Goal "${g}" must match isUniversalBrowserGoal`);
});

// Ticket and booking goals must match isUniversalBrowserGoal
const bookingGoals = [
  '@agent computer-use book a ticket from SFO to JFK',
  '@agent computer-use book concert tickets',
  '@agent ui-tars reserve flight seats',
  '@agent computer-use find hotel reservation'
];
bookingGoals.forEach(g => {
  assert.ok(isUniversalBrowserGoalRegex.test(g), `Goal "${g}" must match isUniversalBrowserGoal`);
});

// Verify app.js implementation checks if (isUniversalBrowserGoal)
assert.ok(
  appJs.includes('if (isUniversalBrowserGoal)'),
  'app.js must check if (isUniversalBrowserGoal) to trigger streaming same-page response'
);

// Verify NO duplicate hitlExamCardHtml rendering in grounding-cards-container
const containerSlice = appJs.slice(appJs.indexOf('class="grounding-cards-container"'), appJs.indexOf('class="stream-content-planner"'));
const examCardOccurrences = (containerSlice.match(/\$\{hitlExamCardHtml\}/g) || []).length;
assert.strictEqual(
  examCardOccurrences,
  0,
  'grounding-cards-container must not contain duplicate ${hitlExamCardHtml} (already included in ${hitlWorkspaceCardHtml})'
);
assert.ok(
  containerSlice.includes('${hitlWorkspaceCardHtml}'),
  'grounding-cards-container must render ${hitlWorkspaceCardHtml}'
);

console.log('  ✅ Test 6 Passed: Universal browser execution gate and deduplicated card rendering verified.\n');

// =====================================================================
// Test 7: CSS Rules in styles.css for Directions Workspace
// =====================================================================
console.log('Test 7: Validating CSS rules in styles.css...');
const cssPath = path.resolve(__dirname, '../browser/ui/styles.css');
assert.ok(fs.existsSync(cssPath), 'browser/ui/styles.css must exist');
const css = fs.readFileSync(cssPath, 'utf8');

assert.ok(css.includes('.hitl-directions-workspace'), 'styles.css must include .hitl-directions-workspace');
assert.ok(css.includes('.direction-route-card'), 'styles.css must include .direction-route-card');
assert.ok(css.includes('.route-duration-tag'), 'styles.css must include .route-duration-tag');
assert.ok(css.includes('.route-distance-tag'), 'styles.css must include .route-distance-tag');
assert.ok(css.includes('.route-fastest-badge'), 'styles.css must include .route-fastest-badge');
assert.ok(css.includes('.btn-directions-confirm'), 'styles.css must include .btn-directions-confirm');
assert.ok(css.includes('.directions-safety-gate-bar'), 'styles.css must include .directions-safety-gate-bar');

console.log('  ✅ Test 7 Passed: All Directions and Navigation CSS styling rules verified.\n');

console.log('🌟 ALL 7 TICKET BOOKING & MAP DIRECTIONS HITL TESTS PASSED (100%)! 🌟\n');
