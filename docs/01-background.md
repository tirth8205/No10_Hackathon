# 1. Background

This document explains the legal and operational context for the project: how legal aid works for private family law, what the Domestic Abuse Gateway is, where things go wrong today, and what the Ministry of Justice (MoJ) has asked for.

## 1.1 Legal aid for private family law

Since the Legal Aid, Sentencing and Punishment of Offenders Act 2012 (LASPO) came into force on 1 April 2013, civil legal aid for most private family law children and finance matters in England and Wales has depended on evidence. It is only available where the applicant can provide specified evidence of domestic abuse or child abuse. People often call this route the "Domestic Abuse Gateway".

The evidence is prescribed in the Civil Legal Aid (Procedure) Regulations 2012:

| Regulation | Schedule | Covers | In scope for this prototype |
|---|---|---|---|
| Regulation 33 | Schedule 1 | Evidence of domestic abuse | Yes |
| Regulation 34 | Schedule 2 | Evidence relating to the protection of children | No (planned extension) |

Schedule 1 lists 22 forms of evidence: paragraphs 1 to 21 plus paragraph 6A. The LAA guidance *Evidence Requirements for Private Family Law Matters* (version 15, 15 June 2026) explains what each one must contain, and includes a checklist for each.

Three rules shape everything in this project.

1. **The list is closed.** The LAA has no discretion to accept any other kind of evidence, and the requirement cannot be waived. The only exception is economic abuse (paragraph 21), where the Director of Legal Aid Casework can accept evidence they are satisfied with.
2. **One valid piece of evidence is enough.** An applicant does not need several documents. They need one that meets every requirement of one paragraph.
3. **The evidence must exist before the decision.** It must be obtained before the legal aid determination is made. Legal aid cannot be used to pay for getting it.

## 1.2 Who is involved

| Role | Who they are | What they do in this process |
|---|---|---|
| Applicant ("A" in the regulations) | The person applying for legal aid | Asks a professional for evidence and gives it to their solicitor |
| Other party ("B" in the regulations) | The other party to the family proceedings | Usually the person alleged to have committed the abuse. Most forms of evidence must name them |
| Provider | A firm of solicitors with a legal aid contract | Advises the applicant, checks the evidence, then decides (Controlled Work) or applies to the LAA (Licensed Work) |
| LAA caseworker | Staff at the Legal Aid Agency, part of MoJ | Reviews Licensed Work applications and their evidence, and audits Controlled Work files |
| Director of Legal Aid Casework (DLAC) | The statutory decision maker at the LAA | Decides discretionary matters, including economic abuse under paragraph 21 |
| Evidence authors | GPs, nurses, police, Witness Care Units, courts, IDVAs, ISVAs, domestic abuse support organisations, councils, housing associations, the Home Office | Write the letters, reports and records that serve as evidence |

## 1.3 Controlled Work and Licensed Work

The same evidence rules apply to both types of legal aid work, but the decision is made in a different place. This difference matters for how the service is designed.

### Controlled Work

- The provider decides whether the client qualifies. They tick the relevant evidence box on the CW1 form and keep the original evidence on the client's file.
- The LAA can call for the file at any time and may check that the evidence met the requirements.
- If the evidence did not meet the requirements, or was obtained after the determination was made, the provider's claim is nil assessed. In practice, the provider is not paid for the work.

### Licensed Work

- The provider sends the evidence to the LAA with the legal aid application and must say which piece of evidence they are relying on.
- The application is rejected if the evidence does not meet the requirements, or if no prescribed evidence is submitted.

### What this means for the design

In Controlled Work, the solicitor is effectively the decision maker on evidence. Most of the value of a checking tool therefore sits with the solicitor.

In Licensed Work, the LAA caseworker also reviews the evidence. Here the value is in getting the application right first time, and in making the caseworker's review quick and consistent.

## 1.4 What goes wrong today

