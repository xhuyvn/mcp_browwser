# AI Agent Task Specification --- Build a Tailwind CSS v4 Theme & Design System Generator

## 0. Mission

Build a production-quality web application inspired by the workflow and
capabilities of:

**Reference:** https://tailwindthememaker.com/

The goal is **not to make a pixel-for-pixel clone**. Reverse-engineer
the useful product concepts, information architecture, interaction
patterns, and design-system workflow from the reference, then create a
**new, independent, modern product** with its own visual identity, UX,
copy, components, and implementation.

The final application should let a user visually create a design system
and export a clean **Tailwind CSS v4** theme using the CSS-first
`@theme` approach.

The agent is responsible for the complete implementation, not just a
prototype.

------------------------------------------------------------------------

# 1. Primary Product Goal

Create a browser-based **Tailwind CSS v4 Design System / Theme
Generator**.

A user should be able to:

1.  Create a new theme.
2.  Define brand colors.
3.  Generate accessible color scales.
4.  Configure typography.
5.  Configure spacing.
6.  Configure border radius.
7.  Configure shadows/elevation.
8.  Configure breakpoints where appropriate.
9.  Configure animation/motion tokens.
10. Configure semantic colors.
11. Configure light and dark themes.
12. Preview the resulting design system on real UI components.
13. Edit individual tokens.
14. See changes immediately in the preview.
15. Generate valid Tailwind CSS v4 `@theme` CSS.
16. Export/copy the generated CSS.
17. Export the theme as JSON.
18. Import an existing theme.
19. Reset/revert changes.
20. Share or save a theme if persistence is implemented.
21. Generate a polished component showcase using the theme.

The application should feel like a serious developer/design tool, not a
simple form.

------------------------------------------------------------------------

# 2. Reference Website Analysis

Before implementation, inspect and understand:

https://tailwindthememaker.com/

Analyze:

-   Information architecture
-   Navigation
-   Theme-generation workflow
-   Input controls
-   Color editing
-   Token organization
-   Preview behavior
-   Export behavior
-   UX patterns
-   Responsive behavior
-   Visual hierarchy
-   Empty states
-   Feedback states
-   Error states
-   Copy/export interactions
-   Component preview patterns

Do NOT copy:

-   Branding
-   Logo
-   Text/content
-   Proprietary graphics
-   Source code
-   Exact visual identity
-   Exact layout where unnecessary
-   Assets
-   Copyrighted illustrations

Use the reference only as a product/UX inspiration.

The new product must have a clearly differentiated visual identity.

------------------------------------------------------------------------

# 3. Product Positioning

The product should communicate:

> "Design your system visually. Export production-ready Tailwind CSS
> v4."

Suggested product characteristics:

-   Developer-friendly
-   Designer-friendly
-   Fast
-   Minimal
-   Modern
-   Professional
-   Highly visual
-   Token-driven
-   Accessible
-   Export-focused

Avoid making it feel like an admin dashboard.

It should feel like a dedicated **design-system workbench**.

------------------------------------------------------------------------

# 4. Recommended Technology Stack

Use the existing project stack if one already exists.

If starting from scratch, prefer:

-   React
-   TypeScript
-   Vite or the project's existing modern React framework
-   Tailwind CSS v4
-   CSS-first Tailwind configuration
-   Modern component architecture
-   Client-side state management appropriate to project complexity
-   Local persistence where useful

Do not introduce unnecessary dependencies.

Prefer browser-native APIs and small utilities where practical.

------------------------------------------------------------------------

# 5. Tailwind CSS v4 Requirement

This is a hard requirement.

The generated theme must use the Tailwind CSS v4 CSS-first architecture.

The generated output should resemble:

``` css
@import "tailwindcss";

@theme {
  --color-primary-50: ...;
  --color-primary-100: ...;
  --color-primary-200: ...;
  --color-primary-300: ...;
  --color-primary-400: ...;
  --color-primary-500: ...;
  --color-primary-600: ...;
  --color-primary-700: ...;
  --color-primary-800: ...;
  --color-primary-900: ...;
  --color-primary-950: ...;

  --font-sans: ...;
  --font-mono: ...;

  --spacing-xs: ...;
  --spacing-sm: ...;
  --spacing-md: ...;
  --spacing-lg: ...;

  --radius-sm: ...;
  --radius-md: ...;
  --radius-lg: ...;
}
```

Do NOT build the core architecture around the old Tailwind v3:

``` text
tailwind.config.js
```

unless compatibility is explicitly required.

The product should treat `@theme` as a first-class output format.

------------------------------------------------------------------------

