# 6. Evidence requirements

This is the reference for the rules the checking engine applies. It summarises Schedule 1 to the Civil Legal Aid (Procedure) Regulations 2012 and the LAA guidance *Evidence Requirements for Private Family Law Matters*, version 15 (15 June 2026).

It is a working summary, not a substitute for the regulations and guidance. Where this document and the official text differ, the official text wins.

## 6.1 Rules that apply to every form of evidence

### Who is who

- **A** is the applicant for legal aid.
- **B** is the person with whom A was in a family relationship that gives rise to the need for legal aid, usually the other party to the proceedings.

### Family relationship

A family relationship takes the meaning in section 62 of the Family Law Act 1996. It covers people who:

- are or have been married or in a civil partnership
- are or have been cohabitants
- live or have lived in the same household (other than as employee, tenant, lodger or boarder)
- are relatives
- have agreed to marry or to enter a civil partnership, even if the agreement has ended
- have or have had an intimate personal relationship of significant duration
- are both parents of, or have parental responsibility for, the same child
- are parties to the same family proceedings

### Whose abuse the evidence can be about

For some forms of evidence, the victim can be the applicant or another person in a family relationship with B, for example a child. For others, the evidence must be about the applicant.

| Paragraphs | The evidence can be about |
|---|---|
| 1 to 10, 16, 18, 19 | The applicant, or another person in a family relationship with B |
| 11, 12, 14, 15, 17, 20, 21 | The applicant only |
| 13 | The applicant, or a person in a family relationship with the applicant |

### Other general points

- **The list is closed.** Only the forms in Schedule 1 count. The exception is paragraph 21 (economic abuse), which is decided by the Director of Legal Aid Casework.
- **One valid piece is enough.**
- **Exact wording is not required where the meaning is clear.** The guidance says this explicitly for health professional letters. MoJ's accepted examples show the same tolerance of typos and template errors elsewhere.
- **There is no general time limit**, but several forms depend on status at the time of application. Examples: B must still be under investigation or charged (paragraph 1), proceedings must not have concluded (paragraph 3), a finding must be made before the application (paragraph 9), and leave must be granted on or before the application (paragraph 20).
- **Overseas evidence** is accepted for several forms. It must be in English, or the original must be provided with a translation.
- **Long documents.** Providers must identify which parts they rely on.
- **Domestic abuse offences.** Where a paragraph refers to a domestic abuse offence, the offence must be on the GOV.UK list: <https://www.gov.uk/government/publications/domestic-violence-and-child-abuse-offences>
- **Withdrawal.** The Director can withdraw funding in some situations, for example if criminal proceedings end without conviction or a without-notice order is set aside. Funding is not withdrawn if the applicant can provide another valid piece of evidence.

## 6.2 The 22 forms of evidence

Each entry gives:

- what the regulation requires
- the documents that are typically accepted
- what the document must show, which the checking engine treats as requirements
- the most common reasons it fails

The requirement keys in brackets match the element names in the test data.

---

### Paragraph 1: arrest for a relevant domestic abuse offence

**Requires:** evidence that B has been arrested for a relevant domestic abuse offence.

**Typical documents:** police bail sheet; written or email confirmation from the police, CPS, Witness Care Unit or a `pnn.police.uk` address; an email from a legal aid provider who has spoken to the police, giving the police station and the officer's name; newspaper reports. Overseas: a letter or email from the law enforcement agency.

**Must show:**
- B named as the person arrested (`perpetrator_named`)
- the victim named and in a family relationship with B (`victim_named`)
- a domestic abuse offence (`da_offence`)
- B still under investigation, on bail or charged at the time of application (`arrest_current`)
- an acceptable source (`acceptable_source`)

**Common failures:** suspect not named; no further action taken; police attended but nobody was arrested; a provider email without the police station or officer's name.

### Paragraph 2: police caution for a domestic abuse offence

**Requires:** a relevant police caution for a domestic abuse offence.

**Typical documents:** the caution record; confirmation from the police, CPS or Witness Care Unit; a provider email after speaking to the police.

**Must show:** B named as the person cautioned; a domestic abuse offence; the victim named, except for some sexual offences where the victim is not named; that a caution was actually given.

