from __future__ import annotations
from typing import List, Tuple, Dict, Any
import re
from .parser import parse, tokenize
from .ast_nodes import TruthValue, And, Or, Not, Implies, Bicond, Universal, Existential, Predicate


def assum(formula):
    if type(formula) == list:
        return formula[0]
    else:
        return formula


def hyp_space_rel(prem, proof, line, exit_lines, sub=False, line2=None):
    emb = 0
    emb_thresh = 0
    for n in range(len(proof)):
        if line == n + len(prem):
            if sub == False:
                emb_thresh = emb
            else:
                emb_thresh = emb - 1
        elif type(proof[n]) == list:
            emb += 1
        elif n + len(prem) in exit_lines:
            emb -= 1
        if emb_thresh > emb:
            return False
    if sub == True and emb_thresh < emb:
        return False
    elif sub == True and line2:
        return hyp_space_rel(prem, proof[:line2 - len(prem) + 1], line, exit_lines, False, False)
    return True


def proof_lines(prem, proof, exit_lines) -> List[str]:
    out: List[str] = []
    count = 0
    for pr in prem:
        out.append(str(count) + (' ' * (6 - len(str(count)))) + str(pr))
        count += 1
    out.append('_________________')
    out.append(' ')
    emb = 0
    for line in proof:
        if type(line) == list:
            emb += 1
            out.append(str(count) + (' ' * (6 - len(str(count)))) + ('|' * emb) + ' ' + str(line[0]))
            count += 1
        elif count in exit_lines:
            emb -= 1
            out.append(str(count) + (' ' * (6 - len(str(count)))) + ('|' * emb) + ' ' + str(line))
            count += 1
        else:
            out.append(str(count) + (' ' * (6 - len(str(count)))) + ('|' * emb) + ' ' + str(line))
            count += 1
    return out


