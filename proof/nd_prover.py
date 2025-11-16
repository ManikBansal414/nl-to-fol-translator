from __future__ import annotations
from typing import List, Tuple
from .parser import parse, tokenize
from .ast_nodes import TruthValue, And, Or, Not, Implies, Bicond, Universal, Existential
import re


def remove_nestings(l):
    def output_gen(l, output):
        for i in l:
            if type(i) == list:
                output_gen(i, output)
            else:
                output.append(i)
        return output
    return output_gen(l, output=[])


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


def end_checker(prem, proof, exit_lines):
    emb = 0
    for n in range(len(proof)):
        if type(proof[n]) == list:
            emb += 1
        elif n + len(prem) in exit_lines:
            emb -= 1
    if emb <= 0:
        return False
    else:
        return True


def active_assum(prem, proof, exit_lines):
    active = []
    for n in range(len(proof)):
        if type(proof[n]) == list:
            active.append(proof[n][0])
        elif n + len(prem) in exit_lines:
            active.pop()
    return active


def proof_display(prem, proof, exit_lines):
    print(' ')
    count = 0
    for pr in prem:
        print(str(count) + (' ' * (6 - len(str(count)))) + str(pr))
        count += 1
    print('_________________')
    print(' ')
    emb = 0
    for line in proof:
        if type(line) == list:
            emb += 1
            print(str(count) + (' ' * (6 - len(str(count)))) + ('|' * emb) + ' ' + str(line[0]))
            count += 1
        elif count in exit_lines:
            emb -= 1
            print(str(count) + (' ' * (6 - len(str(count)))) + ('|' * emb) + ' ' + str(line))
            count += 1
        else:
            print(str(count) + (' ' * (6 - len(str(count)))) + ('|' * emb) + ' ' + str(line))
            count += 1
    print(' ')


# Minimal set of rules ported: Assume, Delete, TI, ^EL, ^ER, ^I, R, >E, Finish
# Additional rules from the original script can be added incrementally.

def prover():
    proof: List = []
    prem: List = []
    print('Please state the premises, separated by commas (in common FOL notation).')
    e = input('%')
    if e == 'Exit':
        return None
    else:
        r = re.compile(r'(?:[^,(]|\([^)]*\))+')
        prems = r.findall(e)
        for pr in prems:
            f = parse(tokenize(pr))
            if f is None:
                print('Could not parse premise:', pr)
                return None
            prem.append(f)
        count = 0
        exit_lines: List[int] = []
        print(' ')
        for pr in prem:
            print(str(count) + (' ' * (6 - len(str(count)))) + str(pr))
            count += 1
        print('_________________')
        print(' ')

        while True:
            print('Enter a rule (Assume <formula> | Delete | TI | ^EL n | ^ER n | ^I n,m | R n | >E n,m | Finish).')
            e = input('%')
            if e == 'Exit':
                break
            elif len(e) == 0:
                continue
            else:
                rule = r.findall(e)
                try:
                    if rule[0] == 'Assume':
                        a = rule[1]
                        assumption = parse(tokenize(a))
                        if assumption is None:
                            print('Bad formula.')
                        else:
                            proof.append([assumption])
                        proof_display(prem, proof, exit_lines)
                    elif rule[0] == 'Delete':
                        if len(proof) == 0:
                            continue
                        proof = proof[:-1]
                        proof_display(prem, proof, exit_lines)
                    elif rule[0] == 'TI':
                        proof.append(TruthValue(True))
                        proof_display(prem, proof, exit_lines)
                    elif rule[0] == '^EL':
                        n = int(rule[1])
                        if hyp_space_rel(prem, proof, n, exit_lines) == False:
                            print('You can no longer use that formula.')
                        else:
                            src = prem[n] if n < len(prem) else assum(proof[n - len(prem)])
                            if not isinstance(src, And):
                                print('That formula is not a conjunction.')
                            else:
                                proof.append(src.left)
                                proof_display(prem, proof, exit_lines)
                    elif rule[0] == '^ER':
                        n = int(rule[1])
                        if hyp_space_rel(prem, proof, n, exit_lines) == False:
                            print('You can no longer use that formula.')
                        else:
                            src = prem[n] if n < len(prem) else assum(proof[n - len(prem)])
                            if not isinstance(src, And):
                                print('That formula is not a conjunction.')
                            else:
                                proof.append(src.right)
                                proof_display(prem, proof, exit_lines)
                    elif rule[0] == '^I':
                        n1 = int(rule[1]); n2 = int(rule[2])
                        if hyp_space_rel(prem, proof, n1, exit_lines) == False or hyp_space_rel(prem, proof, n2, exit_lines) == False:
                            print('You can no longer use that formula.')
                        else:
                            f1 = prem[n1] if n1 < len(prem) else assum(proof[n1 - len(prem)])
                            f2 = prem[n2] if n2 < len(prem) else assum(proof[n2 - len(prem)])
                            proof.append(And(f1, f2))
                            proof_display(prem, proof, exit_lines)
                    elif rule[0] == 'R':
                        n = int(rule[1])
                        if hyp_space_rel(prem, proof, n, exit_lines) == False:
                            print('You can no longer use that formula.')
                        else:
                            proof.append(prem[n] if n < len(prem) else assum(proof[n - len(prem)]))
                            proof_display(prem, proof, exit_lines)
                    elif rule[0] == '>E':
                        n1 = int(rule[1]); n2 = int(rule[2])
                        if hyp_space_rel(prem, proof, n1, exit_lines) == False or hyp_space_rel(prem, proof, n2, exit_lines) == False:
                            print('You can no longer use a specified formula.')
                        else:
                            a = prem[n1] if n1 < len(prem) else assum(proof[n1 - len(prem)])
                            c = prem[n2] if n2 < len(prem) else assum(proof[n2 - len(prem)])
                            if not isinstance(c, Implies) or str(c.left) != str(a):
                                print('The first formula must be the antecedent of the conditional in the second formula.')
                            else:
                                proof.append(c.right)
                                proof_display(prem, proof, exit_lines)
                    elif rule[0] == 'Finish':
                        if len(proof) == 0:
                            print('You have not begun a proof.')
                        else:
                            prem_str = ''
                            if len(prem) == 1:
                                prem_str = str(prem[0])
                            elif len(prem) == 2:
                                prem_str = str(prem[0]) + ' and ' + str(prem[1])
                            else:
                                for pr in prem[:-1]:
                                    prem_str = prem_str + str(pr) + ', '
                                prem_str = prem_str + 'and ' + str(prem[-1])
                            print('Theorem: If {0} then {1}.'.format(prem_str, str(proof[-1])))
                            break
                    else:
                        print('That is not a supported rule (in this minimal port).')
                except (IndexError, ValueError):
                    print('Bad indices or arguments.')

if __name__ == '__main__':
    prover()
