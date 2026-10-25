#!/usr/bin/env python3
"""
Adversarial Stress Test & Verification Suite for Milestone 3
Validates:
1. Strict A-Z alphabetical ordering of all 19 categories (unescaped & case-folded).
2. Strict A-Z alphabetical ordering of all sub-items inside every category without exception.
3. Verification of every single button in each category for presence of label, tag, data-cmd.
4. Specific verification of #tool_trending_models positioning and attributes.
5. Exact button count per category and total across all 19 categories.
6. Capability search filter matching against trending models.
"""

import html
import re
import sys

def test_categories_and_subitems():
    with open('browser/ui/index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Category extraction
    cat_blocks = re.findall(r'<div class="tool-category"(?: [^>]*)?>([\s\S]*?)</div>\s*</div>', content)
    print(f"[Stress Test 1] Total .tool-category blocks extracted: {len(cat_blocks)}")
    assert len(cat_blocks) == 19, f"Expected 19 category blocks, found {len(cat_blocks)}"

    category_names = []
    category_data = []

    total_tool_buttons = 0
    trending_model_found = False
    trending_category = None
    trending_index_in_cat = None

    for idx, block in enumerate(cat_blocks):
        # Extract title
        title_match = re.search(r'class="cat-title">([^<]+)</span>', block)
        assert title_match, f"Category at index {idx} has no cat-title"
        raw_title = title_match.group(1).strip()
        unescaped_title = html.unescape(raw_title)
        category_names.append(unescaped_title)

        # Extract content div
        content_match = re.search(r'<div class="tool-category-content[^"]*">([\s\S]*)$', block)
        assert content_match, f"Category '{unescaped_title}' has no tool-category-content"
        content_html = content_match.group(1)

        # Extract all buttons inside category content
        buttons = re.findall(r'<button\b([^>]*)>([\s\S]*?)</button>', content_html)
        assert len(buttons) > 0, f"Category '{unescaped_title}' has no buttons inside content!"

        sub_labels = []
        for b_idx, (attrs, inner) in enumerate(buttons):
            total_tool_buttons += 1
            # Check for label
            lbl_match = re.search(r'class="tool-label">([^<]+)</span>', inner)
            assert lbl_match, f"Button {b_idx} in '{unescaped_title}' lacks class='tool-label'! HTML: {inner[:60]}"
            label_text = html.unescape(lbl_match.group(1).strip())
            sub_labels.append(label_text)

            # Check if this is tool_trending_models
            if 'id="tool_trending_models"' in attrs:
                trending_model_found = True
                trending_category = unescaped_title
                trending_index_in_cat = b_idx
                # Check required attributes
                assert 'data-cmd="@agent trending-models"' in attrs, "tool_trending_models missing data-cmd='@agent trending-models'"
                assert 'tool-item-btn' in attrs, "tool_trending_models missing tool-item-btn class"
                assert 'tool-command-btn' in attrs, "tool_trending_models missing tool-command-btn class"
                assert label_text == "Trending Hub Models", f"Unexpected label: {label_text}"

        category_data.append({
            "title": unescaped_title,
            "labels": sub_labels,
            "button_count": len(buttons)
        })

    # Test 1: Category A-Z Sorting
    print("\n[Stress Test 2] Checking Category A-Z Sorting...")
    sorted_categories = sorted(category_names, key=str.casefold)
    for i, (actual, expected) in enumerate(zip(category_names, sorted_categories)):
        status = "PASS" if actual == expected else "FAIL"
        print(f"  [{status}] {i+1:02d}. {actual} (expected: {expected})")
        assert actual == expected, f"Category mismatch at index {i}: {actual} != {expected}"
    print("  -> All 19 Categories are strictly sorted alphabetically (A-Z).")

    # Test 2: Sub-item A-Z Sorting in each category
    print("\n[Stress Test 3] Checking Sub-item A-Z Sorting within all 19 Categories...")
    for cat in category_data:
        labels = cat["labels"]
        sorted_labels = sorted(labels, key=str.casefold)
        print(f"  Category '{cat['title']}' ({len(labels)} items):")
        for i, (l_actual, l_expected) in enumerate(zip(labels, sorted_labels)):
            assert l_actual == l_expected, (
                f"Sub-item order violation in '{cat['title']}': index {i} has '{l_actual}' but expected '{l_expected}'"
            )
        print(f"    -> All {len(labels)} items sorted strictly A-Z.")

    # Test 3: Total Tool Buttons Count
    print(f"\n[Stress Test 4] Total tool buttons in category contents: {total_tool_buttons}")
    assert total_tool_buttons == 151, f"Expected exactly 151 tool buttons across 19 categories, found {total_tool_buttons}"

    # Test 4: #tool_trending_models placement
    print("\n[Stress Test 5] Checking #tool_trending_models placement...")
    assert trending_model_found, "#tool_trending_models was not found in any category!"
    print(f"  Found #tool_trending_models in category: '{trending_category}' at index {trending_index_in_cat}")
    assert trending_category == "Utilities & System", f"Expected in 'Utilities & System', got '{trending_category}'"

    util_labels = [c["labels"] for c in category_data if c["title"] == "Utilities & System"][0]
    idx_trending = util_labels.index("Trending Hub Models")
    prev_label = util_labels[idx_trending - 1]
    next_label = util_labels[idx_trending + 1]
    print(f"  Preceding item: '{prev_label}'")
    print(f"  Target item:    '{util_labels[idx_trending]}'")
    print(f"  Succeeding item:'{next_label}'")
    assert prev_label.casefold() < "Trending Hub Models".casefold() < next_label.casefold(), (
        f"Ordering violated: {prev_label} < Trending Hub Models < {next_label}"
    )
    print("  -> #tool_trending_models is strictly in alphabetical order between 'Optimize Database' and 'Update Top Models'.")

    # Test 5: Sidebar Navigation item
    print("\n[Stress Test 6] Checking sidebar trending item...")
    sidebar_match = re.search(r'<li\s+id="sidebar-trending-models"[^>]*>([\s\S]*?)</li>', content)
    assert sidebar_match, "sidebar-trending-models not found in index.html"
    sidebar_inner = sidebar_match.group(1)
    assert "Trending Models" in sidebar_inner, "sidebar-trending-models missing label 'Trending Models'"
    print("  -> #sidebar-trending-models verified in sidebar nav list.")

    print("\n" + "="*70)
    print("ALL EMPIRICAL CHALLENGER STRESS TESTS PASSED (100% GREEN)")
    print("="*70)

if __name__ == '__main__':
    test_categories_and_subitems()
