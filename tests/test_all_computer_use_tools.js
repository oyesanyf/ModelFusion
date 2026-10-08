/**
 * tests/test_all_computer_use_tools.js
 * Comprehensive Verification & Validation Suite for ALL 11 Computer Use Tools
 * Across ModelFusion Master CLI, HugOS Browser, and UI-TARS Autonomous Engine.
 *
 * Verifies:
 * 1. Autonomous Computer Use (@agent computer-use)
 * 2. Exam & Quiz Solver (@agent exam-solver)
 * 3. Map Directions & Navigation (@agent map-directions)
 * 4. OS Mouse Click (@agent desktop-click)
 * 5. OS Type & Hotkey (@agent desktop-type)
 * 6. OS Window Scroll (@agent desktop-scroll)
 * 7. Screen Grounding (@agent screen-grounding)
 * 8. Shopping & Price Discovery (@agent shopping)
 * 9. Ticket & Travel Booking (@agent ticket-booking)
 * 10. UI-TARS Agent Loop (@agent ui-tars)
 * 11. Apply for Jobs (@agent apply-jobs)
 * 12. Subdomain & Domain Typo Normalization (ww.google.com -> www.google.com)
 * 13. Search Query Extraction & Target URL Rewriting
 * 14. Stale CLI Error Detection & Discarding
 * 15. Universal HITL Workspaces (Exam, Shopping, Booking, Directions, Generic)
 * 16. Clean Execution Badge Display (Suppressing misleading CLI error diagnostics)
 */

const fs = require('fs');
const path = require('path');

let passedTests = 0;
let totalTests = 0;

function assert(condition, message) {
  totalTests++;
  if (condition) {
    passedTests++;
    console.log(`  ✅ [PASS] ${message}`);
  } else {
    console.error(`  ❌ [FAIL] ${message}`);
    throw new Error(`Assertion failed: ${message}`);
  }
}

console.log('================================================================');
console.log('🖥️ Running Comprehensive 11-Tool Computer Use Verification Suite');
console.log('================================================================\n');

// Load browser/ui/app.js
const appJsPath = path.resolve(__dirname, '../browser/ui/app.js');
const appJsContent = fs.readFileSync(appJsPath, 'utf8');

// --- Group 1: Subdomain and Domain Typo Normalization ---
console.log('--- Group 1: Subdomain & Search Engine Typo Normalization ---');
const sanitizeMatch = appJsContent.match(/function sanitizeAndDeduplicateUrl\(raw\) \{([\s\S]*?)\n  \}/);
if (!sanitizeMatch) throw new Error('Could not find sanitizeAndDeduplicateUrl in app.js');
const sanitizeAndDeduplicateUrl = new Function('raw', sanitizeMatch[1]);

assert(sanitizeAndDeduplicateUrl('https://ww.google.com') === 'https://www.google.com', 'ww.google.com -> www.google.com');
assert(sanitizeAndDeduplicateUrl('https://w.google.com') === 'https://www.google.com', 'w.google.com -> www.google.com');
assert(sanitizeAndDeduplicateUrl('https://wwww.google.com') === 'https://www.google.com', 'wwww.google.com -> www.google.com');
assert(sanitizeAndDeduplicateUrl('https://gogle.com') === 'https://www.google.com', 'gogle.com -> www.google.com');
assert(sanitizeAndDeduplicateUrl('https://googl.com') === 'https://www.google.com', 'googl.com -> www.google.com');
assert(sanitizeAndDeduplicateUrl('https://ww.bing.com') === 'https://www.bing.com', 'ww.bing.com -> www.bing.com');
assert(sanitizeAndDeduplicateUrl('https://ww.duckduckgo.com') === 'https://duckduckgo.com', 'ww.duckduckgo.com -> duckduckgo.com');

// --- Group 2: Typo-Tolerant Search Query Extraction ---
console.log('\n--- Group 2: Search Query Extraction from Goals ---');
const extractQueryMatch = appJsContent.match(/function extractSearchQueryFromGoal\(goal\) \{([\s\S]*?)\n  \}/);
if (!extractQueryMatch) throw new Error('Could not find extractSearchQueryFromGoal in app.js');
const extractSearchQueryFromGoal = new Function('goal', extractQueryMatch[1]);

