// HugOS Browser Extension Content Script
// Set-of-Mark (SoM) Visual Bounding Box Injector, DOM Tree Pruner, and Table Parser

(function () {
  let somOverlayContainer = null;
  let somElements = [];
  let isSomVisible = false;

  // 1. Set-of-Mark (SoM) Visual Badge Injector
  function injectSetOfMarks() {
    clearSetOfMarks();

    somOverlayContainer = document.createElement('div');
    somOverlayContainer.id = 'hugos-som-overlay-root';
    somOverlayContainer.style.position = 'absolute';
    somOverlayContainer.style.top = '0';
    somOverlayContainer.style.left = '0';
    somOverlayContainer.style.width = '100%';
    somOverlayContainer.style.height = document.documentElement.scrollHeight + 'px';
    somOverlayContainer.style.pointerEvents = 'none';
    somOverlayContainer.style.zIndex = '2147483647';
    document.body.appendChild(somOverlayContainer);

    const selector = 'a[href], button, input, select, textarea, [role="button"], [role="link"], [role="checkbox"], [onclick], [tabindex]:not([tabindex="-1"])';
    const rawElements = Array.from(document.querySelectorAll(selector));

    somElements = [];
    let markId = 1;

    for (const el of rawElements) {
      const rect = el.getBoundingClientRect();
      const style = window.getComputedStyle(el);

      // Filter non-visible elements
      if (rect.width <= 0 || rect.height <= 0 || style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
        continue;
      }

      el.setAttribute('data-hugos-mark-id', markId.toString());

      // Create visual badge overlay
      const badge = document.createElement('div');
      badge.className = 'hugos-som-badge';
      badge.textContent = markId.toString();
      badge.style.position = 'absolute';
      badge.style.top = (rect.top + window.scrollY - 8) + 'px';
      badge.style.left = (rect.left + window.scrollX - 4) + 'px';
      badge.style.backgroundColor = '#6366f1';
      badge.style.color = '#ffffff';
      badge.style.fontSize = '11px';
      badge.style.fontFamily = 'monospace';
      badge.style.fontWeight = 'bold';
      badge.style.padding = '1px 5px';
      badge.style.borderRadius = '4px';
      badge.style.boxShadow = '0 2px 4px rgba(0,0,0,0.5)';
      badge.style.border = '1px solid #ffffff';
      badge.style.zIndex = '2147483647';
      badge.style.pointerEvents = 'none';

      // Outline box around target element
      const outline = document.createElement('div');
      outline.style.position = 'absolute';
      outline.style.top = (rect.top + window.scrollY) + 'px';
      outline.style.left = (rect.left + window.scrollX) + 'px';
      outline.style.width = rect.width + 'px';
      outline.style.height = rect.height + 'px';
      outline.style.border = '2px solid rgba(99, 102, 241, 0.7)';
      outline.style.boxSizing = 'border-box';
      outline.style.pointerEvents = 'none';

      somOverlayContainer.appendChild(outline);
      somOverlayContainer.appendChild(badge);

      somElements.push({
        id: markId,
        tag: el.tagName.toLowerCase(),
        text: (el.innerText || el.value || el.placeholder || el.getAttribute('aria-label') || '').trim().slice(0, 80),
        rect: {
          x: Math.round(rect.x),
          y: Math.round(rect.y),
          width: Math.round(rect.width),
          height: Math.round(rect.height)
        }
      });

      markId++;
      if (markId > 300) break; // Maximum marks ceiling
    }

    isSomVisible = true;
    return somElements;
  }

  function clearSetOfMarks() {
    if (somOverlayContainer && somOverlayContainer.parentNode) {
      somOverlayContainer.parentNode.removeChild(somOverlayContainer);
      somOverlayContainer = null;
    }
    const marked = document.querySelectorAll('[data-hugos-mark-id]');
    for (const el of marked) {
      el.removeAttribute('data-hugos-mark-id');
    }
    somElements = [];
    isSomVisible = false;
  }

  // 2. Table and Grid Extractor
  function extractTables() {
    const tables = [];
    const htmlTables = Array.from(document.querySelectorAll('table'));

    let idCounter = 1;
    for (const table of htmlTables) {
      const captionEl = table.querySelector('caption');
      const caption = captionEl ? captionEl.innerText.trim() : null;

      const headerEls = Array.from(table.querySelectorAll('th'));
      let headers = [];
      if (headerEls.length > 0) {
        headers = headerEls.map(th => th.innerText.trim());
      }

      const rows = [];
      const trEls = Array.from(table.querySelectorAll('tbody tr, tr:not(:first-child)'));
      for (const tr of trEls) {
        const cells = Array.from(tr.querySelectorAll('td, th')).map(td => td.innerText.trim());
        if (cells.length > 0) {
          rows.push(cells);
        }
      }

      if (headers.length === 0 && rows.length > 0) {
        headers = rows[0].map((_, i) => `Col_${i + 1}`);
      }

      if (rows.length > 0) {
        tables.push({
          id: idCounter++,
          caption: caption || `Table #${idCounter - 1}`,
          headers,
          rows,
          rowCount: rows.length,
          colCount: headers.length
        });
      }
    }

    return tables;
  }

  // 3. Clean Pruned Semantic DOM
  function getPrunedDom() {
    // Clone body and strip non-semantic elements
    const clone = document.body.cloneNode(true);
    const stripSelectors = 'script, style, svg, noscript, iframe, meta, link, #hugos-som-overlay-root';
    const nonContent = clone.querySelectorAll(stripSelectors);
    for (const el of nonContent) {
      el.parentNode.removeChild(el);
    }

    const text = clone.innerText
      .replace(/\n{3,}/g, '\n\n')
      .replace(/[ \t]{2,}/g, ' ')
      .trim();

    return {
      title: document.title,
      url: window.location.href,
      text: text.slice(0, 50000),
      originalLength: document.documentElement.outerHTML.length,
      prunedLength: text.length
    };
  }

  // 4. Message Dispatcher
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'toggle_som') {
      if (isSomVisible) {
        clearSetOfMarks();
        sendResponse({ status: 'cleared', count: 0 });
      } else {
        const elements = injectSetOfMarks();
        sendResponse({ status: 'injected', count: elements.length, elements });
      }
      return true;
    }

    if (request.action === 'get_som_elements') {
      if (!isSomVisible) {
        injectSetOfMarks();
      }
      sendResponse({ elements: somElements });
      return true;
    }

    if (request.action === 'extract_tables') {
      const tables = extractTables();
      sendResponse({ tables });
      return true;
    }

    if (request.action === 'get_pruned_dom') {
      const pruned = getPrunedDom();
      sendResponse({ pruned });
      return true;
    }

    if (request.action === 'click_mark') {
      const target = document.querySelector(`[data-hugos-mark-id="${request.markId}"]`);
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
        target.click();
        sendResponse({ success: true, markId: request.markId });
      } else {
        sendResponse({ success: false, error: `Mark [${request.markId}] not found.` });
      }
      return true;
    }
  });
})();