**Common failures:** an incident log where police took no action, which the guidance says is not enough; an offence that is not on the list; a victim with no family relationship to B.

### Paragraph 3: ongoing criminal proceedings

**Requires:** evidence of relevant criminal proceedings for a domestic abuse offence that have not concluded.

**Typical documents:** charge sheet; court listing; confirmation from the police, CPS or Witness Care Unit; provider email; newspaper reports.

**Must show:** B named; B formally charged (the case does not need to be listed yet); a domestic abuse offence; proceedings not concluded; the victim named, except for some sexual offences.

**Common failures:** B released under investigation without charge, which may meet paragraph 1 instead; trial concluded with an acquittal.

### Paragraph 4: conviction for a domestic abuse offence

**Requires:** a relevant conviction for a domestic abuse offence.

**Typical documents:** Memorandum of Conviction (magistrates' court); Certificate of Conviction (Crown Court); confirmation from the police, CPS or Witness Care Unit; provider email; newspaper reports.

**Must show:** B named as the person convicted; a domestic abuse offence; the victim named, except for some sexual offences.

**Common failures:** acquittal; the person convicted is not the other party.

### Paragraph 5: bind over connected with a domestic abuse offence

**Requires:** evidence of a court order binding over B in connection with a domestic abuse offence.

**Typical documents:** court document; confirmation from the police, CPS or Witness Care Unit.

**Must show:** B named as the person bound over; the connected domestic abuse offence; the victim named where applicable.

**Common failures:** bind over not connected with a domestic abuse offence; the applicant, not B, was bound over.

### Paragraph 6: Domestic Violence Protection Notice (DVPN)

**Requires:** a DVPN issued under section 24 of the Crime and Security Act 2010 against B.

**Typical documents:** copy of the DVPN; confirmation from the police, CPS or Witness Care Unit; court document.

**Must show:** B named as the person given the notice; the protected person named.

**Common failures:** respondent redacted; notice given to the applicant rather than B. If a protection order follows, it is treated under paragraph 7.

### Paragraph 6A: Domestic Abuse Protection Notice (DAPN)

**Requires:** a DAPN given under section 22 of the Domestic Abuse Act 2021 against B.

**Context:** DAPNs are part of a pilot that started on 27 November 2024. The pilot areas are Greater Manchester; the London Boroughs of Bromley, Croydon and Sutton; Cleveland; and North Wales. The British Transport Police can also give DAPNs within those areas.

**Must show:** B named; the protected person named.

**Common failures:** notice given to the applicant. A DAPN apparently from outside the pilot areas should be referred for verification.

### Paragraph 7: relevant protective injunction

**Requires:** a relevant protective injunction. This means a court order between people in a family relationship that protects a person from harm, intimidation, threats or harassment; protects against forced marriage; prohibits contact; or concerns occupation of property. It also includes female genital mutilation protection orders and certain violent offender orders.

**Typical documents:** court document. For a restraining order made after criminal proceedings, a police document can be enough.

**Must show:** an order actually made; B as respondent; the protected person named and in a family relationship with B.

**Common failures:** only an application has been made (the order must be obtained first, though this can be on the same day); a without-notice order later set aside; an injunction against someone with no family relationship.

### Paragraph 8: undertaking

**Requires:** an undertaking given in England and Wales under section 46 or 63E of the Family Law Act 1996 (or in Scotland or Northern Ireland in place of a protective injunction) by B, provided A did not give a cross-undertaking relating to domestic abuse.

**Typical documents:** General Form of Undertaking (N117) or another court document.

**Must show:** given by B; the correct statutory basis; the person protected named; no domestic abuse-related cross-undertaking by the applicant.

**Common failures:** mutual undertakings not to use violence. A cross-undertaking about something unrelated, such as a child's schooling, does not count against the evidence.

### Paragraph 9: finding of fact

**Requires:** a copy of a finding of fact, made in UK proceedings, that there has been domestic abuse by B.

**Typical documents:** judgment or court order (this list is exhaustive).

**Must show:** a specific finding of domestic abuse by B; the victim named; if it is the only evidence, the finding was made before the legal aid application.

**Common failures:** allegations in an undefended divorce petition, which are not a finding; a fact-finding hearing listed but not yet held; allegations found not proved; a finding made after the application.

### Paragraph 10: expert report for UK proceedings

**Requires:** an expert report produced as evidence in UK proceedings for the benefit of a court or tribunal, confirming that a person in a family relationship with B was assessed as being, or at risk of being, a victim of domestic abuse by B. This includes Cafcass and Cafcass Cymru reports.

**Must show:** produced for UK proceedings; the expert's name and relevant qualifications or experience; B and the victim named; the assessment.

**Common failures:** the report makes no assessment; a private report not produced for proceedings; qualifications not stated (refer).

### Paragraph 11: letter or report from an appropriate health professional

**Requires:** a letter or report from an appropriate health professional confirming that they, or another appropriate health professional:

- examined A in person, by telephone or by video
- judged that A has, or has had, injuries or a condition consistent with being a victim of domestic abuse

**Appropriate health professionals:**

| Profession | Register |
|---|---|
| Doctors | General Medical Council |
| Nurses (including health visitors, school nurses and mental health nurses) and midwives | Nursing and Midwifery Council |
| Dentists and dental care professionals | General Dental Council |
| Paramedics, practitioner psychologists, radiographers | Health and Care Professions Council |
| Social workers | Social Work England or Social Care Wales |

Overseas professionals must be registered and licensed in their own country.

**Must show:** an appropriate, registered health professional; an examination of the applicant; an unqualified judgement of consistency; the applicant named. The perpetrator does not need to be named.

**Typical documents:** a letter; or an email that includes the professional's registration number.

**Common failures:** hedged judgement ("might be consistent"); the author is not on the list, for example a counsellor; no examination; an email with no registration number (refer).

### Paragraph 12: health professional referral to a domestic abuse support service

**Requires:** a letter or report confirming that an appropriate health professional referred A to a person who provides specialist support for victims of domestic abuse. It can come from the referring professional, a health professional with access to A's records, or the service the referral was made to.

**Must show:** the applicant named; a referral made by an appropriate health professional; to a specialist domestic abuse service.

**Common failures:** referral to a general service such as talking therapies; self-referral; referral by someone who is not a health professional.

### Paragraph 13: MARAC or other local safeguarding forum

**Requires:** a letter from any member of a multi-agency risk assessment conference (MARAC) or other suitable local safeguarding forum. It must confirm that A, or a person in a family relationship with A, is or has been at risk of harm from domestic abuse by B. A safeguarding forum must include more than one agency.

**Typical documents:** letter, report, email identifying the organisation, or minutes.

**Must show:** the author is a forum member; the victim named; B named; at risk of harm from B.

**Common failures:** perpetrator not named; the case was referred but did not meet the threshold and was not heard.

### Paragraph 14: independent domestic violence advisor (IDVA)

**Requires:** a letter from an IDVA confirming that they are providing, or have provided, support to A.

**Must show:** the author is an IDVA; confirmation of support; the applicant named.

**Common failures:** the author is not an IDVA; the applicant not named. MoJ rejected one example where the IDVA wrote "we provided" instead of "I am providing". The reason is not confirmed (see [12 Open questions](12-open-questions-and-risks.md)).

### Paragraph 15: independent sexual violence advisor (ISVA)

**Requires:** a letter from an ISVA confirming that they are providing, or have provided, support to A relating to sexual violence by B.

**Must show:** the author is an ISVA; the applicant named where possible; support relating to sexual violence; by B, who is named.

**Common failures:** perpetrator not named; violence by someone other than B.

### Paragraph 16: local authority or housing association officer

**Requires:** a letter from an officer employed by a local authority or housing association (or the equivalent in Scotland or Northern Ireland) for the purpose of supporting tenants. It must contain:

- a statement that, in their reasonable professional judgement, a person in a family relationship with B is, or is at risk of being, a victim of domestic abuse by B
- a description of the specific matters relied on
- a description of the support provided, which can be a decision such as priority need or an exemption from local connection rules

**Must show:** the officer's name and department; the victim and B named; the judgement; the matters; the support.

**Common failures:** no specific matters; no support described; hedged judgement; a private landlord or letting agent.

### Paragraph 17: organisation providing domestic abuse support services

**Requires:** a letter from an organisation providing domestic abuse support services. The letter must confirm that the organisation:

- is situated in the UK
- has been operating for an uninterrupted period of six months or more (the organisation, not the individual service)
- provided A with support in relation to A's needs as a victim, or person at risk, of domestic abuse

It must also contain:

- a statement of the author's reasonable professional judgement that A is, or is at risk of being, a victim
- a description of the specific matters relied on
- a description of the support provided
- a statement of why A needed that support

If any element is missing, the application is refused. This paragraph also covers refuge admission letters.

**Common failures:** "matters relied on" names a source rather than describing the abuse; operating for less than six months; no reason given; hedged judgement; a letter about someone other than the applicant.

### Paragraph 18: refusal of admission to a refuge

**Requires:** a letter or report from a UK domestic abuse support organisation confirming:

- that a person in a family relationship with B was refused admission to a refuge
- the date of refusal
- that they sought admission because of allegations of domestic abuse by B

The six-month operating rule from paragraph 17 does not apply. The reason for the refusal does not matter.

**Must show:** the organisation identified; B named; the victim named; the date; that admission was sought because of abuse by B.

**Common failures:** perpetrator not named; no date; admission sought for another reason, such as eviction.

### Paragraph 19: public authority

**Requires:** a letter from a public authority confirming that a person in a family relationship with B was assessed as being, or at risk of being, a victim of domestic abuse by B, or a copy of that assessment. A public authority has the meaning in section 6 of the Human Rights Act 1998. A children's services child and family assessment, or a pre-proceedings letter, can qualify.

**Must show:** the authority named; the victim and B named; the assessment.

**Common failures:** "might be a victim", which is not an assessment; an author that is not a public authority; perpetrator not named.

### Paragraph 20: leave to enter or remain as a victim of domestic abuse

**Requires:** a letter from the Home Office confirming that A has been granted leave to enter or leave to remain in the UK as a victim of domestic abuse.

**Must show:** the applicant named; leave granted as a victim of domestic abuse; granted on or before the date of the legal aid application.

**Common failures:** leave granted on another basis; application still pending; leave granted after the legal aid application.

### Paragraph 21: economic abuse

**Requires:** evidence that the Director is satisfied shows that A has been, or is at risk of being, a victim of domestic abuse by B in the form of economic abuse.

**Definition:** behaviour that has a substantial adverse effect on a person's ability to acquire, use or keep money or other property, or to obtain goods or services (section 1(4) of the Domestic Abuse Act 2021).

**Key points from the guidance:**
- It must be done to gain power and control. It is different from reasonable limits on spending, or a dispute over finances when a relationship ends.
- It can be a pattern or a single incident, and can continue after separation.
- No specific form of evidence is required. One piece may or may not be enough; several together may be.
- Where there is little or no documentary evidence, a narrative statement can be used. It should set out when the abuse started, its nature and duration, its impact, and why no other documents are available.

**Typical documents:** bank and credit statements, loan documents, letters from lenders, benefits records, messages, letters from support organisations, employers, mortgage providers or solicitors.

**Service behaviour:** always refer to a person. The service summarises the behaviour, whether it shows control, and the supporting documents.

## 6.3 Lessons from the MoJ examples

Each rejected example in the MoJ pack is almost identical to an accepted one, with one thing changed.

| Paragraph | Accepted wording | Rejected wording | What it tells us |
|---|---|---|---|
| 11 | "is consistent with domestic abuse" | "might be consistent with domestic abuse" | A hedged judgement fails |
| 19 | "was assessed as being, or at risk of being, a victim" | "might be a victim" | Possibility is not an assessment |
| 18 | Perpetrator named; abuse "by John Doe" | No perpetrator; abuse not attributed | The link to B is essential |
| 17 | Specific behaviours described | "Victim testimony and referral" | The matters must describe what happened, not where the information came from |
| 14 | "I am providing ... with support" | "we provided ... with support" | Unclear: see [12 Open questions](12-open-questions-and-risks.md) |

The accepted examples also contain typos and an unfilled "[name of applicant]" placeholder. The service must not reject evidence for that kind of error.

## 6.4 Out of scope: Schedule 2

Schedule 2 covers evidence relating to the protection of children. It has nine forms of evidence with different rules, for example that the victim is a child and B is the person identified as the risk. The checking engine is designed so these can be added as a new set of requirements without code changes.
