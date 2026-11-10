# Recoup UI

## Run the UI

From the repository root, with the project environment installed:

```sh
RECOUP_LLM=fake .venv/bin/python -m streamlit run recoup/ui/streamlit_app.py
```

Open the local URL printed by Streamlit. Set **Database path** to an unused
`runs/ui-demo.db` for a fresh demo, then click **Load demo cases H, C and N**.
All demo data is SYNTHETIC; submissions produce MOCK receipts.

Open **H**, expand **Edit proposal** on its dispute, change the draft, and click
**Edit**, then **Approve** and **Submit** separately. Click **Advance to next due**
(initially day 3) to see revised evidence, new proposals, and updated readiness.
Use **Days** with **Advance N days** to move the demo clock, or **Run agent** to
reconsider the open case. Operations run synchronously with a spinner and refresh
the page when complete. Readiness and action gates follow design/02 §6.