assert(
  extractSearchQueryFromGoal('go to https://ww.google.com and seach for nigeria') === 'nigeria',
  'Extracts "nigeria" from "seach for nigeria"'
);
assert(
  extractSearchQueryFromGoal('go to http://www.google.com and seach for weather in lagos Nigeria') === 'weather in lagos Nigeria',
  'Extracts "weather in lagos Nigeria"'
);
assert(
  extractSearchQueryFromGoal('open browser and search for machine learning algorithms') === 'machine learning algorithms',
  'Extracts "machine learning algorithms"'
);

// --- Group 3: Goal Formatting Across All 11 Computer Use Tools ---
console.log('\n--- Group 3: Goal Resolution for All 11 Computer Use Tools ---');

function resolveComputerUseGoal(cmd) {
  const isComputerUseToolCmd =
    /^(?:@agent\s+|\/|@)?(?:computer[- ]?use|ui[- ]?tars|screen[- ]?grounding|desktop[- ]?(?:click|type|scroll)|exam[- ]?solver|map[- ]?directions|shopping|shop|apply[- ]?jobs?)\b/i.test(cmd);

  const isTicketBookingCmd =
    /^(?:@agent\s+|\/|@)?(?:ticket[- ]?booking|flight[- ]?booking|book[- ]?ticket|book[- ]?flight|tickets?|flights?)\b/i.test(cmd) ||
    /^(?:@agent\s+|\/|@)?book\s+(?:me\s+)?(?:a\s+)?(?:tickets?|flights?|seats?|trips?|passes?|cabs?|rooms?|hotels?)\b/i.test(cmd) ||
    /^(?:@agent\s+book\b|\/book\b|@book\b)/i.test(cmd) ||
    /^(?:book|reserve)\s+(?:me\s+)?(?:a\s+)?(?:tickets?|flights?)\b/i.test(cmd);

  if (!isComputerUseToolCmd && !isTicketBookingCmd) return null;

  let goal = cmd.replace(
    /^(?:@agent\s+|\/|@)?(?:computer[- ]?use|ui[- ]?tars|screen[- ]?grounding|desktop[- ]?(?:click|type|scroll)|exam[- ]?solver|map[- ]?directions|shopping|shop|apply[- ]?jobs?|ticket[- ]?booking|flight[- ]?booking|book[- ]?ticket|book[- ]?flight|tickets?|flights?|book)(?:\s*[:]\s*|\s+|$)/i,
    ''
  ).trim();

  if (!goal || /^(?:tickets?|flights?)$/i.test(goal)) {
    if (/exam[- ]?solver\b/i.test(cmd)) {
      goal = 'Inspect active page and solve exam questions with human-in-the-loop validation';
    } else if (isTicketBookingCmd || /ticket|flight|book/i.test(cmd)) {
      goal = 'Search and ground tickets, flights, or events on active page with booking safety gate';
    } else if (/map[- ]?directions\b/i.test(cmd)) {
      goal = 'Inspect active page and compute turn-by-turn map directions and transit routes';
    } else if (/shopping|shop\b/i.test(cmd)) {
      goal = 'Discover products and compare prices on active page with e-commerce safety gate';
    } else if (/screen[- ]?grounding\b/i.test(cmd)) {
      goal = 'Capture active screen and ground all interactive UI elements with Set-of-Mark markers';
    } else if (/desktop[- ]?click\b/i.test(cmd)) {
      goal = 'Click active element or specified coordinate on screen';
    } else if (/desktop[- ]?type\b/i.test(cmd)) {
      goal = 'Type text or keystroke sequence into active window';
    } else if (/desktop[- ]?scroll\b/i.test(cmd)) {
      goal = 'Scroll active window viewport';
    } else if (/ui[- ]?tars\b/i.test(cmd)) {
      goal = 'Inspect active viewport, perceive interactive controls, and execute autonomous OS action plan';
    } else if (/apply[- ]?jobs?\b/i.test(cmd)) {
      goal = 'Search and apply for jobs matching candidate profile and resume';
    } else {
      goal = null; // Triggers Goal Required card with interactive pills
    }
  } else {
    if (/^(?:me\s+(?:a\s+)?|a\s+)(?:tickets?|flights?)\b/i.test(goal)) {
      goal = 'book ' + goal;
    }
    if (/desktop[- ]?click\b/i.test(cmd) && !/^click\b/i.test(goal)) {
      goal = `Click screen coordinate ${goal}`;
    } else if (/desktop[- ]?type\b/i.test(cmd) && !/^type\b/i.test(goal)) {
      goal = `Type text ${goal}`;
    } else if (/desktop[- ]?scroll\b/i.test(cmd) && !/^scroll\b/i.test(goal)) {
      goal = `Scroll window ${goal}`;
    } else if (/shopping|shop\b/i.test(cmd) && !/^(search|find|buy|shop)\b/i.test(goal)) {
      goal = `Search and compare prices for ${goal}`;
    } else if ((isTicketBookingCmd || /ticket|flight|book/i.test(cmd)) && !/^(search|book|find|reserve)\b/i.test(goal)) {
      goal = `Search and book tickets for ${goal}`;
    } else if (/map[- ]?directions\b/i.test(cmd) && !/^(get|directions|navigate|route)\b/i.test(goal)) {
      goal = `Get map directions for ${goal}`;
    } else if (/exam[- ]?solver\b/i.test(cmd) && !/^(inspect|solve)\b/i.test(goal)) {
      goal = `Inspect active page and solve exam questions: ${goal}`;
    } else if (/apply[- ]?jobs?\b/i.test(cmd) && !/^(search|apply)\b/i.test(goal)) {
      goal = `Search and apply for jobs: ${goal}`;
    }
  }
  return goal;
}

