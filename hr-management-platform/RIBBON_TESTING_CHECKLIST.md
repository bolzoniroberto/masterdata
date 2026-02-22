# Ribbon Interface Testing Checklist

**Date**: 2026-02-19
**Tester**: ___________________
**Browser**: ___________________
**OS**: ___________________

---

## ✅ Pre-Test Setup

- [ ] Streamlit server running: `streamlit run app.py`
- [ ] Application accessible: http://localhost:8501
- [ ] Browser console open: F12 → Console tab
- [ ] Database loaded: Upload Excel file or auto-load existing data
- [ ] Cache cleared: Ctrl+Shift+Delete (to ensure fresh load)

---

## 🧪 Test 1: Ribbon Visibility & Layout

**Objective**: Verify ribbon renders correctly at top of page

| # | Action | Expected Result | ✓/✗ | Notes |
|---|--------|-----------------|-----|-------|
| 1.1 | Observe ribbon at top of page | Ribbon visible below top toolbar | | |
| 1.2 | Check ribbon height | ~120px height with padding | | |
| 1.3 | Check ribbon background | Dark gray (#1e293b) | | |
| 1.4 | Check tab bar | 5 tabs visible: Home, Gestione Dati, Organigrammi, Analisi, Versioni | | |
| 1.5 | Check tab height | ~40px height | | |
| 1.6 | Check collapse button | Chevron icon visible (top-right) | | |
| 1.7 | Check QAT (Quick Access) | 5 small icons in top-left (Save, Undo, Redo, Export, Refresh) | | |
| 1.8 | Check account menu | Avatar and name visible in top-right | | |

**Result**: ☐ PASS ☐ FAIL

---

## 🧪 Test 2: Tab Navigation (Home)

**Objective**: Verify Home tab functionality

| # | Action | Expected Result | ✓/✗ | Notes |
|---|--------|-----------------|-----|-------|
| 2.1 | Verify Home tab active | Home tab highlighted in blue/active color | | |
| 2.2 | Check URL | URL shows no `active_ribbon_tab` param (or `=Home`) | | |
| 2.3 | Observe content | Dashboard with KPI cards/widgets visible | | |
| 2.4 | Check Quick Actions group | 4 large command buttons visible (Nuovo Dipendente, Nuova Struttura, Import File, Export DB_TNS) | | |

**Console Output**:
- Should see initial ribbon logs
- NO SecurityError messages

**Result**: ☐ PASS ☐ FAIL

---

## 🧪 Test 3: Tab Navigation (Gestione Dati)

**Objective**: Verify Gestione Dati tab switching

| # | Action | Expected Result | ✓/✗ | Notes |
|---|--------|-----------------|-----|-------|
| 3.1 | Click "Gestione Dati" tab | Tab highlights blue | | |
| 3.2 | Check URL | URL changes to: `?active_ribbon_tab=Gestione%20Dati` | | |
| 3.3 | Check content | Employee master-detail table visible (Personale view) | | |
| 3.4 | Measure response time | Content loads in < 1 second | | |
| 3.5 | Check if full page reload | Page transitions smoothly (no browser refresh icon) | | |

**Console Output**:
```
✓ Ribbon: Updating URL with new tab: Gestione Dati
✓ URL updated: http://localhost:8501?active_ribbon_tab=Gestione%20Dati
✓ Parent Streamlit will read st.query_params and rerun
```

**Result**: ☐ PASS ☐ FAIL

---

## 🧪 Test 4: Tab Navigation (Organigrammi)

**Objective**: Verify Organigrammi tab with org chart views

| # | Action | Expected Result | ✓/✗ | Notes |
|---|--------|-----------------|-----|-------|
| 4.1 | Click "Organigrammi" tab | Tab highlights blue | | |
| 4.2 | Check URL | URL changes to: `?active_ribbon_tab=Organigrammi` | | |
| 4.3 | Check content | Organization chart visualization visible | | |
| 4.4 | Look for layout toggles | 6 layout buttons visible (Tree H, Tree V, Sunburst, Treemap, Panels, Card Grid) | | |
| 4.5 | Verify layout switcher | Can click between different org chart layouts | | |

**Result**: ☐ PASS ☐ FAIL

---

## 🧪 Test 5: Tab Navigation (Analisi)

**Objective**: Verify Analisi tab with search and audit tools

| # | Action | Expected Result | ✓/✗ | Notes |
|---|--------|-----------------|-----|-------|
| 5.1 | Click "Analisi" tab | Tab highlights blue | | |
| 5.2 | Check URL | URL changes to: `?active_ribbon_tab=Analisi` | | |
| 5.3 | Check content | Search view or audit tools visible | | |
| 5.4 | Look for search box | Advanced search input fields visible | | |

**Result**: ☐ PASS ☐ FAIL

---

## 🧪 Test 6: Tab Navigation (Versioni)

**Objective**: Verify Versioni tab with version management

| # | Action | Expected Result | ✓/✗ | Notes |
|---|--------|-----------------|-----|-------|
| 6.1 | Click "Versioni" tab | Tab highlights blue | | |
| 6.2 | Check URL | URL changes to: `?active_ribbon_tab=Versioni` | | |
| 6.3 | Check content | Version management view visible | | |
| 6.4 | Look for snapshot buttons | Snapshot/Checkpoint buttons visible | | |

**Result**: ☐ PASS ☐ FAIL

---

## 🧪 Test 7: Tab Switching (All Tabs Cycle)

**Objective**: Verify smooth tab switching between all tabs

| # | Action | Expected Result | ✓/✗ | Notes |
|---|--------|-----------------|-----|-------|
| 7.1 | Click tab sequence | Home → Gestione Dati → Organigrammi → Analisi → Versioni → Home | | |
| 7.2 | Monitor URL changes | Each click updates URL correctly | | |
| 7.3 | Monitor content changes | Each tab shows different content | | |
| 7.4 | Check for flicker | Transitions smooth, no visual artifacts | | |
| 7.5 | Check performance | Each switch takes < 1 second | | |

**Result**: ☐ PASS ☐ FAIL

---

## 🧪 Test 8: URL Back/Forward Navigation

**Objective**: Verify browser back/forward buttons work with ribbon

| # | Action | Expected Result | ✓/✗ | Notes |
|---|--------|-----------------|-----|-------|
| 8.1 | Navigate tabs as in Test 7 | Create navigation history | | |
| 8.2 | Click browser back button | Previous tab loads (URL updates) | | |
| 8.3 | Click browser back again | Previous-previous tab loads | | |
| 8.4 | Click browser forward button | Next tab loads | | |

**Result**: ☐ PASS ☐ FAIL

---

## 🧪 Test 9: Quick Access Toolbar (QAT)

**Objective**: Verify QAT buttons are functional

| # | Action | Expected Result | ✓/✗ | Notes |
|---|--------|-----------------|-----|-------|
| 9.1 | Hover over Save icon (💾) | Tooltip appears: "Salva snapshot - Ctrl+S" | | |
| 9.2 | Hover over Undo icon (↩️) | Tooltip appears: "Annulla - Ctrl+Z" | | |
| 9.3 | Hover over Redo icon (↪️) | Tooltip appears: "Ripeti - Ctrl+Y" | | |
| 9.4 | Hover over Export icon (📤) | Tooltip appears: "Export DB_TNS - Ctrl+E" | | |
| 9.5 | Hover over Refresh icon (🔄) | Tooltip appears: "Aggiorna dati - F5" | | |
| 9.6 | Click each icon | Icons are clickable (not just visual) | | |

**Result**: ☐ PASS ☐ FAIL

---

## 🧪 Test 10: Search Bar Integration

**Objective**: Verify search bar functionality (if implemented)

| # | Action | Expected Result | ✓/✗ | Notes |
|---|--------|-----------------|-----|-------|
| 10.1 | Locate search bar | Search input visible in ribbon center | | |
| 10.2 | Click search bar | Focus input (cursor visible) | | |
| 10.3 | Type "rossi" | Autocomplete suggestions appear | | |
| 10.4 | Press Ctrl+K | Focus moves to search bar (or opens search) | | |

**Result**: ☐ PASS ☐ FAIL / ☐ N/A (not yet implemented)

---

## 🧪 Test 11: Account Menu

**Objective**: Verify account menu dropdown functionality

| # | Action | Expected Result | ✓/✗ | Notes |
|---|--------|-----------------|-----|-------|
| 11.1 | Click account avatar/name | Dropdown menu opens | | |
| 11.2 | Check menu items | Profile, Settings, Theme, Help, Logout visible | | |
| 11.3 | Hover over menu items | Hover effects visible | | |
| 11.4 | Click Settings | Settings panel opens (or alert shows) | | |
| 11.5 | Click outside menu | Menu closes | | |

**Result**: ☐ PASS ☐ FAIL / ☐ N/A (menu items may be placeholders)

---

## 🧪 Test 12: Collapse/Minimize Ribbon

**Objective**: Verify ribbon collapse functionality

| # | Action | Expected Result | ✓/✗ | Notes |
|---|--------|-----------------|-----|-------|
| 12.1 | Click collapse button (⌃) | Ribbon collapses to ~40px height | | |
| 12.2 | Check visibility | Only tab bar visible, content hidden | | |
| 12.3 | Observe button change | Button icon changes to ⌄ (chevron down) | | |
| 12.4 | Click tab when collapsed | Ribbon expands temporarily | | |
| 12.5 | Press F1 keyboard shortcut | Ribbon toggles collapse state | | |
| 12.6 | Refresh page | Collapse state persists (saved in session) | | |

**Result**: ☐ PASS ☐ FAIL

---

## 🧪 Test 13: Mobile Responsiveness

**Objective**: Verify ribbon transforms to hamburger menu on mobile

**Setup**: Use browser DevTools to simulate mobile (iPhone 12 / 375px width)

| # | Action | Expected Result | ✓/✗ | Notes |
|---|--------|-----------------|-----|-------|
| 13.1 | Open DevTools (F12) | DevTools panel opens | | |
| 13.2 | Toggle Device Toolbar | Ctrl+Shift+M or toggle in DevTools | | |
| 13.3 | Select iPhone 12 | Width = 375px | | |
| 13.4 | Refresh page | Page reloads in mobile view | | |
| 13.5 | Check ribbon hidden | Desktop ribbon not visible | | |
| 13.6 | Check hamburger visible | Hamburger button (☰) visible in top-left | | |
| 13.7 | Click hamburger | Side menu slides in from left | | |
| 13.8 | Check menu structure | Menu items organized in accordion | | |
| 13.9 | Tap menu item | Navigates to that section, menu closes | | |
| 13.10 | Tap outside menu | Menu closes | | |

**Result**: ☐ PASS ☐ FAIL ☐ N/A (mobile not tested)

---

## 🧪 Test 14: Browser Console (Error-Free)

**Objective**: Verify no errors or warnings in browser console

| # | Action | Expected Result | ✓/✗ | Notes |
|---|--------|-----------------|-----|-------|
| 14.1 | Open DevTools (F12) | Console tab visible | | |
| 14.2 | Clear console | Ctrl+L to clear | | |
| 14.3 | Click all ribbon tabs | Perform all navigation tests | | |
| 14.4 | Filter for errors | Set filter to "Error" | | |
| 14.5 | Check error count | 0 errors | | |
| 14.6 | Check SecurityError | NO "SecurityError" messages | | |
| 14.7 | Check iframe errors | NO "Cannot navigate from iframe" errors | | |
| 14.8 | Check CORS errors | NO "CORS" or "blocked" errors | | |

**Acceptable Messages**:
- ✓ "Ribbon: Updating URL with new tab..."
- ✓ "✓ URL updated..."
- ✓ "✓ Parent Streamlit will read st.query_params and rerun"

**Unacceptable Messages**:
- ✗ "SecurityError: Blocked a frame..."
- ✗ "Failed to navigate from about:srcdoc"
- ✗ "Cannot read property 'location' of cross-origin object"

**Result**: ☐ PASS (0 errors) ☐ FAIL (1+ errors) | Error Count: ____

---

## 🧪 Test 15: Ribbon Commands Functionality

**Objective**: Verify commands in ribbon execute correctly

| # | Action | Expected Result | ✓/✗ | Notes |
|---|--------|-----------------|-----|-------|
| 15.1 | Home tab → Click "Nuovo Dipendente" | Opens employee creation form | | |
| 15.2 | Home tab → Click "Import File" | Opens file uploader | | |
| 15.3 | Gestione Dati → Click "Gestione Personale" | Loads employee table | | |
| 15.4 | Gestione Dati → Click "Gestione Strutture" | Loads structure table | | |
| 15.5 | Organigrammi → Click layout toggle | Org chart layout changes | | |
| 15.6 | Analisi → Click "Ricerca Intelligente" | Opens search interface | | |
| 15.7 | Versioni → Click "Snapshot Manuale" | Opens snapshot dialog | | |

**Result**: ☐ PASS ☐ FAIL | Failed commands: ________________

---

## 🧪 Test 16: URL Query Params Persistence

**Objective**: Verify URL params survive page operations

| # | Action | Expected Result | ✓/✗ | Notes |
|---|--------|-----------------|-----|-------|
| 16.1 | Navigate to Gestione Dati | URL: `?active_ribbon_tab=Gestione%20Dati` | | |
| 16.2 | Perform action (e.g., add filter) | Tab remains active | | |
| 16.3 | Manually add param: `&test=true` | Press Enter | | |
| 16.4 | Verify tab unchanged | Gestione Dati still active | | |
| 16.5 | Reload page (F5) | Tab state restored from URL | | |

**Result**: ☐ PASS ☐ FAIL

---

## 📊 Overall Test Summary

### Pass Rate

| Test # | Name | Status | Notes |
|--------|------|--------|-------|
| 1 | Ribbon Visibility & Layout | ☐ PASS ☐ FAIL | |
| 2 | Tab Navigation (Home) | ☐ PASS ☐ FAIL | |
| 3 | Tab Navigation (Gestione Dati) | ☐ PASS ☐ FAIL | |
| 4 | Tab Navigation (Organigrammi) | ☐ PASS ☐ FAIL | |
| 5 | Tab Navigation (Analisi) | ☐ PASS ☐ FAIL | |
| 6 | Tab Navigation (Versioni) | ☐ PASS ☐ FAIL | |
| 7 | Tab Switching (All Tabs) | ☐ PASS ☐ FAIL | |
| 8 | Browser Back/Forward | ☐ PASS ☐ FAIL | |
| 9 | Quick Access Toolbar | ☐ PASS ☐ FAIL | |
| 10 | Search Bar | ☐ PASS ☐ FAIL ☐ N/A | |
| 11 | Account Menu | ☐ PASS ☐ FAIL ☐ N/A | |
| 12 | Collapse/Minimize | ☐ PASS ☐ FAIL | |
| 13 | Mobile Responsiveness | ☐ PASS ☐ FAIL ☐ N/A | |
| 14 | Console Error-Free | ☐ PASS ☐ FAIL | |
| 15 | Ribbon Commands | ☐ PASS ☐ FAIL | |
| 16 | URL Query Params | ☐ PASS ☐ FAIL | |

**Total Passed**: ___ / 16
**Pass Rate**: ____%

### Critical Issues Found

| Issue # | Severity | Description | Status |
|---------|----------|-------------|--------|
| | ☐ CRITICAL | | ☐ FIXED ☐ OPEN |
| | ☐ HIGH | | ☐ FIXED ☐ OPEN |
| | ☐ MEDIUM | | ☐ FIXED ☐ OPEN |
| | ☐ LOW | | ☐ FIXED ☐ OPEN |

---

## ✅ Final Sign-Off

**Tester Name**: ___________________
**Date Tested**: ___________________
**Overall Status**: ☐ APPROVED ☐ NEEDS FIXES
**Comments**: _______________________________________________

---

**Test Session Complete**
