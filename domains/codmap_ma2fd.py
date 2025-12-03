#!/usr/bin/env python3
"""Convert CoDMAP15 multi-agent PDDL files into classical PDDL
suitable for planners like Fast Downward.

Main transformations (domain files):
 1. Remove :multi-agent and :unfactored-privacy from :requirements.
 2. Remove :private wrappers in :predicates, keeping the inner predicates.
 3. Move :agent parameter of actions into :parameters.

Problem files:
 1. Remove private object declarations in :objects and turn them
    into regular objects.

Usage:
    python codmap_ma2fd.py /path/to/domains/codmap15 \
           -o /path/to/output_codmap15_fd

The script recursively scans the directory for *.pddl files and
writes transformed versions into the output directory, preserving
subdirectory structure.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Tuple, Union, Optional

Sexp = Union[str, List["Sexp"]]


# ---------------------- Tokenizer & Parser ----------------------

def tokenize(s: str) -> List[str]:
    """Tokenize a PDDL file into Lisp-style tokens.

    - Removes line comments starting with ';'.
    - Keeps parentheses as separate tokens.
    """
    tokens: List[str] = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c.isspace():
            i += 1
            continue
        if c == ';':
            # Comment until end of line
            while i < n and s[i] != "\n":
                i += 1
            continue
        if c in "()":
            tokens.append(c)
            i += 1
            continue
        # Symbol
        start = i
        while i < n and (not s[i].isspace()) and s[i] not in "()":
            i += 1
        tokens.append(s[start:i])
    return tokens


def parse_sexp(tokens: List[str]) -> Tuple[Sexp, int]:
    """Parse tokens into a nested Python list (S-expression).

    Returns (sexp, next_index).
    """
    if not tokens:
        raise ValueError("No tokens to parse")

    def _parse(i: int) -> Tuple[Sexp, int]:
        if i >= len(tokens):
            raise ValueError("Unexpected end of tokens")
        if tokens[i] == "(":
            lst: List[Sexp] = []
            i += 1
            while i < len(tokens) and tokens[i] != ")":
                elem, i = _parse(i)
                lst.append(elem)
            if i >= len(tokens):
                raise ValueError("Unbalanced parentheses in input")
            return lst, i + 1
        elif tokens[i] == ")":
            raise ValueError("Unexpected ')' at position %d" % i)
        else:
            return tokens[i], i + 1

    sexp, next_i = _parse(0)
    return sexp, next_i


# ---------------------- Utilities ----------------------

def is_symbol(x: Sexp, name: str) -> bool:
    return isinstance(x, str) and x.lower() == name.lower()


def find_sections(root: List[Sexp]) -> List[Sexp]:
    """Return list of top-level sections within a (define ...) form."""
    # (define (domain ...) <sections...>)
    return root[2:]


# ---------------------- Domain Transform ----------------------

def transform_requirements(sec: List[Sexp]) -> None:
    """Remove :multi-agent and :unfactored-privacy from a :requirements list."""
    if not sec or not is_symbol(sec[0], ":requirements"):
        return
    forbidden = {":multi-agent", ":multiagent", ":unfactored-privacy"}
    new_sec: List[Sexp] = [sec[0]]
    for t in sec[1:]:
        if isinstance(t, str) and t.lower() in forbidden:
            continue
        new_sec.append(t)
    sec[:] = new_sec


def transform_predicates(sec: List[Sexp]) -> None:
    """Flatten (:private ... predicates ...) inside :predicates.

    Example:
      (:predicates
          (on ?x - block ?y - block)
          (:private ?agent - agent
             (holding ?agent - agent ?x - block)
             (handempty ?agent - agent)
          )
      )

    becomes

      (:predicates
          (on ?x - block ?y - block)
          (holding ?agent - agent ?x - block)
          (handempty ?agent - agent)
      )
    """
    if not sec or not is_symbol(sec[0], ":predicates"):
        return

    new_items: List[Sexp] = [sec[0]]
    for item in sec[1:]:
        if isinstance(item, list) and item and is_symbol(item[0], ":private"):
            # Structure is typically [':private', owner, owner-type..., <pred>...]
            # We keep only the predicate S-expressions (lists).
            for sub in item[1:]:
                if isinstance(sub, list):
                    new_items.append(sub)
                # Non-list elements correspond to the agent/type descriptor and
                # are ignored.
        else:
            new_items.append(item)
    sec[:] = new_items


def transform_action(action: List[Sexp]) -> None:
    """Move :agent arguments into :parameters of an :action.

    From:
      (:action pick-up
         :agent ?a - agent
         :parameters (?x - block)
         ...)

    To:
      (:action pick-up
         :parameters (?a - agent ?x - block)
         ...)
    """
    if not action or not is_symbol(action[0], ":action"):
        return

    # Collect agent argument tokens and remove :agent section.
    agent_tokens: List[Sexp] = []

    i = 2  # skip ':action' and name
    while i < len(action):
        item = action[i]
        if is_symbol(item, ":agent"):
            # Gather all subsequent non-keyword, non-list tokens as agent tokens
            j = i + 1
            while j < len(action):
                nxt = action[j]
                if isinstance(nxt, list):
                    break
                if isinstance(nxt, str) and nxt.startswith(":"):
                    break
                agent_tokens.append(nxt)
                j += 1
            # Remove :agent and its arguments
            del action[i:j]
            # Do not advance i; it now points at the next section
            continue
        i += 1

    if not agent_tokens:
        return

    # Attach agent_tokens to :parameters
    params_list: Optional[List[Sexp]] = None

    i = 2
    while i < len(action):
        item = action[i]
        if is_symbol(item, ":parameters"):
            if i + 1 < len(action) and isinstance(action[i + 1], list):
                params_list = action[i + 1]
            break
        i += 1

    if params_list is not None:
        # Insert at the beginning of the existing parameter list
        params_list[0:0] = agent_tokens
    else:
        # No :parameters section existed (unlikely, but just in case).
        # Insert a new one right after the action name.
        name = action[1]
        rest = action[2:]
        new_params = list(agent_tokens)
        action[:] = [action[0], name, ":parameters", new_params] + rest


def transform_domain(root: Sexp) -> Sexp:
    if not isinstance(root, list) or not root:
        return root

    if not is_symbol(root[0], "define"):
        return root

    # Expect (define (domain ...) sections...)
    sections = find_sections(root)
    for sec in sections:
        if isinstance(sec, list) and sec:
            if is_symbol(sec[0], ":requirements"):
                transform_requirements(sec)
            elif is_symbol(sec[0], ":predicates"):
                transform_predicates(sec)
            elif is_symbol(sec[0], ":action"):
                transform_action(sec)
    return root


# ---------------------- Problem Transform ----------------------

def transform_objects(sec: List[Sexp]) -> None:
    """Flatten private object declarations in :objects.

    Example:
      (:objects
         a - block
         (:private a1
            a1 - agent
         )
      )

    becomes
      (:objects
         a - block
         a1 - agent
      )
    """
    if not sec or not is_symbol(sec[0], ":objects"):
        return

    new_items: List[Sexp] = [sec[0]]
    for item in sec[1:]:
        if isinstance(item, list) and item and is_symbol(item[0], ":private"):
            # Typical structure for problems like:
            # (:private a1 a1 - agent)
            # or
            # (:private a1
            #    a1 - agent
            # )
            # First argument after :private is the owner; we ignore it,
            # and keep the rest as standard object declarations.
            if len(item) > 2:
                # Drop owner (item[1]) and keep item[2:]
                for sub in item[2:]:
                    new_items.append(sub)
        else:
            new_items.append(item)
    sec[:] = new_items


def transform_problem(root: Sexp) -> Sexp:
    if not isinstance(root, list) or not root:
        return root
    if not is_symbol(root[0], "define"):
        return root

    # (define (problem ...) (:domain ...) sections...)
    for sec in root[2:]:
        if isinstance(sec, list) and sec:
            if is_symbol(sec[0], ":objects"):
                transform_objects(sec)
    return root


# ---------------------- Pretty Printer ----------------------

def format_sexp(expr: Sexp, level: int = 0) -> str:
    """Pretty-print an S-expression back to PDDL-like text."""
    indent = "  " * level
    if isinstance(expr, str):
        return expr

    if not expr:
        return "()"

    head = expr[0]
    # Decide whether to pretty-print this list on multiple lines
    multiline_heads = {
        "define",
        ":predicates",
        ":types",
        ":objects",
        ":init",
        ":goal",
        ":requirements",
        ":action",
        "and",
        "or",
        "forall",
        "exists",
        "when",
    }

    if isinstance(head, str) and head.lower() in multiline_heads:
        inner_lines = []
        for sub in expr[1:]:
            inner_lines.append("{}{}".format("  " * (level + 1), format_sexp(sub, level + 1)))
        inner = "\n".join(inner_lines)
        return f"({head}\n{inner}\n{indent})"

    # Simple inline list
    inner = " ".join(format_sexp(sub, 0) for sub in expr[1:])
    return f"({head} {inner})"


# ---------------------- File Handling ----------------------

def classify_root(root: Sexp) -> Optional[str]:
    """Return 'domain', 'problem' or None based on top-level form."""
    if not isinstance(root, list) or not root or not is_symbol(root[0], "define"):
        return None
    if len(root) < 2 or not isinstance(root[1], list) or not root[1]:
        return None
    header = root[1]
    if isinstance(header[0], str) and header[0].lower() == "domain":
        return "domain"
    if isinstance(header[0], str) and header[0].lower() == "problem":
        return "problem"
    return None


def transform_file(text: str, path: Path) -> str:
    tokens = tokenize(text)
    if not tokens:
        raise ValueError(f"Empty or comment-only file: {path}")

    sexp, _used = parse_sexp(tokens)
    # Ignore any trailing tokens beyond the first top-level form.

    kind = classify_root(sexp)
    if kind == "domain":
        sexp = transform_domain(sexp)
    elif kind == "problem":
        sexp = transform_problem(sexp)
    else:
        # Not a standard domain/problem; return unchanged.
        return text

    return format_sexp(sexp) + "\n"


# ---------------------- CLI ----------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Convert CoDMAP15 multi-agent PDDL to classical PDDL.")
    parser.add_argument("codmap_dir", help="Path to codmap15 directory (e.g., domains/codmap15)")
    parser.add_argument("-o", "--output-dir", help="Output directory (default: <codmap_dir>_fd)")

    args = parser.parse_args(argv)

    codmap_dir = Path(args.codmap_dir).resolve()
    if not codmap_dir.is_dir():
        print(f"ERROR: {codmap_dir} is not a directory", file=sys.stderr)
        return 1

    out_root = Path(args.output_dir).resolve() if args.output_dir else codmap_dir.with_name(codmap_dir.name + "_fd")
    out_root.mkdir(parents=True, exist_ok=True)

    for pddl_path in codmap_dir.rglob("*.pddl"):
        rel = pddl_path.relative_to(codmap_dir)
        out_path = out_root / rel
        out_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            text = pddl_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = pddl_path.read_text(encoding="latin-1")

        try:
            new_text = transform_file(text, pddl_path)
        except Exception as e:
            print(f"[WARN] Failed to transform {pddl_path}: {e}", file=sys.stderr)
            new_text = text  # fall back to original

        out_path.write_text(new_text, encoding="utf-8")
        print(f"Processed {pddl_path} -> {out_path}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
