"""Coding prompts: generate a function, run it on the prompt's own examples, retry on failure.

Options (eng.opts, strings):
  coder      vlm (Qwen3-VL-4B, already resident) | qwen25-3b (Qwen2.5-Coder-3B-Instruct,
             swaps the VLM out)
  quant      nf4 | bf16, for qwen25-3b
  selfcheck  1 | 0: run the docstring examples in maya/sandbox.py and retry on failure
  retries    retries after a failed self-check (default 2)
  prompt     plain | full | nodoc: "full" also asks for the whole function with its
             signature; "nodoc" asks it not to repeat the docstring (fewer tokens)
  max_new    max new tokens per generation
  fix        plain | explain: on a retry, ask for a short diagnosis before the fixed code
  fallback   qwen25-3b (default) | none: when the self-check still fails, try this coder
             too (a GPU swap: 5.8 s there, 2.9 s back to the VLM, warm file cache)
  budget_s   no new attempt starts after this many seconds (default 90)
  stop       1 | 0: stop generating at the end of the first code block

Self-checks come from the prompt only (doctests and "f(x) == y" style example
lines), never from hidden tests.
"""
import ast
import builtins
import json
import re
import time

from .sandbox import run_python

SYSTEM = ("You are a careful Python programmer. Return the complete function, including "
          "any imports it needs, in one ```python code block. No explanation.")
NODOC = (" Do not repeat the docstring and do not add comments or usage examples.")
FULL_ASK = ("\n\nWrite the complete implementation of `{name}`, starting with its `def` line, "
            "with any imports it needs, in one ```python code block.")
CODER_ID = "Qwen/Qwen2.5-Coder-3B-Instruct"
STDLIB = {"math", "re", "collections", "itertools", "functools", "heapq", "bisect", "string",
          "hashlib", "statistics", "operator", "random", "fractions", "decimal", "datetime"}
TYPING = {"List", "Tuple", "Dict", "Set", "Optional", "Any", "Union", "Callable", "Iterable",
          "Sequence"}
ARROW = re.compile(r"^\s*(?:==|=>|➞|->|→|⇒|#\s*=+>|should return|returns?|should be|gives|=)\s*(.*)$")


# Small models close the code block and then keep "reconsidering" in prose up to
# max_new_tokens: p_code_006 spent all 768 tokens (47 s) after a 12-line block.
STOP = ["\n```\n"]


class VlmCoder:
    """eng.vlm with generation stopped at the end of the first code block.

    Same template and generate call as Vlm.chat (maya/vlm.py:59-81), which has no
    stop-string argument.
    """

    def __init__(self, vlm, stop=STOP):
        self.v = vlm
        self.stop = stop
        self.load_s = getattr(vlm, "load_s", None)

    def text(self, prompt, system=None, max_new_tokens=256, history=None):
        import torch
        msgs = [{"role": "system", "content": [{"type": "text", "text": system}]}] if system else []
        for user, reply in history or []:
            msgs += [{"role": "user", "content": user},
                     {"role": "assistant", "content": [{"type": "text", "text": reply}]}]
        msgs.append({"role": "user", "content": [{"type": "text", "text": prompt}]})
        inputs = self.v.proc.apply_chat_template(
            msgs, add_generation_prompt=True, tokenize=True, return_dict=True,
            return_tensors="pt").to(self.v.model.device)
        t = time.perf_counter()
        with torch.inference_mode():
            out = self.v.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False,
                                        stop_strings=self.stop, tokenizer=self.v.proc.tokenizer)
        n_in = inputs["input_ids"].shape[-1]
        text = self.v.proc.decode(out[0][n_in:], skip_special_tokens=True).strip()
        return text, {"input_tokens": int(n_in), "output_tokens": int(out.shape[-1] - n_in),
                      "model_s": round(time.perf_counter() - t, 3)}


class Coder:
    def __init__(self, quant="nf4"):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        t = time.perf_counter()
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(CODER_ID)
        kw = {"device_map": "cuda", "dtype": torch.bfloat16}
        if quant == "nf4":
            kw["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
        self.model = AutoModelForCausalLM.from_pretrained(CODER_ID, **kw).eval()
        self.stop = STOP
        self.load_s = time.perf_counter() - t

    def text(self, prompt, system=None, max_new_tokens=256, history=None):
        msgs = [{"role": "system", "content": system}] if system else []
        for user, reply in history or []:
            msgs += [{"role": "user", "content": user[0]["text"]},
                     {"role": "assistant", "content": reply}]
        msgs.append({"role": "user", "content": prompt})
        inputs = self.tok.apply_chat_template(msgs, add_generation_prompt=True, return_dict=True,
                                              return_tensors="pt").to(self.model.device)
        t = time.perf_counter()
        with self.torch.inference_mode():
            out = self.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False,
                                      temperature=None, top_p=None, top_k=None,
                                      stop_strings=self.stop, tokenizer=self.tok)
        n_in = inputs["input_ids"].shape[-1]
        text = self.tok.decode(out[0][n_in:], skip_special_tokens=True).strip()
        return text, {"input_tokens": int(n_in), "output_tokens": int(out.shape[-1] - n_in),
                      "model_s": round(time.perf_counter() - t, 3)}


