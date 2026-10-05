#!/usr/bin/env python3
"""
Synthetic test cases for the MoJ Domestic Abuse Gateway challenge (10DS hackathon).

Every case is labelled by construction. A compliant document is written from the
checklist for its Schedule 1 paragraph in the LAA "Evidence Requirements for Private
Family Law Matters" guidance (v15, June 2026). Mutated copies then break exactly one
required element, or add a harmless defect that should NOT cause a rejection.

All people, organisations, addresses and reference numbers are fictional.

    python3 generate_da_evidence.py                          # writes synthetic_cases.json
    python3 generate_da_evidence.py --seed 7 --valid 4 --out more_cases.json

Labels
  document outcome / expected_overall:  pass | fail | refer   (refer = needs a human or more info)
  element status:                       met  | not_met | unclear
"""
import argparse
import json
import random
import re
from datetime import date, timedelta

# --------------------------------------------------------------------------- pools
F_FIRST = ["Sarah", "Aisha", "Emma", "Priya", "Chloe", "Fatima", "Hannah", "Grace", "Leah",
           "Zainab", "Olivia", "Megan", "Natalia", "Bethan", "Amira", "Kerry"]
M_FIRST = ["Daniel", "James", "Mohammed", "Ryan", "Liam", "Kwame", "Thomas", "Adam", "Craig",
           "Lewis", "Ben", "Arjun", "Piotr", "Rhys", "Imran", "Dean"]
SURN = ["Okafor", "Hughes", "Patel", "Kowalski", "Brennan", "Ahmed", "Fletcher", "Mensah", "Davies",
        "Clarke", "Hussain", "Walsh", "Thompson", "Begum", "Morgan", "Novak", "Reid", "Shah"]
KIDS = ["Ella", "Noah", "Maya", "Leo", "Isla", "Zayn", "Ruby", "Oscar", "Amelia", "Kai"]
CITIES = {"Leeds": "West Yorkshire Police", "Bristol": "Avon and Somerset Constabulary",
          "Cardiff": "South Wales Police", "Nottingham": "Nottinghamshire Police",
          "Sheffield": "South Yorkshire Police", "Norwich": "Norfolk Constabulary",
          "Reading": "Thames Valley Police", "Leicester": "Leicestershire Police",
          "Plymouth": "Devon and Cornwall Police"}
DAPN_PILOT = [("Manchester", "Greater Manchester Police"), ("Croydon", "Metropolitan Police Service"),
              ("Middlesbrough", "Cleveland Police"), ("Wrexham", "North Wales Police")]
STREETS = ["Victoria Road", "Mill Lane", "Church Street", "Park Avenue", "Station Road",
           "Queens Crescent", "Oakfield Drive", "Albert Terrace"]
ORGS = ["Northgate Domestic Abuse Service", "Riverside Safe Futures", "Harbour Light Women's Centre",
        "Calder Valley DA Partnership", "New Pathways Support Trust", "Safe Haven Outreach"]
COUNCILS = ["Eastbrook Borough Council", "Harlow Vale District Council", "Westmoor City Council",
            "Ashby Fields Council"]
HAS = ["Meadowbank Housing Association", "Ironbridge Homes", "Kestrel Housing Group"]
SOLS = ["Hartley & Moss Solicitors", "Greenacre Family Law LLP", "Pemberton Clarke Solicitors",
        "Ashworth Legal"]
PRACTICES = ["Riverside Medical Centre", "Kingsway Surgery", "Northfield Health Centre",
             "Elm Tree Medical Practice"]
DA_OFFENCES = [
    "assault occasioning actual bodily harm (section 47 Offences Against the Person Act 1861)",
    "controlling or coercive behaviour in an intimate or family relationship (section 76 Serious Crime Act 2015)",
    "common assault (section 39 Criminal Justice Act 1988)",
    "harassment (section 2 Protection from Harassment Act 1997)",
    "threats to kill (section 16 Offences Against the Person Act 1861)",
    "criminal damage (section 1 Criminal Damage Act 1971)",
]
NON_DA = [
    "driving whilst disqualified (section 103 Road Traffic Act 1988)",
    "possession of a controlled drug (section 5 Misuse of Drugs Act 1971)",
    "being drunk and disorderly in a public place (section 91 Criminal Justice Act 1967)",
]
MATTERS = [
    "{A_first} disclosed that {B_first} regularly checked {a_her} phone, controlled who {a_she} could see "
    "and threatened to take {CH_first} away if {a_she} left",
    "{A_first} described being pushed against a wall and slapped during an argument in {month}, and "
    "repeated threatening text messages from {B_first} since the separation",
    "a DASH risk assessment completed on {d60} scored 16 (high risk); {A_first} described escalating "
    "jealousy, verbal abuse and one incident in which {B_first} held {a_herx} by the throat",
    "{A_first} told us that {B_first} restricted {a_her} access to money, stopped {a_herx} from working "
    "and called {a_herx} worthless in front of {CH_first}",
]
SUPPORT = [
    "risk assessment, safety planning and weekly one-to-one outreach sessions",
    "a place on our 12-week recovery programme, help to apply for a non-molestation order and a "
    "referral for counselling",
    "safety planning, a referral to have new locks fitted, and support to report incidents to the police",
]
REASONS = [
    "{a_she} was living in fear of {B_first} and did not feel safe in {a_her} home",
    "{a_she} had fled the family home with {CH_first} and needed help to stay safe",
    "the abuse was escalating and {a_she} needed help to plan for {a_her} own and {CH_first}'s safety",
]
INTRO = ("I understand that {A} wishes to access legal aid for a family dispute as a victim of domestic "
         "abuse. For this reason, I have been asked to provide a letter in accordance with regulation 33 "
         "and Schedule 1 of the Civil Legal Aid (Procedure) Regulations 2012 (as amended).")


def fmt(d):
    return f"{d.day} {d.strftime('%B %Y')}"


def other_name(r, like_gender_of_b, c):
    pool = M_FIRST if (c["b_he"] == "he") == like_gender_of_b else F_FIRST
    return f"{r.choice(pool)} {r.choice(SURN)}"


def mkctx(r):
    a_f = r.random() < 0.8
    a_first = r.choice(F_FIRST if a_f else M_FIRST)
    b_first = r.choice(M_FIRST if a_f else F_FIRST)
    a_sur, b_sur = r.sample(SURN, 2)
    city = r.choice(list(CITIES))
    force = CITIES[city]
    app_date = date(2026, 9, 1) + timedelta(days=r.randint(0, 34))
    ch_first = r.choice(KIDS)
    others = [s for s in SURN if s not in (a_sur, b_sur)]
    officer = f"{r.choice(F_FIRST + M_FIRST)} {r.choice(others)}"
    sol = r.choice(SOLS)
    c = dict(
        A=f"{a_first} {a_sur}", A_first=a_first,
        B=f"{b_first} {b_sur}", B_first=b_first,
        CH=f"{ch_first} {b_sur}", CH_first=ch_first,
        a_she="she" if a_f else "he", a_her="her" if a_f else "his", a_herx="her" if a_f else "him",
        b_he="he" if a_f else "she", b_his="his" if a_f else "her", b_him="him" if a_f else "her",
        rel=r.choice(["former partner", "former spouse", "former cohabitant"]),
        city=city, CITY_UP=city.upper(), force=force, force_upper=force.upper(),
        force_dom=re.sub(r"[^a-z]", "", force.lower().replace("police", "").replace("constabulary", "")),
        org=r.choice(ORGS), council=r.choice(COUNCILS), ha=r.choice(HAS), practice=r.choice(PRACTICES),
        sol=sol, sol_email=f"family@{re.sub(r'[^a-z]', '', sol.lower())[:14]}.co.uk",
        officer=officer, author=f"{r.choice(F_FIRST + M_FIRST)} {r.choice(others)}",
        app_date=app_date,
        a_dob=fmt(date(r.randint(1978, 2000), r.randint(1, 12), r.randint(1, 28))),
        b_dob=fmt(date(r.randint(1975, 1998), r.randint(1, 12), r.randint(1, 28))),
        crime_ref=f"{r.choice('ABCDEFGHJK')}{r.choice('ABCDEFGHJK')}/{r.randint(10000, 99999)}/26",
        case_no=f"{city[:2].upper()}{r.randint(10, 99)}P{r.randint(10000, 99999)}",
        address=f"{r.randint(2, 140)} {r.choice(STREETS)}, {city}",
        gmc=str(r.randint(6000000, 7999999)),
        nmc=f"{r.randint(10, 99)}{r.choice('ABCDEFGHJ')}{r.randint(1000, 9999)}{r.choice('EOS')}",
        month=fmt(app_date - timedelta(days=r.randint(60, 200))).split(" ", 1)[1],
        offence=r.choice(DA_OFFENCES),
    )
    c["off_email"] = f"{officer.split()[1].lower()}.{r.randint(1000, 9999)}@{c['force_dom']}.pnn.police.uk"
    for n in [2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 90, 100, 140, 200, 400]:
        c[f"d{n}"] = fmt(app_date - timedelta(days=n))
    for n in [7, 14, 21, 40, 60, 180, 365]:
        c[f"f{n}"] = fmt(app_date + timedelta(days=n))
    return c