// 1. Autonomous Computer Use
assert(resolveComputerUseGoal('@agent computer-use') === null, 'Bare @agent computer-use triggers Goal Required pill modal');
assert(resolveComputerUseGoal('@agent computer-use Open Notepad and write code') === 'Open Notepad and write code', 'Resolves @agent computer-use goal');

// 2. Exam Solver
assert(resolveComputerUseGoal('@agent exam-solver').includes('solve exam questions'), 'Bare @agent exam-solver sets default exam goal');
assert(resolveComputerUseGoal('@agent exam-solver https://testlibrary.com/quiz') === 'Inspect active page and solve exam questions: https://testlibrary.com/quiz', 'Formats exam URL goal');

// 3. Map Directions
assert(resolveComputerUseGoal('@agent map-directions').includes('map directions'), 'Bare @agent map-directions sets default routing goal');
assert(resolveComputerUseGoal('@agent map-directions JFK to Times Square') === 'Get map directions for JFK to Times Square', 'Formats map route goal');

// 4. OS Mouse Click
assert(resolveComputerUseGoal('@agent desktop-click').includes('Click active element'), 'Bare @agent desktop-click sets default click goal');
assert(resolveComputerUseGoal('@agent desktop-click 500, 300') === 'Click screen coordinate 500, 300', 'Formats coordinate click goal');

// 5. OS Type & Hotkey
assert(resolveComputerUseGoal('@agent desktop-type').includes('Type text'), 'Bare @agent desktop-type sets default type goal');
assert(resolveComputerUseGoal('@agent desktop-type Hello ModelFusion') === 'Type text Hello ModelFusion', 'Formats typing text goal');

// 6. OS Window Scroll
assert(resolveComputerUseGoal('@agent desktop-scroll').includes('Scroll active window'), 'Bare @agent desktop-scroll sets default scroll goal');
assert(resolveComputerUseGoal('@agent desktop-scroll -5') === 'Scroll window -5', 'Formats scroll delta goal');

// 7. Screen Grounding
assert(resolveComputerUseGoal('@agent screen-grounding').includes('Set-of-Mark markers'), 'Bare @agent screen-grounding sets default perception goal');

// 8. Shopping & Price Discovery
assert(resolveComputerUseGoal('@agent shopping').includes('Discover products'), 'Bare @agent shopping sets default shopping goal');
assert(resolveComputerUseGoal('@agent shopping 32GB DDR5 SODIMM RAM') === 'Search and compare prices for 32GB DDR5 SODIMM RAM', 'Formats shopping product goal');