def model(eng, name="vlm"):
    stop = STOP if eng.opts.get("stop", "1") == "1" else None
    if name == "vlm":
        return VlmCoder(eng.vlm, stop)
    if name == "qwen25-3b":
        quant = eng.opts.get("quant", "nf4")
        m = eng.gpu_model(f"coder-{quant}", lambda: Coder(quant))
        m.stop = stop
        return m
    raise ValueError(f"unknown coder {name!r}")


def extract(text):
    m = re.findall(r"```(?:python|py)?[ \t]*\n(.*?)```", text, re.S)
    if m:
        return max(m, key=lambda b: ("def " in b, len(b))).strip()
    m = re.search(r"```(?:python|py)?[ \t]*\n(.*)", text, re.S)   # cut off at max_new
    return (m.group(1) if m else text).strip()


def prompt_code(question):
    """The Python part of the prompt, parsed: (source, module ast) or (None, None)."""
    # Fence lines become blank so a ```python block parses; prose after the code is cut
    # by taking the longest run of lines that parses.
    lines = [("" if re.match(r"\s*```", l) else l) for l in question.splitlines()]
    for i, line in enumerate(lines):
        if re.match(r"(from \S+ import|import |def |class |@)", line):
            for j in range(len(lines), i, -1):
                src = "\n".join(lines[i:j]).rstrip()
                try:
                    tree = ast.parse(src)
                except SyntaxError:
                    continue
                if tree.body:
                    return src, tree
    return None, None


def entry_def(tree):
    defs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    return defs[-1] if defs else None


def literal_prefix(s):
    """Longest prefix of s that is a Python literal: (value source, rest) or (None, s)."""
    s = s.strip()[:400]
    m = re.match(r"(true|false|none)\b", s)
    if m:
        return m.group(1).capitalize(), s[m.end():]
    for end in range(len(s), 0, -1):
        try:
            ast.literal_eval(s[:end].strip())
            # "1000, the sum ..." parses as the tuple "1000,"
            if s[:end].rstrip().endswith(",") and end > 1:
                continue
            return s[:end].strip(), s[end:]
        except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
            continue
    return None, s


def call_at(line, start):
    """Source of the balanced call that starts at line[start], and the index after it."""
    depth, quote = 0, None
    for i in range(line.index("(", start), len(line)):
        c = line[i]
        if quote:
            if c == quote and line[i - 1] != "\\":
                quote = None
        elif c in "'\"":
            quote = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                return line[start:i + 1], i + 1
    return None, len(line)


def expected_from(rest):
    exp, tail = literal_prefix(rest)
    # "f(5, 19) -> 19 - 5 - 6 = 8": the value is after the last "="
    if re.search(r"(?<![=!<>])=(?!=)", tail):
        exp, _ = literal_prefix(re.split(r"(?<![=!<>])=(?!=)", tail)[-1])
    return exp


def kwargs_call(name, params, text):
    """'N = 1000, k = 2' -> 'name(N=1000, k=2)' when every name is a parameter."""
    pairs, pos = [], 0
    for m in re.finditer(r"\b(\w+)\s*[=:]\s*", text):
        if m.start() < pos:
            continue
        val, rest = literal_prefix(text[m.end():])
        if m.group(1) in params and val is not None:
            pairs.append((m.group(1), val))
            pos = len(text) - len(rest)
    if pairs and {k for k, _ in pairs} == set(params):
        return f"{name}({', '.join(f'{k}={v}' for k, v in pairs)})"
    if not pairs and len(params) == 1:
        val, _ = literal_prefix(text)
        if val is not None:
            return f"{name}({val})"
    return None


