"""A forward-chaining unary Knowledge Base with robust rule support.

Accepted inputs (via `add`):
- Ground unary facts: `P(Const)`
- Universal rules with conjunctive antecedent/consequent over a single variable:
    - `forall x. (P(x) -> Q(x))`
    - `forall x. (P(x) & Q(x) -> R(x))`
    - `forall x. (P(x) -> Q(x) & R(x))`
    - `forall x. (P(x) & Q(x) -> R(x) & S(x))`
- Existential facts (Skolemized into facts):
    - `exists x. P(x)` -> introduces a witness constant `w#` and asserts `P(w#)`
    - `exists x. (P(x) & Q(x) & ...)` -> asserts all conjuncts for the same witness

Graceful acceptance:
- Any well-formed formula parsed by the internal parser is accepted into the KB.
- Formulas outside the supported reasoning fragment are stored and reported during queries
    as "stored but not used for inference".

Accepted queries (via `query`):
- Unary fact: `P(Const)`
- Existential: `exists x. P(x)` or `exists x. (P(x) & Q(x) & ...)` (true if a witness constant exists)
- Universal rule membership check: `forall x. (Ante(x) -> Cons(x))` with conjunctive sides (true if such a rule is present)

Limitations:
- Only unary predicates are supported; no functions in facts/rules.
- No negation/equality reasoning inside the KB.
"""
from __future__ import annotations
import re
from typing import Set, Tuple, List, Dict, Optional, cast
import json
from pathlib import Path
from proof.parser import parse, tokenize
from proof.ast_nodes import Predicate, And, Implies, Universal, Existential


_RE_UNARY = re.compile(r"^([A-Z][A-Za-z0-9_]*)\(([A-Za-z0-9_]+)\)$")