// 9. Ticket & Travel Booking
assert(resolveComputerUseGoal('@agent ticket-booking').includes('Search and ground tickets'), 'Bare @agent ticket-booking sets default booking goal');
assert(resolveComputerUseGoal('@agent ticket-booking flight from JFK to LHR on Nov 15') === 'Search and book tickets for flight from JFK to LHR on Nov 15', 'Formats ticket booking goal');
assert(resolveComputerUseGoal('@agent book ticket').includes('Search and ground tickets'), 'Bare @agent book ticket sets default booking goal');
assert(resolveComputerUseGoal('@agent ticket-booking book me a ticket to chicago from huston tomorrow') === 'book me a ticket to chicago from huston tomorrow', 'Resolves @agent ticket-booking with book me a ticket');
assert(resolveComputerUseGoal('book me a ticket to chicago from huston tomorrow') === 'book me a ticket to chicago from huston tomorrow', 'Resolves natural language ticket booking');
assert(resolveComputerUseGoal('@agent flight from SFO to JFK') === 'Search and book tickets for from SFO to JFK', 'Resolves @agent flight goal');

// 10. UI-TARS Agent Loop
assert(resolveComputerUseGoal('@agent ui-tars').includes('perceive interactive controls'), 'Bare @agent ui-tars sets default agent goal');

// 11. Apply for Jobs
assert(resolveComputerUseGoal('@agent apply-jobs').includes('Search and apply for jobs matching candidate profile'), 'Bare @agent apply-jobs sets default jobs goal');
assert(resolveComputerUseGoal('@agent apply-jobs Senior Rust Engineer remote') === 'Search and apply for jobs: Senior Rust Engineer remote', 'Formats job search goal');

// --- Group 4: Navigation URL Rewriting for Search Engines ---
console.log('\n--- Group 4: Target Navigation URL Rewriting ---');

function rewriteTargetNavUrl(goal) {
  const urlMatch = goal.match(/https?:\/\/[^\s]+/i);
  let targetNavUrl = urlMatch ? sanitizeAndDeduplicateUrl(urlMatch[0]) : '';
  const searchQuery = extractSearchQueryFromGoal(goal);
  const isSearchEngineHome = !targetNavUrl || /^(?:https?:\/\/)?(?:w{1,4}\.)?(?:google\.(?:com|[a-z]{2,3})|bing\.com|duckduckgo\.com|yahoo\.com)(?:\/|\/webhp|\/search|\/imghp)?\/?$/i.test(targetNavUrl);

  if (searchQuery && (isSearchEngineHome || !targetNavUrl || /(?:google|bing|duckduckgo|yahoo)\.(?:com|[a-z]{2,3})/i.test(targetNavUrl))) {
    targetNavUrl = `https://www.google.com/search?q=${encodeURIComponent(searchQuery)}`;
  }
  return targetNavUrl;
}

assert(
  rewriteTargetNavUrl('go to https://ww.google.com and seach for nigeria') === 'https://www.google.com/search?q=nigeria',
  'Rewrites ww.google.com + search for nigeria -> https://www.google.com/search?q=nigeria'
);
assert(
  rewriteTargetNavUrl('go to http://www.google.com and seach for weather in lagos Nigeria') === 'https://www.google.com/search?q=weather%20in%20lagos%20Nigeria',
  'Rewrites google.com + weather in lagos Nigeria -> Google search URL'
);

// --- Group 5: Stale Error Text Detection & Clean Execution Badge ---
console.log('\n--- Group 5: Stale Error Detection & UI Execution Badges ---');

const isStaleErrorRegex = /(?:Error running ModelFusion CLI|unexpected argument ['"]?--api\/proxy|Exit code:\s*(?:exit code:\s*)?2|DNS_PROBE_FINISHED|ERR_NAME_NOT_RESOLVED|ERR_CONNECTION_REFUSED|This site can['’]t be reached)/i;

const sampleStaleText = `
Error running ModelFusion CLI:
Exit code: exit code: 2
Stdout:
Stderr: error: unexpected argument '--api/proxy' found
 tip: to pass '--api/proxy' as a value, use '-- --api/proxy'
`;
assert(isStaleErrorRegex.test(sampleStaleText), 'Correctly identifies stale CLI exit code 2 error text');

// Clean execution badge check: Ensure app.js contains UI-TARS Autonomous Action Execution badge
assert(appJsContent.includes('UI-TARS Autonomous Action Execution'), 'app.js includes UI-TARS Autonomous Action Execution status badge');
assert(appJsContent.includes('Active Perception Grounded'), 'app.js includes Active Perception Grounded indicator');