def checks_from(question):
    """Example calls stated in the prompt: list of [call source, expected source or None].

    expected None means the call is itself a comparison that must be true.
    """
    src, tree = prompt_code(question)
    fn = entry_def(tree) if tree else None
    checks, seen = [], set()
    if fn is not None:
        name = fn.name
        params = [a.arg for a in fn.args.args + fn.args.kwonlyargs]
        doc = ast.get_docstring(fn, clean=True) or ""
    else:
        # MBPP style: prose plus "assert name(...) == ..." lines and no def.
        asserts = re.findall(r"^\s*assert\s+(.+?)\s*$", question, re.M)
        called = [c for a in asserts for c in re.findall(r"\b([A-Za-z_]\w*)\s*\(", a)
                  if c not in dir(builtins)]
        params, doc = [], ""
        if not called:
            # Prose with example lines and no def: "sum_digits(123) -> 6".
            called = [m.group(1) for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", question)
                      if m.group(1) not in dir(builtins) and m.group(1) not in ("def", "print")
                      and call_at(question, m.start())[0]
                      and ARROW.match(question[call_at(question, m.start())[1]:].split("\n")[0])]
            doc = question
        if not called:
            return None, [], src, tree
        name = max(called, key=called.count)
        for a in asserts:
            try:
                ast.parse(a, mode="eval")
            except SyntaxError:
                continue
            if name in a:
                checks.append([a, None])

    def add(call, exp):
        try:
            ast.parse(call, mode="eval")
            if exp is not None:
                ast.parse(exp, mode="eval")
        except SyntaxError:
            return
        if (call, exp) not in seen:
            seen.add((call, exp))
            checks.append([call, exp])

    lines = doc.splitlines()
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith(">>>"):
            call = s[3:].strip()
            i += 1
            while i < len(lines) and lines[i].strip().startswith("..."):
                call += "\n" + lines[i].strip()[3:].lstrip()
                i += 1
            out = []
            while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(">>>"):
                out.append(lines[i].strip())
                i += 1
            if out:
                add(call, "\n".join(out))
            elif re.search(r"[^=!<>]==[^=]", call):
                add(call, None)
            continue
        s = re.sub(r"^assert\s+", "", s)
        for m in re.finditer(rf"\b{re.escape(name)}\s*\(", s):
            call, end = call_at(s, m.start())
            if not call:
                continue
            a = ARROW.match(s[end:])
            exp = expected_from(a.group(1)) if a else None
            if exp is not None:
                add(call, exp)
        i += 1

    # "For lst = [1,2,3] the output should be 14", "Input: arr = [...] Output: 5"
    flat = " ".join(l.strip() for l in lines)
    for m in re.finditer(r"\b(?:for|input\s*:)\s*(.+?)\s*,?\s*(?:the output should be|output\s*:|should return)\s*(.+?)(?=\bfor\b|\binput\s*:|$)",
                         flat, re.I):
        call = kwargs_call(name, params, m.group(1))
        exp, _ = literal_prefix(m.group(2))
        if call and exp is not None:
            add(call, exp)
    return name, checks, src, tree


HARNESS = r'''
import contextlib, io, json, math, signal, sys
SRC, ENTRY, CHECKS = json.loads(PAYLOAD)
def _eq(a, b):
    if isinstance(a, float) or isinstance(b, float):
        try:
            return math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-6)
        except TypeError:
            return False
    if isinstance(a, (list, tuple)) and type(a) is type(b) and len(a) == len(b):
        return all(_eq(x, y) for x, y in zip(a, b))
    return a == b
def _alarm(*_):
    raise TimeoutError("this example ran for over 3 s")
signal.signal(signal.SIGALRM, _alarm)
res = {"defined": False, "error": None, "checks": []}
g = {"__name__": "solution"}
try:
    exec(compile(SRC, "solution.py", "exec"), g)
    res["defined"] = ENTRY is None or callable(g.get(ENTRY))
except BaseException as e:
    res["error"] = f"{type(e).__name__}: {e}"
for call, exp in CHECKS if res["defined"] else []:
    r = {"call": call, "expected": exp, "ok": False}
    buf = io.StringIO()
    try:
        signal.setitimer(signal.ITIMER_REAL, 3)
        with contextlib.redirect_stdout(buf):
            got = eval(call, g)
        signal.setitimer(signal.ITIMER_REAL, 0)
        r["got"] = repr(got)[:300]
        if exp is None:
            r["ok"] = got is True
        else:
            try:
                r["ok"] = bool(_eq(got, eval(exp, {})))
            except Exception:
                printed = buf.getvalue().strip()
                r["ok"] = exp.strip() in (repr(got), str(got), printed)
    except BaseException as e:
        signal.setitimer(signal.ITIMER_REAL, 0)
        r["error"] = f"{type(e).__name__}: {e}"[:300]
    res["checks"].append(r)
print("\n@@RESULT@@" + json.dumps(res))
'''