class KnowledgeBase:
    def __init__(self) -> None:
        # persistent store path
        root = Path(__file__).resolve().parents[1]
        self._store_path = root / 'kb_store.json'

        # facts store strings like 'Human(socrates)'
        self.facts: Set[str] = set()
        # rules_adv store dicts: { 'ant': ['P','Q'], 'cons': ['R','S'] }
        self.rules_adv: List[Dict[str, List[str]]] = []
        # other_formulas store well-formed but unsupported formulas for graceful acceptance
        self.other_formulas: Set[str] = set()

        # attempt to load persisted KB
        self._load()

    def _load(self) -> None:
        try:
            if self._store_path.exists():
                data = json.loads(self._store_path.read_text(encoding='utf8'))
                self.facts = set(data.get('facts', []))
                # Migrate legacy 'rules' into rules_adv if present
                legacy = data.get('rules', [])
                adv = data.get('rules_adv', [])
                migrated: List[Dict[str, List[str]]] = []
                for r in legacy:
                    try:
                        p, q = r
                        migrated.append({'ant': [p], 'cons': [q]})
                    except Exception:
                        continue
                self.rules_adv = [
                    {'ant': list(item.get('ant', [])), 'cons': list(item.get('cons', []))}
                    for item in adv
                ] + migrated
                # Load any previously stored other formulas
                other = data.get('other_formulas', []) or data.get('other', [])
                self.other_formulas = set(other)
        except Exception:
            # ignore errors and start with empty KB
            self.facts = set()
            self.rules_adv = []
            self.other_formulas = set()

    def _save(self) -> None:
        try:
            data = {
                'facts': sorted(self.facts),
                'rules_adv': [{'ant': r['ant'], 'cons': r['cons']} for r in self.rules_adv],
                'other_formulas': sorted(self.other_formulas),
            }
            self._store_path.write_text(json.dumps(data, indent=2), encoding='utf8')
        except Exception:
            # best-effort persistence; ignore failures
            pass

    def add(self, fol: str) -> bool:
        """Add a formula to the KB. Returns True if recognized and added."""
        fol = fol.strip()
        # Try unary fact fast-path
        m2 = _RE_UNARY.match(fol)
        if m2:
            pred, const = m2.group(1), m2.group(2)
            self.facts.add(f"{pred}({const})")
            self._save()
            return True

        # Parse with AST for robust rule/existential handling
        node = parse(tokenize(fol))
        if node is None:
            # Gracefully accept unknown-but-possibly-valid formulas
            self.other_formulas.add(fol)
            self._save()
            return True

        # Existential -> introduce a witness const and assert conjuncts as facts
        if isinstance(node, Existential):
            var = node.var
            conj = node.formula
            # generate witness name
            w = self._next_witness()
            preds = self._collect_unary_preds(conj, var_only=var)
            if preds is None or not preds:
                # Unsupported existential shape; store gracefully
                self.other_formulas.add(fol)
                self._save()
                return True
            for p in preds:
                self.facts.add(f"{p}({w})")
            self._save()
            return True

        # Universal rules with implication and conjunctive sides
        if isinstance(node, Universal) and isinstance(node.formula, Implies):
            var = node.var
            imp = cast(Implies, node.formula)
            ant_preds = self._collect_unary_preds(imp.left, var_only=var)
            cons_preds = self._collect_unary_preds(imp.right, var_only=var)
            if ant_preds is None or cons_preds is None or not ant_preds or not cons_preds:
                # Unsupported rule shape; store gracefully
                self.other_formulas.add(fol)
                self._save()
                return True
            rule = {'ant': sorted(set(ant_preds)), 'cons': sorted(set(cons_preds))}
            if rule not in self.rules_adv:
                self.rules_adv.append(rule)
            self._save()
            return True

        # Any other well-formed formula: accept and store gracefully
        self.other_formulas.add(fol)
        self._save()
        return True

    def list_facts(self) -> List[str]:
        return sorted(self.facts)

    def list_rules(self) -> List[str]:
        out: List[str] = []
        for r in self.rules_adv:
            ant = ' & '.join(f"{p}(x)" for p in r['ant'])
            cons = ' & '.join(f"{p}(x)" for p in r['cons'])
            out.append(f"forall x. ({ant} -> {cons})")
        return out

    def list_other(self) -> List[str]:
        return sorted(self.other_formulas)

    def clear(self) -> None:
        self.facts.clear()
        self.rules_adv.clear()
        self._save()

    def query(self, fol: str, max_steps: int = 1000) -> Tuple[bool, List[str]]:
        """Return (entailed, trace). Supports:
        - unary fact `Q(Const)`
        - existential `exists x. ...`
        - universal rule membership `forall x. ( ... -> ... )`
        """
        fol = fol.strip()
        # Rule membership or disjunction queries
        node = parse(tokenize(fol))
        if isinstance(node, Universal) and isinstance(getattr(node, 'formula', None), Implies):
            var = node.var
            imp = cast(Implies, node.formula)
            ant_preds = self._collect_unary_preds(imp.left, var_only=var)
            cons_preds = self._collect_unary_preds(imp.right, var_only=var)
            if ant_preds and cons_preds:
                target = {'ant': sorted(set(ant_preds)), 'cons': sorted(set(cons_preds))}
                for r in self.rules_adv:
                    if r == target:
                        ant = ' & '.join(f"{p}(x)" for p in r['ant'])
                        cons = ' & '.join(f"{p}(x)" for p in r['cons'])
                        return True, [f"rule present: forall x. ({ant} -> {cons})"]
                return False, ["No matching rule in KB."]

        # Disjunction of unary facts: use resolution
        dj = self._collect_or_unary(node)
        if dj is not None:
            const, preds = dj
            ok, rtrace = self._resolution_entails_disjunction(preds, const, limit_steps=500)
            return (True, ["resolution proof:"] + rtrace) if ok else (False, rtrace or ["resolution could not derive goal."])

        # Existential query: true if there exists a constant satisfying conjunct(s)
        if isinstance(node, Existential):
            var = node.var
            preds = self._collect_unary_preds(node.formula, var_only=var)
            if not preds:
                # Graceful: if stored, acknowledge but unsupported for reasoning
                if fol in self.other_formulas:
                    return False, ["Formula stored but not supported for KB reasoning."]
                return False, ["Unsupported existential pattern."]
            entailed, trace = self._closure_entails_existential(preds)
            return entailed, trace

        # Unary fact query (default)
        m = _RE_UNARY.match(fol)
        if not m:
            # Graceful: if stored but unsupported, acknowledge storage
            if fol in self.other_formulas:
                return False, ["Formula stored in KB but outside reasoning fragment."]
            return False, ["Query not a supported pattern."]
        qpred, qconst = m.group(1), m.group(2)
        entailed, trace = self._closure_entails_fact(qpred, qconst, max_steps=max_steps)
        if entailed:
            return True, trace
        # Attempt generic resolution reasoning over all stored formulas
        r_ok, r_trace = self._resolution_entails_fact(qpred, qconst, limit_steps=500)
        if r_ok:
            return True, ["resolution proof:"] + r_trace
        return False, trace + ["resolution could not derive goal."]

    # ---------------- Backward Chaining Public API -----------------
    def backward_query(self, fol: str, depth_limit: int = 50) -> Tuple[bool, List[str]]:
        """Goal-directed (backward) query. Supports:
        - unary fact Q(Const)
        - existential exists x. (P(x) & Q(x) & ...)
        Returns (entailed, trace). Does not modify KB state.
        """
        fol = fol.strip()
        node = parse(tokenize(fol))
        if isinstance(node, Existential):
            preds = self._collect_unary_preds(node.formula, var_only=node.var)
            if not preds:
                if fol in self.other_formulas:
                    return False, ["Formula stored but not supported for backward reasoning."]
                return False, ["Unsupported existential pattern."]
            return self._backward_existential(preds, depth_limit)
        m = _RE_UNARY.match(fol)
        if not m:
            if fol in self.other_formulas:
                return False, ["Formula stored but not supported for backward reasoning."]
            return False, ["Unsupported query for backward chaining."]
        ok, trace = self._backward_fact(m.group(1), m.group(2), depth_limit)
        if ok:
            return True, trace
        # Fallback to resolution attempt to supply a proof trace if possible
        r_ok, r_trace = self._resolution_entails_fact(m.group(1), m.group(2), limit_steps=500)
        if r_ok:
            return True, ["resolution proof:"] + r_trace
        return False, trace + ["resolution could not derive goal."]

    # ---------- Internal helpers ----------
    def _collect_unary_preds(self, node, var_only: Optional[str] = None) -> Optional[List[str]]:
        """Collect a list of predicate names from a node that is either a single
        Predicate(var) or a conjunction of such. Returns None on unsupported shapes."""
        def _is_var_term(term) -> bool:
            return isinstance(term, str) and (var_only is None or term == var_only)

        def _from(node) -> Optional[List[str]]:
            if isinstance(node, Predicate):
                if len(node.terms) == 1 and _is_var_term(node.terms[0]):
                    return [node.name]
                return None
            if isinstance(node, And):
                left = _from(node.left)
                right = _from(node.right)
                if left is None or right is None:
                    return None
                return left + right
            return None

        return _from(node)

    def _next_witness(self) -> str:
        # generate a fresh witness constant not used in facts
        i = 1
        while True:
            w = f"w{i}"
            if all(not f.endswith(f"({w})") for f in self.facts):
                return w
            i += 1

    def _closure(self, max_steps: int = 1000) -> Tuple[Set[str], Dict[str, str]]:
        derived: Set[str] = set(self.facts)
        trace_map: Dict[str, str] = {f: f"premise: {f}" for f in derived}
        steps = 0
        changed = True
        while changed and steps < max_steps:
            changed = False
            steps += 1
            # Collect known constants
            consts = set()
            for f in derived:
                m = _RE_UNARY.match(f)
                if m:
                    consts.add(m.group(2))
            # Apply each rule to each constant
            for rule in self.rules_adv:
                ant = rule['ant']
                cons = rule['cons']
                for c in consts:
                    needed = [f"{p}({c})" for p in ant]
                    if all(n in derived for n in needed):
                        for k in cons:
                            nf = f"{k}({c})"
                            if nf not in derived:
                                derived.add(nf)
                                changed = True
                                ant_str = ' & '.join(needed)
                                cons_str = f"{k}(x)"
                                trace_map[nf] = f"from {ant_str} and rule { ' & '.join(p + '(x)' for p in ant) } -> { ' & '.join(p + '(x)' for p in cons) } derive {nf}"
        return derived, trace_map

    def _closure_entails_fact(self, pred: str, const: str, max_steps: int = 1000) -> Tuple[bool, List[str]]:
        derived, trace_map = self._closure(max_steps=max_steps)
        key = f"{pred}({const})"
        if key in derived:
            return True, [trace_map.get(key, key)]
        # Provide hints from other_formulas referencing this predicate
        hints = self._related_other([pred])
        trace = ["No derivation found for query."]
        if hints:
            trace += [f"related formula (not used): {h}" for h in hints]
        return False, trace

    def _closure_entails_existential(self, preds: List[str], max_steps: int = 1000) -> Tuple[bool, List[str]]:
        derived, trace_map = self._closure(max_steps=max_steps)
        # look for any constant that satisfies all preds
        consts = set()
        for f in derived:
            m = _RE_UNARY.match(f)
            if m:
                consts.add(m.group(2))
        for c in consts:
            need = [f"{p}({c})" for p in preds]
            if all(n in derived for n in need):
                # Build a small trace mentioning witness
                traces = [trace_map.get(n, n) for n in need]
                return True, [f"witness {c}: all required facts present."] + traces
        hints = self._related_other(preds)
        trace = ["No witness found."]
        if hints:
            trace += [f"related formula (not used): {h}" for h in hints]
        return False, trace

    # ---------------- Backward Chaining Internals -----------------
    def _backward_fact(self, pred: str, const: str, depth_limit: int) -> Tuple[bool, List[str]]:
        # Precompute closure for positive facts availability (optional shortcut)
        derived, trace_map = self._closure(max_steps=1000)
        target = f"{pred}({const})"
        if target in derived:
            return True, [f"fact available: {target}"]

        visited: Set[str] = set()
        path: List[str] = []

        def dfs(p: str) -> bool:
            key = f"{p}({const})"
            if key in visited:
                return False
            visited.add(key)
            # direct fact check
            if key in self.facts:
                path.append(f"premise: {key}")
                return True
            # try rules with p in consequent
            for rule in self.rules_adv:
                if p in rule['cons']:
                    ant_list = rule['ant']
                    # prove all antecedents
                    subproof: List[str] = []
                    ok_all = True
                    for q in ant_list:
                        if not dfs(q):
                            ok_all = False
                            break
                    if ok_all:
                        path.append(
                            f"from {', '.join(a+'('+const+')' for a in ant_list)} via rule {' & '.join(a+'(x)' for a in ant_list)} -> {' & '.join(c+'(x)' for c in rule['cons'])} derive {key}"
                        )
                        return True
            return False

        ok = dfs(pred)
        if ok:
            return True, path
        hints = self._related_other([pred])
        trace = ["Backward chaining failed to derive goal."]
        if hints:
            trace += [f"related formula (not used): {h}" for h in hints]
        return False, trace

    def _backward_existential(self, preds: List[str], depth_limit: int) -> Tuple[bool, List[str]]:
        # Gather existing constants
        consts: Set[str] = set()
        for f in self.facts:
            m = _RE_UNARY.match(f)
            if m:
                consts.add(m.group(2))
        # Try each constant as witness
        for c in sorted(consts):
            traces: List[str] = []
            failed = False
            for p in preds:
                ok, t = self._backward_fact(p, c, depth_limit)
                if not ok:
                    failed = True
                    break
                traces.extend(t)
            if not failed:
                return True, [f"witness {c} found"] + traces
        hints = self._related_other(preds)
        trace = ["No witness constant satisfies all predicates by backward chaining."]
        if hints:
            trace += [f"related formula (not used): {h}" for h in hints]
        return False, trace

    def _related_other(self, preds: List[str], limit: int = 3) -> List[str]:
        # Return up to 'limit' stored other formulas mentioning any predicate
        out: List[str] = []
        if not self.other_formulas:
            return out
        pats = [re.compile(rf"\b{re.escape(p)}\s*\(") for p in preds]
        for s in sorted(self.other_formulas):
            if any(p.search(s) for p in pats):
                out.append(s)
                if len(out) >= limit:
                    break
        return out

    # ---------------- Resolution-based reasoning (experimental) -------------
    def _resolution_entails_fact(self, pred: str, const: str, limit_steps: int = 500, extra_negated: Optional[List[str]] = None) -> Tuple[bool, List[str]]:
        """Attempt to prove P(const) using resolution over all stored formulas.
        Restricted fragment: predicates only (unary), disjunctions, implications, conjunctions.
        Universals are instantiated over known constants. Existentials already skolemized.
        Returns (entailed, trace_of_resolution_steps)."""
        # Build clause set
        clauses, origin = self._build_clause_set()
        goal = f"{pred}({const})"
        # If already a unit clause present, success quickly
        if any(len(c)==1 and goal in c for c in clauses):
            return True, [f"unit present: {goal}"]
        # Add negated goal(s) for refutation
        negs: List[str] = [f"~{goal}"]
        if extra_negated:
            negs.extend(extra_negated)
        for ng in negs:
            clauses.append({ng})
            origin[len(clauses)-1] = f"negated goal {ng}"
        trace: List[str] = []
        # Resolution loop
        step = 0
        seen = set()
        while step < limit_steps:
            step += 1
            progress = False
            new_clauses: List[Set[str]] = []
            for i in range(len(clauses)):
                for j in range(i+1, len(clauses)):
                    c1, c2 = clauses[i], clauses[j]
                    for lit in list(c1):
                        comp = lit[1:] if lit.startswith('~') else f"~{lit}"
                        if comp in c2:
                            resolvent = (c1 - {lit}) | (c2 - {comp})
                            key = tuple(sorted(resolvent))
                            if key in seen:
                                continue
                            seen.add(key)
                            progress = True
                            descr = f"resolve ({origin.get(i,'c'+str(i))}) & ({origin.get(j,'c'+str(j))}) on {lit} with {comp} -> { ' ∅' if not resolvent else ' | '.join(sorted(resolvent)) }"
                            trace.append(descr)
                            if not resolvent:
                                trace.append("derived empty clause; goal entailed")
                                return True, trace
                            new_clauses.append(resolvent)
            if not progress:
                break
            # Integrate new clauses
            for nc in new_clauses:
                clauses.append(nc)
                origin[len(clauses)-1] = "derived"
        return False, trace

    def _resolution_entails_disjunction(self, preds: List[str], const: str, limit_steps: int = 500) -> Tuple[bool, List[str]]:
        # Refutation: add negation of each disjunct as unit clauses
        extra = [f"~{p}({const})" for p in preds]
        # Use dummy predicate that will not match, so base goal contributes nothing
        ok, trace = self._resolution_entails_fact("__Dummy__", const, limit_steps=limit_steps, extra_negated=extra)
        return ok, trace

    def _collect_or_unary(self, node) -> Optional[Tuple[str, List[str]]]:
        # Return (const, [Pred1, Pred2, ...]) if node is P(c) | Q(c) | ...
        from proof.ast_nodes import Predicate, Or
        if node is None:
            return None
        lits: List[Tuple[str,str]] = []  # (pred, const)
        def walk(n):
            if isinstance(n, Or):
                walk(n.left); walk(n.right)
                return
            if isinstance(n, Predicate) and len(n.terms)==1 and isinstance(n.terms[0], str) and n.terms[0][0].isupper():
                lits.append((n.name, n.terms[0])); return
            lits.clear()
        walk(node)
        if not lits:
            return None
        consts = {c for _,c in lits}
        if len(consts)!=1:
            return None
        c = next(iter(consts))
        preds = [p for p,_ in lits]
        if len(preds) < 2:
            return None
        return c, preds

    def _build_clause_set(self) -> Tuple[List[Set[str]], Dict[int,str]]:
        """Construct initial clause set from facts + all formulas (including other_formulas)."""
        clauses: List[Set[str]] = []
        origin: Dict[int,str] = {}
        # Facts as unit clauses
        for f in sorted(self.facts):
            clauses.append({f})
            origin[len(clauses)-1] = f
        # Collect constants for universal instantiation
        consts = self._all_constants()
        # Parse and transform formulas
        for s in sorted(self.rules_adv_to_strings() + list(self.other_formulas)):
            node = parse(tokenize(s))
            if node is None:
                continue
            for clause in self._formula_to_clauses(node, consts):
                if clause:
                    clauses.append(clause)
                    origin[len(clauses)-1] = s
        return clauses, origin

    def rules_adv_to_strings(self) -> List[str]:
        out: List[str] = []
        for r in self.rules_adv:
            ant = ' & '.join(f"{p}(x)" for p in r['ant'])
            cons = ' & '.join(f"{p}(x)" for p in r['cons'])
            out.append(f"forall x. ({ant} -> {cons})")
        return out

    def _all_constants(self) -> Set[str]:
        consts: Set[str] = set()
        for f in self.facts:
            m = _RE_UNARY.match(f)
            if m:
                consts.add(m.group(2))
        # Add witness constants that may appear only in other formulas later
        return consts or {"w1"}

    def _formula_to_clauses(self, node, consts: Set[str]) -> List[Set[str]]:
        """Very limited CNF extraction supporting:
        - Predicate
        - Not(Predicate)
        - A & B (concatenate clauses)
        - A | B (single clause with both literals)
        - Implication A -> B (as ~A | B)
        - Bicond A <-> B as (A -> B) & (B -> A)
        - Universal quantifier forall x. φ (instantiate x with known constants)
        Existentials should have been skolemized already into facts.
        Returns list of clauses (each clause = set of literals)."""
        from proof.ast_nodes import Predicate, Not, And, Or, Implies, Bicond, Universal
        def neg(lit: str) -> str:
            return lit if lit.startswith('~') else f"~{lit}"
        def pred_to_lit(p: Predicate) -> Optional[str]:
            if len(p.terms)!=1:
                return None
            t = p.terms[0]
            if isinstance(t,str) and t[0].isupper():
                return f"{p.name}({t})"
            return None
        if isinstance(node, Universal):
            res: List[Set[str]] = []
            inner = node.formula
            for c in consts:
                # substitute variable occurrences
                replaced = self._subst(inner, node.var, c)
                res.extend(self._formula_to_clauses(replaced, consts))
            return res
        if isinstance(node, Bicond):
            # A <-> B == (A -> B) & (B -> A)
            return self._formula_to_clauses(Implies(node.left,node.right), consts) + self._formula_to_clauses(Implies(node.right,node.left), consts)
        if isinstance(node, Implies):
            # ~A | B
            left_clauses = self._formula_to_clauses(node.left, consts)
            right_clauses = self._formula_to_clauses(node.right, consts)
            # If left/right reduce to single literal sets, combine
            left_lits = [lit for cls in left_clauses for lit in cls]
            right_lits = [lit for cls in right_clauses for lit in cls]
            # Negate every literal in antecedent (assumes antecedent is conjunction of positive literals)
            antecedent_neg = [neg(l) if not l.startswith('~') else l[1:] for l in left_lits]
            return [set(antecedent_neg + right_lits)]
        if isinstance(node, And):
            return self._formula_to_clauses(node.left,consts) + self._formula_to_clauses(node.right,consts)
        if isinstance(node, Or):
            left = self._formula_to_clauses(node.left,consts)
            right = self._formula_to_clauses(node.right,consts)
            # flatten if unit clauses else combine all literals
            lits = set()
            for cls in left+right:
                lits |= cls
            return [lits]
        if isinstance(node, Predicate):
            lit = pred_to_lit(node)
            return [ {lit} ] if lit else []
        if isinstance(node, Not):
            if isinstance(node.formula, Predicate):
                lit = pred_to_lit(node.formula)
                return [ {neg(lit)} ] if lit else []
        return []

    def _subst(self, node, var: str, const: str):
        from proof.ast_nodes import Predicate, And, Or, Implies, Bicond, Universal, Existential, Not
        if isinstance(node, Predicate):
            terms = [const if (isinstance(t,str) and t==var) else t for t in node.terms]
            return Predicate(node.name, terms)
        if isinstance(node, And):
            return And(self._subst(node.left,var,const), self._subst(node.right,var,const))
        if isinstance(node, Or):
            return Or(self._subst(node.left,var,const), self._subst(node.right,var,const))
        if isinstance(node, Implies):
            return Implies(self._subst(node.left,var,const), self._subst(node.right,var,const))
        if isinstance(node, Bicond):
            return Bicond(self._subst(node.left,var,const), self._subst(node.right,var,const))
        if isinstance(node, Universal):
            # shadowing: keep variable if same name
            if node.var == var:
                return node
            return Universal(node.var, self._subst(node.formula,var,const))
        if isinstance(node, Existential):
            if node.var == var:
                return node
            return Existential(node.var, self._subst(node.formula,var,const))
        if isinstance(node, Not):
            return Not(self._subst(node.formula,var,const))
        return node


_global_kb: Optional[KnowledgeBase] = None


def kb() -> KnowledgeBase:
    global _global_kb
    if _global_kb is None:
        _global_kb = KnowledgeBase()
    return _global_kb

    
    
def _serialize(obj: object):
    return obj

