"""Builders for DataConverterFormula token lists.

Expressions are plain lists of token elements. Helpers compose them.
"""
from rml import E

FN = {"min": 0, "max": 1, "round": 2, "ceil": 3, "floor": 4, "sqrt": 5, "pow": 6}
OP = {"+": 0, "-": 1, "*": 2, "/": 3}


def inp():
    return [E("FormulaTokenInput")]


def val(v):
    return [E("FormulaTokenValue", operationValue=float(v))]


def prop(path, default=1.0):
    """A token that reads another view model number property."""
    return [E("FormulaTokenValue", [E("DataBindContext", sourcePathIds=path, propertyKey=777)],
              operationValue=float(default))]


def op(sym):
    return [E("FormulaTokenOperation", operationType=OP[sym])]


def fn(name, *args):
    out = [E("FormulaTokenFunction", functionType=FN[name])]
    for i, a in enumerate(args):
        if i:
            out.append(E("FormulaTokenArgumentSeparator"))
        out += a
    out.append(E("FormulaTokenParenthesisClose"))
    return out


def par(x):
    return [E("FormulaTokenParenthesisOpen")] + x + [E("FormulaTokenParenthesisClose")]


def bin_(a, sym, b):
    return a + op(sym) + b


def clamp01(x):
    return fn("min", val(1), fn("max", val(0), x))


def step_le(x, t):
    """1 when x <= t, else 0 (sharp ramp just above t)."""
    return clamp01(par(par(val(t) + op("-") + x) + op("*") + val(1000) + op("+") + val(1)))


def step_ge(x, t):
    """1 when x >= t."""
    return clamp01(par(par(x + op("-") + val(t)) + op("*") + val(1000) + op("+") + val(1)))