def F(s, c):
    return s.format(**c)


# --------------------------------------------------------------------------- registry
PARAS = {}


def mut(element, status, overall, why, recategorise_to=None):
    return dict(element=element, status=status, overall=overall, why=why, recategorise_to=recategorise_to)


def para(code, title, elements, mutations):
    def deco(fn):
        PARAS[code] = dict(code=code, title=title, elements=elements, mutations=mutations, render=fn)
        return fn
    return deco


# --------------------------------------------------------------------------- para 1
@para("1", "Arrest for a relevant domestic abuse offence", {
    "perpetrator_named": "Other party (B) is named as the person arrested",
    "victim_named": "Victim is named and is or was in a family relationship with B",
    "da_offence": "Arrest was for a listed domestic abuse offence",
    "arrest_current": "B was arrested and is still under investigation, on bail or charged",
    "acceptable_source": "From police/CPS/Witness Care, a pnn.police.uk address, or a provider email naming the station and officer",
}, {
    "perpetrator_not_named": mut("perpetrator_named", "not_met", "fail", "The arrested person is only described as 'a suspect'; B is never named."),
    "non_da_offence": mut("da_offence", "not_met", "fail", "The arrest was for a road traffic offence, not a domestic abuse offence."),
    "no_further_action": mut("arrest_current", "not_met", "fail", "Police confirm no further action, so B is no longer under investigation or charged."),
    "no_arrest_words_of_advice": mut("arrest_current", "not_met", "fail", "Police attended and gave words of advice; nobody was arrested. A call-out with no police action is not sufficient."),
    "provider_email_no_source": mut("acceptable_source", "unclear", "refer", "Provider email says police confirmed the arrest but gives no police station or officer name."),
})
def p1(c, m, r):
    if m == "provider_email_no_source":
        return F("From: {sol} <{sol_email}>\nTo: Legal Aid Agency\nDate: {d2}\nSubject: {A} – arrest of {B}\n\n"
                 "I write to confirm that I have spoken to the police today and they confirmed that {B} was "
                 "arrested on {d25} on suspicion of {offence} against my client, {A}, {b_his} {rel}. I understand "
                 "{b_he} remains on bail pending further enquiries.\n\n{sol}", c)
    head = F("From: DC {officer} <{off_email}>\nTo: {sol} <{sol_email}>\nDate: {d3}\n"
             "Subject: RE: {A} – crime reference {crime_ref}\n\nGood afternoon,\n\n", c)
    tail = F("\n\nKind regards,\nDC {officer}\nSafeguarding and Domestic Abuse Investigation Team\n{force}", c)
    if m == "no_arrest_words_of_advice":
        body = F("Officers attended {address} on {d40} following a call from {A} reporting a verbal argument with "
                 "{B}, {a_her} {rel}. Both parties were spoken to separately. No offences were disclosed and no "
                 "arrest was made. Words of advice were given and no further police action was taken.", c)
    elif m == "non_da_offence":
        body = (F("I can confirm that {B} (date of birth {b_dob}) was arrested on {d25} on suspicion of ", c) + NON_DA[0]
                + F(" following a vehicle stop outside {city}. {B_first} has been released on bail pending a charging decision.", c))
    else:
        if m == "perpetrator_not_named":
            who, who2, pron, rel = "a suspect", "The suspect", "them", F(", the suspect's {rel}", c)
        else:
            who, who2, pron, rel = F("{B} (date of birth {b_dob})", c), c["B_first"], c["b_him"], F(", {b_his} {rel}", c)
        body = F(f"I can confirm that {who} was arrested on {{d25}} on suspicion of {{offence}}. "
                 f"The victim in this matter is {{A}}{rel}. ", c)
        if m == "no_further_action":
            body += F(f"{who2} was interviewed under caution. Following a review of the evidence, a decision was made "
                      "on {d6} to take no further action and the investigation has been closed.", c)
        else:
            body += F(f"{who2} was interviewed and has been released on conditional bail until {{f40}} while enquiries "
                      f"continue. Bail conditions prevent {pron} from contacting {{A}} directly or indirectly.", c)
    return head + body + tail


# --------------------------------------------------------------------------- para 2
@para("2", "Police caution for a domestic abuse offence", {
    "perpetrator_named": "B is named as the person cautioned",
    "caution_given": "A caution was actually administered",
    "da_offence": "Caution was for a listed domestic abuse offence",
    "victim_named": "Victim is named (unless a sexual offence) and is in a family relationship with B",
}, {
    "victim_not_named": mut("victim_named", "not_met", "fail", "Victim field is blank and the offence is not a sexual offence."),
    "non_da_offence": mut("da_offence", "not_met", "fail", "Caution was for drug possession, not a domestic abuse offence."),
    "incident_log_no_action": mut("caution_given", "not_met", "fail", "This is an incident log where police took no action; no caution was given."),
    "stranger_victim": mut("victim_named", "not_met", "fail", "The victim is a member of the public with no family relationship to B."),
})
def p2(c, m, r):
    if m == "incident_log_no_action":
        return F("{force} – INCIDENT LOG (extract)\nIncident ref: {crime_ref}\nDate/time: {d60}, 22:14\n"
                 "Caller: {A}, {address}\nSummary: Caller reports ongoing arguments with {a_her} {rel}, {B}, who "
                 "attended the address uninvited. Officers attended. {B} had left before police arrived. Caller "
                 "declined to provide a statement. No offences disclosed.\nResult: Advice given. No further police action.", c)
    off = c["offence"]
    if m == "victim_not_named":
        victim = "Not recorded"
    elif m == "non_da_offence":
        off, victim = NON_DA[1], "N/A – no individual victim"
    elif m == "stranger_victim":
        off = "common assault (section 39 Criminal Justice Act 1988)"
        victim = f"{r.choice(M_FIRST)} {r.choice(SURN)} (member of the public, not known to the offender)"
    else:
        victim = F("{A} (relationship to offender: {rel})", c)
    return (F("{force_upper}\nRECORD OF SIMPLE CAUTION\n\nName of person cautioned: {B}\nDate of birth: {b_dob}\n"
              "Custody record: {crime_ref}\n", c)
            + f"Offence: {off}\nDate of offence: {c['d70']}\nVictim: {victim}\n"
            + F("Date caution administered: {d60}\n\nThe offender admitted the offence in interview and, having had "
                "its implications explained, accepted a simple caution.\n\nAdministering officer: PS {officer}", c))


# --------------------------------------------------------------------------- para 3
@para("3", "Ongoing criminal proceedings for a domestic abuse offence", {
    "perpetrator_named": "B is named as the person charged",
    "charged": "B has been formally charged (listing not required)",
    "da_offence": "Charge is a listed domestic abuse offence",
    "not_concluded": "Proceedings have not concluded",
    "victim_named": "Victim is named (unless a sexual offence)",
}, {
    "not_charged": mut("charged", "not_met", "fail", "B is released under investigation with no charging decision. This would meet para 1 (arrest) instead.", "1"),
    "concluded_not_guilty": mut("not_concluded", "not_met", "fail", "The trial has concluded and B was found not guilty."),
    "non_da_offence": mut("da_offence", "not_met", "fail", "B is charged with a drugs offence, not a domestic abuse offence."),
})
def p3(c, m, r):
    top = F("{force} Witness Care Unit\n{d4}\n\nDear {A},\n\nCase reference: {crime_ref}\n\n", c)
    if m == "not_charged":
        body = F("I am writing to update you on the investigation into the incident on {d40}. {B} was arrested on "
                 "suspicion of {offence} and has been released under investigation while the file is reviewed by the "
                 "Crown Prosecution Service. No charging decision has yet been made.", c)
    elif m == "concluded_not_guilty":
        body = F("I am writing to let you know the outcome of the case against {B}, who was charged with {offence} in "
                 "relation to the incident on {d140}, in which you were the named victim. The trial took place at "
                 "{city} Magistrates' Court on {d10} and {B} was found not guilty. The case is now concluded.", c)
    elif m == "non_da_offence":
        body = (F("Following the search of {address} on {d40}, {B} has been charged with ", c) + NON_DA[1]
                + F(". You may be asked to give evidence as a witness. The case is listed at {city} Magistrates' Court on {f21}.", c))
    else:
        body = F("I am writing to let you know that {B} has been charged with {offence} in relation to the incident on "
                 "{d40}, in which you are the named victim. The case has been listed for a first hearing at {city} "
                 "Magistrates' Court on {f21}. Your Witness Care Officer will keep you informed.", c)
    return top + body + F("\n\nYours sincerely,\n\n{officer}\nWitness Care Officer\n{force}", c)


