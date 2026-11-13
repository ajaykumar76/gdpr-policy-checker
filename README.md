# GDPR Article 13 privacy-policy checker

Does a public privacy policy contain the information GDPR Article 13 requires? This project checks 8 elements on real policies and measures how well two checkers (regex rules vs. a local LLM) agree with hand labels. It is a screening aid, not a compliance verdict.

Elements: controller contact details, DPO contact, legal basis, recipients, international transfers (with a named safeguard), retention, data subject rights, right to complain to a supervisory authority. The scoring rubric is in `data/rubric.md`: placeholders, "click here" links and empty headings do not count; "as long as necessary" alone does not count as retention; a DPO needs contact details.

## Data
- 139 well-known domains; 98 policy pages collected, 41 failed (JavaScript pages, blocks). Policy texts are third-party content and are **not** in this repo; rerun `src/01_collect_policies.py` to rebuild them.
- Gold labels: 20 policies of 8,000 to 30,000 characters (10 dev, 10 test), 160 element labels, in `data/gold_labels.json`. **I (Claude) labelled them from the rubric; they have not been independently checked**, so there is no agreement rate. Some items are marked borderline.

## Method
- `rules`: one regex per element.
- `llm`: retrieve the 5 most relevant chunks (all-MiniLM-L6-v2), ask local llama3.2 (Ollama) for yes/no plus a quote; a "yes" counts only if the quote appears word for word in the policy.
- Protocol: tune on dev only, state the freeze rule first, run test once. Freeze rule: choose the method with the higher dev F1 unless its false-assurance rate is worse than the rules baseline. False assurance = calling an element present when it is missing (the costly error).

## Results (80 items per split, micro-averaged)
| Method | Split | Precision | Recall | F1 (95% CI) | False assurance |
|---|---|---|---|---|---|
| always "absent" | dev/test | - | - | - | accuracy 0.41 |
| rules, first version | dev | 0.90 | 0.79 | 0.84 | 0.12 |
| LLM | dev | 0.62 | 0.68 | 0.65 (0.51-0.76) | 0.61 |
| rules, after retention fix | dev | 0.91 | 0.87 | 0.89 (0.79-0.96) | 0.12 |
| rules (frozen) | **test** | 0.91 | 0.89 | **0.90 (0.83-0.95)** | 0.12 |
| LLM | **test** | 0.83 | 0.72 | 0.77 (0.64-0.88) | 0.21 |

Findings:
- The simple rules beat the 3B local model on both splits. On dev the LLM said "present" for 61% of missing elements: it treats "mentions the topic" as "meets the requirement". On test it was better on that point (21%) but missed most controller and DPO contact details (recall 2 of 8 and 0 of 2). Its behaviour swings between sets of 10 policies.
- The first retention rule caught 1 of 7 retention statements on dev. I looked at dev misses only and fixed it (periods written as words, "(3) years", long gaps, "how long do we store" headings), which lifted dev F1 from 0.84 to 0.89.
- Rules, by element on test: weakest are DPO (1 of 2) and controller contact (6 of 8); supervisory complaint had 2 false positives.

## Rules on all 98 policies (share where the element was detected)
controller contact 80%, DPO 51%, legal basis 80%, recipients 97%, transfers 71%, retention 70%, rights 91%, complaint 84%.
Treat these as rough: they are detections, not verified findings, and are not corrected for the ~12% false-assurance rate or for misses. The labelled sample (shorter policies) found a DPO in only 4 of 20 policies, so the 51% is probably too high for long policies where a word like "DPO" appears incidentally.

## Limits
- One labeller, no agreement rate. 20 policies, 10 per split; confidence intervals assume independent items and are optimistic.
- **Not a blind test:** I read all 20 labelled policies, test ones included, before writing the regexes.
- Labelled sample is biased towards medium-length policies. Some collected pages are the wrong document (a trust overview, a research policy, a shareholder statement, Apple's marketing privacy page) or have garbled characters or empty sections; labels reflect what the page says, not the company's real policy.
- The checker does not judge whether a policy is truthful or lawful.

## Run
```
pip install -r requirements.txt
python src/01_collect_policies.py
python src/03_check_eval.py --method rules --split dev
python src/03_check_eval.py --method llm --split dev      # needs Ollama + llama3.2
python src/03_check_eval.py --method rules --population
```
