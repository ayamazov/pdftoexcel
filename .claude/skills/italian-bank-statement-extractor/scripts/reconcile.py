#!/usr/bin/env python3
"""Run all five reconciliation axes over one or more rows.json files.

    python reconcile.py rows-1994.json
    python reconcile.py rows-*.json --verbose

Prints FAIL lines and deltas only, unless --verbose. Exit code 1 if anything fails,
so it can gate the workbook build. Sign convention: saldi are positive = debito;
dare increases the saldo, avere decreases it.
"""
import argparse, glob, json, sys
from collections import OrderedDict

INT = "interessi e competenze"


def load(paths):
    sts = []
    for pat in paths:
        for f in sorted(glob.glob(pat)) or [pat]:
            d = json.load(open(f))
            for s in d["statements"]:
                s.setdefault("_src", f)
                s.setdefault("currency", d.get("currency", "ITL"))
                sts.append(s)
    return sorted(sts, key=lambda s: s["estratto_al"])


def r(x, cur):
    return round(x or 0, 2 if cur == "EUR" else 0)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("files", nargs="+")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--allow-gap", action="append", default=[],
                   help="estratto_al date where a chain break is expected (missing year)")
    a = p.parse_args()

    sts = load(a.files)
    fails = []

    def check(axis, ok, msg):
        if not ok:
            fails.append("AXIS %s  %s" % (axis, msg))
        elif a.verbose:
            print("ok   axis %s  %s" % (axis, msg))

    # ---- Axis 1: statement totals -------------------------------------
    for s in sts:
        cur = s["currency"]
        d = sum(x.get("dare") or 0 for x in s["rows"])
        c = sum(x.get("avere") or 0 for x in s["rows"])
        calc = r(s["saldo_iniziale"] + d - c, cur)
        printed = r(s["saldo_finale"], cur)
        check(1, calc == printed,
              "%s  calc %s vs printed %s  delta %s"
              % (s["estratto_al"], calc, printed, r(calc - printed, cur)))

    # ---- Axis 2: movements grouped by valuta vs SALDI PER VALUTA -------
    for s in sts:
        if not s.get("scalare"):
            if a.verbose:
                print("n/a  axis 2  %s (no scalare page)" % s["estratto_al"])
            continue
        cur = s["currency"]
        g = OrderedDict()
        for x in s["rows"]:
            g[x["val"]] = g.get(x["val"], 0) + (x.get("dare") or 0) - (x.get("avere") or 0)
        run = s["saldo_iniziale"]
        for line in s["scalare"]:
            run = r(run + g.get(line["valuta"], 0), cur)
            check(2, run == r(line["saldo"], cur),
                  "%s valuta %s  calc %s vs printed %s  delta %s"
                  % (s["estratto_al"], line["valuta"], run, r(line["saldo"], cur),
                     r(run - line["saldo"], cur)))

    # ---- Axis 3: statement chaining ------------------------------------
    for prev, nxt in zip(sts, sts[1:]):
        if nxt["estratto_al"] in a.allow_gap:
            print("gap  axis 3  chain break declared at %s" % nxt["estratto_al"])
            continue
        cur = nxt["currency"]
        check(3, r(prev["saldo_finale"], cur) == r(nxt["saldo_iniziale"], cur),
              "%s finale %s vs %s iniziale %s  delta %s"
              % (prev["estratto_al"], r(prev["saldo_finale"], cur), nxt["estratto_al"],
                 r(nxt["saldo_iniziale"], cur),
                 r(prev["saldo_finale"] - nxt["saldo_iniziale"], cur)))

    # ---- Axis 4: competenze cross-check --------------------------------
    for prev, nxt in zip(sts, sts[1:]):
        sb = prev.get("sbilancio_competenze")
        if sb is None:
            continue
        cur = nxt["currency"]
        debited = sum(x.get("dare") or 0 for x in nxt["rows"] if x["desc"] == INT)
        check(4, r(debited, cur) == r(sb, cur),
              "%s sbilancio %s vs %s debited %s  delta %s"
              % (prev["estratto_al"], r(sb, cur), nxt["estratto_al"], r(debited, cur),
                 r(debited - sb, cur)))

    # ---- Axis 5: data valuta running saldo vs SALDI PER VALUTA ---------
    for s in sts:
        if not s.get("scalare"):
            continue
        cur = s["currency"]
        order = {ln["valuta"]: i for i, ln in enumerate(s["scalare"])}
        rows = sorted(enumerate(s["rows"]),
                      key=lambda t: (order.get(t[1]["val"], 10 ** 6), t[0]))  # stable
        run = s["saldo_iniziale"]
        seen = {}
        for _, x in rows:
            run = r(run + (x.get("dare") or 0) - (x.get("avere") or 0), cur)
            seen[x["val"]] = run
        for ln in s["scalare"]:
            if ln["valuta"] in seen:
                check(5, seen[ln["valuta"]] == r(ln["saldo"], cur),
                      "%s valuta %s  data-valuta %s vs printed %s"
                      % (s["estratto_al"], ln["valuta"], seen[ln["valuta"]], r(ln["saldo"], cur)))

    print("\n%d statements  %d rows" % (sts.__len__(), sum(len(s["rows"]) for s in sts)))
    if fails:
        print("\n".join(fails))
        print("FAIL: %d check(s). See references/traps.md — the delta names the error." % len(fails))
        sys.exit(1)
    print("ALL AXES PASS")


if __name__ == "__main__":
    main()
