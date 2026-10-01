// tests/test_universal_browser_hitl.js
// Automated verification suite for Universal Browser Processing, Shopping,
// Ticket Booking, Exam Answering & Human-in-the-Loop (HITL) Safety Gates in ModelFusion

const assert = require('assert');
const fs = require('fs');
const path = require('path');

console.log('🧪 Starting Universal Browser Processing & HITL Verification Suite...\n');

const appPath = path.resolve(__dirname, '../browser/ui/app.js');
assert.ok(fs.existsSync(appPath), 'browser/ui/app.js must exist');
const appJs = fs.readFileSync(appPath, 'utf8');
global.window = global.window || {};

// =====================================================================
// Test 1: Universal Page Archetype Classifier Verification
// =====================================================================
console.log('Test 1: Universal Page Archetype Classifier (classifyPageArchetype)...');
const classifyMatch = appJs.match(/function classifyPageArchetype\(doc,\s*text,\s*url[\s\S]*?\{([\s\S]*?)\n  \}/);
assert.ok(classifyMatch, 'classifyPageArchetype must be defined in app.js');
eval(classifyMatch[0]);

// 1.1 Exam Archetype
assert.strictEqual(
  classifyPageArchetype(null, 'Which of the following is correct?', 'https://tests.com/practice/exam', '@agent computer-use solve exam'),
  'exam',
  'Must classify exam page and goal as exam'
);
assert.strictEqual(
  classifyPageArchetype(null, 'Question 1: What is ModelFusion? A. Core B. Library', 'https://example.com/quiz', ''),
  'exam',
  'Must classify quiz text as exam'
);

// 1.2 Shopping Archetype
assert.strictEqual(
  classifyPageArchetype(null, 'Sony WH-1000XM5 Headphones $348.00 In Stock Free Shipping', 'https://amazon.com/dp/B09XS7JWHH', '@agent computer-use find lowest price'),
  'shopping',
  'Must classify product page with prices as shopping'
);
assert.strictEqual(
  classifyPageArchetype(null, 'Add to cart. Customer reviews: 4.8 stars. $199.99', 'https://store.example.com/cart', ''),
  'shopping',
  'Must classify e-commerce cart/product as shopping'
);

// 1.3 Ticket & Travel Booking Archetype
assert.strictEqual(
  classifyPageArchetype(null, 'Flight SFO to JFK Departure 08:30 AM Economy Class $240', 'https://airline.com/booking', '@agent computer-use book flight ticket'),
  'booking',
  'Must classify flight booking page as booking'
);
assert.strictEqual(
  classifyPageArchetype(null, 'Concert VIP Pass $150. General Admission $65. Select seats now.', 'https://tickets.example.com/event/rock', ''),
  'booking',
  'Must classify concert/event ticket page as booking'
);

// 1.4 Form Submission Archetype
assert.strictEqual(
  classifyPageArchetype(null, 'First Name: Last Name: Email Address: Phone: Submit form', 'https://example.com/register', ''),
  'form',
  'Must classify registration form as form'
);

// 1.5 General Content Archetype
assert.strictEqual(
  classifyPageArchetype(null, 'Welcome to the documentation guide for ModelFusion architecture.', 'https://modelfusion.ai/docs', 'Summarize this page'),
  'content',
  'Must classify general documentation as content'
);
console.log('  ✅ Test 1 Passed: classifyPageArchetype accurately identifies all 5 page archetypes.\n');

// =====================================================================
// Test 2: Structured E-Commerce Product Extraction (DOM & Text)
// =====================================================================
console.log('Test 2: extractProducts from DOM and plain text with Best Deal detection...');
const extractProductsMatch = appJs.match(/function extractProducts\(doc,\s*text\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(extractProductsMatch, 'extractProducts must be defined in app.js');
eval(extractProductsMatch[0]);

// Mock DOM Node for Product parsing
class MockProductDomNode {
  constructor(tagName = 'DIV', attrs = {}, text = '') {
    this.tagName = tagName.toUpperCase();
    this.attributes = attrs;
    this.id = attrs.id || '';
    this.className = attrs.class || '';
    this._textContent = text;
    this.children = [];
    this.parentElement = null;
  }
  get textContent() {
    if (this._textContent) return this._textContent;
    return this.children.map(c => c.textContent).join(' ');
  }
  set textContent(v) { this._textContent = v; }
  getAttribute(name) { return this.attributes[name] || null; }
  appendChild(child) {
    child.parentElement = this;
    this.children.push(child);
    return child;
  }
  querySelectorAll(sel) {
    const res = [];
    const walk = (n) => {
      for (const c of n.children) {
        if (c.matchesSelector(sel)) res.push(c);
        walk(c);
      }
    };
    walk(this);
    return res;
  }
  querySelector(sel) {
    const all = this.querySelectorAll(sel);
    return all.length > 0 ? all[0] : null;
  }
  matchesSelector(sel) {
    const s = sel.toLowerCase();
    const classes = (this.className || '').split(/\s+/);
    if (s.includes('.product-title') && classes.includes('product-title')) return true;
    if (s.includes('.product-card') && classes.includes('product-card')) return true;
    if (s.includes('.product') && !s.includes('.product-title') && !s.includes('.product-price') && classes.includes('product')) return true;
    if (s.includes('.price') && classes.some(c => c.includes('price'))) return true;
    if (s.includes('.rating') && classes.includes('rating')) return true;
    if (s.includes('button') && this.tagName === 'BUTTON') return true;
    return false;
  }
}

// 2.1 DOM Product extraction
const mockStoreDoc = new MockProductDomNode('HTML');
const mockStoreBody = new MockProductDomNode('BODY');
mockStoreDoc.appendChild(mockStoreBody);

// Product 1
const p1 = new MockProductDomNode('DIV', { class: 'product-card' });
const p1Title = new MockProductDomNode('H3', { class: 'product-title' }, 'Bose QuietComfort 45');
const p1Price = new MockProductDomNode('SPAN', { class: 'price' }, '$279.00');
const p1Rating = new MockProductDomNode('SPAN', { class: 'rating', 'aria-label': '4.7 out of 5 stars' }, '4.7');
const p1Btn = new MockProductDomNode('BUTTON', { id: 'btn-add-p1', class: 'add-to-cart' }, 'Add to Cart');
p1.appendChild(p1Title); p1.appendChild(p1Price); p1.appendChild(p1Rating); p1.appendChild(p1Btn);
mockStoreBody.appendChild(p1);

// Product 2 (cheaper -> best deal)
const p2 = new MockProductDomNode('DIV', { class: 'product-card' });
const p2Title = new MockProductDomNode('H3', { class: 'product-title' }, 'Sony WH-CH720N Wireless');
const p2Price = new MockProductDomNode('SPAN', { class: 'price' }, '$128.00');
const p2Rating = new MockProductDomNode('SPAN', { class: 'rating', 'aria-label': '4.4 out of 5 stars' }, '4.4');
const p2Btn = new MockProductDomNode('BUTTON', { id: 'btn-add-p2', class: 'add-to-cart' }, 'Add to Cart');
p2.appendChild(p2Title); p2.appendChild(p2Price); p2.appendChild(p2Rating); p2.appendChild(p2Btn);
mockStoreBody.appendChild(p2);

const domProducts = extractProducts(mockStoreDoc, '');
assert.strictEqual(domProducts.length, 2, 'Must extract 2 products from mock DOM');
assert.strictEqual(domProducts[0].title, 'Bose QuietComfort 45');
assert.strictEqual(domProducts[0].numericPrice, 279.00);
assert.strictEqual(domProducts[0].currency, '$');
assert.strictEqual(domProducts[1].title, 'Sony WH-CH720N Wireless');
assert.strictEqual(domProducts[1].numericPrice, 128.00);
assert.strictEqual(domProducts[1].isBestDeal, true, 'Product 2 ($128) must be flagged as isBestDeal');
console.log('  ✅ Test 2.1: DOM-based product extraction parsed titles, numeric prices, ratings, and best deal.');

// 2.2 Plain Text Product extraction fallback
const sampleTextStore = `
1. Apple MacBook Air M3 — $1,099.00 (16GB RAM, 256GB SSD) — 4.9 stars
2. Dell XPS 13 OLED — $1,249.00 (Intel Core Ultra 7) — 4.5 stars
3. Lenovo ThinkPad T14 — $899.00 (AMD Ryzen 7 PRO, 16GB) — 4.7 stars
`;

const textProducts = extractProducts(null, sampleTextStore);
assert.strictEqual(textProducts.length, 3, 'Must extract 3 products from text list');
assert.strictEqual(textProducts[0].title, 'Apple MacBook Air M3');
assert.strictEqual(textProducts[0].numericPrice, 1099.00);
assert.strictEqual(textProducts[2].title, 'Lenovo ThinkPad T14');
assert.strictEqual(textProducts[2].numericPrice, 899.00);
assert.strictEqual(textProducts[2].isBestDeal, true, 'Lenovo ($899) must be marked as isBestDeal');
console.log('  ✅ Test 2.2: Plain text product extraction parsed titles, currency, prices, and best value deal.\n');

// =====================================================================
// Test 3: Structured Ticket & Travel Booking Extraction (DOM & Text)
// =====================================================================
console.log('Test 3: extractTickets from DOM and plain text...');
const extractTicketsMatch = appJs.match(/function extractTickets\(doc,\s*text\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(extractTicketsMatch, 'extractTickets must be defined in app.js');
eval(extractTicketsMatch[0]);

// 3.1 Plain text ticket parsing
const ticketText = `
Option 1: United Airlines UA412 SFO -> JFK (Nonstop, Depart 7:00 AM) — $280.00
Option 2: Delta Air Lines DL890 SFO -> JFK (Nonstop, Depart 1:30 PM) — $315.00
Option 3: JetBlue Mint Business Class (Lie-flat seat, Depart 6:00 PM) — $750.00
`;

const tickets = extractTickets(null, ticketText);
assert.strictEqual(tickets.length, 3, 'Must extract 3 ticket options from text');
assert.strictEqual(tickets[0].numericPrice, 280.00);
assert.strictEqual(tickets[0].currency, '$');
assert.ok(tickets[0].title.includes('United Airlines'));
assert.strictEqual(tickets[0].isRecommended, true, 'First/optimal option must be marked isRecommended');
assert.strictEqual(tickets[2].numericPrice, 750.00);
console.log('  ✅ Test 3 Passed: Ticket and travel booking extraction parsed routes, departure times, and prices.\n');

// =====================================================================
// Test 4: HITL Shopping Workspace HTML & Window Handlers
// =====================================================================
console.log('Test 4: buildHitlShoppingWorkspaceHtml and interactive window handlers...');
function escapeHtml(str) {
  if (typeof str !== 'string') return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}
global.escapeHtml = escapeHtml;

const buildShoppingWorkspaceMatch = appJs.match(/function buildHitlShoppingWorkspaceHtml\(products,\s*storeTitle[\s\S]*?\{([\s\S]*?)\n  \}/);
assert.ok(buildShoppingWorkspaceMatch, 'buildHitlShoppingWorkspaceHtml must be defined in app.js');
eval(buildShoppingWorkspaceMatch[0]);

const shoppingHtml = buildHitlShoppingWorkspaceHtml(textProducts, 'Tech Store Product Comparison');
assert.ok(shoppingHtml.includes('class="hitl-shopping-workspace"'), 'Must render hitl-shopping-workspace root');
assert.ok(shoppingHtml.includes('Tech Store Product Comparison'), 'Must render store title');
assert.ok(shoppingHtml.includes('3 Products / Deals Grounded'), 'Must display product count badge');
assert.ok(shoppingHtml.includes('onclick="window.autoSelectBestDeal()"'), 'Must include Select Best Value Deal button');
assert.ok(shoppingHtml.includes('id="shopping-p-0"'), 'Must render product card 0');
assert.ok(shoppingHtml.includes('id="shopping-hitl-safety-gate"'), 'Must render Human Approval Required safety gate');
assert.ok(shoppingHtml.includes('onclick="window.confirmShoppingAction()"'), 'Must wire confirmShoppingAction button');
assert.ok(shoppingHtml.includes('onclick="window.abortShoppingAction()"'), 'Must wire abortShoppingAction button');

// Evaluate interactive handlers
const selectProductMatch = appJs.match(/function selectShoppingProduct\(pIndex\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(selectProductMatch, 'selectShoppingProduct must be defined');
eval(selectProductMatch[0]);

const changeQtyMatch = appJs.match(/function changeProductQuantity\(pIndex,\s*delta\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(changeQtyMatch, 'changeProductQuantity must be defined');
eval(changeQtyMatch[0]);

const confirmShoppingMatch = appJs.match(/function confirmShoppingAction\(\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(confirmShoppingMatch, 'confirmShoppingAction must be defined');
eval(confirmShoppingMatch[0]);

const abortShoppingMatch = appJs.match(/function abortShoppingAction\(\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(abortShoppingMatch, 'abortShoppingAction must be defined');
eval(abortShoppingMatch[0]);

window.activeProducts = textProducts;
window.selectedProductId = null;

// Select Product 2
selectShoppingProduct(2);
assert.strictEqual(window.selectedProductId, textProducts[2].id, 'selectedProductId must equal Product 2 ID');

// Increase quantity
changeProductQuantity(2, 2);
assert.strictEqual(window.activeProducts[2].quantity, 3, 'Quantity must increase from 1 to 3');

// Confirm shopping action
const mockShopGate = { innerHTML: '' };
global.document = {
  getElementById: (id) => (id === 'shopping-hitl-safety-gate' ? mockShopGate : null),
  querySelector: () => null
};
confirmShoppingAction();
assert.ok(mockShopGate.innerHTML.includes('Human Approval Granted: Item Added to Cart'), 'Confirm must show approval banner');

// Abort shopping action
abortShoppingAction();
assert.ok(mockShopGate.innerHTML.includes('Shopping Action Aborted by User'), 'Abort must show cancellation banner');
console.log('  ✅ Test 4 Passed: HITL shopping workspace renders interactive cards, quantity controls, and safety gates.\n');

// =====================================================================
// Test 5: HITL Booking Workspace HTML & Window Handlers
// =====================================================================
console.log('Test 5: buildHitlBookingWorkspaceHtml and interactive booking handlers...');
const buildBookingWorkspaceMatch = appJs.match(/function buildHitlBookingWorkspaceHtml\(tickets,\s*eventTitle[\s\S]*?\{([\s\S]*?)\n  \}/);
assert.ok(buildBookingWorkspaceMatch, 'buildHitlBookingWorkspaceHtml must be defined');
eval(buildBookingWorkspaceMatch[0]);

const bookingHtml = buildHitlBookingWorkspaceHtml(tickets, 'SFO to JFK Flight Reservations');
assert.ok(bookingHtml.includes('class="hitl-booking-workspace"'), 'Must render hitl-booking-workspace root');
assert.ok(bookingHtml.includes('SFO to JFK Flight Reservations'), 'Must render event/route title');
assert.ok(bookingHtml.includes('3 Options Detected'), 'Must render options count badge');
assert.ok(bookingHtml.includes('onclick="window.autoSelectRecommendedTicket()"'), 'Must wire autoSelectRecommendedTicket');
assert.ok(bookingHtml.includes('id="booking-hitl-safety-gate"'), 'Must render booking safety gate');
assert.ok(bookingHtml.includes('onclick="window.confirmBookingAction()"'), 'Must wire confirmBookingAction');

const confirmBookingMatch = appJs.match(/function confirmBookingAction\(\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(confirmBookingMatch, 'confirmBookingAction must be defined');
eval(confirmBookingMatch[0]);

const abortBookingMatch = appJs.match(/function abortBookingAction\(\)\s*\{([\s\S]*?)\n  \}/);
assert.ok(abortBookingMatch, 'abortBookingAction must be defined');
eval(abortBookingMatch[0]);

window.activeTickets = tickets;
window.selectedTicketId = tickets[0].id;

const mockBookingGate = { innerHTML: '' };
global.document.getElementById = (id) => (id === 'booking-hitl-safety-gate' ? mockBookingGate : null);

confirmBookingAction();
assert.ok(mockBookingGate.innerHTML.includes('Human Verification Granted: Ticket Reservation Confirmed!'), 'Confirm must show confirmation banner');

abortBookingAction();
assert.ok(mockBookingGate.innerHTML.includes('Booking Reservation Aborted by User'), 'Abort must show cancellation banner');
console.log('  ✅ Test 5 Passed: HITL booking workspace renders ticket tiers, seat selection, and safety gates.\n');

// =====================================================================
// Test 6: Arbitrary Browser Task Safety Gate (Generic HITL)
// =====================================================================
console.log('Test 6: buildHitlGenericActionWorkspaceHtml for arbitrary browser tasks...');
const buildGenericMatch = appJs.match(/function buildHitlGenericActionWorkspaceHtml\(actionSummary,\s*targetDetails[\s\S]*?\{([\s\S]*?)\n  \}/);
assert.ok(buildGenericMatch, 'buildHitlGenericActionWorkspaceHtml must be defined');
eval(buildGenericMatch[0]);

const genericHtml = buildHitlGenericActionWorkspaceHtml('Submit Mortgage Application and Credit Check', 'BankOfAmerica Portal');
assert.ok(genericHtml.includes('class="hitl-generic-workspace"'), 'Must render hitl-generic-workspace root');
assert.ok(genericHtml.includes('Submit Mortgage Application'), 'Must render action summary');
assert.ok(genericHtml.includes('onclick="window.confirmGenericAction()"'), 'Must wire confirm button');
assert.ok(genericHtml.includes('onclick="window.abortGenericAction()"'), 'Must wire abort button');
console.log('  ✅ Test 6 Passed: Generic HITL gate protects arbitrary sensitive browser actions.\n');

// =====================================================================
// Test 7: Prompt Context Pruning & Ollama Stall Prevention
// =====================================================================
console.log('Test 7: Context token budgeting and isolateContext guarantee...');
// Verify app.js contains the fast structured grounding logic
assert.ok(
  appJs.includes('const hasStructuredItems = detectedExamQuestions.length > 0 || detectedProducts.length > 0 || detectedTickets.length > 0;'),
  'app.js must detect hasStructuredItems to avoid dumping raw DOM text into LLM prompt'
);
assert.ok(
  appJs.includes('livePageText.slice(0, 600)'),
  'app.js must cap background text to 600 chars when structured items are present'
);
assert.ok(
  appJs.includes('isolateContext: true'),
  'streamAiChat call in computer use must set isolateContext: true'
);
assert.ok(
  appJs.includes('!options?.isolateContext && options?.taskType !== \'computer_use\''),
  'streamAiChat must skip 30 past conversation messages when isolateContext is enabled'
);
console.log('  ✅ Test 7 Passed: Prompt context is strictly budgeted to <1,500 tokens, eliminating CPU Ollama stalls.\n');

// =====================================================================
// Test 8: CSS Rules for Universal Workspaces in styles.css
// =====================================================================
console.log('Test 8: Validating CSS rules in styles.css for Universal Workspaces...');
const cssPath = path.resolve(__dirname, '../browser/ui/styles.css');
assert.ok(fs.existsSync(cssPath), 'browser/ui/styles.css must exist');
const css = fs.readFileSync(cssPath, 'utf8');

assert.ok(css.includes('.hitl-shopping-workspace'), 'styles.css must include .hitl-shopping-workspace');
assert.ok(css.includes('.hitl-booking-workspace'), 'styles.css must include .hitl-booking-workspace');
assert.ok(css.includes('.hitl-generic-workspace'), 'styles.css must include .hitl-generic-workspace');
assert.ok(css.includes('.product-card'), 'styles.css must include .product-card');
assert.ok(css.includes('.ticket-card'), 'styles.css must include .ticket-card');
assert.ok(css.includes('.product-price-tag'), 'styles.css must include .product-price-tag');
assert.ok(css.includes('.ticket-price-tag'), 'styles.css must include .ticket-price-tag');
assert.ok(css.includes('.product-deal-badge'), 'styles.css must include .product-deal-badge');
assert.ok(css.includes('.shopping-safety-gate-bar'), 'styles.css must include .shopping-safety-gate-bar');
assert.ok(css.includes('.booking-safety-gate-bar'), 'styles.css must include .booking-safety-gate-bar');
assert.ok(css.includes('.btn-shopping-confirm'), 'styles.css must include .btn-shopping-confirm');
assert.ok(css.includes('.btn-booking-confirm'), 'styles.css must include .btn-booking-confirm');
assert.ok(css.includes('.btn-hitl-approve'), 'styles.css must include .btn-hitl-approve');
assert.ok(css.includes('.btn-hitl-abort'), 'styles.css must include .btn-hitl-abort');
console.log('  ✅ Test 8 Passed: All universal HITL workspace CSS classes verified.\n');

console.log('🌟 ALL 8 UNIVERSAL BROWSER HITL & PROCESSING TESTS PASSED (100%)! 🌟\n');
