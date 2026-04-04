# Portainer UI Research for Weaver

Research conducted by studying the [Portainer CE](https://github.com/portainer/portainer)
open-source codebase (`app/react/` directory) for UI patterns applicable to Weaver's frontend (Haro).

---

## 1. Project Structure & Tech Stack

### Directory layout (`app/react/`)

| Directory                          | Purpose                                  |
| ---------------------------------- | ---------------------------------------- |
| `components/`                      | Shared UI library — very granular        |
| `components/datatables/`           | **Core** — dedicated datatable subsystem |
| `components/form-components/`      | Reusable form inputs                     |
| `components/buttons/`              | Button variants                          |
| `components/modals/`               | Dialog components                        |
| `components/PageHeader/`           | Page header with breadcrumbs             |
| `components/Widget/`               | Card/section container                   |
| `components/Badge/`, `StatusBadge` | Status indicators                        |
| `components/DashboardItem/`        | Dashboard stat cards                     |
| `components/NavTabs/`              | Tabbed navigation                        |
| `components/PaginationControls/`   | Pagination                               |
| `docker/`                          | Docker-specific pages & features         |
| `kubernetes/`                      | K8s-specific pages                       |
| `sidebar/`                         | Sidebar navigation                       |
| `hooks/`                           | React hooks                              |

### Key observations

- **Domain separation**: `docker/`, `kubernetes/`, `edge/` each have their own
  pages, queries, and components — shared UI stays in `components/`.
- **Fine-grained shared components**: even small pieces (Badge, StatusBadge,
  DashboardItem) are standalone components with their own directories.
- **Datatables as a subsystem**: the fact that tables get their own directory
  under `components/` reveals that list/table views are Portainer's dominant
  UI pattern.
- **Stack**: React, TanStack React Table v8, React Query v4, Formik, ui-router,
  lucide-react icons, toastr, Storybook, lodash.

---

## 2. Page Layout & Navigation

### Sidebar (`DockerSidebar.tsx`)

- Built from `SidebarItem` + `SidebarParent` primitives.
- Each item: `icon` (lucide-react) + `label` + `to` (route) + `data-cy` (e2e id).
- **Auth guards**: `<Authorized authorizations="...">` wraps restricted children.
- **Dynamic visibility**: menu items hide/show based on environment capabilities
  (Swarm vs standalone).
- Docker menu: Dashboard · Templates · Stacks · Services · Containers · Images ·
  Networks · Volumes · Events · Host/Swarm.

### Page structure (`PageHeader` + `Widget`)

- **PageHeader**: Breadcrumbs + page title + optional reload button (with loading
  spinner).
- **Widget**: Generic section container; provides `titleId` via context for a11y.
- Standard page skeleton: `PageHeader` → one or more `Widget` → content
  (typically a `Datatable`).

---

## 3. Datatable System — Core Design

This is Portainer's most sophisticated shared component. Every list page
(containers, images, volumes, stacks, etc.) uses the same composable table.

### Architecture

```
Datatable (top-level orchestrator)
├── DatatableHeader
│   ├── SearchBar (global text filter)
│   ├── Table.Actions (bulk-action buttons — render prop)
│   └── Table.TitleActions (settings gear — render prop)
├── DatatableContent
│   ├── TableHeaderRow (sortable column headers)
│   └── TableRow (data rows with optional checkbox)
└── DatatableFooter
    ├── PaginationControls
    └── SelectedRowsCount
```

### Key design patterns

#### a) TanStack React Table v8 — direct integration

```tsx
const tableInstance = useReactTable({
  data,
  columns,
  getCoreRowModel: getCoreRowModel(),
  ...extendTableOptions(opts),
});
```

Not an abstracted wrapper — consumer code works directly with the TanStack API,
and `extendTableOptions` simply merges additional options.

#### b) Column definitions in dedicated files

Each table has a `columns/` subdirectory. Individual columns or small groups are
in separate files; a `useColumns()` hook assembles and returns the final array.

```
ContainersDatatable/
  columns/
    index.tsx     ← useColumns() hook
    state.tsx     ← status badge column
    quick-actions.tsx
    name.tsx
    ...
```

#### c) Actions and settings as render props

```tsx
<Datatable
  dataset={containers}
  columns={columns}
  renderTableActions={(selectedRows) => (
    <ContainersDatatableActions items={selectedRows} />
  )}
  renderTableSettings={(table) => (
    <ContainerTableSettings settings={tableState} />
  )}
/>
```

- **Bulk actions** live in the header bar (not per-row).
- **Settings** (auto-refresh interval, column visibility, quick-action toggles)
  appear in a dropdown adjacent to the search bar.

#### d) State persistence — localStorage

```tsx
const storeDef = createStore(storageKey, defaultState);
const [tableState, setTableState] = useTableState(storeDef);
```

Persisted state includes: search term, sort column/direction, page size, column
visibility toggles, auto-refresh interval.

#### e) Auto-refresh

`TableSettingsMenuAutoRefresh` offers 10 s / 30 s / 1 min / 2 min / 5 min.
The chosen rate feeds into the React Query hook:

```tsx
const query = useContainers(envId, {
  autoRefreshRate: tableState.autoRefreshRate * 1000,
});
// internally → useQuery({ refetchInterval: autoRefreshRate })
```

#### f) Column visibility menu

Users toggle columns on/off from a settings dropdown. State is persisted via the
same `createStore` mechanism.

#### g) Per-row quick actions

Small icon buttons (Logs, Inspect, Stats, Console, Attach) appear on each row.
Users can configure which quick actions are visible in the table settings.

### Bulk-action design (`ContainersDatatableActions`)

- **ButtonGroup**: Start | Stop | Kill | Restart | Pause | Resume | Remove
- **Smart disable logic**: each button scans selected items' statuses.
  - `Start` enabled only when selection contains stopped/exited containers.
  - `Stop` enabled only when selection contains running containers.
- **Auth guard**: each button wrapped in `<Authorized>`.
- **Execution**: `for` loop over selected items; each success/failure produces
  its own toast notification.
- **Post-action**: `router.stateService.reload()` refreshes the route.

### Portainer vs Weaver — current gap

| Aspect            | Portainer                         | Weaver (Haro)                  |
| ----------------- | --------------------------------- | ------------------------------ |
| List component    | Reusable `<Datatable>`            | Hand-rolled `<table>` per page |
| Bulk actions      | Header ButtonGroup (status-aware) | Per-row text buttons only      |
| Search            | Built-in SearchBar                | None                           |
| Pagination        | Built-in with page-size selector  | Basic prev/next                |
| Column sorting    | Built-in clickable headers        | None                           |
| Auto-refresh      | Configurable polling interval     | SSE push (no polling needed)   |
| Column visibility | User-toggleable                   | Fixed columns                  |
| State persistence | localStorage                      | None                           |

---

## 4. Dashboard Design

`DashboardView.tsx` renders:

- `PageHeader title="Dashboard"` with breadcrumbs
- `DashboardGrid` (CSS grid container) with `DashboardItem` cards:
  - Stacks, Containers, Images, Volumes, Networks
  - Each card: icon + count + link + optional child info component
    (e.g., `ContainerStatus` breakdown, `ImagesTotalSize`)

### vs Weaver

Weaver's Dashboard already follows a similar pattern (4× `StatCard` in a
responsive grid + `ActivityFeed`). The main gap is that Weaver's cards are
simpler — no drill-down child components or clickable links to filtered views.