# --------------------------------------------------------------------------- para 4
@para("4", "Conviction for a domestic abuse offence", {
    "perpetrator_named": "B (the other party) is named as the person convicted",
    "convicted": "Document records a conviction",
    "da_offence": "Conviction is for a listed domestic abuse offence",
    "victim_named": "Victim is named (unless a sexual offence)",
}, {
    "acquitted": mut("convicted", "not_met", "fail", "Defendant was found not guilty."),
    "different_defendant": mut("perpetrator_named", "not_met", "fail", "The person convicted is not the other party in this application."),
    "non_da_offence": mut("da_offence", "not_met", "fail", "Conviction is for a public order offence with no victim."),
})
def p4(c, m, r):
    defendant = other_name(r, True, c) if m == "different_defendant" else c["B"]
    off = NON_DA[2] if m == "non_da_offence" else c["offence"]
    against = "" if m == "non_da_offence" else F(", committed against {A} on {d140}", c)
    if m == "acquitted":
        plea, finding, sentence = "Not guilty", "Not guilty – case dismissed", "None"
    elif m == "non_da_offence":
        plea, finding, sentence = "Guilty", "Convicted", "Fine of £150 and costs of £85."
    else:
        plea, finding = "Guilty", "Convicted"
        sentence = F("Community order for 12 months with a Building Better Relationships programme requirement. "
                     "Restraining order made for 2 years protecting {A}.", c)
    return (F("MEMORANDUM OF AN ENTRY IN THE REGISTER OF {CITY_UP} MAGISTRATES' COURT\n\nDate of hearing: {d90}\n", c)
            + f"Defendant: {defendant}\nDate of birth: {c['b_dob']}\nOffence: {off}{against}\nPlea: {plea}\n"
              f"Finding: {finding}\nSentence: {sentence}\n\nCertified a true extract of the register.\n"
              f"{c['officer']}, Legal Adviser")


# --------------------------------------------------------------------------- para 5
@para("5", "Bind over connected with a domestic abuse offence", {
    "perpetrator_bound_over": "B is named as the person bound over",
    "da_offence_connection": "Bind over is connected with a domestic abuse offence",
    "victim_named": "Victim is named and in a family relationship with B",
}, {
    "unconnected_offence": mut("da_offence_connection", "not_met", "fail", "Bind over followed a drunk and disorderly charge with no domestic abuse connection."),
    "applicant_bound_over": mut("perpetrator_bound_over", "not_met", "fail", "It is the applicant, not B, who was bound over."),
})
def p5(c, m, r):
    defendant, other = (c["A"], c["B"]) if m == "applicant_bound_over" else (c["B"], c["A"])
    if m == "unconnected_offence":
        charge, towards = NON_DA[2] + F(" outside a bar in {city}", c), ""
    else:
        charge, towards = f"{c['offence']} against {other}", f", in particular towards {other}"
    return (F("{CITY_UP} MAGISTRATES' COURT – COURT RESULT\n\nDate: {d70}\n", c)
            + f"Defendant: {defendant}\nCharge: {charge}\nOutcome: The prosecution offered no evidence. The defendant "
              f"was bound over in the sum of £500 to keep the peace and be of good behaviour for 12 months{towards}.\n\n"
              f"Court Legal Adviser: {c['officer']}")


# --------------------------------------------------------------------------- para 6 / 6A
NOTICE_EL = {
    "perpetrator_named": "B is named as the person the notice was given to",
    "protected_party_named": "Protected person is named and in a family relationship with B",
    "valid_notice": "A genuine notice under the correct statute and issuing force",
}


@para("6", "Domestic Violence Protection Notice (DVPN)", NOTICE_EL, {
    "perpetrator_not_named": mut("perpetrator_named", "not_met", "fail", "The name of the person given the notice is redacted."),
    "applicant_is_respondent": mut("perpetrator_named", "not_met", "fail", "The notice was given to the applicant to protect B, not the other way round."),
})
def p6(c, m, r):
    to, prot = (c["A"], c["B"]) if m == "applicant_is_respondent" else (c["B"], c["A"])
    if m == "perpetrator_not_named":
        to = "[name redacted]"
    return (F("DOMESTIC VIOLENCE PROTECTION NOTICE\nSection 24 Crime and Security Act 2010\n\nIssued by: {force}\n"
              "Date and time issued: {d15} at 21:40\n", c)
            + f"Person to whom this notice is given: {to}\nPerson to be protected: {prot}\n\n"
              f"You must not molest {prot}. You must not enter {c['address']} or come within 100 metres of it.\n\n"
              f"An application for a Domestic Violence Protection Order will be heard at {c['city']} Magistrates' "
              f"Court within 48 hours of this notice being served.\n\nAuthorising officer: Superintendent {c['author']}\n"
              f"Serving officer: PC {c['officer']}")


@para("6A", "Domestic Abuse Protection Notice (DAPN)", NOTICE_EL, {
    "non_pilot_force": mut("valid_notice", "unclear", "refer", "DAPNs are only given in the pilot areas; this one claims to be from a non-pilot force, so verify it."),
    "applicant_is_respondent": mut("perpetrator_named", "not_met", "fail", "The notice was given to the applicant to protect B."),
})
def p6a(c, m, r):
    if m != "non_pilot_force":
        c["city"], c["force"] = r.choice(DAPN_PILOT)
        c["address"] = c["address"].rsplit(", ", 1)[0] + ", " + c["city"]
    to, prot = (c["A"], c["B"]) if m == "applicant_is_respondent" else (c["B"], c["A"])
    return (F("DOMESTIC ABUSE PROTECTION NOTICE\nSection 22 Domestic Abuse Act 2021\n\nGiven by: {force}\n"
              "Date and time given: {d12} at 23:05\n", c)
            + f"Person to whom this notice is given: {to}\nPerson to be protected: {prot}\n\n"
              f"You must not be abusive towards {prot}. You must not contact {prot} by any means, and you must not "
              f"come within 200 metres of {c['address']}.\n\nAn application for a Domestic Abuse Protection Order will "
              f"be made to {c['city']} Magistrates' Court within 48 hours.\n\nAuthorising officer: Superintendent {c['author']}")


# --------------------------------------------------------------------------- para 7
@para("7", "Relevant protective injunction", {
    "court_document": "Court document (or police document for a restraining order)",
    "order_made_and_in_force": "An order has actually been made and has not been set aside",
    "respondent_is_other_party": "B is the respondent and is in a family relationship with the protected person",
    "protected_party_named": "Protected person is named",
}, {
    "application_only": mut("order_made_and_in_force", "not_met", "fail", "This is only an application (FL401); no order has been made yet."),
    "set_aside": mut("order_made_and_in_force", "not_met", "fail", "The without-notice order was set aside at the return hearing."),
    "unrelated_respondent": mut("respondent_is_other_party", "not_met", "fail", "Injunction is against a neighbour, not B, and there is no family relationship."),
})
def p7(c, m, r):
    if m == "application_only":
        return F("FORM FL401 – APPLICATION FOR A NON-MOLESTATION ORDER\nFamily Law Act 1996, Part IV\n\n"
                 "Court: The Family Court sitting at {city}\nApplicant: {A}\nRespondent: {B}\n"
                 "Relationship: {rel}s; parents of {CH}\nOrder applied for: Non-molestation order\n"
                 "Date issued: {d4}\nThe application will be heard on notice on {f14}.", c)
    if m == "unrelated_respondent":
        nb = other_name(r, True, c)
        return (F("IN THE COUNTY COURT AT {CITY_UP}\nClaim number: {case_no}\n"
                  "Protection from Harassment Act 1997 – Injunction Order\n\nClaimant: {A}\n", c)
                + f"Defendant: {nb} (neighbour, no other relationship to the claimant)\n\n"
                  f"The Defendant must not harass, intimidate or threaten the Claimant and must not come within 50 metres "
                  f"of {c['address']}. This order lasts until {c['f365']}.\n\nDistrict Judge {c['author']}")
    if m is None and r.random() < 0.3:
        return F("From: PC {officer} <{off_email}>\nDate: {d5}\nSubject: Restraining order – {B}\n\n"
                 "I can confirm that on {d90}, at {city} Crown Court, a restraining order was made against {B} under "
                 "section 360 of the Sentencing Act 2020 following his conviction. The order prohibits {B} from "
                 "contacting {A}, {b_his} {rel}, directly or indirectly, until {f365}.\n\nPC {officer}\n{force}", c).replace(
                     "his conviction", f"{c['b_his']} conviction")
    text = F("IN THE FAMILY COURT SITTING AT {CITY_UP}\nCase number: {case_no}\n"
             "Family Law Act 1996 – Non-Molestation Order (section 42)\n\nApplicant: {A}\nRespondent: {B}\n\n"
             "The court orders that the Respondent, {B}, must not:\n"
             "1. use or threaten violence against the Applicant, or instruct or encourage anyone else to do so;\n"
             "2. intimidate, harass or pester the Applicant;\n"
             "3. communicate with the Applicant by any means, except through solicitors;\n"
             "4. go to or enter {address}.\n\n"
             "This order was made without notice on {d12} and lasts until {f180} unless varied or discharged.\n\n"
             "District Judge {author}", c)
    if m == "set_aside":
        text += F("\n\nNOTE: At the return hearing on {d4} the court set aside the without-notice order made on {d12}.", c)
    return text