# 6. Design Token Architecture

Create an internal normalized token model.

Example:

``` ts
interface ThemeTokens {
  colors: {
    primary: ColorScale;
    secondary?: ColorScale;
    neutral: ColorScale;
    success: ColorScale;
    warning: ColorScale;
    danger: ColorScale;
    info: ColorScale;

    background: TokenColor;
    foreground: TokenColor;
    surface: TokenColor;
    border: TokenColor;
  };

  typography: {
    fontSans: string;
    fontSerif?: string;
    fontMono?: string;

    fontSizes: Record<string, string>;
    lineHeights: Record<string, string>;
    letterSpacing: Record<string, string>;
    fontWeights: Record<string, number>;
  };

  spacing: Record<string, string>;

  radius: Record<string, string>;

  shadows: Record<string, string>;

  motion?: {
    durations: Record<string, string>;
    easings: Record<string, string>;
  };
}
```

The internal model should be independent from the UI.

Create a deterministic compiler:

``` text
ThemeTokens
    ↓
Tailwind v4 CSS generator
    ↓
@theme CSS
```

Also support:

``` text
ThemeTokens
    ↓
JSON serializer
    ↓
Theme JSON
```

------------------------------------------------------------------------

# 7. Color System

Color editing is one of the most important parts of the application.

Support:

-   HEX
-   RGB
-   HSL
-   OKLCH where practical
-   Alpha/transparency where relevant

Prefer OKLCH internally when generating perceptually consistent scales.

Generate scales such as:

``` text
50
100
200
300
400
500
600
700
800
900
950
```

Example:

``` text
Primary
 ├── 50
 ├── 100
 ├── 200
 ├── 300
 ├── 400
 ├── 500
 ├── 600
 ├── 700
 ├── 800
 ├── 900
 └── 950
```

The user must be able to override individual values.

Do not blindly overwrite manually customized values when regenerating a
palette.

------------------------------------------------------------------------

# 8. Accessibility

Include accessibility-oriented functionality.

At minimum:

-   Contrast ratio calculation
-   WCAG AA indication
-   WCAG AAA indication where applicable
-   Text/background contrast preview
-   Warning for insufficient contrast
-   Accessible foreground recommendation

For example:

``` text
Primary 500
White text     ✓ AA
Black text     ✕
```

Do not claim accessibility compliance unless it is actually calculated.

------------------------------------------------------------------------

# 9. Semantic Color Layer

Separate raw palette colors from semantic roles.

Example:

``` text
Primitive
  primary-500
  neutral-900
  success-500

Semantic
  background
  foreground
  surface
  surface-muted
  border
  primary
  primary-hover
  destructive
  warning
  success
```

This makes the design system easier to maintain.

Example mapping:

``` text
--color-primary: var(--color-primary-500);
--color-primary-hover: var(--color-primary-600);
```

Where technically appropriate for the generated output.

------------------------------------------------------------------------

# 10. Typography System

Allow users to configure:

### Fonts

-   Sans
-   Serif
-   Mono

### Font sizes

Example:

``` text
xs
sm
base
lg
xl
2xl
3xl
4xl
5xl
6xl
```

### Font weights

``` text
thin
extralight
light
normal
medium
semibold
bold
extrabold
black
```

### Line heights

### Letter spacing

Show typography previews.

Example:

``` text
Display
Heading
Body
Small text
Caption
Code
```

------------------------------------------------------------------------

# 11. Spacing System

Support configurable spacing tokens.

Example:

``` text
0
px
0.5
1
1.5
2
3
4
5
6
8
10
12
16
20
24
32
40
48
64
```

The UI should make the spacing system easy to understand visually.

------------------------------------------------------------------------

# 12. Border Radius

Support:

``` text
none
sm
md
lg
xl
2xl
3xl
full
```

Show live component previews.

------------------------------------------------------------------------

# 13. Shadows / Elevation

Support a useful shadow system.

Example:

``` text
none
xs
sm
md
lg
xl
2xl
inner
```

Show examples on cards, dialogs, buttons, etc.

------------------------------------------------------------------------

# 14. Motion System

Optional but recommended.

Support:

-   Duration tokens
-   Easing tokens
-   Common transitions
-   Reduced-motion consideration

Example:

``` text
duration-fast
duration-normal
duration-slow

ease-standard
ease-in
ease-out
ease-in-out
```

Avoid excessive animation.

------------------------------------------------------------------------

# 15. Light / Dark Theme

Support:

-   Light
-   Dark
-   System

The preview should immediately demonstrate the generated theme.