The MoJ problem statement describes evidence that is incomplete, wrongly categorised or missing. Applications are refused or returned for more information, which causes:

- repeated exchanges between providers and the LAA
- avoidable administration and higher operating costs
- longer processing times
- more appeals
- delayed access to justice for vulnerable people

There is currently no way to check evidence against the requirements before it is submitted, so problems are usually found at caseworker review.

The LAA guidance and the MoJ example letters show the specific ways evidence tends to fail:

| Problem | Example |
|---|---|
| Hedged professional judgement | A health professional writes "might be consistent with domestic abuse" instead of "is consistent with" |
| Source given instead of substance | A support organisation lists the matters it relied on as "victim testimony and referral" rather than describing what happened |
| Perpetrator not named | A refuge refusal letter does not say who the abuse was by, so it cannot be linked to the other party |
| Wrong paragraph claimed | A letter from a support worker is submitted as an IDVA letter |
| Status has changed | Police took no further action after an arrest, or criminal proceedings ended without a conviction |
| Relevant part not identified | A long social services or expert report is submitted without saying which part is relied on, which the guidance asks providers to do |
| Wrong author type | A counsellor writes a "health professional" letter but is not one of the professions the regulations recognise |

## 1.5 What MoJ asked for

From the challenge statement, MoJ wants an evidence-validation assistant that:

- reviews supporting documents against the Gateway requirements
- identifies which requirements appear to be satisfied
- highlights missing or weak evidence and explains why the gaps exist
- generates a concise checklist for the provider and the caseworker
- supports human decision-making rather than automating funding decisions
- creates a reusable capability that can be extended to other legal aid processes that need supporting evidence

The scenario MoJ describes is a provider who receives an automated review before submission. The review shows whether the evidence appears to meet the Gateway requirements and highlights anything missing or insufficient.

## 1.6 How MoJ will judge success

The MoJ evidence examples document says a successful screening tool would:

- correctly identify prescribed domestic abuse evidence
- reach the same conclusion as expert LAA assessors in at least 90 to 95% of cases
- reliably identify incomplete or unclear evidence
- show very low rates of false approval and false rejection
- improve consistency and reduce assessment effort without replacing final human decisions

Meeting these would show the tool is suitable for screening and triage, not as the only decision maker. Our evaluation approach is set out in [10 Test data and evaluation](10-test-data-and-evaluation.md).

## 1.7 Data provided for the hackathon

The data pack sits in the public S3 bucket `ten-ds-open-hackathon-data`, folder `Domestic Abuse Gateway (MoJ)/`. It contained three Word documents:

| File | Contents |
|---|---|
| Problem statement | The challenge, scenario and expected data sets |
| DA evidence use case | Near-identical wording, with a longer list of promised data |
| Hackathon evidence examples | 12 example letters (7 accepted, 5 rejected) for paragraphs 11, 14, 17, 18 and 19, links to Schedule 1 and the LAA guidance, and the success criteria |

The briefs also promised the following, which were not in the bucket:

- a domestic abuse legal aid application form
- valid and invalid police reports, injunctions and MARAC referrals
- expired, incomplete and poor-quality evidence
- sample provider submissions and caseworker feedback notes
- a larger set of expected validation outcomes

To fill the gap, we built a labelled synthetic data set covering all 22 evidence types. It is described in [10 Test data and evaluation](10-test-data-and-evaluation.md).

## 1.8 Sources

- The Civil Legal Aid (Procedure) Regulations 2012, Schedule 1: <https://www.legislation.gov.uk/uksi/2012/3098/schedule/1>
- LAA, *Evidence Requirements for Private Family Law Matters*, version 15 (15 June 2026): <https://assets.publishing.service.gov.uk/media/6a3122bae50716856ed4b160/Evidence_requirements_for_private_family_law_matters_guidance_version_15_15_June_2026.pdf>
- MoJ hackathon problem statement, use case and evidence examples (29 September 2026)