# --------------------------------------------------------------------------- para 8
@para("8", "Undertaking (Family Law Act 1996 s46 or s63E)", {
    "given_by_other_party": "Undertaking was given by B",
    "correct_statutory_basis": "Given under s46 or s63E FLA 1996 (or Scottish/NI equivalent)",
    "beneficiary_named": "Person protected is named and in a family relationship with B",
    "no_relevant_cross_undertaking": "Applicant did not give a domestic abuse-related cross-undertaking",
}, {
    "mutual_cross_undertaking": mut("no_relevant_cross_undertaking", "not_met", "fail", "Both parties gave undertakings not to use violence, which is a relevant cross-undertaking."),
    "benign_cross_undertaking": mut("no_relevant_cross_undertaking", "met", "pass", "The applicant's cross-undertaking is about the child's schooling, which is not domestic abuse-related, so it still passes."),
    "given_by_applicant": mut("given_by_other_party", "not_met", "fail", "The undertaking was given by the applicant, not B."),
})
def p8(c, m, r):
    giver, other = (c["A"], c["B"]) if m == "given_by_applicant" else (c["B"], c["A"])
    text = F("GENERAL FORM OF UNDERTAKING (N117)\nIn the Family Court at {city}\nCase number: {case_no}\n\n"
             "Applicant: {A}\nRespondent: {B}\n\n", c)
    text += (f"On {c['d30']} {giver} appeared before District Judge {c['author']} and gave an undertaking to the court "
             f"under section 46 of the Family Law Act 1996, promising:\n1. not to use or threaten violence against {other};\n"
             f"2. not to contact {other} directly or indirectly, except through solicitors;\n"
             f"3. not to attend {c['address']}.\n\nThe court accepted the undertaking in place of a non-molestation order.")
    if m == "mutual_cross_undertaking":
        text += F("\n\nThe Applicant, {A}, also gave an undertaking not to use or threaten violence against the "
                  "Respondent and not to contact the Respondent except through solicitors.", c)
    elif m == "benign_cross_undertaking":
        text += F("\n\nThe Applicant, {A}, gave an undertaking to keep {CH} at the same school pending the next hearing.", c)
    else:
        text += "\n\nNo undertaking was given by the other party."
    return text


# --------------------------------------------------------------------------- para 9
@para("9", "Finding of fact of domestic abuse by B", {
    "court_document": "Judgment or court order",
    "specific_finding_by_other_party": "A specific finding that B committed domestic abuse",
    "made_before_application": "Finding made before the legal aid application",
    "victim_named": "Victim named and in a family relationship with B",
}, {
    "undefended_divorce_petition": mut("specific_finding_by_other_party", "not_met", "fail", "Allegations in an undefended divorce petition are not a finding of fact."),
    "finding_after_application": mut("made_before_application", "not_met", "fail", "The finding post-dates the application, so it can't be the only evidence."),
    "hearing_only_listed": mut("specific_finding_by_other_party", "not_met", "fail", "A fact-finding hearing has only been listed; no findings have been made."),
    "allegations_not_proved": mut("specific_finding_by_other_party", "not_met", "fail", "The court found the allegations not proved."),
})
def p9(c, m, r):
    if m == "undefended_divorce_petition":
        return F("DIVORCE PETITION (issued 2021) – extract\nPetitioner: {A}\nRespondent: {B}\n\n"
                 "The Respondent has behaved in such a way that the Petitioner cannot reasonably be expected to live "
                 "with the Respondent, including shouting at the Petitioner, belittling her and damaging property.\n\n"
                 "The Respondent did not file an answer. Decree nisi pronounced on the basis of the Respondent's "
                 "unreasonable behaviour.", c).replace("belittling her", f"belittling {c['a_herx']}")
    head = F("IN THE FAMILY COURT SITTING AT {CITY_UP}\nCase number: {case_no}\nRe: {CH} (Children Act 1989)\n\n"
             "Applicant: {A}\nRespondent: {B}\n\n", c)
    if m == "hearing_only_listed":
        return head + F("CASE MANAGEMENT ORDER\n\nThe Applicant alleges domestic abuse by the Respondent as set out "
                        "in her Scott Schedule. A fact-finding hearing is listed on {f60} to determine those "
                        "allegations.\n\nDistrict Judge {author}", c).replace("her Scott", f"{c['a_her']} Scott")
    when = c["f7"] if m == "finding_after_application" else c["d50"]
    if m == "allegations_not_proved":
        findings = "THE COURT FINDS that the Applicant's allegations are NOT proved on the balance of probabilities."
    else:
        findings = F("THE COURT FINDS proved on the balance of probabilities that:\n"
                     "(a) in {month} the Respondent, {B}, grabbed the Applicant by the throat during an argument;\n"
                     "(b) the Respondent engaged in a pattern of controlling and coercive behaviour towards the "
                     "Applicant, including monitoring {a_her} phone and restricting {a_her} access to money.", c)
    return head + (f"ORDER FOLLOWING FACT-FINDING HEARING\n\nUpon the fact-finding hearing on {when}, and the court "
                   f"having applied Practice Direction 12J,\n\n{findings}\n\nDistrict Judge {c['author']}")


# --------------------------------------------------------------------------- para 10
@para("10", "Expert report produced as evidence for a UK court or tribunal", {
    "produced_for_uk_proceedings": "Report produced as evidence in UK court or tribunal proceedings",
    "expert_identity_and_qualifications": "Expert named with relevant qualifications/experience",
    "names_perpetrator_and_victim": "Names B and the victim (in a family relationship with B)",
    "assessed_victim_or_at_risk": "Victim assessed as being, or at risk of being, a victim of domestic abuse by B",
}, {
    "no_assessment": mut("assessed_victim_or_at_risk", "not_met", "fail", "The report expressly makes no assessment of the abuse allegations."),
    "no_qualifications": mut("expert_identity_and_qualifications", "unclear", "refer", "Author's qualifications and experience are not stated."),
    "private_report_not_for_court": mut("produced_for_uk_proceedings", "not_met", "fail", "A private therapeutic report not produced for any court proceedings."),
})
def p10(c, m, r):
    quals = "" if m == "no_qualifications" else ", BA (Hons) Social Work, registered with Social Work England, 11 years' experience as a Family Court Adviser"
    if m == "private_report_not_for_court":
        header = F("PSYCHOLOGICAL ASSESSMENT – {A}\nAuthor: Dr {author}, HCPC-registered Clinical Psychologist\n"
                   "Commissioned privately by {A} to inform {a_her} own therapy. Not prepared for any court or tribunal.\n\n", c)
    else:
        header = (F("Cafcass – Section 7 Report\nCase number: {case_no}\nChild: {CH}\n", c)
                  + f"Family Court Adviser: {c['author']}{quals}\n"
                  + F("Prepared for: The Family Court sitting at {city}, hearing on {f21}\n\n", c))
    if m == "no_assessment":
        analysis = F("Analysis: Both parents make allegations against each other. I have not been able to reach a view on "
                     "the allegations of domestic abuse made by {A} against {B}; these are matters for the court to determine.", c)
    else:
        analysis = F("Analysis of risk: Having considered police information, local authority records and my interviews "
                     "with both parents, I assess that {A} has been a victim of domestic abuse by {B}, {a_her} {rel}, "
                     "including coercive and controlling behaviour, and that {a_she} remains at risk of further abuse.", c)
    return header + analysis