Where appropriate, use CSS variables and Tailwind v4-compatible
mechanisms rather than duplicating token definitions unnecessarily.

------------------------------------------------------------------------

# 16. Live Preview

This is a core feature.

The user should see the generated theme applied to real UI components.

Include a component gallery containing:

### Buttons

-   Primary
-   Secondary
-   Outline
-   Ghost
-   Destructive
-   Disabled

### Inputs

-   Text
-   Search
-   Select
-   Checkbox
-   Radio
-   Switch

### Content

-   Card
-   Badge
-   Alert
-   Tooltip
-   Avatar
-   Progress

### Navigation

-   Tabs
-   Breadcrumb
-   Sidebar
-   Pagination

### Data

-   Table
-   Stats
-   List

### Feedback

-   Toast
-   Modal/dialog
-   Empty state
-   Loading state
-   Error state

The preview should not merely show color swatches.

It should demonstrate how the design system behaves as a complete UI.

------------------------------------------------------------------------

# 17. Theme Editor UX

Use a clear application structure.

Recommended layout:

``` text
┌──────────────────────────────────────────────────────────────┐
│ Logo / Theme name     Preview     Export     Settings        │
├───────────────┬──────────────────────────────────────────────┤
│               │                                              │
│ Theme         │                                              │
│ Colors        │              Live Preview                    │
│ Typography    │                                              │
│ Spacing       │                                              │
│ Radius        │                                              │
│ Shadows       │                                              │
│ Motion        │                                              │
│ Semantic      │                                              │
│               │                                              │
├───────────────┴──────────────────────────────────────────────┤
│ Token status / actions                                       │
└──────────────────────────────────────────────────────────────┘
```

The exact layout can differ if a better UX is discovered during
implementation.

------------------------------------------------------------------------

# 18. Export Experience

Provide a dedicated export panel.

Formats:

## Tailwind CSS v4

``` css
@import "tailwindcss";

@theme {
  ...
}
```

## JSON

``` json
{
  "colors": {},
  "typography": {},
  "spacing": {},
  "radius": {},
  "shadows": {}
}
```

## Copy

Buttons:

-   Copy CSS
-   Copy JSON
-   Download CSS
-   Download JSON

Show success feedback after copying.

------------------------------------------------------------------------

# 19. CSS Generator Requirements

The CSS generator must:

-   Produce deterministic output
-   Produce stable ordering
-   Use readable formatting
-   Escape invalid identifiers
-   Avoid duplicate variables
-   Avoid undefined references
-   Preserve manually edited values
-   Generate valid Tailwind v4 syntax
-   Be independently testable

Example architecture:

``` ts
generateTailwindTheme(tokens): string
```

The generator should have unit tests.

------------------------------------------------------------------------

# 20. Import

Support importing a generated theme.

At minimum:

``` text
Paste CSS
Upload CSS
Paste JSON
Upload JSON
```

Parse supported Tailwind `@theme` variables into the internal token
model where feasible.

If complete arbitrary CSS parsing is too complex, clearly scope the
supported subset.

Never silently discard unsupported values.

------------------------------------------------------------------------

# 21. Persistence

Prefer local-first persistence.

Use:

``` text
localStorage
```

or IndexedDB where appropriate.

Support:

-   Autosave
-   Restore last theme
-   New theme
-   Duplicate theme
-   Reset theme

If authentication/backend is not required, do not introduce a backend
just for persistence.

------------------------------------------------------------------------

# 22. Undo / Redo

Recommended.

Support:

``` text
Ctrl/Cmd + Z
Ctrl/Cmd + Shift + Z
```

for meaningful theme changes.

The implementation should avoid storing enormous duplicated state
snapshots unnecessarily.

------------------------------------------------------------------------

# 23. Responsive Design

The application must work well on:

-   Desktop
-   Laptop
-   Tablet
-   Mobile

Desktop is the primary authoring experience.

On mobile, adapt the editor to:

``` text
Editor
Preview
Export
```

using tabs, drawers, or another appropriate pattern.

Do not simply shrink the desktop layout.

------------------------------------------------------------------------

# 24. Visual Design Direction

Create a distinctive visual identity.

Suggested direction:

-   Modern developer tool
-   Clean neutral base
-   Strong typography
-   Subtle borders
-   Soft surfaces
-   Excellent spacing
-   High information density without clutter
-   Professional but not corporate
-   Strong visual feedback
-   Polished micro-interactions

Avoid:

-   Generic SaaS dashboard appearance
-   Excessive gradients
-   Excessive glassmorphism
-   Huge marketing hero sections
-   Decorative UI that doesn't improve usability

