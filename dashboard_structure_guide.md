# Dashboard Standardization & Design System Guide

This document serves as the official guide for the "Premium" dashboard layout used in the Gestaosuas project. All new directorate modules must adhere to these standards to ensure visual consistency and a high-end user experience.

## 1. Global Layout Structure

The application follows a "Viewport-Locked" layout to avoid unnecessary scrollbars and maintain a professional "app-like" feel.

### 1.1 The App Shell
- **Body Class**: `.dashboard-fit-vh` (Sets `height: 100vh` and `overflow: hidden`).
- **Navbar**: Absolute positioned at the top.
- **Main Container**: Flexbox-based to distribute space between the header and the main card.

### 1.2 Monitoring Header (`.monitoring-header-container`)
The header provides the module's identity and primary filters.
- **Gradients**:
  - **Emerald (CRAS)**: `linear-gradient(135deg, #064e3b, #10b981)`
  - **Indigo (Benefícios)**: `linear-gradient(135deg, #1e1b4b, #4338ca)`
  - **Amber (SINE/CP)**: `linear-gradient(135deg, #78350f, #d97706)`
- **Padding**: `24px 2% 80px`.
- **Align Items**: `center` (Title and Actions on the same line).

### 1.3 Compact Action Controls
To maximize utility area, all header controls are standardized at **36px** height.
- **Classes**: `.filter-select`, `.btn-primary-premium`, `.pill`.
- **Spacing**: `gap: 6px` between elements.
- **Typography**: `11px` to `13px` with `font-weight: 600/700`.

## 2. The Main Content Card (`.monitoring-main-card`)

This is the primary workspace where charts and data reside.
- **Style**: White background, `border-radius: 32px`, subtle shadow.
- **Overlap**: Positioned `-60px` relative to the header.
- **Responsive Handling**:
  - Should use `flex: 1` to fill remaining vertical space.
  - Internal scrolling allowed via `overflow-y: auto`.

## 3. Metric Indicators (`.indicator-panel`)
Standard panels for quick statistics.
- **Icon**: Lucide icons inside a themed background circle.
- **Typography**: Large font-size for numbers, semi-transparent labels for descriptions.
- **Animations**: Use subtle hover lift effects (`transform: translateY(-4px)`).

## 4. Charts & Data Visualization
- **Library**: Chart.js.
- **Configuration**:
  - `maintainAspectRatio: false` (Crucial for fitting inside containers).
  - Use custom colors matching the directorate theme.
  - Integration with `ChartDataLabels` for key metrics.

## 5. CSS Utility Classes (Standard)
Refer to `static/css/app.css` for these core definitions:
- `.monitoring-header-content`
- `.monitoring-header-actions`
- `.filter-row-group`
- `.visit-filter-form`
- `.dashboard-split-layout` (Side-by-side metrics/charts).

---
*Last updated: May 13, 2026 - Migration to Premium Emerald Design.*