# --------------------------------------------------------------------------- para 11
@para("11", "Letter from an appropriate health professional", {
    "appropriate_health_professional": "Author is a registered appropriate health professional (doctor, nurse, midwife, dentist, paramedic, psychologist, radiographer, social worker)",
    "examined_applicant": "Applicant was examined in person, by phone or by video",
    "consistent_with_domestic_abuse": "Clear (unhedged) judgement that injuries/condition are consistent with domestic abuse",
    "applicant_named": "Applicant is named (perpetrator need not be)",
}, {
    "hedged_judgement": mut("consistent_with_domestic_abuse", "not_met", "fail", "Judgement is hedged ('may possibly be consistent'), mirroring the MoJ rejected example."),
    "counsellor_not_ahp": mut("appropriate_health_professional", "not_met", "fail", "A BACP counsellor is not an appropriate health professional under the regulations."),
    "no_examination": mut("examined_applicant", "not_met", "fail", "Author has not examined the applicant; letter is based on an online form."),
    "email_no_registration_number": mut("appropriate_health_professional", "unclear", "refer", "Email from a personal address with no GMC/NMC registration number."),
})
def p11(c, m, r):
    kind = r.choice(["gp", "ae", "hv"])
    if m == "counsellor_not_ahp":
        sig, reg = F("{author}\nCounsellor (MBACP)\n{org}", c), "I am a counsellor registered with the British Association for Counselling and Psychotherapy."
    elif kind == "hv":
        sig, reg = F("{author}\nHealth Visitor, {city} Community Health Services", c), F("I am a health visitor registered with the Nursing and Midwifery Council (PIN {nmc}).", c)
    elif kind == "ae":
        sig, reg = F("Dr {author}\nEmergency Department, {city} General Hospital", c), F("I am a doctor registered with the General Medical Council (GMC number {gmc}).", c)
    else:
        sig, reg = F("Dr {author}\n{practice}", c), F("I am a general practitioner registered with the General Medical Council (GMC number {gmc}).", c)
    how = r.choice(["in person", "by telephone", "by video consultation"])
    exam = (F("I have not seen {A} myself. This letter is based on information {a_she} provided through our online form.", c)
            if m == "no_examination" else F(f"I examined {{A}} {how} on {{d8}}.", c))
    cond = r.choice(["injuries", "a condition"])
    judge = (F(f"In my reasonable professional judgement, {{a_she}} has {cond} that may possibly be consistent with domestic abuse.", c)
             if m == "hedged_judgement" else
             F(f"In my reasonable professional judgement, {{a_she}} has {cond} consistent with being a victim of domestic abuse.", c))
    body = F(INTRO, c) + "\n\n" + reg + "\n\n" + exam + " " + judge
    if m == "email_no_registration_number":
        addr = c["author"].split()[1].lower() + "doctor@gmail.com"
        return (F("From: {author} <" + addr + ">\nDate: {d5}\nSubject: Letter for {A}\n\n", c)
                + F(INTRO, c) + "\n\n" + F(f"I examined {{A}} {how} on {{d8}}. In my reasonable professional judgement, "
                                          f"{{a_she}} has {cond} consistent with being a victim of domestic abuse.\n\n{{author}}", c))
    return F("{d5}\n\nTo whom it may concern\n\nRe: {A}, date of birth {a_dob}\n\n", c) + body + "\n\n" + sig


# --------------------------------------------------------------------------- para 12
@para("12", "Health professional referral to a domestic abuse support service", {
    "applicant_named": "Applicant is named",
    "referral_by_ahp": "Referral made by an appropriate health professional",
    "specialist_da_service": "Referral was to a specialist domestic abuse support service",
    "author_eligible": "Letter is from the referring professional, one with access to records, or the service referred to",
}, {
    "non_specialist_service": mut("specialist_da_service", "not_met", "fail", "Referral was to a general talking therapies service, not a specialist domestic abuse service."),
    "self_referral": mut("referral_by_ahp", "not_met", "fail", "The applicant self-referred; no health professional made the referral."),
    "referrer_not_ahp": mut("referral_by_ahp", "not_met", "fail", "Referral was made by a school teacher, not an appropriate health professional."),
})
def p12(c, m, r):
    if m == "self_referral" or m == "referrer_not_ahp":
        who = "{A} self-referred to our service" if m == "self_referral" else "{A} was referred to our service by {CH_first}'s class teacher"
        return F("{org}\n{d6}\n\nTo whom it may concern\n\nRe: {A}\n\nWe are a specialist service supporting people "
                 "affected by domestic abuse. I can confirm that " + who + " on {d40} and has since received "
                 "one-to-one support.\n\n{author}\nService Manager", c)
    dest = ("NHS Talking Therapies, for support with low mood and anxiety" if m == "non_specialist_service"
            else "{org}, a specialist service providing support to victims of domestic abuse")
    return F("{practice}\n{d6}\n\nTo whom it may concern\n\nRe: {A}, date of birth {a_dob}\n\n"
             "I am a general practitioner registered with the General Medical Council (GMC number {gmc}). I confirm "
             "that on {d40}, following {a_her} disclosure of abuse during a consultation, I referred {A} to " + dest + ".\n\n"
             "Dr {author}", c)


# --------------------------------------------------------------------------- para 13
@para("13", "Letter from a MARAC or other local safeguarding forum member", {
    "author_forum_member": "Author is a member of a MARAC or multi-agency safeguarding forum",
    "victim_named": "Victim is the applicant or someone in a family relationship with the applicant",
    "perpetrator_named": "B is named as the source of risk",
    "at_risk_of_harm_from_other_party": "Confirms the victim is or has been at risk of harm from domestic abuse by B",
}, {
    "perpetrator_not_named": mut("perpetrator_named", "not_met", "fail", "Risk is attributed to 'a former partner' who is not named."),
    "threshold_not_met": mut("at_risk_of_harm_from_other_party", "not_met", "fail", "Case did not meet the MARAC threshold and was not heard; no risk confirmed."),
})
def p13(c, m, r):
    head = F("{council} – Multi-Agency Risk Assessment Conference (MARAC)\n{d6}\n\nTo whom it may concern\n\n"
             "Re: {A}\n\nI am the MARAC Coordinator for {council} and a member of the MARAC. ", c)
    if m == "threshold_not_met":
        body = F("{A} was referred to MARAC on {d40}. Following review, the referral did not meet the threshold for "
                 "MARAC and the case was not heard. The referrer was advised to continue single-agency support.", c)
    else:
        perp = F("{a_her} former partner", c) if m == "perpetrator_not_named" else F("{B}, {a_her} {rel}", c)
        body = (F("I can confirm that the case of {A} was heard at MARAC on {d35}. The conference agreed that {A} ", c)
                + f"is at high risk of serious harm from domestic abuse by {perp}. "
                + "A multi-agency safety plan was agreed, including police markers on the address and IDVA support.")
    return head + body + F("\n\n{author}\nMARAC Coordinator", c)


# --------------------------------------------------------------------------- para 14
@para("14", "Letter from an independent domestic violence advisor (IDVA)", {
    "author_is_idva": "Author is an IDVA",
    "confirms_support": "IDVA personally confirms they are providing or have provided support",
    "applicant_named": "Applicant is named as the person supported",
}, {
    "we_provided": mut("confirms_support", "not_met", "fail", "Mirrors the MoJ rejected example: 'we provided' rather than the IDVA confirming support personally. MoJ's exact reason is unconfirmed."),
    "author_not_idva": mut("author_is_idva", "not_met", "fail", "Author is a family support worker, not an IDVA."),
    "applicant_not_named": mut("applicant_named", "not_met", "fail", "Template placeholder never filled in; the applicant is not named anywhere."),
})
def p14(c, m, r):
    name = "[name of applicant]" if m == "applicant_not_named" else c["A"]
    confirm = (f"I can confirm that we provided {name} with support." if m == "we_provided"
               else f"I can confirm that I am providing {name} with support." if r.random() < 0.6
               else f"I can confirm that I have provided {name} with support since {c['d100']}.")
    role = "Family Support Worker" if m == "author_not_idva" else "Independent Domestic Violence Advisor (IDVA)"
    return (f"To whom it may concern\n\nName of applicant: {name}\n\n"
            f"I understand that {name} wishes to access legal aid for a family dispute as a victim of domestic abuse. "
            f"For this reason, I have been asked to confirm that I am providing / have provided support to {name} in "
            f"accordance with regulation 33 and Schedule 1 of the Civil Legal Aid (Procedure) Regulations 2012 (as amended).\n\n"
            f"{confirm}\n\nYours sincerely,\n\n{c['author']}\n{role}\n{c['org']}")


# --------------------------------------------------------------------------- para 15
@para("15", "Letter from an independent sexual violence advisor (ISVA)", {
    "author_is_isva": "Author is an ISVA",
    "applicant_named": "Applicant named (where possible)",
    "support_relates_to_sexual_violence": "Support relates to sexual violence",
    "perpetrator_is_other_party": "Sexual violence was by B, who is named",
}, {
    "perpetrator_not_named": mut("perpetrator_is_other_party", "not_met", "fail", "The perpetrator is not named, so it can't be linked to B."),
    "stranger_assault": mut("perpetrator_is_other_party", "not_met", "fail", "Support relates to an assault by an unknown person, not B."),
})
def p15(c, m, r):
    if m == "stranger_assault":
        by = "following a sexual assault by an unknown male in {month}"
    elif m == "perpetrator_not_named":
        by = "relating to sexual violence"
    else:
        by = "relating to sexual violence perpetrated by {B}, {a_her} {rel}"
    return F("{city} Sexual Assault Referral Centre\n{d5}\n\nTo whom it may concern\n\nRe: {A}\n\n"
             "I am an Independent Sexual Violence Advisor (ISVA). I confirm that I have been providing support to {A} "
             "since {d100} " + by + ".\n\n{author}\nISVA", c)