def run_proof(premises: List[str], commands: List[str]) -> Dict[str, Any]:
    proof: List = []
    prem: List = []
    # Simple command tokenizer: preserves formulas for Assume, splits others on spaces/commas
    def tokenize_cmd(s: str):
        s = s.strip()
        if s.startswith('Assume '):
            return ['Assume', s[len('Assume '):].strip()]
        # Replace commas with spaces then split
        return [t for t in re.split(r'[\s,]+', s) if t]
    # Parse premises
    for pr in premises:
        pr = pr.strip()
        if not pr:
            continue
        f = parse(tokenize(pr))
        if f is None:
            return { 'ok': False, 'error': f'Could not parse premise: {pr}', 'lines': [] }
        prem.append(f)
    exit_lines: List[int] = []

    # Substitution helper for ∀E
    def subst(node, var: str, const: str):
        if isinstance(node, Predicate):
            new_terms = [const if (isinstance(t, str) and t == var) else t for t in node.terms]
            return Predicate(node.name, new_terms)
        if isinstance(node, And):
            return And(subst(node.left, var, const), subst(node.right, var, const))
        if isinstance(node, Or):
            return Or(subst(node.left, var, const), subst(node.right, var, const))
        if isinstance(node, Not):
            return Not(subst(node.formula, var, const))
        if isinstance(node, Implies):
            return Implies(subst(node.left, var, const), subst(node.right, var, const))
        if isinstance(node, Bicond):
            return Bicond(subst(node.left, var, const), subst(node.right, var, const))
        if isinstance(node, Universal):
            # avoid capture: if bound var equals target, don't descend
            if node.var == var:
                return node
            return Universal(node.var, subst(node.formula, var, const))
        if isinstance(node, Existential):
            if node.var == var:
                return node
            return Existential(node.var, subst(node.formula, var, const))
        return node

    # Execute commands
    for e in commands:
        e = e.strip()
        if not e:
            continue
        rule = tokenize_cmd(e)
        try:
            if rule[0] == 'Assume':
                a = rule[1]
                assumption = parse(tokenize(a))
                if assumption is None:
                    return { 'ok': False, 'error': f'Bad formula in Assume: {a}', 'lines': proof_lines(prem, proof, exit_lines) }
                proof.append([assumption])
            elif rule[0] == 'Delete':
                if len(proof) > 0:
                    proof = proof[:-1]
            elif rule[0] == 'TI':
                proof.append(TruthValue(True))
            elif rule[0] == '^EL':
                n = int(rule[1])
                if hyp_space_rel(prem, proof, n, exit_lines) == False:
                    return { 'ok': False, 'error': 'Invalid scope for ^EL', 'lines': proof_lines(prem, proof, exit_lines) }
                src = prem[n] if n < len(prem) else assum(proof[n - len(prem)])
                if not isinstance(src, And):
                    return { 'ok': False, 'error': 'Target is not a conjunction', 'lines': proof_lines(prem, proof, exit_lines) }
                proof.append(src.left)
            elif rule[0] == '^ER':
                n = int(rule[1])
                if hyp_space_rel(prem, proof, n, exit_lines) == False:
                    return { 'ok': False, 'error': 'Invalid scope for ^ER', 'lines': proof_lines(prem, proof, exit_lines) }
                src = prem[n] if n < len(prem) else assum(proof[n - len(prem)])
                if not isinstance(src, And):
                    return { 'ok': False, 'error': 'Target is not a conjunction', 'lines': proof_lines(prem, proof, exit_lines) }
                proof.append(src.right)
            elif rule[0] == '^I':
                n1 = int(rule[1]); n2 = int(rule[2])
                if hyp_space_rel(prem, proof, n1, exit_lines) == False or hyp_space_rel(prem, proof, n2, exit_lines) == False:
                    return { 'ok': False, 'error': 'Invalid scope for ^I', 'lines': proof_lines(prem, proof, exit_lines) }
                f1 = prem[n1] if n1 < len(prem) else assum(proof[n1 - len(prem)])
                f2 = prem[n2] if n2 < len(prem) else assum(proof[n2 - len(prem)])
                proof.append(And(f1, f2))
            elif rule[0] == 'R':
                n = int(rule[1])
                if hyp_space_rel(prem, proof, n, exit_lines) == False:
                    return { 'ok': False, 'error': 'Invalid scope for R', 'lines': proof_lines(prem, proof, exit_lines) }
                proof.append(prem[n] if n < len(prem) else assum(proof[n - len(prem)]))
            elif rule[0] == '>E':
                n1 = int(rule[1]); n2 = int(rule[2])
                if hyp_space_rel(prem, proof, n1, exit_lines) == False or hyp_space_rel(prem, proof, n2, exit_lines) == False:
                    return { 'ok': False, 'error': 'Invalid scope for >E', 'lines': proof_lines(prem, proof, exit_lines) }
                a = prem[n1] if n1 < len(prem) else assum(proof[n1 - len(prem)])
                c = prem[n2] if n2 < len(prem) else assum(proof[n2 - len(prem)])
                if not isinstance(c, Implies) or str(c.left) != str(a):
                    return { 'ok': False, 'error': 'Bad >E: antecedent mismatch or not a conditional', 'lines': proof_lines(prem, proof, exit_lines) }
                proof.append(c.right)
            elif rule[0] in ('>I','->I'):
                a = int(rule[1]); b = int(rule[2])
                # a must be an assumption line in proof
                if a < len(prem) or (a - len(prem)) >= len(proof) or not isinstance(proof[a - len(prem)], list):
                    return { 'ok': False, 'error': '->I expects first index to be an assumption line', 'lines': proof_lines(prem, proof, exit_lines) }
                if b <= a:
                    return { 'ok': False, 'error': '->I requires conclusion index after assumption', 'lines': proof_lines(prem, proof, exit_lines) }
                antecedent = assum(proof[a - len(prem)])
                conclusion = prem[b] if b < len(prem) else assum(proof[b - len(prem)])
                # mark subproof exit at this next line index
                exit_lines.append(len(prem) + len(proof))
                proof.append(Implies(antecedent, conclusion))
            elif rule[0] in ('∀E','AE'):
                n = int(rule[1])
                const = str(rule[2])
                if hyp_space_rel(prem, proof, n, exit_lines) == False:
                    return { 'ok': False, 'error': 'Invalid scope for ∀E', 'lines': proof_lines(prem, proof, exit_lines) }
                src = prem[n] if n < len(prem) else assum(proof[n - len(prem)])
                if not isinstance(src, Universal):
                    return { 'ok': False, 'error': 'Target is not universal for ∀E', 'lines': proof_lines(prem, proof, exit_lines) }
                instantiated = subst(src.formula, src.var, const)
                proof.append(instantiated)
            elif rule[0] == 'Finish':
                break
            else:
                return { 'ok': False, 'error': f'Unsupported rule: {rule[0]}', 'lines': proof_lines(prem, proof, exit_lines) }
        except (IndexError, ValueError):
            return { 'ok': False, 'error': 'Bad indices or arguments', 'lines': proof_lines(prem, proof, exit_lines) }

    lines = proof_lines(prem, proof, exit_lines)
    theorem = lines[-1] if lines else ''
    return { 'ok': True, 'error': None, 'lines': lines, 'theorem': theorem }
