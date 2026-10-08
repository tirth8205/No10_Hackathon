#!/usr/bin/env python3
"""Generate pitch/clip5/scene.html (cursor keyframes and per-row timings are computed)."""
T = 15.0
def pct(t): return f"{t / T * 100:.3f}%"

ROW_TOP, ROW_H = 300, 78
CB_X = 824
def row_cy(i): return ROW_TOP + i * ROW_H + ROW_H // 2
CLICKS = [2.85 + 0.38 * i for i in range(8)]
AGREE = (962, 712, 6.95)
DL = (330, 805, 9.2)

reqs = [
    ("Applicant named", "“I can confirm that we have provided Jane Doe with support…”"),
    ("Organisation is in the UK", "“…our organisation is situated in England and Wales”"),
    ("Operating for six months or more", "“an uninterrupted period of six months or more.”"),
    ("Confirms support was provided", "“I can confirm that we have provided Jane Doe with support…”"),
    ("Professional judgement: a victim", "“In my reasonable professional judgement Jane Doe is…”"),
    ("Specific matters relied on", "“Jane's disclosures to me of emotional, physical and psychological abuse…”"),
    ("Support described", "“safety planning, signposting to relevant agencies, advocacy…”"),
    ("Why the applicant needed support", "“…professional support and guidance to end the cycle of abuse.”"),
]
# mark boxes on the d2-06b crop, in crop image pixels: x0, y0, x1, y1
marks = [(86, 586, 890, 621), (86, 520, 882, 552), (86, 552, 510, 581), (38, 586, 890, 621),
         (86, 651, 888, 710), (86, 713, 864, 802), (86, 805, 850, 866), (86, 870, 844, 931)]

# cursor path: (t, x, y)
path = [(0, 1560, 1010), (0.6, 1560, 1010), (1.3, 985, 383), (1.6, 985, 383), (2.1, 417, 771), (2.6, 417, 771)]
for i, c in enumerate(CLICKS):
    path += [(c - 0.17, CB_X, row_cy(i)), (c + 0.1, CB_X, row_cy(i))]
path += [(6.0, 1300, 880), (6.8, AGREE[0], AGREE[1]), (7.3, AGREE[0], AGREE[1]),
         (8.2, 700, 560), (9.0, DL[0], DL[1]), (9.9, DL[0], DL[1])]
cur_kf = "\n".join(f"    {pct(t)} {{ transform: translate({x}px, {y}px); }}" for t, x, y in path)

clicks_all = [(CB_X, row_cy(i), c) for i, c in enumerate(CLICKS)] + [AGREE, DL]
rings = "\n".join(
    f'<div class="ring" style="left:{x}px;top:{y}px;animation-delay:{c:.2f}s"></div>' for x, y, c in clicks_all)

rows_html = []
for i, (name, quote) in enumerate(reqs):
    c = CLICKS[i]
    rows_html.append(f'''      <div class="rrow" style="top:{i * ROW_H}px">
        <div class="rowbg" style="animation-delay:{c:.2f}s"></div>
        <div class="cb"><div class="tick" style="animation-delay:{c:.2f}s"></div></div>
        <div class="num">{i + 1}</div>
        <div class="rtext"><div class="rname">{name}</div><div class="rq">{quote}</div></div>
        <div class="tag">Included</div>
      </div>''')
rows_html = "\n".join(rows_html)

marks_html = "\n".join(
    f'<div class="mk" style="left:{x0}px;top:{y0}px;width:{x1 - x0}px;height:{y1 - y0}px;animation-delay:{CLICKS[i] - 0.1:.2f}s"></div>'
    for i, (x0, y0, x1, y1) in enumerate(marks))

html = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Clip 5 · Gatekeeper to verifier</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: 1920px; height: 1080px; overflow: hidden; }}
  body {{ font-family: Arial, "Helvetica Neue", sans-serif; color: #0b0c0c; background: #f3f2f1; position: relative; }}
  .abs {{ position: absolute; }}

  .chip {{ position: absolute; left: 96px; top: 72px; font-size: 26px; font-weight: 700; color: #fff; background: #0b0c0c;
          padding: 8px 18px; letter-spacing: .02em; animation: fade .6s ease-out .1s both; z-index: 5; }}
  .footer {{ position: absolute; right: 96px; top: 84px; font-size: 18px; color: #505a5f; animation: fade .6s ease-out .4s both; }}

  /* phase wrappers: outer fades out, inner fades in */
  .out {{ position: absolute; inset: 0; }}
  .in {{ position: absolute; inset: 0; }}

  /* browser chrome */
  .win {{ position: absolute; background: #fff; border-radius: 12px; overflow: hidden;
          box-shadow: 0 2px 6px rgba(0,0,0,.16), 0 24px 60px rgba(0,0,0,.14); }}
  .bar {{ height: 44px; background: #e4e3e1; display: flex; align-items: center; padding: 0 18px; gap: 9px; border-bottom: 1px solid #cfcdca; }}
  .bar i {{ width: 13px; height: 13px; border-radius: 50%; background: #b1b4b6; display: block; }}
  .bar .tab {{ margin-left: 18px; background: #fff; border-radius: 8px 8px 0 0; height: 34px; margin-top: 10px; padding: 0 22px;
              display: flex; align-items: center; font-size: 17px; color: #0b0c0c; }}
  .vp {{ position: relative; overflow: hidden; }}

  /* ---------- phase 1: the check page, pre-checked ---------- */
  .p1o {{ animation: fadeout .15s ease-in 2.42s both; }}
  .p1i {{ animation: fade .6s ease-out .15s both; }}
  .w1 {{ left: 96px; top: 150px; width: 1152px; }}
  .w1 .vp {{ width: 1152px; height: 740px; }}
  .w1 .vp img {{ position: absolute; width: 1670px; left: -265px; top: -20px; display: block; }}
  .box {{ position: absolute; border: 5px solid #ffdd00; border-radius: 6px; box-shadow: 0 0 0 3px #0b0c0c; }}
  .b1 {{ left: 745px; top: 332px; width: 480px; height: 126px; animation: pop .35s ease-out .9s both; }}
  .b2 {{ left: 170px; top: 738px; width: 474px; height: 59px; animation: pop .35s ease-out 1.5s both; }}
  .badge {{ position: absolute; width: 50px; height: 50px; border-radius: 50%; background: #0b0c0c; color: #fff; font-size: 28px;
            font-weight: 700; display: flex; align-items: center; justify-content: center; }}
  .bd1 {{ left: 1196px; top: 306px; animation: pop .35s ease-out .95s both; }}
  .bd2 {{ left: 620px; top: 713px; animation: pop .35s ease-out 1.55s both; }}
  .side1 {{ left: 1300px; top: 160px; width: 524px; }}
  .eyebrow {{ font-size: 26px; color: #505a5f; line-height: 1.25; }}
  .h {{ font-size: 56px; font-weight: 700; line-height: 1.08; margin-top: 12px; }}
  .call {{ display: flex; gap: 18px; margin-top: 34px; font-size: 30px; line-height: 1.25; }}
  .call .badge {{ position: static; flex: none; }}
  .c1 {{ animation: slide .45s ease-out .95s both; }}
  .c2 {{ animation: slide .45s ease-out 1.55s both; }}

  /* ---------- phase 2: verify each point ---------- */
  .p2o {{ animation: fadeout .15s ease-in 7.25s both; }}
  .p2i {{ animation: fade .15s ease-out 2.6s both; }}
  .pdf {{ left: 96px; top: 150px; width: 616px; height: 780px; overflow: hidden; background: #fff; border-radius: 4px;
          box-shadow: 0 2px 6px rgba(0,0,0,.16), 0 18px 48px rgba(0,0,0,.12); }}
  .pdfin {{ position: absolute; left: 0; top: 0; width: 1026px; height: 1300px; transform: scale(.6); transform-origin: 0 0; }}
  .pdfin img {{ display: block; width: 1026px; }}
  .mk {{ position: absolute; border: 6px solid #ffdd00; border-radius: 6px; box-shadow: 0 0 0 3px #0b0c0c; opacity: 0;
         animation: flash .9s ease-out both; }}
  .mk6 {{ position: absolute; left: 140px; top: 713px; width: 726px; height: 89px; background: rgba(255,221,0,.5);
          mix-blend-mode: multiply; animation: fade .4s ease-out 5.95s both; }}
  .pdflabel {{ position: absolute; left: 96px; top: 940px; font-size: 22px; color: #505a5f; }}

  .p2ao {{ animation: fadeout .15s ease-in 5.78s both; }}
  .list {{ left: 780px; top: 150px; width: 1044px; }}
  .lh {{ font-size: 48px; font-weight: 700; line-height: 1.1; }}
  .ls {{ font-size: 28px; color: #505a5f; margin-top: 10px; }}
  .rows {{ position: absolute; left: 780px; top: {ROW_TOP}px; width: 1044px; height: {8 * ROW_H}px; background: #fff;
           box-shadow: 0 2px 6px rgba(0,0,0,.10); }}
  .rrow {{ position: absolute; left: 0; width: 1044px; height: {ROW_H}px; border-bottom: 1px solid #b1b4b6; display: flex;
          align-items: center; padding: 0 22px; gap: 18px; }}
  .rowbg {{ position: absolute; inset: 0; background: #e8f3ec; opacity: 0; animation: fade .3s ease-out both; }}
  .cb {{ position: relative; width: 44px; height: 44px; border: 3px solid #0b0c0c; background: #fff; flex: none; }}
  .tick {{ position: absolute; left: 9px; top: 4px; width: 19px; height: 28px; border: solid #00703c; border-width: 0 7px 7px 0;
           transform: rotate(45deg); opacity: 0; animation: tick .25s ease-out both; }}
  .num {{ position: relative; width: 34px; height: 34px; background: #0b3b2a; color: #fff; font-family: Georgia, serif; font-weight: 700;
          font-size: 22px; display: flex; align-items: center; justify-content: center; flex: none; }}
  .rtext {{ position: relative; flex: 1; min-width: 0; }}
  .rname {{ font-size: 29px; font-weight: 700; line-height: 1.1; }}
  .rq {{ font-size: 21px; color: #505a5f; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 4px; }}
  .tag {{ position: relative; font-size: 24px; background: #cce2d8; color: #005a30; padding: 5px 12px; flex: none; }}

  /* comparison */
  .cmpi {{ animation: fade .15s ease-out 5.95s both; }}
  .cmp {{ left: 780px; top: 150px; width: 1044px; }}
  .vlabel {{ display: flex; align-items: center; gap: 16px; font-size: 28px; font-weight: 700; margin-top: 30px; }}
  .vtag {{ font-size: 24px; font-weight: 400; padding: 5px 12px; }}
  .vtag.old {{ background: #f4cdc6; color: #942514; }}
  .vtag.new {{ background: #cce2d8; color: #005a30; }}
  .crop {{ position: relative; overflow: hidden; background: #fff; margin-top: 12px; box-shadow: 0 2px 6px rgba(0,0,0,.12); }}
  .crop img {{ position: absolute; display: block; }}
  .cold {{ width: 1044px; height: 60px; animation: slide .4s ease-out 6.05s both; }}
  .cold img {{ width: 1360px; left: -122px; top: -198px; }}
  .strike {{ position: absolute; left: 30px; top: 31px; height: 5px; background: #d4351c; width: 0; animation: strike6 .5s ease-in-out 7.15s both; }}
  .cnew {{ width: 1044px; height: 132px; animation: slide .4s ease-out 6.35s both; }}
  .cnew img {{ width: 1360px; left: -100px; top: -936px; }}
  .note {{ font-size: 28px; margin-top: 10px; }}
  .note.r {{ color: #d4351c; font-weight: 700; }}
  .note.g {{ color: #00703c; font-weight: 700; }}
  .o1 {{ animation: fade .4s ease-out 6.05s both; }}
  .o2 {{ animation: fade .4s ease-out 6.35s both; }}
  .btn {{ display: inline-block; margin-top: 34px; background: #00703c; color: #fff; font-size: 32px; padding: 14px 24px;
          box-shadow: 0 4px 0 #002d18; animation: fade .3s ease-out 6.55s both, press .3s ease-out {AGREE[2]:.2f}s both; }}

  /* ---------- phase 3: submit through the existing portal ---------- */
  .p3o {{ animation: fadeout .15s ease-in 10.42s both; }}
  .p3i {{ animation: rise .45s cubic-bezier(.2,.8,.2,1) 7.4s both; }}
  .w3 {{ left: 96px; top: 160px; width: 1005px; }}
  .w3 .vp {{ width: 1005px; height: 720px; }}
  .w3 .vp img {{ position: absolute; width: 2160px; left: -330px; top: -555px; display: block;
                animation: pan3 .8s cubic-bezier(.45,0,.25,1) 7.95s both; }}
  .dlpress {{ position: absolute; left: 60px; top: 572px; width: 344px; height: 57px; background: rgba(0,0,0,.25); opacity: 0;
              animation: flash2 .4s ease-out {DL[2]:.2f}s both; }}
  .side3 {{ left: 1180px; top: 190px; width: 644px; }}
  .side3 .h {{ animation: slide .45s ease-out 7.5s both; }}
  .side3 .eyebrow {{ animation: slide .45s ease-out 7.75s both; margin-top: 22px; }}
  .file {{ margin-top: 48px; display: flex; gap: 22px; align-items: center; background: #fff; padding: 22px 26px;
           border-left: 8px solid #00703c; box-shadow: 0 2px 6px rgba(0,0,0,.12); animation: pop .4s ease-out {DL[2] + 0.2:.2f}s both; }}
  .file .ic {{ width: 54px; height: 66px; background: #1d70b8; position: relative; flex: none; clip-path: polygon(0 0, 70% 0, 100% 24%, 100% 100%, 0 100%); }}
  .file .ic::after {{ content: "ZIP"; position: absolute; left: 0; right: 0; bottom: 10px; text-align: center; color: #fff; font-size: 16px; font-weight: 700; }}
  .file b {{ display: block; font-size: 30px; }}
  .file span {{ font-size: 24px; color: #505a5f; }}
  .portal {{ margin-top: 26px; font-size: 28px; line-height: 1.3; animation: fade .4s ease-out {DL[2] + 0.45:.2f}s both; }}

  /* ---------- phase 4: the ledger ---------- */
  .p4i {{ animation: rise .45s cubic-bezier(.2,.8,.2,1) 10.6s both; }}

  /* =====================================================================
     LEDGER (copied verbatim from clip2/scene.html)
     ===================================================================== */
  .ledger {{ position: absolute; left: 640px; top: 420px; width: 1184px; display: flex; gap: 40px; }}
  .ledger .col {{ flex: 1; background: #fff; border-top: 10px solid #0b0c0c; box-shadow: 0 2px 6px rgba(0,0,0,.08); padding: 0 28px 10px; }}
  .ledger .hd {{ display: flex; align-items: baseline; justify-content: space-between; padding: 18px 0 14px; border-bottom: 3px solid #0b0c0c; }}
  .ledger .hd b {{ font-size: 30px; letter-spacing: .06em; }}
  .ledger .hd span {{ font-size: 24px; color: #505a5f; }}
  .ledger .row {{ position: relative; display: flex; align-items: center; gap: 20px; height: 82px; font-size: 36px;
                 border-bottom: 2px solid #b1b4b6; }}
  .ledger .row:last-child {{ border-bottom: 0; }}
  .ledger .row i {{ flex: none; width: 40px; height: 40px; border-radius: 50%; background: #d4351c; color: #fff; font-style: normal;
                   font-size: 32px; font-weight: 700; line-height: 40px; text-align: center; }}
  .ledger .row::after {{ content: ""; position: absolute; left: 60px; top: 50%; height: 4px; width: 0; background: #505a5f; }}
  .ledger .row.cleared, .ledger .row.clearing {{ color: #b1b4b6; }}
  .ledger .row.cleared i {{ background: #b1b4b6; }}
  .ledger .row.cleared::after {{ width: calc(100% - 70px); background: #b1b4b6; }}
  @keyframes clear {{ to {{ color: #b1b4b6; }} }}
  /* ===================== end LEDGER styles ===================== */

  /* Ledger placement and timing for this clip only: the .cleared look, animated in clip 2's row order */
  .ledger {{ left: 96px; top: 190px; width: 960px; }}
  .ledger [data-line="sol-rework"]     {{ animation: clear .4s ease-out 11.0s both; }}
  .ledger [data-line="sol-chase-jane"] {{ animation: clear .4s ease-out 11.4s both; }}
  .ledger [data-line="sol-chase-sw"]   {{ animation: clear .4s ease-out 11.8s both; }}
  .ledger [data-line="sol-rework"] i     {{ animation: clearI .4s ease-out 11.0s both; }}
  .ledger [data-line="sol-chase-jane"] i {{ animation: clearI .4s ease-out 11.4s both; }}
  .ledger [data-line="sol-chase-sw"] i   {{ animation: clearI .4s ease-out 11.8s both; }}
  .ledger [data-line="sol-rework"]::after     {{ animation: clearLine .45s ease-in-out 11.0s both; }}
  .ledger [data-line="sol-chase-jane"]::after {{ animation: clearLine .45s ease-in-out 11.4s both; }}
  .ledger [data-line="sol-chase-sw"]::after   {{ animation: clearLine .45s ease-in-out 11.8s both; }}
  @keyframes clearI {{ to {{ background: #b1b4b6; }} }}
  @keyframes clearLine {{ from {{ width: 0; background: #b1b4b6 }} to {{ width: calc(100% - 70px); background: #b1b4b6 }} }}
  .side4 {{ left: 1150px; top: 200px; width: 674px; }}
  .side4 .h {{ font-size: 60px; animation: slide .45s ease-out 10.75s both; }}
  .side4 .eyebrow {{ margin-top: 26px; font-size: 30px; animation: slide .45s ease-out 11.2s both; }}

  /* caption */
  .caption {{ position: absolute; left: 0; right: 0; bottom: 0; height: 150px; background: #0b0c0c; color: #fff; z-index: 6;
             display: flex; align-items: center; padding: 0 96px; gap: 28px; animation: up .5s cubic-bezier(.2,.8,.2,1) 10.6s both; }}
  .caption b {{ font-size: 46px; }}
  .caption .y {{ font-size: 46px; color: #ffdd00; font-weight: 700; animation: fade .5s ease-out 11.4s both; }}

  /* cursor */
  .cur {{ position: absolute; left: 0; top: 0; z-index: 9; animation: curpath {T}s linear 0s both, curvis {T}s linear 0s both; }}
  .cur svg {{ display: block; filter: drop-shadow(0 2px 3px rgba(0,0,0,.35)); }}
  .ring {{ position: absolute; z-index: 8; width: 70px; height: 70px; margin: -35px 0 0 -35px; border-radius: 50%;
           border: 5px solid #1d70b8; opacity: 0; animation: ring .55s ease-out forwards; }}

  @keyframes curpath {{
{cur_kf}
  }}
  @keyframes curvis {{ 0% {{ opacity: 0 }} {pct(0.6)} {{ opacity: 0 }} {pct(0.85)} {{ opacity: 1 }} {pct(9.9)} {{ opacity: 1 }} {pct(10.2)} {{ opacity: 0 }} 100% {{ opacity: 0 }} }}
  @keyframes ring {{ 0% {{ opacity: .95; transform: scale(.3) }} 100% {{ opacity: 0; transform: scale(1.4) }} }}
  @keyframes fade {{ from {{ opacity: 0 }} to {{ opacity: 1 }} }}
  @keyframes fadeout {{ from {{ opacity: 1 }} to {{ opacity: 0 }} }}
  @keyframes rise {{ from {{ opacity: 0; transform: translateY(40px) }} to {{ opacity: 1; transform: none }} }}
  @keyframes slide {{ from {{ opacity: 0; transform: translateX(30px) }} to {{ opacity: 1; transform: none }} }}
  @keyframes pop {{ from {{ opacity: 0; transform: scale(1.25) }} to {{ opacity: 1; transform: none }} }}
  @keyframes up {{ from {{ transform: translateY(150px) }} to {{ transform: none }} }}
  @keyframes tick {{ from {{ opacity: 0; transform: rotate(45deg) scale(.3) }} to {{ opacity: 1; transform: rotate(45deg) scale(1) }} }}
  @keyframes flash {{ 0% {{ opacity: 0 }} 20% {{ opacity: 1 }} 75% {{ opacity: 1 }} 100% {{ opacity: 0 }} }}
  @keyframes flash2 {{ 0% {{ opacity: 0 }} 30% {{ opacity: 1 }} 100% {{ opacity: 0 }} }}
  @keyframes press {{ 0% {{ transform: none }} 40% {{ transform: translateY(3px); box-shadow: 0 1px 0 #002d18; background: #005a30 }} 100% {{ transform: none }} }}
  @keyframes strike6 {{ from {{ width: 0 }} to {{ width: 990px }} }}
  @keyframes strikeL {{ from {{ width: 0 }} to {{ width: calc(100% + 12px) }} }}
  @keyframes grey {{ from {{ color: #0b0c0c }} to {{ color: #b1b4b6 }} }}
  @keyframes dot {{ from {{ background: #d4351c }} to {{ background: #b1b4b6 }} }}
  @keyframes pan3 {{ from {{ top: -555px }} to {{ top: -1082px }} }}
</style>
</head>
<body>
  <div class="chip">WITH GATEWAY CHECK</div>
  <div class="footer">All names fictional. Prototype screens.</div>

  <!-- phase 1 -->
  <div class="out p1o"><div class="in p1i">
    <div class="win w1"><div class="bar"><i></i><i></i><i></i><div class="tab">Gateway Check · Jane Doe · Support letter</div></div>
      <div class="vp"><img src="d2-06-document-pdf-marks.png" alt=""></div></div>
    <div class="box b1"></div><div class="badge bd1">1</div>
    <div class="box b2"></div><div class="badge bd2">2</div>
    <div class="abs side1">
      <div class="eyebrow">Jane's new letter, on her solicitor's screen</div>
      <div class="h">It arrives<br>pre\u2011checked.</div>
      <div class="call c1"><div class="badge">1</div><div>All 8 requirements included</div></div>
      <div class="call c2"><div class="badge">2</div><div>Each one quotes the exact sentence, highlighted on the letter</div></div>
    </div>
  </div></div>

  <!-- phase 2 -->
  <div class="out p2o"><div class="in p2i">
    <div class="abs pdf"><div class="pdfin"><img src="d2-06b-crop-pdf-page.png" alt="">
{marks_html}
      <div class="mk6"></div>
    </div></div>
    <div class="out p2ao">
      <div class="abs list"><div class="lh">Her solicitor verifies each point.</div>
        <div class="ls">Ticked one at a time. There is no ‘approve all’.</div></div>
      <div class="rows">
{rows_html}
      </div>
    </div>
    <div class="in cmpi"><div class="abs cmp">
      <div class="lh">What changed in the newer version</div>
      <div class="vlabel o1">Specific matters relied on <span class="vtag old">Older version · 7 of 8</span></div>
      <div class="crop cold"><img src="d1-07b-crop-pdf-problem-sentence.png" alt=""></div>
      <div class="note r o1">Check flagged: no specific matters named</div>
      <div class="vlabel o2">Specific matters relied on <span class="vtag new">Newer version · 8 of 8</span></div>
      <div class="crop cnew"><img src="d2-06b-crop-pdf-page.png" alt=""></div>
      <div class="note g o2">Now specific. The solicitor agrees.</div>
      <div class="btn">Choose what to submit</div>
    </div></div>
  </div></div>

  <!-- phase 3 -->
  <div class="out p3o"><div class="in p3i">
    <div class="win w3"><div class="bar"><i></i><i></i><i></i><div class="tab">Gateway Check · Submit</div></div>
      <div class="vp"><img src="d3-02-submit-full.png" alt=""><div class="dlpress"></div></div></div>
    <div class="abs side3">
      <div class="h">Submit through the existing portal, as today.</div>
      <div class="eyebrow">One download: the letter and a summary of what was checked.</div>
      <div class="file"><div class="ic"></div><div><b>Evidence pack downloaded</b><span>Letter + verification summary</span></div></div>
      <div class="portal">Then uploaded in Civil Apply, as now.</div>
    </div>
  </div></div>

  <!-- phase 4 -->
  <div class="in p4i">
    <!-- LEDGER markup: SOLICITOR column copied from clip2/scene.html -->
    <div class="ledger">
      <div class="col sol">
        <div class="hd"><b>SOLICITOR</b><span>after a return</span></div>
        <div class="row" id="sol-rework" data-line="sol-rework"><i>+</i>Unpaid rework</div>
        <div class="row" id="sol-chase-jane" data-line="sol-chase-jane"><i>+</i>Chasing Jane</div>
        <div class="row" id="sol-chase-sw" data-line="sol-chase-sw"><i>+</i>Chasing her support worker</div>
        <div class="row" id="sol-fee" data-line="sol-fee"><i>+</i>Fee held up</div>
      </div>
    </div>
    <div class="abs side4">
      <div class="h">They stay responsible for what they send.</div>
      <div class="eyebrow">The tool checks. A person decides.</div>
    </div>
  </div>

{rings}
  <div class="cur"><svg width="40" height="54" viewBox="0 0 20 27"><path d="M1 1 L1 22 L6.5 17 L10.5 26 L14 24.5 L10 16 L17 16 Z" fill="#0b0c0c" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg></div>

  <div class="caption"><b>Gatekeeper → verifier.</b><span class="y">Still responsible.</span></div>
</body>
</html>
'''
open("/Users/zahid/Documents/no10hack/pitch/clip5/scene.html", "w").write(html)
print("ok")