# --------------------------------------------------------------------------- para 16
@para("16", "Letter from a local authority or housing association officer", {
    "officer_of_la_or_ha": "Officer employed by a local authority or housing association to support tenants",
    "victim_named": "Victim named and in a family relationship with B",
    "perpetrator_named": "B named",
    "professional_judgement": "Statement of reasonable professional judgement that the victim is or is at risk of being a victim",
    "specific_matters": "Description of the specific matters relied on",
    "support_or_decision": "Description of support provided or decision reached",
}, {
    "no_specific_matters": mut("specific_matters", "not_met", "fail", "Only says 'based on our records'; no specific matters are described."),
    "no_support_described": mut("support_or_decision", "not_met", "fail", "No support or housing decision is described."),
    "hedged_judgement": mut("professional_judgement", "not_met", "fail", "Judgement is hedged ('it is possible that ... could be')."),
    "private_landlord": mut("officer_of_la_or_ha", "not_met", "fail", "Author is a private letting agent, not a local authority or housing association."),
})
def p16(c, m, r):
    employer = "Parkside Lettings Ltd (private letting agent)" if m == "private_landlord" else r.choice([c["council"] + " – Housing Options", c["ha"]])
    judge = (F("It is possible that {A} could be a victim of domestic abuse by {B}.", c) if m == "hedged_judgement"
             else F("In my reasonable professional judgement {A} is, or is at risk of being, a victim of domestic abuse by {B}, {a_her} {rel}.", c))
    matters = ("Matters relied on: based on our records." if m == "no_specific_matters" else
               F("Matters relied on: {A} disclosed repeated threats from {B} after the separation, and {B} attended the "
                 "property on several occasions in breach of police advice. A DASH risk assessment completed on {d60} scored 15 (high risk).", c))
    support = ("" if m == "no_support_described" else
               F("\n\nSupport provided: {A} was accepted as homeless and in priority need on {d45} owing to domestic abuse, "
                 "placed in safe temporary accommodation and exempted from the local connection requirement.", c))
    return (F("{d4}\n\nTo whom it may concern\n\nRe: {A}\n\n", c) + judge + "\n\n" + matters + support
            + f"\n\n{c['author']}\nSenior Housing Officer (Domestic Abuse Lead)\n{employer}")


# --------------------------------------------------------------------------- para 17
@para("17", "Letter from an organisation providing domestic abuse support services", {
    "uk_situated": "Organisation confirms it is situated in the UK",
    "operating_six_months": "Organisation confirms it has operated for an uninterrupted 6 months or more",
    "supported_applicant": "Confirms it supported the applicant as a victim or person at risk",
    "professional_judgement": "Unhedged professional judgement that the applicant is or is at risk of being a victim",
    "specific_matters": "Description of the specific matters (what happened), not just the source of information",
    "support_description": "Description of the support provided",
    "reason_for_support": "Statement of why the applicant needed the support",
    "applicant_named": "Applicant named",
}, {
    "vague_matters": mut("specific_matters", "not_met", "fail", "Mirrors the MoJ rejected example: 'victim testimony and referral' names a source, not the abuse."),
    "operating_under_six_months": mut("operating_six_months", "not_met", "fail", "Organisation states it was established about four months ago."),
    "no_reason_for_support": mut("reason_for_support", "not_met", "fail", "No statement of why the applicant needed the support."),
    "hedged_judgement": mut("professional_judgement", "not_met", "fail", "Judgement is hedged ('may be at risk')."),
})
def p17(c, m, r):
    op = ("I can confirm that our organisation is situated in the United Kingdom and has been operating for an "
          "uninterrupted period of six months or more.")
    if m == "operating_under_six_months":
        op = F("Our organisation is situated in England and was established on {d140}.", c)
    judge = (F("In my reasonable professional judgement {A} may be at risk of domestic abuse.", c) if m == "hedged_judgement"
             else F("In my reasonable professional judgement {A} is, or is at risk of being, a victim of domestic abuse.", c))
    matters = "Victim testimony and referral." if m == "vague_matters" else F(r.choice(MATTERS), c) + "."
    reason = "" if m == "no_reason_for_support" else F("\n\n{A} needed this support because " + r.choice(REASONS) + ".", c)
    return (F(INTRO, c) + "\n\n" + op + "\n\n"
            + F("I can confirm that we have provided {A} with support in relation to {a_her} needs as a victim, or person at risk, of domestic abuse.\n\n", c)
            + judge + "\n\nThe matters I have relied upon to support that judgement are: " + matters
            + F("\n\nWe have provided {A} with the following support: ", c) + r.choice(SUPPORT) + "." + reason
            + F("\n\n{author}\nSenior Outreach Worker\n{org}", c))


# --------------------------------------------------------------------------- para 18
@para("18", "Refusal of admission to a refuge", {
    "organisation_identified": "Domestic abuse support organisation is identified",
    "perpetrator_named": "B named",
    "victim_named": "Person refused is named and in a family relationship with B",
    "refusal_date": "Date admission was refused",
    "sought_because_of_abuse_by_other_party": "Sought admission because of allegations of domestic abuse by B",
}, {
    "perpetrator_not_named": mut("perpetrator_named", "not_met", "fail", "Mirrors the MoJ rejected example: no perpetrator named, so no link to B."),
    "no_refusal_date": mut("refusal_date", "not_met", "fail", "The date of refusal is not given."),
    "sought_for_other_reason": mut("sought_because_of_abuse_by_other_party", "not_met", "fail", "Admission was sought after eviction for rent arrears, not because of abuse."),
})
def p18(c, m, r):
    perp_line = "" if m == "perpetrator_not_named" else F("Name of perpetrator: {B}\n", c)
    with_b = "" if m == "perpetrator_not_named" else F(", with whom {B} is or was in a family relationship,", c)
    on_date = "" if m == "no_refusal_date" else F(" on {d20}", c)
    why = ("because {a_she} had been evicted from {a_her} flat following rent arrears" if m == "sought_for_other_reason"
           else "because of allegations of domestic abuse" + ("" if m == "perpetrator_not_named" else " by {B}"))
    return (F("To whom it may concern,\n\n", c) + perp_line + F("Name of applicant: {A}\n\n", c) + F(INTRO, c)
            + f"\n\nI can confirm that {c['A']}{with_b} was refused admission to a refuge{on_date}."
            + F("\n\nI can confirm that {A} sought admission to a refuge " + why + ".", c)
            + F("\n\n{author}\nDomestic Abuse Support Officer\n{org}", c))


# --------------------------------------------------------------------------- para 19
@para("19", "Letter from a public authority", {
    "public_authority_named": "A public authority is identified",
    "victim_named": "Victim named and in a family relationship with B",
    "perpetrator_named": "B named",
    "assessed_victim_or_at_risk": "Confirms the victim was assessed as being, or at risk of being, a victim of domestic abuse by B",
}, {
    "hedged": mut("assessed_victim_or_at_risk", "not_met", "fail", "Mirrors the MoJ rejected example: 'might be a victim' is not an assessment."),
    "not_public_authority": mut("public_authority_named", "not_met", "fail", "A private nursery is not a public authority."),
    "perpetrator_not_named": mut("perpetrator_named", "not_met", "fail", "No perpetrator is named."),
})
def p19(c, m, r):
    authority = "Little Acorns Day Nursery Ltd" if m == "not_public_authority" else c["council"] + " Children's Services"
    perp_line = "" if m == "perpetrator_not_named" else F("Name of perpetrator: {B}\n", c)
    by = "" if m == "perpetrator_not_named" else F(" by {B}", c)
    rel = "" if m == "perpetrator_not_named" else F(", a person with whom {B} is or was in a family relationship,", c)
    outcome = f"might be a victim of domestic abuse{by}" if m == "hedged" else f"was assessed as being, or at risk of being, a victim of domestic abuse{by}"
    return (F("To whom it may concern\n\n", c) + perp_line + F("Name of applicant: {A}\n\n", c) + F(INTRO, c)
            + f"\n\nAccordingly, I can confirm that {c['A']}{rel} {outcome}."
            + f"\n\nYours sincerely,\n\n{c['author']}\n{authority}")


