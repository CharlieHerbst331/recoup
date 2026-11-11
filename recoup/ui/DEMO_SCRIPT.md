# Recoup recording script

Aim for **2 minutes and 15 seconds**. Open [Cases](http://127.0.0.1:8501/#dashboard).
After rehearsal, reset through **Toggle navigation → Demo controls → Run settings
→ Start fresh demo**. Start with the three cases at day zero.

| Time | Show and click | Say |
| --- | --- | --- |
| 0:00 | **Cases**. Point to the action badges and open balances. | “Recoup helps finance teams investigate short-paid invoices. It brings the evidence and recommended action into one case for a reviewer to approve. This demo uses synthetic data and simulated submissions.” |
| 0:15 | **Company Data**. Show Slack and Drive, then scroll to **Finance & operations** and **External portals**. Return to **Cases**. | “Here are examples of where evidence would come from: agreements and conversations, invoice and payment records, and buyer and insurer portals.” |
| 0:30 | **Continue review** → Harbor Market → **Approve credit → Submit credit**. | “Harbor’s signed price amendment supports the $500 deduction. We approve the credit and close the balance.” |
| 0:45 | **Review Northwind Grocers**. Open **View draft & supporting documents** and click **Proof of delivery v1** under **Supporting sources**. Point to the quantity received. Scroll back to **Approve dispute → Submit dispute**. | “Northwind claimed a shortage, but the signed receiving record shows all 400 cases arrived. We dispute the $3,120 deduction and issue no credit.” |
| 1:08 | **Review Juniper Provisions** → **Approve credit → Submit credit**. The recommendation switches to **Notify insurer**. Click **Approve notice → Submit notice**. | “Juniper is owed a $2,150 pricing credit, and a separate $5,000 is still unpaid. The agent prepares the overdue notice for review.” |
| 1:28 | **Advance to next event**. Open **Details → Policy & checks** and point to **Submission blocked: Required statement**. Collapse **Details**. | “Northwind’s repayment arrived. Juniper’s claim is blocked until the account statement is available.” |
| 1:48 | **Advance to next event**. Once the claim is ready, click **Approve claim → Submit claim → Back to cases**. | “The statement arrives and Recoup updates the package for a fresh approval. We submit it for insurer review. The $5,000 remains open.” |
| 2:05 | Hold on **Cases** with Juniper at the top. | “Two balances are closed. Juniper stays at the top with a claim pending insurer review.” |

Use these details only if you need another proof point:

- **Harbor:** **Details → Documents → Authorized VP Sales price amendment**.
  The signed amendment is the basis for the credit.
- **Northwind:** **Details → Documents → Northwind repayment — bank
  confirmation** after day 3. **Details → Audit trail** shows the MOCK dispute
  receipt and the separate payment ledger entry.
- **Juniper:** **Details → Documents → Juniper account statement — net $5,000
  overdue** after day 5. **Details → Policy & checks → Recorded policy checks
  and source clauses** shows the policy evidence.
- **How the agent reached a decision:** **Details → Agent activity** shows its
  run. **Details → Assessment** shows the amounts and citations by line.

Demo behavior follows design/02 §4–§6.
