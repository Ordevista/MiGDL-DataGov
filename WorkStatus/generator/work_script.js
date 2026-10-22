/* MiGDL Work Ontology — four audience reads over one graph.
   The same work items are never recounted differently per view; only which of them,
   and which of their properties, each view surfaces. */
(function () {
  "use strict";
  var W = window.WORK, J = window.JOURNEY;
  var ITEMS = W.issues, BY = {}, DIST = W.districts, C = W.companions;
  ITEMS.forEach(function (i) { BY[i.k] = i; });

  var AUD = [
    { id: "map",    label: "The map",         sub: "as drawn, with live status", key: null },
    { id: "dev",    label: "Developer",       sub: "asset &amp; defect grain", key: "developer" },
    { id: "sprint", label: "Sprint planning", sub: "what is plannable",        key: "sprint-planning" },
    { id: "lead",   label: "Leadership",      sub: "progress &amp; risk",      key: "leadership" },
    { id: "stake",  label: "K-12 stakeholder", sub: "is my district in?",      key: "stakeholder" },
    { id: "plan",   label: "Game plan",       sub: "stages &amp; gates",       key: null }
  ];
  var LAYLABEL = { bronze: "Bronze", silver: "Silver", goldstage: "Gold stage",
    "gold-conformed": "Gold conf", "gold-star": "Gold star",
    "staging-temp": "Temp", platinum: "Platinum" };
  var STAGE_SEQ = ["intake", "connection-setup", "bronze-load", "descriptor-load",
    "silver-load", "goldplat-load", "validation", "ready-for-stage", "complete"];
  var STAGE_LABEL = { intake: "Intake", "connection-setup": "Connection", "bronze-load": "Bronze",
    "descriptor-load": "Descriptor", "silver-load": "Silver", "goldplat-load": "Gold / Plat",
    validation: "Validation", "ready-for-stage": "Ready for stage", complete: "Live",
    blocked: "Blocked" };

  var state = { aud: "map", station: null };

  /* ---- helpers ---- */
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function el(h) { var d = document.createElement("div"); d.innerHTML = h; return d; }
  function jira(k) { return '<a class="mono" href="' + C.jira + k + '" target="_blank" rel="noopener">' + k + "</a>"; }
  function catPill(c) {
    var m = { "To Do": "", "In Progress": "acc", Done: "ok" };
    return '<span class="pill ' + (m[c] || "") + '">' + esc(c) + "</span>";
  }
  function layTag(l) {
    return '<span class="lay ' + l + '">' + esc(LAYLABEL[l] || l) + "</span>";
  }
  function pct(a, b) { return b ? Math.round((a / b) * 100) : 0; }

  /* station membership: by medallion layer or by operational stage */
  function atStation(i, st) {
    if (!st) return true;
    var s = J.stations.filter(function (x) { return x.slug === st; })[0];
    if (!s) return true;
    if (i.ly.some(function (l) { return s.layers.indexOf(l) >= 0; })) return true;
    if (i.stg && s.stages.indexOf(i.stg) >= 0) return true;
    return false;
  }
  function pool(audKey) {
    return ITEMS.filter(function (i) {
      return i.au.indexOf(audKey) >= 0 && atStation(i, state.station);
    });
  }

  /* ---- station rail ---- */
  function rail() {
    var r = document.getElementById("rail");
    r.innerHTML = J.stations.map(function (s) {
      var n = ITEMS.filter(function (i) { return atStation(i, s.slug); }).length;
      var pains = J.pains.filter(function (p) { return p.station === s.slug && !p.none; }).length;
      var lay = s.layers.map(function (l) { return LAYLABEL[l] || l; }).join(" · ") || s.cap || "";
      return '<button class="stg" type="button" data-s="' + s.slug + '"' +
        ' aria-pressed="' + (state.station === s.slug) + '">' +
        '<span class="nm">' + s.n + ". " + esc(s.name.replace(/^MiGDL /, "")) + "</span>" +
        '<span class="ct">' + n + '</span> <span class="sub">items' +
        (pains ? " · " + pains + " pain" : "") + "</span>" +
        '<span class="lyr">' + esc(lay) + "</span>" +
        "</button>";
    }).join("");
    r.querySelectorAll(".stg").forEach(function (b) {
      b.addEventListener("click", function () {
        state.station = state.station === b.dataset.s ? null : b.dataset.s;
        rail(); render();
      });
    });
  }

  /* ---- shared blocks ---- */
  function filterNote() {
    if (!state.station) return "";
    var s = J.stations.filter(function (x) { return x.slug === state.station; })[0];
    return '<div class="gap"><b>Filtered to station ' + s.n + ", " + esc(s.name) +
      ".</b> Only work mapped to that station’s layers or load stages is shown. " +
      "Click the station again to clear.</div>";
  }

  function reconTable(only) {
    var rows = J.recon.filter(function (r) { return !only || r.state === only; });
    if (!rows.length) return "<p class='hint'>Nothing to reconcile.</p>";
    return '<div class="card tscroll"><table><thead><tr>' +
      "<th>Fix</th><th>Ticket</th><th>Map says</th><th>Jira says now</th><th>Work item</th>" +
      "</tr></thead><tbody>" + rows.map(function (r) {
        var cls = r.state === "drifted" ? "warn" : r.state === "missing" ? "crit"
          : r.state === "agrees" ? "ok" : "";
        var now = r.state === "missing" ? "<i>no such issue in Jira</i>" : esc(r.now);
        return "<tr><td class='r mono'>" + r.fix + "</td><td>" + jira(r.key) + "</td>" +
          "<td>" + (r.claim ? esc(r.claim) : "<span class='pill'>not stated</span>") + "</td>" +
          "<td><span class='pill " + cls + "'>" + now + "</span></td>" +
          "<td class='ttl'>" + esc((r.sum || "").replace(/^MiGDL-TT-\d+: /, "")) + "</td></tr>";
      }).join("") + "</tbody></table></div>";
  }

  function barList(pairs, total, limit) {
    var max = Math.max.apply(null, pairs.map(function (p) { return p[1]; }).concat([1]));
    return '<div class="card">' + pairs.slice(0, limit || 99).map(function (p) {
      return '<div class="bar-row"><span class="lbl">' + esc(p[0]) + "</span>" +
        '<span><i class="hbar" style="width:' + Math.max(2, (p[1] / max) * 100) + '%"></i></span>' +
        '<span class="num">' + p[1] + "</span></div>";
    }).join("") + "</div>";
  }

  function statusBar(items) {
    var t = items.filter(function (i) { return i.sc === "To Do"; }).length;
    var p = items.filter(function (i) { return i.sc === "In Progress"; }).length;
    var d = items.filter(function (i) { return i.sc === "Done"; }).length;
    var n = t + p + d || 1;
    return '<span class="sbar"><i class="todo" style="width:' + (t / n) * 100 + '%"></i>' +
      '<i class="prog" style="width:' + (p / n) * 100 + '%"></i>' +
      '<i class="done" style="width:' + (d / n) * 100 + '%"></i></span>';
  }
  var SBAR_LEGEND = '<div class="legend">' +
    '<span><i style="background:var(--line-2)"></i>To do</span>' +
    '<span><i style="background:var(--accent)"></i>In progress</span>' +
    '<span><i style="background:var(--ok)"></i>Done</span></div>';


  /* the three nightly pipelines and the data age each produces */
  function freshBlock(plain) {
    var P = J.pipelines, B = P.filter(function (p) { return p.binding; })[0];
    return '<section class="sect"><h2>How old the data is</h2>' +
      '<p class="hint">' + (plain
        ? 'Districts change their student information system all day. These three nightly runs carry those changes through to the apps, and the slowest one sets how old everything downstream is. Measured ' + esc(J.map.fresh_asof) + '.'
        : 'Pipeline ' + B.id + ' is the binding constraint: it sets the data age for everything downstream of it. Measured ' + esc(J.map.fresh_asof) + '.') +
      '</p><div class="card tscroll"><table><thead><tr>' +
      '<th>Run</th><th>Window</th><th>Rate</th>' +
      '<th class="r">Age, all districts</th><th class="r">Age, MiRead + MiEWIMS</th>' +
      '</tr></thead><tbody>' + P.map(function (p) {
        var cls = p.age_all >= 20 ? "crit" : p.age_all >= 10 ? "warn" : "ok";
        return "<tr><td class='ttl'><b>" + esc(p.name) + "</b>" +
          (p.binding ? " <span class='pill crit'>binding constraint</span>" : "") +
          "<div style='color:var(--muted);font-size:12px'>" + esc(p.note) + "</div></td>" +
          "<td class='mono'>" + esc(p.window) + "</td>" +
          "<td>" + esc(p.rate) + "</td>" +
          "<td class='r'><span class='pill " + cls + "'>" + p.age_all +
          (p.age_all === 1 ? " day" : " days") + "</span></td>" +
          "<td class='r'><span class='pill " + (p.age_app >= 20 ? "crit" : p.age_app >= 10 ? "warn" : "ok") +
          "'>" + p.age_app + (p.age_app === 1 ? " day" : " days") + "</span></td></tr>";
      }).join("") + "</tbody></table></div>" +
      '<div class="gap" style="margin-top:12px"><b>Target.</b> ' + esc(J.map.fresh_target) +
      ' Fix 6 is the lever: ten districts per job brings 29 days to 2, twenty brings it to 1.</div>' +
      "</section>";
  }

  function tile(k, v, n) {
    return '<div class="card kv"><span class="k">' + k + '</span><span class="v">' + v +
      "</span>" + (n ? '<span class="n">' + n + "</span>" : "") + "</div>";
  }


  /* ---- view: the map, replicated, with live Jira status ---- */
  var MARKCH = { ok: "✓", some: "!", lost: "✗" };

  function ticketChip(key) {
    var r = J.recon.filter(function (x) { return x.key === key; })[0] || {};
    var i = BY[key];
    var cls = r.state === "missing" ? "gone"
      : r.state === "drifted" ? "moved"
      : (i && i.sc === "Done") ? "done" : "";
    var now = r.state === "missing" ? "not in Jira" : ((i && i.st) || "?");
    var title = r.state === "drifted"
      ? "Map says “" + r.claim + "”; Jira says “" + now + "”"
      : r.state === "missing" ? "Cited on the map but no such issue exists"
      : "Jira: " + now;
    return '<a class="' + cls + '" href="' + C.jira + key + '" target="_blank" rel="noopener"' +
      ' title="' + esc(title) + '">' + key.replace("MIGDL-", "") +
      (r.state === "drifted" ? " ↑ " : " · ") + esc(now) + "</a>";
  }

  function vMap() {
    var S = J.stations, D = J.station_detail;
    var cells = [];
    function row(label, sub, fn) {
      cells.push('<div class="bandlbl">' + label + (sub ? "<small>" + sub + "</small>" : "") + "</div>");
      S.forEach(function (st) { cells.push(fn(st)); });
    }

    cells.push('<div class="bandlbl sthead">Station</div>');
    S.forEach(function (st) {
      var pl = J.pipelines.filter(function (p) { return p.stations.indexOf(st.slug) >= 0; })[0];
      cells.push('<div class="sthead"><span class="n">' + st.n + ". " +
        esc(st.name.replace(/^MiGDL /, "")) + '</span>' +
        '<span class="t">' + esc(st.tech) + '</span><span class="l">' +
        st.layers.map(layTag).join("") +
        (pl ? '<span class="pill' + (pl.binding ? " crit" : "") + '">Pipeline ' + pl.id +
          (pl.binding ? " · binding" : "") + "</span>" : "") +
        "</span></div>");
    });

    row("Full load", "first time a district comes in", function (st) {
      return '<div class="mapcell">' + esc((D[st.slug] || {}).full || "") + "</div>";
    });

    J.change_kinds.forEach(function (k) {
      row(k[0] + " · " + k[1], k[2], function (st) {
        var d = D[st.slug] || {};
        var mk = (d.mark || {})[k[0]] || "ok";
        return '<div><div class="chg"><span class="mk ' + mk + '">' + MARKCH[mk] + "</span>" +
          "<span>" + esc((d.delta || {})[k[0]] || "") + "</span></div></div>";
      });
    });

    row("What the app shows", "at the delivery counter", function (st) {
      var d = D[st.slug] || {};
      if (!d.app_shows) {
        return '<div class="mapcell none">' +
          (st.slug === "bronze" && d.note ? esc(d.note) : "—") + "</div>";
      }
      return "<div>" + d.app_shows.map(function (a) {
        return '<div class="chg" style="margin-bottom:5px"><span class="mk ' +
          (a[0] === "I" ? "ok" : "lost") + '">' + a[0] + "</span><span>" + esc(a[1]) +
          "</span></div>";
      }).join("") + "</div>";
    });

    row("Pain points", "where the package is lost", function (st) {
      var ps = J.pains.filter(function (p) { return p.station === st.slug; });
      if (!ps.length) return '<div class="mapcell none">—</div>';
      return "<div>" + ps.map(function (p) {
        return '<div class="painc' + (p.none ? " clean" : "") + '" style="margin-bottom:6px">' +
          '<span class="h">' + (p.map_n ? p.map_n + ". " : "") + esc(p.head) + "</span>" +
          (p.asks ? '<span class="q">“' + esc(p.asks) + "”</span>" : "") +
          (p.src ? '<span class="e">' + esc(p.src) + "</span>" : "") + "</div>";
      }).join("") + "</div>";
    });

    row("Fixes", "live Jira status", function (st) {
      var ps = J.pains.filter(function (p) { return p.station === st.slug; });
      var fs = [];
      ps.forEach(function (p) {
        J.fixes.forEach(function (f) { if (f.pain === p.n) fs.push(f); });
      });
      if (!fs.length) return '<div class="mapcell none">—</div>';
      return "<div>" + fs.map(function (f) {
        var keys = Object.keys(f.claim);
        var done = keys.filter(function (k) { return BY[k] && BY[k].sc === "Done"; }).length;
        var moved = keys.filter(function (k) {
          return J.recon.some(function (r) { return r.key === k && r.state === "drifted"; });
        }).length;
        return '<div class="fixc' + (keys.length ? "" : " nojira") + '" style="margin-bottom:6px">' +
          '<span class="h">Fix ' + f.n + ". " + esc(f.head) + "</span>" +
          '<span class="pill ' + (/Not yet/.test(f.chip) ? "crit" : /Complete|Partly/.test(f.chip) ? "ok" : "acc") +
          '" style="margin-top:5px">' + esc(f.chip) + "</span>" +
          (keys.length
            ? ' <span class="pill ok">' + done + " / " + keys.length + " done</span>" +
              (moved ? ' <span class="pill warn">' + moved + " moved</span>" : "") +
              '<div class="tix">' + keys.map(ticketChip).join("") + "</div>"
            : '<div class="tix"><span class="pill crit">no Jira ticket</span></div>') +
          (f.owners && f.owners.length
            ? "<div style='font-size:11px;color:var(--muted);margin-top:4px'>" +
              esc(f.owners.join(", ")) + "</div>" : "") +
          "</div>";
      }).join("") + "</div>";
    });

    row("Callouts", "constraints at the arrows", function (st) {
      var cs = J.callouts.filter(function (c) { return c.station === st.slug; });
      if (!cs.length) return '<div class="mapcell none">—</div>';
      return "<div>" + cs.map(function (c) {
        return '<div class="calo"><span class="h">Callout ' + c.id + ". " + esc(c.head) +
          "</span><span>" + esc(c.body) + "</span>" +
          "<span style='display:block;margin-top:5px;font-size:11px;color:var(--muted)'><b>Fix:</b> " +
          esc(c.fix) + "</span></div>";
      }).join("") + "</div>";
    });

    var whole = J.pains.filter(function (p) { return p.whole_route; })[0];
    var fixWhole = whole ? J.fixes.filter(function (f) { return f.pain === whole.n; })[0] : null;
    var nj = J.notjira;
    var KINDLBL = { fix: "Fix with no ticket", broken: "Broken reference",
      product: "App with no registration field", decision: "Open decision" };

    return '<section class="sect"><h2>Not in Jira</h2>' +
      '<p class="hint">' + nj.length + " things the map commits to that Jira cannot track today. " +
      "Kept apart by kind, because the remedy differs: a fix with no ticket needs one raised, " +
      "a broken reference needs correcting on the map, a product needs a field option, and a " +
      "decision needs an owner and a date rather than a ticket.</p>" +
      '<div class="card">' + nj.map(function (x) {
        var cls = x.kind === "broken" ? "crit" : x.kind === "decision" ? "acc" : "warn";
        return '<div class="nj"><span class="pill ' + cls + '">' + esc(KINDLBL[x.kind]) + "</span>" +
          '<span><span class="w">' + esc(x.what) + "</span>" +
          "<div style='color:var(--fg-2);margin-top:2px'>" + esc(x.why) + "</div>" +
          "<div style='color:var(--muted);font-size:12px;margin-top:2px'>" +
          (x.where ? esc(x.where) + " · " : "") + "<b>Remedy:</b> " + esc(x.remedy) +
          "</div></span></div>";
      }).join("") + "</div></section>" +

      '<section class="sect"><h2>The Data Journey, as drawn</h2>' +
      '<p class="hint">The seven stations with the map’s own bands, and every cited ticket ' +
      "carrying its live Jira status instead of the status the map was drawn with. " +
      '<span class="pill warn">↑</span> marks a ticket that has moved since ' +
      esc(J.map.jira_asof) + ". Scroll sideways; the band labels stay put.</p>" +
      '<div class="mapwrap"><div class="mapgrid">' + cells.join("") + "</div></div>" +
      '<div class="maplegend">' +
      "<span><b>✓</b> the change arrives</span>" +
      "<span><b>!</b> arrives only for some changes</span>" +
      "<span><b>✗</b> lost here, and does not come back</span>" +
      "<span><b>↑</b> ticket moved since the map was drawn</span>" +
      "</div></section>" +

      (whole ? '<section class="sect"><h2>Across the whole route</h2>' +
        '<div class="grid g2"><div class="painc"><span class="h">' + esc(whole.head) +
        '</span><span class="q">“' + esc(whole.asks) + '”</span><span>' +
        esc(whole.body) + '</span><span class="e">' + esc(whole.src) + "</span></div>" +
        (fixWhole ? '<div class="fixc nojira"><span class="h">Fix ' + fixWhole.n + ". " +
          esc(fixWhole.head) + "</span><span>" + esc(fixWhole.body) + "</span>" +
          '<div class="tix"><span class="pill crit">no Jira ticket</span></div>' +
          "<div style='font-size:11px;color:var(--muted);margin-top:4px'>" +
          esc(fixWhole.epic || "") + "</div></div>" : "") +
        "</div></section>" : "") +

      '<section class="sect"><h2>Recommended sequence</h2>' +
      '<p class="hint">' + esc(J.map.sequence) + "</p>" +
      reconTable("drifted") + "</section>";
  }


  /* ---- view: the operations game plan ---- */
  var GSTATE = { met: "ok", partial: "warn", open: "acc", untracked: "crit" };
  var GWORD = { met: "gate met", partial: "part done", open: "not started",
    untracked: "no Jira ticket" };

  function vPlan() {
    var G = window.GAMEPLAN, gs = G.gate_status;

    function gateChip(k) {
      var g = G.gates[k], st = gs[k];
      return '<span class="pill ' + GSTATE[st.state] + '">' + esc(g.label) + " · " +
        GWORD[st.state] + (st.tracked ? " " + st.done + "/" + st.total : "") + "</span>";
    }

    var stageCards = G.stages.map(function (st) {
      var states = st.gates.map(function (k) { return gs[k].state; });
      var worst = states.indexOf("untracked") >= 0 ? "untracked"
        : states.indexOf("open") >= 0 ? "open"
        : states.indexOf("partial") >= 0 ? "partial"
        : states.length ? "met" : "";
      return '<div class="stagec ' + worst + '">' +
        '<span class="sn">' + (st.n === 0 ? "Today" : "Stage " + st.n) + "</span>" +
        "<h3>" + esc(st.name) + "</h3>" +
        '<div class="gate"><b>Gate:</b> ' + esc(st.gate) +
        (st.eta ? " · <b>ETA</b> " + esc(st.eta) : "") +
        (st.gates.length ? "<div style='margin-top:5px;display:flex;gap:4px;flex-wrap:wrap'>" +
          st.gates.map(gateChip).join("") + "</div>" : "") + "</div>" +
        '<div class="does">' + esc(st.does) + "</div>" +
        '<div class="kpi"><b>Correct</b>' + st.correct.map(esc).join(" · ") + "</div>" +
        '<div class="kpi"><b>Throughput</b>' +
        (st.throughput_readable ? st.throughput.map(esc).join(" · ")
          : '<span class="unread">' + st.throughput.map(esc).join(" · ") +
            " — figures not readable from the PDF</span>") + "</div>" +
        '<div class="kpi"><b>Compute</b>' + esc(st.compute) + "</div>" +
        "</div>";
    }).join("");

    var barRows = G.stages.map(function (st) {
      var bars = (G.bars[st.n] || []);
      return '<div style="margin-bottom:14px"><div class="sn" style="font-family:var(--d);' +
        'font-size:10.5px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);' +
        'font-weight:600;margin-bottom:6px">' +
        (st.n === 0 ? "Today" : "Stage " + st.n) + " · " + esc(st.name) +
        " · " + bars.length + " job trigger" + (bars.length === 1 ? "" : "s") + "</div>" +
        bars.map(function (b) {
          return '<div class="bar p' + b.pipe + '">' +
            '<span class="k">' + esc(b.n) + " " + esc(b.kind) +
            (b.tag ? ' <span class="pill warn">' + esc(b.tag) + "</span>" : "") + "</span>" +
            "<span>" + esc(b.note) + "</span>" +
            '<span><span class="hop">' + esc(b.hop) + '</span> <span class="iud">' +
            ["I", "U", "D"].map(function (c) {
              return '<span class="' + b.iud[c] + '">' + c +
                (b.iud[c] === "yes" ? " ✓" : b.iud[c] === "partial" ? " !" : " ✗") +
                "</span>";
            }).join("") + "</span></span></div>";
        }).join("") + "</div>";
    }).join("");

    var untracked = Object.keys(G.gates).filter(function (k) { return !gs[k].tracked; });

    return '<section class="sect"><h2>' + esc(G.title) + "</h2>" +
      '<p class="hint">' + esc(G.lede) + "</p>" +
      '<div class="gap"><b>Figures.</b> ' + esc(G.unreadable) + " " + esc(G.caveat) + "</div>" +
      (untracked.length ? '<div class="gap" style="border-left-color:var(--crit);' +
        'background:var(--crit-soft)"><b>' +
        untracked.map(function (k) { return esc(G.gates[k].label); }).join(" and ") +
        (untracked.length === 1 ? " has" : " have") + " no Jira ticket.</b> " +
        'Stage 2 is gated on Gold batching and Silver scaling. Gold batching is already met, ' +
        'so the only thing holding stage 2 is a spike that nothing in Jira tracks.</div>' : "") +
      '<div class="stagerow">' + stageCards + "</div>" +
      "<p class='hint' style='margin-top:10px'>" + esc(G.independence) + " " +
      esc(G.companion) + "</p></section>" +

      '<section class="sect"><h2>Gates, against Jira</h2>' +
      '<p class="hint">Each gate inherits the work items of the Data Journey fixes it depends ' +
      'on, so whether a stage is unlocked is a query rather than a judgement call.</p>' +
      '<div class="card tscroll"><table><thead><tr><th>Gate</th><th>What it unlocks</th>' +
      '<th>Depends on</th><th class="r">Done</th><th>Live spread</th><th>Tickets</th>' +
      "</tr></thead><tbody>" + Object.keys(G.gates).map(function (k) {
        var g = G.gates[k], st = gs[k];
        var items = st.tickets.filter(function (t) { return t.sc; }).map(function (t) {
          return { sc: t.sc };
        });
        return "<tr><td><b>" + esc(g.label) + "</b><div style='color:var(--muted);" +
          "font-size:12px'>" + esc(g.name) + "</div></td>" +
          "<td class='ttl'>" + esc(g.unlocks) + "</td>" +
          "<td>" + (g.fixes.length
            ? g.fixes.map(function (n) { return "fix " + n; }).join(", ")
            : "<span class='pill crit'>nothing in Jira</span>") + "</td>" +
          "<td class='r num'>" + (st.tracked ? st.done + " / " + st.total : "—") + "</td>" +
          "<td>" + (items.length ? statusBar(items)
            : "<span class='pill crit'>untracked</span>") + "</td>" +
          '<td><div class="tix">' + st.tickets.map(function (t) {
            return ticketChip(t.k);
          }).join("") + "</div></td></tr>";
      }).join("") + "</tbody></table></div>" + SBAR_LEGEND + "</section>" +

      '<section class="sect"><h2>What runs at each stage</h2>' +
      '<p class="hint">Every independent job trigger the plan draws, with the change classes ' +
      'it applies. Blue is Pipeline A (per-district tables, no shared writes); gold is ' +
      'Pipeline B (one Redshift cluster, 350 shared tables). Grouping of bars onto stages ' +
      'follows their order in the drawing.</p>' + barRows + "</section>" +

      '<section class="sect"><h2>Still deciding</h2>' +
      '<p class="hint">Six questions the plan lists as open. None is a ticket; each changes ' +
      'what the tickets should say.</p><div class="grid g2">' +
      G.deciding.map(function (d) {
        return '<div class="card kv"><span class="k">Open question</span>' +
          '<span style="font-family:var(--d);font-weight:600;font-size:14px">' +
          esc(d.head) + "</span><span class='n'>" + esc(d.body) + "</span></div>";
      }).join("") + "</div></section>" +

      '<section class="sect"><h2>The layers the bars run between</h2>' +
      '<div class="lyrstrip">' + G.layers.map(function (l) {
        return "<div><span class='c'>" + esc(l.code) + " · " + esc(l.name) + "</span> " +
          layTag(l.layer) + "<div style='color:var(--muted);margin-top:3px'>" +
          esc(l.store) + "</div><div style='margin-top:3px'>" + esc(l.desc) + "</div></div>";
      }).join("") + "</div></section>";
  }

  /* ---- view: developer ---- */
  function vDev() {
    var P = pool("developer");
    var drift = J.recon.filter(function (r) { return r.state === "drifted"; }).length;
    var miss = J.recon.filter(function (r) { return r.state === "missing"; }).length;

    /* blast radius */
    var blast = [];
    ITEMS.forEach(function (i) {
      (i.td || []).forEach(function (t) {
        if (atStation(i, state.station) || !state.station) blast.push({ i: i, t: t });
      });
    });
    blast.sort(function (a, b) { return b.t.down - a.t.down; });
    var maxd = Math.max.apply(null, blast.map(function (b) { return b.t.down; }).concat([1]));

    /* layers */
    var lay = {};
    P.forEach(function (i) { i.ly.forEach(function (l) { lay[l] = (lay[l] || 0) + 1; }); });
    var layPairs = Object.keys(lay).sort(function (a, b) { return lay[b] - lay[a]; })
      .map(function (l) { return [LAYLABEL[l] || l, lay[l]]; });

    /* blocking */
    var blocking = ITEMS.filter(function (i) { return i.bl && i.bl.length; })
      .map(function (i) {
        return { i: i, open: i.bl.filter(function (k) { return BY[k] && BY[k].sc !== "Done"; }) };
      }).filter(function (x) { return x.open.length; })
      .sort(function (a, b) { return b.open.length - a.open.length; });

    return filterNote() +
      '<section class="sect"><h2>The map against Jira</h2>' +
      '<p class="hint">The Data Journey ' + esc(J.map.version) + ' cites ' + J.recon.length +
      ' tickets, with its Jira state dated ' + esc(J.map.jira_asof) + '. Today ' + drift +
      ' of them sit in a different status than the map draws, and ' + miss +
      ' is cited but does not exist in Jira. The drift is all forward — the work moved, the drawing did not.</p>' +
      '<div class="grid g3" style="margin-bottom:12px">' +
      tile("Claims checked", J.recon.length, "across 9 fixes") +
      tile("Still accurate", J.recon.filter(function (r) { return r.state === "agrees"; }).length, "map matches Jira") +
      tile("Gone stale", drift, "status moved since the map") +
      tile("Broken reference", miss, "MIGDL-230 — no such issue") +
      "</div>" + reconTable("drifted") + "</section>" +

      '<section class="sect"><h2>Blast radius</h2>' +
      '<p class="hint">Work items whose summary names a real table, with the number of tables ' +
      'downstream of it in the lineage graph. A defect in a table with 40 descendants is not the ' +
      'same size of problem as one with none, and Jira cannot tell you which it is.</p>' +
      '<div class="card tscroll"><table><thead><tr><th>Item</th><th>Table</th><th>Layer</th>' +
      '<th class="r">Downstream</th><th>Status</th><th>Concern</th></tr></thead><tbody>' +
      (blast.length ? blast.map(function (b) {
        return "<tr><td>" + jira(b.i.k) + "</td><td class='mono'>" + esc(b.t.t) + "</td>" +
          "<td>" + (b.t.layer ? layTag(b.t.layer) : "") + "</td>" +
          '<td class="r"><span class="blast"><i class="bar" style="width:' +
          Math.max(2, (b.t.down / maxd) * 64) + 'px"></i>' +
          (b.t.down ? '<span class="num">' + b.t.down + "</span>" : '<span class="z">none</span>') +
          "</span></td>" +
          "<td>" + catPill(b.i.sc) + "</td>" +
          "<td class='ttl'>" + esc(b.i.s.replace(/^MiGDL-[A-Za-z0-9-]+: /, "")) + "</td></tr>";
      }).join("") : "<tr><td colspan='6'>No table-linked work at this station.</td></tr>") +
      "</tbody></table></div>" +
      "<p class='hint' style='margin-top:8px'>Open the column-level picture in the " +
      '<a href="' + C.lineage + '" target="_blank" rel="noopener">Pipeline Lineage</a> viewer or the ' +
      '<a href="' + C.atlas + '" target="_blank" rel="noopener">Atlas</a>.</p></section>' +

      '<section class="sect"><h2>Open work blocking other work</h2>' +
      '<p class="hint">' + blocking.length + ' items block at least one unfinished item. ' +
      'The map notes its own ordering: ' + esc(J.map.sequence) + '.</p>' +
      '<div class="card tscroll"><table><thead><tr><th>Blocker</th><th>Status</th>' +
      '<th class="r">Blocks</th><th>Waiting on it</th></tr></thead><tbody>' +
      blocking.slice(0, 14).map(function (x) {
        return "<tr><td>" + jira(x.i.k) + "<div class='ttl' style='color:var(--muted);font-size:12px'>" +
          esc(x.i.s.replace(/^MiGDL-[A-Za-z0-9-]+: /, "").slice(0, 70)) + "</div></td>" +
          "<td>" + catPill(x.i.sc) + "</td><td class='r num'>" + x.open.length + "</td>" +
          "<td>" + x.open.map(jira).join(" ") + "</td></tr>";
      }).join("") + "</tbody></table></div></section>" +

      '<section class="sect"><h2>Structural callouts</h2>' +
      '<p class="hint">Three constraints the map marks at the arrows between stations, as ' +
      'distinct from the pain points at the stations themselves. Each is a property of the ' +
      'architecture, not of any one record.</p><div class="grid g2">' +
      J.callouts.filter(function (c) {
        return !state.station || c.station === state.station;
      }).map(function (c) {
        return '<div class="card kv"><span class="k">Callout ' + c.id + " \u00b7 " +
          esc((J.stations.filter(function (x) { return x.slug === c.station; })[0] || {}).name || "") +
          '</span><span style="font-family:var(--d);font-weight:600;font-size:15px">' +
          esc(c.head) + "</span><span class='n'>" + esc(c.body) + "</span>" +
          "<span class='n' style='margin-top:4px'><b>Fix:</b> " + esc(c.fix) + "</span></div>";
      }).join("") + "</div></section>" +

      '<section class="sect"><h2>The jobs that move it</h2>' +
      '<p class="hint">Named jobs from the map\u2019s Engineering layer. These are the handles ' +
      'in <code>amorphic-cicd</code> that the SQL review and lineage documents analyse.</p>' +
      '<div class="card tscroll"><table><thead><tr><th>Job</th><th>Runs on</th><th>Station</th>' +
      '<th>What it does</th></tr></thead><tbody>' +
      J.jobs.filter(function (j) {
        return !state.station || j.station === state.station || !j.station;
      }).map(function (j) {
        var st = J.stations.filter(function (x) { return x.slug === j.station; })[0];
        return "<tr><td class='mono'>" + esc(j.name) + "</td><td>" + esc(j.tech) + "</td>" +
          "<td>" + (st ? esc(st.n + ". " + st.name.replace(/^MiGDL /, "")) +
            " " + (st.layers[0] ? layTag(st.layers[0]) : "") : "<span class='pill'>all</span>") +
          "</td><td class='ttl'>" + esc(j.does) + "</td></tr>";
      }).join("") + "</tbody></table></div></section>" +

      '<section class="sect"><h2>Where this work lands</h2>' +
      '<p class="hint">Developer-relevant items by medallion layer. A layer is asserted from the ' +
      'load stage where the field gives one, and from the summary otherwise.</p>' +
      barList(layPairs, P.length) + "</section>";
  }

  /* ---- view: sprint planning ---- */
  function vSprint() {
    var P = pool("sprint-planning");
    var blocked = P.filter(function (i) {
      return ITEMS.some(function (o) {
        return o.bl && o.bl.indexOf(i.k) >= 0 && o.sc !== "Done";
      });
    });
    var ready = P.filter(function (i) { return blocked.indexOf(i) < 0; });
    var byWs = {};
    P.forEach(function (i) {
      (i.ws.length ? i.ws : ["(unassigned stream)"]).forEach(function (w) {
        (byWs[w] = byWs[w] || []).push(i);
      });
    });
    var byA = {};
    P.forEach(function (i) { var a = i.a || "— unassigned"; (byA[a] = byA[a] || []).push(i); });
    var aPairs = Object.keys(byA).sort(function (a, b) { return byA[b].length - byA[a].length; })
      .map(function (a) { return [a, byA[a].length]; });

    /* fix queue: the cited tickets, live */
    var fixRows = J.fixes.map(function (f) {
      var keys = Object.keys(f.claim);
      var live = keys.map(function (k) { return BY[k]; }).filter(Boolean);
      var done = live.filter(function (i) { return i.sc === "Done"; }).length;
      return { f: f, keys: keys, live: live, done: done };
    });

    return filterNote() +
      '<div class="gap"><b>Jira holds no sprint data for this project.</b> The Sprint field is ' +
      'empty on all ' + W.coverage.issues + ' items, and the [MiGDL-OPS] sprint fields are set on ' +
      'fewer than five. Story points are set on ' +
      ITEMS.filter(function (i) { return i.sp; }).length + '. So this view cannot show velocity or ' +
      'commitment — it shows what is plannable right now: ready against blocked, and who is ' +
      'already carrying work. Populate Sprint and the same ontology gives you burndown with no ' +
      'change here.</div>' +

      '<section class="sect"><div class="grid g3">' +
      tile("Plannable", P.length, "not done, deliverable grain") +
      tile("Ready", ready.length, "nothing unfinished blocks it") +
      tile("Blocked", blocked.length, "waiting on another item") +
      tile("Unassigned", (byA["— unassigned"] || []).length, "no assignee") +
      "</div></section>" +

      '<section class="sect"><h2>The nine fixes, as Jira holds them now</h2>' +
      '<p class="hint">Each fix on the Data Journey, with the tickets the map cites and their live ' +
      'status. Two fixes have no ticket at all, so nothing in Jira will move them.</p>' +
      '<div class="card tscroll"><table><thead><tr><th>Fix</th><th>What it does</th>' +
      '<th>Map chip</th><th class="r">Tickets</th><th class="r">Done</th><th>Live spread</th>' +
      "</tr></thead><tbody>" + fixRows.map(function (r) {
        var chipCls = /Not yet/.test(r.f.chip) ? "crit" : /Complete|Partly/.test(r.f.chip) ? "ok" : "acc";
        return "<tr><td class='r mono'>" + r.f.n + "</td>" +
          "<td class='ttl'><b>" + esc(r.f.head) + "</b>" +
          (r.f.epic ? "<div style='color:var(--muted);font-size:12px'>" + esc(r.f.epic) + "</div>" : "") +
          "</td><td><span class='pill " + chipCls + "'>" + esc(r.f.chip) + "</span></td>" +
          "<td class='r num'>" + (r.keys.length || "—") + "</td>" +
          "<td class='r num'>" + (r.keys.length ? r.done : "—") + "</td>" +
          "<td>" + (r.live.length ? statusBar(r.live) : "<span class='pill crit'>no Jira ticket</span>") +
          "</td></tr>";
      }).join("") + "</tbody></table></div>" + SBAR_LEGEND + "</section>" +

      '<section class="sect"><h2>Plannable work by workstream</h2>' +
      '<div class="card">' + Object.keys(byWs).sort(function (a, b) {
        return byWs[b].length - byWs[a].length;
      }).map(function (w) {
        var items = byWs[w];
        var b = items.filter(function (i) { return blocked.indexOf(i) >= 0; }).length;
        return '<div class="bar-row"><span class="lbl">' + esc(w) + "</span>" +
          "<span>" + statusBar(items) + "</span>" +
          '<span class="num">' + items.length + (b ? " <span class='pill warn'>" + b + " blocked</span>" : "") +
          "</span></div>";
      }).join("") + "</div>" + SBAR_LEGEND + "</section>" +

      gapSection() +

      '<section class="sect"><h2>Who is carrying it</h2>' +
      '<p class="hint">Count of plannable items per person. Not a capacity model — there are no ' +
      'estimates on most of these items.</p>' + barList(aPairs, P.length, 14) + "</section>";
  }


  /* ---- the Jira gap register, rendered in Sprint planning ---- */
  var PRIOLBL = { 1: "Do first", 2: "Next", 3: "Later" };

  function gapSection() {
    var G = window.GAPS, kinds = G.kinds;
    var order = ["process", "data", "setting", "schema", "hygiene", "keep-out"];
    var actionable = G.gaps.filter(function (g) { return g.kind !== "keep-out"; });
    var closed = actionable.filter(function (g) { return g.closed; }).length;

    function row(g) {
      var pctTxt = g.pct == null ? "" : g.pct + "%";
      var cls = g.pct == null ? "" : g.pct >= 100 ? "full" : g.pct === 0 ? "none" : "";
      return '<div class="gapitem' + (g.closed ? " done" : "") + '">' +
        "<div><span class='pill " + (g.priority === 1 ? "crit" : g.priority === 2 ? "warn" : "") +
        "'>" + PRIOLBL[g.priority] + "</span>" +
        (g.closed ? " <span class='pill ok'>done</span>" : "") + "</div>" +
        '<div><span class="t">' + esc(g.title) + "</span>" +
        (g.unlocks ? '<div class="u"><b>Unlocks.</b> ' + esc(g.unlocks) + "</div>" : "") +
        '<div class="h"><b>Do.</b> ' + esc(g.how) + "</div></div>" +
        "<div>" + (g.pct == null ? "<span class='gapsub'>no measure — judgement call</span>"
          : '<span class="gapnum">' + g.have + " / " + g.need + " " + pctTxt + "</span>" +
            '<div class="meter"><i class="' + cls + '" style="width:' +
            Math.max(g.pct, 1) + '%"></i></div>' +
            '<div class="gapsub">' + esc(g.unit) + "</div>") +
        "</div></div>";
    }

    return '<section class="sect"><h2>To run this from Jira alone</h2>' +
      '<p class="hint">This page is built from three sources: Jira, the ingestion tracker ' +
      'spreadsheet, and two hand transcriptions of the Lucid map and the Game Plan. Below is ' +
      'what Jira would have to hold for it to be the only one. Each row is measured against ' +
      'live data, so the list closes itself as fields get populated — ' + closed +
      ' of ' + actionable.length + ' are done today.</p>' +
      order.map(function (k) {
        var rows = G.gaps.filter(function (g) { return g.kind === k; });
        if (!rows.length) return "";
        rows.sort(function (a, b) { return a.priority - b.priority; });
        return "<h3 style='font-size:13.5px;margin:16px 0 6px'>" + esc(kinds[k]) +
          " <span class='gapsub' style='font-weight:400'>" + rows.length + "</span></h3>" +
          (k === "keep-out" ? "<p class='hint' style='margin-bottom:8px'>Not everything " +
            "belongs in Jira. These are better left where they are.</p>" : "") +
          '<div class="card">' + rows.map(row).join("") + "</div>";
      }).join("") + "</section>";
  }

  /* ---- view: leadership ---- */
  function vLead() {
    // count districts from the tracker, which is the system of record for load state
    var tk = Object.keys(DIST).map(function (k) { return DIST[k]; })
      .filter(function (d) { return d.src === "tracker"; });
    var live = tk.filter(function (d) { return d.stage === "complete"; }).length;
    var nd = tk.length;
    var drift = J.recon.filter(function (r) { return r.state === "drifted"; }).length;
    var risk = ITEMS.filter(function (i) { return i.p === "Highest" && i.sc !== "Done"; });
    var noJira = J.fixes.filter(function (f) { return !Object.keys(f.claim).length; });

    /* pain point progress, live */
    var painRows = J.pains.filter(function (p) { return !p.none; }).map(function (p) {
      var f = J.fixes.filter(function (x) { return x.pain === p.n; })[0];
      var keys = f ? Object.keys(f.claim) : [];
      var liveI = keys.map(function (k) { return BY[k]; }).filter(Boolean);
      var done = liveI.filter(function (i) { return i.sc === "Done"; }).length;
      return { p: p, f: f, live: liveI, done: done, keys: keys };
    });

    /* epic rollup */
    var kids = {};
    ITEMS.forEach(function (i) { if (i.par) (kids[i.par] = kids[i.par] || []).push(i); });
    var epics = Object.keys(kids).map(function (k) {
      return { t: BY[k], ch: kids[k] };
    }).filter(function (e) {
      return e.t && (e.t.c === "Epic" || e.t.c === "Initiative") && e.ch.length >= 4 &&
        (!state.station || e.ch.some(function (c) { return atStation(c, state.station); }));
    }).sort(function (a, b) { return b.ch.length - a.ch.length; });

    return filterNote() +
      '<section class="sect"><div class="grid g3">' +
      tile("Districts loaded", live + " / " + nd, "per the ingestion tracker") +
      tile("Pain points open", painRows.filter(function (r) { return r.done < r.keys.length || !r.keys.length; }).length + " / " + painRows.length, "from the Data Journey") +
      tile("Map gone stale", drift + " / " + J.recon.length, "cited tickets that moved") +
      tile("Highest priority open", risk.length, "not done") +
      tile("Worst-case data age", Math.max.apply(null, J.pipelines.map(function (p) {
        return p.age_all; })) + " days", "set by the binding pipeline") +
      "</div></section>" +
      freshBlock(false) +

      '<section class="sect"><h2>The nine pain points, and whether the fix is moving</h2>' +
      '<p class="hint">Each pain point the map identifies, with the live state of the tickets its ' +
      'fix depends on. A grey bar means the map names no Jira ticket for that fix, so no amount of ' +
      'sprint activity will close it.</p>' +
      '<div class="card tscroll"><table><thead><tr><th class="r">#</th><th>Pain point</th>' +
      '<th>Station</th><th>Gap</th><th class="r">Tickets done</th><th>Progress</th>' +
      "</tr></thead><tbody>" + painRows.map(function (r) {
        var stn = J.stations.filter(function (s) { return s.slug === r.p.station; })[0];
        return "<tr><td class='r mono'>" + (r.p.map_n || "\u2014") + "</td>" +
          "<td class='ttl'><b>" + esc(r.p.head) + "</b>" +
          (r.p.asks ? "<div style='color:var(--muted);font-size:12px'>“" + esc(r.p.asks) + "”</div>" : "") +
          "</td><td>" + (stn ? esc(stn.n + ". " + stn.name.replace(/^MiGDL /, "")) :
            "<span class='pill warn'>whole route</span>") + "</td>" +
          "<td class='mono'>" + esc(r.p.gap || "—") + "</td>" +
          "<td class='r num'>" + (r.keys.length ? r.done + " / " + r.keys.length : "—") + "</td>" +
          "<td>" + (r.live.length ? statusBar(r.live) :
            "<span class='pill crit'>no ticket</span>") + "</td></tr>";
      }).join("") + "</tbody></table></div>" + SBAR_LEGEND + "</section>" +

      '<section class="sect"><h2>Fixes with no engineering owner in Jira</h2>' +
      '<p class="hint">The map draws these with a grey border. They are real commitments with ' +
      'nothing behind them in the tracker.</p><div class="grid g2">' +
      noJira.map(function (f) {
        return '<div class="card kv"><span class="k">Fix ' + f.n + " · " + esc(f.chip) +
          '</span><span style="font-family:var(--d);font-weight:600;font-size:15px">' +
          esc(f.head) + "</span><span class='n'>" + esc(f.body) + "</span>" +
          "<span class='n'>" + esc(f.epic || "") +
          (f.owners.length ? " · " + esc(f.owners.join(", ")) : "") + "</span></div>";
      }).join("") + "</div></section>" +

      '<section class="sect"><h2>Epic progress</h2>' +
      '<p class="hint">Epics and initiatives with four or more children, by size.</p>' +
      '<div class="card tscroll"><table><thead><tr><th>Epic</th><th class="r">Children</th>' +
      '<th class="r">Done</th><th>Progress</th></tr></thead><tbody>' +
      epics.slice(0, 16).map(function (e) {
        var done = e.ch.filter(function (c) { return c.sc === "Done"; }).length;
        return "<tr><td class='ttl'>" + jira(e.t.k) + " " +
          esc(e.t.s.replace(/^MiGDL-[A-Za-z0-9-]+: /, "")) + "</td>" +
          "<td class='r num'>" + e.ch.length + "</td><td class='r num'>" + done + "</td>" +
          "<td>" + statusBar(e.ch) + " <span class='num' style='font-size:12px;color:var(--muted)'>" +
          pct(done, e.ch.length) + "%</span></td></tr>";
      }).join("") + "</tbody></table></div>" + SBAR_LEGEND + "</section>" +

      '<section class="sect"><h2>Decisions waiting on MAISA</h2>' +
      '<p class="hint">Raised by the map. Neither is an engineering task; both block engineering.</p>' +
      '<div class="grid g2">' + J.decisions.map(function (d) {
        return '<div class="card kv"><span class="k">Open decision · ' + esc(d.owner) +
          '</span><span style="font-family:var(--d);font-weight:600;font-size:15px">' +
          esc(d.head) + "</span><span class='n'>" + esc(d.body) + "</span></div>";
      }).join("") + "</div></section>";
  }

  /* ---- view: K-12 stakeholder ---- */
  function vStake() {
    var ds = Object.keys(DIST).map(function (k) { return DIST[k]; })
      .sort(function (a, b) { return (a.name || "").localeCompare(b.name || ""); });
    var TK = W.tracker || {};
    var fromTracker = ds.filter(function (d) { return d.src === "tracker"; });
    var live = fromTracker.filter(function (d) { return d.stage === "complete"; }).length;
    var jiraOnly = ds.filter(function (d) { return d.src === "jira-only"; });
    var byName = ds.filter(function (d) { return d.matched_by === "name"; }).length;
    var withTicket = ds.filter(function (d) { return d.items && d.items.length; }).length;
    var SHOWN = ["bronze-load", "descriptor-load", "silver-load", "goldplat-load"];
    var APPNAME = { miread: "MiRead", miewims: "MiEWIMS", misafestudent: "MiSAFEStudent",
      "community-schools-manager": "Community Schools Manager",
      mistrategybank: "MiStrategyBank" };
    var prodCount = {};
    ds.forEach(function (d) {
      (d.products || []).forEach(function (p) { prodCount[p] = (prodCount[p] || 0) + 1; });
    });
    var worst = Math.max.apply(null, J.pipelines.map(function (p) { return p.age_all; }));
    var sched = fromTracker.filter(function (d) { return d.scheduled; }).length;

    return '<section class="sect"><div class="grid g3">' +
      tile("Districts loaded", live, "of " + fromTracker.length + " in the tracker") +
      tile("Worst-case data age", worst + " days", "what a teacher may be looking at") +
      tile("On the nightly schedule", sched, "of " + fromTracker.length) +
      tile("With an onboarding ticket", withTicket, "Jira covers a subset") +
      "</div></section>" +

      '<div class="gap"><b>Where these numbers come from.</b> District state is read from ' +
      'the <i>' + esc(TK.spreadsheet || "ingestion tracker") + '</i> (' + esc(TK.tab || "") +
      '), fetched ' + esc(TK.fetched || "") + ' — not from Jira. Jira’s onboarding ' +
      'issue types track onboarding <i>work</i>, which covers ' + withTicket + ' of these ' +
      'districts, so counting districts from Jira alone understates it. ' +
      (byName ? byName + ' of those joined to the tracker only by a normalised name, ' +
        'because the Jira ticket carries no SD code — which is the map’s own pain ' +
        'point 9 in miniature.' : "") + "</div>" +

      freshBlock(true) +

      (jiraOnly.length ? '<section class="sect"><h2>In Jira, not in the tracker</h2>' +
        '<p class="hint">' + jiraOnly.length + ' onboarding tickets name a district that has ' +
        'no row in the ingestion tracker and could not be matched by name either. Each is ' +
        'either not yet loaded, or loaded but missing from the tracker.</p>' +
        '<div class="card tscroll"><table><thead><tr><th>District</th><th>Onboarding ticket</th>' +
        '<th class="r">Stages evidenced in Jira</th></tr></thead><tbody>' +
        jiraOnly.map(function (d) {
          return "<tr><td class='ttl'>" + esc(d.name) + "</td><td>" +
            (d.items || []).map(jira).join(" ") + "</td>" +
            "<td class='r num'>" + Object.keys(d.stages || {}).length + "</td></tr>";
        }).join("") + "</tbody></table></div></section>" : "") +

      '<section class="sect"><h2>The apps that receive this data</h2>' +
      '<p class="hint">Per-district registration, as the tracker records it. Every app has a ' +
      'flag here — including the three with no [MiGDL] App Registration option in Jira, ' +
      'so work on them cannot be attributed to the district that asked for it even though ' +
      'the district is registered.</p>' +
      '<div class="card tscroll"><table><thead><tr><th>Application</th>' +
      '<th class="r">Districts registered</th><th>Receives data by</th>' +
      '<th>Attributable in Jira</th></tr></thead><tbody>' +
      J.map.apps.map(function (a) {
        var slug = a.name.toLowerCase().replace(/[^a-z0-9]+/g, "-");
        var alt = a.name.toLowerCase().replace(/[^a-z0-9]+/g, "");
        var n = prodCount[slug] || prodCount[alt] || 0;
        return "<tr><td class='ttl'>" + esc(a.name) + "</td>" +
          "<td class='r num'>" + n + "</td><td>" + esc(a.via) + "</td>" +
          "<td>" + (a.jira ? "<span class='pill ok'>yes</span>"
                           : "<span class='pill warn'>no registration field</span>") +
          "</td></tr>";
      }).join("") + "</tbody></table></div></section>" +

      '<section class="sect"><h2>What the apps show today</h2>' +
      '<p class="hint">The Data Journey traces four kinds of change from a district’s ' +
      'student information system through to the apps. These are properties of the pipeline, ' +
      'not of any one district.</p><div class="grid g2">' +
      (((J.station_detail || {}).delivery || {}).app_shows || []).map(function (a) {
        var kind = (J.change_kinds || []).filter(function (k) { return k[0] === a[0]; })[0];
        var good = a[0] === "I";
        return '<div class="card kv"><span class="k">' + esc(kind ? kind[2] : a[0]) + "</span>" +
          '<span style="font-family:var(--d);font-weight:600;font-size:15px">' + esc(a[1]) +
          "</span><span class='n'><span class='pill " + (good ? "ok" : "crit") + "'>" +
          (good ? "Working" : "Known problem, fix in progress") + "</span></span></div>";
      }).join("") + "</div>" +
      "<p class='hint' style='margin-top:10px'>Every known problem above has an identified " +
      "fix. The Leadership view shows which of those fixes are actually moving.</p></section>" +

      '<section class="sect"><h2>District by district</h2>' +
      '<p class="hint">Every district in the tracker. The dots are the four load steps in ' +
      'order: raw copy, codes, district cabinet, statewide model. A filled dot means the ' +
      'tracker has a completion date for that step.</p>' +
      '<div class="card tscroll"><table><thead><tr><th>District</th><th>Code</th><th>ISD</th>' +
      '<th>SIS</th><th>Progress</th><th>Where it is</th><th>Apps</th><th>Batch</th>' +
      '<th>Last entry</th></tr></thead><tbody>' + ds.map(function (d) {
        var dots = SHOWN.map(function (s) {
          return '<span class="dot' + ((d.stages || {})[s] ? " on" : "") + '" title="' +
            esc(STAGE_LABEL[s] || s) +
            ((d.stages || {})[s] ? ": " + d.stages[s] : ": not recorded") + '"></span>';
        }).join("");
        var cls = d.stage === "complete" ? "ok" : d.stage ? "acc" : "warn";
        var where = d.stage ? (STAGE_LABEL[d.stage] || d.stage)
          : (d.src === "jira-only" ? "not in tracker" : "unknown");
        return "<tr><td class='ttl'>" + esc(d.name) +
          (d.matched_by === "name" ? " <span class='pill warn' title='Joined to its Jira " +
            "ticket by name, not SD code'>name match</span>" : "") + "</td>" +
          "<td class='mono'>" + esc(d.sd || "—") + "</td>" +
          "<td>" + esc(d.isd || "—") + "</td>" +
          "<td>" + esc(d.sis || "—") + "</td>" +
          '<td><span class="dots">' + dots + "</span></td>" +
          "<td><span class='pill " + cls + "'>" + esc(where) + "</span>" +
          (d.next_step ? "<div style='color:var(--muted);font-size:11.5px;margin-top:2px'>" +
            esc(d.next_step) + "</div>" : "") + "</td>" +
          "<td>" + ((d.products || []).map(function (p) {
            return "<span class='pill'>" + esc(APPNAME[p] || p) + "</span>";
          }).join(" ") || "<span style='color:var(--muted)'>—</span>") + "</td>" +
          "<td class='mono'>" + esc(d.batch || "—") +
          (d.scheduled ? "" : " <span class='pill warn'>off</span>") + "</td>" +
          "<td class='mono'>" + esc(d.last_entry || "—") + "</td></tr>";
      }).join("") + "</tbody></table></div>" +
      "<p class='hint' style='margin-top:8px'>Source: " +
      '<a href="' + esc(TK.source || "#") + '" target="_blank" rel="noopener">' +
      esc(TK.spreadsheet || "ingestion tracker") + "</a>, tab " + esc(TK.tab || "") +
      ", as at " + esc(TK.fetched || "") + ".</p></section>";
  }

  /* ---- chrome ---- */
  function tabs() {
    var t = document.getElementById("tabs");
    t.innerHTML = AUD.map(function (a) {
      var n = a.key
        ? ITEMS.filter(function (i) { return i.au.indexOf(a.key) >= 0; }).length + " items"
        : a.id === "plan" ? window.GAMEPLAN.stages.length + " stages"
        : J.stations.length + " stations";
      return '<button class="tab" type="button" role="tab" data-a="' + a.id +
        '" aria-selected="' + (state.aud === a.id) + '">' + a.label +
        "<small>" + a.sub + " · " + n + "</small></button>";
    }).join("");
    t.querySelectorAll(".tab").forEach(function (b) {
      b.addEventListener("click", function () {
        state.aud = b.dataset.a;
        try { location.hash = b.dataset.a; } catch (e) {}
        tabs(); render();
      });
    });
  }

  function render() {
    var v = document.getElementById("view");
    v.innerHTML = state.aud === "map" ? vMap()
      : state.aud === "dev" ? vDev()
      : state.aud === "sprint" ? vSprint()
      : state.aud === "lead" ? vLead()
      : state.aud === "plan" ? vPlan() : vStake();
    v.scrollTop = 0;
  }

  /* theme toggle */
  var tb = document.getElementById("theme");
  if (tb) tb.addEventListener("click", function () {
    var r = document.documentElement;
    var cur = r.getAttribute("data-theme");
    var dark = cur ? cur === "dark"
      : window.matchMedia("(prefers-color-scheme: dark)").matches;
    r.setAttribute("data-theme", dark ? "light" : "dark");
  });

  var h = (location.hash || "").replace("#", "");
  if (AUD.some(function (a) { return a.id === h; })) state.aud = h;
  tabs(); rail(); render();
})();