# --------------------------------------------------------------------------- para 20
@para("20", "Home Office leave to enter or remain as a victim of domestic abuse", {
    "from_home_office": "Letter from the Home Office (Secretary of State)",
    "applicant_named": "Applicant named",
    "leave_as_da_victim": "Leave granted as a victim of domestic abuse",
    "granted_on_or_before_application": "Leave granted on or before the legal aid application date",
}, {
    "other_basis": mut("leave_as_da_victim", "not_met", "fail", "Leave was granted as a partner under Appendix FM, not as a victim of domestic abuse."),
    "application_pending": mut("granted_on_or_before_application", "not_met", "fail", "The immigration application is still pending; no leave has been granted."),
    "granted_after_application": mut("granted_on_or_before_application", "not_met", "fail", "Leave was granted after the legal aid application date."),
})
def p20(c, m, r):
    head = F("Home Office – UK Visas and Immigration\n\nDear {A},\n\n", c)
    if m == "application_pending":
        return head + F("We have received your application for indefinite leave to remain as a victim of domestic abuse "
                        "under Appendix Victim of Domestic Abuse, submitted on {d40}. Your application is being considered "
                        "and we will write to you with a decision.\n\nUK Visas and Immigration", c)
    basis = ("as the partner of a person present and settled in the UK under Appendix FM" if m == "other_basis"
             else "as a victim of domestic abuse under Appendix Victim of Domestic Abuse")
    when = c["f14"] if m == "granted_after_application" else c["d100"]
    return head + (f"Your application for leave to remain in the United Kingdom {basis} has been approved. You have been "
                   f"granted indefinite leave to remain with effect from {when}.\n\nUK Visas and Immigration\nOn behalf of the Secretary of State for the Home Department")


# --------------------------------------------------------------------------- para 21
@para("21", "Economic abuse (Director's discretion)", {
    "perpetrator_named": "B named",
    "economic_behaviour_described": "Describes behaviour affecting the ability to acquire, use or keep money or property, or obtain goods or services",
    "pattern_of_power_or_control": "Behaviour shows an intent to gain power or control, not an ordinary financial dispute",
    "corroboration_or_explanation": "Supporting documents, or an explanation of why none are available",
}, {
    "ordinary_financial_dispute": mut("pattern_of_power_or_control", "not_met", "refer", "Describes an ordinary disagreement about dividing assets, not controlling behaviour."),
    "narrative_only_no_explanation": mut("corroboration_or_explanation", "unclear", "refer", "Narrative only, with no documents and no explanation of why none are available."),
})
def p21(c, m, r):
    head = F("Statement of {A} – economic abuse\nOther party: {B}\n\n", c)
    if m == "ordinary_financial_dispute":
        body = F("1. {B} and I separated in {month}. We jointly own the house at {address}.\n"
                 "2. We disagree about how the proceeds of sale should be divided. {B} says {b_he} should receive 60% "
                 "because {b_he} paid more of the deposit. I think it should be split equally.\n"
                 "3. We have also not agreed who should keep the car.", c)
        ex = F("\n\nExhibits: EX1 – Land Registry title for {address}", c)
    else:
        body = F("1. Throughout our relationship {B} controlled all of the household money. My wages were paid into an "
                 "account in {b_his} sole name and I had to ask {b_him} for money for food and nappies.\n"
                 "2. In {month} {B} took out a loan of £6,000 in my name without my knowledge. I only found out when the "
                 "lender wrote to me about arrears.\n"
                 "3. Since we separated {B} has stopped paying the mortgage, although {b_he} paid it before, and says "
                 "{b_he} will only pay child maintenance if I let {b_him} see {CH_first} whenever {b_he} wants.", c)
        ex = ("" if m == "narrative_only_no_explanation" else
              "\n\nExhibits: EX1 – joint account statements; EX2 – credit report showing the loan; "
              "EX3 – lender's arrears letter; EX4 – text messages about maintenance")
    return head + body + ex


# --------------------------------------------------------------------------- noise and helpers
TYPOS = [("received", "recieved"), ("separate", "seperate"), ("their", "thier"), ("relationship", "relationsip"),
         ("support", "suport"), ("professional", "proffesional"), ("confirm", "comfirm"), ("domestic", "domestc"),
         ("Regulations", "Regualtions"), ("victim", "vicim")]


def noisify(text, r):
    """Harmless defects of the kind seen in MoJ's ACCEPTED examples: typos and a stray template placeholder."""
    applied = []
    for a, b in r.sample(TYPOS, len(TYPOS)):
        if a in text and len(applied) < 3:
            text = text.replace(a, b, 1)
            applied.append(f"typo '{b}'")
    if "To whom it may concern" in text:
        text = text.replace("To whom it may concern", "To whom it may concern\n\nRe: [NAME OF CLIENT]", 1)
        applied.append("unfilled template placeholder")
    return text, applied


def element_block(code, broken=None):
    spec = PARAS[code]
    out = {k: {"description": d, "status": "met"} for k, d in spec["elements"].items()}
    if broken:
        for k, st in broken.items():
            out[k]["status"] = st
    return out


def application(c):
    return {"applicant": c["A"], "other_party": c["B"], "relationship": c["rel"], "child": c["CH"],
            "application_date": c["app_date"].isoformat(),
            "proceedings": "Child arrangements order (Children Act 1989, section 8)"}


def doc(doc_id, code, text, outcome, elements, reason, recat=None):
    return {"doc_id": doc_id, "claimed_para": code, "text": text,
            "expected": {"outcome": outcome, "elements": elements, "reason": reason, "recategorise_to": recat}}


def combine(outcomes):
    if "pass" in outcomes:
        return "pass"
    return "refer" if "refer" in outcomes else "fail"


def render_case(code, m, r):
    c = mkctx(r)
    return c, PARAS[code]["render"](c, m, r)


# --------------------------------------------------------------------------- per-paragraph cases
def para_cases(r, n_valid):
    cases = []
    for code, spec in PARAS.items():
        default = "refer" if code == "21" else "pass"
        default_reason = ("Strong economic abuse evidence, but para 21 is always the Director's discretion."
                          if code == "21" else "All required elements present.")
        for i in range(n_valid):
            c, text = render_case(code, None, r)
            cases.append({"id": f"P{code}-valid-{i + 1:02d}", "source": "synthetic", "category": "valid",
                          "application": application(c),
                          "documents": [doc("D1", code, text, default, element_block(code), default_reason)],
                          "expected_overall": default})
        c, text = render_case(code, None, r)
        text, defects = noisify(text, r)
        cases.append({"id": f"P{code}-benign_defects-01", "source": "synthetic", "category": "valid_with_benign_defects",
                      "application": application(c),
                      "documents": [doc("D1", code, text, default, element_block(code),
                                        "Still valid: " + ", ".join(defects) + ". MoJ accepted letters with similar errors.")],
                      "expected_overall": default})
        for name, mu in spec["mutations"].items():
            c, text = render_case(code, name, r)
            cases.append({"id": f"P{code}-{name}-01", "source": "synthetic",
                          "category": "hard_negative_pass" if mu["overall"] == "pass" else "mutation",
                          "application": application(c),
                          "documents": [doc("D1", code, text, mu["overall"], element_block(code, {mu["element"]: mu["status"]}),
                                            mu["why"], mu["recategorise_to"])],
                          "expected_overall": mu["overall"]})
    return cases


# --------------------------------------------------------------------------- cross-cutting cases
FILLER = [
    "Family composition: The household consists of {A} and {CH}. {CH_first} attends a local primary school and attendance is currently 94%.",
    "Housing: The family live in a two-bedroom flat at {address}. There are no concerns about the physical condition of the home.",
    "Health: {CH_first} is registered with {practice} and is up to date with immunisations. There are no outstanding health concerns.",
    "Education: The school reports that {CH_first} is making expected progress and has a good group of friends.",
    "Wider family: Maternal grandparents live nearby and provide regular childcare.",
    "Parenting capacity: {A} presents as a warm and attentive parent. Routines are consistent and age-appropriate.",
    "Child's wishes and feelings: {CH_first} said that {CH_first} likes school, enjoys football and wants to keep living with {A}.",
    "Finances: The family receives Universal Credit. {A} has been supported to apply for a council tax reduction.",
    "Reason for referral: The referral was received from {CH_first}'s school after {CH_first} appeared withdrawn in class and told a teaching assistant about arguments at home. The school's designated safeguarding lead made the referral on the same day.",
    "Professionals consulted: The class teacher, the school nurse, the family's GP and the health visitor were consulted. All described regular contact with the family and no concerns about basic care.",
    "Daily routine: {CH_first} is taken to school by {A} each morning and attends an after-school club twice a week. Bedtime is around 7.30pm. Meals are regular and {CH_first} has a varied diet.",
    "Contact arrangements: There are currently no agreed arrangements for {CH_first} to spend time with {B}. {A} has said {a_she} would support safe, supervised contact if it is in {CH_first}'s interests.",
]