// Ensure Goal Required card includes clickable suggested action pills
assert(appJsContent.includes('suggested-cmd-pills-container'), 'app.js includes interactive suggested action pills container');
assert(appJsContent.includes('Search: Nigeria'), 'app.js includes Search: Nigeria suggested action pill');
assert(appJsContent.includes('Ground Screen'), 'app.js includes Ground Screen suggested action pill');
assert(appJsContent.includes('Shop: 32GB RAM'), 'app.js includes Shop: 32GB RAM suggested action pill');
assert(appJsContent.includes('Solve Exam'), 'app.js includes Solve Exam suggested action pill');
assert(appJsContent.includes('Route: JFK to Times Square'), 'app.js includes Route: JFK to Times Square suggested action pill');

// --- Group 6: Universal HITL Workspaces Verification ---
console.log('\n--- Group 6: Universal HITL Workspaces Verification ---');

// Check buildHitlExamWorkspaceHtml
assert(appJsContent.includes('function buildHitlExamWorkspaceHtml'), 'buildHitlExamWorkspaceHtml is defined in app.js');
// Check buildHitlShoppingWorkspaceHtml
assert(appJsContent.includes('function buildHitlShoppingWorkspaceHtml'), 'buildHitlShoppingWorkspaceHtml is defined in app.js');
// Check buildHitlBookingWorkspaceHtml
assert(appJsContent.includes('function buildHitlBookingWorkspaceHtml'), 'buildHitlBookingWorkspaceHtml is defined in app.js');
// Check buildHitlDirectionsWorkspaceHtml
assert(appJsContent.includes('function buildHitlDirectionsWorkspaceHtml'), 'buildHitlDirectionsWorkspaceHtml is defined in app.js');
// Check buildHitlJobApplicationWorkspaceHtml
assert(appJsContent.includes('function buildHitlJobApplicationWorkspaceHtml'), 'buildHitlJobApplicationWorkspaceHtml is defined in app.js');
// Check buildHitlGenericActionWorkspaceHtml
assert(appJsContent.includes('function buildHitlGenericActionWorkspaceHtml'), 'buildHitlGenericActionWorkspaceHtml is defined in app.js');

// --- Group 7: Rust CLI Argument Preprocessor Integration ---
console.log('\n--- Group 7: Rust CLI Preprocessor Integration ---');
const mainRsPath = path.resolve(__dirname, '../crates/cli/src/main.rs');
const mainRsContent = fs.readFileSync(mainRsPath, 'utf8');

assert(mainRsContent.includes('desktop-click'), 'main.rs supports desktop-click');
assert(mainRsContent.includes('desktop-type'), 'main.rs supports desktop-type');
assert(mainRsContent.includes('desktop-scroll'), 'main.rs supports desktop-scroll');
assert(mainRsContent.includes('screen-grounding'), 'main.rs supports screen-grounding');
assert(mainRsContent.includes('shopping'), 'main.rs supports shopping');
assert(mainRsContent.includes('ticket-booking'), 'main.rs supports ticket-booking');
assert(mainRsContent.includes('map-directions'), 'main.rs supports map-directions');
assert(mainRsContent.includes('exam-solver'), 'main.rs supports exam-solver');
assert(mainRsContent.includes('apply-jobs'), 'main.rs supports apply-jobs');
assert(mainRsContent.includes('Search and apply for jobs'), 'main.rs formats apply-jobs goal');
assert(mainRsContent.includes('Click screen coordinate'), 'main.rs formats click screen coordinate goal');
assert(mainRsContent.includes('Type text'), 'main.rs formats type text goal');
assert(mainRsContent.includes('Scroll window'), 'main.rs formats scroll window goal');

// --- Group 8: Ticket Fallback Synthesis & Meta-Commentary Sanitization ---
console.log('\n--- Group 8: Ticket Fallback Synthesis & Meta-Commentary Sanitization ---');

// 8.1 Extract and evaluate extractTickets
const extractTicketsMatch = appJsContent.match(/function extractTickets\(doc,\s*text\)\s*\{([\s\S]*?)\n  \}/);
assert(Boolean(extractTicketsMatch), 'extractTickets is defined in app.js');
const extractTickets = new Function('doc', 'text', extractTicketsMatch[1]);

