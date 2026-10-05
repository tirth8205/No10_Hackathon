# Disagreements

## P1-non_da_offence-01 / D1 (para 1)
- expected **needs_change**, predicted **needs_change**
- label reason: The arrest was for a road traffic offence, not a domestic abuse offence.
- elements: victim_named: expected included, got missing
- flags: quote_multi_span

## P1-no_arrest_words_of_advice-01 / D1 (para 1)
- expected **needs_change**, predicted **needs_change**
- label reason: Police attended and gave words of advice; nobody was arrested. A call-out with no police action is not sufficient.
- elements: perpetrator_named: expected included, got missing; victim_named: expected included, got missing; da_offence: expected included, got missing
- flags: quote_multi_span

## P2-non_da_offence-01 / D1 (para 2)
- expected **needs_change**, predicted **needs_change**
- label reason: Caution was for drug possession, not a domestic abuse offence.
- elements: victim_named: expected included, got missing

## P2-incident_log_no_action-01 / D1 (para 2)
- expected **needs_change**, predicted **needs_change**
- label reason: This is an incident log where police took no action; no caution was given.
- elements: perpetrator_named: expected included, got missing; da_offence: expected included, got missing; victim_named: expected included, got missing

## P3-not_charged-01 / D1 (para 3)
- expected **needs_change**, predicted **needs_change**
- label reason: B is released under investigation with no charging decision. This would meet para 1 (arrest) instead.
- elements: perpetrator_named: expected included, got missing; da_offence: expected included, got missing; not_concluded: expected included, got missing; victim_named: expected included, got missing

## P3-non_da_offence-01 / D1 (para 3)
- expected **needs_change**, predicted **needs_change**
- label reason: B is charged with a drugs offence, not a domestic abuse offence.
- elements: victim_named: expected included, got missing

## P4-non_da_offence-01 / D1 (para 4)
- expected **needs_change**, predicted **needs_change**
- label reason: Conviction is for a public order offence with no victim.
- elements: victim_named: expected included, got missing

## P5-valid-01 / D1 (para 5)
- expected **meets**, predicted **needs_caseworker**
- label reason: All required elements present.
- elements: perpetrator_bound_over: expected included, got unclear
- flags: quote_not_found, quote_multi_span

## P5-benign_defects-01 / D1 (para 5)
- expected **meets**, predicted **needs_caseworker**
- label reason: Still valid: . MoJ accepted letters with similar errors.
- elements: perpetrator_bound_over: expected included, got unclear
- flags: quote_not_found, quote_multi_span

## P5-unconnected_offence-01 / D1 (para 5)
- expected **needs_change**, predicted **needs_change**
- label reason: Bind over followed a drunk and disorderly charge with no domestic abuse connection.
- elements: victim_named: expected included, got missing
- flags: quote_multi_span

## P5-applicant_bound_over-01 / D1 (para 5)
- expected **needs_change**, predicted **needs_change**
- label reason: It is the applicant, not B, who was bound over.
- elements: victim_named: expected included, got missing
- flags: quote_multi_span, name_mismatch

## P6-applicant_is_respondent-01 / D1 (para 6)
- expected **needs_change**, predicted **needs_change**
- label reason: The notice was given to the applicant to protect B, not the other way round.
- elements: protected_party_named: expected included, got missing
- flags: name_mismatch

## P6A-applicant_is_respondent-01 / D1 (para 6A)
- expected **needs_change**, predicted **needs_change**
- label reason: The notice was given to the applicant to protect B.
- elements: protected_party_named: expected included, got missing
- flags: name_mismatch

## P7-application_only-01 / D1 (para 7)
- expected **needs_change**, predicted **needs_change**
- label reason: This is only an application (FL401); no order has been made yet.
- elements: court_document: expected included, got missing
- flags: quote_fuzzy_match

## P7-set_aside-01 / D1 (para 7)
- expected **needs_change**, predicted **needs_change**
- label reason: The without-notice order was set aside at the return hearing.
- elements: respondent_is_other_party: expected included, got unclear
- flags: quote_not_found

## P7-unrelated_respondent-01 / D1 (para 7)
- expected **needs_change**, predicted **needs_change**
- label reason: Injunction is against a neighbour, not B, and there is no family relationship.
- elements: order_made_and_in_force: expected included, got unclear
- flags: name_mismatch

## P8-mutual_cross_undertaking-01 / D1 (para 8)
- expected **needs_change**, predicted **needs_change**
- label reason: Both parties gave undertakings not to use violence, which is a relevant cross-undertaking.
- elements: beneficiary_named: expected included, got unclear
- flags: quote_not_found

## P8-given_by_applicant-01 / D1 (para 8)
- expected **needs_change**, predicted **needs_change**
- label reason: The undertaking was given by the applicant, not B.
- elements: beneficiary_named: expected included, got missing; no_relevant_cross_undertaking: expected included, got missing
- flags: quote_multi_span, name_mismatch