def cross_cases(r):
    cases = []

    c, t = render_case("17", None, r)
    el = element_block("14", {"author_is_idva": "not_met"})
    cases.append({"id": "X-wrong_para_17_claimed_as_14", "source": "synthetic", "category": "cross_cutting",
                  "application": application(c),
                  "documents": [doc("D1", "14", t, "fail", el, "A support-organisation letter submitted as an IDVA letter. It is not from an IDVA, but it does meet para 17.", "17")],
                  "expected_overall": "fail"})

    c, t = render_case("14", None, r)
    el = element_block("17", {"specific_matters": "not_met", "professional_judgement": "not_met", "reason_for_support": "not_met",
                              "operating_six_months": "not_met", "uk_situated": "not_met", "support_description": "not_met"})
    cases.append({"id": "X-wrong_para_14_claimed_as_17", "source": "synthetic", "category": "cross_cutting",
                  "application": application(c),
                  "documents": [doc("D1", "17", t, "fail", el, "An IDVA letter submitted under para 17. It lacks the para 17 elements but meets para 14.", "14")],
                  "expected_overall": "fail"})

    c, t = render_case("17", None, r)
    app = application(c)
    app["applicant"] = c["A"][:-2] + ("u" if c["A"][-2] != "u" else "a") + c["A"][-1]
    cases.append({"id": "X-name_mismatch", "source": "synthetic", "category": "cross_cutting", "application": app,
                  "documents": [doc("D1", "17", t, "refer", element_block("17", {"applicant_named": "unclear"}),
                                    f"Letter names '{c['A']}' but the application is for '{app['applicant']}'. Check identity before relying on it.")],
                  "expected_overall": "refer"})

    c = mkctx(r)
    filler = [F(s, c) for s in r.sample(FILLER, len(FILLER))]
    key = F("Domestic abuse: Information from {force} and the family's account confirm that {A} has experienced "
            "domestic abuse from {B}, {a_her} {rel}. Children's Services have assessed {A} as being a victim of "
            "domestic abuse by {B} and as remaining at risk of further abuse.", c)
    body = filler[:5] + [key] + filler[5:]
    t = (F("{council} Children's Services\nCHILD AND FAMILY ASSESSMENT\nChild: {CH}\nParent: {A}\nOther parent: {B}\n"
           "Assessment completed: {d30}\nSocial Worker: {author}\n\n", c) + "\n\n".join(body)
         + "\n\nOutcome: Child in Need plan; IDVA referral made; review in 3 months.")
    cases.append({"id": "X-long_report_key_sentence_buried", "source": "synthetic", "category": "cross_cutting",
                  "application": application(c),
                  "documents": [doc("D1", "19", t, "pass", element_block("19"), "A long assessment from a public authority. One paragraph contains the required assessment; the tool should quote it.")],
                  "expected_overall": "pass"})

    c = mkctx(r)
    d1 = doc("D1", "11", PARAS["11"]["render"](c, "hedged_judgement", r), "fail",
             element_block("11", {"consistent_with_domestic_abuse": "not_met"}), "Hedged health judgement.")
    d2 = doc("D2", "17", PARAS["17"]["render"](c, "vague_matters", r), "fail",
             element_block("17", {"specific_matters": "not_met"}), "Specific matters not described.")
    d3 = doc("D3", "13", PARAS["13"]["render"](c, None, r), "pass", element_block("13"), "Valid MARAC letter.")
    cases.append({"id": "X-bundle_one_valid", "source": "synthetic", "category": "cross_cutting", "application": application(c),
                  "documents": [d1, d2, d3], "expected_overall": "pass",
                  "notes": "One valid piece of prescribed evidence is enough; the two weak documents don't sink the application."})

    c = mkctx(r)
    d1 = doc("D1", "11", PARAS["11"]["render"](c, "hedged_judgement", r), "fail",
             element_block("11", {"consistent_with_domestic_abuse": "not_met"}), "Hedged health judgement.")
    d2 = doc("D2", "18", PARAS["18"]["render"](c, "perpetrator_not_named", r), "fail",
             element_block("18", {"perpetrator_named": "not_met"}), "No perpetrator named.")
    cases.append({"id": "X-bundle_all_invalid", "source": "synthetic", "category": "cross_cutting", "application": application(c),
                  "documents": [d1, d2], "expected_overall": "fail"})

    c = mkctx(r)
    t = F("IN THE FAMILY COURT SITTING AT {CITY_UP}\nCase number: {case_no}\n"
          "Family Law Act 1996 – Non-Molestation Order (section 42)\n\nApplicant: {A}, on behalf of {CH} (a child)\n"
          "Respondent: {B} (father of the child)\n\nThe court orders that the Respondent, {B}, must not use or threaten "
          "violence against {CH}, and must not go within 100 metres of {CH_first}'s school.\n\n"
          "This order was made on notice on {d30} and lasts until {f365}.\n\nDistrict Judge {author}", c)
    if c["b_he"] == "she":
        t = t.replace("(father of the child)", "(mother of the child)")
    cases.append({"id": "X-child_is_protected_party_allowed", "source": "synthetic", "category": "cross_cutting",
                  "application": application(c),
                  "documents": [doc("D1", "7", t, "pass", element_block("7"), "Para 7 allows the protected person to be someone else in a family relationship with B, such as the child.")],
                  "expected_overall": "pass"})

    c = mkctx(r)
    t = PARAS["17"]["render"](c, None, r)
    t = t.replace(F("we have provided {A} with support in relation to {a_her} needs", c),
                  F("we have provided {CH}, the child of {A}, with support in relation to {CH_first}'s needs", c))
    t = t.replace(F("In my reasonable professional judgement {A} is", c), F("In my reasonable professional judgement {CH} is", c))
    t = t.replace(F("We have provided {A} with the following support", c), F("We have provided {CH} with the following support", c))
    t = re.sub(re.escape(c["A"]) + r" needed this support because [^\n]*",
               F("{CH_first} needed this support because {CH_first} had witnessed abuse at home and was showing signs of distress.", c), t)
    cases.append({"id": "X-child_victim_not_allowed_para17", "source": "synthetic", "category": "cross_cutting",
                  "application": application(c),
                  "documents": [doc("D1", "17", t, "fail", element_block("17", {"supported_applicant": "not_met", "professional_judgement": "not_met"}),
                                    "Para 17 must relate to the applicant themselves; this letter is about the child.")],
                  "expected_overall": "fail"})

    c, t = render_case("11", None, r)
    m = re.search(r"In my reasonable professional judgement[^.]*\.", t)
    garbled = "".join(ch if (ch == " " or r.random() < 0.45) else r.choice("#%~|?*") for ch in m.group(0))
    t = t.replace(m.group(0), garbled)
    cases.append({"id": "X-illegible_scan", "source": "synthetic", "category": "cross_cutting", "application": application(c),
                  "documents": [doc("D1", "11", t, "refer", element_block("11", {"consistent_with_domestic_abuse": "unclear"}),
                                    "The key sentence is illegible (poor scan). Ask for a clearer copy rather than rejecting.")],
                  "expected_overall": "refer"})

    c = mkctx(r)
    t = F("{d10}\n\nRe: {A}\n\n[Letter written in Polish on the headed paper of a medical clinic in Kraków. "
          "No English translation has been supplied.]\n\nlek. med. {author}", c)
    cases.append({"id": "X-untranslated_overseas_letter", "source": "synthetic", "category": "cross_cutting",
                  "application": application(c),
                  "documents": [doc("D1", "11", t, "refer",
                                    element_block("11", {"appropriate_health_professional": "unclear", "examined_applicant": "unclear",
                                                         "consistent_with_domestic_abuse": "unclear"}),
                                    "Overseas evidence is accepted but must be in English or come with a translation plus the original.")],
                  "expected_overall": "refer"})
    return cases


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--valid", type=int, default=2, help="compliant documents per paragraph")
    ap.add_argument("--out", default="synthetic_cases.json")
    a = ap.parse_args()
    r = random.Random(a.seed)
    cases = para_cases(r, a.valid) + cross_cases(r)
    meta = {"description": "Synthetic Domestic Abuse Gateway evidence cases, labelled by construction from the LAA "
                           "Evidence Requirements guidance v15 (June 2026). All names and organisations are fictional.",
            "seed": a.seed, "n_cases": len(cases),
            "labels": {"outcome": ["pass", "fail", "refer"], "element_status": ["met", "not_met", "unclear"]}}
    with open(a.out, "w") as fh:
        json.dump({"meta": meta, "cases": cases}, fh, indent=2, ensure_ascii=False)
    print(f"Wrote {len(cases)} cases to {a.out}")


if __name__ == "__main__":
    main()
