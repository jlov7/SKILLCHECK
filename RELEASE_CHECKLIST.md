# Release Checklist (v1)

- [ ] Core user journeys are coherent end-to-end (happy path + key failure states) with clear UX and copy.
- [ ] Onboarding is implemented (first-run, empty states, progressive disclosure).
- [ ] Help is implemented (in-app help/tooltips + a minimal docs/help page).
- [ ] Quality gates: tests exist for critical logic and key UI flows, lint/typecheck/build pass, and CI is green.
- [ ] Accessibility basics: keyboard navigation for primary flows, sensible focus states, labels/aria where needed.
- [ ] Performance basics: no obvious slow pages, avoid unnecessary re-renders, reasonable bundle size for stack.
- [ ] Security hygiene: no secrets in repo, validate inputs, safe error handling, auth boundaries respected (if applicable).
- [ ] Docs: README includes local setup + run + test + deploy notes + env vars.
