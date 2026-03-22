/**
 * G-Exam — ergonomie saisie des notes (par épreuve / par élève).
 */
(function () {
  function parseFloatSafe(v) {
    if (v === "" || v === null || v === undefined) return null;
    var n = parseFloat(String(v).replace(",", "."));
    return Number.isFinite(n) ? n : null;
  }

  function applyInputStyle(input) {
    var maxV = parseFloat(input.getAttribute("max")) || 20;
    var minV = parseFloat(input.getAttribute("min")) || 0;
    var thr = parseFloat(input.getAttribute("data-passing-threshold"));
    if (!Number.isFinite(thr)) thr = maxV * 0.5;
    var raw = input.value.trim();
    input.classList.remove("score-input-valid", "score-input-below", "score-input-warning");
    if (raw === "") return;
    var val = parseFloatSafe(raw);
    if (val === null) return;
    if (val < minV || val > maxV) {
      input.classList.add("score-input-warning");
      return;
    }
    if (val >= thr) input.classList.add("score-input-valid");
    else input.classList.add("score-input-below");
  }

  function stripAccents(s) {
    return String(s)
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

  function normKey(s) {
    return stripAccents(String(s || "").toLowerCase());
  }

  function syncGetFiltersToPostForm(root, postForm) {
    var getForm = root.querySelector('form[method="get"]');
    if (!getForm) return;
    var getQ = getForm.querySelector('input[name="q"]');
    var postQ = postForm.querySelector('input[name="q"]');
    if (getQ && postQ) postQ.value = getQ.value.trim();
    var getSchool = getForm.querySelector('select[name="school"]');
    var postSchool = postForm.querySelector('input[name="school"]');
    if (getSchool && postSchool) postSchool.value = getSchool.value;
    var getEmpty = getForm.querySelector('input[name="empty_only"]');
    var postEmpty = postForm.querySelector('input[name="empty_only"]');
    if (getEmpty && postEmpty) postEmpty.value = getEmpty.checked ? "1" : "";
  }

  function initLiveRowFilter(root, postForm) {
    var searchInput = root.querySelector("#scores-subject-search");
    var rows = Array.prototype.slice.call(postForm.querySelectorAll("tr.score-row"));
    var countEl = document.getElementById("scores-live-filter-count");
    if (!searchInput || !rows.length) return;

    var debounceTimer = null;

    function tokens(q) {
      return normKey(q)
        .split(/\s+/)
        .map(function (t) {
          return t.trim();
        })
        .filter(Boolean);
    }

    function rowHaystack(tr) {
      return normKey(
        [
          tr.getAttribute("data-candidate") || "",
          tr.getAttribute("data-last") || "",
          tr.getAttribute("data-first") || ""
        ].join(" ")
      );
    }

    function applyFilter() {
      var ts = tokens(searchInput.value);
      var visible = 0;
      rows.forEach(function (tr) {
        if (!ts.length) {
          tr.removeAttribute("hidden");
          tr.setAttribute("aria-hidden", "false");
          visible++;
          return;
        }
        var hay = rowHaystack(tr);
        var ok = ts.every(function (t) {
          return hay.indexOf(t) !== -1;
        });
        if (ok) {
          tr.removeAttribute("hidden");
          tr.setAttribute("aria-hidden", "false");
          visible++;
        } else {
          tr.setAttribute("hidden", "hidden");
          tr.setAttribute("aria-hidden", "true");
        }
      });
      if (countEl) {
        if (!ts.length) {
          countEl.textContent = "";
          countEl.classList.add("hidden");
        } else {
          countEl.classList.remove("hidden");
          countEl.textContent =
            visible + " élève(s) affiché(s) sur " + rows.length + " (cette page)";
        }
      }
    }

    searchInput.addEventListener("input", function () {
      if (debounceTimer) window.clearTimeout(debounceTimer);
      debounceTimer = window.setTimeout(applyFilter, 120);
    });
  }

  function initSubjectForm(root) {
    var form = root.querySelector("#scores-by-subject-form");
    if (!form) return;

    var inputs = Array.prototype.slice.call(form.querySelectorAll("input.score-input"));
    var dirty = false;
    var initial = inputs.map(function (inp) {
      return inp.value;
    });

    function markDirty() {
      dirty = inputs.some(function (inp, i) {
        return inp.value !== initial[i];
      });
      var el = document.getElementById("scores-dirty-indicator");
      if (el) el.classList.toggle("hidden", !dirty);
    }

    function updateCounts() {
      var filled = inputs.filter(function (inp) {
        return inp.value.trim() !== "";
      }).length;
      var total = inputs.length;
      var el = document.getElementById("scores-page-count");
      if (el) el.textContent = filled + " / " + total + " sur cette page";
    }

    inputs.forEach(function (input, idx) {
      input.addEventListener("input", function () {
        applyInputStyle(input);
        markDirty();
        updateCounts();
      });
      input.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
          e.preventDefault();
          var next = e.shiftKey ? inputs[idx - 1] : inputs[idx + 1];
          if (next) {
            next.focus();
            next.select();
          }
        }
      });
      applyInputStyle(input);
    });
    updateCounts();

    initLiveRowFilter(root, form);

    window.addEventListener("beforeunload", function (e) {
      if (!dirty) return;
      e.preventDefault();
      e.returnValue = "";
    });

    form.addEventListener("submit", function () {
      syncGetFiltersToPostForm(root, form);
      dirty = false;
    });

    var btnAbsent = document.getElementById("btn-fill-absent-zero");
    if (btnAbsent) {
      btnAbsent.addEventListener("click", function () {
        inputs.forEach(function (inp) {
          if (inp.getAttribute("data-absent") === "1" && inp.value.trim() === "") {
            inp.value = "0";
            inp.classList.add("score-input-flash");
            setTimeout(function () {
              inp.classList.remove("score-input-flash");
            }, 400);
            applyInputStyle(inp);
          }
        });
        markDirty();
        updateCounts();
      });
    }

    var btnClear = document.getElementById("btn-clear-page-scores");
    if (btnClear) {
      btnClear.addEventListener("click", function () {
        var runClear = function () {
          inputs.forEach(function (inp) {
            inp.value = "";
            inp.classList.remove("score-input-valid", "score-input-below", "score-input-warning");
          });
          markDirty();
          updateCounts();
        };
        if (typeof window.gexamConfirm === "function") {
          window.gexamConfirm("Effacer toutes les notes de cette page (champs non enregistrés) ?").then(function (ok) {
            if (ok) runClear();
          });
        } else if (window.confirm("Effacer toutes les notes de cette page ?")) {
          runClear();
        }
      });
    }
  }

  function studentAverageFromMeta(meta, getVal, targetScale) {
    var list = [];
    for (var i = 0; i < meta.length; i++) {
      var s = meta[i];
      var v = getVal(s.id);
      if (v === null || v === undefined) continue;
      list.push({
        value: v,
        coefficient: s.coefficient,
        max_score: s.max_score,
      });
    }
    if (!list.length) return null;
    var target =
      Number.isFinite(targetScale) && targetScale > 0 ? targetScale : 20.0;
    var hasCoef = list.some(function (x) {
      return x.coefficient != null && x.coefficient > 0;
    });
    var hasVarMax = list.some(function (x) {
      return x.max_score != null && x.max_score > 0;
    });
    if (hasVarMax) {
      if (hasCoef) {
        var tw = 0;
        var tc = 0;
        list.forEach(function (s) {
          var coef = s.coefficient != null && s.coefficient > 0 ? s.coefficient : 1.0;
          var maxS = s.max_score != null && s.max_score > 0 ? s.max_score : target;
          var norm = maxS > 0 ? (s.value / maxS) * target : 0;
          tw += norm * coef;
          tc += coef;
        });
        return tc > 0 ? Math.round((tw / tc) * 100) / 100 : null;
      }
      var ts = 0;
      var tm = 0;
      list.forEach(function (s) {
        var maxS = s.max_score != null && s.max_score > 0 ? s.max_score : target;
        ts += s.value;
        tm += maxS;
      });
      return tm > 0 ? Math.round((ts / tm) * target * 100) / 100 : null;
    }
    if (hasCoef) {
      var tw2 = 0;
      var tc2 = 0;
      list.forEach(function (s) {
        var coef = s.coefficient != null && s.coefficient > 0 ? s.coefficient : 1.0;
        tw2 += s.value * coef;
        tc2 += coef;
      });
      return tc2 > 0 ? Math.round((tw2 / tc2) * 100) / 100 : null;
    }
    var sum = list.reduce(function (a, b) {
      return a + b.value;
    }, 0);
    return Math.round((sum / list.length) * 100) / 100;
  }

  function mentionFromAvg(avg, passing, scaleMax) {
    if (avg == null || !Number.isFinite(avg)) return "—";
    var sm = Number.isFinite(scaleMax) && scaleMax > 0 ? scaleMax : 20;
    var r = sm / 20;
    if (avg < passing) return "Ajourné";
    if (avg < 12 * r) return "Passable";
    if (avg < 14 * r) return "Assez Bien";
    if (avg < 16 * r) return "Bien";
    if (avg < 18 * r) return "Très Bien";
    return "Excellent";
  }

  function initStudentForm(root) {
    var metaEl = document.getElementById("scores-student-meta");
    if (!metaEl) return;
    var meta;
    try {
      meta = JSON.parse(metaEl.textContent);
    } catch (e) {
      return;
    }
    var passing = parseFloat(metaEl.getAttribute("data-passing")) || 10;
    var scaleMax = parseFloat(metaEl.getAttribute("data-scale"));
    if (!Number.isFinite(scaleMax) || scaleMax <= 0) scaleMax = 20;
    var inputs = Array.prototype.slice.call(root.querySelectorAll("input.score-input-student"));
    var outAvg = document.getElementById("student-live-average");
    var outMen = document.getElementById("student-live-mention");

    function getVal(id) {
      var inp = root.querySelector('input[name="score_subj_' + id + '"]');
      if (!inp) return null;
      var v = parseFloatSafe(inp.value.trim());
      return v;
    }

    function refresh() {
      inputs.forEach(function (inp) {
        applyInputStyle(inp);
      });
      var avg = studentAverageFromMeta(meta, getVal, scaleMax);
      if (outAvg) outAvg.textContent = avg != null ? String(avg) + " / " + String(scaleMax) : "—";
      if (outMen) outMen.textContent = mentionFromAvg(avg, passing, scaleMax);
    }

    inputs.forEach(function (inp) {
      inp.addEventListener("input", refresh);
      inp.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
          e.preventDefault();
          var idx = inputs.indexOf(inp);
          var next = e.shiftKey ? inputs[idx - 1] : inputs[idx + 1];
          if (next) {
            next.focus();
            next.select();
          }
        }
      });
    });
    refresh();
  }

  document.addEventListener("DOMContentLoaded", function () {
    var root = document.getElementById("scores-entry-root");
    if (!root) return;
    if (root.getAttribute("data-mode") === "subject") initSubjectForm(root);
    if (root.getAttribute("data-mode") === "student") initStudentForm(root);
  });
})();
