# Recoup UI

Run from the repository root with the project environment installed:

```sh
RECOUP_LLM=fake .venv/bin/python -m streamlit run recoup/ui/streamlit_app.py
```

The workbench uses a light theme, a customer case list, and three tabs:
**Review**, **Documents**, and **Activity**. Data is SYNTHETIC, actions are MOCK,
and the visible LLM mode identifies the current provider.

For a fresh walkthrough, expand **Demo controls** in the sidebar, set
**Database path** to an unused path such as `runs/ui-demo.db`, and click
**Load demo cases H, C and N**. Select **Northwind Grocers** from the case list.

In **Review**, expand **Edit proposal**, revise the draft, and click
**Save changes**. **Approve draft** and **Submit MOCK action** are separate
steps. Other actions, earlier versions, decision details, and document
checklists are available in their own expandable sections.

Use **Documents** to inspect current and earlier document versions, confirm
extracted fields, or **Add supporting document** using a BundleDoc JSON
specification and optional file. **Activity** shows the case history.

Expand **Simulation controls** for **Advance to next due** (initially day 3),
**Advance N days**, or **Run agent** for the selected case. Operations show a
spinner and refresh the page when complete. UI behavior follows design/02 §6.
The theme is configured in `.streamlit/config.toml`; no extra frontend packages
are required.