## P9-valid-01 / D1 (para 9)
- expected **meets**, predicted **needs_caseworker**
- label reason: All required elements present.
- elements: victim_named: expected included, got unclear
- flags: quote_multi_span

## P9-valid-02 / D1 (para 9)
- expected **meets**, predicted **needs_caseworker**
- label reason: All required elements present.
- elements: victim_named: expected included, got unclear
- flags: quote_multi_span, quote_not_found

## P9-benign_defects-01 / D1 (para 9)
- expected **meets**, predicted **needs_caseworker**
- label reason: Still valid: . MoJ accepted letters with similar errors.
- elements: victim_named: expected included, got unclear
- flags: quote_not_found

## P9-undefended_divorce_petition-01 / D1 (para 9)
- expected **needs_change**, predicted **needs_change**
- label reason: Allegations in an undefended divorce petition are not a finding of fact.
- elements: court_document: expected included, got unclear; made_before_application: expected included, got missing
- flags: quote_fuzzy_match

## P9-finding_after_application-01 / D1 (para 9)
- expected **needs_change**, predicted **needs_change**
- label reason: The finding post-dates the application, so it can't be the only evidence.
- elements: victim_named: expected included, got unclear

## P9-hearing_only_listed-01 / D1 (para 9)
- expected **needs_change**, predicted **needs_change**
- label reason: A fact-finding hearing has only been listed; no findings have been made.
- elements: made_before_application: expected included, got missing; victim_named: expected included, got unclear
- flags: quote_not_found

## P9-allegations_not_proved-01 / D1 (para 9)
- expected **needs_change**, predicted **needs_change**
- label reason: The court found the allegations not proved.
- elements: victim_named: expected included, got missing

## P11-counsellor_not_ahp-01 / D1 (para 11)
- expected **needs_change**, predicted **needs_change**
- label reason: A BACP counsellor is not an appropriate health professional under the regulations.
- elements: examined_applicant: expected included, got missing

## P12-self_referral-01 / D1 (para 12)
- expected **needs_change**, predicted **needs_change**
- label reason: The applicant self-referred; no health professional made the referral.
- elements: author_eligible: expected included, got unclear
- flags: quote_not_found

## P13-perpetrator_not_named-01 / D1 (para 13)
- expected **needs_change**, predicted **needs_change**
- label reason: Risk is attributed to 'a former partner' who is not named.
- elements: at_risk_of_harm_from_other_party: expected included, got missing

## P13-threshold_not_met-01 / D1 (para 13)
- expected **needs_change**, predicted **needs_change**
- label reason: Case did not meet the MARAC threshold and was not heard; no risk confirmed.
- elements: victim_named: expected included, got unclear; perpetrator_named: expected included, got missing
- flags: quote_not_found

## P18-perpetrator_not_named-01 / D1 (para 18)
- expected **needs_change**, predicted **needs_change**
- label reason: Mirrors the MoJ rejected example: no perpetrator named, so no link to B.
- elements: sought_because_of_abuse_by_other_party: expected included, got unclear

## P19-perpetrator_not_named-01 / D1 (para 19)
- expected **needs_change**, predicted **needs_change**
- label reason: No perpetrator is named.
- elements: assessed_victim_or_at_risk: expected included, got missing

## P20-application_pending-01 / D1 (para 20)
- expected **needs_change**, predicted **needs_change**
- label reason: The immigration application is still pending; no leave has been granted.
- elements: leave_as_da_victim: expected included, got missing

## P21-ordinary_financial_dispute-01 / D1 (para 21)
- expected **needs_caseworker**, predicted **needs_caseworker**
- label reason: Describes an ordinary disagreement about dividing assets, not controlling behaviour.
- elements: perpetrator_named: expected included, got missing; economic_behaviour_described: expected included, got missing; corroboration_or_explanation: expected included, got unclear

## X-wrong_para_17_claimed_as_14 / D1 (para 14)
- expected **needs_change**, predicted **needs_change**
- label reason: A support-organisation letter submitted as an IDVA letter. It is not from an IDVA, but it does meet para 17.
- elements: confirms_support: expected included, got missing

## X-name_mismatch / D1 (para 17)
- expected **needs_caseworker**, predicted **needs_caseworker**
- label reason: Letter names 'Amira Hussain' but the application is for 'Amira Hussaun'. Check identity before relying on it.
- elements: supported_applicant: expected included, got unclear; professional_judgement: expected included, got unclear; specific_matters: expected included, got unclear; support_description: expected included, got unclear; reason_for_support: expected included, got unclear
- flags: victim_name_mismatch

## X-bundle_all_invalid / D2 (para 18)
- expected **needs_change**, predicted **needs_change**
- label reason: No perpetrator named.
- elements: sought_because_of_abuse_by_other_party: expected included, got unclear

## X-child_victim_not_allowed_para17 / D1 (para 17)
- expected **needs_change**, predicted **needs_change**
- label reason: Para 17 must relate to the applicant themselves; this letter is about the child.
- elements: specific_matters: expected included, got missing; support_description: expected included, got missing; reason_for_support: expected included, got missing; applicant_named: expected included, got missing