def err_tail(err):
    return "\n".join(l for l in err.strip().splitlines() if "_run.py" not in l)[-600:]


def self_check(code, name, checks):
    if name is None:
        # Free-form request with no function to call: run it as a program.
        # stdin is empty (maya/sandbox.py), so a program that asks for input stops at
        # its first input() with EOFError; that is a program waiting for a user, not a bug.
        ok, out, err = run_python(code, timeout_s=10)
        needs_input = not ok and re.search(r"(?m)^EOFError\b", err) is not None
        return {"defined": ok or needs_input, "error": None if ok or needs_input else err_tail(err),
                "checks": [], "stdout": out[-2000:], "needs_input": needs_input}
    payload = json.dumps([code, name, checks])
    ok, out, err = run_python(f"PAYLOAD = {payload!r}\n" + HARNESS, timeout_s=10)
    if "@@RESULT@@" not in out:
        return {"defined": False, "error": err_tail(err) or "no result", "checks": []}
    return json.loads(out.rsplit("@@RESULT@@", 1)[1])


def unbound_names(tree):
    bound = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            bound |= {(a.asname or a.name).split(".")[0] for a in n.names}
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(n.name)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            bound.add(n.id)
        elif isinstance(n, ast.arg):
            bound.add(n.arg)
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    return used - bound