The product is a tool first.

------------------------------------------------------------------------

# 25. AI Theme Generation

If feasible within the project, add an AI-assisted workflow.

Example:

``` text
"Create a modern dark theme for a fintech dashboard with blue primary colors."
```

The system should transform the prompt into structured theme tokens.

Important:

AI output must be validated against the token schema before being
applied.

Never allow arbitrary AI output to directly become executable code.

If no AI backend is available, create a clean provider interface so one
can be added later.

Example:

``` ts
interface ThemeGenerator {
  generate(prompt: string): Promise<ThemeTokens>;
}
```

------------------------------------------------------------------------

# 26. Preset Themes

Include several presets.

Examples:

-   Minimal
-   Modern
-   Ocean
-   Forest
-   Sunset
-   Monochrome
-   SaaS
-   Dashboard
-   Editorial
-   Dark Pro

Presets should simply populate the same token model.

They must not use a separate architecture.

------------------------------------------------------------------------

# 27. Code Architecture

Keep clear separation:

``` text
src/
  components/
  features/
    theme-editor/
    color-system/
    typography/
    preview/
    export/
    import/
  lib/
    theme/
    color/
    accessibility/
    generators/
    parsers/
  state/
  types/
  styles/
```

Adapt this structure to the actual framework.

Avoid one giant component.

Avoid putting business logic inside presentation components.

------------------------------------------------------------------------

# 28. State Architecture

Theme state should have a single normalized source of truth.

Recommended:

``` text
ThemeState
   ↓
Selectors
   ↓
Editor UI
   ↓
Preview
   ↓
Export generator
```

Do not maintain separate independent copies of the same token data.

------------------------------------------------------------------------

# 29. Validation

Validate:

-   Color syntax
-   Numeric values
-   CSS values
-   Token names
-   Duplicate tokens
-   Missing required values
-   Invalid references
-   Contrast issues

Provide human-readable errors.

Bad:

``` text
Invalid value
```

Better:

``` text
Primary 500 must be a valid CSS color.
Try HEX, RGB, HSL, or OKLCH.
```

------------------------------------------------------------------------

# 30. Performance

The editor should feel instantaneous.

Avoid unnecessary:

-   Full application re-renders
-   Expensive color calculations
-   Re-generating large preview trees
-   Parsing CSS on every keystroke

Debounce expensive operations where appropriate.

Keep the preview responsive while editing.

------------------------------------------------------------------------

# 31. Quality Requirements

The implementation must be production-oriented.

Do not leave:

-   TODO placeholders
-   Fake buttons
-   Dead navigation
-   Broken interactions
-   Console errors
-   Dummy export actions
-   Hardcoded preview values that ignore theme changes

Every visible control should either work or be intentionally hidden
until implemented.

------------------------------------------------------------------------

# 32. Testing

At minimum test:

## Theme generation

``` text
ThemeTokens → Tailwind CSS
```

## Serialization

``` text
ThemeTokens → JSON → ThemeTokens
```

## Color generation

Test palette generation with multiple base colors.

## Accessibility

Test contrast calculations.

## Import

Test supported CSS/JSON imports.

## UI

Test the most important editor interactions.

------------------------------------------------------------------------

# 33. Browser QA

After implementation:

1.  Run the application.
2.  Open the actual UI.
3.  Test the main user journey.
4.  Create a theme.
5.  Change primary color.
6.  Change typography.
7.  Change radius.
8.  Change spacing.
9.  Verify preview updates.
10. Switch dark/light mode.
11. Export CSS.
12. Export JSON.
13. Reload the page.
14. Verify persistence.
15. Test responsive layouts.
16. Check browser console.
17. Fix visual defects.
18. Repeat until stable.

Do not declare completion based only on source-code inspection.

------------------------------------------------------------------------

# 34. Main User Journey

The final implementation must support this complete flow:

``` text
Open application
      ↓
Create new theme
      ↓
Choose preset or start blank
      ↓
Edit primary color
      ↓
Generate / adjust color scale
      ↓
Configure semantic colors
      ↓
Configure typography
      ↓
Configure spacing
      ↓
Configure radius
      ↓
Configure shadows
      ↓
Switch light/dark
      ↓
Inspect live components
      ↓
Fix accessibility issues
      ↓
Open Export
      ↓
Copy Tailwind CSS v4
      ↓
Download JSON
      ↓
Reload application
      ↓
Theme is restored
```

Every step should work.

------------------------------------------------------------------------

# 35. Definition of Done

The task is complete only when:

