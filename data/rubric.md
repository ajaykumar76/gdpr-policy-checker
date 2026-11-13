# Labelling rubric: GDPR Article 13 items (documented = 1, not documented = 0)

Judged from the policy TEXT only. A bare heading, a link to another page ("see our DPO page"), or a statement that
only applies to another region does not count unless the text itself states the item. Labels for this project were
written by Claude; an independent sample is labelled by the project owner to measure agreement.

| element | GDPR ref | 1 if the policy text ... |
|---|---|---|
| controller_contact | Art. 13(1)(a) | names the legal entity responsible for the data (not just a brand) AND gives a way to contact it about privacy (postal address, email, or privacy contact form) |
| dpo_contact | Art. 13(1)(b) | mentions a data protection officer AND gives how to reach them (email, address, form). Mentioning a DPO without contact details = 0 |
| legal_basis | Art. 13(1)(c) | names at least one GDPR legal basis for processing (consent, contract, legal obligation, legitimate interests, ...) |
| recipients | Art. 13(1)(e) | says who personal data is shared with, by name or by category (service providers, affiliates, authorities, advertisers, ...) |
| international_transfers | Art. 13(1)(f) | says data is transferred outside the EEA/UK AND names a safeguard or mechanism (standard contractual clauses, adequacy decision, Data Privacy Framework, binding corporate rules, ...). "We operate globally" alone = 0 |
| retention | Art. 13(2)(a) | gives a retention period, or concrete criteria for deciding it. "As long as necessary" with nothing else = 0 (flag borderline) |
| data_subject_rights | Art. 13(2)(b) | lists access plus at least one more GDPR right (rectification, erasure, restriction, portability, objection) |
| supervisory_complaint | Art. 13(2)(d) | states the right to lodge a complaint with a supervisory / data protection authority |

Each policy also lists "borderline" elements: ones where reasonable reviewers could disagree.
Not covered (kept simple): purposes, legitimate-interest detail, statutory/contractual requirement, automated decision-making.