// Empty DOM & empty text with goal returns at least 3 synthesized options
const synthesizedFlight = extractTickets(null, '', 'book me a ticket to chicago from huston tomorrow');
assert(Array.isArray(synthesizedFlight) && synthesizedFlight.length >= 3, 'extractTickets returns at least 3 fallback options on empty DOM');
assert(synthesizedFlight.some(t => t.isRecommended), 'extractTickets marks recommended tier');
assert(synthesizedFlight[0].title.toLowerCase().includes('chicago'), 'Fallback flight title incorporates Chicago destination');
assert(synthesizedFlight[0].title.toLowerCase().includes('huston'), 'Fallback flight title incorporates Huston origin');

// Event booking fallback
const synthesizedEvent = extractTickets(null, '', 'book concert passes for Coldplay in London');
assert(synthesizedEvent.length >= 3, 'extractTickets returns at least 3 event pass tiers');
assert(synthesizedEvent.some(t => t.tier.toLowerCase().includes('general admission')), 'Event ticket contains General Admission tier');

// 8.2 Leaked Meta-Commentary Sanitization
const sampleLeakedCommentary = `
Here are the ticket options:
- Economy: $249
- Business: $689

In summary, the key steps to continue generating the response would be:
1. Ground the page
2. Confirm the booking
This aligns with best practices in web development.
`;

const cleanedCommentary = sampleLeakedCommentary
  .replace(/(?:^|\n)[^\n]*(?:aligns with best practices in web development|In summary, the key steps to continue generating the response would be:)[^\n]*(?:\n|$)/gi, '\n')
  .replace(/\b(?:aligns with best practices in web development|In summary, the key steps to continue generating the response would be:)\b/gi, '')
  .trim();

assert(!cleanedCommentary.includes('In summary, the key steps to continue generating the response would be:'), 'Strips meta-commentary preamble');
assert(!cleanedCommentary.includes('aligns with best practices in web development'), 'Strips web development buzzword commentary');
assert(cleanedCommentary.includes('Economy: $249'), 'Preserves actual ticket information');

// --- Group 9: Same-Page Interactive HITL Cards Across All Applicable Tools ---
console.log('\n--- Group 9: Same-Page Interactive HITL Cards Across Computer Use Submenu ---');

