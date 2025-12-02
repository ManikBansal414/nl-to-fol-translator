from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Dict, Any

from flask import Flask, render_template, request

# Ensure project root is importable when running from GUI/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from translator import translate_sentence
from method_lark.validator import validate as validate_lark
from method_nltk.validator import validate as validate_nltk
from method_fomaster.validator import validate as validate_fomaster
from knowledge_base import kb
from proof.engine import run_proof

app = Flask(__name__)

METHODS = {
    "lark": validate_lark,
    "nltk": validate_nltk,
    "fomaster": validate_fomaster,
}


def run_validation(sentence: str, method: str) -> Dict[str, Any]:
    fol = translate_sentence(sentence)
    if fol.startswith("[ERROR]"):
        return {"sentence": sentence, "fol": None, "error": fol, "results": {}}

    results: Dict[str, bool] = {}
    if method == "all":
        for name, fn in METHODS.items():
            try:
                results[name] = bool(fn(fol))
            except Exception:
                results[name] = False
    else:
        fn = METHODS.get(method)
        if fn is None:
            return {
                "sentence": sentence,
                "fol": fol,
                "error": f"Unknown method: {method}",
                "results": {},
            }
        try:
            results[method] = bool(fn(fol))
        except Exception:
            results[method] = False

    return {"sentence": sentence, "fol": fol, "error": None, "results": results}


@app.route("/", methods=["GET", "POST"])
def index():
    context: Dict[str, Any] = {
        "selected_method": "all",
        "sentence": "",
        "data": None,
        "methods": ["all", "lark", "nltk", "fomaster"],
        "kb_data": None,
        "kb_state": {
            "facts": kb().list_facts(),
            "rules": kb().list_rules(),
            "other": kb().list_other(),
        },
        "proof_result": None,
    }

    if request.method == "POST":
        sentence = request.form.get("sentence", "").strip()
        method = request.form.get("method", "all")
        action = request.form.get("action", "validate")
        context["selected_method"] = method
        context["sentence"] = sentence

        if action == "validate":
            if sentence:
                context["data"] = run_validation(sentence, method)
            else:
                context["data"] = {
                    "sentence": "",
                    "fol": None,
                    "error": "Please enter a sentence to translate.",
                    "results": {},
                }
        elif action == "kb_add":
            if sentence:
                fol = translate_sentence(sentence)
                if fol.startswith("[ERROR]"):
                    context["kb_data"] = {
                        "action": "add",
                        "sentence": sentence,
                        "fol": None,
                        "ok": False,
                        "error": fol,
                        "trace": [],
                    }
                else:
                    ok = kb().add(fol)
                    stored_other = fol in kb().list_other()
                    context["kb_data"] = {
                        "action": "add",
                        "sentence": sentence,
                        "fol": fol,
                        "ok": bool(ok),
                        "stored_other": stored_other,
                        "error": None if ok else "Unrecognized formula",
                        "trace": [],
                    }
            else:
                context["kb_data"] = {
                    "action": "add",
                    "sentence": "",
                    "fol": None,
                    "ok": False,
                    "error": "Please enter a sentence.",
                    "trace": [],
                }
        elif action == "kb_query":
            if sentence:
                fol = translate_sentence(sentence)
                if fol.startswith("[ERROR]"):
                    context["kb_data"] = {
                        "action": "query",
                        "sentence": sentence,
                        "fol": None,
                        "ok": False,
                        "error": fol,
                        "trace": [],
                    }
                else:
                    kb_mode = request.form.get("kb_mode", "both")
                    ok_f = False
                    trace_f = []
                    ok_b = False
                    trace_b = []
                    if kb_mode in ("forward", "both"):
                        ok_f, trace_f = kb().query(fol)
                    if kb_mode in ("backward", "both"):
                        try:
                            ok_b, trace_b = kb().backward_query(fol)
                        except Exception as e:
                            ok_b, trace_b = False, [f"Backward error: {e}"]
                    context["kb_data"] = {
                        "action": "query",
                        "sentence": sentence,
                        "fol": fol,
                        "mode": kb_mode,
                        "ok_forward": bool(ok_f),
                        "trace_forward": trace_f,
                        "ok_backward": bool(ok_b),
                        "trace_backward": trace_b,
                    }
            else:
                context["kb_data"] = {
                    "action": "query",
                    "sentence": "",
                    "fol": None,
                    "ok": False,
                    "error": "Please enter a sentence.",
                    "trace": [],
                }
        elif action == "kb_clear":
            kb().clear()
            context["kb_data"] = {
                "action": "clear",
                "sentence": "",
                "fol": None,
                "ok": True,
                "error": None,
                "trace": ["KB cleared"],
            }
        elif action == "proof_run":
            # collect premises and commands
            prem_raw = request.form.get("premises", "").strip()
            cmds_raw = request.form.get("commands", "").strip()
            premises = [p.strip() for p in prem_raw.split("\n") if p.strip()]
            commands = [c.strip() for c in cmds_raw.split("\n") if c.strip()]
            result = run_proof(premises, commands)
            context["proof_result"] = result

        # refresh KB state after any action
        context["kb_state"] = {
            "facts": kb().list_facts(),
            "rules": kb().list_rules(),
            "other": kb().list_other(),
        }
    return render_template("index.html", **context)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
