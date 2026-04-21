# Mica Otter Illustrations

This directory contains the SVG illustrations for the Mica procurement system.

## Adding New Illustrations

1. Create a new SVG file named `otter-[name].svg`.
2. Use a 240x240 viewBox.
3. Use the following CSS classes to ensure the illustration adapts to the theme:
   - `.primary`: Base otter brown (`var(--color-primary-500)`)
   - `.secondary`: Lighter brown for belly/snout (`var(--color-primary-200)`)
   - `.accent`: Dark brown for nose/eyes (`var(--color-primary-700)`)
   - `.bg`: Subtle background blob (`var(--color-bg-subtle)`)

Example:
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240">
  <defs>
    <style>
      .primary { fill: var(--color-primary-500, #8B5E3C); }
      .secondary { fill: var(--color-primary-200, #D8C3B1); }
      .accent { fill: var(--color-primary-700, #543824); }
      .bg { fill: var(--color-bg-subtle, #F7F6F5); }
    </style>
  </defs>
  <!-- SVG content -->
</svg>
```