def keep_node(n, name):
    if isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return True
    if isinstance(n, (ast.Assign, ast.AnnAssign)):
        calls = {c.func.id for c in ast.walk(n) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
        return not calls & {name, "print", "input"}
    return False


def clean(code, name, question, ptree):
    """Strip example usage and tests from the model's code, add what it left out.

    Returns (code, problem) where problem is None or a message for a retry.
    """
    psrc, _ = prompt_code(question)
    if psrc and name and not re.search(rf"\bdef\s+{re.escape(name)}\s*\(", code):
        # Body only, without the def line: put it under the prompt's signature.
        # extract() stripped the first line's indent, so try both layouts.
        first, _, rest = code.partition("\n")
        for body in ("    " + first + "\n" + rest, "\n".join("    " + l for l in code.splitlines())):
            try:
                ast.parse(psrc.rstrip() + "\n" + body)
                code = psrc.rstrip() + "\n" + body
                break
            except SyntaxError:
                pass
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return code, f"SyntaxError: {e.msg} (line {e.lineno})"
    lines = code.splitlines()
    keep = []
    for n in tree.body:
        if name is None or keep_node(n, name):
            start = min([n.lineno] + [d.lineno for d in getattr(n, "decorator_list", [])]) - 1
            keep.append("\n".join(lines[start:n.end_lineno]))
    code = "\n\n".join(keep)
    tree = ast.parse(code)
    defined = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    head = []
    if ptree is not None:
        plines = psrc.splitlines()
        for n in ptree.body:
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                seg = "\n".join(plines[n.lineno - 1:n.end_lineno])
                if seg.strip() not in code:
                    head.append(seg)
            # Helpers the prompt defines in full, which the model may call but not repeat.
            elif (isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name != name
                  and n.name not in defined and not (len(n.body) == 1 and isinstance(n.body[0], ast.Expr))):
                head.append("\n".join(plines[n.lineno - 1:n.end_lineno]))
    missing = unbound_names(ast.parse("\n\n".join(head + [code])))
    head = [f"import {m}" for m in sorted(missing & STDLIB)] + head
    if missing & TYPING:
        head.insert(0, f"from typing import {', '.join(sorted(missing & TYPING))}")
    code = "\n".join(head + [code]) if head else code
    if name and name not in defined:
        return code, f"The code does not define the function `{name}`."
    return code, None


def hardcoded(code, checks):
    """Expected example outputs that the code returns as literals, e.g. `if n == 4: return 13`."""
    expected = []
    for _, exp in checks:
        try:
            v = ast.literal_eval(exp) if exp is not None else None
        except (ValueError, SyntaxError):
            continue
        # Small values are ordinary base cases (return 0, return -1, return "No").
        if (isinstance(v, bool) or v is None or (isinstance(v, int) and -1 <= v <= 1)
                or (isinstance(v, (str, list, tuple)) and len(v) <= 3)):
            continue
        expected.append(v)
    found = []
    for n in ast.walk(ast.parse(code)):
        if isinstance(n, ast.Return) and n.value is not None:
            try:
                v = ast.literal_eval(n.value)
            except (ValueError, SyntaxError, TypeError):
                continue
            if v in expected and v not in found:
                found.append(v)
    # Two literal returns can be base cases; three matching examples is a lookup table.
    return found if len(found) >= 3 else []


def feedback(problem, result, explain=False):
    if problem:
        msg = problem
    elif not result["defined"]:
        msg = f"Running the code failed:\n{result['error']}"
    else:
        bad = []
        for r in result["checks"]:
            if r["ok"]:
                continue
            exp = r["expected"] if r["expected"] is not None else "True"
            got = f"raised {r['error']}" if "error" in r else f"returned {r['got']}"
            bad.append(f"- {r['call']} {got}, expected {exp}")
        msg = "The function was run on the examples in the docstring and these failed:\n" + "\n".join(bad[:6])
    ask = ("First explain in two or three sentences why the code is wrong, then give the "
           "complete corrected code in one ```python code block." if explain else
           "Fix the code so it does what the task asks. Return the complete corrected "
           "code in one ```python code block.")
    return msg + "\n\n" + ask


def answer(eng, path, question):
    t0 = time.perf_counter()
    max_new = int(eng.opts.get("max_new", 768))
    selfcheck = eng.opts.get("selfcheck", "1") == "1"
    retries = int(eng.opts.get("retries", 2)) if selfcheck else 0
    budget = float(eng.opts.get("budget_s", 90))
    explain = eng.opts.get("fix", "plain") == "explain"
    coders = [eng.opts.get("coder", "vlm")]
    if selfcheck and eng.opts.get("fallback", "qwen25-3b") not in ("none", coders[0]):
        coders.append(eng.opts.get("fallback", "qwen25-3b"))
    name, checks, _, ptree = checks_from(question)
    prompt, system, variant = question, SYSTEM, eng.opts.get("prompt", "plain")
    if variant == "full" and name:
        prompt += FULL_ASK.format(name=name)
    if variant == "nodoc":
        system += NODOC

    attempts, best, load_s = [], None, {}
    t_gen, n_out = 0.0, 0
    for coder in coders:
        if attempts and time.perf_counter() - t0 > budget:
            break
        t = time.perf_counter()
        # A VlmCoder still bound here keeps the VLM alive through gpu_model's swap,
        # so both models would sit on the 8 GB card.
        m = None
        m = model(eng, coder)
        load_s[coder] = round(time.perf_counter() - t, 2)
        history = []
        for k in range(retries + 1):
            if k and time.perf_counter() - t0 > budget:
                break
            user = prompt if k == 0 else feedback(problem, result, explain)
            text, ginfo = m.text(user, system, max_new_tokens=max_new, history=history)
            t_gen += ginfo.get("model_s", 0)
            n_out += ginfo.get("output_tokens", 0)
            history.append(([{"type": "text", "text": user}], text))
            code, problem = clean(extract(text), name, question, ptree)
            if problem is None and selfcheck:
                result = self_check(code, name, checks)
            else:
                result = {"defined": problem is None, "error": problem, "checks": []}
            passed = sum(r["ok"] for r in result["checks"])
            hc = hardcoded(code, checks) if problem is None and selfcheck else []
            score = (problem is None and result["defined"], not hc, passed)
            if hc:
                problem = (f"The code returns the docstring examples as fixed values "
                           f"({', '.join(map(repr, hc[:4]))}). Write a general solution that "
                           f"works for any input.")
            attempts.append({"coder": coder, "passed": passed, "problem": problem or result.get("error")})
            # Ties keep the earlier attempt: the first greedy answer is not anchored on a wrong fix.
            if best is None or score > best[0]:
                best = (score, code, result, coder)
            if not selfcheck or (score[0] and score[1] and passed == len(checks)):
                break
        if best[0][0] and best[0][1] and best[0][2] == len(checks):
            break
    (ok_def, not_hc, passed), code, result, coder = best
    info = {"route": "code", "coder": coder, "attempts": len(attempts),
            "self_checks": len(checks) if selfcheck else 0, "self_checks_passed": passed,
            "self_check_ok": bool(ok_def and not_hc and passed == len(checks)),
            "hardcoded": not not_hc, "model_s": round(t_gen, 3), "output_tokens": n_out,
            "model_switch_s": load_s, "attempt_log": attempts}
    if result.get("stdout"):
        info["run_output"] = result["stdout"]
    if result.get("needs_input"):
        info["needs_input"] = True
        info["note"] = ("The program asks for keyboard input, so it was only run up to its "
                        "first prompt, with no input typed.")
    return code, info
