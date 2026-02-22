# Organigrammi Fixes - 2026-02-22

## Summary

Fixed three major issues in all organizational chart views (HR, ORG, TNS):

1. ✅ **Drill-down functionality** - Click on a manager now shows ONLY direct reports (not entire subtree)
2. ✅ **Auto-fit responsive behavior** - Charts automatically fit within page boundaries
3. ✅ **Sunburst and Treemap rendering** - Fixed layout calculation and rendering issues

---

## Changes by File

### 1. `/ui/orgchart_hr_view.py`

#### **Drill-down Fix** (lines 380-396)
**Problem**: `shouldShowNode()` showed ALL descendants (entire subtree)
**Solution**: Changed to show only DIRECT children

```javascript
// BEFORE: Show all descendants
const descendants = getDescendants(focusedNode);
if (descendants.includes(node)) return true;

// AFTER: Show only direct children
if (node.parent === focusedNode) return true;
```

#### **Auto-fit Function** (lines 300-318)
**Problem**: No auto-fit logic - charts overflow page boundaries
**Solution**: Added `autoFit()` function that calculates bbox and centers/scales tree

```javascript
function autoFit() {
  const bbox = g.node().getBBox();
  const scale = Math.min(
    (w - 60) / fullWidth,
    (h - 60) / fullHeight,
    1.5  // Max zoom in
  );
  const centerX = w / 2 - (bbox.x + fullWidth / 2) * scale;
  const centerY = h / 2 - (bbox.y + fullHeight / 2) * scale;
  svg.transition().duration(300).call(zoom.transform,
    d3.zoomIdentity.translate(centerX, centerY).scale(scale));
}
```

#### **Toggle Behavior** (lines 398-414)
**Problem**: Toggle didn't update focus correctly
**Solution**: Set focused node on expand, reset to parent on collapse

```javascript
// Collapsing - keep focus on parent
if (d.depth > 1) {
  focusedNode = d.parent;
} else {
  focusedNode = null;
}

// Expanding - set as focused to show only its children
focusedNode = d;
```

#### **Horizontal Tree Filter** (lines 424-434)
**Problem**: drawHorizontal() showed all nodes regardless of focus
**Solution**: Filter nodes and links based on `shouldShowNode()`

```javascript
const allNodes = root.descendants();
const allLinks = root.links();
const nodes = allNodes.filter(shouldShowNode);
const links = allLinks.filter(link =>
  shouldShowNode(link.source) && shouldShowNode(link.target)
);
```

#### **Sunburst Fix** (lines 556-603)
**Problem**: Overlapping arcs, incorrect padding
**Solution**:
- Increased radius margin from 20 to 40
- Changed `sum(d=>Math.max(...))` to `sum(d=>employee_count||1)`
- Added `g.selectAll('*').remove()` before rendering
- Fixed depth color indexing (`d.depth-1` instead of `d.depth`)

#### **Treemap Fix** (lines 605-639)
**Problem**: Overlapping cells, incorrect layout
**Solution**:
- Changed `sum(d=>Math.max(...))` to `sum(d=>employee_count||1)`
- Increased padding from 1 to 2, paddingTop from 18 to 20
- Added `g.selectAll('*').remove()` before rendering

---

### 2. `/ui/orgchart_org_view.py`

Applied same fixes as HR view:

1. **Added drill-down logic** (lines 240-264)
   - `focusedNode` variable
   - `getAncestors()` helper
   - `shouldShowNode()` with direct children only

2. **Updated toggle()** (lines 275-293)
   - Set focused node on expand/collapse
   - Call `autoFit()` after toggle

3. **Added autoFit()** (lines 411-429)
   - Same implementation as HR view

4. **Updated drawTreeBase()** (lines 282-289)
   - Filter nodes/links based on `shouldShowNode()`

