# Style Guide

A comprehensive design system specification for light and dark themes. This guide is framework-agnostic and defines design tokens, components, and patterns.

---

## Table of Contents

1. [Color System](#color-system)
2. [Typography](#typography)
3. [Spacing](#spacing)
4. [Border Radius](#border-radius)
5. [Shadows](#shadows)
6. [Components](#components)
7. [Layout Patterns](#layout-patterns)
8. [Transitions](#transitions)

---

## Color System

### Light Theme

```
/* Backgrounds */
--bg-primary: #FFFFFF
--bg-secondary: #F8FAFC
--bg-tertiary: #F1F5F9
--bg-sidebar: linear-gradient(180deg, #E0F2FE 0%, #DBEAFE 100%)
--bg-sidebar-alt: #EFF6FF

/* Surfaces */
--surface-primary: #FFFFFF
--surface-elevated: #FFFFFF
--surface-hover: #F8FAFC
--surface-active: #F1F5F9
--surface-selected: #EFF6FF

/* Borders */
--border-primary: #E2E8F0
--border-secondary: #CBD5E1
--border-subtle: #F1F5F9
--border-focus: #3B82F6

/* Text */
--text-primary: #0F172A
--text-secondary: #475569
--text-tertiary: #64748B
--text-muted: #94A3B8
--text-inverse: #FFFFFF

/* Brand / Primary */
--primary-50: #EFF6FF
--primary-100: #DBEAFE
--primary-200: #BFDBFE
--primary-300: #93C5FD
--primary-400: #60A5FA
--primary-500: #3B82F6
--primary-600: #2563EB
--primary-700: #1D4ED8
--primary-800: #1E40AF
--primary-900: #1E3A8A

/* Semantic Colors */
--success-bg: #DCFCE7
--success-border: #86EFAC
--success-text: #166534
--success-solid: #22C55E

--warning-bg: #FEF9C3
--warning-border: #FDE047
--warning-text: #854D0E
--warning-solid: #EAB308

--error-bg: #FEE2E2
--error-border: #FECACA
--error-text: #991B1B
--error-solid: #EF4444

--info-bg: #DBEAFE
--info-border: #93C5FD
--info-text: #1E40AF
--info-solid: #3B82F6

/* Status Colors */
--status-accepted: #22C55E
--status-rejected: #EF4444
--status-processing: #F59E0B
--status-analyzing: #06B6D4
--status-pending: #94A3B8
--status-mutating: #8B5CF6

/* Chart Colors */
--chart-1: #3B82F6
--chart-2: #06B6D4
--chart-3: #22C55E
--chart-4: #F59E0B
--chart-5: #EF4444
--chart-6: #8B5CF6
```

### Dark Theme

```
/* Backgrounds */
--bg-primary: #0F172A
--bg-secondary: #1E293B
--bg-tertiary: #334155
--bg-sidebar: #0F172A
--bg-sidebar-alt: #1E293B

/* Surfaces */
--surface-primary: #1E293B
--surface-elevated: #334155
--surface-hover: #334155
--surface-active: #475569
--surface-selected: #1E3A5F

/* Borders */
--border-primary: #334155
--border-secondary: #475569
--border-subtle: #1E293B
--border-focus: #60A5FA

/* Text */
--text-primary: #F8FAFC
--text-secondary: #CBD5E1
--text-tertiary: #94A3B8
--text-muted: #64748B
--text-inverse: #0F172A

/* Brand / Primary (same across themes) */
--primary-50: #1E3A5F
--primary-100: #1E40AF
--primary-200: #1D4ED8
--primary-300: #2563EB
--primary-400: #3B82F6
--primary-500: #60A5FA
--primary-600: #93C5FD
--primary-700: #BFDBFE
--primary-800: #DBEAFE
--primary-900: #EFF6FF

/* Semantic Colors */
--success-bg: #14532D
--success-border: #166534
--success-text: #86EFAC
--success-solid: #22C55E

--warning-bg: #713F12
--warning-border: #854D0E
--warning-text: #FDE047
--warning-solid: #EAB308

--error-bg: #7F1D1D
--error-border: #991B1B
--error-text: #FECACA
--error-solid: #EF4444

--info-bg: #1E3A8A
--info-border: #1E40AF
--info-text: #93C5FD
--info-solid: #60A5FA

/* Status Colors (same across themes) */
--status-accepted: #22C55E
--status-rejected: #EF4444
--status-processing: #F59E0B
--status-analyzing: #06B6D4
--status-pending: #64748B
--status-mutating: #A78BFA
```

---

## Typography

### Font Family

```
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif
--font-mono: 'JetBrains Mono', 'Fira Code', 'SF Mono', Monaco, 'Cascadia Code', monospace
```

### Font Sizes

```
--text-xs: 0.75rem      /* 12px */
--text-sm: 0.875rem     /* 14px */
--text-base: 1rem       /* 16px */
--text-lg: 1.125rem     /* 18px */
--text-xl: 1.25rem      /* 20px */
--text-2xl: 1.5rem      /* 24px */
--text-3xl: 1.875rem    /* 30px */
--text-4xl: 2.25rem     /* 36px */
```

### Font Weights

```
--font-normal: 400
--font-medium: 500
--font-semibold: 600
--font-bold: 700
```

### Line Heights

```
--leading-none: 1
--leading-tight: 1.25
--leading-snug: 1.375
--leading-normal: 1.5
--leading-relaxed: 1.625
```

### Typography Scale

| Element | Size | Weight | Line Height | Letter Spacing |
|---------|------|--------|-------------|----------------|
| Display | 2.25rem | 700 | 1.1 | -0.02em |
| Heading 1 | 1.875rem | 600 | 1.25 | -0.01em |
| Heading 2 | 1.5rem | 600 | 1.25 | -0.01em |
| Heading 3 | 1.25rem | 600 | 1.375 | 0 |
| Heading 4 | 1.125rem | 600 | 1.375 | 0 |
| Body Large | 1rem | 400 | 1.5 | 0 |
| Body | 0.875rem | 400 | 1.5 | 0 |
| Body Small | 0.75rem | 400 | 1.5 | 0.01em |
| Caption | 0.75rem | 500 | 1.25 | 0.02em |
| Code | 0.8125rem | 400 | 1.6 | 0 |

---

## Spacing

Based on a 4px grid system:

```
--space-0: 0
--space-px: 1px
--space-0.5: 0.125rem   /* 2px */
--space-1: 0.25rem      /* 4px */
--space-1.5: 0.375rem   /* 6px */
--space-2: 0.5rem       /* 8px */
--space-2.5: 0.625rem   /* 10px */
--space-3: 0.75rem      /* 12px */
--space-3.5: 0.875rem   /* 14px */
--space-4: 1rem         /* 16px */
--space-5: 1.25rem      /* 20px */
--space-6: 1.5rem       /* 24px */
--space-7: 1.75rem      /* 28px */
--space-8: 2rem         /* 32px */
--space-9: 2.25rem      /* 36px */
--space-10: 2.5rem      /* 40px */
--space-12: 3rem        /* 48px */
--space-14: 3.5rem      /* 56px */
--space-16: 4rem        /* 64px */
--space-20: 5rem        /* 80px */
--space-24: 6rem        /* 96px */
```

---

## Border Radius

```
--radius-none: 0
--radius-sm: 0.25rem    /* 4px */
--radius-md: 0.375rem   /* 6px */
--radius-lg: 0.5rem     /* 8px */
--radius-xl: 0.75rem    /* 12px */
--radius-2xl: 1rem      /* 16px */
--radius-3xl: 1.5rem    /* 24px */
--radius-full: 9999px
```

### Usage Guidelines

| Component | Radius |
|-----------|--------|
| Buttons | lg (8px) |
| Cards | xl (12px) |
| Inputs | lg (8px) |
| Badges/Pills | full |
| Modals | xl (12px) |
| Tooltips | md (6px) |
| Avatars | full |
| Progress bars | full |

---

## Shadows

### Light Theme

```
--shadow-xs: 0 1px 2px 0 rgb(0 0 0 / 0.05)
--shadow-sm: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)
--shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)
--shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)
--shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)
--shadow-2xl: 0 25px 50px -12px rgb(0 0 0 / 0.25)

/* Colored shadows for elevated primary elements */
--shadow-primary: 0 4px 14px 0 rgb(59 130 246 / 0.3)
--shadow-success: 0 4px 14px 0 rgb(34 197 94 / 0.3)
--shadow-error: 0 4px 14px 0 rgb(239 68 68 / 0.3)
```

### Dark Theme

```
--shadow-xs: 0 1px 2px 0 rgb(0 0 0 / 0.3)
--shadow-sm: 0 1px 3px 0 rgb(0 0 0 / 0.4), 0 1px 2px -1px rgb(0 0 0 / 0.4)
--shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.4), 0 2px 4px -2px rgb(0 0 0 / 0.4)
--shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.5), 0 4px 6px -4px rgb(0 0 0 / 0.5)
--shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.5), 0 8px 10px -6px rgb(0 0 0 / 0.5)
--shadow-2xl: 0 25px 50px -12px rgb(0 0 0 / 0.6)

/* Use glow effects instead of shadows for emphasis in dark mode */
--glow-primary: 0 0 20px rgb(59 130 246 / 0.4)
--glow-success: 0 0 20px rgb(34 197 94 / 0.4)
--glow-error: 0 0 20px rgb(239 68 68 / 0.4)
```

---

## Components

### Buttons

#### Primary Button
```
/* Light */
background: var(--primary-500)
color: white
border: none
padding: var(--space-2.5) var(--space-4)
border-radius: var(--radius-lg)
font-weight: var(--font-medium)
font-size: var(--text-sm)

hover: background: var(--primary-600)
active: background: var(--primary-700)
disabled: opacity: 0.5; cursor: not-allowed

/* Dark - same styles apply */
```

#### Secondary Button
```
/* Light */
background: transparent
color: var(--text-primary)
border: 1px solid var(--border-primary)
padding: var(--space-2.5) var(--space-4)
border-radius: var(--radius-lg)

hover: background: var(--surface-hover)

/* Dark */
border: 1px solid var(--border-primary)
hover: background: var(--surface-hover)
```

#### Ghost Button
```
/* Light & Dark */
background: transparent
color: var(--text-secondary)
border: none
padding: var(--space-2) var(--space-3)
border-radius: var(--radius-lg)

hover: background: var(--surface-hover); color: var(--text-primary)
```

#### Danger Button
```
background: var(--error-solid)
color: white
/* Other properties same as Primary */
```

### Cards

```
/* Light */
background: var(--surface-primary)
border: 1px solid var(--border-primary)
border-radius: var(--radius-xl)
box-shadow: var(--shadow-sm)
padding: var(--space-5)

/* Dark */
background: var(--surface-primary)
border: 1px solid var(--border-primary)
border-radius: var(--radius-xl)
box-shadow: none
padding: var(--space-5)
```

### Metric Card

```
/* Container */
background: var(--surface-primary)
border-radius: var(--radius-xl)
padding: var(--space-4) var(--space-5)
border: 1px solid var(--border-primary)

/* Metric Value */
font-size: var(--text-3xl)
font-weight: var(--font-bold)
color: var(--text-primary)

/* Metric Label */
font-size: var(--text-sm)
color: var(--text-secondary)
text-transform: uppercase
letter-spacing: 0.05em

/* Trend Indicator (positive) */
color: var(--success-solid)
font-size: var(--text-sm)

/* Trend Indicator (negative) */
color: var(--error-solid)
font-size: var(--text-sm)
```

### Sidebar

```
/* Light */
width: 240px (expanded) / 64px (collapsed)
background: var(--bg-sidebar)
border-right: 1px solid var(--border-subtle)
padding: var(--space-4)

/* Dark */
background: var(--bg-sidebar)
border-right: 1px solid var(--border-primary)

/* Nav Item */
padding: var(--space-2.5) var(--space-3)
border-radius: var(--radius-lg)
color: var(--text-secondary)
font-size: var(--text-sm)
font-weight: var(--font-medium)

/* Nav Item - Active */
background: var(--surface-selected) /* Light: rgba(59, 130, 246, 0.1) */
color: var(--primary-500)

/* Nav Item - Hover */
background: var(--surface-hover)
color: var(--text-primary)

/* Nav Icon */
width: 20px
height: 20px
margin-right: var(--space-3)
```

### Inputs

```
/* Light */
background: var(--surface-primary)
border: 1px solid var(--border-primary)
border-radius: var(--radius-lg)
padding: var(--space-2.5) var(--space-3)
font-size: var(--text-sm)
color: var(--text-primary)

focus: border-color: var(--border-focus); box-shadow: 0 0 0 3px var(--primary-100)

/* Dark */
background: var(--surface-primary)
border: 1px solid var(--border-primary)

focus: border-color: var(--border-focus); box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2)

/* Placeholder */
color: var(--text-muted)
```

### Badges / Pills

```
/* Base */
padding: var(--space-1) var(--space-2.5)
border-radius: var(--radius-full)
font-size: var(--text-xs)
font-weight: var(--font-medium)
display: inline-flex
align-items: center
gap: var(--space-1.5)

/* Variants */
/* Success */
background: var(--success-bg)
color: var(--success-text)

/* Error */
background: var(--error-bg)
color: var(--error-text)

/* Warning */
background: var(--warning-bg)
color: var(--warning-text)

/* Info */
background: var(--info-bg)
color: var(--info-text)

/* Neutral */
background: var(--surface-hover)
color: var(--text-secondary)
```

### Progress Bar

```
/* Track */
height: 8px
background: var(--bg-tertiary)
border-radius: var(--radius-full)
overflow: hidden

/* Fill */
height: 100%
background: var(--primary-500)
border-radius: var(--radius-full)
transition: width 0.3s ease

/* Striped variant - add gradient */
background-image: linear-gradient(
  45deg,
  rgba(255,255,255,0.15) 25%,
  transparent 25%,
  transparent 50%,
  rgba(255,255,255,0.15) 50%,
  rgba(255,255,255,0.15) 75%,
  transparent 75%
)
background-size: 1rem 1rem
```

### Code Block / Code Viewer

```
/* Container */
background: var(--bg-secondary) /* Light: #F8FAFC, Dark: #1E293B */
border: 1px solid var(--border-primary)
border-radius: var(--radius-xl)
overflow: hidden
font-family: var(--font-mono)
font-size: var(--text-sm)
line-height: var(--leading-relaxed)

/* Line Numbers */
color: var(--text-muted)
padding-right: var(--space-4)
text-align: right
user-select: none

/* Syntax Highlighting */
--syntax-keyword: #8B5CF6      /* purple - if, else, return, const, let */
--syntax-string: #22C55E       /* green - strings */
--syntax-number: #F59E0B       /* amber - numbers */
--syntax-function: #3B82F6     /* blue - function names */
--syntax-comment: #94A3B8      /* gray - comments */
--syntax-operator: #EC4899     /* pink - operators */
--syntax-variable: #06B6D4     /* cyan - variables */
--syntax-type: #F97316         /* orange - types */

/* Diff highlighting */
--diff-add-bg: rgba(34, 197, 94, 0.15)
--diff-add-border: var(--success-solid)
--diff-remove-bg: rgba(239, 68, 68, 0.15)
--diff-remove-border: var(--error-solid)
```

### Status Indicator Dot

```
width: 8px
height: 8px
border-radius: var(--radius-full)

/* With pulse animation for active states */
animation: pulse 2s ease-in-out infinite

/* Colors */
online/success: var(--status-accepted)
offline/error: var(--status-rejected)
processing: var(--status-processing)
analyzing: var(--status-analyzing)
pending: var(--status-pending)
```

### Tooltip

```
/* Light */
background: var(--text-primary)
color: var(--text-inverse)
padding: var(--space-2) var(--space-3)
border-radius: var(--radius-md)
font-size: var(--text-xs)
box-shadow: var(--shadow-lg)

/* Dark */
background: var(--surface-elevated)
color: var(--text-primary)
border: 1px solid var(--border-primary)
```

### Table

```
/* Header */
background: var(--bg-secondary)
font-weight: var(--font-semibold)
font-size: var(--text-xs)
text-transform: uppercase
letter-spacing: 0.05em
color: var(--text-secondary)
padding: var(--space-3) var(--space-4)
border-bottom: 1px solid var(--border-primary)

/* Row */
padding: var(--space-4)
border-bottom: 1px solid var(--border-subtle)

/* Row Hover */
background: var(--surface-hover)

/* Row Striped (alternate) */
background: var(--bg-secondary)
```

### Console / Log

```
/* Container */
background: var(--bg-primary)  /* Dark: #0F172A */
font-family: var(--font-mono)
font-size: var(--text-xs)
padding: var(--space-3) var(--space-4)
border-top: 1px solid var(--border-primary)

/* Timestamp */
color: var(--text-muted)

/* Log levels */
--log-info: var(--info-solid)
--log-success: var(--success-solid)
--log-warning: var(--warning-solid)
--log-error: var(--error-solid)
```

---

## Layout Patterns

### Main Layout

```
/* App container */
display: flex
min-height: 100vh

/* Sidebar */
width: 240px
flex-shrink: 0
position: fixed
height: 100vh
overflow-y: auto

/* Main content */
margin-left: 240px
flex: 1
padding: var(--space-6)
background: var(--bg-secondary)
```

### Header Bar

```
height: 64px
padding: 0 var(--space-6)
display: flex
align-items: center
justify-content: space-between
background: var(--surface-primary)
border-bottom: 1px solid var(--border-primary)
```

### Dashboard Grid

```
display: grid
gap: var(--space-6)

/* Metric cards row */
grid-template-columns: repeat(auto-fit, minmax(200px, 1fr))

/* Main content area */
grid-template-columns: 1fr 320px  /* main + sidebar panel */
```

### Split Pane (Code Viewer)

```
display: flex
gap: var(--space-4)

/* Left pane */
flex: 1
min-width: 0

/* Right pane (sidebar) */
width: 320px
flex-shrink: 0
```

---

## Transitions

```
/* Default transition */
--transition-fast: 150ms ease
--transition-base: 200ms ease
--transition-slow: 300ms ease

/* Specific transitions */
--transition-colors: color 150ms ease, background-color 150ms ease, border-color 150ms ease
--transition-transform: transform 200ms ease
--transition-opacity: opacity 200ms ease
--transition-shadow: box-shadow 200ms ease

/* Animation easings */
--ease-in: cubic-bezier(0.4, 0, 1, 1)
--ease-out: cubic-bezier(0, 0, 0.2, 1)
--ease-in-out: cubic-bezier(0.4, 0, 0.2, 1)
```

### Keyframes

```css
/* Pulse animation for status indicators */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Fade in */
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* Slide up */
@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Spin for loading indicators */
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
```

---

## Icon Guidelines

- **Size**: 16px (small), 20px (default), 24px (large)
- **Stroke width**: 1.5px - 2px
- **Style**: Outlined (not filled) for consistency
- **Color**: Inherit from parent text color

---

## Responsive Breakpoints

```
--breakpoint-sm: 640px
--breakpoint-md: 768px
--breakpoint-lg: 1024px
--breakpoint-xl: 1280px
--breakpoint-2xl: 1536px
```

### Sidebar behavior

- `< 1024px`: Collapse to icon-only (64px width)
- `< 768px`: Hidden by default, toggle to overlay

---

## Z-Index Scale

```
--z-base: 0
--z-dropdown: 100
--z-sticky: 200
--z-overlay: 300
--z-modal: 400
--z-popover: 500
--z-tooltip: 600
--z-toast: 700
```