---

## 5. Forms & Workflows (Container CreateView)

### Formik + NavTabs tabbed form

- **Outer layer**: `<Formik>` wraps the entire form with a single values tree.
  - `useValidation()` returns a Yup schema.
  - `useInitialValues()` computes defaults (supports "duplicate" mode for
    cloning an existing container).
  - `useCreateOrReplaceMutation()` handles submission.
- **Inner `CreateInnerForm`**: `<Form>` containing:
  - `BaseForm` (top half — name, image selection)
  - `Widget` (bottom half — advanced settings in a card)
- **NavTabs** in `pills` mode: Commands | Volumes | Network | Env | Labels |
  Restart | Runtime & Resources | Capabilities
  - Each tab is an independent component writing back via
    `setFieldValue('namespace.field', value)`.
  - Tab switches preserve state (no remount).
- **Destructive confirmation**: replacing an existing container triggers
  `confirmDestructive()` modal.

### vs Weaver

- Weaver uses **RJSF** (React JSON Schema Form) for dynamic strategy
  configuration — more appropriate for schema-driven, variable-shape forms.
- Portainer uses **Formik + hand-built tabs** — better suited for fixed-structure
  forms with known fields.
- **Takeaway**: keep RJSF for strategy params. The Widget + NavTabs layout is
  worth borrowing only if future config schemas grow complex enough to warrant
  sectioning.

---

## 6. Notification System

### Portainer notifications

- `toastr` library: 3 s auto-dismiss (success), 6 s (warning/error), with a
  progress bar.
- **XSS protection**: `sanitize-html` + `_.escape()` double-sanitize all
  messages before rendering.
- **Persistent history**: `notificationsStore` (Zustand) stores notifications
  keyed by userId. A notification center lets users review past alerts.
- **Error extraction**: `pickErrorMsg(e)` walks a priority list of nested
  property paths (`err.data.details`, `data.message`, `message`, etc.) to
  extract the most useful error string.
- Global helpers: `notifySuccess(title, text)`, `notifyError(title, e)`,
  `notifyWarning(title, text)`.

### vs Weaver

Weaver also uses Zustand for notifications + a custom `Toast` component with
5 s auto-dismiss. The main gaps:

- No persistent notification history (once a toast disappears, it's gone).
- No notification center / review panel.
- Simpler error extraction logic.

---

## 7. Actionable Recommendations for Weaver

### P0 — High value / Low–medium cost

| #     | Pattern                          | Current state                                                              | Recommendation                                                                                                                                                                                  |
| ----- | -------------------------------- | -------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **A** | **Reusable DataTable component** | RunsPage and OrdersPage each hand-roll `<table>` with no sorting or search | Extract a shared `<DataTable>` powered by TanStack Table v8. Include: sortable column headers, global search bar, column definitions imported from `columns/` files.                            |
| **B** | **Bulk actions**                 | Per-row Start/Stop text buttons                                            | Add row checkboxes → header ButtonGroup (Start / Stop / Delete). Smart enable/disable based on selected items' statuses. Especially useful for batch backtests. Depends on DataTable component. |
| **C** | **Page shell standardization**   | Every page repeats ~40 lines of loading/error/title boilerplate            | Extract `<PageShell title query>` — handles loading skeleton, error panel, page title, and optional breadcrumbs. Similar to Portainer's PageHeader + Widget hierarchy.                          |

### P1 — Medium value / Medium cost

| #     | Pattern                     | Recommendation                                                                                                                                                       |
| ----- | --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **D** | **Table state persistence** | Store search term, sort direction, page size in localStorage via a small `createTableStore(key)` helper. Restores user preferences on reload.                        |
| **E** | **Notification center**     | Keep toast notifications in Zustand history. Add a bell icon / drawer so users can review past alerts (especially important for async backtest completion & errors). |
| **F** | **Row quick actions**       | Replace text buttons with lucide-react icon buttons (view details / view logs / clone config / delete) + tooltips on hover.                                          |

### P2 — Future consideration

| #     | Pattern                           | Notes                                                                                                                                        |
| ----- | --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| **G** | **Widget container component**    | Replace repeated `bg-slate-800 rounded-lg border...` divs with a semantic `<Widget>` / `<Widget.Title>` / `<Widget.Body>`.                   |
| **H** | **Tabbed config forms (NavTabs)** | Only needed if strategy `config_schema` grows complex enough to warrant sectioning. Keep RJSF — it's better than Formik for dynamic schemas. |
| **I** | **Column visibility menu**        | User-toggleable columns, persisted to localStorage. Depends on DataTable component.                                                          |

### Patterns NOT recommended to adopt

| Pattern            | Reason                                                                            |
| ------------------ | --------------------------------------------------------------------------------- |
| ui-router          | Weaver uses react-router v7 which is more modern.                                 |
| Formik over RJSF   | RJSF's schema-driven approach is a better fit for dynamic strategy configuration. |
| toastr library     | Weaver's custom Toast is sufficient and avoids an aging dependency.               |
| AngularJS patterns | Portainer still carries significant AngularJS legacy code — skip entirely.        |

---

## Appendix: Portainer Source Files Studied

| File                                                                                      | Key content                         |
| ----------------------------------------------------------------------------------------- | ----------------------------------- |
| `app/react/sidebar/DockerSidebar.tsx`                                                     | Sidebar navigation with auth guards |
| `app/react/components/PageHeader/PageHeader.tsx`                                          | Breadcrumbs + title + refresh       |
| `app/react/components/Widget/Widget.tsx`                                                  | Section container with context      |
| `app/react/components/datatables/Datatable.tsx`                                           | Core composable table               |
| `app/react/components/datatables/DatatableHeader.tsx`                                     | Search + actions + settings         |
| `app/react/components/datatables/TableSettingsMenuAutoRefresh.tsx`                        | Auto-refresh UI                     |
| `app/react/docker/containers/ListView/ContainersDatatable/ContainersDatatable.tsx`        | Containers list page                |
| `app/react/docker/containers/ListView/ContainersDatatable/ContainersDatatableActions.tsx` | Bulk actions (Start/Stop/Kill/etc)  |
| `app/react/docker/containers/ListView/ContainersDatatable/columns/state.tsx`              | Status badge column                 |
| `app/react/docker/containers/ListView/ContainersDatatable/columns/quick-actions.tsx`      | Per-row quick actions               |
| `app/react/docker/containers/ListView/ContainersDatatable/columns/index.tsx`              | Column assembly                     |
| `app/react/docker/containers/queries/useContainers.ts`                                    | React Query with autoRefreshRate    |
| `app/react/docker/DashboardView/DashboardView.tsx`                                        | Dashboard with stat cards           |
| `app/portainer/services/notifications.ts`                                                 | toastr notification system          |
| `app/react/docker/containers/CreateView/CreateView.tsx`                                   | Formik container creation form      |
| `app/react/docker/containers/CreateView/CreateInnerForm.tsx`                              | Tabbed form layout                  |
| `app/react/components/NavTabs/NavTabs.tsx`                                                | Generic tab navigation component    |