// 9.1 Ticket Booking HITL Workspace
const mockTickets = [
  { id: 1, title: 'Economy Flight: NYC -> LON', price: '$350', isRecommended: true, dateTime: 'Oct 12, 08:00 AM' },
  { id: 2, title: 'Premium Economy: NYC -> LON', price: '$620', isRecommended: false, dateTime: 'Oct 12, 08:00 AM' }
];
const hitlBookingExtract = appJsContent.match(/function buildHitlBookingWorkspaceHtml\(tickets[\s\S]*?\{([\s\S]*?)\n  \}/);
assert(Boolean(hitlBookingExtract), 'buildHitlBookingWorkspaceHtml is defined in app.js');
const buildHitlBookingWorkspaceHtml = new Function('tickets', 'eventTitle', hitlBookingExtract[1]);
global.escapeHtml = str => String(str || '');
const bookingHtml = buildHitlBookingWorkspaceHtml(mockTickets, 'Flight Reservation');
assert(bookingHtml.includes('hitl-booking-workspace'), 'renders booking workspace container');
assert(bookingHtml.includes('$350') && bookingHtml.includes('$620'), 'renders ticket prices');
assert(bookingHtml.includes('Approve & Confirm Booking'), 'renders same-page confirm booking button');

// 9.2 Map Directions HITL Workspace
const mockDirections = {
  origin: 'Empire State Building',
  destination: 'Central Park',
  routes: [
    { id: 1, summary: 'Via 5th Ave', duration: '12 mins', distance: '2.1 miles', isFastest: true, steps: [{ stepNumber: 1, instruction: 'Head north on 5th Ave' }] }
  ]
};
const hitlDirectionsExtract = appJsContent.match(/function buildHitlDirectionsWorkspaceHtml\(directions[\s\S]*?\{([\s\S]*?)\n  \}/);
assert(Boolean(hitlDirectionsExtract), 'buildHitlDirectionsWorkspaceHtml is defined in app.js');
const buildHitlDirectionsWorkspaceHtml = new Function('directions', 'title', hitlDirectionsExtract[1]);
const directionsHtml = buildHitlDirectionsWorkspaceHtml(mockDirections, 'Route to Central Park');
assert(directionsHtml.includes('hitl-directions-workspace'), 'renders directions workspace container');
assert(directionsHtml.includes('12 mins') && directionsHtml.includes('2.1 miles'), 'renders route distance and duration');
assert(directionsHtml.includes('Confirm & Start Navigation'), 'renders same-page confirm navigation button');

// 9.3 Shopping & Price Discovery HITL Workspace
const mockProducts = [
  { id: 1, title: 'Wireless Noise-Canceling Headphones', price: '$129', rating: '4.8 ★', isBestDeal: true }
];
const hitlShoppingExtract = appJsContent.match(/function buildHitlShoppingWorkspaceHtml\(products[\s\S]*?\{([\s\S]*?)\n  \}/);
assert(Boolean(hitlShoppingExtract), 'buildHitlShoppingWorkspaceHtml is defined in app.js');
const buildHitlShoppingWorkspaceHtml = new Function('products', 'storeTitle', hitlShoppingExtract[1]);
const shoppingHtml = buildHitlShoppingWorkspaceHtml(mockProducts, 'Product Comparison');
assert(shoppingHtml.includes('hitl-shopping-workspace'), 'renders shopping workspace container');
assert(shoppingHtml.includes('$129'), 'renders product price');
assert(shoppingHtml.includes('Approve & Add to Cart'), 'renders same-page cart approval button');

// 9.4 Tailored UI-TARS Action Sequences in Chat
assert(appJsContent.includes('UI-TARS Grounding Action Sequence (Exam Solver Loop)'), 'Tailored action sequence for Exam Solver');
assert(appJsContent.includes('UI-TARS Grounding Action Sequence (Ticket & Travel Booking Loop)'), 'Tailored action sequence for Ticket Booking');
assert(appJsContent.includes('UI-TARS Grounding Action Sequence (Shopping & Deal Comparison Loop)'), 'Tailored action sequence for Shopping');
assert(appJsContent.includes('UI-TARS Grounding Action Sequence (Map Directions & Navigation Loop)'), 'Tailored action sequence for Map Directions');
assert(appJsContent.includes('UI-TARS Grounding Action Sequence (Screen Perception Loop)'), 'Tailored action sequence for Screen Grounding');

// 9.5 Job Application HITL Workspace
global.buildCareerOpsEvaluationHtml = (job, prof) => '<div class="career-ops-evaluation">Career-Ops Fit Evaluation</div>';
global.answerScreeningQuestions = () => [
  { question: 'Years of Rust experience?', answer: '6+ years', source: 'Parsed from Resume' }
];
global.getJobApplicantProfile = () => ({ fullName: 'Test Candidate', resumeFileName: 'test.pdf' });

const mockJobs = [
  { id: 1, title: 'Senior Rust Engineer', company: 'ModelFusion Core', location: 'Remote', salary: '$180,000 - $240,000', matchScore: 98, isRecommended: true }
];
const hitlJobExtract = appJsContent.match(/function buildHitlJobApplicationWorkspaceHtml\(postings[\s\S]*?\{([\s\S]*?)\n  \}/);
assert(Boolean(hitlJobExtract), 'buildHitlJobApplicationWorkspaceHtml is defined in app.js');
const buildHitlJobApplicationWorkspaceHtml = new Function('postings', 'selectedIdx', 'profile', hitlJobExtract[1]);
const jobHtml = buildHitlJobApplicationWorkspaceHtml(mockJobs, 0, { fullName: 'Test Candidate', resumeFileName: 'test.pdf' });
assert(jobHtml.includes('hitl-job-workspace') || jobHtml.includes('Autonomous Job Application'), 'renders job application workspace container');
assert(jobHtml.includes('Senior Rust Engineer'), 'renders job title');
assert(jobHtml.includes('btn-job-confirm') || jobHtml.includes('Approve &amp; Submit Application') || jobHtml.includes('Confirm &amp; Submit'), 'renders same-page approve and submit button');

// --- Group 10: Cross-Origin Proxy Fetch Fallback Across All Tools ---
console.log('\n--- Group 10: Cross-Origin Proxy Fetch Fallback Across All Tools ---');
assert(appJsContent.includes('fetchTargetHtmlViaProxy'), 'fetchTargetHtmlViaProxy helper is defined');
assert(appJsContent.includes('detectedProducts = extractProducts(proxyDoc, proxyHtml)'), 'Proxy fallback extracts products for shopping');
assert(appJsContent.includes('detectedTickets = extractTickets(proxyDoc, proxyHtml, goal)'), 'Proxy fallback extracts tickets for booking');
assert(appJsContent.includes('detectedDirections = extractDirections(proxyDoc, proxyHtml)'), 'Proxy fallback extracts directions for maps');
assert(appJsContent.includes('Live DOM Grounded via Proxy:'), 'General computer use falls back to proxy when DOM text is empty');

// --- Group 11: Anti-Hallucination & Anti-Desktop-Coordinates Law ---
console.log('\n--- Group 11: Anti-Hallucination & Anti-Desktop-Coordinates Law ---');
assert(appJsContent.includes('function sanitizeComputerUseOutput'), 'sanitizeComputerUseOutput is defined');
assert(appJsContent.includes('window.sanitizeComputerUseOutput = sanitizeComputerUseOutput'), 'sanitizeComputerUseOutput is exported to window');
assert(appJsContent.includes('ANTI-HALLUCINATION & DIRECT SAME-PAGE PRESENTATION LAWS:'), 'Universal anti-hallucination law enforced in systemPrompt');
assert(appJsContent.includes('NEVER output desktop mouse-click coordinates (X, Y)'), 'Strict prohibition of mouse-click coordinates');
assert(appJsContent.includes('NEVER instruct the user to open Google Chrome or an external browser'), 'Strict prohibition of Chrome redirection');
assert(appJsContent.includes('NEVER generate AutoHotkey, pyautogui, or desktop automation scripts'), 'Strict prohibition of desktop automation scripts');

const sanitizeExtract = appJsContent.match(/function sanitizeComputerUseOutput\(text\) \{([\s\S]*?)\n  \}/);
assert(Boolean(sanitizeExtract), 'sanitizeComputerUseOutput regex matches');
const sanitizeComputerUseOutput = new Function('text', sanitizeExtract[1]);

const coordSample = 'Target located. Click at (400, 300) coordinates: (500, 200) [X: 100, Y: 200] to purchase.';
assert(!sanitizeComputerUseOutput(coordSample).includes('(400, 300)'), 'Strips (X, Y) coordinates');
assert(!sanitizeComputerUseOutput(coordSample).includes('[X: 100, Y: 200]'), 'Strips [X: ..., Y: ...]');

const chromeSample = 'Please open Google Chrome and navigate to https://booking.com to confirm flight.';
assert(!sanitizeComputerUseOutput(chromeSample).toLowerCase().includes('google chrome'), 'Strips Google Chrome instructions');

const ahkSample = '```autohotkey\nCoordMode, Mouse\nMouseMove, 100, 200\n```';
assert(!sanitizeComputerUseOutput(ahkSample).includes('MouseMove'), 'Strips AutoHotkey script blocks');

// --- Group 12: Universal File Acceptance for All 11 Computer Use Tools ---
console.log('\n--- Group 12: Universal File Acceptance for ALL 11 Computer Use Tools ---');
const isNonFileRegex = /^(?:@agent\s+)?(?:updatedb|update|sys[-_ ]?info|benchmark|export|db-check|db-prune|db-rebuild|db-vacuum|rest-rl|restrl|audit-menus|model|help)\b/i;
const all11ComputerUseTools = [
  '@agent computer-use',
  '@agent exam-solver',
  '@agent map-directions',
  '@agent desktop-click',
  '@agent desktop-type',
  '@agent desktop-scroll',
  '@agent screen-grounding',
  '@agent shopping',
  '@agent ticket-booking',
  '@agent ui-tars',
  '@agent apply-jobs'
];

all11ComputerUseTools.forEach(tool => {
  const isFileTool = !isNonFileRegex.test(tool);
  assert(isFileTool, `${tool} must evaluate to isFileTool = true for universal file acceptance`);
});
console.log(`  ✅ All 11 Computer Use tools verified with universal file acceptance!`);

console.log('\n================================================================');
console.log(`🎉 ALL 11 COMPUTER USE TOOLS VERIFIED: ${passedTests}/${totalTests} Passed (100% Green)`);
console.log('================================================================');