-   [ ] Reference website has been analyzed.
-   [ ] New product has a differentiated identity.
-   [ ] Tailwind CSS v4 is actually used.
-   [ ] CSS-first `@theme` architecture is implemented.
-   [ ] Theme tokens have a normalized data model.
-   [ ] Colors work.
-   [ ] Color scales work.
-   [ ] Semantic colors work.
-   [ ] Typography works.
-   [ ] Spacing works.
-   [ ] Radius works.
-   [ ] Shadows work.
-   [ ] Light/dark themes work.
-   [ ] Live component preview works.
-   [ ] Preview responds to token changes.
-   [ ] Tailwind CSS export works.
-   [ ] JSON export works.
-   [ ] Copy-to-clipboard works.
-   [ ] Download works.
-   [ ] Import works for the supported formats.
-   [ ] Local persistence works.
-   [ ] Reset/new-theme functionality works.
-   [ ] Accessibility checks work.
-   [ ] No obvious console errors remain.
-   [ ] Responsive behavior is tested.
-   [ ] Main user journey works end-to-end.
-   [ ] Tests pass.
-   [ ] Production build succeeds.

------------------------------------------------------------------------

# 36. Agent Execution Rules

You are the implementation agent.

Do not stop after producing a design proposal.

Do not ask for confirmation for every small decision.

Make reasonable engineering decisions yourself.

When a requirement is ambiguous:

1.  Prefer the simplest production-quality implementation.
2.  Follow established web conventions.
3.  Preserve the main product goal.
4.  Avoid unnecessary dependencies.
5.  Document significant architectural decisions.

Do not replace working functionality with mockups.

Do not claim a feature is implemented unless it actually works.

------------------------------------------------------------------------

# 37. Implementation Strategy

Work in these phases.

## Phase 1 --- Research

Analyze the reference product.

Create an internal understanding of:

-   UX
-   Information architecture
-   Feature set
-   Design-system concepts
-   Export model

Do not copy the implementation.

## Phase 2 --- Foundation

Set up:

-   Application
-   Tailwind CSS v4
-   Token types
-   Theme state
-   Theme generator
-   Basic layout

## Phase 3 --- Theme Editor

Implement:

-   Colors
-   Typography
-   Spacing
-   Radius
-   Shadows
-   Semantic tokens

## Phase 4 --- Preview

Implement a comprehensive component showcase driven entirely by theme
tokens.

## Phase 5 --- Export / Import

Implement:

-   CSS export
-   JSON export
-   Copy
-   Download
-   Import
-   Validation

## Phase 6 --- Persistence

Implement:

-   Autosave
-   Restore
-   New
-   Duplicate
-   Reset

## Phase 7 --- Accessibility / Quality

Implement:

-   Contrast checking
-   Validation
-   Error handling
-   Keyboard interaction

## Phase 8 --- Polish

Improve:

-   Responsive UX
-   Micro-interactions
-   Loading states
-   Empty states
-   Visual consistency
-   Performance

## Phase 9 --- QA

Run the complete user journey.

Fix all discovered issues.

## Phase 10 --- Final Review

Verify every Definition of Done item.

------------------------------------------------------------------------

# 38. Important Engineering Principle

The application should be **token-driven**.

Do not hardcode separate colors into individual components.

Bad:

``` tsx
<button className="bg-blue-500">
```

when the application is supposed to demonstrate the user's generated
theme.

Prefer theme-driven values.

The preview should prove that changing one token actually changes the
design system.

------------------------------------------------------------------------

# 39. Expected Final Deliverable

Deliver a working application, not merely documentation.

The final result should include:

1.  Working source code.
2.  Tailwind CSS v4 implementation.
3.  Theme editor.
4.  Live preview.
5.  Token engine.
6.  CSS generator.
7.  JSON export/import.
8.  Persistence.
9.  Accessibility checks.
10. Tests.
11. Production build.

At the end, provide a concise implementation report containing:

``` text
Implemented:
- ...

Architecture:
- ...

Tailwind v4 approach:
- ...

Export formats:
- ...

Testing:
- ...

Known limitations:
- ...

How to run:
- ...
```

Do not claim completion if critical functionality is still mocked or
broken.

------------------------------------------------------------------------

# 40. Final Product Principle

The product should answer one question extremely well:

> **"Can I visually design a complete UI system and immediately get
> clean, production-ready Tailwind CSS v4 tokens?"**

If the answer is yes, the implementation is successful.

The reference website is the starting point for understanding the
problem.

The final product should be **better organized, more extensible, more
visually useful, and more developer-oriented than a simple clone.**