5. **Updated all action functions** to call `autoFit()`:
   - `resetView()` - clears focus and auto-fits
   - `expandOne()` - auto-fits after expanding
   - `collapseAll()` - auto-fits after collapsing
   - `setLayout()` - auto-fits on layout change

---

### 3. `/ui/orgchart_tns_structures_view.py`

TNS view already had some drill-down logic, but needed fixes:

1. **Fixed shouldShowNode()** (lines 348-365)
   - Changed from showing ALL descendants to only DIRECT children
   - Same fix as HR view

2. **Updated toggle()** (lines 367-387)
   - Fixed focus management
   - Added `autoFit()` call

3. **Added autoFit()** (lines 658-676)
   - Same implementation as other views

4. **Fixed drawHorizontal()** (lines 414-427)
   - Added filter for nodes/links based on focus

5. **Fixed Sunburst** (lines 550-605)
   - Changed radius margin 20→40
   - Fixed `sum()` calculation
   - Added clear before rendering

6. **Fixed Treemap** (lines 607-656)
   - Fixed `sum()` calculation
   - Increased padding
   - Added clear before rendering

7. **Updated action functions** to call `autoFit()`:
   - `resetView()`
   - `expandOne()`
   - `collapseAll()`
   - `setLayout()`

---

## Behavior Changes

### Before
❌ Click manager → show entire subtree (hundreds of nodes)
❌ Tree overflows page boundaries
❌ No way to focus on specific branch
❌ Sunburst/Treemap don't render correctly
❌ Manual zoom/pan required to see everything

### After
✅ Click manager → show ONLY direct reports (drill-down)
✅ Tree auto-fits to page (responsive)
✅ Click again to collapse back to parent level
✅ Sunburst/Treemap render correctly with proper spacing
✅ Automatic centering and scaling

---

## User Workflow

1. **Initial load**: Tree collapsed at depth 1, auto-fitted to viewport
2. **Click node**: Expands to show direct children only
3. **View updates**: Auto-fits to show focused branch optimally
4. **Click background**: Resets focus to show all levels
5. **Reset button**: Clears all focus, shows full tree, auto-fits

---

## Technical Details

### Focus State Management
- `focusedNode = null` → Show all nodes (no filter)
- `focusedNode = node` → Show: node + ancestors + direct children
- Siblings and their branches are hidden

### Auto-fit Algorithm
1. Calculate bounding box of visible nodes
2. Compute scale to fit within viewport (with padding)
3. Center the tree horizontally and vertically
4. Animate zoom transform smoothly

### Filter Logic
```javascript
function shouldShowNode(node) {
  if (!focusedNode) return true;
  if (node === focusedNode) return true;
  if (getAncestors(focusedNode).includes(node)) return true;
  if (node.parent === focusedNode) return true;  // ONLY direct children
  return false;
}
```

---

## Testing Checklist

### HR Hierarchy (`/orgchart_hr_view.py`)
- [x] Albero H: drill-down, auto-fit, collapse
- [x] Albero V: drill-down, auto-fit, wrapping
- [x] Sunburst: renders correctly, no overlaps
- [x] Treemap: renders correctly, proper padding
- [x] Reset button: clears focus, shows all, auto-fits
- [x] Background click: same as reset

### ORG Hierarchy (`/orgchart_org_view.py`)
- [x] Albero H: drill-down, auto-fit
- [x] Albero V: drill-down, auto-fit
- [x] Panels: navigation works
- [x] Card Grid: displays all nodes

### TNS Structures (`/orgchart_tns_structures_view.py`)
- [x] Albero H: drill-down, auto-fit
- [x] Albero V: drill-down, auto-fit, wrapping
- [x] Sunburst: renders with approver colors
- [x] Treemap: renders with approver colors

---

## Files Modified
1. `/ui/orgchart_hr_view.py` - 11 edits
2. `/ui/orgchart_org_view.py` - 7 edits
3. `/ui/orgchart_tns_structures_view.py` - 8 edits

**Total**: 26 code changes across 3 files
